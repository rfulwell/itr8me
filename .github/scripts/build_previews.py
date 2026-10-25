#!/usr/bin/env python3
"""Build a preview of each open pull request into _site/preview/pr-<number>/.

Runs in the Pages workflow after the main site is built, so every deploy
carries a preview of every open PR, plus an index at /preview/. A PR's preview
appears when it opens, updates on each push, and disappears once it's closed.

Only PRs from branches in this repository are built. The workflow can deploy
the site, so building a fork's branch would run a stranger's code with that
access.

Previews use the main branch's Gemfile, so a PR that changes gems previews
with the current ones. A preview that fails to build is listed as failed and
doesn't stop the deploy.

Uses only the Python standard library.
"""

import html
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

PREVIEWS_DIR = Path("_site/preview")
NOINDEX = '<meta name="robots" content="noindex">'
HEAD_TAG = re.compile(r"<head(\s[^>]*)?>", re.I)


def open_pulls(repo, token):
    request = urllib.request.Request(
        f"https://api.github.com/repos/{repo}/pulls?state=open&per_page=100",
        headers={"Accept": "application/vnd.github+json", **({"Authorization": f"Bearer {token}"} if token else {})},
    )
    with urllib.request.urlopen(request, timeout=60) as resp:
        return json.load(resp)


def same_repo(pull, repo):
    head_repo = pull["head"]["repo"]
    return head_repo is not None and head_repo["full_name"] == repo


def build(pull, base_path, workdir):
    number = pull["number"]
    source = workdir / f"pr-{number}"
    destination = PREVIEWS_DIR / f"pr-{number}"
    subprocess.run(["git", "fetch", "--quiet", "--depth", "1", "origin", f"pull/{number}/head"], check=True)
    subprocess.run(["git", "worktree", "add", "--quiet", "--detach", str(source), "FETCH_HEAD"], check=True)
    try:
        subprocess.run(
            ["bundle", "exec", "jekyll", "build", "--source", str(source),
             "--destination", str(destination), "--baseurl", f"{base_path}/preview/pr-{number}"],
            check=True,
        )
    finally:
        subprocess.run(["git", "worktree", "remove", "--force", str(source)], check=True)
    # Keep previews out of search results.
    for page in destination.rglob("*.html"):
        text = page.read_text(encoding="utf-8")
        page.write_text(HEAD_TAG.sub(lambda m: m.group(0) + NOINDEX, text, count=1), encoding="utf-8")


def render_index(entries, base_path, built_at):
    items = []
    for pull, ok in entries:
        number, title = pull["number"], html.escape(pull["title"])
        branch, author = html.escape(pull["head"]["ref"]), html.escape(pull["user"]["login"])
        preview = (f'<a href="{base_path}/preview/pr-{number}/">{title}</a>' if ok
                   else f'{title} <span class="failed">(preview failed to build; see the workflow log)</span>')
        items.append(
            f'<li>{preview}<br><span class="meta">#{number} · {branch} · {author} · '
            f'<a href="{html.escape(pull["html_url"])}">pull request</a></span></li>'
        )
    body = f"<ul>{''.join(items)}</ul>" if items else "<p>No open pull requests.</p>"
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
{NOINDEX}
<meta name="color-scheme" content="light dark">
<title>Previews · itr8me</title>
<style>
  body {{ font: 16px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
         max-width: 760px; margin: 40px auto; padding: 0 16px; color: #111; background: #fdfdfd; }}
  a {{ color: #2a7ae2; }}
  ul {{ list-style: none; padding: 0; }}
  li {{ margin-bottom: 20px; font-size: 18px; }}
  .meta, footer {{ font-size: 14px; color: #828282; }}
  .failed {{ font-size: 14px; color: #b3261e; }}
  @media (prefers-color-scheme: dark) {{
    body {{ color: #e3e3e3; background: #1e1e1e; }}
    a {{ color: #6cb2ff; }}
    .meta, footer {{ color: #a0a0a0; }}
    .failed {{ color: #ffa198; }}
  }}
</style>
</head>
<body>
<h1>Previews of open pull requests</h1>
{body}
<footer>Built {built_at}. <a href="{base_path}/">Back to the live site</a></footer>
</body>
</html>
"""


def main():
    repo = os.environ["GITHUB_REPOSITORY"]
    base_path = os.environ.get("BASE_PATH", "").rstrip("/")
    pulls = [p for p in open_pulls(repo, os.environ.get("GITHUB_TOKEN")) if same_repo(p, repo)]
    pulls.sort(key=lambda p: p["number"], reverse=True)

    entries = []
    with tempfile.TemporaryDirectory() as workdir:
        for pull in pulls:
            print(f"Building preview of #{pull['number']}: {pull['title']}", flush=True)
            try:
                build(pull, base_path, Path(workdir))
                entries.append((pull, True))
            except subprocess.CalledProcessError as error:
                print(f"::warning::Preview of #{pull['number']} failed to build: {error}", flush=True)
                entries.append((pull, False))

    PREVIEWS_DIR.mkdir(parents=True, exist_ok=True)
    built_at = datetime.now(ZoneInfo(os.environ.get("SITE_TZ", "America/Los_Angeles"))).strftime("%b %-d, %Y, %-I:%M %p %Z")
    (PREVIEWS_DIR / "index.html").write_text(render_index(entries, base_path, built_at), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
