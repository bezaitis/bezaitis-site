#!/usr/bin/env python3
"""Build the static site from content/site.json.

Usage: python3 build.py

Writes index.html files for every page into the repo root, ready for
GitHub Pages. Photos live in assets/img/<slug>/NN.webp with a smaller
NN-sm.webp beside each one. Standard library only.
"""

import hashlib
import html
import json
import re
import struct
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SITE_URL = "https://bezaitis.com"
CONTENT = json.loads((ROOT / "content" / "site.json").read_text())

COUNTRY_NAMES = {
    "036": "Australia", "124": "Canada", "156": "China", "158": "Taiwan", "300": "Greece",
    "392": "Japan", "410": "South Korea", "446": "Macao", "528": "Netherlands", "554": "New Zealand",
    "578": "Norway", "604": "Peru", "608": "The Philippines", "704": "Vietnam", "764": "Thailand",
    "784": "United Arab Emirates", "818": "Egypt", "826": "United Kingdom",
}

esc = html.escape


def smart(text):
    """Typographic quotes: ' to ’, "x" to “x”."""
    text = re.sub(r'(^|[\s(\[])"', "\\1\u201c", text)
    text = text.replace('"', "\u201d")
    text = re.sub(r"(^|[\s(\[])'", "\\1\u2018", text)
    return text.replace("'", "\u2019")


def inline(text):
    """Escape text, then turn [label](url) into links."""
    out = esc(smart(text), quote=False)
    return re.sub(r"\[([^\]]+)\]\(([^)]+)\)", lambda m: f'<a href="{esc(m.group(2))}">{m.group(1)}</a>', out)


def plain(text):
    return re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)


def month_label(ym):
    y, m = map(int, ym.split("-"))
    return date(y, m, 1).strftime("%b %Y")


def month_long(ym):
    y, m = map(int, ym.split("-"))
    return date(y, m, 1).strftime("%B %Y")


def first_sentence(text, limit=160):
    text = plain(text)
    m = re.match(r"(.+?[.!?])(\s|$)", text)
    s = m.group(1) if m else text
    return s if len(s) <= limit else s[: limit - 1].rsplit(" ", 1)[0] + "…"


def webp_size(path):
    """Read width and height from a WebP header."""
    data = path.read_bytes()[:40]
    chunk = data[12:16]
    if chunk == b"VP8 ":
        w, h = struct.unpack("<HH", data[26:30])
        return w & 0x3FFF, h & 0x3FFF
    if chunk == b"VP8L":
        b = data[21:25]
        w = 1 + (((b[1] & 0x3F) << 8) | b[0])
        h = 1 + (((b[3] & 0xF) << 10) | (b[2] << 2) | ((b[1] & 0xC0) >> 6))
        return w, h
    if chunk == b"VP8X":
        w = 1 + int.from_bytes(data[24:27], "little")
        h = 1 + int.from_bytes(data[27:30], "little")
        return w, h
    raise ValueError(f"unknown webp header in {path}")


def img(folder, file, alt, sizes, cls="", eager=False, small=True):
    """An <img> with the small and full sizes in srcset."""
    full = ROOT / "assets" / "img" / folder / file
    w, h = webp_size(full)
    src = f"/assets/img/{folder}/{file}"
    attrs = [f'src="{src}"', f'width="{w}"', f'height="{h}"', f'alt="{esc(alt)}"']
    sm = full.with_name(full.stem + "-sm.webp")
    if small and sm.exists():
        sw, _ = webp_size(sm)
        attrs.append(f'srcset="/assets/img/{folder}/{sm.name} {sw}w, {src} {w}w"')
        attrs.append(f'sizes="{sizes}"')
    if cls:
        attrs.append(f'class="{cls}"')
    attrs.append('fetchpriority="high"' if eager else 'loading="lazy"')
    attrs.append('decoding="async"')
    return f"<img {' '.join(attrs)}>"


# Chrome ---------------------------------------------------------------

def head(title, description, path, extra=""):
    canonical = SITE_URL + path
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(description)}">
<link rel="canonical" href="{canonical}">
<meta property="og:type" content="website">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(description)}">
<meta property="og:url" content="{canonical}">
<meta property="og:image" content="{SITE_URL}/assets/icons/og.jpg">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="/assets/icons/favicon-light.png" media="(prefers-color-scheme: light)">
<link rel="icon" href="/assets/icons/favicon-dark.png" media="(prefers-color-scheme: dark)">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Hanken+Grotesk:wght@500;600&family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,500;1,6..72,400&family=IBM+Plex+Mono:wght@400;500&display=swap">
<link rel="stylesheet" href="/assets/css/site.css">
{extra}</head>
<body>
<a class="skip" href="#main">Skip to content</a>
"""


def nav(current):
    links = [("/trips/", "Trips"), ("/work/", "Work"), ("/about/", "About")]
    current_attr = ' aria-current="page"'
    items = "".join(
        f'<li><a href="{href}"{current_attr if current == href else ""}>{label}</a></li>'
        for href, label in links
    )
    return f"""<header class="site-nav">
  <div class="wrap">
    <a class="wordmark" href="/">John Bezaitis</a>
    <nav aria-label="Main"><ul>{items}</ul></nav>
    <a class="btn" href="{esc(CONTENT['resume'])}">Resume</a>
  </div>
</header>
"""


def footer(scripts=""):
    c = CONTENT
    year = max(t["date"] for t in c["trips"])[:4]
    return f"""<footer class="site-footer">
  <div class="wrap">
    <div class="footer-grid">
      <div class="footer-intro">
        <a class="mail" href="mailto:{c['email']}">{c['email']}</a>
        <p>If you’re interested in connecting, or just want to share stories about the latest adventure, I’d love to hear from you!</p>
      </div>
      <div>
        <h2>Elsewhere</h2>
        <ul>
          <li><a href="{esc(c['linkedin'])}">LinkedIn</a></li>
          <li><a href="{esc(c['github'])}">GitHub</a></li>
          <li><a href="{esc(c['resume'])}">Resume</a></li>
        </ul>
      </div>
      <div>
        <h2>Also on this site</h2>
        <ul>
          <li><a href="/poppy/">Poppy</a></li>
          <li><a href="/sailing/">Sailing</a></li>
          <li><a href="/dabears/">Da Bears</a></li>
        </ul>
      </div>
    </div>
    <p class="footer-base">© John Bezaitis, {year}</p>
  </div>
</footer>
{scripts}</body>
</html>
"""


def new_tabs(text):
    """Open links to other sites (resume, reports, models, profiles) in a new tab."""
    return re.sub(r'<a ((?:(?!target=)[^>])*?)href="(https?://[^"]+)"', r'<a \1href="\2" target="_blank" rel="noopener"', text)


def bust(text):
    """Stamp scripts, styles and images with a content hash so browsers fetch new versions."""
    def stamp(m):
        file = ROOT / m.group(1).lstrip("/")
        if not file.is_file():
            return m.group(0)
        return f"{m.group(1)}?v={hashlib.sha1(file.read_bytes()).hexdigest()[:8]}"
    return re.sub(r'(/assets/(?:css|js|img)/[^"?\s,]+\.(?:css|js|webp|png|jpg|svg))(?![?\w])', stamp, text)


def write(path, text):
    text = bust(new_tabs(text))
    out = ROOT / path.strip("/") / "index.html" if path != "/" else ROOT / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text)
    return out


# Shared pieces --------------------------------------------------------

TRIPS = sorted(CONTENT["trips"], key=lambda t: t["date"], reverse=True)
WORK = CONTENT["work"]


def trip_data_script():
    data = [
        {
            "slug": t["slug"], "title": t["title"], "date": t["date"], "label": month_label(t["date"]),
            "countries": t["countries"], "pin": t["pin"],
            "thumb": f"/assets/img/{t['slug']}/{t['photos'][0].replace('.webp', '-sm.webp')}",
        }
        for t in TRIPS
    ]
    payload = json.dumps({"trips": data, "names": COUNTRY_NAMES}, ensure_ascii=False).replace("</", "<\\/")
    return f'<script type="application/json" id="trip-data">{payload}</script>\n'


MAP_SCRIPTS = (
    '<script src="/assets/vendor/d3-array.min.js" defer></script>\n'
    '<script src="/assets/vendor/d3-geo.min.js" defer></script>\n'
    '<script src="/assets/vendor/topojson-client.min.js" defer></script>\n'
    '<script src="/assets/js/atlas.js" defer></script>\n'
)
GALLERY_SCRIPT = '<script src="/assets/js/gallery.js" defer></script>\n'

LIGHTBOX = """<dialog class="lightbox" aria-label="Photo viewer">
  <div class="lightbox-bar">
    <span class="count" aria-live="polite"></span>
    <div class="tools">
      <button class="btn" type="button" data-step="-1">Previous</button>
      <button class="btn" type="button" data-step="1">Next</button>
      <button class="btn" type="button" data-close>Close</button>
    </div>
  </div>
  <div class="lightbox-stage"></div>
</dialog>
"""


def countries_count(trips):
    return len({c for t in trips for c in t["countries"]})


def trip_card(t, sizes, heading="h3"):
    cover = img(t["slug"], t["photos"][0], f"{t['title']}, {month_long(t['date'])}", sizes)
    return f"""<li class="trip-card" data-year="{t['date'][:4]}">
  <a href="/trips/{t['slug']}/">
    <div class="photo">{cover}</div>
    <div class="caption"><{heading}>{esc(t['title'])}</{heading}><time datetime="{t['date']}">{month_label(t['date'])}</time></div>
  </a>
</li>"""


def map_figure(mode, atlas, caption="", focus="", label="World map of the countries I have visited"):
    focus_attr = f' data-focus="{focus}"' if focus else ""
    cls = f"map map--{mode}"
    return f"""<div class="{cls}" data-map="{mode}" data-atlas="/assets/data/{atlas}"{focus_attr} role="group" aria-label="{esc(label)}">
  <p class="map-fallback">The map needs JavaScript. Every trip is listed on this page.</p>
</div>{caption}"""


def gallery(folder, title, photos, start=0):
    items = []
    for i, f in enumerate(photos):
        n = i + start
        full = f"/assets/img/{folder}/{f}"
        alt = f"{title}, photo {n + 1} of {len(photos) + start}"
        items.append(
            f'<li><a class="photo-btn" href="{full}" data-index="{n}" aria-label="Open {esc(alt)}">'
            f'{img(folder, f, alt, "(max-width: 56rem) 50vw, 33vw")}</a></li>'
        )
    return '<ul class="gallery">' + "".join(items) + "</ul>"


# Pages ----------------------------------------------------------------

def build_home():
    c = CONTENT
    latest = TRIPS[0]
    first = TRIPS[-1]
    bio = "".join(f"<p>{inline(p)}</p>" for p in c["home"]["bio"])
    cards = "".join(trip_card(t, "(max-width: 48rem) 50vw, (max-width: 64rem) 33vw, 25vw") for t in TRIPS[:4])
    photo = c["home"]["photo"]
    trip = next(t for t in TRIPS if t["slug"] == photo["trip"])
    bio_photo = img(photo["trip"], photo["file"], photo["alt"], "(max-width: 52rem) 100vw, 30vw")
    projects = "".join(project_card(w) for w in WORK)
    caption = f"""
  <figcaption class="meta"><span><span class="num">{len(TRIPS)}</span> trips since {month_long(first['date'])}, <span class="num">{countries_count(TRIPS)}</span> countries and territories</span><span>Magenta marks the latest, {esc(latest['title'])}</span></figcaption>"""
    page = head(
        "John Bezaitis",
        "Welcome to my personal website! Here, you can learn about me, my work, and future plans!",
        "/",
    ) + nav("/") + f"""<main id="main">
<section class="hero-stage">
  <div class="wrap">
    <div>
      <h1>John Bezaitis</h1>
      <p class="lede">A senior at the University of Illinois studying economics and statistics.</p>
      <p class="meta">{esc(c['location'])}</p>
      <div class="actions">
        <a class="btn btn--primary" href="/trips/">Browse the trips</a>
        <a class="btn" href="/work/">See my work</a>
      </div>
    </div>
    <figure class="sheet hero-map">
      {map_figure("compact", "countries-110m.json", caption)}
    </figure>
  </div>
</section>

<section class="section section--well">
  <div class="wrap split split--bio">
    <div class="bio-side">
      <h2>Hi, I’m John</h2>
      <figure class="bio-photo">
        <a href="/trips/{trip['slug']}/">{bio_photo}</a>
        <figcaption class="meta">{esc(trip['title'])}, <time datetime="{trip['date']}">{month_long(trip['date'])}</time></figcaption>
      </figure>
    </div>
    <div class="prose">{bio}</div>
  </div>
</section>

<section class="section">
  <div class="wrap">
    <div class="section-head"><h2>Latest trips</h2><a href="/trips/">All {len(TRIPS)} trips</a></div>
    <ul class="trip-grid">{cards}</ul>
  </div>
</section>

<section class="section section--tight">
  <div class="wrap">
    <div class="section-head"><h2>My work</h2><a href="/work/">All projects</a></div>
    <ul class="project-grid">{projects}</ul>
  </div>
</section>
</main>
""" + footer(trip_data_script() + MAP_SCRIPTS)
    write("/", page)


def work_row(w):
    docs = "".join(f'<a href="{esc(l["href"])}">{esc(l["label"])}</a>' for l in w["links"])
    return f"""<tr>
  <td class="title"><a href="/work/{w['slug']}/">{esc(w['title'])}</a></td>
  <td>{esc(w['tagline'])}</td>
  <td class="docs">{docs}</td>
</tr>"""


def project_card(w):
    folder = f"work-{w['slug']}"
    logo = img(folder, w["logo"], f"{w['title']} logo", "(max-width: 40rem) 100vw, (max-width: 72rem) 50vw, 25vw")
    docs = "".join(f'<a href="{esc(l["href"])}">{esc(l["label"])}</a>' for l in w["links"])
    return f"""<li class="project-card">
  <a class="project-link" href="/work/{w['slug']}/">
    <div class="plate">{logo}</div>
    <h3>{esc(w['title'])}</h3>
    <p>{esc(w['tagline'])}</p>
  </a>
  {f'<p class="docs">{docs}</p>' if docs else ""}
</li>"""


def collage(works):
    """Exhibits from every project, the newest set large."""
    tiles = []
    for w in works:
        folder = f"work-{w['slug']}"
        pic = img(folder, w["exhibit"], f"Exhibit from {w['title']}", "(max-width: 52rem) 50vw, 25vw")
        tiles.append(f'<li><a href="/work/{w["slug"]}/"><div class="tile">{pic}</div><span>{esc(w["title"])}</span></a></li>')
    return '<ul class="collage">' + "".join(tiles) + "</ul>"


def work_table(rows):
    return f"""<div class="sheet ledger-sheet">
      <table class="ledger">
        <thead><tr><th scope="col">Project</th><th scope="col">Focus</th><th scope="col" class="docs">Documents</th></tr></thead>
        <tbody>{rows}</tbody>
      </table>
    </div>"""


def build_trips():
    c = CONTENT
    years = sorted({t["date"][:4] for t in TRIPS}, reverse=True)
    chips = '<button class="chip" type="button" data-year="all" aria-pressed="true">All</button>' + "".join(
        f'<button class="chip" type="button" data-year="{y}" aria-pressed="false"><span class="num">{y}</span></button>' for y in years
    )
    views = "".join(
        f'<button class="chip" type="button" data-view="{v}" aria-pressed="{"true" if v == "world" else "false"}">{label}</button>'
        for v, label in (("world", "World"), ("europe", "Europe"), ("asia", "East Asia"))
    )
    index = "".join(
        f'<li><a href="/trips/{t["slug"]}/" data-slug="{t["slug"]}" data-year="{t["date"][:4]}"><span>{esc(t["title"])}</span>'
        f'<time datetime="{t["date"]}">{month_label(t["date"])}</time></a></li>'
        for t in TRIPS
    )
    # A year with fewer than three trips joins its neighbours, so no row stands near empty.
    runs, run = [], []
    for y in years:
        n = sum(t["date"].startswith(y) for t in TRIPS)
        if n >= 3:
            if run:
                runs.append(run)
                run = []
            runs.append([y])
        else:
            run.append(y)
    if run:
        runs.append(run)
    groups = []
    for run in runs:
        ts = [t for t in TRIPS if t["date"][:4] in run]
        label = run[0] if len(run) == 1 else f"{run[-1]} to {run[0]}"
        gid = "y" + run[-1]
        cards = "".join(trip_card(t, "(max-width: 48rem) 50vw, (max-width: 64rem) 33vw, 25vw") for t in ts)
        groups.append(f"""<section class="year" data-years="{' '.join(run)}" aria-labelledby="{gid}">
  <div class="year-head"><h2 id="{gid}">{label}</h2><p><span class="num">{len(ts)}</span> {"trip" if len(ts) == 1 else "trips"}</p></div>
  <ul class="trip-grid">{cards}</ul>
</section>""")
    lede = "".join(f"<p>{inline(p)}</p>" for p in c["trips_page"]["text"])
    page = head(
        "My Trips | John Bezaitis",
        "Here you can find photos of the countries I've traveled to, and the trips I've taken.",
        "/trips/",
    ) + nav("/trips/") + f"""<main id="main">
<section class="page-head">
  <div class="wrap banner">
    <h1>My Trips</h1>
    <div class="lede">{lede}</div>
  </div>
</section>

<section aria-label="Map of every trip">
  <div class="wrap">
    <div class="sheet atlas" data-atlas-root>
      <div class="atlas-main">
        <div class="atlas-tools">
          <fieldset><legend>Year</legend>{chips}</fieldset>
          <fieldset><legend>View</legend>{views}</fieldset>
        </div>
        {map_figure("full", "countries-50m.json")}
        <div class="atlas-stats" aria-live="polite">
          <p class="stat"><span class="num" data-stat="trips">{len(TRIPS)}</span><span>trips</span></p>
          <p class="stat"><span class="num" data-stat="countries">{countries_count(TRIPS)}</span><span>countries and territories</span></p>
          <p class="stat"><span class="num" data-stat="span">{TRIPS[-1]['date'][:4]} to {TRIPS[0]['date'][:4]}</span><span>years travelled</span></p>
        </div>
      </div>
      <nav class="atlas-index" aria-label="Every trip">
        <h2>Every trip, newest first</h2>
        <ol>{index}</ol>
      </nav>
    </div>
  </div>
</section>

<div class="wrap section" style="padding-top: 0">
  {"".join(groups)}
</div>
</main>
""" + footer(trip_data_script() + MAP_SCRIPTS)
    write("/trips/", page)


def pager(prev_item, next_item, base, prev_label, next_label):
    cells = []
    if prev_item:
        cells.append(f'<a href="{base}{prev_item["slug"]}/"><span>{prev_label}</span><strong>{esc(prev_item["title"])}</strong></a>')
    if next_item:
        cells.append(f'<a class="next" href="{base}{next_item["slug"]}/"><span>{next_label}</span><strong>{esc(next_item["title"])}</strong></a>')
    return f'<nav class="pager" aria-label="More">{"".join(cells)}</nav>'


def build_trip(i, t):
    newer = TRIPS[i - 1] if i > 0 else None
    older = TRIPS[i + 1] if i + 1 < len(TRIPS) else None
    when = month_long(t["date"])
    text = "".join(f"<p>{inline(p)}</p>" for p in t["text"])
    cover = img(t["slug"], t["photos"][0], f"{t['title']}, {when}", "(max-width: 56rem) 100vw, 58vw", eager=True)
    rest = gallery(t["slug"], t["title"], t["photos"][1:], start=1)
    place = ", ".join(COUNTRY_NAMES[c] for c in t["countries"])
    loc_caption = f'<figcaption class="meta">{esc(t["title"])} on the map{"" if place == t["title"] else ", " + esc(place)}</figcaption>'
    page = head(f"{t['title']} | John Bezaitis", first_sentence(t["text"][0]), f"/trips/{t['slug']}/") + nav("/trips/") + f"""<main id="main" data-gallery>
<div class="wrap feature">
  <div>
    <a class="crumb" href="/trips/">All trips</a>
    <h1>{esc(t['title'])}</h1>
    <time class="when" datetime="{t['date']}">{when}</time>
    <div class="prose">{text}</div>
    <figure class="sheet locator">
      {map_figure("locator", "countries-50m.json" if t.get("pin") else "countries-110m.json", loc_caption, focus=t['slug'], label=f"Map locating {t['title']}")}
    </figure>
  </div>
  <figure class="feature-photo">
    <a class="photo-btn" href="/assets/img/{t['slug']}/{t['photos'][0]}" data-index="0" aria-label="Open {esc(t['title'])}, photo 1 of {len(t['photos'])}">{cover}</a>
  </figure>
</div>
<section class="wrap" aria-label="Photos from {esc(t['title'])}">
  {rest}
</section>
<div class="wrap section section--tight">
  {pager(older, newer, "/trips/", "Earlier trip", "Later trip")}
</div>
{LIGHTBOX}</main>
""" + footer(trip_data_script() + MAP_SCRIPTS + GALLERY_SCRIPT)
    write(f"/trips/{t['slug']}/", page)


def build_work_index():
    c = CONTENT
    wp = c["work_page"]
    projects = "".join(project_card(w) for w in WORK)
    body = "".join(f"<p>{inline(p)}</p>" for p in wp["text"][1:])
    page = head(
        "My Work | John Bezaitis",
        "Here you can find my works and projects completed in the Investment Management Academy and my coursework.",
        "/work/",
    ) + nav("/work/") + f"""<main id="main">
<section class="page-head">
  <div class="wrap banner">
    <h1>My Work</h1>
    <div>
      <p class="lede">{inline(wp['text'][0])}</p>
      <div class="actions" style="margin-top: var(--space-md)"><a class="btn btn--primary" href="{esc(c['resume'])}">Resume</a></div>
    </div>
  </div>
</section>
<section class="section section--well">
  <div class="wrap background">
    <div>
      <h2>Background</h2>
      <div class="prose">{body}</div>
    </div>
    {collage(WORK)}
  </div>
</section>
<section class="section">
  <div class="wrap">
    <div class="section-head"><h2>All projects</h2></div>
    <ul class="project-grid">{projects}</ul>
    <div class="prose" style="margin-top: var(--space-2xl)"><p>{inline(wp['closing'])}</p></div>
  </div>
</section>
</main>
""" + footer()
    write("/work/", page)


def build_work(i, w):
    prev_w = WORK[i - 1] if i > 0 else None
    next_w = WORK[i + 1] if i + 1 < len(WORK) else None
    links = w["links"]
    actions = "".join(
        f'<a class="btn{" btn--primary" if j == 0 else ""}" href="{esc(l["href"])}">Open the {l["label"].lower()}</a>'
        for j, l in enumerate(links)
    )
    folder = f"work-{w['slug']}"
    logo = img(folder, w["logo"], f"{w['title']} logo", "20rem", eager=True, small=False)
    exhibit = img(folder, w["exhibit"], f"Summary exhibit from the {w['title']} analysis", "(max-width: 90rem) 100vw, 1360px", small=False)
    text = "".join(f"<p>{inline(p)}</p>" for p in w["text"])
    page = head(f"{w['title']} | John Bezaitis", first_sentence(w["summary"]), f"/work/{w['slug']}/") + nav("/work/") + f"""<main id="main">
<div class="wrap doc-head">
  <div>
    <a class="crumb" href="/work/">All work</a>
    <h1>{esc(w['title'])}</h1>
    <p class="lede">{inline(w['summary'])}</p>
    <div class="actions">{actions}</div>
  </div>
  <div class="logo-plate">{logo}</div>
</div>
<div class="wrap">
  <figure class="sheet exhibit"><a class="exhibit-scroll" href="/assets/img/{folder}/{w['exhibit']}" aria-label="Open the full-size exhibit">{exhibit}</a><figcaption class="meta">From the {w.get("exhibit_source") or ("model" if any(l["label"] == "Model" for l in links) else "report")}.</figcaption></figure>
</div>
<section class="wrap section">
  <div class="doc-body">
    <h2>Overview</h2>
    <div class="prose">{text}</div>
  </div>
</section>
<div class="wrap section section--tight" style="padding-top: 0">
  {pager(prev_w, next_w, "/work/", "Previous project", "Next project")}
</div>
</main>
""" + footer()
    write(f"/work/{w['slug']}/", page)


def build_about():
    a = CONTENT["about"]
    t = [f"<p>{inline(p)}</p>" for p in a["text"]]
    p1, p2 = a["photos"]
    page = head(
        "About Me | John Bezaitis",
        "A student with a passion for finance, data-analytics, and education.",
        "/about/",
    ) + nav("/about/") + f"""<main id="main">
<section class="page-head"><div class="wrap"><h1>About Me</h1></div></section>
<div class="wrap section" style="padding-top: 0">
  <div class="about-grid">
    <div class="prose">{"".join(t)}</div>
    <div class="about-photos">
      <figure>{img("about", p1["file"], p1["alt"], "(max-width: 52rem) 100vw, 40vw", eager=True)}</figure>
      <figure>{img("about", p2["file"], p2["alt"], "(max-width: 52rem) 100vw, 40vw")}</figure>
    </div>
  </div>
</div>
</main>
""" + footer()
    write("/about/", page)


def build_gallery_page(p):
    text = "".join(f"<p>{inline(x)}</p>" for x in p["text"])
    cover = img(p["slug"], p["photos"][0], f"{p['title']}, photo 1 of {len(p['photos'])}", "(max-width: 56rem) 100vw, 58vw", eager=True)
    page = head(f"{p['title']} | John Bezaitis", first_sentence(p["text"][0]), f"/{p['slug']}/") + nav("") + f"""<main id="main" data-gallery>
<div class="wrap feature">
  <div>
    <h1>{esc(p['title'])}</h1>
    <div class="prose">{text}</div>
  </div>
  <figure class="feature-photo">
    <a class="photo-btn" href="/assets/img/{p['slug']}/{p['photos'][0]}" data-index="0" aria-label="Open {esc(p['title'])}, photo 1 of {len(p['photos'])}">{cover}</a>
  </figure>
</div>
<section class="wrap section" style="padding-top: 0" aria-label="Photos">
  {gallery(p["slug"], p["title"], p["photos"][1:], start=1)}
</section>
{LIGHTBOX}</main>
""" + footer(GALLERY_SCRIPT)
    write(f"/{p['slug']}/", page)


def build_404():
    page = head("Page not found | John Bezaitis", "This page does not exist.", "/404.html") + nav("") + """<main id="main">
<div class="wrap lost">
  <h1>Nothing here</h1>
  <p class="lede">This page moved or never existed.</p>
  <div class="actions" style="margin-top: var(--space-lg)"><a class="btn btn--primary" href="/trips/">Browse the trips</a><a class="btn" href="/">Home</a></div>
</div>
</main>
""" + footer()
    (ROOT / "404.html").write_text(bust(new_tabs(page)))


def main():
    build_home()
    build_trips()
    for i, t in enumerate(TRIPS):
        build_trip(i, t)
    build_work_index()
    for i, w in enumerate(WORK):
        build_work(i, w)
    build_about()
    for p in CONTENT["pages"]:
        build_gallery_page(p)
    build_404()
    print(f"Built {len(TRIPS)} trips, {len(WORK)} projects and {len(CONTENT['pages'])} gallery pages.")


if __name__ == "__main__":
    main()
