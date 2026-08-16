/* Stroke-order animation for the inlined KanjiVG diagram.
 *
 * Every <path> in a KanjiVG file is one stroke, stored in writing order, which
 * is what makes this possible without any library: give each path a dash
 * pattern as long as the path itself, offset it out of sight, then run the
 * offset back to zero. The stroke draws itself, in order.
 *
 * Duration is shared out by each stroke's share of the total length, so the pen
 * keeps a constant speed instead of racing through the long strokes and
 * crawling through the short ones. Deriving it from the ratio rather than from
 * an absolute pixel rate also keeps the timing right whatever viewBox scale a
 * file happens to use.
 *
 * Progressive enhancement throughout: the diagram is already complete when this
 * runs and stays complete if it never does. Nothing is hidden and no control is
 * added until we know the animation can actually work, so a reader without
 * JavaScript sees exactly what they saw before.
 */
(function () {
  'use strict';

  var AVERAGE_STROKE_MS = 320;   // target pace, per stroke
  var MIN_STROKE_MS = 110;
  var GAP_MS = 70;               // pen lift between strokes

  var figures = document.querySelectorAll('.stroke-diagram');
  if (!figures.length) return;

  Array.prototype.forEach.call(figures, function (figure) {
    var svg = figure.querySelector('svg');
    if (!svg) return;

    var paths = Array.prototype.slice.call(svg.querySelectorAll('path'));
    // getTotalLength is the whole mechanism; without it there is nothing to do.
    if (!paths.length || typeof paths[0].getTotalLength !== 'function') return;
    if (typeof paths[0].animate !== 'function') return;   // no Web Animations API

    var numbers = svg.querySelector('.stroke-numbers');
    var lengths = paths.map(function (p) { return p.getTotalLength(); });
    var totalLength = lengths.reduce(function (a, b) { return a + b; }, 0);
    if (!totalLength) return;

    var budget = AVERAGE_STROKE_MS * paths.length;
    var running = [];

    function stop() {
      running.forEach(function (a) { a.cancel(); });
      running = [];
    }

    /* Put the SVG back exactly as it was served, so the resting state is the
       plain static diagram rather than whatever the animation left behind. */
    function reset() {
      stop();
      paths.forEach(function (p) {
        p.style.strokeDasharray = '';
        p.style.strokeDashoffset = '';
      });
      if (numbers) numbers.style.opacity = '';
    }

    function play() {
      stop();
      // The numbers label finished strokes, so they only make sense at the end.
      if (numbers) numbers.style.opacity = '0';

      var delay = 0;
      running = paths.map(function (path, i) {
        var length = lengths[i];
        var duration = Math.max(MIN_STROKE_MS, (length / totalLength) * budget);

        path.style.strokeDasharray = length + ' ' + length;
        path.style.strokeDashoffset = length;

        var animation = path.animate(
          [{ strokeDashoffset: length }, { strokeDashoffset: 0 }],
          { duration: duration, delay: delay, easing: 'ease-in-out', fill: 'forwards' }
        );
        delay += duration + GAP_MS;
        return animation;
      });

      var last = running[running.length - 1];
      last.finished.then(function () {
        /* Just clear the inline value - deliberately no fade back in.
           Any animation restoring this would *own* the property while it runs,
           so a cancel, a backgrounded tab with no frames, or an interrupted
           replay would leave the numbers invisible for good. Restoring a
           default is not a job to hand to an animation. */
        if (numbers) numbers.style.opacity = '';
        paths.forEach(function (p) {
          p.style.strokeDasharray = '';
          p.style.strokeDashoffset = '';
        });
        setLabel('idle');
      }).catch(function () {
        // Cancelled by a reset. Put the control back so it is never stranded.
        setLabel('idle');
      });

      setLabel('drawing');
    }

    var button = document.createElement('button');
    button.type = 'button';
    button.className = 'btn btn-outline-primary btn-sm mt-3 d-block mx-auto';

    /* Driven by the animation's own completion, never by a timer. A timer set
       from the planned duration goes wrong the moment reality differs from the
       plan - an early finish, a cancel, a tab that stopped getting frames - and
       leaves the button disabled with nothing to re-enable it. */
    function setLabel(state) {
      var drawing = state === 'drawing';
      button.disabled = drawing;
      button.innerHTML = drawing
        ? '<i class="fa-solid fa-pen-nib me-2" aria-hidden="true"></i>Drawing…'
        : '<i class="fa-solid fa-rotate-right me-2" aria-hidden="true"></i>Replay strokes';
    }

    button.innerHTML = '<i class="fa-solid fa-play me-2" aria-hidden="true"></i>Animate strokes';
    button.addEventListener('click', function () {
      reset();
      play();
    });

    figure.appendChild(button);
  });
})();
