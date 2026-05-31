"""Utility script for Jazz Fuzz website maintenance.

Supports matching albums on YouTube Music, testing YouTube links, benchmarking
poster image load times, and exporting album indexes to TSV format.
"""

import argparse
import concurrent.futures
import csv
import logging
import os
import re
import sys
import time
from typing import Dict, List, Optional, Tuple, Union

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
    """Scans HTML for YouTube video and playlist IDs and validates them.

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
                    logger.error(
                        "Broken link in %s: %s ID '%s' is invalid (404/OEmbed error)",
                        album_name,
                        item_type,
                        item_id,
                    )
            except Exception as e:  # pylint: disable=broad-except
                broken_count += 1
                logger.error("Failed checking %s ID %s: %s", item_type, item_id, e)

    logger.info(
        "Link validation finished. Valid: %d, Broken: %d", valid_count, broken_count
    )
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

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
