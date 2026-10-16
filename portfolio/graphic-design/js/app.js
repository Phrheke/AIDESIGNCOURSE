/*
  Renders the portfolio from content/build/site-data.json (built from what you edit in /admin).
  All text is inserted as text, never as HTML, so nothing typed in the admin can break the page.
*/
(() => {
  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];
  const page = document.body.dataset.page;
  let data = null;

  // ---------- tiny DOM helpers ----------
  function el(tag, attrs = {}, ...children) {
    const node = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs)) {
      if (v === null || v === undefined || v === false) continue;
      if (k === 'class') node.className = v;
      else if (k === 'text') node.textContent = v;
      else if (k === 'style') node.setAttribute('style', v);
      else if (k.startsWith('on')) node.addEventListener(k.slice(2), v);
      else node.setAttribute(k, v === true ? '' : v);
    }
    children.flat().forEach(c => { if (c !== null && c !== undefined && c !== false) node.append(c); });
    return node;
  }
  // Blank lines become paragraphs, single line breaks stay as line breaks.
  function paragraphs(text) {
    return String(text || '').split(/\n{2,}/).map(t => t.trim()).filter(Boolean).map(t => {
      const p = el('p');
      t.split('\n').forEach((line, i) => { if (i) p.append(el('br')); p.append(line); });
      return p;
    });
  }
  const fill = (target, nodes) => { if (target) target.replaceChildren(...nodes); };
  const setText = (sel, text) => { const n = typeof sel === 'string' ? $(sel) : sel; if (n) n.textContent = text; };

  // ---------- images: reserve space from known sizes, resize on Netlify, never show a broken icon ----------
  const WIDTHS = [480, 800, 1200, 1600, 2400];
  function cdnUrl(src, w) { return `/.netlify/images?url=/${encodeURI(src)}&w=${w}&q=80`; }
  function canResize(img) { return data?.site?.image_cdn && img && !img.external && !/\.(svg|gif)$/i.test(img.src); }
  function picture(img, { alt = '', sizes = '100vw', eager = false, cls = '' } = {}) {
    if (!img || !img.src) return missing('Image missing');
    if (img.missing) return missing('Image not found', img);
    const attrs = { src: img.src, alt, class: cls || null, decoding: 'async', loading: eager ? 'eager' : 'lazy' };
    if (img.w && img.h) { attrs.width = img.w; attrs.height = img.h; }
    if (canResize(img)) {
      const ws = WIDTHS.filter(w => !img.w || w <= img.w);
      if (!ws.length) ws.push(img.w);
      attrs.srcset = ws.map(w => `${cdnUrl(img.src, w)} ${w}w`).join(', ');
      attrs.sizes = sizes;
      attrs.src = cdnUrl(img.src, Math.min(1200, img.w || 1200));
    }
    const node = el('img', attrs);
    if (eager) node.setAttribute('fetchpriority', 'high');
    node.addEventListener('error', () => {
      if (node.dataset.retried) { node.replaceWith(missing('Image could not load', img)); return; }
      node.dataset.retried = '1';
      node.removeAttribute('srcset');
      node.src = img.src;
    });
    return node;
  }
  function missing(label, img) {
    const ar = img && img.w && img.h ? `${img.w}/${img.h}` : '4/3';
    return el('div', { class: 'img-missing', style: `--ar:${ar}`, role: 'img', 'aria-label': label, text: label });
  }
  const ratio = img => (img && img.w && img.h ? img.h / img.w : 1.25);

  // ---------- site-wide ----------
  const ICONS = {
    linkedin: '<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="2" y="2" width="20" height="20" rx="3" fill="currentColor"/><rect x="6" y="10" width="2.6" height="8" fill="#fff"/><circle cx="7.3" cy="6.8" r="1.6" fill="#fff"/><path d="M11 10h2.5v1.2c.5-.8 1.5-1.4 2.8-1.4 2 0 3 1.2 3 3.6V18h-2.6v-4.2c0-1.2-.4-1.9-1.4-1.9s-1.7.7-1.7 1.9V18H11z" fill="#fff"/></svg>',
    instagram: '<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="2.5" y="2.5" width="19" height="19" rx="5.5" fill="none" stroke="currentColor" stroke-width="2"/><circle cx="12" cy="12" r="4.3" fill="none" stroke="currentColor" stroke-width="2"/><circle cx="17.4" cy="6.6" r="1.3" fill="currentColor"/></svg>',
    behance: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M2 6h5.2c2.2 0 3.5 1 3.5 2.8 0 1.1-.6 1.9-1.5 2.3 1.3.3 2 1.3 2 2.6 0 2-1.5 3.3-3.9 3.3H2zm2.5 2v2.8h2.4c.9 0 1.4-.5 1.4-1.4S7.8 8 6.9 8zm0 4.7v3.1h2.6c1 0 1.6-.6 1.6-1.6s-.6-1.5-1.6-1.5zM15 7h5v1.3h-5zM17.6 9.6c2.5 0 3.8 1.8 3.7 4.5h-5.5c.1 1.2.8 1.9 1.9 1.9.8 0 1.4-.4 1.6-1h1.9c-.4 1.7-1.8 2.7-3.6 2.7-2.4 0-3.9-1.6-3.9-4s1.5-4.1 3.9-4.1zm-1.8 3.2h3.4c-.1-1-.7-1.6-1.6-1.6-1 0-1.7.6-1.8 1.6z" fill="currentColor"/></svg>',
  };
  const SOCIAL_LABELS = { linkedin: 'LinkedIn', instagram: 'Instagram', behance: 'Behance' };
  function socialLinks(target, withIcons) {
    if (!target) return;
    const links = Object.entries(data.site.social).filter(([, url]) => url);
    fill(target, links.map(([key, url]) => {
      const a = el('a', { href: url, target: '_blank', rel: 'noopener me' });
      if (withIcons) a.insertAdjacentHTML('afterbegin', ICONS[key]);
      a.append(SOCIAL_LABELS[key]);
      return el('li', {}, a);
    }));
    target.hidden = !links.length;
  }
  function applySite() {
    const s = data.site;
    $$('[data-bind="name"]').forEach(n => { n.textContent = s.name; });
    socialLinks($('#footer-social'), false);
    setText('#year', String(new Date().getFullYear()));
    if (page === 'home') {
      document.title = s.seo.title || `${s.name}, ${s.role || 'graphic designer'}`;
      const meta = $('meta[name="description"]');
      if (meta && s.seo.description) meta.setAttribute('content', s.seo.description);
    }
  }

  // ---------- nav marker follows the section in view ----------
  function navMarker() {
    const nav = $('.main-nav'), marker = $('.nav-marker');
    if (!nav || !marker || !('IntersectionObserver' in window)) return;
    const links = $$('a', nav).filter(a => a.getAttribute('href').startsWith('#'));
    const sections = links.map(a => document.querySelector(a.getAttribute('href')));
    const seen = new Map();
    const io = new IntersectionObserver(entries => {
      entries.forEach(e => seen.set(e.target, e.isIntersecting ? e.intersectionRatio : 0));
      let best = null, r = 0;
      seen.forEach((v, k) => { if (v > r) { r = v; best = k; } });
      links.forEach(a => a.removeAttribute('aria-current'));
      const link = best && !best.hidden ? links[sections.indexOf(best)] : null;
      if (!link) { marker.style.opacity = 0; return; }
      link.setAttribute('aria-current', 'true');
      marker.style.opacity = 1;
      marker.style.transform = `translateX(${link.offsetLeft}px) scaleX(${link.offsetWidth})`;
    }, { rootMargin: '-35% 0px -55% 0px', threshold: [0, 0.01, 0.5, 1] });
    sections.forEach(s => s && io.observe(s));
  }

  // ---------- lightbox ----------
  const lightbox = (() => {
    const dlg = $('#lightbox');
    if (!dlg) return { open() {} };
    const img = $('#lb-img'), cap = $('#lb-caption'), count = $('#lb-count'), proj = $('#lb-project');
    let items = [], index = 0, opener = null;
    function show(i, dir = 0) {
      index = (i + items.length) % items.length;
      const it = items[index];
      const set = () => {
        img.removeAttribute('srcset');
        img.src = it.image.src;
        img.alt = it.alt || it.caption || '';
        cap.textContent = it.caption || '';
        count.textContent = items.length > 1 ? `${index + 1} of ${items.length}` : '';
        proj.hidden = !it.project;
        if (it.project) proj.href = `project.html?p=${encodeURIComponent(it.project)}`;
        img.classList.remove('is-leaving');
        [1, -1].forEach(d => { const n = items[(index + d + items.length) % items.length]; if (n) new Image().src = n.image.src; });
      };
      if (dir && !reduceMotion && dlg.open) {
        img.style.setProperty('--dx', `${dir * -24}px`);
        img.classList.add('is-leaving');
        setTimeout(set, 160);
      } else set();
      $('#lb-prev').hidden = $('#lb-next').hidden = items.length < 2;
    }
    function open(list, i, from) {
      items = list.filter(x => x.image && x.image.src && !x.image.missing);
      if (!items.length) return;
      opener = from || document.activeElement;
      const start = Math.max(0, items.indexOf(list[i]));
      show(start);
      dlg.showModal();
      document.documentElement.style.overflow = 'hidden';
    }
    dlg.addEventListener('close', () => { document.documentElement.style.overflow = ''; opener?.focus?.(); });
    $('#lb-close').addEventListener('click', () => dlg.close());
    $('#lb-prev').addEventListener('click', () => show(index - 1, -1));
    $('#lb-next').addEventListener('click', () => show(index + 1, 1));
    dlg.addEventListener('keydown', e => {
      if (e.key === 'ArrowRight') show(index + 1, 1);
      if (e.key === 'ArrowLeft') show(index - 1, -1);
    });
    dlg.addEventListener('click', e => { if (e.target === dlg || e.target.classList.contains('lb-stage')) dlg.close(); });
    let startX = null;
    const stage = $('.lb-stage', dlg);
    stage.addEventListener('pointerdown', e => { startX = e.clientX; });
    stage.addEventListener('pointerup', e => {
      if (startX === null) return;
      const dx = e.clientX - startX;
      startX = null;
      if (Math.abs(dx) > 50) show(index + (dx < 0 ? 1 : -1), dx < 0 ? 1 : -1);
    });
    return { open };
  })();

  // ---------- home: hero + gallery ----------
  function renderHero() {
    const s = data.site;
    setText('#hero-role', [s.role, s.location].filter(Boolean).join(', '));
    setText('#hero-intro', s.intro);
    const items = [];
    if (s.availability.full_time) items.push(el('li', {}, el('a', { href: '#contact', 'data-intent': 'role', text: s.availability.full_time_note })));
    if (s.availability.freelance) items.push(el('li', {}, el('a', { href: '#contact', 'data-intent': 'project', text: s.availability.freelance_note })));
    fill($('#availability'), items);
    $('#availability').hidden = !items.length;
  }

  function renderGallery() {
    const root = $('#gallery');
    const list = data.gallery.map(g => ({ image: g.image, alt: g.alt || g.title, caption: g.title, project: g.project }));
    if (!list.length) { root.replaceChildren(el('p', { class: 'empty', text: 'Gallery images will appear here.' })); return; }
    const nodes = list.map((it, i) => {
      const btn = el('button', { type: 'button', class: 'g-open', 'aria-label': `Open ${it.caption || 'image ' + (i + 1)} full size` },
        picture(it.image, { alt: it.alt, sizes: '(max-width: 760px) 50vw, (max-width: 1100px) 33vw, 25vw', eager: i < 4 }));
      btn.addEventListener('click', () => lightbox.open(list, i, btn));
      const cap = (it.caption || it.project) ? el('div', { class: 'g-cap' },
        it.caption ? el('span', { text: it.caption }) : null,
        it.project ? el('a', { href: `project.html?p=${encodeURIComponent(it.project)}`, text: 'View project' }) : null) : null;
      return { node: el('figure', { class: 'g-item', style: `--i:${i}` }, btn, cap), h: ratio(it.image) };
    });
    let cols = 0;
    const layout = () => {
      const w = root.clientWidth || window.innerWidth;
      const n = Math.min(nodes.length, w >= 1100 ? 4 : w >= 700 ? 3 : 2);
      if (n === cols) return;
      cols = n;
      const columns = Array.from({ length: n }, () => ({ el: el('div', { class: 'g-col' }), h: 0 }));
      nodes.forEach(item => {
        const c = columns.reduce((a, b) => (b.h < a.h ? b : a));
        c.el.append(item.node);
        c.h += item.h + 0.12; // 0.12 accounts for the caption and gap
      });
      root.replaceChildren(...columns.map(c => c.el));
    };
    layout();
    window.addEventListener('resize', layout);
  }

  // ---------- home: ways to work ----------
  function renderWays() {
    const s = data.site;
    setText('#hire-heading', s.hire.heading);
    fill($('#hire-body'), paragraphs(s.hire.body));
    setText('#hire-button', s.hire.button);
    const cv = $('#hire-cv');
    if (s.hire.cv) { cv.href = s.hire.cv; cv.hidden = false; }
    const li = $('#hire-linkedin');
    if (s.social.linkedin) { li.href = s.social.linkedin; li.hidden = false; }
    setText('#freelance-heading', s.freelance.heading);
    fill($('#freelance-body'), paragraphs(s.freelance.body));
    fill($('#services'), s.freelance.services.map(t => el('li', { text: t })));
    $('#services').hidden = !s.freelance.services.length;
    setText('#freelance-button', s.freelance.button);
    $('#way-hire').hidden = !s.availability.full_time;
    $('#way-freelance').hidden = !s.availability.freelance;
    $('#ways').hidden = !s.availability.full_time && !s.availability.freelance;
    if ($('#way-hire').hidden !== $('#way-freelance').hidden) $('.ways-grid').style.gridTemplateColumns = 'minmax(0, 1fr)';
  }

  // ---------- home: projects ----------
  function projectMeta(p) { return [p.category, p.year].filter(Boolean).join(', '); }
  function renderProjects() {
    const list = data.projects.filter(p => p.featured);
    $('#projects-empty').hidden = list.length > 0;
    fill($('#projects'), list.map(p => {
      const media = el('div', { class: 'p-card-media' }, picture(p.cover, { alt: '', sizes: '(max-width: 640px) 100vw, (max-width: 960px) 50vw, 33vw' }));
      const img = $('img', media);
      if (img) img.style.objectPosition = `center ${p.cover_focus}`;
      return el('a', { class: 'p-card', href: `project.html?p=${encodeURIComponent(p.slug)}` },
        media,
        projectMeta(p) ? el('p', { class: 'p-card-meta', text: projectMeta(p) }) : null,
        el('h3', { text: p.title }),
        p.summary ? el('p', { class: 'p-card-summary', text: p.summary }) : null);
    }));
  }

  // ---------- home: process loop ----------
  function renderProcess() {
    const pr = data.site.process;
    const section = $('#process');
    if (pr.steps.length < 2) { section.hidden = true; return; }
    setText('#process-title', pr.heading);
    setText('#process-intro', pr.intro);
    const ol = $('#process-steps');
    ol.style.setProperty('--n', pr.steps.length);
    fill(ol, pr.steps.map((st, i) => el('li', { class: `step${st.loops_back ? ' is-loop' : ''}${pr.steps[i + 1]?.loops_back ? ' is-target' : ''}` },
      el('span', { class: 'step-num', text: String(i + 1) }),
      el('h3', { text: st.title }),
      st.body ? el('p', { text: st.body }) : null,
      st.loops_back ? el('p', { class: 'step-loop-note', text: `${pr.loop_label} (step ${i})` }) : null)));
    const svg = $('#process-loop');
    const flow = $('#process-flow');
    const loops = pr.steps.map((s, i) => (s.loops_back ? i : -1)).filter(i => i > 0);
    const draw = (animate) => {
      svg.innerHTML = '';
      const stepsEls = $$('.step', ol);
      const inRow = stepsEls.length > 1 && stepsEls[0].offsetTop === stepsEls[1].offsetTop;
      flow.style.paddingTop = inRow && loops.length ? '76px' : '';
      if (!inRow || !loops.length) return;
      const box = flow.getBoundingClientRect();
      loops.forEach(i => {
        const a = $('.step-num', stepsEls[i]).getBoundingClientRect();
        const b = $('.step-num', stepsEls[i - 1]).getBoundingClientRect();
        const x1 = a.left + a.width / 2 - box.left, x0 = b.left + b.width / 2 - box.left;
        const y = a.top - box.top - 8;
        const lift = 54;
        const ns = 'http://www.w3.org/2000/svg';
        const path = document.createElementNS(ns, 'path');
        path.setAttribute('d', `M${x1},${y} C${x1},${y - lift} ${x0},${y - lift} ${x0},${y - 4}`);
        const head = document.createElementNS(ns, 'path');
        head.setAttribute('class', 'loop-head');
        head.setAttribute('d', `M${x0 - 6},${y - 12} L${x0},${y - 2} L${x0 + 6},${y - 12} Z`);
        const label = document.createElementNS(ns, 'text');
        label.setAttribute('x', (x0 + x1) / 2);
        label.setAttribute('y', y - lift + 2);
        label.setAttribute('text-anchor', 'middle');
        label.textContent = pr.loop_label;
        svg.append(path, head, label);
        if (animate && !reduceMotion) {
          svg.classList.add('will-draw');
          const len = path.getTotalLength();
          path.style.strokeDasharray = len; path.style.strokeDashoffset = len;
          head.style.opacity = 0; label.style.opacity = 0;
          requestAnimationFrame(() => requestAnimationFrame(() => { path.style.strokeDashoffset = 0; head.style.opacity = ''; label.style.opacity = ''; }));
        }
      });
    };
    draw(false);
    let drawn = false;
    if ('IntersectionObserver' in window && !reduceMotion) {
      const io = new IntersectionObserver(([e]) => { if (e.isIntersecting && !drawn) { drawn = true; io.disconnect(); draw(true); } }, { threshold: 0.5 });
      io.observe(flow);
    }
    let t;
    window.addEventListener('resize', () => { clearTimeout(t); t = setTimeout(() => draw(false), 120); });
    document.fonts?.ready.then(() => draw(false));
    // Hovering the feedback step highlights the loop it starts
    $$('.step.is-loop', ol).forEach(stepEl => {
      stepEl.addEventListener('mouseenter', () => section.classList.add('is-hl'));
      stepEl.addEventListener('mouseleave', () => section.classList.remove('is-hl'));
    });
  }

  // ---------- home: about, quotes, contact ----------
  function renderAbout() {
    const a = data.site.about;
    setText('#about-title', a.heading);
    const photo = $('#about-photo');
    if (a.photo && !a.photo.missing) fill(photo, [picture(a.photo, { alt: `Portrait of ${data.site.name}`, sizes: '(max-width: 960px) 340px, 30vw' })]);
    else { photo.remove(); $('.about-grid').classList.add('no-photo'); }
    fill($('#about-body'), paragraphs(a.body));
    fill($('#tools-list'), a.tools.map(t => el('li', { text: t })));
    $('#about-tools').hidden = !a.tools.length;
    fill($('#experience-list'), a.experience.map(e => el('li', {},
      el('strong', { text: [e.role, e.company].filter(Boolean).join(', ') }),
      e.years ? el('span', { class: 'exp-years', text: e.years }) : null,
      e.note ? el('span', { class: 'exp-note', text: e.note }) : null)));
    $('#about-experience').hidden = !a.experience.length;
  }
  function renderQuotes() {
    const q = data.site.testimonials;
    $('#quotes').hidden = !q.length;
    fill($('#quote-grid'), q.map(t => el('figure', { class: 'quote' },
      el('blockquote', { text: `“${t.quote.replace(/^["“]|["”]$/g, '')}”` }),
      el('figcaption', { text: [t.name, t.role].filter(Boolean).join(', ') }))));
  }
  function renderContact() {
    const c = data.site.contact;
    setText('#contact-title', c.heading);
    setText('#contact-body', c.body);
    const alt = $('#contact-alt');
    const parts = [];
    if (c.email) {
      const email = el('span', { class: 'email', text: c.email });
      const copy = el('button', { type: 'button', class: 'copy', text: 'Copy' });
      copy.addEventListener('click', () => {
        const done = () => { copy.textContent = 'Copied'; copy.classList.add('is-done'); setTimeout(() => { copy.textContent = 'Copy'; copy.classList.remove('is-done'); }, 1800); };
        const select = () => { const r = document.createRange(); r.selectNodeContents(email); const sel = getSelection(); sel.removeAllRanges(); sel.addRange(r); };
        navigator.clipboard ? navigator.clipboard.writeText(c.email).then(done).catch(select) : select();
      });
      parts.push('Email ', el('a', { href: `mailto:${c.email}`, class: 'email-link' }, email), copy);
    }
    if (c.whatsapp) parts.push(parts.length ? ', or ' : '', el('a', { href: `https://wa.me/${c.whatsapp}`, target: '_blank', rel: 'noopener', text: 'message me on WhatsApp' }));
    fill(alt, parts);
    alt.hidden = !parts.length;
    socialLinks($('#contact-social'), true);
  }

  // ---------- contact form ----------
  function setupForm() {
    const form = $('#contact-form');
    if (!form) return;
    const intent = $('#f-intent'), msgLabel = $('#f-msg-label'), msg = $('#f-msg'), company = $('#f-company-field');
    const copyFor = {
      role: ['About the role', 'The role, the team, and a link to the job post if there is one.'],
      project: ['About the project', 'What needs designing, for what business, and when you need it.'],
      other: ['Message', ''],
    };
    const applyIntent = () => {
      const [label, ph] = copyFor[intent.value] || ['Message', ''];
      msgLabel.textContent = label;
      msg.placeholder = ph;
      company.hidden = intent.value !== 'role';
    };
    intent.addEventListener('change', applyIntent);
    document.addEventListener('click', e => {
      const link = e.target.closest('[data-intent]');
      if (!link) return;
      intent.value = link.dataset.intent;
      applyIntent();
      const field = intent.closest('.field');
      field.classList.remove('has-error', 'is-filled');
      void field.offsetWidth;
      field.classList.add('is-filled');
    });

    const status = $('#form-status'), submit = $('#f-submit'), label = $('.btn-label', submit);
    const fields = $$('[required]', form);
    const check = input => {
      const ok = input.checkValidity() && input.value.trim() !== '';
      input.closest('.field').classList.toggle('has-error', !ok);
      input.setAttribute('aria-invalid', String(!ok));
      return ok;
    };
    fields.forEach(input => {
      input.addEventListener('blur', () => { if (input.value) check(input); });
      input.addEventListener('input', () => { if (input.closest('.field').classList.contains('has-error')) check(input); });
      input.addEventListener('change', () => check(input));
    });
    const showDone = () => {
      const from = form.offsetHeight;
      $('.form-fields', form).hidden = true;
      $('#form-done').hidden = false;
      const to = form.offsetHeight;
      if (!reduceMotion) {
        form.style.height = `${from}px`;
        requestAnimationFrame(() => { form.style.height = `${to}px`; });
        form.addEventListener('transitionend', () => { form.style.height = ''; }, { once: true });
      }
      $('#form-done').focus({ preventScroll: true });
    };
    form.addEventListener('submit', async e => {
      e.preventDefault();
      const invalid = fields.filter(f => !check(f));
      if (invalid.length) {
        status.textContent = invalid.length === 1 ? 'One field needs attention.' : `${invalid.length} fields need attention.`;
        invalid[0].focus();
        return;
      }
      const id = data?.site?.contact?.formspree_id;
      const local = ['localhost', '127.0.0.1', ''].includes(location.hostname) || location.protocol === 'file:';
      if (!id && local) { status.textContent = 'The form sends messages once the site is live on Netlify.'; return; }
      status.textContent = '';
      submit.classList.add('is-loading');
      label.textContent = 'Sending';
      try {
        const body = new FormData(form);
        const res = id
          ? await fetch(`https://formspree.io/f/${id}`, { method: 'POST', body, headers: { Accept: 'application/json' } })
          : await fetch('/', { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' }, body: new URLSearchParams(body).toString() });
        if (!res.ok) throw new Error(res.status);
        showDone();
      } catch {
        const email = data?.site?.contact?.email;
        status.textContent = `Your message didn't send. Check your connection and try again${email ? `, or email ${email}` : ''}.`;
      } finally {
        submit.classList.remove('is-loading');
        label.textContent = 'Send message';
      }
    });
  }

  // ---------- project page ----------
  function renderProject() {
    const slug = new URLSearchParams(location.search).get('p') || '';
    const list = data.projects;
    const p = list.find(x => x.slug === slug);
    if (!p) {
      document.title = `Project not found, ${data.site.name}`;
      setText('#p-title', 'That project isn’t here');
      setText('#p-summary', 'It may have been renamed or removed.');
      $('#p-facts').hidden = true;
      $('#p-layout').replaceChildren(el('p', { class: 'p-missing' }, el('a', { class: 'text-link', href: 'index.html#work', text: 'See all projects' })));
      return;
    }
    document.title = `${p.title}, ${data.site.name}`;
    const meta = $('meta[name="description"]');
    if (meta && p.summary) meta.setAttribute('content', p.summary);
    setText('#p-title', p.title);
    setText('#p-summary', p.summary);
    const facts = [['Client', p.client], ['My role', p.role], ['Type', p.category], ['Year', p.year], ['Tools', p.tools.join(', ')]].filter(([, v]) => v);
    fill($('#p-facts'), facts.map(([k, v]) => el('div', {}, el('dt', { text: k }), el('dd', { text: v }))));
    $('#p-facts').hidden = !facts.length;

    // Every image on the page opens in the same lightbox, in reading order
    const all = [];
    const zoomable = (img, alt, caption) => {
      const item = { image: img, alt, caption };
      all.push(item);
      const btn = el('button', { type: 'button', 'aria-label': `Open ${caption || alt || 'image'} full size` }, picture(img, { alt, sizes: '(max-width: 960px) 100vw, 1100px' }));
      btn.addEventListener('click', () => lightbox.open(all, all.indexOf(item), btn));
      return btn;
    };
    if (p.cover) fill($('#p-cover'), [zoomable(p.cover, '', p.title)]);
    else $('#p-cover').remove();

    let stageNo = 0;
    const rail = [];
    const blocks = p.blocks.map(b => {
      switch (b.type) {
        case 'text': return el('section', { class: 'b-text' }, b.heading ? el('h2', { text: b.heading }) : null, ...paragraphs(b.body));
        case 'stage': {
          stageNo++;
          const id = `stage-${stageNo}`;
          rail.push({ id, label: b.label });
          return el('section', { class: 'b-stage', id },
            el('div', { class: 'b-stage-label' }, el('span', { text: String(stageNo) }), el('h2', { text: b.label })),
            ...paragraphs(b.body));
        }
        case 'image': return el('figure', { class: `b-image size-${b.size}` }, zoomable(b.image, b.alt, b.caption), b.caption ? el('figcaption', { text: b.caption }) : null);
        case 'gallery': return el('figure', { class: 'b-gallery' },
          el('div', { class: 'b-gallery-grid', style: `--cols:${b.columns}` }, ...b.images.map(g => zoomable(g.image, g.alt, b.caption))),
          b.caption ? el('figcaption', { text: b.caption }) : null);
        case 'quote': return el('figure', { class: 'b-quote' }, el('blockquote', { text: `“${b.text.replace(/^["“]|["”]$/g, '')}”` }), (b.name || b.role) ? el('figcaption', { text: [b.name, b.role].filter(Boolean).join(', ') }) : null);
        case 'video': return el('figure', { class: 'b-video' },
          el('div', { class: 'b-video-frame' }, el('iframe', { src: b.embed, title: b.caption || 'Project video', loading: 'lazy', allow: 'autoplay; fullscreen; picture-in-picture', allowfullscreen: true })),
          b.caption ? el('figcaption', { text: b.caption }) : null);
        default: return null;
      }
    }).filter(Boolean);
    fill($('#p-blocks'), blocks);

    if (rail.length > 1) {
      $('#p-layout').classList.add('has-rail');
      $('#p-rail').hidden = false;
      const links = rail.map(r => el('a', { href: `#${r.id}`, text: r.label }));
      fill($('#p-rail-list'), links.map(a => el('li', {}, a)));
      if ('IntersectionObserver' in window) {
        const io = new IntersectionObserver(entries => {
          entries.forEach(e => {
            if (!e.isIntersecting) return;
            links.forEach(a => a.toggleAttribute('aria-current', a.getAttribute('href') === `#${e.target.id}`));
            links.forEach(a => { if (a.hasAttribute('aria-current')) a.setAttribute('aria-current', 'true'); });
          });
        }, { rootMargin: '-20% 0px -70% 0px' });
        rail.forEach(r => io.observe(document.getElementById(r.id)));
      }
    }

    if (list.length > 1) {
      const next = list[(list.indexOf(p) + 1) % list.length];
      const a = $('#p-next-link');
      a.textContent = next.title;
      a.href = `project.html?p=${encodeURIComponent(next.slug)}`;
      $('#p-next').hidden = false;
    }
  }

  // ---------- boot ----------
  function fail() {
    const msg = 'The portfolio content didn’t load. Refresh the page to try again.';
    const target = page === 'home' ? $('#gallery') : $('#p-blocks');
    if (target) target.replaceChildren(el('p', { class: 'empty', text: msg }));
    if (page === 'project') setText('#p-title', 'Project');
  }
  fetch('content/build/site-data.json', { cache: 'no-cache' })
    .then(r => { if (!r.ok) throw new Error(r.status); return r.json(); })
    .then(json => {
      data = json;
      data.site = data.site || {};
      data.gallery = Array.isArray(data.gallery) ? data.gallery : [];
      data.projects = Array.isArray(data.projects) ? data.projects : [];
      applySite();
      if (page === 'home') {
        // Each section renders on its own, so a problem in one never blanks the rest.
        [renderHero, renderGallery, renderWays, renderProjects, renderProcess, renderAbout, renderQuotes, renderContact].forEach(fn => {
          try { fn(); } catch (err) { console.error(fn.name, err); }
        });
        navMarker();
      } else if (page === 'project') {
        try { renderProject(); } catch (err) { console.error(err); fail(); }
      }
    })
    .catch(err => { console.error(err); fail(); });
  if (page === 'home') setupForm();
})();
