# Portfolio sites

Two static portfolio sites, built from the research in [RESEARCH.md](RESEARCH.md).

| Site | Folder | Style |
|---|---|---|
| Graphic design | `graphic-design/` | White page, black type, cobalt accent, print details (crop marks, colour specs). Light and dark mode. |
| Video editing | `video-editing/` | Dark by design, amber accent, timeline and timecode details. Reel first. |

No build step and no framework. Open `index.html` in a browser, or serve the folder:

```bash
cd portfolio && python3 -m http.server 8000
# http://localhost:8000/graphic-design/   http://localhost:8000/video-editing/
```

Each folder is self-contained, so you can deploy either one on its own (Netlify drop, Vercel, GitHub Pages, Cloudflare Pages).

---

## Page structure (both sites)

1. **Hero**: who you help, what you make, one button, proof visible straight away
2. **Client strip**: names or logos
3. **Work**: strongest first, sorted by the kind of job a client is hiring for, one-line result under each
4. **Mid-page call to action**
5. **Services / pricing**: what's included, how long, "from" price
6. **Process**: what happens after someone gets in touch
7. **About** (design site)
8. **FAQ**: price, timing, revisions, rights
9. **Testimonials**: right above the form
10. **Contact**: 4-field form + WhatsApp + email

The header button stays visible while scrolling, on phones too.

---

## Replace checklist

Everything marked as a placeholder must be replaced before you publish. **Never publish the sample quotes, client names or numbers as if they were real.**

### Both sites
- [ ] `yourname`: search and replace across all files (wordmark, titles, about text, footer)
- [ ] Delete the grey "Template preview" banner at the top of each `index.html`
- [ ] Hero headline: name your real niche and audience
- [ ] Client strip: real clients only (with permission)
- [ ] Testimonials: real quotes with full name, role and business
- [ ] Prices in Services/Pricing and the FAQ (switch currency if your clients pay in ₦)
- [ ] WhatsApp link: `https://wa.me/234XXXXXXXXXX` (country code, no `+` or leading `0`)
- [ ] Email address
- [ ] Social links in the footer
- [ ] **Contact form**: create a free form at [formspree.io](https://formspree.io), then replace `YOUR_FORM_ID` in the form's `action`. Until then the form shows "Form not connected yet" instead of sending.

### Graphic design site
- [ ] Project tiles: replace the CSS placeholder tiles (`.tile-kora`, `.tile-lumen`, …) with real mockup images, 1600×1200, `.webp`, under 300 KB each. Keep 4–8 projects.
- [ ] Case studies: duplicate `work/mos-world-of-scents.html` for each project and keep the same section order. Point each card's link at its own page.
- [ ] Outcome numbers on the case study page (`3×`, `12`, `6`): use real figures only, or describe what the client did with the work
- [ ] About photo: `assets/instructor.webp` is currently used; swap it if it isn't you

### Video editing site
- [ ] **Reel loop**: export a silent 10–15 second loop of your best cuts as `video-editing/assets/reel-loop.mp4` (1280×720, H.264, under 3 MB). Until then a styled placeholder shows.
- [ ] **Full reel**: upload a 60–90 second reel to YouTube and put its 11-character ID in both `data-video="REEL_VIDEO_ID"` attributes
- [ ] **Each video**: put its YouTube ID in `data-video` (players only load when clicked) and set a real thumbnail as the button's `background-image`
- [ ] Raw vs edited: upload both versions and set the IDs in `script.js` (`versions.raw.id`, `versions.edit.id`)
- [ ] Retention chart: replace the `retention` array in `script.js` with real numbers from YouTube Studio (Analytics → Engagement → Audience retention), with the creator's permission
- [ ] Hero stats (`48M+`, `+38%`, `600+`, `72h`) and every result chip under the videos

---

## Before launch

- [ ] Run [PageSpeed Insights](https://pagespeed.web.dev/) on the live URL. Aim for 90+ on mobile.
- [ ] Test the form by sending yourself a message
- [ ] Check every page on a real phone
- [ ] Add analytics (Plausible, Umami or GA4) and track form submissions as the main goal
