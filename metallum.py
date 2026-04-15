#!/usr/bin/env python3

import argparse
import re
import sys
from curl_cffi import requests

base_url = 'https://www.metal-archives.com/'
url_search_songs = 'search/ajax-advanced/searching/songs?'
url_lyrics = 'release/ajax-view-lyrics/id/'
tags_re = re.compile(r'<[^>]+>')

def get_lyrics():
    parser = argparse.ArgumentParser(description='Metallum Lyrics Fix')
    parser.add_argument('band', type=str)
    parser.add_argument('song', type=str)
    args = parser.parse_args()

    # Wir nutzen wieder curl_cffi für das TLS-Fingerprinting
    session = requests.Session(impersonate="chrome120")

    try:
        # 1. Suche ausführen
        params = {'bandName': args.band, 'songTitle': args.song}
        search_response = session.get(base_url + url_search_songs, params=params)
        
        if search_response.status_code == 403:
            sys.exit("Fehler: HTTP 403. Cloudflare blockiert die Anfrage weiterhin.")
            
        data = search_response.json()
        
        if not data.get('aaData'):
            sys.exit("Keine Songs gefunden.")

        # 2. Song ID extrahieren
        # Wir nehmen den ersten Treffer
        first_song_row = data['aaData'][0]
        
        # Das Feld mit der ID ist üblicherweise das letzte (Index 4)
        # Es sieht oft so aus: <a href="..." id="lyricLink_12345">Lyrics</a>
        # Wir suchen einfach nach der ersten längeren Zahl im HTML-String dieses Feldes
        id_field = first_song_row[4]
        id_match = re.search(r'(\d+)', id_field)

        if not id_match:
            # Debug-Hilfe: Falls es scheitert, zeig uns, was im Feld steht
            sys.exit(f"ID konnte im Feld nicht gefunden werden. Inhalt: {id_field}")
            
        song_id = id_match.group(1)

        # 3. Lyrics abrufen
        lyrics_response = session.get(base_url + url_lyrics + song_id)
        
        # Säuberung: HTML-Tags weg, Sonderzeichen fixen
        lyrics = tags_re.sub('', lyrics_response.text).strip()
        
        # Bandname (aus Feld 0) und Songtitel (aus Feld 3) extrahieren
        display_band = tags_re.sub('', first_song_row[0]).strip()
        display_song = first_song_row[3]
        
        print(f"\n\033[1;4m{display_band} - {display_song}\033[0m")
        if not lyrics or lyrics == "(lyrics not available)":
            print("\nLyrics für diesen Song sind leider nicht verfügbar.")
        else:
            print(f"\n{lyrics}\n")

    except Exception as e:
        sys.exit(f"Ein unerwarteter Fehler ist aufgetreten: {e}")

if __name__ == '__main__':
    get_lyrics()
