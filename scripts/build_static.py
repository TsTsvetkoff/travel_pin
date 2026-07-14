"""
Rebuild the GitHub Pages static site in ./docs from the live data + assets.

Run before `git push` so the Pages deploy matches the current DB:
    python scripts/build_static.py

Steps:
1. db.export_locations() to refresh locations.json (this is the file you commit
   alongside docs/ for the Pages build).
2. Copy locations.json into docs/locations.json.
3. Copy static/style.css into docs/static/.
4. Copy every file from static/diplomas/ into docs/static/diplomas/.
5. Write docs/diplomas.json (sorted list of diploma filenames) for hall_of_fame.html.

The docs HTML files and the trail JS files are committed by hand — this script
only refreshes the data + binary assets so a `git diff` is small and obvious.
"""

import json
import shutil
import sys
from pathlib import Path

# Make the repo root importable so `import db` works regardless of CWD.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import db


REPO_ROOT = Path(__file__).resolve().parent.parent
DOCS = REPO_ROOT / 'docs'
DOCS_STATIC = DOCS / 'static'
DOCS_DIPLOMAS = DOCS_STATIC / 'diplomas'
STATIC = REPO_ROOT / 'static'
STATIC_DIPLOMAS = STATIC / 'diplomas'
IMG_EXTS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}


def _copy_file(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def _copy_tree(src_dir: Path, dst_dir: Path) -> int:
    if not src_dir.exists():
        return 0
    dst_dir.mkdir(parents=True, exist_ok=True)
    count = 0
    for f in sorted(src_dir.iterdir()):
        if f.is_file():
            _copy_file(f, dst_dir / f.name)
            count += 1
    return count


def build() -> None:
    DOCS.mkdir(parents=True, exist_ok=True)

    # 1. Refresh locations.json at the repo root (this is the file you commit).
    locations = db.export_locations()
    print(f'  locations.json: {len(locations)} entries')

    # 2. Copy it into docs/.
    _copy_file(REPO_ROOT / 'locations.json', DOCS / 'locations.json')
    print('  docs/locations.json: copied')

    # 3. Copy style.css.
    if (STATIC / 'style.css').exists():
        _copy_file(STATIC / 'style.css', DOCS_STATIC / 'style.css')
        print('  docs/static/style.css: copied')

    # 4. Copy every diploma image.
    diploma_count = _copy_tree(STATIC_DIPLOMAS, DOCS_DIPLOMAS)
    print(f'  docs/static/diplomas/: {diploma_count} files')

    # 5. Write the diplomas manifest. hall_of_fame.html reads this.
    diplomas = sorted(
        f.name for f in STATIC_DIPLOMAS.iterdir()
        if f.is_file() and f.suffix.lower() in IMG_EXTS
    )
    (DOCS / 'diplomas.json').write_text(
        json.dumps(diplomas, ensure_ascii=False, indent=2),
        encoding='utf-8',
    )
    print(f'  docs/diplomas.json: {len(diplomas)} entries')


if __name__ == '__main__':
    print('Building static site in', DOCS)
    build()
    print('Done.')