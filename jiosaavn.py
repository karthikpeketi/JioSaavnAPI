import requests
import endpoints
import helper
import json
from traceback import print_exc
import re
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from functools import lru_cache

# Create a session with connection pooling
session = requests.Session()
retry_strategy = Retry(
    total=3,
    backoff_factor=0.1,
    status_forcelist=[500, 502, 503, 504]
)
adapter = HTTPAdapter(
    pool_connections=100,
    pool_maxsize=100,
    max_retries=retry_strategy,
    pool_block=False
)
session.mount("http://", adapter)
session.mount("https://", adapter)

@lru_cache(maxsize=1000)
def search_for_song(query, lyrics, songdata):
    if query.startswith('http') and 'saavn.com' in query:
        id = get_song_id(query)
        return get_song(id, lyrics)

    search_base_url = endpoints.search_base_url+query
    response = session.get(search_base_url).text.encode().decode('unicode-escape')
    pattern = r'\(From "([^"]+)"\)'
    response = json.loads(re.sub(pattern, r"(From '\1')", response))
    song_response = response['songs']['data']
    if not songdata:
        return song_response
    songs = []
    for song in song_response:
        id = song['id']
        song_data = get_song(id, lyrics)
        if song_data:
            songs.append(song_data)
    return songs

@lru_cache(maxsize=1000)
def get_song(id, lyrics):
    try:
        song_details_base_url = endpoints.song_details_base_url+id
        song_response = session.get(
            song_details_base_url).text.encode().decode('unicode-escape')
        song_response = json.loads(song_response)
        song_data = helper.format_song(song_response[id], lyrics)
        if song_data:
            return song_data
    except:
        return None

@lru_cache(maxsize=100)
def get_song_id(url):
    res = session.get(url, data=[('bitrate', '320')])
    try:
        return(res.text.split('"pid":"'))[1].split('","')[0]
    except IndexError:
        return res.text.split('"song":{"type":"')[1].split('","image":')[0].split('"id":"')[-1]

@lru_cache(maxsize=100)
def get_album(album_id, lyrics):
    songs_json = []
    try:
        response = session.get(endpoints.album_details_base_url+album_id)
        if response.status_code == 200:
            songs_json = response.text.encode().decode('unicode-escape')
            songs_json = json.loads(songs_json)
            return helper.format_album(songs_json, lyrics)
    except Exception as e:
        print(e)
        return None

@lru_cache(maxsize=100)
def get_album_id(input_url):
    res = session.get(input_url)
    try:
        return res.text.split('"album_id":"')[1].split('"')[0]
    except IndexError:
        return res.text.split('"page_id","')[1].split('","')[0]

@lru_cache(maxsize=100)
def get_playlist(listId, lyrics):
    try:
        response = session.get(endpoints.playlist_details_base_url+listId)
        if response.status_code == 200:
            songs_json = response.text.encode().decode('unicode-escape')
            songs_json = json.loads(songs_json)
            return helper.format_playlist(songs_json, lyrics)
        return None
    except Exception:
        print_exc()
        return None

@lru_cache(maxsize=100)
def get_playlist_id(input_url):
    res = session.get(input_url).text
    try:
        return res.split('"type":"playlist","id":"')[1].split('"')[0]
    except IndexError:
        return res.split('"page_id","')[1].split('","')[0]

@lru_cache(maxsize=1000)
def get_lyrics(id):
    url = endpoints.lyrics_base_url+id
    lyrics_json = session.get(url).text
    lyrics_text = json.loads(lyrics_json)
    return lyrics_text['lyrics']
