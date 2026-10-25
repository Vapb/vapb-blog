"""Fail if any post title exceeds MAX_TITLE_LENGTH characters.

Usage: python scripts/check_titles.py
"""
import re
import sys
from pathlib import Path

MAX_TITLE_LENGTH = 60
POSTS_DIR = Path(__file__).resolve().parent.parent / "content" / "pt" / "posts"

TITLE_RE = re.compile(r'^title:\s*(?:"(.*)"|(.*?))\s*$', re.MULTILINE)


def get_title(path):
    text = path.read_text(encoding="utf-8")
    front_matter = text.split("---")[1] if text.startswith("---") else ""
    match = TITLE_RE.search(front_matter)
    if not match:
        return None
    return match.group(1) if match.group(1) is not None else match.group(2)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    too_long = []
    for path in sorted(POSTS_DIR.rglob("*.md")):
        if path.name == "_index.md":
            continue
        title = get_title(path)
        if title and len(title) > MAX_TITLE_LENGTH:
            too_long.append((path.relative_to(POSTS_DIR), title))

    if not too_long:
        print(f"OK: all post titles have at most {MAX_TITLE_LENGTH} characters.")
        return 0

    print(f"Post titles must have at most {MAX_TITLE_LENGTH} characters:")
    for path, title in too_long:
        print(f"  {len(title):>3}  {path.as_posix()}  {title}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
