const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

// ---------- Reel preview: fall back to the styled frame if no loop file exists ----------
const reelVideo = document.querySelector('.reel-video');
if (reelVideo) {
  const source = reelVideo.querySelector('source');
  const broken = () => reelVideo.classList.add('is-broken');
  reelVideo.addEventListener('error', broken);
  if (source) source.addEventListener('error', broken);
  if (reduceMotion) reelVideo.pause();
}

// Running timecode in the reel HUD (24fps)
const tc = document.getElementById('tc');
if (tc && !reduceMotion) {
  const start = performance.now();
  const pad = n => String(n).padStart(2, '0');
  const tick = now => {
    const t = ((now - start) / 1000) % 75;
    const s = Math.floor(t);
    tc.textContent = `00:${pad(Math.floor(s / 60))}:${pad(s % 60)}:${pad(Math.floor((t - s) * 24))}`;
    requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);
}

// ---------- Lightbox: load the YouTube player only on click ----------
const lightbox = document.getElementById('lightbox');
const frame = document.getElementById('lightbox-frame');
const closeBtn = document.getElementById('lightbox-close');
let lastFocus = null;

function openVideo(id, title) {
  lastFocus = document.activeElement;
  frame.innerHTML = '';
  // Placeholder IDs are all caps with underscores. Real YouTube IDs are 11 characters.
  if (!id || /^[A-Z0-9_]+$/.test(id)) {
    const p = document.createElement('p');
    p.textContent = `“${title}” will play here. Add its YouTube video ID to the data-video attribute in index.html.`;
    frame.appendChild(p);
  } else {
    const iframe = document.createElement('iframe');
    iframe.src = `https://www.youtube-nocookie.com/embed/${encodeURIComponent(id)}?autoplay=1&rel=0&modestbranding=1`;
    iframe.title = title || 'Video';
    iframe.allow = 'autoplay; encrypted-media; picture-in-picture; fullscreen';
    iframe.allowFullscreen = true;
    frame.appendChild(iframe);
  }
  lightbox.hidden = false;
  document.body.style.overflow = 'hidden';
  closeBtn.focus();
}
function closeVideo() {
  lightbox.hidden = true;
  frame.innerHTML = '';
  document.body.style.overflow = '';
  if (lastFocus) lastFocus.focus();
}
document.querySelectorAll('[data-video]').forEach(el => {
  el.addEventListener('click', () => openVideo(el.dataset.video, el.dataset.title));
});
if (lightbox) {
  closeBtn.addEventListener('click', closeVideo);
  lightbox.addEventListener('click', e => { if (e.target === lightbox) closeVideo(); });
  document.addEventListener('keydown', e => { if (e.key === 'Escape' && !lightbox.hidden) closeVideo(); });
}

// ---------- Work tabs ----------
const tabs = [...document.querySelectorAll('.tab')];
function selectTab(tab) {
  tabs.forEach(t => {
    const on = t === tab;
    t.classList.toggle('is-active', on);
    t.setAttribute('aria-selected', on);
    t.tabIndex = on ? 0 : -1;
    document.getElementById(t.getAttribute('aria-controls')).hidden = !on;
  });
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

// ---------- Raw vs edited toggle ----------
const compareThumb = document.getElementById('compare-thumb');
const compareLabel = document.getElementById('compare-label');
const versions = {
  raw: { id: 'RAW_VIDEO_ID', title: 'The raw footage', label: 'Raw · 03:20' },
  edit: { id: 'EDIT_VIDEO_ID', title: 'The edited version', label: 'Edited · 00:58' },
};
document.querySelectorAll('.seg-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    const v = versions[btn.dataset.version];
    document.querySelectorAll('.seg-btn').forEach(b => {
      b.classList.toggle('is-active', b === btn);
      b.setAttribute('aria-pressed', b === btn);
    });
    compareThumb.classList.toggle('is-raw', btn.dataset.version === 'raw');
    compareThumb.classList.toggle('is-edit', btn.dataset.version === 'edit');
    compareThumb.dataset.video = v.id;
    compareThumb.dataset.title = v.title;
    compareLabel.textContent = v.label;
  });
});

// ---------- Retention chart (sample data: replace with real YouTube Studio numbers) ----------
const retention = [
  { x: 0,   before: 100, after: 100 },
  { x: 5,   before: 61,  after: 79 },
  { x: 10,  before: 52,  after: 72 },
  { x: 20,  before: 45,  after: 66 },
  { x: 30,  before: 41,  after: 62 },
  { x: 40,  before: 38,  after: 59 },
  { x: 50,  before: 35,  after: 56 },
  { x: 60,  before: 33,  after: 54 },
  { x: 70,  before: 31,  after: 52 },
  { x: 80,  before: 30,  after: 50 },
  { x: 90,  before: 29,  after: 48 },
  { x: 100, before: 28,  after: 46 },
];
const series = [
  { key: 'after', name: 'With my edits', color: 'var(--series-after)' },
  { key: 'before', name: 'Before', color: 'var(--series-before)' },
];
const chartEl = document.getElementById('chart');
const tableBody = document.querySelector('#chart-table tbody');

if (tableBody) {
  tableBody.innerHTML = retention.map(d =>
    `<tr><td>${d.x === 0 ? 'Start' : d.x === 100 ? 'End' : d.x + '%'}</td><td>${d.before}%</td><td>${d.after}%</td></tr>`
  ).join('');
}

function drawChart() {
  if (!chartEl) return;
  const W = Math.max(280, chartEl.clientWidth);
  const narrow = W < 520;
  const H = narrow ? 240 : 300;
  const m = { top: 14, right: narrow ? 64 : 120, bottom: 28, left: 36 };
  const iw = W - m.left - m.right;
  const ih = H - m.top - m.bottom;
  const sx = x => m.left + (x / 100) * iw;
  const sy = y => m.top + (1 - y / 100) * ih;
  const ns = 'http://www.w3.org/2000/svg';
  const path = key => retention.map((d, i) => `${i ? 'L' : 'M'}${sx(d.x).toFixed(1)},${sy(d[key]).toFixed(1)}`).join('');

  let svg = `<svg xmlns="${ns}" viewBox="0 0 ${W} ${H}" width="${W}" height="${H}" role="img" aria-label="Line chart: audience retention falls to 28% by the end of the video before, and to 46% with my edits.">`;
  svg += '<g class="grid">';
  [0, 25, 50, 75, 100].forEach(v => { svg += `<line x1="${m.left}" x2="${m.left + iw}" y1="${sy(v)}" y2="${sy(v)}"/>`; });
  svg += '</g><g class="axis">';
  [0, 25, 50, 75, 100].forEach(v => { svg += `<text x="${m.left - 8}" y="${sy(v) + 4}" text-anchor="end">${v}%</text>`; });
  [[0, 'Start'], [25, '25%'], [50, '50%'], [75, '75%'], [100, 'End']].forEach(([v, l], i, a) => {
    const anchor = i === 0 ? 'start' : i === a.length - 1 ? 'end' : 'middle';
    svg += `<text x="${sx(v)}" y="${H - 8}" text-anchor="${anchor}">${l}</text>`;
  });
  svg += '</g>';
  const area = `${path('after')}L${sx(100)},${sy(0)}L${sx(0)},${sy(0)}Z`;
  svg += `<path class="area-after" d="${area}"/>`;
  svg += `<path class="line line-before" d="${path('before')}"/>`;
  svg += `<path class="line line-after" d="${path('after')}"/>`;
  const last = retention[retention.length - 1];
  series.forEach(s => {
    const y = sy(last[s.key]);
    svg += `<circle class="end-dot" cx="${sx(100)}" cy="${y}" r="4.5" fill="${s.color}"/>`;
    const label = narrow ? `${last[s.key]}%` : `${s.name} ${last[s.key]}%`;
    svg += `<text class="end-label" x="${sx(100) + 10}" y="${y + 4}">${label}</text>`;
  });
  svg += `<line class="cross" id="cross" x1="0" x2="0" y1="${m.top}" y2="${m.top + ih}" visibility="hidden"/>`;
  svg += `<g id="hover-dots" visibility="hidden">${series.map(s => `<circle class="end-dot" r="4.5" fill="${s.color}" data-key="${s.key}"/>`).join('')}</g>`;
  svg += `<rect x="${m.left}" y="${m.top}" width="${iw}" height="${ih}" fill="transparent" id="hit"/>`;
  svg += '</svg>';
  chartEl.innerHTML = svg + '<div class="chart-tip" id="chart-tip" hidden></div>';

  const hit = chartEl.querySelector('#hit');
  const cross = chartEl.querySelector('#cross');
  const dots = chartEl.querySelector('#hover-dots');
  const tip = chartEl.querySelector('#chart-tip');
  const move = e => {
    const rect = chartEl.querySelector('svg').getBoundingClientRect();
    const px = (e.clientX - rect.left) * (W / rect.width);
    const xVal = ((px - m.left) / iw) * 100;
    const d = retention.reduce((a, b) => Math.abs(b.x - xVal) < Math.abs(a.x - xVal) ? b : a);
    const cx = sx(d.x);
    cross.setAttribute('x1', cx); cross.setAttribute('x2', cx);
    cross.setAttribute('visibility', 'visible');
    dots.setAttribute('visibility', 'visible');
    dots.querySelectorAll('circle').forEach(c => { c.setAttribute('cx', cx); c.setAttribute('cy', sy(d[c.dataset.key])); });
    const when = d.x === 0 ? 'Start' : d.x === 100 ? 'End of video' : `${d.x}% through`;
    tip.innerHTML = `<div class="t">${when}</div>` + series.map(s =>
      `<div class="row"><span class="sw" style="background:${s.color}"></span>${s.name}: <strong>${d[s.key]}%</strong></div>`).join('');
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
drawChart();
if ('ResizeObserver' in window && chartEl) {
  let lastW = chartEl.clientWidth;
  new ResizeObserver(() => {
    if (Math.abs(chartEl.clientWidth - lastW) > 4) { lastW = chartEl.clientWidth; drawChart(); }
  }).observe(chartEl);
}

// ---------- Pricing buttons preselect the project type ----------
const typeSelect = document.getElementById('f-type');
document.querySelectorAll('[data-project]').forEach(link => {
  link.addEventListener('click', () => { if (typeSelect) typeSelect.value = link.dataset.project; });
});

// ---------- Copy email ----------
const copyBtn = document.getElementById('copy-email');
const emailText = document.getElementById('email-text');
if (copyBtn && emailText) {
  copyBtn.addEventListener('click', () => {
    const select = () => {
      const range = document.createRange();
      range.selectNodeContents(emailText);
      const sel = window.getSelection();
      sel.removeAllRanges();
      sel.addRange(range);
    };
    if (navigator.clipboard) {
      navigator.clipboard.writeText(emailText.textContent.trim())
        .then(() => { copyBtn.textContent = 'Copied'; setTimeout(() => copyBtn.textContent = 'Copy', 2000); })
        .catch(select);
    } else {
      select();
    }
  });
}

// ---------- Contact form ----------
const form = document.getElementById('contact-form');
const status = document.getElementById('form-status');
if (form) {
  form.addEventListener('submit', async e => {
    e.preventDefault();
    let firstInvalid = null;
    form.querySelectorAll('[required]').forEach(input => {
      const ok = input.checkValidity();
      input.closest('.field').classList.toggle('has-error', !ok);
      if (!ok && !firstInvalid) firstInvalid = input;
    });
    if (firstInvalid) {
      status.textContent = 'Please fill in the highlighted fields.';
      firstInvalid.focus();
      return;
    }
    if (form.action.includes('YOUR_FORM_ID')) {
      status.textContent = 'Form not connected yet. Add your Formspree ID in index.html to receive messages.';
      return;
    }
    status.textContent = 'Sending…';
    try {
      const res = await fetch(form.action, { method: 'POST', body: new FormData(form), headers: { Accept: 'application/json' } });
      if (!res.ok) throw new Error();
      form.reset();
      status.textContent = 'Got it. I’ll reply within 24 hours.';
    } catch {
      status.textContent = 'That didn’t send. Please try WhatsApp or email instead.';
    }
  });
}

const year = document.getElementById('year');
if (year) year.textContent = new Date().getFullYear();
