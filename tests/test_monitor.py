import json
import tempfile
import unittest
from pathlib import Path

import monitor


class MonitorTests(unittest.TestCase):
    def test_normalize_content_removes_blank_lines_and_whitespace(self):
        text = "  a  \n\n b\n   \n c "
        self.assertEqual(monitor.normalize_content(text), "a\nb\nc")

    def test_build_snapshot_matches_keywords_case_insensitive(self):
        snap = monitor.build_snapshot("予約可能です", ["予約", "空き", "可能"])
        self.assertEqual(snap.matched_keywords, ("予約", "可能"))

    def test_save_and_load_snapshot_roundtrip(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "state.json"
            original = monitor.Snapshot(checksum="abc", matched_keywords=("空き",))
            monitor.save_snapshot(path, original)

            loaded = monitor.load_snapshot(path)
            self.assertIsNotNone(loaded)
            assert loaded is not None
            self.assertEqual(loaded.checksum, "abc")
            self.assertEqual(loaded.matched_keywords, ("空き",))

            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(data["matched_keywords"], ["空き"])


if __name__ == "__main__":
    unittest.main()
