import queue
import tempfile
import unittest
from pathlib import Path

from file_organizer import OrganizerApp


class OrganizerLogicTests(unittest.TestCase):
    def setUp(self):
        self.app = object.__new__(OrganizerApp)
        self.app.log_queue = queue.Queue()
        self.app.last_manifest = []

    @staticmethod
    def config(root, **overrides):
        values = {
            "source": root,
            "destination": root,
            "index": 2,
            "extensions": {"jpg"},
            "recursive": False,
            "include_unmatched": False,
            "separator": "-",
            "pattern": "",
        }
        values.update(overrides)
        return values

    def test_example_files_are_grouped_and_moved(self):
        names = [
            "abc-123456-001.jpg",
            "abc-123456-002.jpg",
            "abc-123456-003.jpg",
            "acb-1234567-001.jpg",
            "acb-1234567-002.jpg",
            "acb-1234567-003.jpg",
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            for name in names:
                (root / name).write_text(name, encoding="utf-8")

            _, _, groups, unmatched = self.app._scan_files(self.config(root))

            self.assertFalse(unmatched)
            self.assertEqual({name: len(files) for name, files in groups.items()}, {
                "123456": 3,
                "1234567": 3,
            })

            self.app._organize_worker(root, "跳过（推荐）", groups)
            self.assertEqual(self.app.log_queue.get_nowait(), ("organize_ok", (6, 0, 0)))
            self.assertEqual(sorted(path.name for path in (root / "123456").iterdir()), names[:3])
            self.assertEqual(sorted(path.name for path in (root / "1234567").iterdir()), names[3:])

    def test_regex_uses_first_capture_group(self):
        path = Path("prefix-778899-suffix.png")
        group = self.app._extract_group(path, 1, "-", r"^[^-]+-(\d+)-")
        self.assertEqual(group, "778899")

    def test_invalid_windows_folder_names_are_sanitized(self):
        self.assertEqual(self.app._safe_group_name("CON"), "_CON")
        self.assertEqual(self.app._safe_group_name("../bad:name"), "_bad_name")

    def test_recursive_rescan_ignores_already_sorted_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            group_dir = root / "123456"
            group_dir.mkdir()
            (group_dir / "abc-123456-001.jpg").write_text("data", encoding="utf-8")

            _, _, groups, _ = self.app._scan_files(self.config(root, recursive=True))

            self.assertEqual(groups, {})


if __name__ == "__main__":
    unittest.main()

