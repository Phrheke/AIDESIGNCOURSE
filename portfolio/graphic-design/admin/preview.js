/*
  Live previews in the admin: as you type, the right-hand pane shows the content
  with the site's own styles, so you can see how long text or new images will look.
*/
(function () {
  if (!window.CMS) return;
  var h = window.h;
  var createClass = window.createClass;
  CMS.registerPreviewStyle('/styles.css');
  CMS.registerPreviewStyle('https://fonts.googleapis.com/css2?family=Schibsted+Grotesk:wght@400;500;700;800;900&display=swap');

  function toJS(v) { return v && v.toJS ? v.toJS() : v; }
  function asset(getAsset, path) { if (!path) return ''; var a = getAsset(path); return a ? a.toString() : path; }
  function paras(text) {
    return String(text || '').split(/\n{2,}/).filter(Boolean).map(function (t, i) { return h('p', { key: i }, t); });
  }
  function img(getAsset, path, alt) {
    if (!path) return h('div', { className: 'img-missing' }, 'No image yet');
    return h('img', { src: asset(getAsset, path), alt: alt || '', style: { width: '100%', height: 'auto' } });
  }
  function note(text) {
    return h('p', { style: { background: '#F4F3EF', padding: '10px 14px', fontSize: '14px', margin: '0 0 24px' } }, text);
  }

  var STAGES = { inspiration: 'Inspiration', research: 'Research', design: 'Design', feedback: 'Client feedback', revisions: 'Revisions', final: 'Final delivery', custom: 'Stage' };

  // ---------- Project ----------
  var ProjectPreview = createClass({
    render: function () {
      var d = toJS(this.props.entry.get('data')) || {};
      var getAsset = this.props.getAsset;
      var stageNo = 0;
      var facts = [['Client', d.client], ['My role', d.role], ['Type', d.category], ['Year', d.year], ['Tools', (d.tools || []).join(', ')]].filter(function (f) { return f[1]; });
      var blocks = (d.blocks || []).map(function (b, i) {
        if (!b) return null;
        if (b.type === 'text') return h('section', { key: i, className: 'b-text' }, b.heading ? h('h2', {}, b.heading) : null, paras(b.body));
        if (b.type === 'stage') {
          stageNo++;
          return h('section', { key: i, className: 'b-stage' },
            h('div', { className: 'b-stage-label' }, h('span', {}, String(stageNo)), h('h2', {}, b.label || STAGES[b.stage] || 'Stage')),
            paras(b.body));
        }
        if (b.type === 'image') return h('figure', { key: i, className: 'b-image size-' + (b.size || 'wide') }, img(getAsset, b.image, b.alt), b.caption ? h('figcaption', {}, b.caption) : null);
        if (b.type === 'gallery') return h('figure', { key: i, className: 'b-gallery' },
          h('div', { className: 'b-gallery-grid', style: { '--cols': b.columns || 2 } }, (b.images || []).map(function (g, j) { return h('div', { key: j }, img(getAsset, g && g.image, g && g.alt)); })),
          b.caption ? h('figcaption', {}, b.caption) : null);
        if (b.type === 'quote') return h('figure', { key: i, className: 'b-quote' }, h('blockquote', {}, '“' + (b.text || '') + '”'), h('figcaption', {}, [b.name, b.role].filter(Boolean).join(', ')));
        if (b.type === 'video') return h('figure', { key: i, className: 'b-video' }, h('div', { className: 'b-video-frame', style: { display: 'grid', placeItems: 'center', color: '#fff' } }, 'Video: ' + (b.url || 'add a link')), b.caption ? h('figcaption', {}, b.caption) : null);
        return null;
      });
      return h('div', { style: { padding: '24px' } },
        d.draft ? note('This project is a draft and is hidden from the site.') : null,
        h('section', { className: 'p-head', style: { paddingTop: 0 } },
          h('h1', {}, d.title || 'Untitled project'),
          d.summary ? h('p', { className: 'lead' }, d.summary) : null,
          facts.length ? h('dl', { className: 'p-facts' }, facts.map(function (f, i) { return h('div', { key: i }, h('dt', {}, f[0]), h('dd', {}, f[1])); })) : null),
        d.cover ? h('figure', { className: 'p-cover' }, img(getAsset, d.cover, '')) : null,
        h('article', { className: 'p-blocks' }, blocks));
    },
  });

  // ---------- Gallery ----------
  var GalleryPreview = createClass({
    render: function () {
      var d = toJS(this.props.entry.get('data')) || {};
      var getAsset = this.props.getAsset;
      var images = d.images || [];
      var cols = [[], [], []];
      images.forEach(function (it, i) { cols[i % 3].push(it); });
      return h('div', { style: { padding: '24px' } },
        note('The live site arranges these in 2 to 4 columns depending on screen width, keeping each image\'s shape.'),
        h('div', { className: 'gallery' }, cols.map(function (col, c) {
          return h('div', { key: c, className: 'g-col' }, col.map(function (it, i) {
            return h('figure', { key: i, className: 'g-item' },
              h('div', { className: 'g-open' }, img(getAsset, it && it.image, it && it.alt)),
              it && it.title ? h('div', { className: 'g-cap' }, h('span', {}, it.title)) : null);
          }));
        })));
    },
  });

  // ---------- Homepage text ----------
  var SitePreview = createClass({
    render: function () {
      var d = toJS(this.props.entry.get('data')) || {};
      var getAsset = this.props.getAsset;
      var av = d.availability || {}, hire = d.hire || {}, fr = d.freelance || {}, pr = d.process || {}, ab = d.about || {}, ct = d.contact || {};
      return h('div', {},
        h('section', { className: 'hero', style: { paddingBottom: '24px' } },
          h('div', { className: 'wrap' },
            h('div', { className: 'hero-intro' },
              h('div', {}, h('h1', {}, d.name || 'Your name'), h('p', { className: 'hero-role' }, [d.role, d.location].filter(Boolean).join(', '))),
              h('div', { className: 'hero-side' },
                h('p', { className: 'hero-text' }, d.intro),
                h('ul', { className: 'availability' },
                  av.full_time ? h('li', {}, av.full_time_note) : null,
                  av.freelance ? h('li', {}, av.freelance_note) : null))))),
        h('section', { className: 'ways' },
          h('div', { className: 'wrap ways-grid' },
            av.full_time ? h('article', { className: 'way' }, h('h2', {}, hire.heading), h('div', { className: 'way-body' }, paras(hire.body)), h('div', { className: 'way-actions' }, h('span', { className: 'btn btn-primary' }, hire.button))) : null,
            av.freelance ? h('article', { className: 'way' }, h('h2', {}, fr.heading), h('div', { className: 'way-body' }, paras(fr.body)),
              h('ul', { className: 'services' }, (fr.services || []).map(function (s, i) { return h('li', { key: i }, s); })),
              h('div', { className: 'way-actions' }, h('span', { className: 'btn btn-primary' }, fr.button))) : null)),
        h('section', { className: 'process' },
          h('div', { className: 'wrap' },
            h('div', { className: 'process-head' }, h('h2', {}, pr.heading), h('p', {}, pr.intro)),
            h('ol', { className: 'steps', style: { '--n': (pr.steps || []).length || 1 } }, (pr.steps || []).map(function (s, i) {
              return h('li', { key: i, className: 'step' + (s && s.loops_back ? ' is-loop' : '') },
                h('span', { className: 'step-num' }, String(i + 1)), h('h3', {}, s && s.title), h('p', {}, s && s.body),
                s && s.loops_back ? h('p', { style: { color: '#F5C400', fontWeight: 700, fontSize: '14px' } }, (pr.loop_label || 'Loops back') + ' (to step ' + i + ')') : null);
            })))),
        h('section', { className: 'about' },
          h('div', { className: 'wrap about-grid' + (ab.photo ? '' : ' no-photo') },
            ab.photo ? h('div', { className: 'about-photo-wrap' }, img(getAsset, ab.photo, '')) : null,
            h('div', { className: 'about-copy' }, h('h2', {}, ab.heading), h('div', {}, paras(ab.body))))),
        h('section', { className: 'contact' },
          h('div', { className: 'wrap' }, h('h2', {}, ct.heading), h('p', {}, ct.body), h('p', {}, ct.email))));
    },
  });

  CMS.registerPreviewTemplate('projects', ProjectPreview);
  CMS.registerPreviewTemplate('gallery', GalleryPreview);
  CMS.registerPreviewTemplate('site', SitePreview);
})();
