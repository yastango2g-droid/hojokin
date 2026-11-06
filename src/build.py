"""data/subsidies.json から静的サイトを docs/ に生成する。事実項目はAPIの値をそのまま出す。"""
import html
import json
import shutil
from datetime import datetime, timedelta, timezone

from design import CSS
from config import (ADSENSE_CLIENT, AFFILIATE_LINKS, DATA_DIR, OUT_DIR, SITE_DESC,
                    SITE_NAME, SITE_URL)

JST = timezone(timedelta(hours=9))
NOW = datetime.now(JST)
TODAY = NOW.strftime("%Y年%m月%d日")
esc = html.escape

DISCLAIMER = (
    "本サイトは公的データ(Jグランツ)をもとに情報を整理したもので、申請の可否や採択を保証するものではありません。"
    "募集内容は変更・終了する場合があります。申請前に必ず公式ページで最新の公募要領をご確認ください。"
)


def area_of(d):
    """対象地域。複数地域の連結値は「全国」に丸める(表示・地域フィルタ用)。"""
    a = d.get("target_area_search") or "全国"
    parts = a.split("/")
    return "全国" if "全国" in parts or len(parts) > 3 else a


def jst(iso):
    if not iso:
        return None
    return datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(JST)


def fmt_dt(dt):
    return dt.strftime("%Y年%m月%d日") if dt else "公式ページで確認"


def fmt_yen(n):
    if not n:
        return "公式ページで確認"
    if n >= 100_000_000:
        oku = n / 100_000_000
        return f"{oku:,.0f}億円" if oku == int(oku) else f"{oku:,.1f}億円"
    if n >= 10000:
        man = n / 10000
        return f"{man:,.0f}万円" if man == int(man) else f"{man:,.1f}万円"
    return f"{n:,}円"


def page(title, body, path, desc="", extra_head="", hero=""):
    ads = (
        f'<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={esc(ADSENSE_CLIENT)}" crossorigin="anonymous"></script>'
        if ADSENSE_CLIENT else ""
    )
    return f"""<!doctype html><html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title><meta name="description" content="{esc(desc or SITE_DESC)}">
<link rel="canonical" href="{SITE_URL}/{path}">{extra_head}{ads}<style>{CSS}</style></head><body>
<header class="site-h"><div class="w"><a class="brand" href="{SITE_URL}/"><i>補</i>{esc(SITE_NAME)}</a>
<nav class="nav"><a href="{SITE_URL}/">補助金一覧</a><a href="{SITE_URL}/deadline.html">今月締切</a></nav></div></header>
{hero}<main class="w">{body}</main>
<footer><div class="w"><p>{esc(DISCLAIMER)}</p>
<p><a href="{SITE_URL}/about.html">運営者情報・免責</a> / <a href="{SITE_URL}/privacy.html">プライバシーポリシー</a></p>
<p>出典: <a href="https://www.jgrants-portal.go.jp/">Jグランツ(デジタル庁)</a></p></div></footer></body></html>"""


def affiliate_block():
    if not AFFILIATE_LINKS:
        return ""
    items = "".join(
        f'<li><a href="{esc(a["url"])}" rel="sponsored nofollow noopener">{esc(a["label"])}</a> <span class="meta">[{esc(a.get("note", "PR"))}]</span></li>'
        for a in AFFILIATE_LINKS
    )
    return f'<h2>専門家・関連サービス</h2><ul>{items}</ul><p class="meta">※広告(アフィリエイト)を含みます。</p>'


from views import make_views

build_detail, build_deadline, build_index = make_views(
    page, fmt_dt, fmt_yen, area_of, jst, affiliate_block, DISCLAIMER, NOW)


def static_pages():
    about = f"""<div class="prose"><h1 class="t">運営者情報・免責事項</h1>
<p>{esc(SITE_NAME)}は、Jグランツ(デジタル庁)が公開する補助金データをもとに、募集情報を自動で収集・整理して掲載するサイトです。
一部の概要文は生成AIによる要約です。</p><h2>免責事項</h2><p>{esc(DISCLAIMER)}</p>
<p>掲載内容の誤りや古い情報にお気づきの場合は、公式ページの情報を優先してください。</p>
<h2>広告について</h2><p>当サイトは広告(Google AdSense、アフィリエイトプログラム)を利用する場合があります。広告を含むリンクにはその旨を明記します。</p></div>"""
    priv = """<div class="prose"><h1 class="t">プライバシーポリシー</h1>
<p>当サイトは、アクセス解析や広告配信のためにCookie等を利用する場合があります。広告配信事業者(Google等)は、
Cookieを使用して利用者の過去のアクセス情報に基づく広告を配信することがあります。
Cookieはブラウザの設定で無効にできます。個人を特定する情報を当サイトが直接収集することはありません。</p></div>"""
    return {"about.html": page(f"運営者情報|{SITE_NAME}", about, "about.html"),
            "privacy.html": page(f"プライバシーポリシー|{SITE_NAME}", priv, "privacy.html")}


def main():
    data = json.loads((DATA_DIR / "subsidies.json").read_text(encoding="utf-8"))
    items = []
    for d in data.values():
        end = jst(d.get("acceptance_end_datetime"))
        if end and end < NOW:  # 募集終了は掲載しない
            continue
        items.append((d, end))
    items.sort(key=lambda x: x[1] or NOW + timedelta(days=9999))

    if OUT_DIR.exists():
        shutil.rmtree(OUT_DIR)
    (OUT_DIR / "s").mkdir(parents=True)
    # static/ に置いたファイル(Search Console の確認ファイル等)を docs/ 直下へコピー
    static = DATA_DIR.parent / "static"
    if static.exists():
        for f in static.iterdir():
            if f.is_file():
                shutil.copy(f, OUT_DIR / f.name)
    (OUT_DIR / ".nojekyll").write_text("")
    (OUT_DIR / "index.html").write_text(build_index(items), encoding="utf-8")
    (OUT_DIR / "deadline.html").write_text(build_deadline(items), encoding="utf-8")
    for name, content in static_pages().items():
        (OUT_DIR / name).write_text(content, encoding="utf-8")
    for d, end in items:
        (OUT_DIR / "s" / f"{d['id']}.html").write_text(build_detail(d, end), encoding="utf-8")

    urls = [f"{SITE_URL}/", f"{SITE_URL}/deadline.html", f"{SITE_URL}/about.html", f"{SITE_URL}/privacy.html"] + [
        f"{SITE_URL}/s/{d['id']}.html" for d, _ in items]
    (OUT_DIR / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        + "".join(f"<url><loc>{u}</loc><lastmod>{NOW:%Y-%m-%d}</lastmod></url>" for u in urls) + "</urlset>",
        encoding="utf-8")
    (OUT_DIR / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {SITE_URL}/sitemap.xml\n")
    print(f"生成: {len(items)} 件 → {OUT_DIR}")


if __name__ == "__main__":
    main()
