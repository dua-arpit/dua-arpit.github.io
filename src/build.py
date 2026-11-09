#!/usr/bin/env python3
"""Build the static site for dua-arpit.github.io.

All sources live in src/: profile.yml, papers.bib, news/*.md, style.css,
icons/, logos/, img/, fonts/. The output is plain HTML written into the
repository root, which GitHub Pages serves as is (no Jekyll, no build step).

Usage:   pip install -r src/requirements.txt
         python src/build.py            # writes the site into the repo root
         python src/build.py --out DIR  # writes it somewhere else (preview)
"""
import argparse, datetime as dt, html, pathlib, re, shutil

import bibtexparser, markdown, yaml
from bibtexparser.bparser import BibTexParser
from bibtexparser.customization import convert_to_unicode

SRC = pathlib.Path(__file__).resolve().parent
ROOT = SRC.parent
SITE = SRC
# Paths that the build owns in the output folder. Nothing else is touched.
GENERATED = ["index.html", "404.html", "style.css", "robots.txt", ".nojekyll", "publications", "group",
             "cv", "people", "news", "teaching", "repositories", "assets", "logos"]
E = html.escape
MONTHS = {m: i for i, m in enumerate(
    "jan feb mar apr may jun jul aug sep oct nov dec".split(), 1)}


# ----------------------------------------------------------------------------- data
def load_profile():
    return yaml.safe_load((SITE / "profile.yml").read_text(encoding="utf-8"))


def clean_tex(s):
    s = re.sub(r"\\%", "%", s)
    s = re.sub(r"\\&", "&", s)
    s = s.replace("{", "").replace("}", "").replace("~", " ")
    return re.sub(r"\s+", " ", s).strip()


def person(name):
    name = clean_tex(name)
    if "," in name:
        last, first = [x.strip() for x in name.split(",", 1)]
        name = f"{first} {last}"
    return name


def load_papers():
    text = (SRC / "papers.bib").read_text(encoding="utf-8")
    text = re.sub(r"\A\s*---\s*\n\s*---\s*\n", "", text)  # Jekyll front matter
    parser = BibTexParser(common_strings=True)
    parser.customization = convert_to_unicode
    parser.ignore_nonstandard_types = False
    db = bibtexparser.loads(text, parser=parser)
    papers = []
    for e in db.entries:
        arxiv = e.get("arxiv") or e.get("eprint")
        if not arxiv:
            m = re.search(r"arxiv\.org/abs/([\w.\-/]+?)(v\d+)?$", e.get("url", "").strip())
            arxiv = m.group(1) if m else None
        doi = e.get("doi", "").strip() or None
        month = str(e.get("month", "")).strip().lower()[:3]
        journal = clean_tex(e.get("journal", "")) or None
        venue = None
        if journal:
            venue = journal
            if e.get("volume"):
                venue += f" {e['volume'].strip()}"
            if e.get("pages"):
                venue += f", {e['pages'].strip()}"
        papers.append(dict(
            key=e["ID"], title=clean_tex(e["title"]),
            authors=[person(a) for a in re.split(r"\s+and\s+", e.get("author", ""))],
            year=int(str(e["year"]).strip()), month=MONTHS.get(month, 0),
            venue=venue, arxiv=arxiv, doi=doi))
    papers.sort(key=lambda p: (p["year"], p["month"], p["arxiv"] or ""), reverse=True)
    return papers


def load_news():
    items = []
    for f in sorted((SRC / "news").glob("*.md")):
        raw = f.read_text(encoding="utf-8").replace("\r\n", "\n")
        _, fm, body = raw.split("---", 2)
        meta = yaml.safe_load(fm)
        d = meta["date"]
        if isinstance(d, str):
            d = dt.datetime.fromisoformat(d.strip()[:10])
        body_html = markdown.markdown(body.strip())
        body_html = re.sub(r"^<p>(.*)</p>$", r"\1", body_html, flags=re.S)
        items.append(dict(date=d, html=body_html))
    items.sort(key=lambda n: n["date"], reverse=True)
    return items


# ----------------------------------------------------------------------------- parts
def icon(name, cls="icon"):
    svg = (SITE / "icons" / f"{name}.svg").read_text(encoding="utf-8")
    svg = re.sub(r"<title>.*?</title>", "", svg)
    return svg.replace("<svg ", f'<svg class="{cls}" aria-hidden="true" focusable="false" ', 1)


def logo(slug, name):
    for ext in ("svg", "png", "jpg", "webp"):
        if (SITE / "logos" / f"{slug}.{ext}").exists():
            return f'<img class="logo" src="/logos/{slug}.{ext}" alt="{E(name)} logo">'
    return ""


# Flat research glyphs in the house figure style (ink, mute, wire, X blue, Z vermillion, teal).
def glyph(kind):
    w, h = 132, 76
    s = []
    if kind == "tanner":  # Tanner graph: checks above, qubits below, two long-range edges
        q = [(14 + 20.8 * i, 60) for i in range(6)]
        c = [(24, 16, "x"), (55, 16, "z"), (86, 16, "x"), (117, 16, "z")]
        edges = [(0, 0), (0, 1), (1, 1), (1, 2), (1, 3), (2, 3), (2, 4), (3, 4), (3, 5)]
        far = [(0, 4), (3, 1)]
        for ci, qi in edges:
            s.append(f'<line x1="{c[ci][0]}" y1="{c[ci][1]+6}" x2="{q[qi][0]}" y2="{q[qi][1]-5}" class="wire"/>')
        for ci, qi in far:
            s.append(f'<line x1="{c[ci][0]}" y1="{c[ci][1]+6}" x2="{q[qi][0]}" y2="{q[qi][1]-5}" class="accent"/>')
        for x, y, t in c:
            s.append(f'<rect x="{x-6}" y="{y-6}" width="12" height="12" rx="2" class="chk-{t}"/>')
        for x, y in q:
            s.append(f'<circle cx="{x}" cy="{y}" r="5" class="qubit"/>')
    elif kind == "surgery":  # two code blocks joined by an ancilla bridge
        s.append('<rect x="6" y="14" width="46" height="48" rx="8" class="block"/>')
        s.append('<rect x="80" y="14" width="46" height="48" rx="8" class="block"/>')
        s.append('<rect x="50" y="30" width="32" height="16" rx="3" class="bridge"/>')
        for bx in (6, 80):
            for i in range(3):
                for j in range(3):
                    s.append(f'<circle cx="{bx+11+12*i}" cy="{26+12*j}" r="3" class="qubit"/>')
        for i in range(2):
            s.append(f'<circle cx="{60+12*i}" cy="38" r="3" class="qubit acc"/>')
    elif kind == "decoding":  # rounds in time, two defects joined by a matching path
        for i in range(3):
            s.append(f'<rect x="{6+42*i}" y="8" width="36" height="60" rx="6" class="round"/>')
        for i in range(3):
            for j in range(4):
                s.append(f'<circle cx="{24+42*i}" cy="{17+14*j}" r="2.5" class="dot"/>')
        s.append('<path d="M24 31 L66 31 L66 45 L108 45" class="match"/>')
        s.append('<circle cx="24" cy="31" r="6" class="defect"/>')
        s.append('<circle cx="108" cy="45" r="6" class="defect"/>')
    elif kind == "fracton":  # membrane operator in one lattice plane; fractons at its four corners
        x0, y0, c, nx, ny = 10, 8, 15, 8, 4
        for i in range(nx + 1):
            s.append(f'<line x1="{x0+c*i}" y1="{y0}" x2="{x0+c*i}" y2="{y0+c*ny}" class="grid"/>')
        for j in range(ny + 1):
            s.append(f'<line x1="{x0}" y1="{y0+c*j}" x2="{x0+c*nx}" y2="{y0+c*j}" class="grid"/>')
        s.append(f'<rect x="{x0+c*1.5}" y="{y0+c*0.5}" width="{c*5}" height="{c*3}" class="membrane"/>')
        for i, j in [(1.5, 0.5), (6.5, 0.5), (1.5, 3.5), (6.5, 3.5)]:
            s.append(f'<circle cx="{x0+c*i}" cy="{y0+c*j}" r="4.5" class="fracton"/>')
    elif kind == "atoms":  # atom array; one row moved by a mobile tweezer
        for i in range(7):
            for j in range(4):
                if j == 1:
                    continue
                s.append(f'<circle cx="{12+18*i}" cy="{12+17*j}" r="4" class="qubit"/>')
        for i in range(7):
            s.append(f'<circle cx="{30+18*i}" cy="29" r="4" class="qubit acc"/>')
        s.append('<path d="M6 29 L18 29 M13 24 L18 29 L13 34" class="move"/>')
    return (f'<svg class="glyph" viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
            f'aria-hidden="true">{"".join(s)}</svg>')


def fmt_authors(authors, me="Arpit Dua"):
    out = [f'<span class="me">{E(a)}</span>' if a == me else E(a) for a in authors]
    return ", ".join(out)


def paper_li(p):
    links = []
    if p["arxiv"]:
        links.append(f'<a href="https://arxiv.org/abs/{E(p["arxiv"])}">arXiv</a>')
    if p["doi"]:
        links.append(f'<a href="https://doi.org/{E(p["doi"])}">doi</a>')
    href = (f"https://doi.org/{p['doi']}" if p["doi"] else
            f"https://arxiv.org/abs/{p['arxiv']}" if p["arxiv"] else "#")
    venue = (f'<span><span class="venue">{E(p["venue"])}</span> ({p["year"]})</span>' if p["venue"]
             else f'<span>preprint ({p["year"]})</span>')
    search = E(" ".join([p["title"]] + p["authors"] + [p["venue"] or "", str(p["year"])]).lower())
    return (f'<li class="paper" data-s="{search}"><a class="ptitle" href="{E(href)}">{E(p["title"])}</a>'
            f'<div class="authors">{fmt_authors(p["authors"])}</div>'
            f'<div class="meta">{venue}<span class="plinks">{" ".join(links)}</span></div></li>')


def news_li(n):
    return f'<li><time datetime="{n["date"]:%Y-%m}">{n["date"]:%b %Y}</time><span>{n["html"]}</span></li>'


def page(title, active, body, prof, desc=None):
    nav = "".join(
        f'<a href="{href}"{" aria-current=page" if key == active else ""}>{label}</a>'
        for key, label, href in [("about", "About", "/"), ("publications", "Publications", "/publications/"),
                                 ("group", "Group", "/group/"), ("cv", "CV", "/cv/")])
    full = prof["name"] if title is None else f'{title} · {prof["name"]}'
    year = dt.date.today().year
    return f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{E(full)}</title>
<meta name="description" content="{E(desc or prof['description'])}">
<link rel="preload" href="/assets/fonts/ibm-plex-sans-latin-400-normal.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="/style.css">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16'%3E%3Ccircle cx='8' cy='8' r='6' fill='none' stroke='%231f7a78' stroke-width='2'/%3E%3C/svg%3E">
</head><body>
<header class="top"><div class="wrap">
<a class="name" href="/">{E(prof['name'])}</a>
<nav>{nav}</nav>
</div></header>
<main class="wrap">
{body}
</main>
<footer class="wrap"><span>© {year} {E(prof['name'])}</span><span>Updated {dt.date.today():%B %Y}</span></footer>
</body></html>
"""


# ----------------------------------------------------------------------------- pages
def home(prof, news, papers):
    roles = "".join(f'<li>{E(r["title"])}, <a href="{E(r["href"])}">{E(r["org"])}</a></li>' for r in prof["roles"])
    bio = "".join(f"<p>{b}</p>" for b in prof["bio"])
    links = "".join(f'<a href="{E(l["href"])}">{icon(l["icon"])}<span>{E(l["label"])}</span></a>' for l in prof["links"])
    mails = "".join(f'<a href="mailto:{E(m)}">{E(m)}</a>' for m in prof["contact"]["emails"])
    offices = "".join(f"<span>{E(o)}</span>" for o in prof["contact"].get("offices", []))
    aff = "".join(f'<a class="org" href="{E(a["href"])}">{logo(a["logo"], a["name"])}<span>{E(a["name"])}</span></a>'
                  for a in prof["affiliations"])
    research = "".join(f'<li>{glyph(r["glyph"])}<h3>{E(r["title"])}</h3><p>{E(r["text"])}</p></li>'
                       for r in prof["research"])
    shown, rest = news[:6], news[6:]
    more = (f'<details><summary>Earlier news</summary><ul class="news">'
            f'{"".join(news_li(n) for n in rest)}</ul></details>') if rest else ""
    grants = "".join(
        f'<li>{logo(g["logo"], g["name"])}<span class="gtitle">{E(g["title"])}</span>'
        f'<span class="gname">{E(g["name"])}' + (f', {E(g["note"])}' if g.get("note") else "") + '</span>'
        f'<span class="grole">{E(g["role"])}</span></li>'
        for g in prof["grants"])
    body = f"""
<section class="hero">
  <div class="intro">
    <ul class="roles">{roles}</ul>
    {bio}
    <div class="orgs">{aff}</div>
  </div>
  <aside class="card">
    <img class="portrait" src="/assets/img/arpit.jpg" alt="Portrait of {E(prof['name'])}" width="320" height="400">
    <div class="contact">{mails}{offices}</div>
    <div class="links">{links}</div>
  </aside>
</section>

<section>
  <h2>Research</h2>
  <ul class="research">{research}</ul>
</section>

<section class="newsblock">
  <h2>News</h2>
  <ul class="news">{"".join(news_li(n) for n in shown)}</ul>
  {more}
</section>

<section>
  <h2>Funding</h2>
  <ul class="grants">{grants}</ul>
</section>
"""
    return page(None, "about", body, prof)


def publications(prof, papers):
    years = sorted({p["year"] for p in papers}, reverse=True)
    blocks = []
    for y in years:
        items = "".join(paper_li(p) for p in papers if p["year"] == y)
        blocks.append(f'<section class="year" data-year="{y}"><h3 class="yr">{y}</h3><ol class="papers">{items}</ol></section>')
    body = f"""
<section class="head">
  <h1>Publications</h1>
  <p class="mute">Also on
  <a href="https://scholar.google.com/citations?user=w4ASA38AAAAJ">Google Scholar</a> and
  <a href="https://arxiv.org/search/?searchtype=author&amp;query=Dua%2C+Arpit">arXiv</a>.</p>
  <input id="q" type="search" placeholder="Filter by title, author, journal, or year" aria-label="Filter publications">
</section>
{"".join(blocks)}
<script>
const q=document.getElementById('q');
q.addEventListener('input',()=>{{const t=q.value.trim().toLowerCase();
document.querySelectorAll('.paper').forEach(li=>li.hidden=t&&!li.dataset.s.includes(t));
document.querySelectorAll('.year').forEach(s=>s.hidden=![...s.querySelectorAll('.paper')].some(li=>!li.hidden));}});
</script>
"""
    return page("Publications", "publications", body, prof, f"Publications of {prof['name']}.")


def group(prof):
    g = prof["group"]

    def portrait(m):
        if m.get("photo"):
            return f'<img src="/{E(m["photo"])}" alt="{E(m["name"])}" width="240" height="300" loading="lazy">'
        initials = "".join(w[0] for w in m["name"].split()[:2] if w)
        return f'<div class="mono" aria-hidden="true">{E(initials)}</div>'

    def li(m):
        role = f'<p class="role">{E(m["role"])}</p>' if m.get("role") else ""
        bio = f'<p>{E(m["bio"])}</p>' if m.get("bio") else ""
        mail = (f'<p class="mute"><a href="mailto:{E(m["email"])}">{E(m["email"])}</a></p>'
                if m.get("email") else "")
        return f'<li>{portrait(m)}<div><h3>{E(m["name"])}</h3>{role}{bio}{mail}</div></li>'

    members = "".join(li(m) for m in g["members"])
    alumni = "".join(
        f'<li>{portrait(m)}<div><h3>{E(m["name"])}</h3>'
        + (f'<p class="role">Former {E(m["role"][0].lower() + m["role"][1:])}</p>' if m.get("role") else "")
        + (f'<p class="mute">Now: {E(m["now"])}</p>' if m.get("now") else "") + '</div></li>'
        for m in g.get("alumni", []))
    alumni_block = f'<section class="alumni"><h2>Alumni</h2><ul class="alumni-list">{alumni}</ul></section>' if alumni else ""
    body = f"""
<section class="head"><h1>Group at Virginia Tech</h1><p class="mute">{E(g["intro"])}</p></section>
<ul class="members">{members}</ul>
{alumni_block}
"""
    return page("Group at Virginia Tech", "group", body, prof, f"Research group of {prof['name']}.")


def cv(prof):
    def rows(items):
        out = []
        for it in items:
            t = E(it["title"])
            if it.get("href"):
                t = f'<a href="{E(it["href"])}">{t}</a>'
            notes = "".join(f"<li>{E(n)}</li>" for n in it.get("notes", []))
            out.append(f'<li><span class="when">{E(str(it.get("years", "")))}</span>'
                       f'<div><span class="what">{t}</span><span class="where">{E(it.get("org", ""))}</span>'
                       + (f'<ul class="notes">{notes}</ul>' if notes else "") + "</div></li>")
        return '<ul class="rows">' + "".join(out) + "</ul>"
    grants = "".join(
        f'<li><span class="when">{E(g["role"])}</span><div><span class="what">{E(g["title"])}</span>'
        f'<span class="where">{E(g["name"])}' + (f', {E(g["note"])}' if g.get("note") else "") + "</span></div></li>"
        for g in prof["grants"])
    code = "".join(f'<li><a href="{E(c["href"])}">{icon("github", "icon sm")}{E(c["name"])}</a></li>' for c in prof["code"])
    body = f"""
<section class="head"><h1>Curriculum vitae</h1><p class="mute">{E(prof["name"])}. {" · ".join(E(m) for m in prof["contact"]["emails"])}</p></section>
<section class="cv"><h2>Positions</h2>{rows(prof["positions"])}</section>
<section class="cv"><h2>Education</h2>{rows(prof["education"])}</section>
<section class="cv"><h2>Funding</h2><ul class="rows">{grants}</ul></section>
<section class="cv"><h2>Teaching</h2>{rows(prof["teaching"])}</section>
<section class="cv"><h2>Software</h2><ul class="code">{code}</ul></section>
<section class="cv"><h2>Publications</h2><p><a href="/publications/">Full list of publications</a></p></section>
"""
    return page("CV", "cv", body, prof, f"Curriculum vitae of {prof['name']}.")


def not_found(prof):
    return page("Not found", None, '<section class="head"><h1>Page not found</h1>'
                '<p class="mute">This page does not exist. Go to the <a href="/">home page</a>.</p></section>', prof)


# ----------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT))
    out = pathlib.Path(ap.parse_args().out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    for name in GENERATED:
        t = out / name
        if t.is_dir():
            shutil.rmtree(t)
        elif t.exists():
            t.unlink()
    prof, papers, news = load_profile(), load_papers(), load_news()

    def write(rel, text):
        f = out / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(text, encoding="utf-8")

    write("index.html", home(prof, news, papers))
    write("publications/index.html", publications(prof, papers))
    write("group/index.html", group(prof))
    write("cv/index.html", cv(prof))
    write("404.html", not_found(prof))
    for old in ("people", "news", "teaching", "repositories"):  # keep old al-folio URLs working
        target = {"people": "/group/", "news": "/", "teaching": "/cv/", "repositories": "/cv/"}[old]
        write(f"{old}/index.html", f'<!doctype html><meta charset="utf-8"><meta http-equiv="refresh" content="0; url={target}">'
                                   f'<link rel="canonical" href="{target}"><a href="{target}">moved</a>')
    write(".nojekyll", "")
    write("robots.txt", "User-agent: *\nAllow: /\n")
    shutil.copy(SRC / "style.css", out / "style.css")
    shutil.copytree(SRC / "fonts", out / "assets" / "fonts")
    shutil.copytree(SRC / "img", out / "assets" / "img")
    logos = [p for p in (SITE / "logos").glob("*") if p.suffix.lower() in {".svg", ".png", ".jpg", ".webp"}]
    if logos:
        (out / "logos").mkdir()
        for p in logos:
            shutil.copy(p, out / "logos" / p.name)
    print(f"built {out}: {len(papers)} papers, {len(news)} news items, {len(logos)} logos")


if __name__ == "__main__":
    main()
