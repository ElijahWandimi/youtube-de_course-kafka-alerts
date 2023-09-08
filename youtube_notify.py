#!/usr/bin/env python

import sys
import logging
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


def main():
    logging.info("START")

    google_api_key = config['google_api_key']
    playlist_id = config['youtube_playlist_id']

    for video_item in fetch_playlist_items(google_api_key, playlist_id):
        video_id = video_item['contentDetails']['videoId']
        for video in fetch_videos(google_api_key, video_id):
            logging.info(f"Got {pformat(summarise_video(video))}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    sys.exit(main())
