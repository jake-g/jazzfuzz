"""Unit tests for maintenance.py utility."""

import unittest
from unittest import mock

import maintenance


class MaintenanceTest(unittest.TestCase):
    """Tests for maintenance.py functions."""

    def test_extract_year_valid(self):
        self.assertEqual(maintenance.extract_year("June, 2018"), 2018)
        self.assertEqual(maintenance.extract_year("1966"), 1966)
        self.assertEqual(maintenance.extract_year("Released: 1954"), 1954)

    def test_extract_year_invalid(self):
        self.assertIsNone(maintenance.extract_year("Unknown"))
        self.assertIsNone(maintenance.extract_year("June"))

    def test_get_album_id_no_year(self):
        self.assertEqual(
            maintenance.get_album_id("Miles Davis", "Kind of Blue"),
            "Miles Davis - Kind of Blue",
        )

    def test_get_album_id_with_year(self):
        self.assertEqual(
            maintenance.get_album_id("Miles Davis", "Kind of Blue", 1959),
            "Miles Davis - Kind of Blue [1959]",
        )

    @mock.patch("requests.head")
    def test_validate_single_link_video_success(self, mock_head):
        mock_response = mock.Mock()
        mock_response.status_code = 200
        mock_head.return_value = mock_response

        item_type, item_id, is_valid = maintenance.validate_single_link(
            "video", "rqpriUFsMQQ"
        )
        self.assertEqual(item_type, "video")
        self.assertEqual(item_id, "rqpriUFsMQQ")
        self.assertTrue(is_valid)

    @mock.patch("requests.head")
    def test_validate_single_link_playlist_fail(self, mock_head):
        mock_response = mock.Mock()
        mock_response.status_code = 404
        mock_head.return_value = mock_response

        item_type, item_id, is_valid = maintenance.validate_single_link(
            "playlist", "invalid_id"
        )
        self.assertEqual(item_type, "playlist")
        self.assertEqual(item_id, "invalid_id")
        self.assertFalse(is_valid)

    @mock.patch(
        "builtins.open",
        new_callable=mock.mock_open,
        read_data="""
    <article>
      <header>
        <h2>Giant Steps</h2>
        <h3>By: John Coltrane</h3>
        <h3>Released: January, 1960</h3>
        <h3>Genre: Jazz</h3>
      </header>
      <div class="playerContainer">
        <lite-youtube params="rel=0&modestbranding=1"
          videoid="XYZ123"
          playlistid="OLAK5uy_XYZ"
        ></lite-youtube>
      </div>
      <main>
        <ol>
          <li>Giant Steps</li>
          <li>Cousin Mary</li>
        </ol>
      </main>
    </article>
  """,
    )
    @mock.patch("os.path.exists")
    def test_extract_album_entries_from_html(self, mock_exists, mock_file):
        mock_exists.return_value = True
        albums = maintenance.extract_album_entries_from_html("index.html")
        self.assertEqual(len(albums), 1)
        album = albums["John Coltrane - Giant Steps"]
        self.assertEqual(album["title"], "Giant Steps")
        self.assertEqual(album["artist"], "John Coltrane")
        self.assertEqual(album["year"], 1960)
        self.assertEqual(album["video_id"], "XYZ123")
        self.assertEqual(album["playlist_id"], "OLAK5uy_XYZ")
        self.assertEqual(album["track_count"], 2)

    @mock.patch("os.path.exists")
    def test_load_musicbee_tracks(self, mock_exists):
        mock_exists.return_value = True
        read_data = (
            "Artist\tAlbum\tRating\n"
            "Miles Davis\tKind of Blue\t5.0\n"
            "John Coltrane\tA Love Supreme\t4.5\n"
        )
        with mock.patch("builtins.open", mock.mock_open(read_data=read_data)) as mock_file:
            tracks = maintenance.load_musicbee_tracks("dummy_path")
            self.assertEqual(len(tracks), 2)
            self.assertEqual(tracks[0]["artist"], "Miles Davis")
            self.assertEqual(tracks[0]["album"], "Kind of Blue")
            self.assertEqual(tracks[0]["rating"], 5.0)

    @mock.patch("maintenance.load_musicbee_tracks")
    @mock.patch("os.path.exists")
    def test_research_todos(self, mock_exists, mock_load):
        mock_exists.return_value = True
        mock_load.side_effect = [
            [
                {"artist": "Miles Davis", "album": "In a Silent Way", "rating": 5.0},
                {"artist": "Miles Davis", "album": "In a Silent Way", "rating": 4.0},
                {"artist": "Miles Davis", "album": "Bitches Brew", "rating": 3.0}
            ],
            [] # inbox empty
        ]

        read_data = (
            "Album\tArtist\n"
            "In a Silent Way\tMiles Davis\n"
        )
        m_open = mock.mock_open(read_data=read_data)
        with mock.patch("builtins.open", m_open) as mock_file:
            maintenance.research_todos("todo.tsv", "lib.tsv", "inbox.tsv")
            # Verify open was called to write the output
            mock_file.assert_any_call("todo.tsv", "w", encoding="utf-8", newline="")


    def test_sort_tsv_file_by_criteria(self):
        import tempfile
        import os

        fd, path = tempfile.mkstemp()
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(
                    "Album\tArtist\tReleased\tPopularity\n"
                    "Kind of Blue\tMiles Davis\tAugust, 1959\t100\n"
                    "Moanin'\tArt Blakey\tJanuary, 1959\t95\n"
                    "Time Out\tDave Brubeck\tDecember, 1959\t98\n"
                )

            # Test "newest" sorting
            maintenance.sort_tsv_file(path, "newest")

            with open(path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            self.assertEqual(len(lines), 4)
            self.assertIn("Kind of Blue", lines[1])  # Dec 1959 (tie-breaker pop 100)
            self.assertIn("Time Out", lines[2])      # Dec 1959 (tie-breaker pop 98)
            self.assertIn("Moanin'", lines[3])       # Jan 1959 (tie-breaker pop 95)
        finally:
            os.remove(path)


if __name__ == "__main__":
    unittest.main()
