const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

// ---------- Before / after wipe ----------
document.querySelectorAll('[data-ba]').forEach(ba => {
  const range = ba.querySelector('.ba-range');
  let touched = false;
  const set = v => {
    ba.style.setProperty('--pos', `${v}%`);
    ba.classList.toggle('at-start', v <= 4);
    ba.classList.toggle('at-end', v >= 96);
  };
  range.addEventListener('input', () => { touched = true; set(range.value); });
  // Pointer drags map straight to the cursor position (the range input handles keyboard and screen readers).
  const fromPointer = e => {
    const r = ba.getBoundingClientRect();
    const v = Math.max(0, Math.min(100, ((e.clientX - r.left) / r.width) * 100));
    range.value = Math.round(v);
    set(v.toFixed(1));
  };
  ba.addEventListener('dragstart', e => e.preventDefault());
  ba.addEventListener('pointerdown', e => {
    if (e.pointerType === 'mouse') e.preventDefault();
    touched = true;
    ba.setPointerCapture(e.pointerId);
    ba.classList.add('is-dragging');
    fromPointer(e);
  });
  ba.addEventListener('pointermove', e => { if (ba.classList.contains('is-dragging')) fromPointer(e); });
  const stop = () => ba.classList.remove('is-dragging');
  ba.addEventListener('pointerup', stop);
  ba.addEventListener('pointercancel', stop);

  // Show once that the line moves: a short sweep when the wipe first comes into view.
  if (reduceMotion || !('IntersectionObserver' in window)) return;
  const io = new IntersectionObserver(([entry]) => {
    if (!entry.isIntersecting) return;
    io.disconnect();
    setTimeout(() => {
      if (touched) return;
      const keys = [[0, 50], [450, 32], [1000, 66], [1400, 50]];
      const start = performance.now();
      const ease = t => 1 - Math.pow(1 - t, 3);
      const step = now => {
        if (touched) return;
        const t = Math.max(1, now - start);
        const i = keys.findIndex(k => k[0] >= t);
        if (i === -1) { set(50); range.value = 50; return; }
        const [t0, v0] = keys[i - 1], [t1, v1] = keys[i];
        const v = v0 + (v1 - v0) * ease((t - t0) / (t1 - t0));
        set(v.toFixed(1));
        range.value = Math.round(v);
        requestAnimationFrame(step);
      };
      requestAnimationFrame(step);
    }, 1100);
  }, { threshold: 0.6 });
  io.observe(ba);
});

// ---------- Nav marker follows the section in view ----------
const nav = document.querySelector('.main-nav');
const marker = document.querySelector('.nav-marker');
if (nav && marker && 'IntersectionObserver' in window) {
  const links = [...nav.querySelectorAll('a')];
  const sections = links.map(a => document.querySelector(a.getAttribute('href'))).filter(Boolean);
  const moveTo = link => {
    links.forEach(a => a.removeAttribute('aria-current'));
    if (!link) { marker.style.opacity = 0; return; }
    link.setAttribute('aria-current', 'true');
    marker.style.opacity = 1;
    marker.style.transform = `translateX(${link.offsetLeft}px) scaleX(${link.offsetWidth})`;
  };
  const visible = new Map();
  const io = new IntersectionObserver(entries => {
    entries.forEach(e => visible.set(e.target, e.isIntersecting ? e.intersectionRatio : 0));
    let best = null, ratio = 0;
    visible.forEach((r, el) => { if (r > ratio) { ratio = r; best = el; } });
    moveTo(best ? links[sections.indexOf(best)] : null);
  }, { rootMargin: '-35% 0px -55% 0px', threshold: [0, 0.01, 0.5, 1] });
  sections.forEach(s => io.observe(s));
}

// ---------- Project filter, animated with View Transitions where supported ----------
const chips = document.querySelectorAll('.chip');
const grid = document.querySelector('.work-grid');
const empty = document.querySelector('.work-empty');
function applyFilter(filter) {
  let shown = 0;
  grid.querySelectorAll('.project').forEach(p => {
    const show = filter === 'all' || p.dataset.type === filter;
    p.hidden = !show;
    if (show) shown++;
  });
  grid.classList.toggle('is-filtered', filter !== 'all');
  if (empty) empty.hidden = shown > 0;
}
chips.forEach(chip => {
  chip.addEventListener('click', () => {
    if (chip.getAttribute('aria-pressed') === 'true') return;
    chips.forEach(c => c.setAttribute('aria-pressed', c === chip));
    const run = () => applyFilter(chip.dataset.filter);
    if (document.startViewTransition && !reduceMotion) document.startViewTransition(run);
    else run();
  });
});

// ---------- Price links fill in the form and show it ----------
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
      const range = document.createRange();
      range.selectNodeContents(emailText);
      const sel = window.getSelection();
      sel.removeAllRanges();
      sel.addRange(range);
    };
    if (navigator.clipboard) navigator.clipboard.writeText(emailText.textContent.trim()).then(done).catch(select);
    else select();
  });
}

// ---------- Contact form: check each field when you leave it, show sending and sent ----------
const form = document.getElementById('contact-form');
if (form) {
  const status = document.getElementById('form-status');
  const submit = document.getElementById('f-submit');
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
    submit.querySelector('.btn-label').textContent = 'Sending project details';
    try {
      const res = await fetch(form.action, { method: 'POST', body: new FormData(form), headers: { Accept: 'application/json' } });
      if (!res.ok) throw new Error();
      showDone();
    } catch {
      status.textContent = 'Your details didn’t send. Check your connection and try again, or message me on WhatsApp.';
    } finally {
      submit.classList.remove('is-loading');
      submit.querySelector('.btn-label').textContent = 'Send project details';
    }
  });
}

const year = document.getElementById('year');
if (year) year.textContent = new Date().getFullYear();

// ---------- Case study: pins and list highlight each other ----------
document.querySelectorAll('.annotate').forEach(block => {
  const items = block.querySelectorAll('[data-pin]');
  const activate = n => items.forEach(el => el.classList.toggle('is-active', el.dataset.pin === n));
  items.forEach(el => {
    el.addEventListener('mouseenter', () => activate(el.dataset.pin));
    el.addEventListener('focus', () => activate(el.dataset.pin));
    el.addEventListener('click', () => activate(el.dataset.pin));
  });
  block.addEventListener('mouseleave', () => activate(null));
});
