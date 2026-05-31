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


if __name__ == "__main__":
    unittest.main()
