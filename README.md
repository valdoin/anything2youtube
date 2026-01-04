# anything2youtube

For all my bums who can't afford a premium music service and still want to listen to their annoying friends playlists.

## Overview

This is a local web application that acts as a bridge between streaming platforms and YouTube. It allows you to input a playlist link from Spotify, Apple Music or Deezer, and streams the audio directly from YouTube in a clean, ad-free web player.

## How it Works

The application runs on a lightweight **Flask** backend that retrieves tracklists using different methods depending on the service:

* **Spotify:** It scrapes the public embed page to extract track metadata hidden in the page source, avoiding the need for developer API keys.
* **Apple Music:** It converts embed links to public URLs and scrapes the JSON metadata intended for search engines to retrieve the tracklist.
* **Deezer:** It utilizes Deezer's public API, which is open and allows reading playlist data without authentication.

Once the artist and title are retrieved, the backend uses `yt-dlp` to search for the best matching audio on YouTube and extracts the direct streaming URL. This URL is directly sent to the music player, bypassing YouTube's embedding restrictions.

## Dependencies

This project relies on the following open-source Python libraries:

* [Flask](https://github.com/pallets/flask): For the web server and backend logic.
* [yt-dlp](https://github.com/yt-dlp/yt-dlp): For searching YouTube and extracting raw audio stream URLs.
* [requests](https://github.com/psf/requests): For handling HTTP requests to the streaming platforms.
* [BeautifulSoup4 (bs4)](https://pypi.org/project/beautifulsoup4/): For parsing HTML and extracting data from Spotify and Apple Music pages.

The frontend uses:
* [Plyr](https://plyr.io/): For the audio player interface.
* [Pickr](https://simonwep.github.io/pickr/): For the color customization tool.
* [Plus Jakarta Sans](https://fonts.google.com/specimen/Plus+Jakarta+Sans): Font provided by Google Fonts.

## Usage

1. Install the required packages:
   `pip install -r requirements.txt`

2. Prepare cookies:
    [Follow this guide](https://github.com/yt-dlp/yt-dlp/wiki/extractors)

3. Run the application:
   `python app.py`

4. Open your browser and navigate to the local address (usually `http://127.0.0.1:5000`).