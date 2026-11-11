#!/usr/bin/env python3
"""Copy the project photos from the Squarespace site into this repo.

Run once from the repo root, while the Squarespace site is still live:

    python3 scripts/import_squarespace_images.py            # download everything
    python3 scripts/import_squarespace_images.py --dry-run  # just list what it would do

For every page in _events/ whose front matter has `squarespace_slug: <slug>`,
it reads that page's images from the Squarespace sitemap, saves them to
assets/images/work/<event-slug>/, and writes _data/galleries/<event-slug>.yml.
The event layout shows that file as a photo gallery, and the first photo is
used as the page hero and the card image on /events.

Logo/graphic files (.png, .svg, .gif) are skipped by default because on the
old site those were sponsor and team logo carousels; pass --include-graphics
to keep them. Re-running is safe: files already downloaded are not fetched again.

Standard library only; needs Python 3.8+.
"""
import argparse
import json
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

DEFAULT_SITEMAP = "https://www.mattcoleto.com/sitemap.xml"
NS = {
    "sm": "http://www.sitemaps.org/schemas/sitemap/0.9",
    "image": "http://www.google.com/schemas/sitemap-image/1.1",
}
GRAPHIC_EXT = {".png", ".svg", ".gif"}
UA = {"User-Agent": "Mozilla/5.0 (portfolio image import)"}

REPO = Path(__file__).resolve().parent.parent


def fetch(url, timeout=60):
    if re.match(r"^https?://", url):
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read()
    return Path(url).read_bytes()  # local file, used for testing


def event_slug_map():
    """squarespace_slug -> (event slug, title) from _events/*.md front matter."""
    out = {}
    for md in sorted((REPO / "_events").glob("*.md")):
        text = md.read_text(encoding="utf-8")
        fm = re.match(r"^---\n(.*?)\n---", text, re.S)
        if not fm:
            continue
        sq = re.search(r"^squarespace_slug:\s*[\"']?([^\"'\n]+)", fm.group(1), re.M)
        title = re.search(r"^title:\s*[\"']?(.+?)[\"']?\s*$", fm.group(1), re.M)
        if sq:
            out[sq.group(1).strip()] = (md.stem, title.group(1) if title else md.stem)
    return out


def sitemap_images(xml_bytes):
    """page url -> [image urls] in sitemap order."""
    root = ET.fromstring(xml_bytes)
    pages = {}
    for url in root.findall("sm:url", NS):
        loc = url.findtext("sm:loc", default="", namespaces=NS).strip()
        imgs = [i.findtext("image:loc", default="", namespaces=NS).strip()
                for i in url.findall("image:image", NS)]
        pages[loc] = [i for i in imgs if i]
    return pages


def cover_image(page_url):
    """The page's thumbnail (Squarespace 'assetUrl'), if the JSON view offers it."""
    if not re.match(r"^https?://", page_url):
        return None
    try:
        data = json.loads(fetch(page_url.rstrip("/") + "?format=json", timeout=30))
        return (data.get("item") or {}).get("assetUrl")
    except Exception:
        return None


def clean_name(url):
    name = urllib.parse.unquote(urllib.parse.urlparse(url).path.rsplit("/", 1)[-1])
    name = re.sub(r"[^A-Za-z0-9._-]+", "-", name).strip("-").lower()
    return name or "image.jpg"


def sized(url, width):
    """Ask the CDN for a web-sized copy (originals can be 20MB+)."""
    if "squarespace-cdn.com" not in url:
        return url
    base = url.split("?", 1)[0]
    return f"{base}?format={width}w"


def yaml_str(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--sitemap", default=DEFAULT_SITEMAP, help="sitemap URL or local file")
    ap.add_argument("--width", type=int, default=1500, help="image width to download (default 1500)")
    ap.add_argument("--include-graphics", action="store_true", help="also keep .png/.svg/.gif files")
    ap.add_argument("--dry-run", action="store_true", help="list what would be downloaded and stop")
    args = ap.parse_args()

    mapping = event_slug_map()
    if not mapping:
        sys.exit("No _events/*.md files have a squarespace_slug; nothing to do.")

    pages = sitemap_images(fetch(args.sitemap))
    total = 0
    for page_url, images in pages.items():
        path = urllib.parse.urlparse(page_url).path.rstrip("/")
        m = re.match(r"^/work/([^/]+)$", path)
        if not m or m.group(1) not in mapping:
            continue
        slug, title = mapping[m.group(1)]

        cover = cover_image(page_url)
        if cover and cover.split("?")[0] not in [i.split("?")[0] for i in images]:
            images = [cover] + images

        keep, skipped = [], []
        for url in images:
            ext = Path(urllib.parse.urlparse(url).path).suffix.lower()
            (skipped if ext in GRAPHIC_EXT and not args.include_graphics else keep).append(url)

        print(f"\n{slug}: {len(keep)} photos" + (f", {len(skipped)} graphics skipped" if skipped else ""))
        for s in skipped:
            print(f"  skip  {clean_name(s)}")

        dest = REPO / "assets" / "images" / "work" / slug
        entries, seen = [], set()
        for n, url in enumerate(keep, 1):
            name = f"{n:02d}-{clean_name(url)}"
            if name in seen:
                continue
            seen.add(name)
            target = dest / name
            rel = "/" + target.relative_to(REPO).as_posix()
            entries.append(rel)
            if args.dry_run:
                print(f"  get   {name}")
                continue
            if target.exists() and target.stat().st_size > 0:
                print(f"  have  {name}")
                continue
            try:
                data = fetch(sized(url, args.width))
            except Exception as e:  # keep going; report at the end
                print(f"  FAIL  {name}: {e}")
                entries.pop()
                continue
            dest.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            total += 1
            print(f"  saved {name} ({len(data) // 1024} KB)")

        if args.dry_run or not entries:
            continue
        gal = REPO / "_data" / "galleries" / f"{slug}.yml"
        gal.parent.mkdir(parents=True, exist_ok=True)
        lines = [f"# Photos for /events/{slug}/, imported from the Squarespace page {path}",
                 "# Reorder or delete lines to change the gallery; the first photo is the hero/card image."]
        for i, rel in enumerate(entries, 1):
            lines.append(f"- src: {rel}")
            lines.append(f"  alt: {yaml_str(f'{title}, photo {i}')}")
        gal.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"  wrote {gal.relative_to(REPO)}")

    print("\nDry run, nothing downloaded." if args.dry_run else f"\nDone. {total} new files downloaded.")


if __name__ == "__main__":
    main()
