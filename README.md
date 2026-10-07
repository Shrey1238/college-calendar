# College Calendar

A live dashboard with all your course deadlines in one place — Canvas due
dates sync automatically, exam dates from syllabi live in `manual.yaml`.

## One-time setup (~3 min)

1. **Create the repo.** Create a new GitHub repo named `college-calendar`
   (public — GitHub Pages is only free on public repos). Push this code to it.

2. **Add your Canvas feed as a secret.**
   - In Canvas: **Calendar → Calendar Feed** (link at the bottom-right of the
     sidebar) → copy the `https://...ics` URL.
   - In the repo: **Settings → Secrets and variables → Actions → New
     repository secret**, name `CANVAS_ICS_URL`, paste the URL.

3. **Enable Pages.** Repo **Settings → Pages → Source: GitHub Actions**.

4. **Run it once.** Actions tab → "Refresh calendar data" → Run workflow.
   Your dashboard goes live at `https://<username>.github.io/college-calendar/`.

It refreshes every 6 hours after that.

## Files

- `ingest.py` — collects events → `events.json` (Canvas ICS + `manual.yaml`)
- `courses.yaml` — your courses: display name, color, matching keywords
- `manual.yaml` — exams/anything not in the Canvas feed
- `index.html` — the dashboard
- `.github/workflows/refresh.yml` — scheduled refresh + Pages deploy

## Privacy note

The Pages site is publicly reachable (obscure URL, but public). Assignment
titles and dates are visible — nothing else. If that's not OK, skip the Pages
deploy step and open `index.html` locally, or host it somewhere with auth.
