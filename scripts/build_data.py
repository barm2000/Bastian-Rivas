#!/usr/bin/env python3
from pathlib import Path
from urllib.parse import quote, urljoin
from datetime import datetime, timezone
from html import escape as html_escape
import json, re, sys

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "content"
DATA_DIR = ROOT / "data"
MEDIA_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".mp4", ".webm", ".mov"}
VIDEO_EXTS = {".mp4", ".webm", ".mov"}

ALIASES = {
    "title":"title", "titulo":"title", "name":"title", "nombre":"title",
    "label":"label", "etiqueta":"label",
    "summary":"summary", "resumen":"summary",
    "description":"description", "descripcion":"description",
    "technologies":"technologies", "tecnologias":"technologies",
    "link":"link", "enlace":"link",
    "linktext":"linkText", "textoenlace":"linkText",
    "order":"order", "orden":"order",
    "placeholder":"placeholder",
    "cover":"cover", "portada":"cover",
    "mediafit":"mediaFit", "ajustemultimedia":"mediaFit", "ajusteimagen":"mediaFit",
    "relatedtitle":"relatedTitle", "titulorelacionado":"relatedTitle", "difusiontitle":"relatedTitle",
    "relatedfile":"relatedFile", "archivorelacionado":"relatedFile", "difusionfile":"relatedFile",
    "type":"type", "tipo":"type",
    "role":"role", "rol":"role",
    "year":"year", "ano":"year", "año":"year",
    "date":"date", "fecha":"date",
    "datetext":"dateText", "fechatexto":"dateText",
    "authors":"authors", "autores":"authors",
    "source":"source", "fuente":"source",
    "details":"details", "detalles":"details",
    "student":"student", "estudiante":"student",
    "degree":"degree", "titulo_profesional":"degree", "programa":"degree",
    "institution":"institution", "institucion":"institution",
    "guide":"guide", "guia":"guide",
    "coguide":"coGuide", "coguia":"coGuide",
    "status":"status", "estado":"status",
    "platforms":"platforms", "plataformas":"platforms",
    "participants":"participants", "participantes":"participants",
    "kicker":"kicker", "intro":"intro",
    "keywords":"keywords", "palabrasclave":"keywords",
    "color":"color", "category":"category", "categoria":"category",
    "short":"short", "sigla":"short",
    "showinnavbar":"showInNavbar", "mostrarennavbar":"showInNavbar",
    "brand":"brand", "marca":"brand",
    "browsertitle":"browserTitle", "titulonavegador":"browserTitle",
    "metadescription":"metaDescription", "descripcionmeta":"metaDescription",
    "footername":"footerName", "nombrefinal":"footerName",
    "footertext":"footerText", "textofinal":"footerText",
    "eyebrow":"eyebrow",
    "nameline1":"nameLine1", "nombrelinea1":"nameLine1",
    "nameline2":"nameLine2", "nombrelinea2":"nameLine2",
    "subtitle":"subtitle", "subtitulo":"subtitle",
    "tags":"tags", "etiquetas":"tags",
    "primarytext":"primaryText", "textoprimario":"primaryText",
    "primarylink":"primaryLink", "enlaceprimario":"primaryLink",
    "secondarytext":"secondaryText", "textosecundario":"secondaryText",
    "secondarylink":"secondaryLink", "enlacesecundario":"secondaryLink",
    "qrimage":"qrImage", "imagenqr":"qrImage",
    "qrtitle":"qrTitle", "tituloqr":"qrTitle",
    "qrtext":"qrText", "textoqr":"qrText",
    "navknowledge":"navKnowledge",
    "navfocus":"navFocus",
    "navprojects":"navProjects",
    "navproduction":"navProduction",
    "navformation":"navFormation",
    "navtools":"navTools",
    "navcourses":"navCourses",
    "navcontact":"navContact",
    "siteurl":"siteURL", "urlsitio":"siteURL",
    "language":"language", "idioma":"language",
    "robots":"robots",
    "googlesiteverification":"googleSiteVerification", "verificaciongoogle":"googleSiteVerification",
    "socialimage":"socialImage", "imagensocial":"socialImage",
}

def norm_key(key):
    k = key.strip().lower().replace(" ", "").replace("-", "_")
    return ALIASES.get(k, key.strip())

def parse_info(path):
    data = {}
    current = None
    if not path.exists():
        return data
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        m = re.match(r"^([^:]+):\s*(.*)$", line)
        if m:
            current = norm_key(m.group(1))
            data[current] = m.group(2).strip()
        elif current:
            extra = line.strip()
            data[current] = (str(data.get(current, "")) + " " + extra).strip()
    return data

def split_list(value):
    return [x.strip() for x in str(value or "").split(";") if x.strip()]

def as_bool(value, default=True):
    if value is None or str(value).strip() == "": return default
    return str(value).strip().lower() not in {"0","false","no","off","n"}

def media_type(path):
    return "video" if path.suffix.lower() in VIDEO_EXTS else "image"

def web_path(path):
    rel = path.relative_to(ROOT).as_posix()
    return quote(rel, safe="/-_.~")

def collect_media(folder, requested_cover=""):
    files = sorted([p for p in folder.rglob("*") if p.is_file() and p.suffix.lower() in MEDIA_EXTS], key=lambda p: p.as_posix().lower())
    media = [{"src": web_path(p), "type": media_type(p), "name": p.name} for p in files]
    cover = None
    requested_cover = str(requested_cover or "").strip()
    if requested_cover:
        candidate = folder / requested_cover
        if candidate.exists() and candidate.is_file():
            cover = {"src": web_path(candidate), "type": media_type(candidate), "name": candidate.name}
        else:
            by_name = next((m for m in media if m["name"] == Path(requested_cover).name), None)
            if by_name: cover = by_name
            elif re.match(r"^(https?:|/|\.\.?/)", requested_cover):
                ext = Path(requested_cover.split("?")[0]).suffix.lower()
                cover = {"src": requested_cover, "type": "video" if ext in VIDEO_EXTS else "image", "name": Path(requested_cover).name}
            else:
                print(f"ADVERTENCIA: portada no encontrada: {folder.relative_to(ROOT)}/{requested_cover}", file=sys.stderr)
    if cover is None and media:
        cover = media[0]
    return media, cover

def resolve_media_ref(base, value):
    raw = str(value or "").strip()
    if not raw: return None
    candidate = base / raw
    if candidate.exists() and candidate.is_file():
        return {"src": web_path(candidate), "type": media_type(candidate), "name": candidate.name}
    if re.match(r"^(https?:|/|\.\.?/)", raw):
        ext = Path(raw.split("?")[0]).suffix.lower()
        return {"src": raw, "type": "video" if ext in VIDEO_EXTS else "image", "name": Path(raw).name}
    print(f"ADVERTENCIA: archivo multimedia no encontrado: {base.relative_to(ROOT)}/{raw}", file=sys.stderr)
    return None

def parse_related_links(path):
    """Lee enlaces relacionados: Fecha | Tipo | Título | URL.

    También acepta Tipo | Título | URL o Título | URL.
    """
    if not path.exists() or not path.is_file():
        return []
    items = []
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) >= 4:
            date, kind, title = parts[0], parts[1], parts[2]
            url = "|".join(parts[3:]).strip()
        elif len(parts) == 3:
            date, kind, title, url = "", parts[0], parts[1], parts[2]
        elif len(parts) == 2:
            date, kind, title, url = "", "Recurso", parts[0], parts[1]
        else:
            print(f"ADVERTENCIA: línea inválida en {path.relative_to(ROOT)}: {raw}", file=sys.stderr)
            continue
        if title and url:
            items.append({"date": date, "type": kind or "Recurso", "title": title, "url": url})
    if any(item.get("date") for item in items):
        indexed = list(enumerate(items))
        indexed.sort(key=lambda pair: (pair[1].get("date", ""), -pair[0]), reverse=True)
        items = [item for _, item in indexed]
    return items

def as_int(value, default=0):
    try: return int(str(value).strip())
    except Exception: return default

def load_singleton(name):
    d = parse_info(CONTENT / name / "info.txt")
    if name == "profile":
        d["tags"] = split_list(d.get("tags"))
    return d

def load_section(name):
    d = parse_info(CONTENT / name / "section.txt")
    if name == "contact" and d.get("qrImage"):
        d["qr"] = resolve_media_ref(CONTENT / name, d.get("qrImage"))
    return d

def load_collection(name):
    base = CONTENT / name
    items = []
    if not base.exists(): return items
    for folder in sorted([p for p in base.iterdir() if p.is_dir() and not p.name.startswith(('_','.'))]):
        info = folder / "info.txt"
        if not info.exists():
            print(f"ADVERTENCIA: {folder.relative_to(ROOT)} no tiene info.txt; se omite.", file=sys.stderr)
            continue
        d = parse_info(info)
        if not d.get("title"):
            raise SystemExit(f"ERROR: falta Title/Titulo en {info.relative_to(ROOT)}")
        d["folder"] = folder.name
        d["order"] = as_int(d.get("order"), 9999)
        media, cover = collect_media(folder, d.get("cover", ""))
        d["media"] = media
        d["cover"] = cover
        if name == "projects":
            related_file = str(d.get("relatedFile") or "links.txt").strip()
            d["relatedLinks"] = parse_related_links(folder / related_file)
            if d["relatedLinks"]:
                d["relatedTitle"] = str(d.get("relatedTitle") or "Difusión y vinculación").strip()
        if name == "courses": d["participants"] = max(0, as_int(d.get("participants"), 0))
        if name in {"production", "formation"}:
            d["year"] = str(d.get("year", "")).strip()
            d["date"] = str(d.get("date") or d.get("year") or "").strip()
        if name == "knowledge": d["keywords"] = split_list(d.get("keywords"))
        if name == "memberships": d["showInNavbar"] = as_bool(d.get("showInNavbar"), True)
        items.append(d)
    if name in {"production", "formation"}:
        items.sort(key=lambda x: (x.get("date", ""), -x.get("order",9999)), reverse=True)
    else:
        items.sort(key=lambda x: (x.get("order",9999), x.get("title","").lower()))
    return items

def normalize_site_url(value):
    url = str(value or "").strip()
    if not url:
        return ""
    if not re.match(r"^https?://", url, flags=re.I):
        url = "https://" + url.lstrip("/")
    return url.rstrip("/") + "/"


def clean_verification_token(value):
    raw = str(value or "").strip()
    if not raw:
        return ""
    m = re.search(r'content=["\']([^"\']+)["\']', raw, flags=re.I)
    return (m.group(1) if m else raw).strip()


def absolute_asset_url(site_url, value):
    raw = str(value or "").strip()
    if not raw:
        return ""
    if re.match(r"^https?://", raw, flags=re.I):
        return raw
    return urljoin(site_url, raw.lstrip("/"))


def build_structured_data(data, site_url):
    site = data.get("site", {})
    profile = data.get("profile", {})
    full_name = " ".join(
        x for x in [profile.get("nameLine1", ""), profile.get("nameLine2", "")] if x
    ).strip()

    same_as = []
    for item in data.get("contact", []):
        link = str(item.get("link") or "").strip()
        if re.match(r"^https?://", link, flags=re.I):
            same_as.append(link)

    member_of = []
    for item in data.get("memberships", []):
        org = {"@type": "Organization", "name": item.get("title", "")}
        link = str(item.get("link") or "").strip()
        if re.match(r"^https?://", link, flags=re.I):
            org["url"] = link
        if org.get("name"):
            member_of.append(org)

    knows = []
    for value in profile.get("tags", []):
        if value and value not in knows:
            knows.append(value)
    for item in data.get("knowledge", []):
        values = [item.get("title", "")] + list(item.get("keywords", []))
        for value in values:
            if value and value not in knows:
                knows.append(value)

    person = {
        "@type": "Person",
        "@id": site_url + "#person",
        "name": full_name or site.get("footerName", ""),
        "url": site_url,
        "description": profile.get("description") or site.get("metaDescription", ""),
        "jobTitle": profile.get("subtitle", ""),
        "sameAs": same_as,
        "memberOf": member_of,
        "knowsAbout": knows,
    }
    website = {
        "@type": "WebSite",
        "@id": site_url + "#website",
        "url": site_url,
        "name": site.get("browserTitle") or full_name or "Portafolio",
        "description": site.get("metaDescription", ""),
        "inLanguage": site.get("language") or "es-CL",
        "mainEntity": {"@id": site_url + "#person"},
    }
    return {"@context": "https://schema.org", "@graph": [website, person]}


def render_seo_block(data, site_url):
    site = data.get("site", {})
    profile = data.get("profile", {})
    title = str(site.get("browserTitle") or "Portafolio").strip()
    description = str(
        site.get("metaDescription") or profile.get("description") or ""
    ).strip()
    author = " ".join(
        x for x in [profile.get("nameLine1", ""), profile.get("nameLine2", "")] if x
    ).strip() or str(site.get("footerName") or "").strip()
    language = str(site.get("language") or "es-CL").strip()
    robots = str(
        site.get("robots")
        or "index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1"
    ).strip()
    verification = clean_verification_token(site.get("googleSiteVerification"))
    social_image = absolute_asset_url(site_url, site.get("socialImage")) if site_url else ""
    structured = build_structured_data(data, site_url) if site_url else {}

    lines = [
        "<!-- SEO:AUTO:START -->",
        f'<title>{html_escape(title)}</title>',
        f'<meta name="description" content="{html_escape(description, quote=True)}">',
        f'<meta name="author" content="{html_escape(author, quote=True)}">',
        f'<meta name="robots" content="{html_escape(robots, quote=True)}">',
    ]
    if site_url:
        lines.extend([
            f'<link rel="canonical" href="{html_escape(site_url, quote=True)}">',
            f'<link rel="sitemap" type="application/xml" href="{html_escape(urljoin(site_url, "sitemap.xml"), quote=True)}">',
            '<meta property="og:type" content="profile">',
            f'<meta property="og:site_name" content="{html_escape(site.get("brand") or "BARM", quote=True)}">',
            f'<meta property="og:title" content="{html_escape(title, quote=True)}">',
            f'<meta property="og:description" content="{html_escape(description, quote=True)}">',
            f'<meta property="og:url" content="{html_escape(site_url, quote=True)}">',
            f'<meta property="og:locale" content="{html_escape(language.replace("-", "_"), quote=True)}">',
            '<meta name="twitter:card" content="summary">',
            f'<meta name="twitter:title" content="{html_escape(title, quote=True)}">',
            f'<meta name="twitter:description" content="{html_escape(description, quote=True)}">',
        ])
        if social_image:
            lines.extend([
                f'<meta property="og:image" content="{html_escape(social_image, quote=True)}">',
                f'<meta name="twitter:image" content="{html_escape(social_image, quote=True)}">',
            ])
    if verification:
        lines.append(
            f'<meta name="google-site-verification" content="{html_escape(verification, quote=True)}">'
        )
    if structured:
        structured_text = json.dumps(
            structured, ensure_ascii=False, separators=(",", ":")
        ).replace("</", "<\\/")
        lines.append(f'<script type="application/ld+json">{structured_text}</script>')
    if site_url:
        icon_base = site_url.rstrip("/") + "/"
        lines.extend([
            f'<link rel="icon" href="{html_escape(icon_base + "favicon.ico?v=20261118", quote=True)}" sizes="any">',
            f'<link rel="icon" type="image/png" sizes="512x512" href="{html_escape(icon_base + "favicon.png?v=20261118", quote=True)}">',
            f'<link rel="shortcut icon" type="image/x-icon" href="{html_escape(icon_base + "favicon.ico?v=20261118", quote=True)}">',
            f'<link rel="apple-touch-icon" sizes="180x180" href="{html_escape(icon_base + "apple-touch-icon.png?v=20261118", quote=True)}">',
        ])
    lines.append("<!-- SEO:AUTO:END -->")
    return "\n".join(lines)


def update_index_seo(data):
    index_path = ROOT / "index.html"
    if not index_path.exists():
        return

    source = index_path.read_text(encoding="utf-8")
    site_url = normalize_site_url(data.get("site", {}).get("siteURL"))
    language = str(data.get("site", {}).get("language") or "es-CL").strip()
    source = re.sub(
        r'<html\s+lang="[^"]*">',
        f'<html lang="{html_escape(language, quote=True)}">',
        source,
        count=1,
        flags=re.I,
    )
    block = render_seo_block(data, site_url)

    if '<!-- SEO:AUTO:START -->' in source and '<!-- SEO:AUTO:END -->' in source:
        source = re.sub(
            r'<!-- SEO:AUTO:START -->.*?<!-- SEO:AUTO:END -->',
            lambda _m: block,
            source,
            count=1,
            flags=re.S,
        )
    else:
        source = re.sub(r'\s*<meta[^>]+name=["\']description["\'][^>]*>', '', source, count=1, flags=re.I)
        source = re.sub(r'\s*<meta[^>]+name=["\']keywords["\'][^>]*>', '', source, count=1, flags=re.I)
        source = re.sub(r'\s*<meta[^>]+name=["\']author["\'][^>]*>', '', source, count=1, flags=re.I)
        source = re.sub(r'\s*<title>.*?</title>', '', source, count=1, flags=re.I | re.S)
        viewport = re.search(r'<meta[^>]+name=["\']viewport["\'][^>]*>', source, flags=re.I)
        if viewport:
            pos = viewport.end()
            source = source[:pos] + "\n" + block + source[pos:]
        else:
            source = source.replace('<head>', '<head>\n' + block, 1)

    index_path.write_text(source, encoding="utf-8")


def generate_seo_files(data):
    site_url = normalize_site_url(data.get("site", {}).get("siteURL"))
    if not site_url:
        print(
            "ADVERTENCIA: SiteURL vacío; no se generan sitemap.xml ni robots.txt.",
            file=sys.stderr,
        )
        return

    robots_text = (
        "User-agent: *\n"
        "Allow: /\n\n"
        "Sitemap: " + urljoin(site_url, "sitemap.xml") + "\n"
    )
    (ROOT / "robots.txt").write_text(robots_text, encoding="utf-8")

    lastmod = datetime.now(timezone.utc).date().isoformat()
    sitemap = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        '  <url>\n'
        f'    <loc>{html_escape(site_url)}</loc>\n'
        f'    <lastmod>{lastmod}</lastmod>\n'
        '  </url>\n'
        '</urlset>\n'
    )
    (ROOT / "sitemap.xml").write_text(sitemap, encoding="utf-8")
    update_index_seo(data)


def validate(data):
    allowed_type = {"Publicación", "Proyecto"}
    allowed_prod_role = {"Autor", "Colaborador"}
    allowed_form_role = {"Guía", "Co-guía"}
    for x in data["production"]:
        if x.get("type") and x["type"] not in allowed_type:
            print(f"ADVERTENCIA: Type '{x['type']}' no estándar en production/{x['folder']}", file=sys.stderr)
        if x.get("role") and x["role"] not in allowed_prod_role:
            print(f"ADVERTENCIA: Role '{x['role']}' no estándar en production/{x['folder']}", file=sys.stderr)
    for x in data["formation"]:
        if x.get("role") and x["role"] not in allowed_form_role:
            print(f"ADVERTENCIA: Role '{x['role']}' no estándar en formation/{x['folder']}", file=sys.stderr)

def main():
    collections = ["memberships","knowledge","focus","projects","production","formation","tools","courses","contact"]
    section_names = ["memberships","knowledge","focus","projects","production","formation","tools","courses","contact"]
    data = {
        "site": load_singleton("site"),
        "profile": load_singleton("profile"),
        "sections": {name: load_section(name) for name in section_names},
    }
    for name in collections:
        data[name] = load_collection(name)
    validate(data)
    generate_seo_files(data)
    DATA_DIR.mkdir(exist_ok=True)
    json_text = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    (DATA_DIR / "site-data.json").write_text(json_text, encoding="utf-8")
    (DATA_DIR / "site-data.js").write_text("window.PORTFOLIO_DATA = " + json_text.rstrip() + ";\n", encoding="utf-8")
    print(
        "OK: "
        f"{len(data['memberships'])} membresías, {len(data['knowledge'])} áreas, {len(data['focus'])} enfoques, "
        f"{len(data['projects'])} proyectos, {len(data['production'])} contribuciones, {len(data['formation'])} formación, "
        f"{len(data['tools'])} herramientas, {len(data['courses'])} cursos, {len(data['contact'])} enlaces de contacto."
    )

if __name__ == "__main__": main()
