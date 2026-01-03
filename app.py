from flask import Flask, render_template, request, jsonify
import yt_dlp
import requests
from bs4 import BeautifulSoup
import json
import re
import urllib.parse

app = Flask(__name__)
app.json.ensure_ascii = False 

YDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'extract_flat': True,
}

@app.route('/')
def index():
    return render_template('index.html')

def scrape_spotify_embed(spotify_url):
    if "open.spotify.com" in spotify_url and "embed" not in spotify_url:
        embed_url = spotify_url.replace("open.spotify.com", "open.spotify.com/embed")
    else:
        embed_url = spotify_url

    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
        response = requests.get(embed_url, headers=headers)
        
        if response.status_code != 200:
            return []

        soup = BeautifulSoup(response.text, 'html.parser')
        script_tag = soup.find('script', id='__NEXT_DATA__')
        
        if not script_tag:
            return []

        data = json.loads(script_tag.string)
        
        try:
            entity = data['props']['pageProps']['state']['data']['entity']
            track_list = entity['trackList']
            
            album_artist = ""
            if 'artists' in entity and len(entity['artists']) > 0:
                album_artist = entity['artists'][0]['name']
                
        except KeyError:
            return []

        cleaned_tracks = []
        for item in track_list:
            try:
                title = item.get('title')
                artist = item.get('subtitle')
                
                if not artist:
                    artist = album_artist

                if artist:
                    artist = artist.replace('\u00a0', ' ')
                
                if title:
                    query = f"{artist} - {title}"
                    cleaned_tracks.append({
                        "title": title,
                        "artist": artist,
                        "query": query
                    })
            except:
                continue
                
        return cleaned_tracks

    except:
        return []

def scrape_deezer(url):
    try:
        object_id = re.search(r'/(playlist|album|track)/(\d+)', url)
        if not object_id:
            return []
        
        type_content = object_id.group(1)
        id_content = object_id.group(2)

        api_url = f"https://api.deezer.com/{type_content}/{id_content}"
        
        response = requests.get(api_url)
        data = response.json()

        tracks = []
        raw_tracks = []
        
        if 'tracks' in data:
            raw_tracks = data['tracks']['data']
        elif 'data' in data:
            raw_tracks = data['data']
        elif type_content == 'track':
            raw_tracks = [data]

        for t in raw_tracks:
            title = t.get('title')
            artist = t.get('artist', {}).get('name')
            if title and artist:
                query = f"{artist} - {title}"
                tracks.append({"title": title, "artist": artist, "query": query})
        
        return tracks
    except:
        return []

def scrape_apple_music(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
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
                    artist_name = ""
                    if isinstance(by_artist, list) and len(by_artist) > 0:
                        artist_name = by_artist[0].get('name')
                    elif isinstance(by_artist, dict):
                        artist_name = by_artist.get('name')
                    
                    if name and artist_name:
                        query = f"{artist_name} - {name}"
                        tracks.append({"title": name, "artist": artist_name, "query": query})
                return tracks
            return []

        raw_data = script_tag.string
        try:
            decoded_data = urllib.parse.unquote(raw_data)
            data = json.loads(decoded_data)
        except:
            data = json.loads(raw_data)

        tracks = []
        
        for section in data[0]['data']['sections']:
            if 'items' in section:
                for item in section['items']:
                    try:
                        title = item.get('title')
                        artist = item.get('artistName')
                        
                        if title and artist:
                            query = f"{artist} - {title}"
                            tracks.append({"title": title, "artist": artist, "query": query})
                    except:
                        continue
                        
        return tracks

    except Exception as e:
        print(f"Apple Music Error: {e}")
        return []

@app.route('/api/get_tracks', methods=['POST'])
def get_tracks():
    data = request.json
    url = data.get('url')
    
    if not url:
        return jsonify({"error": "Missing link"}), 400

    if "spotify.com" in url:
        tracks = scrape_spotify_embed(url)
    elif "deezer.com" in url:
        tracks = scrape_deezer(url)
    elif "apple.com" in url:
        tracks = scrape_apple_music(url)
    else:
        return jsonify({"error": "Service not supported"}), 400
    
    if not tracks:
        return jsonify({"error": "Unable to read playlist."}), 400
        
    return jsonify({"tracks": tracks})

@app.route('/api/find_video', methods=['POST'])
def find_video():
    data = request.json
    query = data.get('query')
    
    try:
        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            info = ydl.extract_info(f"ytsearch1:{query}", download=False)
            
            if 'entries' in info and len(info['entries']) > 0:
                video_id = info['entries'][0]['id']
                
                url_info = ydl.extract_info(video_id, download=False)
                
                thumbnail = url_info.get('thumbnail')
                if not thumbnail and 'thumbnails' in url_info and len(url_info['thumbnails']) > 0:
                     thumbnail = url_info['thumbnails'][-1]['url']
                
                for format in url_info['formats']:
                    if format.get('acodec') != 'none' and format.get('vcodec') == 'none':
                        return jsonify({
                            "audioUrl": format['url'],
                            "title": url_info.get('title', 'Unknown title'),
                            "thumbnail": thumbnail
                        })
                        
        return jsonify({"error": "Not found"}), 404

    except Exception:
        return jsonify({"error": "Extraction error"}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)