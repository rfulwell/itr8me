#!/usr/bin/env python3
"""Sync blog posts from a public Google Drive folder into _posts/gdocs/.

Every Google Doc in the folder or its subfolders is a post, unless the first
word of its title is "draft" (any case, ignoring symbols: "Draft: x",
"[DRAFT] x" and "draft - x" are all drafts). Google's default "Untitled document" also counts
as a draft so a freshly created doc never goes live by accident.

Edits go live once a doc has been quiet for QUIET, so half-written sentences
aren't published. A doc whose title goes from draft to non-draft publishes on
the next run regardless, and a manual run (GDOCS_PUBLISH_NOW=true, set by the
workflow) publishes every doc without waiting. Removing a doc from the folder,
trashing it, or renaming it back to a draft takes the post down.

Each post keeps the slug and date from its first publish, recorded in
.gdocs/state.json, so renaming a published doc doesn't change its URL.

There's no API key: the folder listing and edit times are scraped from Drive's
public folder page, and docs are downloaded from their public export links.
That page only shows FOLDER_PAGE_LIMIT items, so a folder that reaches it fails
the sync rather than unpublishing the docs it can't see; move older posts into
a subfolder.

The folder must be shared as "Anyone with the link can view"; its ID is set as
GDRIVE_FOLDER_ID in .github/workflows/jekyll.yml.

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
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

DOC_MIME = "application/vnd.google-apps.document"
FOLDER_MIME = "application/vnd.google-apps.folder"
FOLDER_PAGE_LIMIT = 50
QUIET = timedelta(minutes=10)
USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"

# The folder page embeds its items as JSON inside an escaped JavaScript string.
FOLDER_DATA = re.compile(r"_DRIVE_ivd'\] = '((?:[^'\\]|\\.)*)'")
JS_ESCAPE = re.compile(r"\\(x[0-9a-fA-F]{2}|u[0-9a-fA-F]{4}|.)", re.S)
JS_CHARS = {"n": "\n", "r": "\r", "t": "\t", "b": "\b", "f": "\f", "v": "\v", "0": "\0"}

POSTS_DIR = Path("_posts/gdocs")
ASSETS_DIR = Path("assets/gdocs")
STATE_FILE = Path(".gdocs/state.json")

IMAGE_EXTS = {"jpeg": "jpg", "svg+xml": "svg"}
# A base64 image data URI, optionally wrapped in <...> as Google's export does
# for reference-style image links.
DATA_URI = re.compile(r"(<)?data:image/([\w.+-]+);base64,([A-Za-z0-9+/=]+)(?(1)>)")
HEADING = re.compile(r"#{1,6}[ \t]+(.*?)[ \t#]*$")
# A blank line styled as a heading in the doc exports as a bare "#", which
# Jekyll would show as a literal "#".
EMPTY_HEADING = re.compile(r"^#{1,6}[ \t]*$\n?", re.M)
# Backticks typed in a doc come out escaped, so ```code``` and `code` have to be
# found in their escaped form.
CODE_FENCE = re.compile(r"^[ \t]*\\`\\`\\`([\w+-]*)(.*?)\\`\\`\\`[ \t]*$", re.M | re.S)
INLINE_CODE = re.compile(r"\\`([^`\n]+?)\\`")
MD_ESCAPE = re.compile(r"\\([!-/:-@\[-`{-~])")


def words(text):
    return re.findall(r"[^\W_]+", text.casefold())


def is_draft(title):
    return title.strip() == "Untitled document" or words(title)[:1] == ["draft"]


def slugify(title):
    ascii_title = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode()
    return "-".join(words(ascii_title))


def js_unescape(text):
    def replace(match):
        escape = match.group(1)
        if len(escape) > 1:
            return chr(int(escape[1:], 16))
        return JS_CHARS.get(escape, escape)

    # \u escapes can encode emoji as surrogate pairs; this joins them.
    return JS_ESCAPE.sub(replace, text).encode("utf-16", "surrogatepass").decode("utf-16")


def parse_folder_page(html):
    """Return the folder's items as (id, name, mime type, modified datetime)."""
    match = FOLDER_DATA.search(html)
    if not match:
        raise RuntimeError("No folder data on the Drive page; is the folder shared publicly?")
    items = json.loads(js_unescape(match.group(1)))[0] or []
    # Index 10 is the last-modified time in epoch milliseconds (9 is created).
    return [(i[0], i[2], i[3], datetime.fromtimestamp(i[10] / 1000, timezone.utc)) for i in items]


class Drive:
    def _get(self, url):
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(request, timeout=60) as resp:
            return resp.headers.get_content_type(), resp.read().decode("utf-8")

    def list_docs(self, folder_id):
        _, html = self._get(f"https://drive.google.com/drive/folders/{folder_id}")
        items = parse_folder_page(html)
        if len(items) >= FOLDER_PAGE_LIMIT:
            raise RuntimeError(
                f"Folder {folder_id} has {len(items)} items, the most Drive's page shows, so "
                "some may be missing. Move older posts into a subfolder."
            )
        docs = []
        for item_id, name, mime, modified in items:
            if mime == FOLDER_MIME:
                docs += self.list_docs(item_id)
            elif mime == DOC_MIME:
                docs.append({"id": item_id, "name": name, "modified": modified})
        return docs

    def export_markdown(self, doc_id):
        content_type, text = self._get(f"https://docs.google.com/document/d/{doc_id}/export?format=md")
        # A doc that isn't public serves a sign-in page instead.
        if content_type == "text/html":
            raise RuntimeError(f"Doc {doc_id} didn't export; is it shared publicly?")
        return text


def unescape(text):
    return MD_ESCAPE.sub(r"\1", text)


def code_block(match):
    # Each line of code is its own paragraph in the doc (blank line between) or
    # a line break (two trailing spaces), so turn both back into plain newlines.
    code = re.sub(r"[ \t]+\n", "\n", match.group(2)).replace("\n\n", "\n").strip("\n")
    return f"```{match.group(1)}\n{unescape(code)}\n```"


def convert(markdown, title, slug):
    """Turn exported Markdown into a post body plus {filename: bytes} images."""
    images = {}

    def extract(match):
        subtype, data = match.group(2).lower(), match.group(3)
        content = base64.b64decode(data)
        name = f"{hashlib.sha256(content).hexdigest()[:12]}.{IMAGE_EXTS.get(subtype, subtype)}"
        images[name] = content
        return f"/{ASSETS_DIR}/{slug}/{name}"

    body = DATA_URI.sub(extract, markdown)
    body = EMPTY_HEADING.sub("", body).strip()
    body = CODE_FENCE.sub(code_block, body)
    body = INLINE_CODE.sub(lambda m: f"`{unescape(m.group(1))}`", body)

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


def sync(root, drive, folder_id, now, quiet=QUIET):
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
        if was_draft is not True and now - doc["modified"] < quiet:
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
    folder_id = os.environ.get("GDRIVE_FOLDER_ID")
    if not folder_id:
        print("GDRIVE_FOLDER_ID not set; skipping Google Docs sync.")
        return 0
    now = datetime.now(ZoneInfo(os.environ.get("SITE_TZ", "America/Los_Angeles")))
    quiet = timedelta(0) if os.environ.get("GDOCS_PUBLISH_NOW") == "true" else QUIET
    sync(Path.cwd(), Drive(), folder_id, now, quiet)
    return 0


if __name__ == "__main__":
    sys.exit(main())
