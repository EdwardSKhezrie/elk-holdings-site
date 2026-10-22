# ELK Holdings website

Public website for ELK Holdings (Eddie Khezrie, Founder & CEO). Static site, no build step.
Hosted on Cloudflare Pages, deployed automatically from the `main` branch of this repo.

## Files
- `index.html` — the whole public site: single page with views (home, investments, 7 category pages, portfolio, leadership, contact). Navigation is hash-based (`#platform`, `#realestate`, ...). Styles and script are inline.
- `portal/index.html` — partner portal placeholder. The real portal (per-partner holdings, deal pages, daily stock prices) is NOT published here yet. It must only go live behind Cloudflare Access (email one-time-code login for named partners). Never put partner names, amounts, deal details or login codes in a public file.
- `crest.jpg`, `crest-icon.jpg`, `crest-head.jpg` — ELK crest images.

## Brand
Black (#000) background, gold accents (#C9A45C / #E8CB8A). Fonts: Cinzel (marks/labels), Cormorant Garamond (headings), Figtree (body). Plain, simple wording. Do not mention Jimmy Jazz. ELK is a family office; every category is core (not real-estate-first).

## Content rules
- Public pages never show specific deals, amounts or the healthcare deal under review. The Portfolio page is intentionally private ("Partner access required").
- Tickers on category pages are examples of public companies, labeled as not recommendations or ELK holdings.
- Never add made-up holdings, deal counts or track record to public pages.
