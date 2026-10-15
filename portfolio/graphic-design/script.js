// Project filter
const chips = document.querySelectorAll('.chip');
const projects = document.querySelectorAll('.project');
chips.forEach(chip => {
  chip.addEventListener('click', () => {
    const filter = chip.dataset.filter;
    chips.forEach(c => {
      const on = c === chip;
      c.classList.toggle('is-active', on);
      c.setAttribute('aria-pressed', on);
    });
    projects.forEach(p => {
      p.hidden = filter !== 'all' && p.dataset.type !== filter;
    });
  });
});

// Service links preselect the project type in the form
const typeSelect = document.getElementById('f-type');
document.querySelectorAll('[data-project]').forEach(link => {
  link.addEventListener('click', () => {
    if (typeSelect) typeSelect.value = link.dataset.project;
  });
});

// Copy email
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

// Contact form: validate, then submit to Formspree (or show a note if not connected yet)
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
      status.textContent = 'Thanks. Your message is in. I reply within 24 hours.';
    } catch {
      status.textContent = 'That didn’t send. Please try WhatsApp or email instead.';
    }
  });
}

const year = document.getElementById('year');
if (year) year.textContent = new Date().getFullYear();
