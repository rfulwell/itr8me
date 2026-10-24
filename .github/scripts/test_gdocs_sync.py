import base64
import json
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import gdocs_sync as g

NOW = datetime(2026, 10, 24, 12, 0, tzinfo=ZoneInfo("America/Los_Angeles"))
PNG = b"\x89PNG fake image"
PNG_B64 = base64.b64encode(PNG).decode()


def modified(minutes_ago):
    return (NOW - timedelta(minutes=minutes_ago)).astimezone(ZoneInfo("UTC")).isoformat().replace("+00:00", "Z")


class FakeDrive:
    def __init__(self):
        self.docs = {}
        self.exported = []

    def add(self, doc_id, name, minutes_ago, markdown="Hello."):
        self.docs[doc_id] = ({"id": doc_id, "name": name, "modifiedTime": modified(minutes_ago)}, markdown)

    def list_docs(self, folder_id):
        return [meta for meta, _ in self.docs.values()]

    def export_markdown(self, doc_id):
        self.exported.append(doc_id)
        return self.docs[doc_id][1]


class IsDraftTest(unittest.TestCase):
    def test_drafts(self):
        for title in ["Draft", "draft my post", "DRAFT: my post", "[Draft] my post", "  -- draft-my post", "Untitled document"]:
            self.assertTrue(g.is_draft(title), title)

    def test_not_drafts(self):
        for title in ["Drafting a plan", "My draft", "Draftee", "Untitled thoughts", ""]:
            self.assertFalse(g.is_draft(title), title)


class ConvertTest(unittest.TestCase):
    def test_extracts_reference_and_inline_images(self):
        md = (
            "# My Post\n\nIntro ![][image1] and ![alt](data:image/png;base64," + PNG_B64 + ")\n\n"
            "[image1]: <data:image/jpeg;base64," + PNG_B64 + ">\n"
        )
        body, images = g.convert(md, "My post!", "my-post")
        digest = next(iter(images)).split(".")[0]
        self.assertEqual(set(images), {f"{digest}.png", f"{digest}.jpg"})
        self.assertNotIn("data:", body)
        self.assertNotIn("# My Post", body)
        self.assertIn(f"](/assets/gdocs/my-post/{digest}.png)", body)
        self.assertIn(f"[image1]: /assets/gdocs/my-post/{digest}.jpg", body)

    def test_keeps_heading_that_is_not_the_title(self):
        body, _ = g.convert("# Background\n\nText", "My post", "my-post")
        self.assertTrue(body.startswith("# Background"))


class SyncTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.drive = FakeDrive()

    def run_sync(self, now=NOW):
        g.sync(self.root, self.drive, "folder", now)

    def posts(self):
        return sorted(p.name for p in (self.root / g.POSTS_DIR).glob("*.md"))

    def state(self):
        return json.loads((self.root / g.STATE_FILE).read_text())

    def test_publishes_quiet_doc_with_front_matter(self):
        self.drive.add("a", 'He said "hi": a story', 30, "Body {{ not liquid }}")
        self.run_sync()
        self.assertEqual(self.posts(), ["2026-10-24-he-said-hi-a-story.md"])
        text = (self.root / g.POSTS_DIR / self.posts()[0]).read_text()
        self.assertIn('title: "He said \\"hi\\": a story"\n', text)
        self.assertIn("date: 2026-10-24 12:00:00 -0700\n", text)
        self.assertIn("{% raw %}\nBody {{ not liquid }}\n{% endraw %}", text)

    def test_waits_for_recent_edits(self):
        self.drive.add("a", "New post", 3)
        self.run_sync()
        self.assertEqual(self.posts(), [])
        self.run_sync(NOW + timedelta(minutes=8))
        self.assertEqual(self.posts(), ["2026-10-24-new-post.md"])

    def test_draft_never_publishes(self):
        self.drive.add("a", "Draft: secret", 60)
        self.run_sync()
        self.assertEqual(self.posts(), [])
        self.assertEqual(self.state(), {"a": {"draft": True}})

    def test_draft_to_published_skips_quiet_period(self):
        self.drive.add("a", "Draft: Big news", 60)
        self.run_sync()
        self.drive.add("a", "Big news", 0)
        self.run_sync()
        self.assertEqual(self.posts(), ["2026-10-24-big-news.md"])

    def test_later_edits_wait_again_after_going_live(self):
        self.drive.add("a", "Draft: Big news", 60)
        self.run_sync()
        self.drive.add("a", "Big news", 0, "v1")
        self.run_sync()
        self.drive.add("a", "Big news", 0, "v2")
        self.run_sync(NOW + timedelta(minutes=1))
        self.assertIn("v1", (self.root / g.POSTS_DIR / self.posts()[0]).read_text())

    def test_rename_keeps_url_and_updates_title(self):
        self.drive.add("a", "First title", 60)
        self.run_sync()
        self.drive.add("a", "Second title", 60)
        self.run_sync(NOW + timedelta(days=2))
        self.assertEqual(self.posts(), ["2026-10-24-first-title.md"])
        self.assertIn('title: "Second title"', (self.root / g.POSTS_DIR / self.posts()[0]).read_text())

    def test_back_to_draft_unpublishes_and_republish_keeps_url(self):
        self.drive.add("a", "Post", 60, "![](data:image/png;base64," + PNG_B64 + ")")
        self.run_sync()
        self.assertTrue((self.root / g.ASSETS_DIR / "post").exists())
        self.drive.add("a", "Draft Post", 60)
        self.run_sync()
        self.assertEqual(self.posts(), [])
        self.assertFalse((self.root / g.ASSETS_DIR / "post").exists())
        self.drive.add("a", "Post", 0)
        self.run_sync(NOW + timedelta(days=3))
        self.assertEqual(self.posts(), ["2026-10-24-post.md"])

    def test_removed_doc_unpublishes(self):
        self.drive.add("a", "Post", 60)
        self.run_sync()
        del self.drive.docs["a"]
        self.run_sync()
        self.assertEqual(self.posts(), [])
        self.assertEqual(self.state(), {})

    def test_duplicate_titles_get_distinct_slugs(self):
        self.drive.add("a", "Same", 60)
        self.drive.add("b", "Same", 60)
        self.run_sync()
        self.assertEqual(self.posts(), ["2026-10-24-same-2.md", "2026-10-24-same.md"])

    def test_stale_images_removed(self):
        self.drive.add("a", "Post", 60, "![](data:image/png;base64," + PNG_B64 + ")")
        self.run_sync()
        other = base64.b64encode(b"other").decode()
        self.drive.add("a", "Post", 60, "![](data:image/gif;base64," + other + ")")
        self.run_sync()
        names = [p.suffix for p in (self.root / g.ASSETS_DIR / "post").iterdir()]
        self.assertEqual(names, [".gif"])


if __name__ == "__main__":
    unittest.main()
