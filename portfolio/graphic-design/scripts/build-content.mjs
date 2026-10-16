// Builds content/build/site-data.json from the files the admin edits.
// Runs on every deploy (see netlify.toml) and locally with: node scripts/build-content.mjs
// It never stops a deploy: bad or missing content is cleaned up or dropped, with a warning in the log.
import { readFileSync, writeFileSync, readdirSync, existsSync, mkdirSync, openSync, readSync, closeSync, statSync } from 'node:fs';
import { join, dirname, extname, basename } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const warnings = [];
const warn = msg => { warnings.push(msg); console.warn(`  ! ${msg}`); };

// ---------- small helpers ----------
const readJSON = (rel, fallback) => {
  const file = join(ROOT, rel);
  if (!existsSync(file)) { warn(`${rel} is missing, using defaults`); return fallback; }
  try { return JSON.parse(readFileSync(file, 'utf8')); }
  catch (e) { warn(`${rel} could not be read (${e.message}), using defaults`); return fallback; }
};
const str = (v, max, field) => {
  if (v === null || v === undefined) return '';
  let s = String(v).replace(/\r\n?/g, '\n').replace(/[\u0000-\u0008\u000B\u000C\u000E-\u001F]/g, '').trim();
  if (max && s.length > max) {
    warn(`${field} was ${s.length} characters, shortened to ${max}`);
    s = s.slice(0, max - 1).replace(/\s+\S*$/, '') + '…';
  }
  return s;
};
const bool = v => v === true || v === 'true';
const list = v => (Array.isArray(v) ? v : []);
const slugify = s => String(s || '').toLowerCase().normalize('NFKD').replace(/[̀-ͯ]/g, '')
  .replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 60) || 'project';

// ---------- image sizes (PNG, JPEG, GIF, WebP, SVG) so the page can reserve space and never jump ----------
function imageSize(file) {
  try {
    const ext = extname(file).toLowerCase();
    if (ext === '.svg') {
      const s = readFileSync(file, 'utf8').slice(0, 2000);
      const w = s.match(/\swidth="([\d.]+)/), h = s.match(/\sheight="([\d.]+)/);
      if (w && h) return { w: Math.round(+w[1]), h: Math.round(+h[1]) };
      const vb = s.match(/viewBox="[\d.\s-]*?([\d.]+)\s+([\d.]+)"/);
      return vb ? { w: Math.round(+vb[1]), h: Math.round(+vb[2]) } : null;
    }
    const fd = openSync(file, 'r');
    const buf = Buffer.alloc(Math.min(statSync(file).size, 262144));
    readSync(fd, buf, 0, buf.length, 0);
    closeSync(fd);
    if (buf.readUInt32BE(0) === 0x89504e47) return { w: buf.readUInt32BE(16), h: buf.readUInt32BE(20) };
    if (buf.toString('ascii', 0, 3) === 'GIF') return { w: buf.readUInt16LE(6), h: buf.readUInt16LE(8) };
    if (buf.toString('ascii', 0, 4) === 'RIFF' && buf.toString('ascii', 8, 12) === 'WEBP') {
      const chunk = buf.toString('ascii', 12, 16);
      if (chunk === 'VP8 ') return { w: buf.readUInt16LE(26) & 0x3fff, h: buf.readUInt16LE(28) & 0x3fff };
      if (chunk === 'VP8L') { const b = buf.readUInt32LE(21); return { w: (b & 0x3fff) + 1, h: ((b >> 14) & 0x3fff) + 1 }; }
      if (chunk === 'VP8X') return { w: 1 + buf.readUIntLE(24, 3), h: 1 + buf.readUIntLE(27, 3) };
    }
    if (buf[0] === 0xff && buf[1] === 0xd8) {
      let i = 2;
      while (i < buf.length) {
        if (buf[i] !== 0xff) { i++; continue; }
        const marker = buf[i + 1];
        if (marker >= 0xc0 && marker <= 0xcf && ![0xc4, 0xc8, 0xcc].includes(marker)) {
          return { w: buf.readUInt16BE(i + 7), h: buf.readUInt16BE(i + 5) };
        }
        i += 2 + buf.readUInt16BE(i + 2);
      }
    }
  } catch { /* fall through */ }
  return null;
}
// Turn whatever the admin stored ("/uploads/a.jpg", "uploads/a.jpg", a full URL) into { src, w, h }.
function image(value, field) {
  const raw = str(typeof value === 'object' && value ? value.src || value.image : value, 600);
  if (!raw) return null;
  if (/^https?:\/\//i.test(raw)) return { src: raw, w: 0, h: 0, external: true };
  const clean = raw.replace(/^\.?\//, '');
  const file = join(ROOT, clean);
  if (!existsSync(file)) { warn(`${field}: image "${raw}" was not found, it will show as missing`); return { src: clean, w: 0, h: 0, missing: true }; }
  const size = imageSize(file);
  if (!size) warn(`${field}: couldn't read the size of "${raw}"`);
  const bytes = statSync(file).size;
  if (bytes > 5 * 1024 * 1024) warn(`${field}: "${raw}" is ${(bytes / 1048576).toFixed(1)} MB. It will still work, but smaller files load faster.`);
  return { src: clean, w: size?.w || 0, h: size?.h || 0 };
}
function fileRef(value, field) {
  const raw = str(value, 600);
  if (!raw) return '';
  if (/^https?:\/\//i.test(raw)) return raw;
  const clean = raw.replace(/^\.?\//, '');
  if (!existsSync(join(ROOT, clean))) { warn(`${field}: file "${raw}" was not found, hidden`); return ''; }
  return clean;
}
function socialUrl(value, platform) {
  let v = str(value, 300);
  if (!v) return '';
  if (/^https?:\/\//i.test(v)) return v;
  if (/^(www\.)?(linkedin|instagram|behance)\.(com|net)\//i.test(v)) return `https://${v.replace(/^www\./i, 'www.')}`;
  v = v.replace(/^@/, '');
  if (!/^[\w.-]+$/.test(v)) { warn(`social.${platform}: "${value}" isn't a link or a username, hidden`); return ''; }
  return { linkedin: `https://www.linkedin.com/in/${v}`, instagram: `https://www.instagram.com/${v}`, behance: `https://www.behance.net/${v}` }[platform];
}
function videoEmbed(url) {
  const u = str(url, 400);
  let m = u.match(/(?:youtube\.com\/(?:watch\?v=|shorts\/|embed\/)|youtu\.be\/)([\w-]{11})/);
  if (m) return { provider: 'youtube', id: m[1], embed: `https://www.youtube-nocookie.com/embed/${m[1]}?rel=0` };
  m = u.match(/vimeo\.com\/(?:video\/)?(\d+)/);
  if (m) return { provider: 'vimeo', id: m[1], embed: `https://player.vimeo.com/video/${m[1]}?dnt=1` };
  return null;
}

// ---------- site ----------
const s = readJSON('content/site.json', {});
const site = {
  name: str(s.name, 60, 'name') || 'Your name',
  role: str(s.role, 60, 'role'),
  location: str(s.location, 60, 'location'),
  intro: str(s.intro, 280, 'intro'),
  availability: {
    full_time: bool(s.availability?.full_time),
    full_time_note: str(s.availability?.full_time_note, 70, 'availability.full_time_note') || 'Open to full-time roles',
    freelance: bool(s.availability?.freelance),
    freelance_note: str(s.availability?.freelance_note, 70, 'availability.freelance_note') || 'Taking freelance projects',
  },
  hire: {
    heading: str(s.hire?.heading, 60, 'hire.heading') || 'Join your team',
    body: str(s.hire?.body, 600, 'hire.body'),
    cv: fileRef(s.hire?.cv, 'hire.cv'),
    button: str(s.hire?.button, 30, 'hire.button') || 'Talk about a role',
  },
  freelance: {
    heading: str(s.freelance?.heading, 60, 'freelance.heading') || 'Hire me for a project',
    body: str(s.freelance?.body, 600, 'freelance.body'),
    services: list(s.freelance?.services).map((x, i) => str(x, 60, `freelance.services[${i}]`)).filter(Boolean).slice(0, 12),
    button: str(s.freelance?.button, 30, 'freelance.button') || 'Start a project',
  },
  process: {
    heading: str(s.process?.heading, 60, 'process.heading') || 'How I work',
    intro: str(s.process?.intro, 400, 'process.intro'),
    loop_label: str(s.process?.loop_label, 60, 'process.loop_label') || 'Back for another round',
    steps: list(s.process?.steps).map((st, i) => ({
      title: str(st?.title, 40, `process.steps[${i}].title`),
      body: str(st?.body, 260, `process.steps[${i}].body`),
      loops_back: bool(st?.loops_back) && i > 0,
    })).filter(st => st.title).slice(0, 6),
  },
  about: {
    heading: str(s.about?.heading, 60, 'about.heading') || 'About me',
    photo: image(s.about?.photo, 'about.photo'),
    body: str(s.about?.body, 1500, 'about.body'),
    tools: list(s.about?.tools).map((x, i) => str(x, 40, `about.tools[${i}]`)).filter(Boolean).slice(0, 20),
    experience: list(s.about?.experience).map((e, i) => ({
      role: str(e?.role, 80, `about.experience[${i}].role`),
      company: str(e?.company, 80, `about.experience[${i}].company`),
      years: str(e?.years, 40, `about.experience[${i}].years`),
      note: str(e?.note, 200, `about.experience[${i}].note`),
    })).filter(e => e.role || e.company).slice(0, 12),
  },
  testimonials: list(s.testimonials).map((t, i) => ({
    quote: str(t?.quote, 320, `testimonials[${i}].quote`),
    name: str(t?.name, 60, `testimonials[${i}].name`),
    role: str(t?.role, 80, `testimonials[${i}].role`),
  })).filter(t => t.quote && t.name).slice(0, 6),
  contact: {
    heading: str(s.contact?.heading, 60, 'contact.heading') || "Let's talk",
    body: str(s.contact?.body, 300, 'contact.body'),
    email: /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(str(s.contact?.email, 120)) ? str(s.contact.email, 120) : '',
    whatsapp: str(s.contact?.whatsapp, 30).replace(/[^\d]/g, ''),
    formspree_id: str(s.contact?.formspree_id, 40).replace(/^https?:\/\/formspree\.io\/f\//, '').replace(/[^\w]/g, ''),
  },
  social: {
    linkedin: socialUrl(s.social?.linkedin, 'linkedin'),
    instagram: socialUrl(s.social?.instagram, 'instagram'),
    behance: socialUrl(s.social?.behance, 'behance'),
  },
  seo: {
    title: str(s.seo?.title, 70, 'seo.title'),
    description: str(s.seo?.description, 170, 'seo.description'),
    share_image: s.seo?.share_image ? image(s.seo.share_image, 'seo.share_image') : null,
  },
  // Resize images through Netlify's image CDN only when the build runs on Netlify.
  image_cdn: s.image_cdn !== false && process.env.NETLIFY === 'true',
};
if (!site.contact.email) warn('contact.email is empty or not a valid address');
if (site.process.steps.length < 2) warn('process has fewer than 2 steps, the section will be hidden');

// ---------- projects ----------
const STAGES = { inspiration: 'Inspiration', research: 'Research', design: 'Design', feedback: 'Client feedback', revisions: 'Revisions', final: 'Final delivery' };
const projectsDir = join(ROOT, 'content/projects');
const files = existsSync(projectsDir) ? readdirSync(projectsDir).filter(f => f.endsWith('.json')) : [];
const seen = new Set();
const projects = files.map(f => {
  const rel = `content/projects/${f}`;
  const p = readJSON(rel, null);
  if (!p || typeof p !== 'object') return null;
  if (bool(p.draft)) return null;
  let slug = slugify(basename(f, '.json'));
  while (seen.has(slug)) slug += '-2';
  seen.add(slug);
  const blocks = list(p.blocks).map((b, i) => {
    const where = `${rel} block ${i + 1}`;
    switch (b?.type) {
      case 'text': {
        const body = str(b.body, 3000, `${where} text`);
        const heading = str(b.heading, 80, `${where} heading`);
        return body || heading ? { type: 'text', heading, body } : null;
      }
      case 'stage': {
        const key = STAGES[b.stage] ? b.stage : 'custom';
        const label = str(b.label, 40, `${where} label`) || STAGES[key] || 'Stage';
        return { type: 'stage', stage: key, label, body: str(b.body, 1200, `${where} text`) };
      }
      case 'image': {
        const img = image(b.image, where);
        if (!img) return null;
        return { type: 'image', image: img, alt: str(b.alt, 200), caption: str(b.caption, 200, `${where} caption`), size: ['full', 'wide', 'normal'].includes(b.size) ? b.size : 'wide' };
      }
      case 'gallery': {
        const images = list(b.images).map((g, j) => {
          const img = image(g?.image ?? g, `${where} image ${j + 1}`);
          return img ? { image: img, alt: str(g?.alt, 200) } : null;
        }).filter(Boolean).slice(0, 12);
        if (!images.length) return null;
        const cols = Math.min(Math.max(parseInt(b.columns, 10) || 2, 2), 3);
        return { type: 'gallery', images, columns: Math.min(cols, images.length < 2 ? 1 : cols), caption: str(b.caption, 200, `${where} caption`) };
      }
      case 'quote': {
        const text = str(b.text, 400, `${where} quote`);
        return text ? { type: 'quote', text, name: str(b.name, 60), role: str(b.role, 80) } : null;
      }
      case 'video': {
        const v = videoEmbed(b.url);
        if (!v) { if (b.url) warn(`${where}: "${b.url}" isn't a YouTube or Vimeo link, skipped`); return null; }
        return { type: 'video', ...v, caption: str(b.caption, 200, `${where} caption`) };
      }
      default:
        if (b) warn(`${where}: unknown block type "${b.type}", skipped`);
        return null;
    }
  }).filter(Boolean);
  const cover = image(p.cover, `${rel} cover`) || blocks.find(b => b.type === 'image')?.image || blocks.find(b => b.type === 'gallery')?.images[0].image || null;
  if (!cover) warn(`${rel} has no cover image`);
  return {
    slug,
    title: str(p.title, 90, `${rel} title`) || 'Untitled project',
    category: str(p.category, 40, `${rel} category`),
    year: str(p.year, 10).replace(/[^\d–-]/g, ''),
    client: str(p.client, 60, `${rel} client`),
    role: str(p.role, 60, `${rel} role`),
    tools: list(p.tools).map(t => str(t, 30)).filter(Boolean).slice(0, 10),
    summary: str(p.summary, 220, `${rel} summary`),
    cover,
    cover_focus: ['top', 'center', 'bottom'].includes(p.cover_focus) ? p.cover_focus : 'center',
    featured: p.featured !== false,
    order: Number.isFinite(+p.order) ? +p.order : 999,
    blocks,
  };
}).filter(Boolean).sort((a, b) => a.order - b.order || (b.year || '').localeCompare(a.year || '') || a.title.localeCompare(b.title));

// ---------- gallery ----------
const g = readJSON('content/gallery.json', { images: [] });
const slugs = new Set(projects.map(p => p.slug));
const gallery = list(g.images).map((it, i) => {
  const img = image(it?.image, `gallery image ${i + 1}`);
  if (!img) return null;
  const project = slugify(it?.project || '');
  return { image: img, title: str(it?.title, 70, `gallery image ${i + 1} title`), alt: str(it?.alt, 200), project: it?.project && slugs.has(project) ? project : '' };
}).filter(Boolean).slice(0, 30);
if (!gallery.length) warn('the gallery has no images');

mkdirSync(join(ROOT, 'content/build'), { recursive: true });
writeFileSync(join(ROOT, 'content/build/site-data.json'), JSON.stringify({ site, gallery, projects }, null, 1));
console.log(`Built site data: ${gallery.length} gallery images, ${projects.length} projects, ${warnings.length} warning(s).`);
