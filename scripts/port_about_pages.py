"""One-off: port the MkDocs About pages into this Jekyll site.

Converts Material's `!!! note` admonition blocks into Bootstrap alerts and
rewrites `page.md` cross-links to this site's `/about/page/` permalinks. Run
once; the result is hand-editable Markdown and is not regenerated.

    python scripts/port_about_pages.py [--source ../MKDocs]
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGES = ("how-to-study", "sources", "credits")

ADMONITION = re.compile(r'^!!! (\w+)(?: "([^"]*)")?\s*$')
BOOTSTRAP_KIND = {
    "note": "secondary",
    "info": "info",
    "tip": "success",
    "warning": "warning",
    "danger": "danger",
    "example": "secondary",
    "abstract": "info",
}


def convert_admonitions(md: str) -> str:
    lines = md.split("\n")
    out: list[str] = []
    i = 0
    while i < len(lines):
        match = ADMONITION.match(lines[i])
        if not match:
            out.append(lines[i])
            i += 1
            continue

        kind, title = match.group(1), match.group(2)
        css = BOOTSTRAP_KIND.get(kind, "secondary")
        i += 1
        body: list[str] = []
        while i < len(lines) and (lines[i].startswith("    ") or not lines[i].strip()):
            body.append(lines[i][4:] if lines[i].startswith("    ") else "")
            i += 1
        while body and not body[-1].strip():
            body.pop()

        # markdown="1" lets kramdown keep processing the block's contents.
        out.append(f'<div class="alert alert-{css}" markdown="1">')
        if title:
            out.append(f"**{title}**")
            out.append("")
        out.extend(body)
        out.append("</div>")
        out.append("")
    return "\n".join(out)


def front_matter_value(front: str, key: str) -> str:
    folded = re.search(rf"^{key}:\s*>-\s*\n((?:[ \t]{{2,}}.*\n)+)", front, re.M)
    if folded:
        return " ".join(folded.group(1).split())
    plain = re.search(rf"^{key}:\s*(.+)$", front, re.M)
    return plain.group(1).strip().strip('"') if plain else ""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default=str(ROOT.parent / "MKDocs"))
    args = parser.parse_args()

    source = Path(args.source).resolve() / "docs" / "about"
    if not source.is_dir():
        print(f"error: no About pages at {source}", file=sys.stderr)
        return 2

    out_dir = ROOT / "about"
    out_dir.mkdir(parents=True, exist_ok=True)

    for name in PAGES:
        raw = (source / f"{name}.md").read_text(encoding="utf-8")
        _, _, rest = raw.partition("---\n")
        front, _, body = rest.partition("---\n")

        title = front_matter_value(front, "title") or name.replace("-", " ").title()
        description = front_matter_value(front, "description")

        # The layout renders the <h1>, so drop the one in the body. re.M is
        # required: the body starts with a newline, so an unanchored `^` only
        # ever matches position 0 and the heading survives.
        body = re.sub(r"^#\s+.*\n", "", body, count=1, flags=re.M)
        body = convert_admonitions(body)
        # sources.md -> /about/sources/, through relative_url. A bare absolute
        # path would resolve locally and then 404 on the deployed project site,
        # which is served from a /<repo>/ subpath.
        body = re.sub(
            r"\]\((?!https?:|/)([\w-]+)\.md\)",
            r"]({{ '/about/\1/' | relative_url }})",
            body,
        )

        header = (
            "---\n"
            f"title: {title}\n"
            f"permalink: /about/{name}/\n"
            f"description: >-\n  {description}\n"
            "---\n\n"
        )
        (out_dir / f"{name}.md").write_text(header + body.strip() + "\n", encoding="utf-8", newline="\n")
        print(f"wrote about/{name}.md")

    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
