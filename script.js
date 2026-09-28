// Mark JS as available — CSS uses html.js to gate scroll-reveal animations,
// so content stays visible by default if this script fails to load.
document.documentElement.classList.add('js');

document.addEventListener('DOMContentLoaded', function () {
  initHeaderScrollState();
  initScrollReveal();
  initFaqAccordion();
  initStickyCta();
});

/* ---------- Copy account number ---------- */
function copyAccount() {
  var text = document.getElementById('acct-num').textContent.trim();
  var btn = document.getElementById('copy-btn');

  function done() {
    btn.textContent = 'Copied!';
    btn.classList.add('copied');
    setTimeout(function () {
      btn.textContent = 'Copy';
      btn.classList.remove('copied');
    }, 1800);
  }

  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(text).then(done).catch(function () {
      fallbackCopy(text, done);
    });
  } else {
    fallbackCopy(text, done);
  }
}

function fallbackCopy(text, cb) {
  var ta = document.createElement('textarea');
  ta.value = text;
  ta.style.position = 'fixed';
  ta.style.opacity = '0';
  document.body.appendChild(ta);
  ta.select();
  try { document.execCommand('copy'); } catch (e) { /* no-op */ }
  document.body.removeChild(ta);
  cb();
}

/* ---------- Sticky header shadow on scroll ---------- */
function initHeaderScrollState() {
  var header = document.querySelector('header');
  if (!header) return;
  var onScroll = function () {
    header.classList.toggle('is-scrolled', window.scrollY > 8);
  };
  onScroll();
  window.addEventListener('scroll', onScroll, { passive: true });
}

/* ---------- Scroll-reveal for sections and cards ---------- */
function initScrollReveal() {
  var targets = document.querySelectorAll('.reveal');
  if (!targets.length) return;

  // Respect reduced-motion: reveal everything immediately, skip the observer.
  var prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (prefersReduced || !('IntersectionObserver' in window)) {
    targets.forEach(function (el) { el.classList.add('in-view'); });
    return;
  }

  var observer = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      if (entry.isIntersecting) {
        entry.target.classList.add('in-view');
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.15, rootMargin: '0px 0px -40px 0px' });

  targets.forEach(function (el) { observer.observe(el); });
}

/* ---------- FAQ accordion ---------- */
function initFaqAccordion() {
  var triggers = document.querySelectorAll('.faq-trigger');
  triggers.forEach(function (trigger) {
    trigger.addEventListener('click', function () {
      var item = trigger.closest('.faq-item');
      var isOpen = item.getAttribute('data-open') === 'true';
      item.setAttribute('data-open', isOpen ? 'false' : 'true');
      trigger.setAttribute('aria-expanded', isOpen ? 'false' : 'true');
    });
  });
}

/* ---------- Sticky mobile CTA: show after the hero, hide while the payment
   section or final CTA is on screen (they already have their own buttons) ---------- */
function initStickyCta() {
  var bar = document.getElementById('sticky-cta');
  var hero = document.querySelector('.hero');
  if (!bar || !hero || !('IntersectionObserver' in window)) return;
  var link = bar.querySelector('a');
  var onScreen = new Set();

  var sync = function () {
    var show = onScreen.size === 0;
    bar.classList.toggle('is-visible', show);
    bar.setAttribute('aria-hidden', show ? 'false' : 'true');
    link.tabIndex = show ? 0 : -1;
    document.body.classList.toggle('sticky-on', show);
  };

  var observer = new IntersectionObserver(function (entries) {
    entries.forEach(function (e) {
      if (e.isIntersecting) onScreen.add(e.target); else onScreen.delete(e.target);
    });
    sync();
  });
  [hero].concat(Array.prototype.slice.call(document.querySelectorAll('.payment, .final-cta')))
    .forEach(function (el) { observer.observe(el); });
}
