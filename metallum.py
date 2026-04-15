#!/usr/bin/env python3
import argparse
import re
import sys
import os
import time
from curl_cffi import requests

# Abhängigkeiten prüfen
try:
    from mutagen.easyid3 import EasyID3
    from mutagen.flac import FLAC
    from mutagen.oggvorbis import OggVorbis
    from mutagen.mp4 import MP4
except ImportError:
    print("\033[0;31mFehler: mutagen nicht gefunden. Bitte installiere es mit: pip install mutagen\033[0m")
    sys.exit(1)

# Globale Konfiguration
base_url = 'https://www.metal-archives.com/'
url_search_songs = 'search/ajax-advanced/searching/songs?'
url_lyrics = 'release/ajax-view-lyrics/id/'
tags_re = re.compile(r'<[^>]+>')

# TLS-Session (Cloudflare Bypass)
session = requests.Session(impersonate="chrome120")

def clean_string(text):
    """Das 'Alcest-Problem' & Klammern: Bereinigt Strings für die Suche"""
    if not text: return ""
    # Hex-Ersetzungen für krumme Apostrophe
    text = text.replace('\u2019', "'").replace('\u0060', "'").replace('\u00b4', "'")
    # Klammern entfernen (optional, wie im Bash-Script)
    search_text = re.sub(r'\([^)]*\)|\[[^]]*\]', '', text).strip()
    return search_text if search_text else text

def get_tags(file_path):
    """Extrahiert Tags aus verschiedenen Formaten"""
    ext = os.path.splitext(file_path)[1].lower()
    try:
        if ext == ".mp3":
            audio = EasyID3(file_path)
            artist = audio.get('artist', [''])[0]
            title = audio.get('title', [''])[0]
        elif ext == ".flac":
            audio = FLAC(file_path)
            artist = audio.get('artist', [''])[0]
            title = audio.get('title', [''])[0]
        elif ext == ".ogg":
            audio = OggVorbis(file_path)
            artist = audio.get('artist', [''])[0]
            title = audio.get('title', [''])[0]
        elif ext in [".m4a", ".mp4"]:
            audio = MP4(file_path)
            # MP4 tags sind oft anders gemappt (\xa9ART, \xa9nam)
            artist = audio.get('\xa9ART', [''])[0]
            title = audio.get('\xa9nam', [''])[0]
        else:
            return None, None
        return artist, title
    except Exception:
        return None, None

def fetch_lyrics_logic(band, song):
    """Kern-Logik: Holt Lyrics von Metallum ohne das Programm zu beenden"""
    try:
        params = {'bandName': band, 'songTitle': song}
        response = session.get(base_url + url_search_songs, params=params, timeout=10)
        
        if response.status_code != 200:
            return None
            
        data = response.json()
        if not data.get('aaData'):
            return None

        # ID extrahieren (Erster Treffer)
        first_row = data['aaData'][0]
        id_match = re.search(r'(\d+)', first_row[4])
        
        if not id_match:
            return None
            
        song_id = id_match.group(1)
        lyrics_res = session.get(base_url + url_lyrics + song_id, timeout=10)
        lyrics = tags_re.sub('', lyrics_res.text).strip()
        
        if not lyrics or "lyrics not available" in lyrics.lower():
            return None
            
        return lyrics
    except Exception:
        return None

def jellyfin_scan(root_path):
    """Scannt Ordner und erstellt Jellyfin .txt Dateien"""
    print(f"\033[0;36mStarte Deep-Scan (Jellyfin Mode)...\033[0m")
    if not os.path.exists(root_path):
        print(f"\033[0;31mPfad nicht gefunden: {root_path}\033[0m")
        return

    valid_exts = (".mp3", ".flac", ".m4a", ".ogg")
    
    for root, _, files in os.walk(root_path):
        for file in files:
            if file.lower().endswith(valid_exts):
                file_path = os.path.join(root, file)
                lyrics_file = os.path.splitext(file_path)[0] + ".txt"
                
                if os.path.exists(lyrics_file):
                    continue
                
                artist, title = get_tags(file_path)
                
                if artist and title:
                    c_artist = clean_string(artist)
                    c_title = clean_string(title)
                    
                    print(f"\033[1;33mSuche: [{artist}] - [{title}]...\033[0m", end=" ", flush=True)
                    
                    lyrics = fetch_lyrics_logic(c_artist, c_title)
                    
                    if lyrics:
                        with open(lyrics_file, "w", encoding="utf-8") as f:
                            f.write(lyrics)
                        print("\033[0;32m[ERFOLG]\033[0m")
                        time.sleep(3) # Sicherheits-Pause gegen Ban
                    else:
                        print("\033[0;31m[KEIN TREFFER]\033[0m")

def main():
    parser = argparse.ArgumentParser(description='Metallum Lyrics Fix for Jellyfin')
    parser.add_argument('band', type=str, nargs='?', help='Name der Band')
    parser.add_argument('song', type=str, nargs='?', help='Name des Songs')
    parser.add_argument('-j', '--jellyfin', type=str, help='Pfad zum Musik-Ordner')

    args = parser.parse_args()

    if args.jellyfin:
        jellyfin_scan(args.jellyfin)
    elif args.band and args.song:
        print(f"Suche: {args.band} - {args.song}...")
        lyrics = fetch_lyrics_logic(args.band, args.song)
        if lyrics:
            print(f"\n\033[1;4m{args.band} - {args.song}\033[0m\n\n{lyrics}\n")
        else:
            print("\033[0;31mKeine Lyrics gefunden.\033[0m")
    else:
        parser.print_help()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\033[0;31mAbgebrochen durch Nutzer.\033[0m")
        sys.exit(0)