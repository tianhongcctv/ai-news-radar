#!/usr/bin/env python3
"""Remove known-bad RSS feeds from a local OPML file before fetching."""

from __future__ import annotations

import argparse
import xml.etree.ElementTree as ET
from pathlib import Path

BAD_FEEDS = {
    "https://ai.meta.com/blog/rss/",
    "https://oecd.ai/en/rss",
    "https://openai.com/news/research/rss.xml",
}


def prune_bad_outlines(parent: ET.Element) -> int:
    removed = 0
    for child in list(parent):
        xml_url = (child.attrib.get("xmlUrl") or "").strip()
        if xml_url in BAD_FEEDS:
            parent.remove(child)
            removed += 1
            continue
        removed += prune_bad_outlines(child)
    return removed


def main() -> int:
    parser = argparse.ArgumentParser(description="Clean known-bad RSS feeds from OPML")
    parser.add_argument("opml", help="Path to OPML file")
    args = parser.parse_args()

    path = Path(args.opml)
    if not path.exists():
        print(f"OPML not found: {path}")
        return 0

    tree = ET.parse(path)
    root = tree.getroot()
    removed = prune_bad_outlines(root)
    tree.write(path, encoding="utf-8", xml_declaration=True)
    print(f"Removed {removed} known-bad OPML feed(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
