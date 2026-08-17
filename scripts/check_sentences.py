"""Check the example sentences in _kanji/ for structural breakage.

_kanji/ is hand-maintained source, so nothing but this stands between a typo and
a shipped page. Structural faults fail the build:

  * a sentence tagged with a word that is not in the page's word list
  * a sentence that does not actually contain the word it is tagged with
  * a reading containing kanji (it is meant to be the kana rendering)
  * romaji containing Japanese script
  * a missing translation

Two further things are reported but do NOT fail, because existing content
already breaks them in bulk and neither is a defect on its own:

  * `--strict` also fails on kanji harder than the page's own level. The site
    aims for this, but 1,237 sentences inherited from the corpus break it, so
    it cannot gate a build until they are dealt with. Kanji belonging to the
    target word itself are always exempt: a word like 綱領 or 小選挙区 carries
    a harder character in the word being taught, so no sentence using it can
    comply.
  * coverage - words that have no sentence yet. There are thousands; that is a
    backlog, not an error.

    python scripts/check_sentences.py                # structural check
    python scripts/check_sentences.py --level n2     # one level only
    python scripts/check_sentences.py --strict       # also enforce the level rule
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
KANJI_DIR = ROOT / "_kanji"

# Higher number = easier. A sentence may use kanji at or below its page's level.
ORDER = {"n5": 5, "n4": 4, "n3": 3, "n2": 2, "n1": 1}

KANJI = re.compile(r"[一-鿿]")
JAPANESE = re.compile(r"[぀-ゟ゠-ヿ一-鿿]")


def load() -> dict[str, dict]:
    docs = {}
    for path in sorted(KANJI_DIR.glob("*.html")):
        head = path.read_text(encoding="utf-8").split("---")[1]
        docs[path.name] = yaml.safe_load(head)
    return docs


def stem(word: str) -> str:
    """The part of a word that survives conjugation.

    A sentence for 設ける contains 設けました, never the dictionary form, so
    matching on the whole word would reject correct Japanese. Everything up to
    and including the last kanji is stable; the okurigana after it is not.
    """
    positions = [i for i, ch in enumerate(word) if KANJI.match(ch)]
    return word[: positions[-1] + 1] if positions else word


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--level", help="only check one level, e.g. n2")
    parser.add_argument("--strict", action="store_true", help="also fail on the level rule")
    args = parser.parse_args()

    docs = load()
    if not docs:
        print("error: no documents under _kanji/", file=sys.stderr)
        return 2
    level_of = {d["char"]: d["level_id"] for d in docs.values()}

    broken: list[str] = []
    too_hard: list[str] = []
    uncovered = 0
    checked = 0

    for fm in docs.values():
        if args.level and fm["level_id"] != args.level:
            continue
        page = ORDER[fm["level_id"]]
        words = {w["word"] for w in (fm.get("words") or [])}
        tagged = set()

        for s in fm.get("sentences") or []:
            checked += 1
            word = s.get("word") or ""
            tagged.add(word)
            where = f'{fm["char"]} ({fm["level_id"]}) "{word}"'
            ja = s.get("ja", "")

            if word and word not in words:
                broken.append(f"{where}: tagged with a word that is not in the word list")
            if word and stem(word) not in ja:
                broken.append(f"{where}: the sentence does not contain this word")
            if KANJI.search(s.get("reading", "")):
                broken.append(f"{where}: reading contains kanji")
            if JAPANESE.search(s.get("romaji", "")):
                broken.append(f"{where}: romaji contains Japanese script")
            if not s.get("translation"):
                broken.append(f"{where}: no translation")

            for ch in ja:
                if not KANJI.match(ch) or ch in word:
                    continue
                lv = level_of.get(ch)
                if lv is None:
                    too_hard.append(f"{where}: {ch} is in no JLPT level")
                elif ORDER[lv] < page:
                    too_hard.append(f"{where}: {ch} is {lv.upper()}, above {fm['level_id'].upper()}")

        uncovered += len(words - tagged)

    scope = f" at {args.level}" if args.level else ""
    print(f"checked {checked:,} sentences{scope}")
    print(f"  structural faults        : {len(broken)}")
    print(f"  above the page's level   : {len(too_hard)}{' (enforced)' if args.strict else ''}")
    print(f"  words with no sentence   : {uncovered:,}")

    for item in broken[:40]:
        print(f"    {item}", file=sys.stderr)
    if args.strict:
        for item in too_hard[:40]:
            print(f"    {item}", file=sys.stderr)

    if broken:
        return 1
    if args.strict and too_hard:
        return 1
    print("ok")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
