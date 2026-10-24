#!/usr/bin/env python3
"""Sync blog posts from a public Google Drive folder into _posts/gdocs/.

Every Google Doc directly inside the folder is a post, unless the first word of
its title is "draft" (any case, ignoring symbols: "Draft: x", "[DRAFT] x" and
"draft - x" are all drafts). Google's default "Untitled document" also counts
as a draft so a freshly created doc never goes live by accident.

Edits go live once a doc has been quiet for QUIET, so half-written sentences
aren't published. A doc whose title goes from draft to non-draft publishes on
the next run regardless. Removing a doc from the folder, trashing it, or
renaming it back to a draft takes the post down.

Each post keeps the slug and date from its first publish, recorded in
.gdocs/state.json, so renaming a published doc doesn't change its URL.

Setup:
  1. Share the Drive folder as "Anyone with the link can view".
  2. In a Google Cloud project, enable the Google Drive API and create an API
     key restricted to it.
  3. In the GitHub repo settings, add the secret GDRIVE_API_KEY and the
     variable GDRIVE_FOLDER_ID (the ID at the end of the folder's URL).

Uses only the Python standard library.
"""

import base64
import hashlib
import json
import os
import re
import shutil
import sys
import unicodedata
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

DRIVE_API = "https://www.googleapis.com/drive/v3"
DOC_MIME = "application/vnd.google-apps.document"
QUIET = timedelta(minutes=10)

POSTS_DIR = Path("_posts/gdocs")
ASSETS_DIR = Path("assets/gdocs")
STATE_FILE = Path(".gdocs/state.json")

IMAGE_EXTS = {"jpeg": "jpg", "svg+xml": "svg"}
# A base64 image data URI, optionally wrapped in <...> as Google's export does
# for reference-style image links.
DATA_URI = re.compile(r"(<)?data:image/([\w.+-]+);base64,([A-Za-z0-9+/=]+)(?(1)>)")
HEADING = re.compile(r"#{1,6}[ \t]+(.*?)[ \t#]*$")


def words(text):
    return re.findall(r"[^\W_]+", text.casefold())


def is_draft(title):
    return title.strip() == "Untitled document" or words(title)[:1] == ["draft"]


def slugify(title):
    ascii_title = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode()
    return "-".join(words(ascii_title))


class Drive:
    def __init__(self, api_key):
        self.api_key = api_key

    def _get(self, path, **params):
        query = urllib.parse.urlencode({**params, "key": self.api_key})
        with urllib.request.urlopen(f"{DRIVE_API}/{path}?{query}", timeout=60) as resp:
            return resp.read()

    def list_docs(self, folder_id):
        docs, token = [], None
        while True:
            params = {
                "q": f"'{folder_id}' in parents and mimeType='{DOC_MIME}' and trashed=false",
                "fields": "nextPageToken,files(id,name,modifiedTime)",
                "pageSize": 1000,
            }
            if token:
                params["pageToken"] = token
            page = json.loads(self._get("files", **params))
            docs.extend(page.get("files", []))
            token = page.get("nextPageToken")
            if not token:
                return docs

    def export_markdown(self, doc_id):
        return self._get(f"files/{doc_id}/export", mimeType="text/markdown").decode("utf-8")


def convert(markdown, title, slug):
    """Turn exported Markdown into a post body plus {filename: bytes} images."""
    images = {}

    def extract(match):
        subtype, data = match.group(2).lower(), match.group(3)
        content = base64.b64decode(data)
        name = f"{hashlib.sha256(content).hexdigest()[:12]}.{IMAGE_EXTS.get(subtype, subtype)}"
        images[name] = content
        return f"/{ASSETS_DIR}/{slug}/{name}"

    body = DATA_URI.sub(extract, markdown).strip()

    # The post layout already shows the title, so drop a leading heading that
    # repeats it.
    first, _, rest = body.partition("\n")
    heading = HEADING.fullmatch(first.strip())
    if heading and words(heading.group(1)) == words(title):
        body = rest.strip()

    return body, images


def render_post(title, date, doc_id, body):
    # Wrapped in raw so "{{" or "{%" in a post (e.g. code samples) isn't run as
    # Liquid.
    return (
        "---\n"
        "layout: post\n"
        f"title: {json.dumps(title, ensure_ascii=False)}\n"
        f"date: {date}\n"
        f"gdoc_id: {doc_id}\n"
        "---\n"
        "{% raw %}\n"
        f"{body}\n"
        "{% endraw %}\n"
    )


def post_path(root, entry):
    return root / POSTS_DIR / f"{entry['date'][:10]}-{entry['slug']}.md"


def unpublish(root, entry):
    if "slug" not in entry:
        return
    post_path(root, entry).unlink(missing_ok=True)
    shutil.rmtree(root / ASSETS_DIR / entry["slug"], ignore_errors=True)


def publish(root, drive, doc, entry, state, now):
    if "slug" not in entry:
        base = slugify(doc["name"]) or doc["id"]
        taken = {e.get("slug") for e in state.values()}
        slug, n = base, 2
        while slug in taken:
            slug, n = f"{base}-{n}", n + 1
        entry["slug"] = slug
        entry["date"] = now.strftime("%Y-%m-%d %H:%M:%S %z")

    body, images = convert(drive.export_markdown(doc["id"]), doc["name"], entry["slug"])

    path = post_path(root, entry)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_post(doc["name"], entry["date"], doc["id"], body), encoding="utf-8")

    image_dir = root / ASSETS_DIR / entry["slug"]
    if image_dir.exists():
        for stale in image_dir.iterdir():
            if stale.name not in images:
                stale.unlink()
    for name, content in images.items():
        image_dir.mkdir(parents=True, exist_ok=True)
        (image_dir / name).write_bytes(content)


def sync(root, drive, folder_id, now):
    state_path = root / STATE_FILE
    state = json.loads(state_path.read_text()) if state_path.exists() else {}

    docs = drive.list_docs(folder_id)
    for doc in docs:
        entry = state.setdefault(doc["id"], {})
        was_draft = entry.get("draft")
        entry["draft"] = is_draft(doc["name"])
        if entry["draft"]:
            unpublish(root, entry)
            continue
        modified = datetime.fromisoformat(doc["modifiedTime"].replace("Z", "+00:00"))
        if was_draft is not True and now - modified < QUIET:
            print(f"Waiting for edits to settle: {doc['name']}")
            continue
        print(f"Publishing: {doc['name']}")
        publish(root, drive, doc, entry, state, now)

    present = {doc["id"] for doc in docs}
    for doc_id in [d for d in state if d not in present]:
        unpublish(root, state.pop(doc_id))

    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")


def main():
    api_key = os.environ.get("GDRIVE_API_KEY")
    folder_id = os.environ.get("GDRIVE_FOLDER_ID")
    if not api_key or not folder_id:
        print("GDRIVE_API_KEY or GDRIVE_FOLDER_ID not set; skipping Google Docs sync.")
        return 0
    now = datetime.now(ZoneInfo(os.environ.get("SITE_TZ", "America/Los_Angeles")))
    sync(Path.cwd(), Drive(api_key), folder_id, now)
    return 0


if __name__ == "__main__":
    sys.exit(main())
