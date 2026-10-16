# What makes a website look AI-made, and what these sites do instead

Collected from Reddit and Hacker News threads, design-studio write-ups, and two Claude design skills. Each tell is something people recognise on sight. None of them proves a model made a page. They're defaults nobody chose.

## What people actually say

From a study of 3,033 comments in 125 Reddit threads like "what are dead giveaways for AI slop websites" (ranked by share of comments):

| Rank | Tell | Share of comments |
|---|---|---|
| 1 | "Screams AI", soulless | 6.4% |
| 2 | "All looks the same", template, cookie-cutter | 6.1% |
| 3 | shadcn / Tailwind default look | 2.5% |
| 4 | Purple / violet ("AI purple") | 2.3% |
| 5 | Gradients everywhere, gradient text | 2.0% |
| 6 | Too many animations, fade-ins on everything | 1.1% |
| 7 | Rounded corners and pill buttons on everything | 0.8% |
| 8 | Dark mode with neon glow | 0.7% |
| 9 | Emoji and ✨ sparkles in copy | 0.5% |
| 10 | Generic sans font (Inter, Geist) | 0.4% |
| 11 | Three-column feature cards | 0.4% |
| 12 | Same hero: huge headline and two buttons | 0.2% |

The top-voted comment (373 upvotes, r/ClaudeAI): *"the purple-to-blue gradient is the biggest tell lol. also bento grid layouts, rounded corners on everything, hero section with gradient text that says 'transform your X', and way too much whitespace."* Another: *"Purple gradients and the urge to put a box around everything."*

## The full checklist

### The "tasteful" defaults (what AI does when told to avoid purple)
1. Cream background with a terracotta or clay accent
2. Near-black background with one acid-green, vermilion or neon accent
3. Small ALL-CAPS letter-spaced labels above every heading
4. Monospace font for little labels and stats
5. Meta lines joined with middle dots ("Brand · 2025 · Lagos")
6. One word in the headline coloured, italic or highlighted
7. Decorative 01 / 02 / 03 numbering on things that aren't steps
8. An arrow glued to every link and button ("Learn more →")
9. Fake browser or macOS window frames around a mock screen

### Type and colour
10. Inter, Roboto or the system font for everything
11. The "tasteful free font" set: Space Grotesk, Geist, Syne, Instrument Serif, Fraunces
12. Purple or indigo gradients, gradient-filled headline text
13. Indigo or violet buttons
14. Glowing coloured shadows
15. Grey text too light to read (below WCAG AA contrast)

### Layout
16. Centred hero with a pill badge, headline, subhead and two buttons
17. Three identical cards with an icon on top
18. A row of round numbers: "10,000+ users · 99.9% uptime · 4.9★"
19. Three pricing tiers with the middle one ringed "Most popular"
20. The stock section order: hero, logos, features, how it works, stats, testimonials, pricing, FAQ, CTA
21. Every section the same width
22. Four-column footer with a newsletter box

### Components
23. Same large radius and soft shadow on every box
24. Frosted-glass (backdrop-blur) headers and cards
25. Coloured stripe down the left edge of cards
26. Icon inside a tinted rounded square
27. Initial-letter avatars or generated faces in testimonials
28. Missing hover, focus, loading and error states

### Motion
29. The same fade-up-on-scroll on every section
30. Numbers that count up
31. Bouncy, springy easing
32. Things that loop forever for decoration (pulsing dots, blinking lights)
33. Motion that ignores the "reduce motion" setting

### Copy
34. "Elevate", "seamless", "powerful", "transform your X", "unleash"
35. Three-word slogans: "Faster. Smarter. Simpler."
36. "Get started", "Learn more", "Submit"
37. Title Case On Every Heading

## What we found on our first version, and what changed

An automated scan of the first version found 20 tells. After the rebuild it finds none that aren't false positives or deliberate.

| Tell found | Graphic design site now | Video site now |
|---|---|---|
| Near-black + one accent (video) | — | Mid-grey editing-suite panels, with the blue of YouTube Studio's retention graph as the only accent |
| Cobalt/indigo accent (design) | Danfo-bus yellow, used only for things you can click | — |
| ALL-CAPS mono labels, "A · B · C" lines | Removed. Plain sentence-case text, one typeface | Removed. Timecodes use the same font with even-width numbers |
| One coloured headline word | Whole headline carries the idea | Whole headline carries the idea |
| 01/02/03 numbering | Only on the real process, written as days | Only on the real process, written as days |
| Arrows on links | Removed | Removed |
| Frosted header | Solid header | Solid header |
| Three pricing cards, "Most booked" ring | A price list you can scan | A price list you can scan |
| Stats strip of round numbers | Cut | Replaced by one result with a chart |
| Initials avatars | Name, role and business in text | Name, channel and size in text |
| Pulsing "available" dot, blinking record light, fake timecode HUD | Plain sentence | Removed. The hero is now a real comparison |
| Bricolage / Instrument Sans / JetBrains Mono / Figtree / IBM Plex Mono | Schibsted Grotesk only | Archivo only, using its width axis |
| Logo wall | A sentence naming clients | Kept as part of the comparison caption |

## Motion: only where it explains something

Following the rule from Anthropic's frontend-design skill (*"motion that answers a person's action is welcome when it shows what changed"*) and UI UX Pro Max's guidelines (animate 1–2 key elements per view, ease-out, use transform and opacity, never loop decoration, respect reduced motion).

**Graphic design site**
- On load, once: your name rises in and the gallery images settle in one after another.
- Gallery and project images open in a full-screen viewer with arrows, swipe and keyboard, and slide between images.
- The process loop arrow draws once when it scrolls into view, and highlights when you hover the feedback step.
- On project pages, the step guide beside the page follows the stage you're reading.
- A yellow marker under the nav follows the section you're reading.
- "Talk about a role" and "Start a project" fill in the form's first question, and the field flashes so you see it changed. The message label changes to match.
- Form: errors slide open under the field you left, the button shows a spinner while sending, and the form shrinks into a "Sent" message.

**Video site**
- Raw vs edited wipe (drag, tap or use arrow keys). It sweeps once on first view. With real clips added, both play in sync.
- "The cut, on a timeline": switch between Raw (3:20) and Edited (0:58) and watch the cut footage collapse and the opening line jump to the front.
- Clicking an item under "What changed" drives the timeline or moves the wipe to show that change.
- The retention line draws once when the chart scrolls into view. Hover or tap for exact values.
- Thumbnails grow into the player when you press play, and shrink back when you close it.
- Tabs: the underline slides to the chosen format and the panel eases in.
- Same form behaviour as the design site.

Everything is switched off for anyone with "reduce motion" turned on.

## Sources
- [vibecoded-design-tells: Reddit-mined ranking (3.2M posts, 3,033 on-topic comments)](https://github.com/JCarterJohnson/vibecoded-design-tells)
- [avoid-ai-design skill and tells catalog](https://github.com/funboy322/avoid-ai-design)
- [Anthropic frontend-design skill](https://github.com/anthropics/skills/tree/main/skills/frontend-design)
- [UI UX Pro Max skill (UX guidelines)](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill)
- [Adrian Krebs: scoring Show HN sites for AI design patterns](https://adriankrebs.ch/blog/design-slop/) and the [Hacker News discussion](https://news.ycombinator.com/item?id=47864393)
- [The Purple Gradient Problem (DEV)](https://dev.to/james_anderson_h/the-purple-gradient-problem-why-ai-ui-all-looks-alike-and-how-to-fix-it-3j65)
- [Why your AI keeps building the same purple gradient website](https://prg.sh/ramblings/Why-Your-AI-Keeps-Building-the-Same-Purple-Gradient-Website)
- [925 Studios: AI slop web design guide](https://www.925studios.co/blog/ai-slop-web-design-guide)
