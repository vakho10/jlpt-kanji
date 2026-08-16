/* Client-side kanji search.
 *
 * Deliberately not lunr. Lunr tokenises on whitespace, which Japanese does not
 * have, so it needs the lunr-languages Japanese tokeniser and a full inverted
 * index to work at all - that is what made the MkDocs site's index 5.3 MB. The
 * fields worth searching here are all short and enumerable (a character, a few
 * meanings, a handful of readings and words), so a direct scored match over a
 * compact JSON array is smaller, faster and handles CJK correctly.
 *
 * The index is fetched on first use, not on page load.
 */
(function () {
    'use strict';

    var indexUrl = document.querySelector('meta[name="jlpt:search-index"]');
    var baseMeta = document.querySelector('meta[name="jlpt:baseurl"]');
    if (!indexUrl) return;
    indexUrl = indexUrl.getAttribute('content');
    var baseurl = baseMeta ? baseMeta.getAttribute('content') || '' : '';

    var input = document.getElementById('searchInput');
    var results = document.getElementById('searchResults');
    var status = document.getElementById('searchStatus');
    var modalEl = document.getElementById('searchModal');
    if (!input || !results || !status || !modalEl) return;

    var docs = null;
    var loading = null;
    var MAX_RESULTS = 40;

    // --- kana folding --------------------------------------------------------
    // Readings are stored in their own script; a reader typing hiragana should
    // still find an on'yomi recorded in katakana, so both fold to katakana.
    function toKatakana(s) {
        var out = '';
        for (var i = 0; i < s.length; i++) {
            var c = s.charCodeAt(i);
            out += (c >= 0x3041 && c <= 0x3096) ? String.fromCharCode(c + 0x60) : s[i];
        }
        return out;
    }

    // Romaji is stored in Hepburn with macrons; almost nobody types those, so
    // strip diacritics and accept the doubled-vowel spelling as well.
    function foldRomaji(s) {
        return s
            .toLowerCase()
            .normalize('NFD').replace(/[̀-ͯ]/g, '')
            .replace(/[^a-z0-9]/g, '');
    }

    function expandRomaji(s) {
        // "shou" and "shoo" both stand in for "shō" once the macron is stripped.
        return foldRomaji(s).replace(/ou|oo/g, 'o').replace(/uu/g, 'u').replace(/aa/g, 'a');
    }

    function load() {
        if (docs) return Promise.resolve(docs);
        if (loading) return loading;
        status.textContent = 'Loading index…';
        loading = fetch(indexUrl, {credentials: 'same-origin'})
            .then(function (r) {
                if (!r.ok) throw new Error('HTTP ' + r.status);
                return r.json();
            })
            .then(function (data) {
                docs = (data.docs || []).map(function (d) {
                    return {
                        c: d.c,
                        u: d.u,
                        l: d.l,
                        m: d.m || [],
                        r: d.r || [],
                        t: d.t || [],
                        w: d.w || [],
                        g: d.g || [],
                        f: d.f,
                        _m: (d.m || []).join(' ').toLowerCase(),
                        _r: (d.r || []).map(toKatakana),
                        _t: (d.t || []).map(expandRomaji),
                        _w: (d.w || []).join(' '),
                        _g: (d.g || []).map(toKatakana).join(' ')
                    };
                });
                status.textContent = '';
                return docs;
            })
            .catch(function (err) {
                status.textContent = 'Could not load the search index (' + err.message + ').';
                loading = null;
                throw err;
            });
        return loading;
    }

    /* Scoring, highest first. The intent is that the most literal interpretation
     * of what was typed wins: the character itself, then a reading, then a word,
     * then an English meaning. */
    function score(doc, raw) {
        var q = raw.trim();
        if (!q) return 0;
        var lower = q.toLowerCase();
        var kata = toKatakana(q);
        var rom = expandRomaji(q);
        var best = 0;

        if (doc.c === q) return 1000;                       // the exact character
        if (doc._w === q || doc.w.indexOf(q) !== -1) best = Math.max(best, 700);
        if (q.length > 1 && doc._w.indexOf(q) !== -1) best = Math.max(best, 520);

        for (var i = 0; i < doc._r.length; i++) {
            if (doc._r[i] === kata) {
                best = Math.max(best, 600);
                break;
            }
            if (kata.length > 1 && doc._r[i].indexOf(kata) === 0) best = Math.max(best, 460);
        }
        if (rom) {
            for (var j = 0; j < doc._t.length; j++) {
                if (doc._t[j] === rom) {
                    best = Math.max(best, 580);
                    break;
                }
                if (rom.length > 1 && doc._t[j].indexOf(rom) === 0) best = Math.max(best, 440);
            }
        }

        for (var k = 0; k < doc.m.length; k++) {
            var meaning = doc.m[k].toLowerCase();
            if (meaning === lower) {
                best = Math.max(best, 500);
                break;
            }
            if (meaning.indexOf(lower) === 0) best = Math.max(best, 380);
            else if (lower.length > 2 && meaning.indexOf(lower) !== -1) best = Math.max(best, 260);
        }
        if (best === 0 && lower.length > 2 && doc._m.indexOf(lower) !== -1) best = 200;
        if (best === 0 && doc._g.indexOf(kata) !== -1 && kata.length > 1) best = 180;

        // Break ties towards the more common kanji, which is what a learner wants.
        return best === 0 ? 0 : best * 1000 + Math.max(0, 3000 - (doc.f || 99999) / 40);
    }

    function escapeHtml(s) {
        return String(s).replace(/[&<>"']/g, function (c) {
            return {'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c];
        });
    }

    function render(matches, query) {
        if (!query.trim()) {
            results.innerHTML = '';
            status.textContent = '';
            return;
        }
        if (!matches.length) {
            results.innerHTML = '';
            status.textContent = 'No kanji matches “' + query + '”.';
            return;
        }
        status.textContent =
            matches.length >= MAX_RESULTS
                ? 'Showing the first ' + MAX_RESULTS + ' matches.'
                : matches.length + (matches.length === 1 ? ' match.' : ' matches.');

        // list-group-item-action carries the hover and focus styling, so the result
        // rows need no CSS of their own.
        var html = matches.map(function (d) {
            return (
                '<a class="list-group-item list-group-item-action d-flex align-items-center gap-3" ' +
                'role="option" href="' + baseurl + escapeHtml(d.u) + '">' +
                '<span class="fs-3 lh-1 text-center flex-shrink-0 jp-serif" style="width:2.5rem" lang="ja">' +
                escapeHtml(d.c) + '</span>' +
                '<span class="flex-grow-1" style="min-width:0">' +
                '<span class="d-block fw-semibold">' + escapeHtml(d.m.slice(0, 3).join(', ')) + '</span>' +
                '<span class="d-block text-body-secondary" lang="ja">' +
                escapeHtml(d.r.slice(0, 4).join('・')) + '</span>' +
                '</span>' +
                '<span class="badge text-bg-primary">' + escapeHtml(d.l) + '</span>' +
                '</a>'
            );
        }).join('');
        results.innerHTML = html;
    }

    function run() {
        var query = input.value;
        if (!query.trim()) {
            render([], query);
            return;
        }
        load().then(function (all) {
            var scored = [];
            for (var i = 0; i < all.length; i++) {
                var s = score(all[i], query);
                if (s > 0) scored.push({s: s, d: all[i]});
            }
            scored.sort(function (a, b) {
                return b.s - a.s;
            });
            render(scored.slice(0, MAX_RESULTS).map(function (x) {
                return x.d;
            }), query);
        }).catch(function () { /* status already shows the error */
        });
    }

    var timer = null;
    input.addEventListener('input', function () {
        clearTimeout(timer);
        timer = setTimeout(run, 90);
    });

    // Warm the index as soon as the dialog opens, and focus the field.
    modalEl.addEventListener('shown.bs.modal', function () {
        input.focus();
        input.select();
        load().catch(function () {
        });
    });

    // Arrow keys walk the results; Enter follows the highlighted one.
    input.addEventListener('keydown', function (e) {
        var hits = results.querySelectorAll('.list-group-item-action');
        if (!hits.length) return;
        var current = document.activeElement;
        var idx = Array.prototype.indexOf.call(hits, current);
        if (e.key === 'ArrowDown') {
            e.preventDefault();
            hits[Math.min(idx + 1, hits.length - 1)] === undefined ? hits[0].focus() : hits[idx + 1 < hits.length ? idx + 1 : 0].focus();
        } else if (e.key === 'Enter' && idx === -1) {
            e.preventDefault();
            hits[0].click();
        }
    });
    results.addEventListener('keydown', function (e) {
        var hits = Array.prototype.slice.call(results.querySelectorAll('.list-group-item-action'));
        var idx = hits.indexOf(document.activeElement);
        if (e.key === 'ArrowDown') {
            e.preventDefault();
            (hits[idx + 1] || hits[0]).focus();
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            if (idx <= 0) input.focus(); else hits[idx - 1].focus();
        }
    });

    // "/" opens search from anywhere, the way the MkDocs site did.
    document.addEventListener('keydown', function (e) {
        var tag = (e.target.tagName || '').toLowerCase();
        if (tag === 'input' || tag === 'textarea' || e.target.isContentEditable) return;
        var isSlash = e.key === '/';
        var isCmdK = (e.key === 'k' || e.key === 'K') && (e.metaKey || e.ctrlKey);
        if (!isSlash && !isCmdK) return;
        e.preventDefault();
        if (window.bootstrap && window.bootstrap.Modal) {
            window.bootstrap.Modal.getOrCreateInstance(modalEl).show();
        }
    });

})();
