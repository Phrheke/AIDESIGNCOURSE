const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
const pad = n => String(n).padStart(2, '0');
const fmt = s => `${Math.floor(s / 60)}:${pad(Math.round(s % 60))}`;

// ---------- Raw vs edited wipe ----------
const ba = document.querySelector('[data-ba]');
const range = ba?.querySelector('.ba-range');
let wipeTouched = false;
function setWipe(v) {
  ba.style.setProperty('--pos', `${v}%`);
  ba.classList.toggle('at-start', v <= 4);
  ba.classList.toggle('at-end', v >= 96);
}
function animateWipe(to, ms = 600) {
  const from = parseFloat(range.value);
  if (reduceMotion) { range.value = to; setWipe(to); return; }
  const start = performance.now();
  const step = now => {
    const t = Math.min(1, Math.max(0, now - start) / ms);
    const e = 1 - Math.pow(1 - t, 3);
    const v = from + (to - from) * e;
    range.value = Math.round(v);
    setWipe(v.toFixed(1));
    if (t < 1) requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
}
if (ba) {
  range.addEventListener('input', () => { wipeTouched = true; setWipe(range.value); });
  // Pointer drags map straight to the cursor position (the range input handles keyboard and screen readers).
  const fromPointer = e => {
    const r = ba.getBoundingClientRect();
    const v = Math.max(0, Math.min(100, ((e.clientX - r.left) / r.width) * 100));
    range.value = Math.round(v);
    setWipe(v.toFixed(1));
  };
  ba.addEventListener('dragstart', e => e.preventDefault());
  ba.addEventListener('pointerdown', e => {
    if (e.pointerType === 'mouse') e.preventDefault();
    wipeTouched = true;
    ba.setPointerCapture(e.pointerId);
    ba.classList.add('is-dragging');
    fromPointer(e);
  });
  ba.addEventListener('pointermove', e => { if (ba.classList.contains('is-dragging')) fromPointer(e); });
  const stopDrag = () => ba.classList.remove('is-dragging');
  ba.addEventListener('pointerup', stopDrag);
  ba.addEventListener('pointercancel', stopDrag);

  // One sweep when it first comes into view, so people see the line moves.
  if (!reduceMotion && 'IntersectionObserver' in window) {
    const io = new IntersectionObserver(([entry]) => {
      if (!entry.isIntersecting) return;
      io.disconnect();
      setTimeout(() => {
        if (wipeTouched) return;
        animateWipe(28, 500);
        setTimeout(() => { if (!wipeTouched) animateWipe(72, 650); }, 520);
        setTimeout(() => { if (!wipeTouched) animateWipe(50, 450); }, 1200);
      }, 900);
    }, { threshold: 0.6 });
    io.observe(ba);
  }

  // Two muted clips of the same moment, kept in sync under the wipe.
  const raw = ba.querySelector('.clip-raw'), edit = ba.querySelector('.clip-edit');
  const btn = document.querySelector('.play-both');
  const big = ba.querySelector('.big-play');
  if (raw && edit) {
    const both = [raw, edit];
    const setPlaying = on => {
      btn.setAttribute('aria-pressed', String(on));
      btn.textContent = on ? 'Pause' : 'Play both';
      ba.classList.toggle('is-paused', !on);
    };
    const play = () => Promise.all(both.map(v => v.play())).then(() => setPlaying(true)).catch(() => setPlaying(false));
    const pause = () => { both.forEach(v => v.pause()); setPlaying(false); };
    btn.addEventListener('click', () => (raw.paused ? play() : pause()));
    big.addEventListener('pointerdown', e => e.stopPropagation());
    big.addEventListener('click', e => { e.stopPropagation(); play(); });
    // Keep the edit in step with the raw clip. Small drift is fixed by speeding up or slowing down the edit
    // a little (works on any host); a big jump is only attempted where the browser can seek.
    raw.addEventListener('timeupdate', () => {
      if (raw.paused || edit.seeking) return;
      const d = raw.duration || 0;
      let drift = raw.currentTime - edit.currentTime;
      if (d && Math.abs(drift) > d / 2) drift -= Math.sign(drift) * d; // across the loop point
      if (Math.abs(drift) > 1 && edit.seekable.length && edit.seekable.end(0) > raw.currentTime) edit.currentTime = raw.currentTime;
      else edit.playbackRate = Math.abs(drift) < 0.05 ? 1 : Math.min(1.5, Math.max(0.66, 1 + drift));
    });
    raw.addEventListener('pause', () => setPlaying(false));
    raw.addEventListener('playing', () => setPlaying(true));
    setPlaying(false);
    // Browsers may refuse to start video on their own (Low Power Mode, data saver). The play button then stays visible.
    if (reduceMotion) both.forEach(v => { v.removeAttribute('autoplay'); v.pause(); });
    else play();
  }
}

// ---------- The cut, as a timeline ----------
// Raw recording: 200 seconds. Kept moments total 58 seconds. Replace with your own edit decisions.
const RAW_LEN = 200;
const clips = [
  { id: 'warmup',  start: 0,   end: 12,  type: 'cut',  note: 'Warm-up chat' },
  { id: 'a',       start: 12,  end: 26,  type: 'keep', order: 1 },
  { id: 'retake1', start: 26,  end: 52,  type: 'cut',  note: 'Retakes and pauses' },
  { id: 'b',       start: 52,  end: 64,  type: 'keep', order: 2 },
  { id: 'tangent', start: 64,  end: 95,  type: 'cut',  note: 'A tangent' },
  { id: 'c',       start: 95,  end: 104, type: 'keep', order: 3 },
  { id: 'retake2', start: 104, end: 134, type: 'cut',  note: 'Retakes' },
  { id: 'hook',    start: 134, end: 142, type: 'hook', order: 0 },
  { id: 'pause',   start: 142, end: 160, type: 'cut',  note: 'Long pause' },
  { id: 'd',       start: 160, end: 175, type: 'keep', order: 4 },
  { id: 'outro',   start: 175, end: 200, type: 'cut',  note: 'Rambling outro' },
];
const EDIT_LEN = clips.filter(c => c.type !== 'cut').reduce((s, c) => s + c.end - c.start, 0);
const track = document.getElementById('cut-track');
const cutEnd = document.getElementById('cut-end');
const segBtns = document.querySelectorAll('.seg-btn');
let cutView = 'edit';

if (track) {
  clips.forEach(c => {
    const el = document.createElement('span');
    el.className = `clip ${c.type === 'cut' ? 'is-cut' : c.type === 'hook' ? 'is-hook' : ''}`;
    el.dataset.id = c.id;
    el.title = c.type === 'cut' ? `Cut: ${c.note}, ${c.end - c.start}s` : c.type === 'hook' ? `Opening line, from ${fmt(c.start)}` : `Kept, ${c.end - c.start}s`;
    c.el = el;
    track.appendChild(el);
  });
}
function layoutCut(view) {
  cutView = view;
  const editFrac = EDIT_LEN / RAW_LEN; // the edited timeline is drawn to the same scale, so it is visibly shorter
  if (view === 'raw') {
    clips.forEach(c => {
      c.el.style.left = `${(c.start / RAW_LEN) * 100}%`;
      c.el.style.width = `calc(${((c.end - c.start) / RAW_LEN) * 100}% - 2px)`;
      c.el.style.opacity = 1;
    });
    cutEnd.textContent = fmt(RAW_LEN);
    cutEnd.style.transform = 'none';
  } else {
    let t = 0;
    [...clips].filter(c => c.type !== 'cut').sort((a, b) => a.order - b.order).forEach(c => {
      c.el.style.left = `${(t / RAW_LEN) * 100}%`;
      c.el.style.width = `calc(${((c.end - c.start) / RAW_LEN) * 100}% - 2px)`;
      c.el.style.opacity = 1;
      t += c.end - c.start;
    });
    // Cut footage collapses where it stood
    clips.filter(c => c.type === 'cut').forEach(c => {
      c.el.style.width = '0%';
      c.el.style.opacity = 0;
      c.el.style.left = `${Math.min(c.start / RAW_LEN, editFrac) * 100}%`;
    });
    cutEnd.textContent = fmt(EDIT_LEN);
    const axis = cutEnd.parentElement.getBoundingClientRect().width;
    cutEnd.style.transform = `translateX(-${axis * (1 - editFrac)}px)`;
  }
  segBtns.forEach(b => b.setAttribute('aria-pressed', b.dataset.view === view));
}
function highlight(kind) {
  clips.forEach(c => c.el.classList.toggle('is-hl',
    kind === 'hook' ? c.type === 'hook' : kind === 'cut' ? c.type === 'cut' : kind === 'keep' ? c.type !== 'cut' : false));
}
if (track) {
  layoutCut('edit');
  segBtns.forEach(b => b.addEventListener('click', () => { highlight(null); layoutCut(b.dataset.view); }));
  window.addEventListener('resize', () => layoutCut(cutView));
}

// "What changed" items drive the timeline and the wipe
document.querySelectorAll('.change').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.change').forEach(b => b.classList.toggle('is-active', b === btn));
    if (btn.dataset.view) {
      layoutCut(btn.dataset.view);
      highlight(btn.dataset.hl);
      document.querySelector('.cut').scrollIntoView({ behavior: reduceMotion ? 'auto' : 'smooth', block: 'nearest' });
    }
    if (btn.dataset.wipe && ba) {
      wipeTouched = true;
      animateWipe(parseFloat(btn.dataset.wipe), 700);
    }
  });
});

// ---------- Nav marker ----------
const nav = document.querySelector('.main-nav');
const marker = document.querySelector('.nav-marker');
if (nav && marker && 'IntersectionObserver' in window) {
  const links = [...nav.querySelectorAll('a')];
  const sections = links.map(a => document.querySelector(a.getAttribute('href'))).filter(Boolean);
  const visible = new Map();
  const io = new IntersectionObserver(entries => {
    entries.forEach(e => visible.set(e.target, e.isIntersecting ? e.intersectionRatio : 0));
    let best = null, ratio = 0;
    visible.forEach((r, el) => { if (r > ratio) { ratio = r; best = el; } });
    links.forEach(a => a.removeAttribute('aria-current'));
    const link = best ? links[sections.indexOf(best)] : null;
    if (!link) { marker.style.opacity = 0; return; }
    link.setAttribute('aria-current', 'true');
    marker.style.opacity = 1;
    marker.style.transform = `translateX(${link.offsetLeft}px) scaleX(${link.offsetWidth})`;
  }, { rootMargin: '-35% 0px -55% 0px', threshold: [0, 0.01, 0.5, 1] });
  sections.forEach(s => io.observe(s));
}

// ---------- Format tabs: the marker slides, the panel eases in ----------
const tabs = [...document.querySelectorAll('.tab')];
const tabMarker = document.querySelector('.tab-marker');
function placeTabMarker(tab) {
  if (tabMarker) tabMarker.style.transform = `translateX(${tab.offsetLeft}px) scaleX(${tab.offsetWidth})`;
}
function selectTab(tab) {
  tabs.forEach(t => {
    const on = t === tab;
    t.setAttribute('aria-selected', on);
    t.tabIndex = on ? 0 : -1;
    const panel = document.getElementById(t.getAttribute('aria-controls'));
    if (on && panel.hidden) {
      panel.hidden = false;
      panel.classList.remove('is-entering');
      void panel.offsetWidth;
      panel.classList.add('is-entering');
    } else if (!on) {
      panel.hidden = true;
    }
  });
  placeTabMarker(tab);
}
tabs.forEach((tab, i) => {
  tab.addEventListener('click', () => selectTab(tab));
  tab.addEventListener('keydown', e => {
    if (e.key !== 'ArrowRight' && e.key !== 'ArrowLeft') return;
    const next = tabs[(i + (e.key === 'ArrowRight' ? 1 : tabs.length - 1)) % tabs.length];
    selectTab(next);
    next.focus();
  });
});
if (tabs.length) {
  const place = () => placeTabMarker(tabs.find(t => t.getAttribute('aria-selected') === 'true'));
  place();
  window.addEventListener('resize', place);
  document.fonts?.ready.then(place);
}

// ---------- Player: grows out of the thumbnail you clicked (View Transitions), YouTube loads on click ----------
const lightbox = document.getElementById('lightbox');
const frame = document.getElementById('lightbox-frame');
const closeBtn = document.getElementById('lightbox-close');
let opener = null;

function fillPlayer(id, title) {
  frame.innerHTML = '';
  if (!id || /^[A-Z0-9_]+$/.test(id)) {
    const p = document.createElement('p');
    p.textContent = `“${title}” will play here once you add its YouTube video ID to the data-video attribute in index.html.`;
    frame.appendChild(p);
    return;
  }
  const iframe = document.createElement('iframe');
  iframe.src = `https://www.youtube-nocookie.com/embed/${encodeURIComponent(id)}?autoplay=1&rel=0`;
  iframe.title = title || 'Video';
  iframe.allow = 'autoplay; encrypted-media; picture-in-picture; fullscreen';
  iframe.allowFullscreen = true;
  frame.appendChild(iframe);
}
function openVideo(el) {
  opener = el;
  const show = () => {
    el.style.viewTransitionName = '';
    frame.style.viewTransitionName = 'player';
    fillPlayer(el.dataset.video, el.dataset.title);
    lightbox.hidden = false;
    document.body.style.overflow = 'hidden';
  };
  if (document.startViewTransition && !reduceMotion && el.classList.contains('thumb')) {
    el.style.viewTransitionName = 'player';
    document.startViewTransition(show).finished.finally(() => { frame.style.viewTransitionName = ''; closeBtn.focus(); });
  } else {
    show();
    closeBtn.focus();
  }
}
function closeVideo() {
  const hide = () => {
    lightbox.hidden = true;
    frame.innerHTML = '';
    document.body.style.overflow = '';
    frame.style.viewTransitionName = '';
    if (opener?.classList.contains('thumb')) opener.style.viewTransitionName = 'player';
  };
  if (document.startViewTransition && !reduceMotion && opener?.classList.contains('thumb')) {
    frame.style.viewTransitionName = 'player';
    document.startViewTransition(hide).finished.finally(() => { if (opener) { opener.style.viewTransitionName = ''; opener.focus(); } });
  } else {
    hide();
    opener?.focus();
  }
}
document.querySelectorAll('[data-video]').forEach(el => el.addEventListener('click', () => openVideo(el)));
if (lightbox) {
  closeBtn.addEventListener('click', closeVideo);
  lightbox.addEventListener('click', e => { if (e.target === lightbox) closeVideo(); });
  document.addEventListener('keydown', e => { if (e.key === 'Escape' && !lightbox.hidden) closeVideo(); });
}

// ---------- Retention chart (sample data) ----------
const retention = [
  { x: 0, before: 100, after: 100 }, { x: 5, before: 61, after: 79 }, { x: 10, before: 52, after: 72 },
  { x: 20, before: 45, after: 66 }, { x: 30, before: 41, after: 62 }, { x: 40, before: 38, after: 59 },
  { x: 50, before: 35, after: 56 }, { x: 60, before: 33, after: 54 }, { x: 70, before: 31, after: 52 },
  { x: 80, before: 30, after: 50 }, { x: 90, before: 29, after: 48 }, { x: 100, before: 28, after: 46 },
];
const series = [
  { key: 'after', name: 'With my edits', color: 'var(--series-after)' },
  { key: 'before', name: 'Before', color: 'var(--series-before)' },
];
const chartEl = document.getElementById('chart');
const tableBody = document.querySelector('#chart-table tbody');
if (tableBody) {
  tableBody.innerHTML = retention.map(d => `<tr><td>${d.x === 0 ? 'Start' : d.x === 100 ? 'End' : d.x + '%'}</td><td>${d.before}%</td><td>${d.after}%</td></tr>`).join('');
}
let chartDrawn = false;
function drawChart(animate) {
  if (!chartEl) return;
  const W = Math.max(280, chartEl.clientWidth);
  const narrow = W < 520;
  const H = narrow ? 230 : 290;
  const m = { top: 12, right: narrow ? 46 : 112, bottom: 26, left: 38 };
  const iw = W - m.left - m.right, ih = H - m.top - m.bottom;
  const sx = x => m.left + (x / 100) * iw;
  const sy = y => m.top + (1 - y / 100) * ih;
  const path = key => retention.map((d, i) => `${i ? 'L' : 'M'}${sx(d.x).toFixed(1)},${sy(d[key]).toFixed(1)}`).join('');
  let svg = `<svg viewBox="0 0 ${W} ${H}" width="${W}" height="${H}" role="img" aria-label="Line chart. Before, audience retention falls to 28% by the end of the video. With my edits it falls to 46%.">`;
  svg += '<g class="grid">' + [0, 25, 50, 75, 100].map(v => `<line x1="${m.left}" x2="${m.left + iw}" y1="${sy(v)}" y2="${sy(v)}"/>`).join('') + '</g>';
  svg += '<g class="axis">' + [0, 25, 50, 75, 100].map(v => `<text x="${m.left - 8}" y="${sy(v) + 4}" text-anchor="end">${v}%</text>`).join('');
  svg += [[0, 'Start'], [50, 'Halfway'], [100, 'End']].map(([v, l], i, a) => `<text x="${sx(v)}" y="${H - 6}" text-anchor="${i === 0 ? 'start' : i === a.length - 1 ? 'end' : 'middle'}">${l}</text>`).join('') + '</g>';
  svg += `<path class="area-after" d="${path('after')}L${sx(100)},${sy(0)}L${sx(0)},${sy(0)}Z"/>`;
  svg += `<path class="line line-before" d="${path('before')}"/><path class="line line-after" d="${path('after')}"/>`;
  const last = retention[retention.length - 1];
  series.forEach(s => {
    const y = sy(last[s.key]);
    svg += `<circle class="end-dot" cx="${sx(100)}" cy="${y}" r="4.5" fill="${s.color}"/>`;
    svg += `<text class="end-label" x="${sx(100) + 10}" y="${y + 4}">${narrow ? '' : s.name + ' '}${last[s.key]}%</text>`;
  });
  svg += `<line class="cross" id="cross" x1="0" x2="0" y1="${m.top}" y2="${m.top + ih}" visibility="hidden"/>`;
  svg += `<g id="hover-dots" visibility="hidden">${series.map(s => `<circle class="end-dot" r="4.5" fill="${s.color}" data-key="${s.key}"/>`).join('')}</g>`;
  svg += `<rect x="${m.left}" y="${m.top}" width="${iw}" height="${ih}" fill="transparent" id="hit"/></svg>`;
  chartEl.innerHTML = svg + '<div class="chart-tip" id="chart-tip" hidden></div>';

  if (animate && !reduceMotion) {
    chartEl.classList.add('will-draw');
    const lines = chartEl.querySelectorAll('.line');
    const fades = chartEl.querySelectorAll('.area-after, .end-dot, .end-label');
    lines.forEach(l => { const len = l.getTotalLength(); l.style.strokeDasharray = len; l.style.strokeDashoffset = len; });
    fades.forEach(f => { f.style.opacity = 0; });
    requestAnimationFrame(() => requestAnimationFrame(() => {
      lines.forEach(l => { l.style.strokeDashoffset = 0; });
      fades.forEach(f => { f.style.opacity = ''; });
    }));
  }

  const hit = chartEl.querySelector('#hit'), cross = chartEl.querySelector('#cross');
  const dots = chartEl.querySelector('#hover-dots'), tip = chartEl.querySelector('#chart-tip');
  const move = e => {
    const rect = chartEl.querySelector('svg').getBoundingClientRect();
    const xVal = (((e.clientX - rect.left) * (W / rect.width)) - m.left) / iw * 100;
    const d = retention.reduce((a, b) => Math.abs(b.x - xVal) < Math.abs(a.x - xVal) ? b : a);
    const cx = sx(d.x);
    cross.setAttribute('x1', cx); cross.setAttribute('x2', cx); cross.setAttribute('visibility', 'visible');
    dots.setAttribute('visibility', 'visible');
    dots.querySelectorAll('circle').forEach(c => { c.setAttribute('cx', cx); c.setAttribute('cy', sy(d[c.dataset.key])); });
    tip.innerHTML = `<div class="t">${d.x === 0 ? 'Start' : d.x === 100 ? 'End of video' : d.x + '% through'}</div>` +
      series.map(s => `<div class="row"><span class="sw" style="background:${s.color}"></span>${s.name}: <strong>${d[s.key]}%</strong></div>`).join('');
    tip.hidden = false;
    const scale = rect.width / W;
    let left = cx * scale + 12;
    if (left + tip.offsetWidth > rect.width) left = cx * scale - tip.offsetWidth - 12;
    tip.style.left = `${left}px`;
    tip.style.top = `${m.top * scale}px`;
  };
  const leave = () => { cross.setAttribute('visibility', 'hidden'); dots.setAttribute('visibility', 'hidden'); tip.hidden = true; };
  hit.addEventListener('pointermove', move);
  hit.addEventListener('pointerdown', move);
  hit.addEventListener('pointerleave', leave);
}
if (chartEl) {
  drawChart(false);
  if (!reduceMotion && 'IntersectionObserver' in window) {
    const io = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting && !chartDrawn) { chartDrawn = true; io.disconnect(); drawChart(true); }
    }, { threshold: 0.5 });
    io.observe(chartEl);
  }
  if ('ResizeObserver' in window) {
    let lastW = chartEl.clientWidth;
    new ResizeObserver(() => { if (Math.abs(chartEl.clientWidth - lastW) > 4) { lastW = chartEl.clientWidth; drawChart(false); } }).observe(chartEl);
  }
}

// ---------- Price links fill in the form ----------
const typeSelect = document.getElementById('f-type');
document.querySelectorAll('[data-project]').forEach(link => {
  link.addEventListener('click', () => {
    if (!typeSelect) return;
    typeSelect.value = link.dataset.project;
    const field = typeSelect.closest('.field');
    field.classList.remove('has-error', 'is-filled');
    void field.offsetWidth;
    field.classList.add('is-filled');
  });
});

// ---------- Copy email ----------
const copyBtn = document.getElementById('copy-email');
const emailText = document.getElementById('email-text');
if (copyBtn && emailText) {
  copyBtn.addEventListener('click', () => {
    const done = () => {
      copyBtn.textContent = 'Copied';
      copyBtn.classList.add('is-done');
      setTimeout(() => { copyBtn.textContent = 'Copy'; copyBtn.classList.remove('is-done'); }, 1800);
    };
    const select = () => {
      const r = document.createRange();
      r.selectNodeContents(emailText);
      const sel = window.getSelection();
      sel.removeAllRanges();
      sel.addRange(r);
    };
    if (navigator.clipboard) navigator.clipboard.writeText(emailText.textContent.trim()).then(done).catch(select);
    else select();
  });
}

// ---------- Contact form ----------
const form = document.getElementById('contact-form');
if (form) {
  const status = document.getElementById('form-status');
  const submit = document.getElementById('f-submit');
  const label = submit.querySelector('.btn-label');
  const idleLabel = label.textContent;
  const fields = [...form.querySelectorAll('[required]')];
  const check = input => {
    const ok = input.checkValidity();
    input.closest('.field').classList.toggle('has-error', !ok);
    input.setAttribute('aria-invalid', !ok);
    return ok;
  };
  fields.forEach(input => {
    input.addEventListener('blur', () => { if (input.value) check(input); });
    input.addEventListener('input', () => { if (input.closest('.field').classList.contains('has-error')) check(input); });
    input.addEventListener('change', () => check(input));
  });
  const showDone = () => {
    const fieldsWrap = form.querySelector('.form-fields');
    const doneWrap = document.getElementById('form-done');
    const from = form.offsetHeight;
    fieldsWrap.hidden = true;
    doneWrap.hidden = false;
    const to = form.offsetHeight;
    if (!reduceMotion) {
      form.style.height = `${from}px`;
      requestAnimationFrame(() => { form.style.height = `${to}px`; });
      form.addEventListener('transitionend', () => { form.style.height = ''; }, { once: true });
    }
    doneWrap.focus({ preventScroll: true });
  };
  form.addEventListener('submit', async e => {
    e.preventDefault();
    const invalid = fields.filter(f => !check(f));
    if (invalid.length) {
      status.textContent = invalid.length === 1 ? 'One field needs attention.' : `${invalid.length} fields need attention.`;
      invalid[0].focus();
      return;
    }
    if (form.action.includes('YOUR_FORM_ID')) {
      status.textContent = 'The form isn’t connected yet. Add your Formspree ID in index.html to receive messages.';
      return;
    }
    status.textContent = '';
    submit.classList.add('is-loading');
    label.textContent = 'Sending';
    try {
      const res = await fetch(form.action, { method: 'POST', body: new FormData(form), headers: { Accept: 'application/json' } });
      if (!res.ok) throw new Error();
      showDone();
    } catch {
      status.textContent = 'Your details didn’t send. Check your connection and try again, or message me on WhatsApp.';
    } finally {
      submit.classList.remove('is-loading');
      label.textContent = idleLabel;
    }
  });
}

const year = document.getElementById('year');
if (year) year.textContent = new Date().getFullYear();
