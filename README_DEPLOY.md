# Voyadecir — Static Hybrid Site (Phase 3A)

Bilingual (EN/ES), minimalist, SEO-ready static site with embedded translator.

## Deploy to Render (Static Site)
1. Create **Static Site** in Render.
2. **Build Command:** *(none)*
3. **Publish Directory:** `/`
4. Connect your custom domain **voyadecir.com** (and **www**). Render will issue SSL automatically.
5. Keep your translator app running at its current Render URL. The site embeds it in `translate.html`.

### DNS (GoDaddy quick recap)
- **A @** → per Render instructions (or use Render’s ALIAS/ANAME if available).
- **CNAME www** → `voyadecir.com`
- Leave `_domainconnect` as is.

## Customize
- Logo: replace `assets/img/logo.png` and `assets/img/logo.svg` with your final art.
- Language: edit `/lang/en.json` and `/lang/es.json` (add more languages by adding new JSON files and updating `main.js` if needed).
- Contact Form: set your Formspree endpoint in `contact.html` (`your-form-id`).

## Notes
- Privacy-first: no analytics by default. Add Plausible or GA4 if desired.
- Accessibility: semantic HTML, focusable controls.
- Performance: lean CSS/JS, no frameworks.
