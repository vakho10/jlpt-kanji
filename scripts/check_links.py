"""Verify every internal link and asset reference in the built site resolves.

Jekyll has no equivalent of `mkdocs build --strict`, so a mistyped permalink or
a renamed page ships silently. This walks _site/, resolves every internal href
and src against the output tree, and fails if anything is missing.

    python scripts/check_links.py            # after `bundle exec jekyll build`
    python scripts/check_links.py --site _site --base /jlpt-kanji

Exit code 0 = every link resolves, 1 = something is broken.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urljoin, urlparse

ROOT = Path(__file__).resolve().parent.parent

ATTRS = {"a": "href", "link": "href", "img": "src", "script": "src", "source": "src", "use": "href"}
EXTERNAL = re.compile(r"^(?:[a-z][a-z0-9+.-]*:|//)", re.I)


class Refs(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.refs: list[tuple[str, str]] = []

    def handle_starttag(self, tag, attrs):
        wanted = ATTRS.get(tag)
        if not wanted:
            return
        for name, value in attrs:
            if name == wanted and value:
                self.refs.append((tag, value))


def load_baseurl(site_root: Path) -> str:
    config = ROOT / "_config.yml"
    if config.exists():
        # Stop at an inline `#` comment - `baseurl: /jlpt-kanji  # the repo name`
        # is valid YAML, and swallowing the comment would make every path here
        # look like it was missing the baseurl.
        match = re.search(r"^baseurl:\s*([^#\r\n]*)", config.read_text(encoding="utf-8"), re.M)
        if match:
            return match.group(1).strip().strip('"').strip("'")
    return ""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", default=str(ROOT / "_site"))
    parser.add_argument("--base", default=None, help="baseurl (default: read from _config.yml)")
    args = parser.parse_args()

    site = Path(args.site).resolve()
    if not site.is_dir():
        print(f"error: no built site at {site} - run `bundle exec jekyll build` first", file=sys.stderr)
        return 2

    base = args.base if args.base is not None else load_baseurl(site)
    base = "/" + base.strip("/") if base.strip("/") else ""

    pages = sorted(site.rglob("*.html"))
    print(f"checking {len(pages):,} pages (baseurl {base or '(none)'}) ...")

    broken: dict[str, set[str]] = defaultdict(set)
    checked = 0

    for page in pages:
        # The URL this page is served at, so relative links resolve correctly.
        rel = page.relative_to(site).as_posix()
        page_url = "/" + (rel[: -len("index.html")] if rel.endswith("index.html") else rel)

        parser_ = Refs()
        try:
            parser_.feed(page.read_text(encoding="utf-8", errors="replace"))
        except Exception as exc:  # noqa: BLE001 - keep going, report at the end
            broken[str(page.relative_to(site))].add(f"(could not parse: {exc})")
            continue

        for _tag, raw in parser_.refs:
            value = raw.strip()
            if not value or value.startswith("#") or EXTERNAL.match(value) or value.startswith("data:"):
                continue

            target = urljoin(page_url, value)
            path = unquote(urlparse(target).path)
            checked += 1

            if base and path.startswith(base + "/"):
                path = path[len(base):]
            elif base and path == base:
                path = "/"
            elif base and not path.startswith(base):
                # An absolute path that forgets the baseurl 404s once deployed,
                # even though it may resolve locally.
                broken[str(page.relative_to(site))].add(f"{raw}  (missing baseurl {base})")
                continue

            candidate = site / path.lstrip("/")
            if candidate.is_dir():
                candidate = candidate / "index.html"
            if not candidate.exists():
                broken[str(page.relative_to(site))].add(raw)

    if broken:
        total = sum(len(v) for v in broken.values())
        print(f"\nBROKEN: {total} reference(s) across {len(broken)} page(s)\n", file=sys.stderr)
        for page in sorted(broken)[:40]:
            print(f"  {page}", file=sys.stderr)
            for ref in sorted(broken[page])[:10]:
                print(f"      -> {ref}", file=sys.stderr)
        if len(broken) > 40:
            print(f"  ... and {len(broken) - 40} more pages", file=sys.stderr)
        return 1

    print(f"ok: {checked:,} internal references across {len(pages):,} pages all resolve")
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
