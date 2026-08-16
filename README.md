# JLPT Kanji — Jekyll

A study site for the JLPT kanji lists — N5 through N1, built for **N2**. Jekyll
with hand-written [Bootstrap 5.3](https://getbootstrap.com/) templates, so the
styling is fully under our control rather than a theme's.

All **2,284** kanji are covered:

| N5 | N4 | N3 | N2 | N1 | total |
| -: | -: | -: | -: | -: | ----: |
| 79 | 167 | 416 | 373 | 1,249 | 2,284 |

This is a sibling of the [MkDocs project](../MKDocs), which holds the kanji data
and remains the single source of truth. Both sites describe the same characters.

## Quick start

```bash
bundle install
bundle exec jekyll serve
```

Then open <http://127.0.0.1:4000/JLPT-Jekyll/> — note the `baseurl` path.

## Set your repository name before deploying

This is a GitHub *project* site, served from `https://<user>.github.io/<repo>/`.
Two lines in [`_config.yml`](_config.yml) must match the repository name, or
every link and asset 404s once deployed:

```yaml
url: https://vakho10.github.io
baseurl: /JLPT-Jekyll        # <- the repository name, leading slash, no trailing slash
```

The MkDocs site already owns the `JLPT` repository, so this one needs a
different name.

## Where the content comes from

`_kanji/`, `_data/levels.yml` and `assets/search-index.json` are **generated**
and committed. The two projects are separate repositories, so GitHub Actions
cannot reach the MkDocs data at build time — it has to be vendored in.

```bash
python scripts/sync_from_mkdocs.py            # refresh from ../MKDocs
python scripts/sync_from_mkdocs.py --check    # non-zero if anything is stale
```

Everything else — layouts, includes, styles, the prose pages — is hand-written
and safe to edit.

## Stroke-order animation

Every `<path>` in a KanjiVG file is one stroke in writing order, so
[`assets/js/stroke-order.js`](assets/js/stroke-order.js) can draw them in
sequence with no library: give each path a dash pattern as long as itself,
offset it out of sight, then run the offset to zero. Each stroke gets its share
of the time budget by length, so the pen keeps a constant speed rather than
racing through the long strokes.

Progressive enhancement — the diagram is complete before the script runs and
stays complete if it never does. The button is created by JavaScript, so it
never appears unless it works.

## Search

Client-side, covering characters, English meanings, on'yomi and kun'yomi in both
kana and romaji, and the vocabulary each kanji appears in. Press <kbd>/</kbd> or
<kbd>Ctrl</kbd>+<kbd>K</kbd> anywhere.

It deliberately does **not** use lunr.js. Lunr tokenises on whitespace, which
Japanese does not have, so indexing Japanese with it needs the `lunr-languages`
tokeniser plus a full inverted index — that is why the MkDocs site's index is
5.3 MB. Every field worth searching here is short and enumerable, so a direct
scored match over a compact array is smaller and faster: **660 KB**, fetched
only when search is first opened.

Matching is ranked most-literal-first — exact character, then a reading, then a
word, then an English meaning — with ties broken towards the more common kanji.
Hiragana and katakana are folded together, and Hepburn macrons are folded so
`shou`, `shoo` and `shō` all find ショウ.

## Commands

| Command | What it does |
| --- | --- |
| `bundle exec jekyll serve` | Live-reloading dev server |
| `bundle exec jekyll build` | Build into `_site/` (~15s for 2,290 pages) |
| `python scripts/check_links.py` | Verify every internal link resolves — Jekyll has no `--strict` |
| `python scripts/sync_from_mkdocs.py` | Regenerate content from the MkDocs data |
| `python scripts/port_about_pages.py` | One-off: re-import the About pages |

## Deployment

Push to `main`. [`.github/workflows/deploy.yml`](.github/workflows/deploy.yml)
builds with Jekyll 4, checks every internal link, and publishes via the official
GitHub Pages actions. Pull requests build but do not deploy.

Built by Actions rather than GitHub Pages' classic Jekyll build, which pins
Jekyll 3.9 and an allowlist of plugins.

**One-time setup:** in the repository's *Settings → Pages*, set **Source** to
**GitHub Actions**.

## Styling

Stock Bootstrap on a white background, with Font Awesome for icons. No theme
switcher, no `data-bs-theme` attribute, no recoloured components — the default
light palette exactly as Bootstrap ships it.

Both libraries are **vendored** under `assets/vendor/`, not loaded from a CDN, so
the site has no third-party runtime dependency and builds offline. Font Awesome
Free 7 carries only what is used: the core and solid stylesheets and the solid
webfont, about 190 KB. Every icon is `fa-solid`; adding one from another style
means vendoring that style's CSS and webfont too.

Icons are decorative and always sit beside their own label, so each carries
`aria-hidden="true"` and nothing depends on an icon alone to be understood.

The palette is deliberately narrow, so nothing looks improvised:

- **Buttons** — `btn-primary` for the action on a page, `btn-outline-primary`
  for everything else. No other variants.
- **Badges** — `text-bg-primary` for a kanji's own JLPT level,
  `text-bg-secondary` for anything secondary.
- **Surfaces** — white. Cards are plain `card`; no tinted section backgrounds,
  no coloured accent borders.
- **Text** — default body colour, with `text-body-secondary` for anything
  subordinate. Headings are not coloured.
- **Alerts** — `alert-warning` for a caveat on a kanji, `alert-secondary` for a
  note on a level page.

[`assets/css/site.css`](assets/css/site.css) is **154 lines**, and holds only the
six things Bootstrap has no utility for:

| Rule | Why it cannot be a utility class |
| --- | --- |
| `:lang(ja)`, `.jp-serif` | CJK font stacks; also disables `palt` so kana keep monospaced advances |
| `.stroke-diagram svg …` | styles elements *inside* the inlined KanjiVG SVG, which utilities cannot reach |
| `.kanji-grid` | `row-cols-*` caps at 6 columns; N1's 1,249 cards are 29 screens at 6 across against 18.6 at 10 |
| `.card-hover` | Bootstrap gives cards no hover state, so a clickable card looks identical to a static one |
| `.kanji-grid a:visited` | Bootstrap ships no `:visited` rule at all, and browsers allow only colour properties here |
| `.clamp-2` | Bootstrap has no line-clamp utility, and one long gloss otherwise makes its whole row taller |

Kanji already opened are tinted with `--bs-success-bg-subtle` via `:visited`.
Browsers restrict `:visited` to a short list of colour properties — colour,
background, border/outline colour, SVG fill and stroke — so a page cannot read
your history back out. That means no icon or badge is possible, colour is the
only available channel, and `getComputedStyle()` deliberately reports the
*unvisited* style, so this is the one rule here that cannot be checked by
measuring the page. The tint comes from browser history: it clears when history
clears and does not follow you to another device.

`.card-hover` goes on any card that is a link — the level cards on the home page,
the kanji cards on a level page, and the three About cards. It lifts the card 2px,
deepens the shadow and turns the border `--bs-primary`. It matches on
`:focus-within` as well as `:hover` and `:focus-visible`, because the home page's
level card is a `<div>` whose link is a `.stretched-link`: the card itself never
takes focus, so a keyboard user would otherwise get no feedback. The whole effect
is dropped under `prefers-reduced-motion: reduce`.

Everything else — cards, badges, buttons, spacing, blockquotes, and the search
result rows' hover and focus states — is stock Bootstrap.

## Licensing and attribution

Font Awesome Free 7 is used under its own licences — icons CC BY 4.0, fonts
SIL OFL 1.1, code MIT.

Kanji readings and vocabulary derive from **KANJIDIC2** and **JMdict** (EDRDG,
CC BY-SA 4.0); example sentences from the **Tanaka corpus** (Tatoeba,
CC BY 2.0 FR); stroke-order diagrams from **KanjiVG** (CC BY-SA 3.0). Level
membership is cross-checked against [kanji.jepang.org](https://kanji.jepang.org/)
and [kanjilibrary.com](https://kanjilibrary.com/). Not affiliated with the JLPT.
