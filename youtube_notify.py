#!/usr/bin/env python

import sys
import logging
from confluent_kafka import SerializingProducer
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.avro import AvroSerializer
from confluent_kafka.serialization import StringSerializer
import requests
import json
from pprint import pformat
from config import config


playlist_url = 'https://www.googleapis.com/youtube/v3/playlistItems'
video_url = 'https://www.googleapis.com/youtube/v3/videos'


def fetch_playlist_items_page(google_api_key, playlist_id, page_token = None):
    response = requests.get(playlist_url, params = {
        "key": google_api_key,
        "playlist_id": playlist_id,
        "part": 'contentDetails',
        "pageToken": page_token,
    })
    payload = json.loads(response.text)

    logging.debug(f"Got {payload}")
    return payload


def fetch_playlist_items(google_api_key, playlist_id, page_token = None):
    payload = fetch_playlist_items_page(google_api_key, playlist_id, page_token)

    yield from payload['items']

    next_page_token = payload.get('nextPageToken')

    if next_page_token is not None:
        yield from fetch_playlist_items(google_api_key, playlist_id, next_page_token)


def fetch_videos_page(google_api_key, video_id, page_token = None):
    response = requests.get(video_url, params = {
        "key": google_api_key,
        "id": video_id,
        "part": 'snippet, statistics',
        "pageToken": page_token,
    })
    payload = json.loads(response.text)

    logging.debug(f"Got {payload}")
    return payload


def fetch_videos(google_api_key, video_id, page_token = None):
    payload = fetch_videos_page(google_api_key, video_id, page_token)

    yield from payload['items']

    next_page_token = payload.get('nextPageToken')

    if next_page_token is not None:
        yield from fetch_videos(google_api_key, video_id, next_page_token)


def summarise_video(video):
    return {
        "video_id": video['id'],
        "title": video['snippet']['title'],
        "views": int(video['statistics'].get('viewCount', 0)),
        "likes": int(video['statistics'].get('likeCount', 0)),
        "comments": int(video['statistics'].get('commentCount'), 0)
    }


def on_delivery(error, record):
    pass


def main():
    logging.info("START")

    schema_registry_client = SchemaRegistryClient(config['schema_registry'])
    kahan_de_value_schema = schema_registry_client.get_latest_version('youtube_kahan_de_course-value')

    kafka_config = config['kafka'] | {
        "key.serializer": StringSerializer(),
        "value.serializer": AvroSerializer(
            schema_registry_client,
            kahan_de_value_schema.schema.schema_str,
            ),
    }
    producer = SerializingProducer(kafka_config)

    google_api_key = config['google_api_key']
    playlist_id = config['youtube_playlist_id']

    for video_item in fetch_playlist_items(google_api_key, playlist_id):
        video_id = video_item['contentDetails']['videoId']
        for video in fetch_videos(google_api_key, video_id):
            logging.info(f"Got {pformat(summarise_video(video))}")

            producer.produce(
                topic = 'youtube_kahan_de_course',
                key = video_id,
                value = {
                    "TITLE": video['snippet']['title'],
                    "VIEWS": int(video['statistics'].get('viewCount', 0)),
                    "LIKES": int(video['statistics'].get('likeCount', 0)),
                    "COMMENTS": int(video['statistics'].get('commentCount'), 0)
                },
                on_delivery = on_delivery
            )

    producer.flush()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    sys.exit(main())
