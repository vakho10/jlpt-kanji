# JLPT Kanji — Jekyll

**Live: <https://vakho10.github.io/jlpt-kanji/>**

A study site for the JLPT kanji lists — N5 through N1, built for **N2**. Every
kanji gets meanings, both readings, a numbered stroke-order diagram, the words it
appears in, and example sentences. Jekyll with hand-written
[Bootstrap 5.3](https://getbootstrap.com/) templates rather than a theme.

| N5 |  N4 |  N3 |  N2 |    N1 | total |
|---:|----:|----:|----:|------:|------:|
| 79 | 167 | 416 | 373 | 1,249 | 2,284 |

## Quick start

```bash
bundle install
bundle exec jekyll serve
```

Then open <http://127.0.0.1:4000/jlpt-kanji/> — note the `baseurl` path.

## The repository name is part of every URL

This is a GitHub *project* site, served from `https://<user>.github.io/<repo>/`.
Three lines in [`_config.yml`](_config.yml) must match the repository name, or
every link and asset 404s once deployed:

```yaml
url: https://vakho10.github.io
baseurl: /jlpt-kanji         # <- the repository name, leading slash, no trailing slash
repository: vakho10/jlpt-kanji
```

Nothing else hardcodes the prefix — internal links go through `relative_url` and
the search index stores baseurl-free paths — so a rename touches only this file.

## Generated vs hand-written

`_kanji/`, `_data/levels.yml` and `assets/search-index.json` are **generated and
committed**. They are the site's own copy of the data; neither a local build nor
CI needs anything else. Everything else — layouts, includes, styles, prose pages
— is hand-written and safe to edit.

[`scripts/sync_kanji_data.py`](scripts/sync_kanji_data.py) is what produced them,
from a directory of per-character YAML plus the KanjiVG stroke SVGs. That source
is no longer available, so the script cannot be run today — it is kept as the
record of how the generated files are structured and how they were built.

## Commands

| Command                                              | What it does                                                   |
|------------------------------------------------------|----------------------------------------------------------------|
| `bundle exec jekyll serve`                           | Live-reloading dev server                                      |
| `bundle exec jekyll build`                           | Build into `_site/`                                            |
| `python scripts/check_links.py`                      | Verify every internal link resolves — Jekyll has no `--strict` |
| `python scripts/sync_kanji_data.py --source <path>`  | Regenerate content (add `--check` to fail when stale)          |

## Deployment

Push to `main`. [`.github/workflows/deploy.yml`](.github/workflows/deploy.yml)
builds with Jekyll 4, verifies every internal link, and publishes via the
official GitHub Pages actions. Pull requests build but do not deploy.

Built by Actions rather than Pages' classic Jekyll build, which pins Jekyll 3.9
and an allowlist of plugins. **One-time setup:** *Settings → Pages → Source* must
be **GitHub Actions**.

## How a few things work

**Search** is client-side over characters, meanings, readings in kana and romaji,
and vocabulary. Press <kbd>/</kbd> or <kbd>Ctrl</kbd>+<kbd>K</kbd>. Deliberately
not lunr.js: lunr tokenises on whitespace, which Japanese lacks, so it would need
the `lunr-languages` tokeniser plus a full inverted index. A direct scored match
over a compact array is smaller and faster — 660 KB, fetched on first use.
Matching is most-literal-first (character, reading, word, meaning), kana are
folded together, and macrons are folded so `shou`, `shoo` and `shō` all find
ショウ.

**Stroke order** — each `<path>` in a KanjiVG file is one stroke in writing
order, so [`assets/js/stroke-order.js`](assets/js/stroke-order.js) animates them
with no library: dash the path as long as itself, offset it out of sight, run the
offset to zero. Time is shared by stroke length, so the pen keeps a constant
speed. Progressive enhancement — the diagram is complete before the script runs,
and the button only exists if the script works.

**Styling** is stock Bootstrap on white, with Font Awesome for icons; both
vendored under `assets/vendor/` rather than a CDN, so there is no third-party
runtime dependency. Icons are decorative and always beside a label, so each is
`aria-hidden`. [`assets/css/site.css`](assets/css/site.css) is short by design,
holding only what Bootstrap has no utility for: CJK font stacks, styling *inside*
the inlined KanjiVG SVG, `.kanji-grid` (`row-cols-*` caps at 6 columns, which
makes N1's 1,249 cards 29 screens of scrolling), a card hover state, a `:visited`
tint, and a line clamp.

Opened kanji are tinted via `:visited`, using the browser's own history — it
clears when history clears and does not follow you to another device. Browsers
restrict `:visited` to colour properties and report the *unvisited* style to
`getComputedStyle()`, so colour is the only channel available and this is the one
rule here that cannot be verified by measuring the page.

## Licensing and attribution

Font Awesome Free 7 under its own licences — icons CC BY 4.0, fonts SIL OFL 1.1,
code MIT.

Kanji readings and vocabulary derive from **KANJIDIC2** and **JMdict** (EDRDG,
CC BY-SA 4.0); example sentences from the **Tanaka corpus** (Tatoeba,
CC BY 2.0 FR); stroke-order diagrams from **KanjiVG** (CC BY-SA 3.0). Level
membership is cross-checked against [kanji.jepang.org](https://kanji.jepang.org/)
and [kanjilibrary.com](https://kanjilibrary.com/). Not affiliated with the JLPT.
