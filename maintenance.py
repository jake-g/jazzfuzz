"""Utility script for Jazz Fuzz website maintenance.

Supports matching albums on YouTube Music, testing YouTube links, benchmarking
poster image load times, and exporting album indexes to TSV format.
"""

import argparse
import concurrent.futures
import csv
import json
import logging
import os
import re
import subprocess
import sys
import time
from typing import Dict, List, Optional, Tuple, Union, Any

from bs4 import BeautifulSoup
import requests

try:
    from fuzzywuzzy import fuzz
except ImportError:
    fuzz = None

try:
    from ytmusicapi import YTMusic
except ImportError:
    YTMusic = None

# Setup logging following Google style
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

HEADER_FILE = "oauth.json"
INDEX_FILE = "index.html"

CLASSIC_JAZZ_ARTISTS = {
    "miles davis",
    "john coltrane",
    "thelonious monk",
    "charles mingus",
    "art blakey",
    "bill evans",
    "sonny rollins",
    "stan getz",
    "ornette coleman",
    "kenny burrell",
    "grant green",
    "herbie hancock",
    "donald byrd",
    "wayne shorter",
    "freddie hubbard",
    "alice coltrane",
    "cannonball adderley",
    "chet baker",
    "louis armstrong",
    "billie holiday",
    "charlie parker",
    "duke ellington",
    "modern jazz quartet",
    "art pepper",
    "dizzy gillespie",
    "django reinhardt",
    "eric dolphy",
    "horace silver",
    "jackie mclean",
    "sun ra",
    "wynton kelly",
}


def extract_year(released_str: str) -> Optional[int]:
    """Extracts the year from a release date string.

    Args:
        released_str: The release date string (e.g., 'June, 2018', '1966').

    Returns:
        The year as an integer, or None if it cannot be parsed.
    """
    match = re.search(r",?\s*(\d{4})", released_str)
    if match:
        return int(match.group(1))
    return None


def get_album_id(artist: str, title: str, year: Optional[int] = None) -> str:
    """Creates an album ID string in the format "artist - title".

    Args:
        artist: The artist's name.
        title: The title of the album or track.
        year: The year of release (optional).

    Returns:
        The fuzzy ID string.
    """
    album_id = f"{artist} - {title}"
    if year:
        album_id += f" [{year}]"
    return album_id


def extract_album_entries_from_html(html_file: str) -> Dict[str, Dict]:
    """Extracts album data from an HTML file.

    Args:
        html_file: The path to the HTML file.

    Returns:
        A dictionary containing album data, with album IDs as keys.
    """
    albums = {}
    if not os.path.exists(html_file):
        logger.error("HTML file not found: %s", html_file)
        return albums

    with open(html_file, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")
        for i, article in enumerate(soup.find_all("article")):
            header = article.find("header")
            if not header or not header.find("h2"):
                continue

            album_data = {"index": i, "title": header.find("h2").text.strip()}

            for h3 in header.find_all("h3"):
                if ":" in h3.text:
                    key, val = h3.text.split(": ", 1)
                    album_data[key.lower()] = val.strip()

            player_div = article.find("div", class_="playerContainer")
            lite_yt = player_div.find("lite-youtube") if player_div else None
            if lite_yt:
                album_data["playlist_id"] = lite_yt.get("playlistid", "")
                album_data["video_id"] = lite_yt.get("videoid", "")
                album_data["poster_quality"] = lite_yt.get("posterquality", "")

            album_data["popularity"] = article.get("data-popularity", "")
            album_data["artist"] = album_data.pop(
                "by", album_data.get("artist", "Unknown Artist")
            )
            released = album_data.get("released", "")
            album_data["year"] = extract_year(released) if released else None
            ol = article.find("ol")
            album_data["track_count"] = len(ol.find_all("li")) if ol else 0

            album_key = get_album_id(album_data["artist"], album_data["title"])
            albums[album_key] = album_data

    return albums


def get_youtube_album(
    yt: YTMusic,
    artist: str,
    title: str,
    year: Optional[int] = None,
    year_err_thresh: int = 3,
    match_score_thresh: int = 90,
    match_score_perfect_thresh: int = 98,
) -> Optional[Dict[str, Union[str, int]]]:
    """Searches YouTube Music for albums and finds the best match.

    Args:
        yt: The YouTube Music API client.
        artist: Album artist.
        title: Album title.
        year: Album release year, if known.
        year_err_thresh: Max allowable difference in release year.
        match_score_thresh: Min fuzzy matching score required.
        match_score_perfect_thresh: Score threshold to consider perfect match.

    Returns:
        A dictionary with matching YouTube Music album details, or None.
    """
    query = get_album_id(artist, title)
    logger.info("Searching YouTube Music for: %s", query)

    try:
        results = yt.search(query, filter="albums")
    except Exception as e:  # pylint: disable=broad-except
        logger.error("Search failed: %s", e)
        return None

    for res in results:
        res_id = res.get("browseId", "")
        if not res.get("year"):
            logger.debug("Skipping result without year: %s", res.get("title"))
            continue

        best_match_score = 0
        matched_artist = res["artists"][0]["name"]
        for artist_dict in res.get("artists", []):
            a_name = artist_dict.get("name", "")
            score = fuzz.token_set_ratio(get_album_id(a_name, res["title"]), query)
            if score > best_match_score:
                best_match_score = score
                matched_artist = a_name

        res["artist"] = matched_artist
        res["match_fuzzy_score"] = best_match_score
        match_score = best_match_score

        if match_score < match_score_thresh:
            logger.debug(
                "Skipping score %d below thresh %d: %s",
                match_score,
                match_score_thresh,
                res_id,
            )
            continue

        if year:
            try:
                res_year = int(res["year"])
                year_err = abs(res_year - year)
                res["match_year_diff"] = year_err
                if year_err > year_err_thresh and match_score < (
                    match_score_perfect_thresh
                ):
                    logger.debug("Skipping year diff %d: %s", year_err, res_id)
                    continue
            except ValueError:
                logger.debug("Could not parse year: %s", res["year"])
                continue

        try:
            details = yt.get_album(res["browseId"])
            res.update(details)
            if res.get("tracks"):
                res["firstVideoId"] = res["tracks"][0]["videoId"]
            res.pop("thumbnails", None)
            return res
        except Exception as e:  # pylint: disable=broad-except
            logger.error("Failed fetching album details: %s", e)
            continue

    return None


def validate_single_link(item_type: str, item_id: str) -> Tuple[str, str, bool]:
    """Validates a single YouTube video or playlist ID using OEmbed.

    Args:
        item_type: Either 'video' or 'playlist'.
        item_id: The ID of the item.

    Returns:
        A tuple of (item_type, item_id, is_valid).
    """
    if not item_id:
        return item_type, item_id, False

    if item_type == "video":
        url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={item_id}"
    else:
        url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/playlist?list={item_id}"

    try:
        r = requests.head(url, timeout=5)
        # OEmbed returns 200 or 400/404
        return item_type, item_id, r.status_code == 200
    except requests.RequestException:
        return item_type, item_id, False


def test_youtube_links(html_file: str) -> bool:
    """Scans HTML for YouTube video and playlist IDs, validates them, and offers suggestions for broken links.

    Args:
        html_file: Path to index.html.

    Returns:
        True if all links are valid, False if there are any broken links.
    """
    albums = extract_album_entries_from_html(html_file)
    logger.info("Verifying links for %d albums...", len(albums))

    tasks = []
    for album_key, info in albums.items():
        video_id = info.get("video_id")
        playlist_id = info.get("playlist_id")
        if video_id:
            tasks.append(("video", video_id, album_key))
        if playlist_id:
            tasks.append(("playlist", playlist_id, album_key))

    valid_count = 0
    broken_count = 0
    broken_items = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = {
            executor.submit(validate_single_link, t[0], t[1]): (t[2], t[0], t[1])
            for t in tasks
        }
        for future in concurrent.futures.as_completed(futures):
            album_name, item_type, item_id = futures[future]
            try:
                _, _, is_valid = future.result()
                if is_valid:
                    valid_count += 1
                else:
                    broken_count += 1
                    broken_items.append((album_name, item_type, item_id))
                    logger.error(
                        "Broken link in %s: %s ID '%s' is invalid (404/OEmbed error)",
                        album_name,
                        item_type,
                        item_id,
                    )
            except Exception as e:  # pylint: disable=broad-except
                broken_count += 1
                broken_items.append((album_name, item_type, item_id))
                logger.error("Failed checking %s ID %s: %s", item_type, item_id, e)

    logger.info(
        "Link validation finished. Valid: %d, Broken: %d", valid_count, broken_count
    )

    if broken_count > 0:
        print("\n🔍 Researching alternative working IDs for broken links...")
        try:
            yt = YTMusic()
        except Exception:
            yt = None

        fixes_suggested = []
        for album_name, item_type, item_id in broken_items:
            parts = album_name.split(" - ", 1)
            artist = parts[0]
            title = parts[1] if len(parts) == 2 else album_name

            if yt:
                logger.info("Searching YTMusic for: %s - %s...", artist, title)
                match = get_youtube_album(yt, artist, title)
                if match:
                    alt_playlist = match.get("playlistId")
                    alt_video = match.get("firstVideoId")

                    if item_type == "playlist" and alt_playlist and alt_playlist != item_id:
                        fixes_suggested.append({
                            "album": album_name,
                            "type": "playlist",
                            "old": item_id,
                            "new": alt_playlist
                        })
                        print(f"💡 Suggestion for '{album_name}': Replace broken playlist ID '{item_id}' with '{alt_playlist}'")
                    elif item_type == "video" and alt_video and alt_video != item_id:
                        fixes_suggested.append({
                            "album": album_name,
                            "type": "video",
                            "old": item_id,
                            "new": alt_video
                        })
                        print(f"💡 Suggestion for '{album_name}': Replace broken video ID '{item_id}' with '{alt_video}'")

        if fixes_suggested:
            apply_fixes = input(f"\nWould you like to automatically apply these {len(fixes_suggested)} fixes to index.html? [Y/n]: ").strip().lower()
            if apply_fixes != "n":
                with open(html_file, "r", encoding="utf-8") as f:
                    html_content = f.read()

                for fix in fixes_suggested:
                    old_str = fix["old"]
                    new_str = fix["new"]
                    if fix["type"] == "video":
                        html_content = html_content.replace(f'videoid="{old_str}"', f'videoid="{new_str}"')
                    else:
                        html_content = html_content.replace(f'playlistid="{old_str}"', f'playlistid="{new_str}"')

                with open(html_file, "w", encoding="utf-8") as f:
                    f.write(html_content)
                logger.info("Successfully applied fixes to index.html!")
                # Re-export glossary
                export_tsv_glossary(html_file, "albums_glossary.tsv")

    return broken_count == 0


def fetch_image_size(url: str) -> Tuple[str, int, float]:
    """Fetches an image URL and returns its size and download time.

    Args:
        url: The image URL to fetch.

    Returns:
        A tuple of (url, size_bytes, download_time_seconds).
    """
    start = time.time()
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            return url, len(r.content), time.time() - start
    except requests.RequestException:
        pass
    return url, 0, time.time() - start


def run_benchmark(html_file: str) -> None:
    """Benchmarks page load speeds of poster images for maxres vs hq quality.

    Args:
        html_file: Path to index.html.
    """
    albums = extract_album_entries_from_html(html_file)
    video_ids = [info["video_id"] for info in albums.values() if info.get("video_id")]

    if not video_ids:
        logger.warning("No video IDs found to benchmark.")
        return

    logger.info("Benchmarking image loading times for %d posters...", len(video_ids))

    maxres_urls = [
        f"https://i.ytimg.com/vi/{vid}/maxresdefault.jpg" for vid in video_ids
    ]
    hq_urls = [f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg" for vid in video_ids]

    # Measure maxresdefault quality
    logger.info("Fetching maxresdefault posters...")
    maxres_sizes = []
    maxres_times = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(fetch_image_size, maxres_urls))
        for _, size, elapsed in results:
            if size > 0:
                maxres_sizes.append(size)
                maxres_times.append(elapsed)

    # Measure hqdefault quality
    logger.info("Fetching hqdefault posters...")
    hq_sizes = []
    hq_times = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(fetch_image_size, hq_urls))
        for _, size, elapsed in results:
            if size > 0:
                hq_sizes.append(size)
                hq_times.append(elapsed)

    def format_bytes(b: int) -> str:
        return f"{b / (1024 * 1024):.2f} MB"

    print("\n=========================================================")
    print("📊 Poster Image Quality Benchmarks")
    print("=========================================================")
    print(f"Total Videos Benchmarked: {len(video_ids)}")
    print("\nQuality: maxresdefault (1280x720)")
    print(f"  Total Download Size:  {format_bytes(sum(maxres_sizes))}")
    print(
        f"  Avg Image Size:       {sum(maxres_sizes) / len(maxres_sizes) / 1024:.1f} KB"
    )
    print(
        f"  Avg Fetch Time:       {sum(maxres_times) / len(maxres_times):.3f} seconds"
    )

    print("\nQuality: hqdefault (480x360)")
    print(f"  Total Download Size:  {format_bytes(sum(hq_sizes))}")
    print(f"  Avg Image Size:       {sum(hq_sizes) / len(hq_sizes) / 1024:.1f} KB")
    print(f"  Avg Fetch Time:       {sum(hq_times) / len(hq_times):.3f} seconds")
    print("=========================================================")

    size_diff = sum(maxres_sizes) - sum(hq_sizes)
    print(
        f"\n💡 Conclusion: Using maxresdefault adds {format_bytes(size_diff)} of payload weight."
    )
    if size_diff > 0:
        speedup = sum(maxres_sizes) / sum(hq_sizes)
        print(f"   hqdefault is approx {speedup:.1f}x lighter to load.")
    print("=========================================================")


def export_tsv_glossary(html_file: str, tsv_file: str) -> None:
    """Parses HTML and exports an index glossary of all albums to a TSV file.

    Args:
        html_file: Path to index.html.
        tsv_file: Path to output tsv file.
    """
    albums = extract_album_entries_from_html(html_file)
    if not albums:
        logger.error("No albums extracted from HTML.")
        return

    logger.info("Exporting %d albums to TSV glossary '%s'...", len(albums), tsv_file)

    fieldnames = [
        "Artist",
        "Album",
        "Released",
        "Genre",
        "Tracks",
        "YouTube Music URL",
    ]

    with open(tsv_file, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        for info in albums.values():
            playlist_id = info.get("playlist_id", "")
            yt_url = (
                f"https://music.youtube.com/playlist?list={playlist_id}"
                if playlist_id
                else ""
            )
            writer.writerow(
                {
                    "Artist": info.get("artist", ""),
                    "Album": info.get("title", ""),
                    "Released": info.get("released", ""),
                    "Genre": info.get("genre", ""),
                    "Tracks": info.get("track_count", 0),
                    "YouTube Music URL": yt_url,
                }
            )

    logger.info("Glossary file exported successfully.")


def load_musicbee_tracks(filepath: str) -> List[Dict]:
    """Loads and parses tracks from a MusicBee TSV export.

    Args:
        filepath: Path to the TSV file.

    Returns:
        A list of parsed track dictionaries.
    """
    tracks = []
    if not os.path.exists(filepath):
        logger.warning("MusicBee file not found: %s", filepath)
        return tracks

    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            rating_str = row.get("Rating", "0")
            try:
                rating = float(rating_str) if rating_str else 0.0
            except ValueError:
                rating = 0.0

            tracks.append(
                {
                    "artist": row.get("Artist", "").strip(),
                    "album": row.get("Album", "").strip(),
                    "rating": rating,
                }
            )
    return tracks


def research_todos(todo_file: str, library_file: str, inbox_file: str) -> None:
    """Researches todo albums against MusicBee ratings and popularity.

    Args:
        todo_file: Path to albums_todo.tsv.
        library_file: Path to musicbee_library.tsv.
        inbox_file: Path to musicbee_inbox.tsv.
    """
    logger.info("Loading MusicBee database tracks...")
    all_tracks = load_musicbee_tracks(library_file) + load_musicbee_tracks(
        inbox_file
    )
    logger.info("Loaded %d tracks total.", len(all_tracks))

    if not os.path.exists(todo_file):
        logger.error("Todo TSV file not found: %s", todo_file)
        return

    try:
        yt = YTMusic()
    except Exception:
        yt = None

    # Extract popularity from existing html index
    existing_albums = extract_album_entries_from_html(INDEX_FILE)
    popularity_by_album = {}
    for info in existing_albums.values():
        key = f"{info['artist']} - {info['title']}"
        if info.get("popularity"):
            popularity_by_album[key] = info["popularity"]

    # Read current todos
    todos = []
    with open(todo_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            if row.get("Album") and row.get("Artist"):
                todos.append(row)

    evaluated_todos = []
    for item in todos:
        artist_name = item["Artist"].strip()
        album_name = item["Album"].strip()

        artist_ratings = []
        album_ratings = []

        # Match in database
        for track in all_tracks:
            track_artist = track["artist"].lower()
            target_artist = artist_name.lower()

            # Check artist match
            if target_artist in track_artist or track_artist in target_artist:
                if track["rating"] > 0:
                    artist_ratings.append(track["rating"])

                # Check album match
                track_album = track["album"].lower()
                target_album = album_name.lower()
                if target_album in track_album or track_album in target_album:
                    if track["rating"] > 0:
                        album_ratings.append(track["rating"])

        # Calculate averages
        my_rating = (
            str(round(sum(album_ratings) / len(album_ratings), 2))
            if album_ratings
            else ""
        )
        artist_avg = (
            str(round(sum(artist_ratings) / len(artist_ratings), 2))
            if artist_ratings
            else ""
        )

        key = f"{artist_name} - {album_name}"
        # Check if Popularity is already set in the item, otherwise check index.html
        popularity = item.get("Popularity", "").strip()
        if not popularity:
            popularity = str(popularity_by_album.get(key, "50"))

        # Fetch original release year if not present
        year = item.get("Year", "").strip()
        if not year and yt:
            try:
                match = get_youtube_album(yt, artist_name, album_name)
                if match and match.get("year"):
                    year = str(match["year"])
            except Exception:
                pass

        # Update row dictionary
        item.update(
            {
                "Year": year,
                "Popularity": popularity,
                "My Rating": my_rating,
                "Artist Avg Rating": artist_avg,
            }
        )
        evaluated_todos.append(item)

    def parse_pop_sort(row):
        try:
            return float(row.get("Popularity") or 0)
        except ValueError:
            return 0.0

    def parse_year_sort(row):
        y_str = row.get("Year") or row.get("Released") or ""
        match = re.search(r"\d{4}", y_str)
        return int(match.group(0)) if match else 0

    # Sort: popularity descending, then year descending (default sorting)
    evaluated_todos.sort(key=lambda x: (-parse_pop_sort(x), -parse_year_sort(x)))

    if not evaluated_todos:
        logger.warning("No todo entries found to write.")
        return

    # Determine fieldnames (preserve any extra fields)
    fieldnames = [
        "Album",
        "Artist",
        "Year",
        "Popularity",
        "My Rating",
        "Artist Avg Rating",
    ]
    for key in evaluated_todos[0].keys():
        if key not in fieldnames:
            fieldnames.append(key)

    with open(todo_file, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        for entry in evaluated_todos:
            writer.writerow(entry)

    logger.info("Todo TSV updated with ratings and popularity successfully.")


def fetch_album_metadata_from_llm(artist: str, album: str) -> Dict[str, Any]:
    """Uses agentapi to lookup original release year, genres, and popularity score.

    Args:
        artist: Album artist.
        album: Album title.

    Returns:
        Dict mapping metadata fields (popularity, original_year, genres).
    """
    prompt = f"""You are a music metadata expert. For the following album, look up and return:
1. The original release/recording year (e.g. 1959 for Ornette Coleman's "The Shape of Jazz to Come").
2. A list of 1 to 3 curated genres (comma-separated, e.g. "Free Jazz, Avant-Garde Jazz").
3. A global popularity/acclaim score from 1 to 100 (where 100 is maximum acclaim/masterpiece, based on RateYourMusic and BestEverAlbums).

Artist: {artist}
Album: {album}

Return the result STRICTLY as a JSON object with these keys:
"popularity" (integer), "original_year" (integer), "genres" (string).
Do not include markdown formatting or any wrapper text. Just the JSON object.
"""
    logger.info(
        "Querying LLM via agentapi for metadata of '%s - %s'...", artist, album
    )
    try:
        res = subprocess.run(
            ["agentapi", "new-conversation", "--model=flash", prompt],
            capture_output=True,
            text=True,
            timeout=20,
        )
        if res.returncode == 0:
            output = res.stdout.strip()
            start = output.find("{")
            end = output.rfind("}") + 1
            if start != -1 and end > start:
                data = json.loads(output[start:end])
                logger.info("Retrieved LLM metadata: %s", data)
                return data
    except Exception as e:
        logger.warning("Failed to fetch LLM metadata: %s", e)

    return {}


def promote_album_to_html(
    artist: str, title: str, popularity: str, details: Dict
) -> None:
    """Formats and inserts a promoted album into index.html chronologically.

    Args:
        artist: Album artist.
        title: Album title.
        popularity: Popularity score (1-100).
        details: Dictionary containing YouTube Music metadata (tracks, year,
          etc).
    """
    logger.info("Promoting '%s - %s' to index.html...", artist, title)

    if not os.path.exists(INDEX_FILE):
        logger.error("index.html not found: %s", INDEX_FILE)
        return

    # Dynamic original recording year & genres lookup via LLM knowledge
    llm_meta = fetch_album_metadata_from_llm(artist, title)
    if llm_meta:
        popularity = str(llm_meta.get("popularity", popularity))
        year = (
            str(llm_meta.get("original_year"))
            if llm_meta.get("original_year")
            else details.get("year", "Unknown")
        )
        genre = (
            llm_meta.get("genres")
            if llm_meta.get("genres")
            else details.get("genre", "Jazz")
        )
    else:
        year = details.get("year", "Unknown")
        genre = details.get("genre", "Jazz")

    playlist_id = details.get("playlistId", "")
    video_id = details.get("firstVideoId", "")

    # Generate tracklist HTML
    tracklist_items = []
    for track in details.get("tracks", []):
        t_title = track.get("title", "")
        sec = track.get("duration_seconds")
        if sec:
            m = sec // 60
            s = sec % 60
            dur_str = f"{m}:{s:02d}"
        else:
            dur_str = track.get("duration", "")
        tracklist_items.append(f"          <li>{t_title} ({dur_str})</li>")

    track_list_html = "\n".join(tracklist_items)

    # Build the exact article HTML block matching our layout
    article_block = f"""    <article data-popularity="{popularity}">
      <header>
        <h2>{title}</h2>
        <h3>By: {artist}</h3>
        <h3>Released: {year}</h3>
        <h3>Genre: {genre}</h3>
      </header>
      <div class="playerContainer">
        <lite-youtube params="rel=0&amp;modestbranding=1&amp;enablejsapi=1&amp;autoplay=0"
          videoid="{video_id}"
          playlistid="{playlist_id}"
          posterquality="maxresdefault"
        ></lite-youtube>
      </div>
      <button class="toggle-details-btn">Collapse</button>
      <main>
        <h3>Musicians:</h3>
        <ul>
          <li>(Add musicians manually)</li>
        </ul>
        <h3>Production Credits:</h3>
        <ul>
          <li>(Add production credits manually)</li>
        </ul>
        <h3>Track List:</h3>
        <ol>
{track_list_html}
        </ol>
      </main>
    </article>
"""

    with open(INDEX_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    # Find the positions and release years of all existing articles
    articles = list(re.finditer(r"<article[^>]*>", content))

    insert_pos = None
    new_year = extract_year(year) or 0

    for idx, match in enumerate(articles):
        start_idx = match.start()
        # Find boundaries of this article section
        end_idx = (
            articles[idx + 1].start()
            if idx + 1 < len(articles)
            else content.find("</section>", start_idx)
        )
        sub_content = content[start_idx:end_idx]

        # Extract released year
        rel_match = re.search(r"<h3>Released:\s*([^<]+)</h3>", sub_content)
        ex_year = 0
        if rel_match:
            ex_year = extract_year(rel_match.group(1)) or 0

        if new_year >= ex_year:
            insert_pos = start_idx
            break

    if insert_pos is None:
        # Fallback to appending right before closing tag of section #posts
        sec_match = re.search(r"</section>", content)
        if sec_match:
            insert_pos = sec_match.start()
        else:
            insert_pos = len(content)

    new_content = (
        content[:insert_pos] + article_block + "\n" + content[insert_pos:]
    )

    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        f.write(new_content)

    logger.info("Successfully promoted '%s' to index.html.", title)


def todo_wizard(todo_file: str) -> None:
    """Runs the interactive todo wizard to evaluate and promote albums.

    Args:
        todo_file: Path to albums_todo.tsv.
    """
    print("=========================================================")
    print("🔍 Sync Ratings & Popularity")
    print("=========================================================")
    run_research = (
        input("Would you like to run 'research-todos' first to sync the latest ratings? [Y/n]: ")
        .strip()
        .lower()
    )
    if run_research != "n":
        lib_path = "../music-library/music-sources-unified/db_assets/musicbee_library.tsv"
        inbox_path = "../music-library/music-sources-unified/db_assets/musicbee_inbox.tsv"
        print("Running research-todos...")
        research_todos(todo_file, lib_path, inbox_path)
        print("Done researching. Proceeding to wizard.\n")

    if not os.path.exists(todo_file):
        logger.error("Todo TSV file not found: %s", todo_file)
        return

    # Read current todos
    todos = []
    with open(todo_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            if row.get("Album") and row.get("Artist"):
                # Initialize skip_count and last_action if missing
                if "skip_count" not in row:
                    row["skip_count"] = "0"
                if "last_action" not in row:
                    row["last_action"] = ""
                todos.append(row)

    if not todos:
        logger.info("No todo items available.")
        return

    # Helper function to calculate Combined Score
    def get_combined_score(item: Dict) -> float:
        try:
            pop = float(item.get("Popularity") or 50)
        except ValueError:
            pop = 50
        try:
            rating = float(item.get("My Rating") or 0)
        except ValueError:
            rating = 0
        try:
            artist_avg = float(item.get("Artist Avg Rating") or 0)
        except ValueError:
            artist_avg = 0

        score_rating = rating if rating > 0 else artist_avg
        return 0.7 * pop + 0.3 * (score_rating * 20)

    # Sort todos by Combined Score descending
    todos.sort(key=get_combined_score, reverse=True)

    # Initialize YouTube Music client
    try:
        yt = YTMusic(HEADER_FILE) if os.path.exists(HEADER_FILE) else YTMusic()
    except Exception:
        logger.info("Initializing YTMusic in unauthenticated mode.")
        yt = YTMusic()

    logger.info("Starting Todo evaluation wizard...")
    logger.info("Press Q at any prompt to save and quit.\n")

    remaining_todos = list(todos)

    for i, item in enumerate(todos):
        album = item["Album"]
        artist = item["Artist"]
        popularity = item.get("Popularity", "50")
        my_rating = item.get("My Rating")
        artist_avg = item.get("Artist Avg Rating")
        skip_count = int(item.get("skip_count", "0"))
        last_action = item.get("last_action", "")

        score = get_combined_score(item)

        print("=========================================================")
        print(f"💿 Album: {album}")
        print(f"👤 Artist: {artist}")
        print("=========================================================")
        print(f"  Combined Score:     {score:.1f}")
        print(f"  Popularity Score:   {popularity}/100")
        my_rating_str = "N/A"
        if my_rating:
            try:
                val = float(my_rating)
                my_rating_str = f"{val:.2f}/5.0 ({val * 20:.0f}/100)"
            except ValueError:
                pass

        artist_avg_str = "N/A"
        if artist_avg:
            try:
                val = float(artist_avg)
                artist_avg_str = f"{val:.2f}/5.0 ({val * 20:.0f}/100)"
            except ValueError:
                pass

        print(f"  Library Rating:     {my_rating_str}")
        print(f"  Artist Avg Rating:  {artist_avg_str}")
        print(f"  Skip Count:         {skip_count}")
        print(f"  Last Action:        {last_action or 'None'}")
        print("=========================================================")

        # Offer permanent deletion if skipped too many times
        if skip_count >= 3:
            print(
                "⚠️  Notice: This album has been skipped 3+ times."
            )
            remove_prompt = input(
                "Would you like to delete it from todo permanently? [y/N]: "
            ).strip().lower()
            if remove_prompt == "y":
                remaining_todos.remove(item)
                save_wizard_state(todo_file, remaining_todos)
                print("Album deleted from todo permanently.\n")
                continue

        choice = (
            input("Select Action - [P]romote, [S]kip, [D]elete, [Q]uit: ")
            .strip()
            .lower()
        )

        if choice == "p":
            print(f"\nSearching YouTube Music for: {artist} - {album}...")
            match = get_youtube_album(yt, artist, album)
            if match:
                matched_title = match.get("title")
                matched_artist = match["artists"][0]["name"]
                matched_year = match.get("year", "Unknown")
                print(
                    f"Match found: '{matched_title}' by {matched_artist} ({matched_year})"
                )

                # Heuristic warning for classic reissue years
                is_classic = any(c in artist.lower() for c in CLASSIC_JAZZ_ARTISTS)
                try:
                    yr_val = int(matched_year) if matched_year != "Unknown" else 0
                except ValueError:
                    yr_val = 0

                if is_classic and yr_val > 1990:
                    print(f"\n⚠️  WARNING: Matched year '{matched_year}' seems to be a reissue/remaster year for classic artist '{artist}'.")
                    user_yr = input(f"Please enter the original release year (or press Enter to keep '{matched_year}'): ").strip()
                    if user_yr:
                        match["year"] = user_yr
                        matched_year = user_yr
                        item["Year"] = user_yr

                album_id = match.get("browseId")
                if album_id:
                    print(f"Listen:      https://music.youtube.com/browse/{album_id}")
                confirm = (
                    input("Proceed with promoting this match? [Y/n]: ")
                    .strip()
                    .lower()
                )
                if confirm != "n":
                    promote_album_to_html(artist, album, popularity, match)
                    remaining_todos.remove(item)
                    save_wizard_state(todo_file, remaining_todos)
                    # Automatically update glossary
                    export_tsv_glossary(INDEX_FILE, "albums_glossary.tsv")
                    print("Album successfully promoted to site!\n")
                else:
                    print("Promotion cancelled. Kept in todo.\n")
            else:
                print("No matching album details found on YouTube Music.\n")

        elif choice == "s":
            item["skip_count"] = str(skip_count + 1)
            item["last_action"] = "skipped"
            save_wizard_state(todo_file, remaining_todos)
            print("Album skipped.\n")

        elif choice == "d":
            remaining_todos.remove(item)
            save_wizard_state(todo_file, remaining_todos)
            print("Album deleted from todo.\n")

        elif choice == "q":
            print("Exiting wizard.")
            break
        else:
            print("Invalid option. Skipping for now.\n")

    print("Wizard session finished.")


def save_wizard_state(todo_file: str, todos: List[Dict]) -> None:
    """Helper to save the current wizard state back to TSV file.

    Args:
        todo_file: Path to todo TSV.
        todos: List of remaining todo items.
    """
    fieldnames = [
        "Album",
        "Artist",
        "Popularity",
        "My Rating",
        "Artist Avg Rating",
        "skip_count",
        "last_action",
    ]
    # Add any extra columns dynamically
    if todos:
        for key in todos[0].keys():
            if key not in fieldnames:
                fieldnames.append(key)

    with open(todo_file, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        for entry in todos:
            writer.writerow(entry)


def sort_tsv_file(filepath: str, sort_by: str) -> None:
    """Sorts a TSV file (glossary or todo list) by specified criteria.

    Args:
        filepath: Path to the TSV file.
        sort_by: Sort option ('newest', 'oldest', 'popular', 'default').
    """
    if not os.path.exists(filepath):
        logger.error("TSV file not found: %s", filepath)
        return

    rows = []
    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        fieldnames = reader.fieldnames
        for row in reader:
            rows.append(row)

    if not rows:
        return

    def parse_pop(row):
        try:
            return float(row.get("Popularity") or 0)
        except ValueError:
            return 0.0

    def parse_year(row):
        y_str = row.get("Year") or row.get("Released") or ""
        match = re.search(r"\d{4}", y_str)
        return int(match.group(0)) if match else 0

    if sort_by == "newest":
        rows.sort(key=lambda x: (-parse_year(x), -parse_pop(x)))
    elif sort_by == "oldest":
        rows.sort(key=lambda x: (parse_year(x), -parse_pop(x)))
    elif sort_by == "popular":
        rows.sort(key=lambda x: (-parse_pop(x), -parse_year(x)))
    elif sort_by == "default":
        rows.sort(key=lambda x: (-parse_pop(x), -parse_year(x)))

    # Ensure fieldnames has Year if it is populated
    if rows[0].get("Year") and "Year" not in fieldnames:
        # Insert Year right after Album & Artist
        if "Artist" in fieldnames:
            idx = fieldnames.index("Artist") + 1
            fieldnames.insert(idx, "Year")
        else:
            fieldnames.append("Year")

    with open(filepath, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

    logger.info("TSV file '%s' successfully sorted by '%s'.", filepath, sort_by)


def validate_catalog_years(html_file: str) -> bool:
    """Validates that no classic jazz artist in index.html has a reissue/remaster year (>1990).

    Args:
        html_file: Path to the HTML catalog file.

    Returns:
        True if all years are valid, False otherwise.
    """
    logger.info("Validating release years in %s...", html_file)
    albums = extract_album_entries_from_html(html_file)
    invalid_entries = 0
    for key, info in albums.items():
        artist = info["artist"]
        year = info["year"]

        is_classic = any(c in artist.lower() for c in CLASSIC_JAZZ_ARTISTS)
        if is_classic and year > 1990:
            logger.warning(
                "❌ INVALID YEAR: '%s' has year %d which looks like a reissue/remaster for classic artist.",
                key,
                year,
            )
            invalid_entries += 1

    if invalid_entries > 0:
        logger.error("Year validation failed with %d anomalies.", invalid_entries)
        return False
    logger.info("Year validation passed successfully!")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Jazz Fuzz maintenance and matching helper."
    )
    subparsers = parser.add_subparsers(dest="command", help="Subcommand to run")

    # match subcommand
    match_parser = subparsers.add_parser("match", help="Match albums on YouTube Music")
    match_parser.add_argument(
        "--search", type=str, help="Query search string in format 'Artist - Title'"
    )
    match_parser.add_argument(
        "--html", type=str, default=INDEX_FILE, help="HTML file to parse & match"
    )

    # test-links subcommand
    test_parser = subparsers.add_parser(
        "test-links", help="Validate all YouTube links in index.html"
    )
    test_parser.add_argument(
        "--html", type=str, default=INDEX_FILE, help="HTML file to parse & test"
    )

    # benchmark subcommand
    bench_parser = subparsers.add_parser(
        "benchmark", help="Benchmark poster quality loading times"
    )
    bench_parser.add_argument(
        "--html", type=str, default=INDEX_FILE, help="HTML file to parse & bench"
    )

    # export-tsv subcommand
    export_parser = subparsers.add_parser(
        "export-tsv", help="Export index.html content to TSV glossary"
    )
    export_parser.add_argument(
        "--html", type=str, default=INDEX_FILE, help="HTML file to parse & export"
    )
    export_parser.add_argument(
        "--tsv", type=str, default="albums_glossary.tsv", help="TSV output file"
    )

    # research-todos subcommand
    eval_parser = subparsers.add_parser(
        "research-todos",
        help="Research todo albums against MusicBee ratings and popularity",
    )
    eval_parser.add_argument(
        "--todo", type=str, default="albums_todo.tsv", help="Path to todo TSV file"
    )
    eval_parser.add_argument(
        "--library",
        type=str,
        default="../music-library/music-sources-unified/db_assets/musicbee_library.tsv",
        help="Path to MusicBee library TSV",
    )
    eval_parser.add_argument(
        "--inbox",
        type=str,
        default="../music-library/music-sources-unified/db_assets/musicbee_inbox.tsv",
        help="Path to MusicBee inbox TSV",
    )

    # todo-wizard subcommand
    wizard_parser = subparsers.add_parser(
        "todo-wizard",
        help="Interactive CLI wizard to step through and evaluate todo albums",
    )
    wizard_parser.add_argument(
        "--todo", type=str, default="albums_todo.tsv", help="Path to todo TSV file"
    )

    # import-album subcommand
    import_parser = subparsers.add_parser(
        "import-album",
        help="Search and import a specific album directly into catalog index.html",
    )
    import_parser.add_argument(
        "--artist", type=str, required=True, help="Album artist name"
    )
    import_parser.add_argument(
        "--album", type=str, required=True, help="Album title"
    )
    import_parser.add_argument(
        "--popularity",
        type=str,
        default="50",
        help="Album popularity score (1-100, default: 50)",
    )

    # sort-tsv subcommand
    sort_parser = subparsers.add_parser(
        "sort-tsv", help="Sort a TSV file by specific columns"
    )
    sort_parser.add_argument(
        "--file", type=str, required=True, help="TSV file to sort"
    )
    sort_parser.add_argument(
        "--by",
        type=str,
        choices=["newest", "oldest", "popular", "default"],
        default="default",
        help="Sort criteria: newest, oldest, popular, default",
    )

    # validate-years subcommand
    validate_parser = subparsers.add_parser(
        "validate-years",
        help="Validate that classic artist entries are not using reissue years",
    )
    validate_parser.add_argument(
        "--html", type=str, default=INDEX_FILE, help="Path to index.html"
    )

    args = parser.parse_args()

    if args.command == "match":
        try:
            yt = YTMusic(HEADER_FILE) if os.path.exists(HEADER_FILE) else YTMusic()
        except Exception:
            logger.info(
                "Failed to load header file. Initializing in unauthenticated mode."
            )
            yt = YTMusic()

        if args.search:
            parts = args.search.split(" - ", 1)
            artist = parts[0] if len(parts) == 2 else "Unknown"
            title = parts[1] if len(parts) == 2 else args.search
            match = get_youtube_album(yt, artist, title)
            if match:
                logger.info(
                    "Match found: PlaylistID=%s, VideoID=%s",
                    match.get("playlistId"),
                    match.get("firstVideoId"),
                )
            else:
                logger.warning("No match found.")
        else:
            albums = extract_album_entries_from_html(args.html)
            for album_id, info in albums.items():
                match = get_youtube_album(
                    yt, info["artist"], info["title"], info["year"]
                )
                if match:
                    print(f"\nAlbum: {album_id}")
                    print(f"  PlaylistID: {match.get('playlistId')}")
                    print(f"  FirstVideoID: {match.get('firstVideoId')}")

    elif args.command == "test-links":
        success = test_youtube_links(args.html)
        if not success:
            sys.exit(1)

    elif args.command == "benchmark":
        run_benchmark(args.html)

    elif args.command == "export-tsv":
        export_tsv_glossary(args.html, args.tsv)

    elif args.command == "research-todos":
        research_todos(args.todo, args.library, args.inbox)

    elif args.command == "todo-wizard":
        todo_wizard(args.todo)

    elif args.command == "import-album":
        try:
            yt = (
                YTMusic(HEADER_FILE)
                if os.path.exists(HEADER_FILE)
                else YTMusic()
            )
        except Exception:
            yt = YTMusic()

        logger.info(
            "Searching YTMusic for: %s - %s...", args.artist, args.album
        )
        match = get_youtube_album(yt, args.artist, args.album)
        if match:
            matched_title = match.get("title")
            matched_artist = match["artists"][0]["name"]
            matched_year = match.get("year", "Unknown")
            album_id = match.get("browseId")

            logger.info(
                "Match found: '%s' by %s (%s)",
                matched_title,
                matched_artist,
                matched_year,
            )
            if album_id:
                logger.info(
                    "URL:         https://music.youtube.com/browse/%s",
                    album_id,
                )

            promote_album_to_html(
                args.artist, args.album, args.popularity, match
            )
            export_tsv_glossary(INDEX_FILE, "albums_glossary.tsv")
            logger.info("Album successfully imported and index updated!")
        else:
            logger.error("Could not find matching album on YouTube Music.")

    elif args.command == "sort-tsv":
        sort_tsv_file(args.file, args.by)

    elif args.command == "validate-years":
        success = validate_catalog_years(args.html)
        sys.exit(0 if success else 1)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
