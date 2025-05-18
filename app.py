from flask import Flask, request, redirect, jsonify, json
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import time
import jiosaavn
import os
from traceback import print_exc
from flask_cors import CORS
from flask_caching import Cache
from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET", 'thankyoutonystark#weloveyou3000')
CORS(app)

# Add ProxyFix for better header handling
app.wsgi_app = ProxyFix(app.wsgi_app)

# Environment configuration
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'development')
DEBUG = os.environ.get('DEBUG', 'false').lower() == 'true'

# Configure limiter with different rates for prod/dev
if ENVIRONMENT == 'production':
    default_limits = ["200 per day", "50 per hour"]
else:
    default_limits = ["1000 per day", "200 per hour"]

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=default_limits
)

# Configure caching
try:
    if ENVIRONMENT == 'production' and os.environ.get('REDIS_URL'):
        cache_config = {
            'CACHE_TYPE': 'redis',
            'CACHE_REDIS_URL': os.environ.get('REDIS_URL'),
            'CACHE_DEFAULT_TIMEOUT': 300
        }
    else:
        cache_config = {
            'CACHE_TYPE': 'simple',
            'CACHE_DEFAULT_TIMEOUT': 60
        }
    cache = Cache(app, config=cache_config)
except Exception as e:
    print(f"Warning: Caching initialization failed: {e}")
    # Fallback to simple cache if Redis fails
    cache_config = {
        'CACHE_TYPE': 'simple',
        'CACHE_DEFAULT_TIMEOUT': 60
    }
    cache = Cache(app, config=cache_config)

# Optimize response compression
app.config['COMPRESS_ALGORITHM'] = 'gzip'
app.config['COMPRESS_LEVEL'] = 6
app.config['COMPRESS_MIN_SIZE'] = 500

# Configure async support
app.config['ASYNC_MODE'] = 'gevent'


@app.route('/')
def home():
    return redirect("https://cyberboysumanjay.github.io/JioSaavnAPI/")


@app.route('/song/')
@cache.cached(timeout=300)
def search():
    lyrics = False
    songdata = True
    query = request.args.get('query')
    lyrics_ = request.args.get('lyrics')
    songdata_ = request.args.get('songdata')
    if lyrics_ and lyrics_.lower() != 'false':
        lyrics = True
    if songdata_ and songdata_.lower() != 'true':
        songdata = False
    if query:
        return jsonify(jiosaavn.search_for_song(query, lyrics, songdata))
    else:
        error = {
            "status": False,
            "error": 'Query is required to search songs!'
        }
        return jsonify(error)


@app.route('/song/get/')
def get_song():
    lyrics = False
    id = request.args.get('id')
    lyrics_ = request.args.get('lyrics')
    if lyrics_ and lyrics_.lower() != 'false':
        lyrics = True
    if id:
        resp = jiosaavn.get_song(id, lyrics)
        if not resp:
            error = {
                "status": False,
                "error": 'Invalid Song ID received!'
            }
            return jsonify(error)
        else:
            return jsonify(resp)
    else:
        error = {
            "status": False,
            "error": 'Song ID is required to get a song!'
        }
        return jsonify(error)


@app.route('/playlist/')
@cache.cached(timeout=300)
def playlist():
    lyrics = False
    query = request.args.get('query')
    lyrics_ = request.args.get('lyrics')
    if lyrics_ and lyrics_.lower() != 'false':
        lyrics = True
    if query:
        id = jiosaavn.get_playlist_id(query)
        songs = jiosaavn.get_playlist(id, lyrics)
        return jsonify(songs)
    else:
        error = {
            "status": False,
            "error": 'Query is required to search playlists!'
        }
        return jsonify(error)


@app.route('/album/')
@cache.cached(timeout=300)
def album():
    lyrics = False
    query = request.args.get('query')
    lyrics_ = request.args.get('lyrics')
    if lyrics_ and lyrics_.lower() != 'false':
        lyrics = True
    if query:
        id = jiosaavn.get_album_id(query)
        songs = jiosaavn.get_album(id, lyrics)
        return jsonify(songs)
    else:
        error = {
            "status": False,
            "error": 'Query is required to search albums!'
        }
        return jsonify(error)


@app.route('/lyrics/')
def lyrics():
    query = request.args.get('query')

    if query:
        try:
            if 'http' in query and 'saavn' in query:
                id = jiosaavn.get_song_id(query)
                lyrics = jiosaavn.get_lyrics(id)
            else:
                lyrics = jiosaavn.get_lyrics(query)
            response = {}
            response['status'] = True
            response['lyrics'] = lyrics
            return jsonify(response)
        except Exception as e:
            error = {
                "status": False,
                "error": str(e)
            }
            return jsonify(error)

    else:
        error = {
            "status": False,
            "error": 'Query containing song link or id is required to fetch lyrics!'
        }
        return jsonify(error)


@app.route('/result/')
def result():
    lyrics = False
    query = request.args.get('query')
    lyrics_ = request.args.get('lyrics')
    if lyrics_ and lyrics_.lower() != 'false':
        lyrics = True

    if 'saavn' not in query:
        return jsonify(jiosaavn.search_for_song(query, lyrics, True))
    try:
        if '/song/' in query:
            print("Song")
            song_id = jiosaavn.get_song_id(query)
            song = jiosaavn.get_song(song_id, lyrics)
            return jsonify(song)

        elif '/album/' in query:
            print("Album")
            id = jiosaavn.get_album_id(query)
            songs = jiosaavn.get_album(id, lyrics)
            return jsonify(songs)

        elif '/playlist/' or '/featured/' in query:
            print("Playlist")
            id = jiosaavn.get_playlist_id(query)
            songs = jiosaavn.get_playlist(id, lyrics)
            return jsonify(songs)

    except Exception as e:
        print_exc()
        error = {
            "status": True,
            "error": str(e)
        }
        return jsonify(error)
    return None


if __name__ == '__main__':
    app.debug = DEBUG
    app.run(host='0.0.0.0', port=5100, use_reloader=True, threaded=True)
