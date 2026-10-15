# Portfolio sites

Two static portfolio sites, built from the research in [RESEARCH.md](RESEARCH.md) and checked against the AI-design tells in [AI-TELLS.md](AI-TELLS.md).

| Site | Folder | Style |
|---|---|---|
| Graphic design | `graphic-design/` | White paper, black ink, Lagos danfo yellow only on things you can click. Draggable before/after in the hero. |
| Video editing | `video-editing/` | Editing-suite grey with YouTube Studio blue. Draggable raw-vs-edited wipe in the hero and a timeline that shows the cut. |

No build step and no framework. Open `index.html` in a browser, or serve the folder:

```bash
cd portfolio && python3 -m http.server 8000
# http://localhost:8000/graphic-design/   http://localhost:8000/video-editing/
```

Each folder is self-contained, so you can deploy either one on its own (Netlify drop, Vercel, GitHub Pages, Cloudflare Pages).

---

## Page structure

**Graphic design:** headline + before/after wipe → clients in a sentence → work (filterable) → price list → process (by day) → about → FAQ → quotes + contact form.

**Video editing:** headline + raw-vs-edited wipe with "what changed" → the cut on a timeline → retention result → work by format → monthly packages → process (by day) → FAQ → quotes + contact form.

The header button stays visible while scrolling, on phones too.

---

## Replace checklist

Everything marked as a placeholder must be replaced before you publish. **Never publish the sample quotes, client names or numbers as if they were real.**

### Both sites
- [ ] `yourname`: search and replace across all files (wordmark, titles, about text, footer)
- [ ] Delete the "This is a template" note at the top of each `index.html`
- [ ] Hero headline: name your real niche and audience
- [ ] Client strip: real clients only (with permission)
- [ ] Testimonials: real quotes with full name, role and business
- [ ] Prices in Services/Pricing and the FAQ (switch currency if your clients pay in ₦)
- [ ] WhatsApp link: `https://wa.me/234XXXXXXXXXX` (country code, no `+` or leading `0`)
- [ ] Email address
- [ ] Social links in the footer
- [ ] **Contact form**: create a free form at [formspree.io](https://formspree.io), then replace `YOUR_FORM_ID` in the form's `action`. Until then the form shows "Form not connected yet" instead of sending.

### Graphic design site
- [ ] Before/after in the hero: use your strongest redesign. Both images should share a layout so the wipe lines up.
- [ ] Project tiles: replace the CSS placeholder tiles (`.tile-kora`, `.tile-lumen`, …) with real mockup images, `.webp`, under 300 KB each. Keep 4–8 projects.
- [ ] Case studies: duplicate `work/mos-world-of-scents.html` for each project and keep the same section order. Point each card's link at its own page.
- [ ] Outcome numbers on the case study page (`3×`, `12`, `6`): use real figures only, or describe what the client did with the work
- [ ] About photo: `assets/instructor.webp` is currently used; swap it if it isn't you

### Video editing site
- [ ] **Raw vs edited clips** (the most important item): pick one 6–10 second moment. Export it twice at the same length, once straight from the camera and once finished (graded, reframed, captioned), both 1280×720 H.264, muted, under 2 MB each. Put them in `video-editing/assets/` and set `data-raw-src="assets/raw.mp4"` and `data-edit-src="assets/edit.mp4"` on the `.ba` element in `index.html`. The sample illustration is replaced automatically and both clips play in sync under the wipe.
- [ ] **"What changed" list**: rewrite the four items for your real example (timecodes, seconds cut).
- [ ] **The cut timeline**: edit the `clips` array in `script.js` with your real edit decisions (start and end seconds of each kept and cut section, and the order kept sections appear in the edit). The raw and edited lengths update automatically.
- [ ] **Full reel**: upload a 60–90 second reel to YouTube and put its 11-character ID in `data-video="REEL_VIDEO_ID"`
- [ ] **Each video**: put its YouTube ID in `data-video` (players only load when clicked) and set a real thumbnail as the button's `background-image`
- [ ] Retention chart: replace the `retention` array in `script.js` with real numbers from YouTube Studio (Analytics → Engagement → Audience retention), with the creator's permission, and update the 34% → 52% sentence
- [ ] Every result line under the videos

---

## Before launch

- [ ] Run [PageSpeed Insights](https://pagespeed.web.dev/) on the live URL. Aim for 90+ on mobile.
- [ ] Test the form by sending yourself a message
- [ ] Check every page on a real phone
- [ ] Add analytics (Plausible, Umami or GA4) and track form submissions as the main goal
