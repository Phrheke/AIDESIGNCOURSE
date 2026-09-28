// Mark JS as available — CSS uses html.js to gate scroll-reveal animations,
// so content stays visible by default if this script fails to load.
document.documentElement.classList.add('js');

document.addEventListener('DOMContentLoaded', function () {
  initHeaderScrollState();
  initScrollReveal();
  initFaqAccordion();
  initWorkGallery();
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

/* ---------- Student work gallery arrows ---------- */
function initWorkGallery() {
  var track = document.getElementById('work-track');
  if (!track) return;
  // Hide the arrows when every card already fits on screen.
  var nav = document.querySelector('.work-nav');
  var syncNav = function () {
    if (nav) nav.style.visibility = track.scrollWidth > track.clientWidth + 1 ? '' : 'hidden';
  };
  syncNav();
  window.addEventListener('resize', syncNav);
  document.querySelectorAll('.work-arrow').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var card = track.querySelector('.work-card');
      var step = card ? card.getBoundingClientRect().width + 20 : 300;
      track.scrollBy({ left: step * Number(btn.getAttribute('data-dir')), behavior: 'smooth' });
    });
  });
}
