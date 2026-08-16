---
title: About
permalink: /about/
description: >-
  How this site is put together, where its kanji data comes from, and how to
  study with it.
---

This is an independent study site for the JLPT kanji lists — N5 through N1,
built primarily for **N2**. Every one of the 2,284 kanji gets meanings, both
kinds of reading, a numbered stroke-order diagram, the vocabulary it appears in,
and example sentences using that vocabulary.

<div class="row row-cols-1 row-cols-md-3 g-3 mt-1">
  <div class="col">
    <a class="card h-100 text-decoration-none text-body card-hover" href="{{ '/about/how-to-study/' | relative_url }}">
      <div class="card-body">
        <span class="d-block fs-3 text-primary mb-2" aria-hidden="true"><i class="fa-solid fa-graduation-cap"></i></span>
        <span class="d-block fs-5 fw-semibold">How to study</span>
        <span class="d-block text-body-secondary mt-2">Getting the most out of these pages, and what changes at N2.</span>
      </div>
    </a>
  </div>
  <div class="col">
    <a class="card h-100 text-decoration-none text-body card-hover" href="{{ '/about/sources/' | relative_url }}">
      <div class="card-body">
        <span class="d-block fs-3 text-primary mb-2" aria-hidden="true"><i class="fa-solid fa-list-check"></i></span>
        <span class="d-block fs-5 fw-semibold">Sources</span>
        <span class="d-block text-body-secondary mt-2">Which references the level lists come from, and how they compare.</span>
      </div>
    </a>
  </div>
  <div class="col">
    <a class="card h-100 text-decoration-none text-body card-hover" href="{{ '/about/credits/' | relative_url }}">
      <div class="card-body">
        <span class="d-block fs-3 text-primary mb-2" aria-hidden="true"><i class="fa-solid fa-scale-balanced"></i></span>
        <span class="d-block fs-5 fw-semibold">Credits</span>
        <span class="d-block text-body-secondary mt-2">Licensing and attribution for the data and diagrams.</span>
      </div>
    </a>
  </div>
</div>

## How the site is built

The kanji data began as one YAML file per character in a companion
[MkDocs project]({{ site.mkdocs_site_url }}). `scripts/sync_from_mkdocs.py`
turned that data into the collection documents and the search index this site is
built from; both are committed here, so this site now builds on its own and
describes all 2,284 kanji without needing anything else.

This site is Jekyll with hand-written [Bootstrap](https://getbootstrap.com/)
templates, which is what makes its styling fully controllable, and it is built
and deployed by GitHub Actions.

## Search

Search covers characters, English meanings, on'yomi and kun'yomi in both kana
and romaji, and the vocabulary each kanji appears in. Press <kbd>/</kbd>
anywhere to open it.

It is deliberately not built on lunr.js. Lunr splits text on whitespace, which
Japanese does not use, so indexing Japanese with it requires a separate
tokeniser and a full inverted index. The fields worth searching here are all
short, so a direct scored match over a compact index is smaller and faster —
about 660 KB, fetched only when you first open search.
