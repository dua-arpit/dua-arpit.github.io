# dua-arpit.github.io

Personal website of Arpit Dua: https://dua-arpit.github.io

The site is plain HTML in this folder. GitHub Pages serves it as is, with no Jekyll and no build step,
so it loads fast and does not break when tools change.

## Update the site

1. Edit the sources in `src/`:
   - `src/profile.yml`: bio, positions, research, grants, group, CV
   - `src/papers.bib`: publications
   - `src/news/YYYY-MM-DD-name.md`: one news item per file
   - `src/logos/`: logo files (see `src/logos/README.md`)
2. Regenerate the HTML:
   ```
   pip install -r src/requirements.txt
   python src/build.py
   ```
3. Commit and push.

## GitHub Pages setting

Settings > Pages > Build and deployment > Source: "Deploy from a branch", branch `master`, folder `/ (root)`.
