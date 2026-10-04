# Trail Atlas · My Bulgaria

A responsive Flask pin editor and GitHub Pages travel atlas using the same templates and data. The supplied 425 places and all five certificates are preserved. The old embedded E routes have been replaced by your E3, E4 and E8 GPX recordings.

## Run locally

Use Python 3.10+.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Windows: activate with `.venv\Scripts\activate` instead. Open http://127.0.0.1:5000. The editor binds to your computer only; it is intended as a single-user, single-process editor. Keep that default. This is not a remotely authenticated admin application.

The local SQLite file is created from `locations.json` on first launch. Existing databases are preserved. Every saved pin updates SQLite, writes `locations.json` atomically, and rebuilds `_site/`. SQLite is the local working copy; JSON is the versioned website snapshot. Work from one editor checkout. If you pull a newer JSON from another computer, back up your local DB and remove it before restarting to reseed from that snapshot.

## Enable GitHub Pages once

1. Put the contents of this project at the root of your GitHub repository, including `.github/workflows/pages.yml`, `locations.json`, `templates/`, and `static/`. Do not upload just `_site/`. If using the GitHub upload UI, ensure the hidden `.github` folder is included.
2. Use branch `main`, or change the workflow branch to match yours.
3. In repository **Settings → Pages → Build and deployment → Source**, select **GitHub Actions**.
4. Commit and push. The included workflow tests, builds, and publishes your site. It supports both `username.github.io` and `username.github.io/repository/` using relative URLs.

If your repository is configured as **Deploy from a branch** with the `/docs` folder, the supplied `docs/` directory is already a static snapshot. Keep the `/docs/.nojekyll` file and select `main` + `/docs`; this bypasses Jekyll and avoids SCSS conversion errors. Regenerate it after data or template changes with:

```bash
python build_static.py --output docs
```

The error `Jekyll::Converters::Scss ... /github/workspace/docs` means Pages is using that branch-based Jekyll mode while the `docs` directory is missing or contains a stale Jekyll configuration. Select **GitHub Actions** for automatic builds, or use the included `docs/` snapshot with `.nojekyll`.

The bundle is ready to deploy, but no GitHub repository was supplied or connected here, so it has not been published to a live GitHub URL.

## Automatically publish after adding a pin

Run Flask from a local clone of that repository, on your publishing branch. Configure Git authentication (SSH or your credential manager), and Git `user.name` / `user.email`, then confirm that an ordinary `git push origin main` succeeds.

macOS / Linux:

```bash
export PAGES_AUTO_PUSH=1
export PAGES_REMOTE=origin
export PAGES_BRANCH=main
python app.py
```

PowerShell:

```powershell
$env:PAGES_AUTO_PUSH="1"
$env:PAGES_REMOTE="origin"
$env:PAGES_BRANCH="main"
python app.py
```

Saving a pin now does: **SQLite → locations.json → local static build → data-only Git commit → Git push → GitHub Actions → GitHub Pages**. Deployment usually takes a few minutes. The app reports “queued”, not “published”, because GitHub must finish the deployment. Review the Actions tab for the final deployment result.

Auto-push commits only `locations.json` and leaves unrelated staged files out of that commit. A push also includes any earlier commits already on your branch. Use a dedicated, current checkout. It never force-pushes, resets, rebases, or silently resolves conflicts. A failed build or push leaves your saved pin in the DB and shows a warning; fix Git access/conflicts, then use **Retry website sync** on `/add` without resubmitting the pin. Retrying also pushes a previous data commit after a failed push.

With `PAGES_AUTO_PUSH` unset, local saving/building still works. Commit and push `locations.json` manually to publish. `.env.example` documents settings; it is not auto-loaded. No GitHub token belongs in templates or browser code.

GitHub Pages serves static files and cannot run Flask or write SQLite. Its Add page links to your local editor. Map filters, route toggles, Nearby search, and the certificate gallery work directly on Pages. Original endpoints remain `/`, `/city_search`, `/add`, `/hall_of_fame` in Flask; Pages uses matching directory paths with trailing slashes.

## What changed

- Shared responsive layout, navigation, clear form labels, mobile layouts, keyboard focus, friendly errors and empty states.
- Map filters work together and preserve the URL query. Matching places are paged in groups of 30; the map includes every match. Personal hikes have independent toggles and start/finish markers.
- `/city_search` previously received dictionaries but accessed `loc[1]`, `loc[4]`, `loc[5]`. This produced blank titles/categories and the misleading “Regular” label. It now uses named fields, checks ranges, distinguishes the initial and empty states, and sorts by exact distance before rounding.
- Nearby uses a bundled GeoNames Bulgarian settlement index: Bulgarian and Latin aliases, support for “град ” and “гр.” prefixes, and explicit choices for duplicate names. The same local data and distance formula serve Flask and static Pages. There are no runtime geocoding API calls, API keys or Nominatim rate limits. It searches your saved pins, not all tourist sites in Bulgaria.
- Add validates finite coordinates, ranges, category and name, preserves invalid form input, and uses CSRF protection. The map can fill coordinates by clicking.
- Certificate viewer uses a keyboard-accessible native dialog with Escape-to-close.

## Personal E hikes

`static/data/hikes.geojson` contains only your three uploaded tracks:

- E3 Kom Emine merged.gpx — 168,891 source points; 17 recorded dates.
- E4 Pet Planini merged.gpx — 83,360 source points; 13 recorded dates.
- E8 Rila rodopi merged.gpx — 84,597 source points; 11 recorded dates.

Display geometry is simplified to approximately 12 metres. Segments are separated at original segment boundaries, non-increasing timestamps and recording gaps above 30 minutes. The map preserves recorded travel, including faster sections; it does not apply the earlier analysis's walking-speed filter. E8 timestamps contain a six-day date gap and continuous midnight crossings, so dates are not presented as verified original stages.

To replace/rebuild the route layer, place exactly one E3, E4 and E8 `.gpx` or `.gpx.gz` file in a folder:

```bash
python scripts/import_gpx.py /path/to/your/gpx-files
python build_static.py
```

Commit and push `static/data/hikes.geojson` for that route change. Automatic pin publishing intentionally commits only the pin JSON; template, route and certificate edits require a normal commit/push. The full original GPX files remain your inputs and are not republished in this bundle.

## Preview the static build

```bash
python build_static.py
python -m http.server 8000 --directory _site
```

Open http://127.0.0.1:8000. Serve via HTTP; do not double-click the HTML, because browsers restrict local JSON fetches under `file://`. The ZIP also includes a prebuilt `_site/` for immediate HTTP preview. JavaScript and settlement data are bundled locally. Map background tiles need an internet connection.

## Checks

```bash
python -m unittest discover -s tests -v
```

Optional offline frontend checks (Node.js 18+):

```bash
python build_static.py
npm install
npm test
```

Tests cover the city-search regression, invalid input, Bulgarian aliases, duplicate place names, no-result cases, persistent pin insertion, CSRF rejection, static export, route identity, and publishing behavior. Browser visual verification could not be completed in this environment: local Chromium could not start, and access to the local preview in the cloud browser was denied. Offline DOM tests exercise the frontend logic; rendered desktop/mobile appearance and real map tile loading remain unverified here.

## Data and dependencies

- Saved pins, personal tracks, certificates: your supplied files.
- Settlement snapshot: https://download.geonames.org/export/dump/BG.zip, retrieved 4 October 2026. Filtered to populated settlements; name aliases normalized for lookup. Region labels use GeoNames `admin1CodesASCII.txt`. GeoNames is licensed under CC BY 4.0: https://creativecommons.org/licenses/by/4.0/. Attribution is displayed in the footer. This may include villages/localities as well as cities; duplicate names are disambiguated.
- Refresh settlements with `python scripts/import_cities.py`, then commit the changed `static/data/cities.json`.
- Leaflet 1.9.4 is bundled under its BSD license (`static/vendor/LEAFLET-LICENSE.txt`). Basemap tiles © OpenStreetMap contributors.
- GitHub Pages workflow follows https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages.
