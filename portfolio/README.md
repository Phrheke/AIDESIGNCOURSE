# Portfolio sites

Two static portfolio sites, built from the research in [RESEARCH.md](RESEARCH.md) and checked against the AI-design tells in [AI-TELLS.md](AI-TELLS.md).

| Site | Folder | What it is |
|---|---|---|
| Graphic design (Ndifreke Akpan) | `graphic-design/` | Gallery-first portfolio for both job offers and freelance clients, with Behance-style project pages and an admin at `/admin` for updating everything without code. |
| Video editing | `video-editing/` | Editing-suite grey with YouTube Studio blue. Draggable raw-vs-edited wipe in the hero and a timeline that shows the cut. Edited in code. |

---

## Graphic design site

### What's on it
- **Top gallery** of your best work. Any image shape works; nothing is cropped. Click any image to view it full size, with arrows, swipe and keyboard.
- **Two ways to work with you**: "Join your team" for companies hiring (with optional CV download and LinkedIn link) and "Hire me for a project" for freelance clients. Either can be switched off.
- **Projects** with their own pages, built from blocks like on Behance: text, images, image grids, client quotes, videos, and **process stages** (Inspiration, Design, Client feedback, Revisions, Final delivery). Stages become a step guide beside the page.
- **How I work**: your process, with feedback drawn as a loop back to design.
- **About**, optional **experience** and **client quotes**, and **contact** with a form, email, WhatsApp, and LinkedIn, Instagram and Behance links.

### Putting it live (one-time, about 15 minutes)

The site is hosted free on Netlify. The admin saves your changes to GitHub, and Netlify rebuilds the site about a minute later.

1. **Merge this branch into `main`.** The admin saves to `main`.
2. **Create the Netlify site.** On [netlify.com](https://app.netlify.com), click *Add new site*, then *Import an existing project*, then GitHub, and pick `Phrheke/AIDESIGNCOURSE`. Set **Base directory** to `portfolio/graphic-design`. The build command and publish folder are read from `netlify.toml`. Deploy.
3. **Let the admin log in with GitHub.**
   - On GitHub go to *Settings*, *Developer settings*, *OAuth Apps*, *New OAuth App*. Use your Netlify address (e.g. `https://ndifreke.netlify.app`) as the homepage URL and `https://api.netlify.com/auth/done` as the callback URL. Copy the Client ID and generate a Client secret.
   - In Netlify go to *Site configuration*, *Access & security*, *OAuth*, *Install provider*, choose GitHub, and paste both.
4. **Open `https://your-site.netlify.app/admin`** and log in with GitHub.
5. **Turn on form notifications.** In Netlify go to *Forms* and add your email under notifications, so messages from the contact form reach you.

If you later move the portfolio to its own GitHub repository, change `repo:` at the top of `graphic-design/admin/config.yml`.

### Using the admin

| Section | What you change there |
|---|---|
| **Top gallery** | Add, remove and drag to reorder gallery images. Add a caption and optionally link each image to a project. |
| **Projects** | *New Project* to add work. Fill in the title, summary, cover and details, then add blocks for the page. Turn on *Hide this project* to keep a draft offline. *Position on the homepage* sets the order. |
| **Text and links** | Your name, intro, availability, both "ways to work" cards (including CV upload), process steps, about text and photo, tools, experience, client quotes, email, WhatsApp, and LinkedIn, Instagram and Behance links. You can paste the full link or just your username. |

The right-hand side of every editing screen shows a live preview in the site's own styles.

### Why it doesn't break
- **Length limits** on every field in the admin, with the limit written under the field. The build step also shortens anything that slips past.
- **Any image size or shape.** The gallery and project pages keep each image's shape. Cards crop to a fixed frame, and you choose which part stays in view. On Netlify, large uploads are resized automatically, so a 10 MB photo still loads fast.
- **Missing or deleted images** show a quiet "Image not found" box instead of a broken icon. A project with a missing cover uses its first image instead.
- **Mistakes in content** (an unknown block, a bad video link, a broken file) are skipped with a warning in the Netlify deploy log. The site still builds.
- **Text is always inserted as text**, so nothing typed into the admin can break the page layout or inject code.
- Empty sections (no quotes yet, no experience, no CV, no social links) simply don't appear.

### Before launch
- [ ] Replace the 9 sample gallery images and 3 sample projects (they say "Replace in /admin").
- [ ] Delete the grey note at the top of `graphic-design/index.html`.
- [ ] In *Text and links*: set your real email, WhatsApp, and LinkedIn, Instagram and Behance links. They are hidden until you add them.
- [ ] Check the About photo is you, and update the bio.
- [ ] Optionally upload your CV and add your experience.

### Working on it locally (optional, for developers)
```bash
cd portfolio/graphic-design
node scripts/build-content.mjs        # rebuild content/build/site-data.json after editing content by hand
python3 -m http.server 8000           # http://localhost:8000
# Admin against local files: run `npx decap-server` from the repository root, then open /admin
```

---

## Video editing site

Edited directly in `video-editing/index.html` and `script.js`. Replace `yourname`, the email, WhatsApp link, Formspree ID (`YOUR_FORM_ID`) and social links, delete the grey template note, then:

- [ ] **Raw vs edited clips** (the most important item): the site already plays two sample clips. Pick one 6–10 second moment from your own work and export it twice at the same length: once straight from the camera, once finished (graded, reframed, captioned). Use 1280×720, H.264 MP4, no audio, under 2 MB each. Save them over `video-editing/assets/sample-raw.mp4` and `sample-edit.mp4`, and replace the two `-poster.jpg` stills with a frame from each. Optionally export `.webm` copies with the same names for older browsers.
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
