"""Generate this Jekyll site's content from the MkDocs project's kanji data.

The MkDocs project is no longer checked out beside this one, and this repository
carries the generated output rather than the source data, so nothing here needs
it to build. The script is kept for the day the source data resurfaces and the
generated content has to be rebuilt from it.

`--source` is therefore required and has no default: it used to default to
`../MKDocs`, which silently became wrong when that project moved, and a default
pointing at a path that does not exist is worse than no default at all.

    python scripts/sync_from_mkdocs.py --source <path to the MkDocs project>
    python scripts/sync_from_mkdocs.py --source <path> --check   # fail if stale

It writes, all of which are committed:

    _data/levels.yml            level metadata and ordering
    _kanji/<codepoint>.html     one collection document per kanji, data in front
                                matter, cleaned stroke-order SVG as the body
    assets/search-index.json    the client-side search index

Nothing else in the repository is generated - layouts, includes, styles and the
prose pages are all hand-written.

Why .html and not .md: the body is raw SVG markup. Giving the file an .html
extension keeps Jekyll's Markdown converter away from it, and inlining the SVG
in the document body avoids a per-page `include` lookup, which matters when
there are 2,284 of them.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
LEVELS = ["n5", "n4", "n3", "n2", "n1"]

KANJI_OUT = ROOT / "_kanji"
DATA_OUT = ROOT / "_data"
INDEX_OUT = ROOT / "assets" / "search-index.json"


# ---------------------------------------------------------------------------
# stroke-order SVG
#
# Ported from the MkDocs project's scripts/gen_pages.py. KanjiVG ships a
# DOCTYPE with an internal subset, private kvg:* metadata and hard-coded black
# strokes; none of that belongs inline in a page.
# ---------------------------------------------------------------------------

_SVG_OPEN = re.compile(r"<svg\b[^>]*>", re.IGNORECASE)
_STROKE_NUMBERS = re.compile(r'(<g\b[^>]*\bid="kvg:StrokeNumbers_[^"]*")([^>]*)>', re.IGNORECASE)


def _strip_doctype(svg: str) -> str:
    """Remove a DOCTYPE including KanjiVG's `[ ... ]` internal subset.

    A naive `<!DOCTYPE.*?>` stops at the first `>` inside the subset and leaves
    the rest of the declaration behind as visible text on the page.
    """
    start = svg.find("<!DOCTYPE")
    if start == -1:
        return svg
    close = svg.find(">", start)
    if close == -1:
        return svg
    bracket = svg.find("[", start)
    if bracket != -1 and bracket < close:
        subset_end = svg.find("]>", bracket)
        end = subset_end + 2 if subset_end != -1 else close + 1
    else:
        end = close + 1
    return svg[:start] + svg[end:]


def clean_stroke_svg(path: Path) -> str | None:
    if not path.exists():
        return None
    svg = path.read_text(encoding="utf-8")
    svg = re.sub(r"<\?xml[^>]*\?>", "", svg)
    svg = _strip_doctype(svg)
    svg = re.sub(r"<!--.*?-->", "", svg, flags=re.DOTALL)
    svg = re.sub(r'\s+xmlns:kvg="[^"]*"', "", svg)
    svg = re.sub(r'\s+kvg:[\w-]+="[^"]*"', "", svg)
    # Let CSS drive the stroke colour so the diagram follows the Bootstrap theme.
    svg = re.sub(r"stroke:\s*#0{3,6}\b", "stroke:currentColor", svg, flags=re.IGNORECASE)
    # Reuse KanjiVG's own numbering group rather than computing our own, so the
    # numbers can never drift from the strokes.
    svg = _STROKE_NUMBERS.sub(r'\1 class="stroke-numbers">', svg)

    def strip_size(match: re.Match) -> str:
        tag = match.group(0)
        tag = re.sub(r'\s(width|height)="[^"]*"', "", tag)
        if "aria-hidden" not in tag:
            tag = tag[:-1] + ' aria-hidden="true" focusable="false">'
        return tag

    svg = _SVG_OPEN.sub(strip_size, svg, count=1)
    return re.sub(r"\n\s*\n+", "\n", svg).strip()


# ---------------------------------------------------------------------------
# loading
# ---------------------------------------------------------------------------


def load_kanji(source: Path) -> dict[str, list[dict]]:
    by_level: dict[str, list[dict]] = {}
    for level in LEVELS:
        entries = []
        for path in sorted((source / "data" / "kanji" / level).glob("*.yaml")):
            k = yaml.safe_load(path.read_text(encoding="utf-8"))
            readings = k.get("readings") or {}
            # YAML 1.1 resolves a bare `on:` key to the boolean True. The MkDocs
            # files quote it, but accept both rather than silently dropping
            # every on'yomi if an unquoted one ever appears.
            k["readings"] = {
                "on": readings.get("on") or readings.get(True) or [],
                "kun": readings.get("kun") or readings.get(False) or [],
            }
            k["words"] = k.get("words") or []
            k["sentences"] = k.get("sentences") or []
            entries.append(k)
        entries.sort(key=sort_key)
        by_level[level] = entries
    return by_level


def sort_key(k: dict):
    """Most common first; unranked kanji last, simplest first."""
    freq = k.get("freq")
    return (freq is None, freq if freq is not None else 0, k["strokes"], k["codepoint"])


# ---------------------------------------------------------------------------
# emitting
# ---------------------------------------------------------------------------


def yaml_block(data: dict) -> str:
    return yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=10_000).rstrip()


def kanji_document(k: dict, level: str, index: int, previous, following, svg: str | None) -> str:
    front = {
        "layout": "kanji",
        # The URL carries the character itself, matching the MkDocs site, so old
        # links keep their shape and a shared URL is readable.
        "permalink": f'/{level}/kanji/{k["char"]}/',
        "char": k["char"],
        "codepoint": k["codepoint"],
        "level": k["level"],
        "level_id": level,
        # Liquid cannot sort on a key that is sometimes nil, so the frequency
        # ordering is resolved here and stored as a plain integer.
        "sort_index": index,
        "title": f'{k["char"]} · {k["meanings"][0]}',
        "description": (
            f'JLPT {k["level"]} kanji {k["char"]} - {", ".join(k["meanings"])}. '
            "Readings, stroke order, common words and example sentences."
        ),
        "strokes": k["strokes"],
        "grade": k.get("grade"),
        "freq": k.get("freq"),
        "radical": k["radical"],
        "meanings": k["meanings"],
        "onyomi": k["readings"]["on"],
        "kunyomi": k["readings"]["kun"],
        "words": k["words"],
        "sentences": k["sentences"],
        "has_stroke": bool(svg),
    }
    if k.get("level_note"):
        front["level_note"] = k["level_note"]
    if previous:
        front["prev_char"] = previous["char"]
        front["prev_url"] = f'/{level}/kanji/{previous["char"]}/'
    if following:
        front["next_char"] = following["char"]
        front["next_url"] = f'/{level}/kanji/{following["char"]}/'

    body = svg or ""
    return f"---\n{yaml_block(front)}\n---\n{body}\n"


def search_row(k: dict) -> dict:
    """One compact search record.

    Kept deliberately small: character, level, meanings, both readings in kana
    and romaji, and the vocabulary. No example sentences - they would multiply
    the index size for terms nobody searches a kanji site by.
    """
    on = k["readings"]["on"]
    kun = k["readings"]["kun"]
    return {
        "c": k["char"],
        "u": f'/{k["level"].lower()}/kanji/{k["char"]}/',
        "l": k["level"],
        "m": k["meanings"],
        "r": [r["kana"] for r in on + kun],
        "t": [r["romaji"].replace(".", "").replace("-", "") for r in on + kun],
        "w": [w["word"] for w in k["words"]],
        "g": [w["reading"] for w in k["words"]],
        "f": k.get("freq") or 99999,
        "s": k["strokes"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        required=True,
        help="path to the MkDocs project (the directory holding data/kanji/)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="report what would change and exit non-zero, without writing",
    )
    args = parser.parse_args()

    source = Path(args.source).resolve()
    if not (source / "data" / "kanji").is_dir():
        print(f"error: no kanji data under {source}", file=sys.stderr)
        print("       pass --source with the path to the MkDocs project", file=sys.stderr)
        return 2

    print(f"source: {source}")
    by_level = load_kanji(source)
    total = sum(len(v) for v in by_level.values())
    if not total:
        print("error: found no kanji", file=sys.stderr)
        return 2

    # --- levels -----------------------------------------------------------
    levels_raw = yaml.safe_load((source / "data" / "levels.yml").read_text(encoding="utf-8"))
    levels = []
    for entry in levels_raw["levels"]:
        lid = entry["id"]
        levels.append(
            {
                "id": lid,
                "name": entry["name"],
                "order": entry["order"],
                "title": entry["title"],
                "tagline": entry["tagline"],
                "intro": " ".join(str(entry["intro"]).split()),
                "count": len(by_level[lid]),
                "totals": entry.get("totals", {}),
            }
        )
    levels.sort(key=lambda lv: lv["order"])

    stale: list[str] = []

    def write(path: Path, text: str) -> bool:
        if path.exists() and path.read_text(encoding="utf-8") == text:
            return False
        if args.check:
            stale.append(str(path.relative_to(ROOT)))
            return True
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")
        return True

    DATA_OUT.mkdir(parents=True, exist_ok=True)
    header = (
        "# GENERATED by scripts/sync_from_mkdocs.py from the MkDocs project.\n"
        "# Do not edit by hand - rerun the script instead.\n"
    )
    write(DATA_OUT / "levels.yml", header + yaml_block({"levels": levels}) + "\n")

    # --- kanji documents --------------------------------------------------
    changed = 0
    wanted: set[Path] = set()
    index_rows = []

    for level in LEVELS:
        entries = by_level[level]
        for i, k in enumerate(entries):
            previous = entries[i - 1] if i > 0 else None
            following = entries[i + 1] if i + 1 < len(entries) else None
            svg = clean_stroke_svg(source / "data" / "stroke" / f'{k["codepoint"]}.svg')
            path = KANJI_OUT / f'{k["codepoint"]}.html'
            wanted.add(path)
            if write(path, kanji_document(k, level, i, previous, following, svg)):
                changed += 1
            index_rows.append(search_row(k))

    # Drop documents for kanji that no longer exist upstream.
    removed = 0
    if KANJI_OUT.exists():
        for path in KANJI_OUT.glob("*.html"):
            if path not in wanted:
                if args.check:
                    stale.append(f"{path.relative_to(ROOT)} (orphan)")
                else:
                    path.unlink()
                removed += 1

    # --- search index -----------------------------------------------------
    index_rows.sort(key=lambda r: (r["f"], r["s"]))
    index_text = json.dumps(
        {"generated_from": "MkDocs kanji data", "count": len(index_rows), "docs": index_rows},
        ensure_ascii=False,
        separators=(",", ":"),
    )
    write(INDEX_OUT, index_text + "\n")

    if args.check:
        if stale:
            print(f"STALE: {len(stale)} file(s) differ from the MkDocs data")
            for name in stale[:20]:
                print(f"  {name}")
            if len(stale) > 20:
                print(f"  ... and {len(stale) - 20} more")
            print(f"\nRun: python scripts/sync_from_mkdocs.py --source {args.source}")
            return 1
        print(f"up to date: {total} kanji")
        return 0

    size = INDEX_OUT.stat().st_size
    print(f"kanji     : {total} ({changed} written, {removed} removed)")
    print(f"levels    : {', '.join(f'{lv['name']} {lv['count']}' for lv in levels)}")
    print(f"search    : {INDEX_OUT.relative_to(ROOT)}, {size / 1024:.0f} KB")
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
