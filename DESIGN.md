---
version: alpha
name: client-solutions-ops-desk
description: A dark, vertical, snap-scrolling feed where each "clip" is one finding, framed like a short-video app: phone-shaped stage, caption and source line bottom-left, action rail (Save, SQL, Share) bottom-right. A Desk toggle turns the feed into a grid for people who would rather scan. No platform logo, wordmark or typeface is used.

colors:
  bg: "#08080d"
  clip: "#111118"
  raise: "#1b1b25"
  line: "#2a2a37"
  ink: "#f3f3f7"
  muted: "#9b9bb0"
  cyan: "#25f0e8"   # clean / client data
  pink: "#ff2d6f"   # raw data / the problem
  good: "#3ddc97"
  warn: "#ffb347"
  bad: "#ff5470"

typography:
  display:
    fontFamily: "'Unbounded', 'Arial Black', sans-serif"
    fontWeight: 800
    use: clip headlines only, with a cyan/pink split shadow
  body:
    fontFamily: "'Figtree', 'Segoe UI', sans-serif"
    fontSize: 15px
  utility:
    fontFamily: "'JetBrains Mono', ui-monospace, monospace"
    use: numbers, kickers, chart labels, the source ticker
---

## Rules

- Cyan is the clean number, pink is the raw or wrong one. The two never swap meaning.
- One loud moment per clip: the headline. Everything else is quiet.
- Motion plays once when a clip comes into view (bars grow, lines draw, the headline splits),
  from a resting state that is already complete. `prefers-reduced-motion` turns it all off.
- The SQL button on every clip opens the query behind it. Nothing on the page is unsourced.
- Charts are hand-drawn SVG from tokens; labels name values the chart reaches.
