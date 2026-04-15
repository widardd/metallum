#!/usr/bin/env python3
import argparse
import re
import sys
import os
import time
from curl_cffi import requests

try:
    from mutagen.easyid3 import EasyID3
    from mutagen.flac import FLAC
    from mutagen.oggvorbis import OggVorbis
    from mutagen.mp4 import MP4
except ImportError:
    print("\033[0;31mFehler: mutagen nicht gefunden. Bitte installiere es mit: pip install mutagen\033[0m")
    sys.exit(1)

base_url = 'https://www.metal-archives.com/'
url_search_songs = 'search/ajax-advanced/searching/songs?'
url_lyrics = 'release/ajax-view-lyrics/id/'
tags_re = re.compile(r'<[^>]+>')

session = requests.Session(impersonate="chrome120")

def clean_string(text):
    if not text: return ""
    text = text.replace('\u2019', "'").replace('\u0060', "'").replace('\u00b4', "'")
    search_text = re.sub(r'\([^)]*\)|\[[^]]*\]', '', text).strip()
    return search_text if search_text else text

def get_tags(file_path):
    ext = os.path.splitext(file_path)[1].lower()
    try:
        if ext == ".mp3":
            audio = EasyID3(file_path)
            return audio.get('artist', [''])[0], audio.get('title', [''])[0]
        elif ext == ".flac":
            audio = FLAC(file_path)
            return audio.get('artist', [''])[0], audio.get('title', [''])[0]
        elif ext == ".ogg":
            audio = OggVorbis(file_path)
            return audio.get('artist', [''])[0], audio.get('title', [''])[0]
        elif ext in [".m4a", ".mp4"]:
            audio = MP4(file_path)
            return audio.get('\xa9ART', [''])[0], audio.get('\xa9nam', [''])[0]
        return None, None
    except:
        return None, None

def fetch_lyrics_logic(band, song):
    try:
        params = {'bandName': band, 'songTitle': song}
        response = session.get(base_url + url_search_songs, params=params, timeout=10)
        if response.status_code != 200: return None
        data = response.json()
        if not data.get('aaData'): return None

        first_row = data['aaData'][0]
        id_match = re.search(r'(\d+)', first_row[4])
        if not id_match: return None
        
        lyrics_res = session.get(base_url + url_lyrics + id_match.group(1), timeout=10)
        lyrics = tags_re.sub('', lyrics_res.text).strip()
        return None if not lyrics or "lyrics not available" in lyrics.lower() else lyrics
    except:
        return None

def jellyfin_scan(root_path, log_callback=None):
    def log(msg, color=""):
        if log_callback: log_callback(msg)
        print(f"{color}{msg}\033[0m")

    valid_exts = (".mp3", ".flac", ".m4a", ".ogg")
    files_to_process = []
    
    for root, _, files in os.walk(root_path):
        for file in files:
            if file.lower().endswith(valid_exts):
                p = os.path.join(root, file)
                if not os.path.exists(os.path.splitext(p)[0] + ".txt"):
                    files_to_process.append(p)

    total = len(files_to_process)
    if total == 0:
        log("Keine neuen Songs zum Verarbeiten gefunden.")
        return

    log(f"Gefundene Songs: {total} | Geschätzte Dauer: ~{int((total*5)/60)} Min.")
    log("-" * 40)

    start_time = time.time()
    for i, file_path in enumerate(files_to_process, 1):
        artist, title = get_tags(file_path)
        if artist and title:
            lyrics = fetch_lyrics_logic(clean_string(artist), clean_string(title))
            
            elapsed = time.time() - start_time
            avg = elapsed / i
            rem = int(avg * (total - i))
            stats = f"[{i}/{total}] (Rest: {rem//60}m {rem%60}s)"

            if lyrics:
                with open(os.path.splitext(file_path)[0] + ".txt", "w", encoding="utf-8") as f:
                    f.write(lyrics)
                log(f"{stats} SUCCESS: {artist} - {title}", "\033[0;32m")
                time.sleep(3)
            else:
                log(f"{stats} FAILED: {artist} - {title}", "\033[0;31m")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('band', nargs='?')
    parser.add_argument('song', nargs='?')
    parser.add_argument('-j', '--jellyfin')
    args = parser.parse_args()
    if args.jellyfin: jellyfin_scan(args.jellyfin)
    elif args.band and args.song:
        l = fetch_lyrics_logic(args.band, args.song)
        print(f"\n{l}\n" if l else "Nichts gefunden.")
    else: parser.print_help()

if __name__ == '__main__':
    main()