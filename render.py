"""
HTML Renderer — baca dataset.jsonl, generate portal berita HTML
Gausah GPT lagi, langsung dari data yang udah ada
"""

import json
import random
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ── CONFIG ──────────────────────────────────
JSONL_PATH   = "out_news/dataset.jsonl"
OUT_DIR      = "out_news"
PORTAL_NAME  = "Kabar Nusantara"
TAGLINE      = "Terpercaya, Cepat, Berimbang"
# ────────────────────────────────────────────

BULAN = {1:'Januari',2:'Februari',3:'Maret',4:'April',5:'Mei',6:'Juni',
         7:'Juli',8:'Agustus',9:'September',10:'Oktober',11:'November',12:'Desember'}

def gradient_div(kategori, judul, height="260px"):
    import hashlib
    seed = hashlib.md5(judul.encode()).hexdigest()[:12]
    url = f"https://api.dicebear.com/9.x/shapes/svg?seed={seed}&backgroundColor=0f172a,1e293b,1a1a2e,0d1b2a,1c2951&size=400"
    return f'<img src="{url}" alt="{judul}" style="width:100%;height:{height};object-fit:cover;border-radius:4px;margin-bottom:6px;">'



NAVBAR = lambda name, tagline, back="": f"""<!doctype html>
<html lang="id"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Georgia',serif;background:#f4f4f4;color:#222}}
.navbar{{background:#c0392b}}
.navbar-inner{{max-width:1200px;margin:0 auto;display:flex;align-items:center;justify-content:space-between;padding:12px 20px}}
.logo{{color:#fff;font-size:1.5em;font-weight:900;text-decoration:none;font-family:Arial,sans-serif}}
.logo span{{color:#ffcdd2;font-size:0.5em;font-weight:400;display:block}}
.nav-links a{{color:#ffcdd2;text-decoration:none;font-size:0.85em;font-family:Arial,sans-serif;margin-left:18px}}
.nav-links a:hover{{color:#fff}}
.breaking{{background:#222;color:#ffeb3b;font-size:0.78em;padding:5px 20px;font-family:Arial}}
.container{{max-width:1200px;margin:20px auto;padding:0 20px;display:grid;grid-template-columns:1fr 300px;gap:24px}}
.main{{}} .sidebar{{}}
.card{{background:#fff;border-radius:4px;margin-bottom:18px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.1);cursor:pointer}}
.card:hover{{box-shadow:0 3px 10px rgba(0,0,0,.15)}}
.card img{{width:100%;height:200px;object-fit:cover}}
.card-body{{padding:14px}}
.cat{{font-size:.72em;font-weight:700;text-transform:uppercase;color:#c0392b;letter-spacing:.5px;font-family:Arial;margin-bottom:5px}}
.title{{font-size:1.1em;font-weight:700;line-height:1.35;margin-bottom:6px}}
.title a{{color:#111;text-decoration:none}}
.title a:hover{{color:#c0392b}}
.meta{{font-size:.75em;color:#888;font-family:Arial;margin-bottom:6px}}
.summary{{font-size:.88em;color:#555;line-height:1.6}}
.headline img{{height:320px}}
.headline .title{{font-size:1.4em}}
.badge{{background:#c0392b;color:#fff;font-size:.65em;padding:2px 6px;border-radius:2px;font-family:Arial;font-weight:700;margin-right:5px}}
.sw{{background:#fff;border-radius:4px;padding:14px;margin-bottom:18px;box-shadow:0 1px 3px rgba(0,0,0,.1)}}
.sw-title{{font-size:.82em;font-weight:700;text-transform:uppercase;letter-spacing:.5px;border-bottom:2px solid #c0392b;padding-bottom:7px;margin-bottom:12px;font-family:Arial}}
.si{{padding:9px 0;border-bottom:1px solid #eee;font-size:.84em}}
.si:last-child{{border-bottom:none}}
.si a{{color:#222;text-decoration:none;line-height:1.4;display:block}}
.si a:hover{{color:#c0392b}}
.si .sm{{font-size:.74em;color:#999;margin-top:2px;font-family:Arial}}
.footer{{background:#222;color:#aaa;text-align:center;padding:22px;font-size:.8em;font-family:Arial;margin-top:30px}}
/* Article page */
.art-container{{max-width:780px;margin:0 auto;padding:28px 20px}}
.art-cat{{font-size:.75em;font-weight:700;text-transform:uppercase;color:#c0392b;letter-spacing:.5px;font-family:Arial;margin-bottom:8px}}
.art-title{{font-size:1.85em;font-weight:700;line-height:1.25;margin-bottom:8px}}
.art-sub{{font-size:1.05em;color:#555;line-height:1.5;margin-bottom:14px;font-style:italic}}
.art-meta{{font-size:.78em;color:#888;font-family:Arial;display:flex;gap:14px;margin-bottom:18px;flex-wrap:wrap}}
.art-meta .author{{color:#c0392b;font-weight:600}}
.hero{{width:100%;border-radius:4px;margin-bottom:6px;max-height:460px;object-fit:cover}}
.caption{{font-size:.78em;color:#888;font-family:Arial;margin-bottom:22px;font-style:italic}}
.art-body{{font-size:1em;line-height:1.8;color:#333}}
.art-body p{{margin-bottom:15px}}
.art-body blockquote{{border-left:3px solid #c0392b;padding:10px 15px;margin:18px 0;background:#fff8f8;font-style:italic;color:#555}}
.related{{margin-top:28px}}
.rel-title{{font-size:.88em;font-weight:700;text-transform:uppercase;letter-spacing:.5px;border-bottom:2px solid #c0392b;padding-bottom:7px;margin-bottom:14px;font-family:Arial}}
.rel-item{{padding:9px 0;border-bottom:1px solid #eee;font-size:.87em}}
.rel-item a{{color:#222;text-decoration:none}}
.rel-item a:hover{{color:#c0392b}}
.share{{background:#fff;border:1px solid #eee;border-radius:4px;padding:14px;margin-top:22px;font-family:Arial;font-size:.84em}}
.share strong{{display:block;margin-bottom:8px}}
.sbtn{{display:inline-block;padding:5px 13px;border-radius:3px;color:#fff;font-size:.8em;margin-right:7px;border:none;cursor:pointer}}
.fb{{background:#1877f2}}.tw{{background:#1da1f2}}.wa{{background:#25d366}}
@media(max-width:768px){{.container{{grid-template-columns:1fr}}.sidebar{{display:none}}}}
</style></head><body>
<nav class="navbar"><div class="navbar-inner">
<a href="{back}index.html" class="logo">{name}<span>{tagline}</span></a>
<div class="nav-links"><a href="{back}kategori/kriminal.html">Kriminal</a><a href="{back}kategori/keamanan.html">Keamanan</a><a href="{back}kategori/hukum.html">Hukum</a><a href="{back}kategori/bencana.html">Bencana</a><a href="{back}kategori/politik.html">Politik</a><a href="{back}kategori/umum.html">Umum</a></div>
</div></nav>
<div class="breaking">TERKINI: Ikuti terus perkembangan berita dari seluruh Indonesia &nbsp;|&nbsp; Kirim info ke redaksi &nbsp;|&nbsp; Aktifkan notifikasi</div>
"""

FOOTER = lambda name: f"""<div class="footer">&copy; {datetime.now().year} {name}. Seluruh hak cipta dilindungi.<br>Redaksi | Iklan | Karir | Syarat & Ketentuan | Kebijakan Privasi</div></body></html>"""


def fmt_tanggal(iso_str):
    try:
        pub = datetime.fromisoformat(iso_str.replace('Z', '+00:00'))
        pub_local = pub + timedelta(hours=7)
        return f"{pub_local.day} {BULAN[pub_local.month]} {pub_local.year}, {pub_local.strftime('%H:%M')} WIB"
    except:
        return iso_str


def write_article_page(article, out_dir, portal_name, tagline, related):
    berita_dir = Path(out_dir) / "berita"
    berita_dir.mkdir(exist_ok=True)

    tanggal = fmt_tanggal(article.get("published_at", ""))

    # Image
    if article.get("image_local"):
        img_html = f'<img class="hero" src="../images/{article["image_local"]}" alt="{article["judul"]}">\n<p class="caption">Foto: Tim Redaksi / {portal_name}</p>'
    else:
        img_html = gradient_div(article.get("kategori","Umum"), article["judul"], height="260px")

    # Body paragraphs
    isi = article.get("isi", "")
    paragraphs = [p.strip() for p in isi.split('\n') if p.strip()]
    body = ""
    for i, p in enumerate(paragraphs):
        if i == 1 and article.get("kutipan_utama") and article.get("narasumber"):
            body += f'<blockquote>"{article["kutipan_utama"]}"<br><strong>— {article["narasumber"]}, {article.get("jabatan_narasumber","")}</strong></blockquote>\n'
        body += f"<p>{p}</p>\n"

    # Related
    rel_html = ""
    if related:
        rel_html = '<div class="related"><div class="rel-title">Berita Terkait</div>'
        for r in related[:4]:
            rel_html += f'<div class="rel-item"><a href="{r["id"]}.html">{r["judul"]}</a><div style="font-size:.74em;color:#999;font-family:Arial;margin-top:2px">{r.get("kategori","")} &bull; {r.get("lokasi","")}</div></div>'
        rel_html += '</div>'

    html = NAVBAR(portal_name, tagline, back="../")
    html += f"""<div class="art-container">
<div class="art-cat">{article.get("kategori","")}</div>
<h1 class="art-title">{article["judul"]}</h1>
<p class="art-sub">{article.get("subjudul","")}</p>
<div class="art-meta">
  <span class="author">&#9998; {article.get("reporter","")}</span>
  <span>&#128336; {tanggal}</span>
  <span>&#128205; {article.get("lokasi","")}, {article.get("provinsi","")}</span>
</div>
{img_html}
<div class="art-body">{body}</div>
<div class="share"><strong>Bagikan:</strong>
  <button class="sbtn fb">Facebook</button>
  <button class="sbtn tw">Twitter/X</button>
  <button class="sbtn wa">WhatsApp</button>
</div>
{rel_html}
</div>"""
    html += FOOTER(portal_name)

    with open(berita_dir / f"{article['id']}.html", "w", encoding="utf-8") as f:
        f.write(html)


def write_index(articles, out_dir, portal_name, tagline):
    sorted_arts = sorted(articles, key=lambda x: x.get("published_at",""), reverse=True)
    headline = sorted_arts[0]
    recents  = sorted_arts[1:8]
    sidebar  = sorted_arts[8:20]

    def img_src(a, prefix=""):
        if a.get("image_local"):
            return f"{prefix}images/{a['image_local']}"
        return None  # handled by gradient_div below

    html = NAVBAR(portal_name, tagline)
    html += '<div class="container"><div class="main">\n'

    # Headline
    html += f"""<div class="card headline" onclick="location.href='berita/{headline['id']}.html'">
{gradient_div(headline.get("kategori","Umum"), headline["judul"], height="320px") if not headline.get("image_local") else f'<img src="{img_src(headline)}" alt="{headline["judul"]}" style="width:100%;height:320px;object-fit:cover">' }
<div class="card-body">
  <div class="cat"><span class="badge">TERBARU</span>{headline.get("kategori","")}</div>
  <div class="title" style="font-size:1.4em"><a href="berita/{headline['id']}.html">{headline['judul']}</a></div>
  <div class="meta">{headline.get("reporter","")} &bull; {fmt_tanggal(headline.get("published_at",""))} &bull; {headline.get("lokasi","")}, {headline.get("provinsi","")}</div>
  <div class="summary">{headline.get("subjudul","")}</div>
</div></div>\n"""

    # Recent
    for a in recents:
        html += f"""<div class="card" onclick="location.href='berita/{a['id']}.html'">
{gradient_div(a.get("kategori","Umum"), a["judul"]) if not a.get("image_local") else f'<img src="{img_src(a)}" alt="{a["judul"]}" style="width:100%;height:200px;object-fit:cover">' }
<div class="card-body">
  <div class="cat">{a.get("kategori","")}</div>
  <div class="title"><a href="berita/{a['id']}.html">{a['judul']}</a></div>
  <div class="meta">{a.get("reporter","")} &bull; {fmt_tanggal(a.get("published_at",""))} &bull; {a.get("lokasi","")}</div>
  <div class="summary">{a.get("subjudul","")}</div>
</div></div>\n"""

    html += '</div><div class="sidebar">\n'

    # Sidebar terpopuler
    html += '<div class="sw"><div class="sw-title">Terpopuler</div>\n'
    for i, a in enumerate(sidebar[:6], 1):
        html += f'<div class="si"><a href="berita/{a["id"]}.html"><strong style="color:#c0392b;font-family:Arial">{i}.</strong> {a["judul"]}</a><div class="sm">{a.get("kategori","")} &bull; {a.get("provinsi","")}</div></div>\n'
    html += '</div>\n'

    # Sidebar daerah
    html += '<div class="sw"><div class="sw-title">Berita Daerah</div>\n'
    for a in sidebar[6:12]:
        html += f'<div class="si"><a href="berita/{a["id"]}.html">{a["judul"]}</a><div class="sm">{a.get("provinsi","")} &bull; {fmt_tanggal(a.get("published_at",""))}</div></div>\n'
    html += '</div>\n'

    html += '</div></div>\n'
    html += FOOTER(portal_name)

    with open(Path(out_dir) / "index.html", "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Index: {out_dir}/index.html")



KATEGORI_SLUG = {
    "Kriminal": "kriminal",
    "Keamanan": "keamanan",
    "Hukum & Peradilan": "hukum",
    "Kecelakaan & Bencana": "bencana",
    "Sosial & Politik": "politik",
    "Umum": "umum",
}

def write_category_pages(articles, out_dir, portal_name, tagline):
    kat_dir = Path(out_dir) / "kategori"
    kat_dir.mkdir(exist_ok=True)

    # Group by kategori
    grouped = {}
    for a in articles:
        k = a.get("kategori", "Umum")
        grouped.setdefault(k, []).append(a)

    for kat_name, arts in grouped.items():
        slug = KATEGORI_SLUG.get(kat_name, kat_name.lower().replace(" & ", "-").replace(" ", "-"))
        arts_sorted = sorted(arts, key=lambda x: x.get("published_at",""), reverse=True)

        html = NAVBAR(portal_name, tagline, back="../")
        html += f'''<div style="max-width:1200px;margin:20px auto;padding:0 20px">
<h2 style="font-family:Arial,sans-serif;font-size:1.1em;font-weight:700;text-transform:uppercase;
letter-spacing:.5px;border-bottom:3px solid #c0392b;padding-bottom:8px;margin-bottom:20px;color:#111">
{kat_name} <span style="color:#888;font-weight:400;font-size:.85em">({len(arts_sorted)} berita)</span></h2>
<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:18px">'''

        for a in arts_sorted:
            if a.get("image_local"):
                img = f'<img src="../images/{a["image_local"]}" style="width:100%;height:180px;object-fit:cover">'
            else:
                import hashlib
                seed = hashlib.md5(a["judul"].encode()).hexdigest()[:12]
                img = f'<img src="https://api.dicebear.com/9.x/shapes/svg?seed={seed}&backgroundColor=0f172a,1e293b,1a1a2e,0d1b2a,1c2951&size=400" style="width:100%;height:180px;object-fit:cover">'

            html += f'''<div style="background:#fff;border-radius:4px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.1);cursor:pointer" onclick="location.href='../berita/{a["id"]}.html'">
{img}
<div style="padding:12px">
  <div style="font-size:.72em;font-weight:700;text-transform:uppercase;color:#c0392b;font-family:Arial;margin-bottom:4px">{a.get("kategori","")}</div>
  <div style="font-size:.95em;font-weight:700;line-height:1.35;margin-bottom:6px"><a href="../berita/{a["id"]}.html" style="color:#111;text-decoration:none">{a["judul"]}</a></div>
  <div style="font-size:.74em;color:#888;font-family:Arial">{a.get("reporter","")} &bull; {fmt_tanggal(a.get("published_at",""))}</div>
</div></div>'''

        html += '</div></div>'
        html += FOOTER(portal_name)

        with open(kat_dir / f"{slug}.html", "w", encoding="utf-8") as f:
            f.write(html)
        print(f"  Kategori: {kat_name} ({len(arts_sorted)} artikel) -> kategori/{slug}.html")

def main():
    jsonl_path = Path(JSONL_PATH)
    if not jsonl_path.exists():
        print(f"ERROR: {JSONL_PATH} tidak ditemukan. Jalankan bulk_generate.py dulu.")
        return

    articles = []
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                articles.append(json.loads(line))

    print(f"Loaded {len(articles)} artikel dari {JSONL_PATH}")
    print(f"Generating HTML untuk {len(articles)} artikel...")

    out_dir = Path(OUT_DIR)
    out_dir.mkdir(exist_ok=True)
    (out_dir / "berita").mkdir(exist_ok=True)
    (out_dir / "images").mkdir(exist_ok=True)

    for i, a in enumerate(articles):
        related = random.sample([x for x in articles if x["id"] != a["id"]], min(4, len(articles)-1))
        write_article_page(a, str(out_dir), PORTAL_NAME, TAGLINE, related)
        if (i+1) % 100 == 0:
            print(f"  {i+1}/{len(articles)} artikel HTML selesai...")

    write_category_pages(articles, str(out_dir), PORTAL_NAME, TAGLINE)
    write_index(articles, str(out_dir), PORTAL_NAME, TAGLINE)
    print(f"\nSelesai! Buka: {OUT_DIR}/index.html")


if __name__ == "__main__":
    main()