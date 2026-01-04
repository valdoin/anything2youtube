from flask import Flask, render_template, request, jsonify, Response, stream_with_context
import yt_dlp
import requests
from bs4 import BeautifulSoup
import json
import re
import urllib.parse
import os

app = Flask(__name__)
app.json.ensure_ascii = False 

URL_CACHE = {}

YDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'extract_flat': False,
    'no_warnings': True,
    'cookiefile': 'cookies.txt',
    'nocheckcertificate': True,
    'ignoreerrors': True,
    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'remote_components': ['ejs:github'],
}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/stream')
def stream():
    video_url = request.args.get('url')
    if not video_url:
        return "Missing URL", 400
    
    range_header = request.headers.get('Range', None)
    req_headers = {
        'User-Agent': YDL_OPTIONS['user_agent']
    }
    
    if range_header:
        req_headers['Range'] = range_header

    try:
        req = requests.get(video_url, stream=True, verify=False, headers=req_headers)
        
        resp_headers = {
            'Content-Type': 'audio/mp4',
            'Accept-Ranges': 'bytes',
            'Access-Control-Allow-Origin': '*',
            'Connection': 'keep-alive'
        }

        if 'Content-Length' in req.headers:
            resp_headers['Content-Length'] = req.headers['Content-Length']
        
        if 'Content-Range' in req.headers:
            resp_headers['Content-Range'] = req.headers['Content-Range']

        status_code = req.status_code

        def generate():
            for chunk in req.iter_content(chunk_size=131072): 
                if chunk:
                    yield chunk

        return Response(stream_with_context(generate()), headers=resp_headers, status=status_code)
    except Exception:
        return "", 500

def scrape_spotify_embed(spotify_url):
    if "open.spotify.com" in spotify_url and "embed" not in spotify_url:
        embed_url = spotify_url.replace("open.spotify.com", "open.spotify.com/embed")
    else:
        embed_url = spotify_url
    try:
        headers = {'User-Agent': YDL_OPTIONS['user_agent']}
        response = requests.get(embed_url, headers=headers)
        if response.status_code != 200: return []
        soup = BeautifulSoup(response.text, 'html.parser')
        script_tag = soup.find('script', id='__NEXT_DATA__')
        if not script_tag: return []
        data = json.loads(script_tag.string)
        try:
            entity = data['props']['pageProps']['state']['data']['entity']
            track_list = entity['trackList']
            album_artist = ""
            if 'artists' in entity and len(entity['artists']) > 0:
                album_artist = entity['artists'][0]['name']
        except KeyError: return []
        cleaned_tracks = []
        for item in track_list:
            try:
                title = item.get('title')
                artist = item.get('subtitle') or album_artist
                if artist: artist = artist.replace('\u00a0', ' ')
                if title:
                    cleaned_tracks.append({
                        "title": title,
                        "artist": artist,
                        "query": f"{artist} - {title}"
                    })
            except: continue
        return cleaned_tracks
    except: return []

def scrape_deezer(url):
    try:
        object_id = re.search(r'/(playlist|album|track)/(\d+)', url)
        if not object_id: return []
        type_content, id_content = object_id.groups()
        response = requests.get(f"https://api.deezer.com/{type_content}/{id_content}")
        data = response.json()
        raw_tracks = data.get('tracks', {}).get('data') or data.get('data') or ([data] if type_content == 'track' else [])
        tracks = []
        for t in raw_tracks:
            title = t.get('title')
            artist = t.get('artist', {}).get('name')
            if title and artist:
                tracks.append({"title": title, "artist": artist, "query": f"{artist} - {title}"})
        return tracks
    except: return []

def scrape_apple_music(url):
    try:
        headers = {'User-Agent': YDL_OPTIONS['user_agent']}
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        script_tag = soup.find('script', id='serialized-server-data')
        if not script_tag:
            clean_url = url.replace('embed.music.apple.com', 'music.apple.com')
            response_public = requests.get(clean_url, headers=headers)
            soup_public = BeautifulSoup(response_public.text, 'html.parser')
            script_tag = soup_public.find('script', type='application/ld+json')
            if script_tag:
                data = json.loads(script_tag.string)
                if isinstance(data, list): data = data[0]
                track_list = data.get('tracks') or data.get('track') or []
                tracks = []
                for t in track_list:
                    name = t.get('name')
                    by_artist = t.get('byArtist')
                    artist_name = by_artist[0].get('name') if isinstance(by_artist, list) else (by_artist.get('name') if isinstance(by_artist, dict) else "")
                    if name and artist_name:
                        tracks.append({"title": name, "artist": artist_name, "query": f"{artist_name} - {name}"})
                return tracks
            return []
        
        raw_data = script_tag.string
        try: decoded_data = urllib.parse.unquote(raw_data)
        except: decoded_data = raw_data
        data = json.loads(decoded_data) if isinstance(decoded_data, str) else json.loads(raw_data)
        tracks = []
        try:
            for section in data[0]['data']['sections']:
                if 'items' in section:
                    for item in section['items']:
                        title = item.get('title')
                        artist = item.get('artistName')
                        if title and artist:
                            tracks.append({"title": title, "artist": artist, "query": f"{artist} - {title}"})
        except: pass
        return tracks
    except Exception as e:
        print(f"Apple Music Error: {e}")
        return []

@app.route('/api/get_tracks', methods=['POST'])
def get_tracks():
    data = request.json
    url = data.get('url')
    if not url: return jsonify({"error": "Missing link"}), 400

    tracks = []
    if "spotify" in url: tracks = scrape_spotify_embed(url)
    elif "deezer.com" in url: tracks = scrape_deezer(url)
    elif "apple.com" in url: tracks = scrape_apple_music(url)
    else: return jsonify({"error": "Service not supported"}), 400
    
    if not tracks: return jsonify({"error": "Unable to read playlist."}), 400
    return jsonify({"tracks": tracks})

@app.route('/api/find_video', methods=['POST'])
def find_video():
    data = request.json
    query = data.get('query')
    
    if query in URL_CACHE:
        return jsonify(URL_CACHE[query])

    try:
        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            info = ydl.extract_info(f"ytsearch1:{query}", download=False)
            
            if 'entries' in info and len(info['entries']) > 0:
                video_info = info['entries'][0]
                
                audio_url = None
                for f in video_info.get('formats', []):
                    if f.get('acodec') != 'none' and f.get('vcodec') == 'none':
                        audio_url = f['url']
                        break
                
                if not audio_url:
                    audio_url = video_info.get('url')

                thumbnail = video_info.get('thumbnail')
                
                proxied_url = f"/stream?url={urllib.parse.quote(audio_url)}"

                result = {
                    "audioUrl": proxied_url,
                    "youtubeUrl": video_info.get('webpage_url'),
                    "title": video_info.get('title', 'Unknown title'),
                    "thumbnail": thumbnail,
                    "duration": video_info.get('duration')
                }
                
                URL_CACHE[query] = result
                return jsonify(result)
                        
        return jsonify({"error": "Not found"}), 404

    except Exception:
        return jsonify({"error": "Extraction error"}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)