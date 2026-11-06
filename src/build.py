"""data/subsidies.json から静的サイトを docs/ に生成する。事実項目はAPIの値をそのまま出す。"""
import html
import json
import shutil
from datetime import datetime, timedelta, timezone

from design import CSS
from config import (ADSENSE_CLIENT, AFFILIATE_LINKS, CF_ANALYTICS_TOKEN, DATA_DIR, OUT_DIR, SITE_DESC,
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
    cf = ("<script defer src=\"https://static.cloudflareinsights.com/beacon.min.js\" data-cf-beacon='"
          + json.dumps({"token": CF_ANALYTICS_TOKEN}) + "'></script>"
          if CF_ANALYTICS_TOKEN else "")
    return f"""<!doctype html><html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title><meta name="description" content="{esc(desc or SITE_DESC)}">
<link rel="canonical" href="{SITE_URL}/{path}">{extra_head}{ads}{cf}<style>{CSS}</style></head><body>
<header class="site-h"><div class="w"><a class="brand" href="{SITE_URL}/"><i>補</i>{esc(SITE_NAME)}</a>
<nav class="nav"><a href="{SITE_URL}/">補助金一覧</a><a href="{SITE_URL}/deadline.html">今月締切</a><a href="{SITE_URL}/guide.html">使い方</a></nav></div></header>
{hero}<main class="w">{body}</main>
<footer><div class="w"><p>{esc(DISCLAIMER)}</p>
<p><a href="{SITE_URL}/guide.html">補助金の探し方・申請の流れ</a> / <a href="{SITE_URL}/about.html">運営者情報・免責</a> / <a href="{SITE_URL}/privacy.html">プライバシーポリシー</a></p>
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
from topics import PURPOSES, PREF_SLUG, GUIDE_HTML

build_detail, build_deadline, build_index, build_topic = make_views(
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
Cookieはブラウザの設定で無効にできます。個人を特定する情報を当サイトが直接収集することはありません。</p>
<h2>アクセス解析について</h2>
<p>当サイトは、閲覧状況の把握のためにアクセス解析ツール(Cloudflare Web Analytics)を利用する場合があります。このツールはCookieを使用せず、個人を特定する情報を収集しません。</p></div>"""
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

    OUT_DIR.mkdir(exist_ok=True)
    for child in OUT_DIR.iterdir():  # フォルダ自体は消さず中身だけ入れ替える(Windowsのロック対策)
        shutil.rmtree(child) if child.is_dir() else child.unlink()
    (OUT_DIR / "s").mkdir()
    (OUT_DIR / "topic").mkdir()
    (OUT_DIR / "area").mkdir()
    # static/ に置いたファイル(Search Console の確認ファイル等)を docs/ 直下へコピー
    static = DATA_DIR.parent / "static"
    if static.exists():
        for f in static.iterdir():
            if f.is_file():
                shutil.copy(f, OUT_DIR / f.name)
    (OUT_DIR / ".nojekyll").write_text("")
    (OUT_DIR / "deadline.html").write_text(build_deadline(items), encoding="utf-8")
    for name, content in static_pages().items():
        (OUT_DIR / name).write_text(content, encoding="utf-8")
    for d, end in items:
        (OUT_DIR / "s" / f"{d['id']}.html").write_text(build_detail(d, end), encoding="utf-8")

    topic_urls, links_p, links_a = [], [], []
    for key, (slug, name, intro) in PURPOSES.items():
        sel = [(d, e) for d, e in items if key in (d.get("use_purpose") or "")]
        if len(sel) < 5:
            continue
        path = f"topic/{slug}.html"
        (OUT_DIR / path).write_text(build_topic(
            path, f"{name}の補助金・助成金(募集中{len(sel)}件)", intro, sel, name,
            f"{name}に使える募集中の補助金・助成金{len(sel)}件を締切順に掲載。上限額・補助率・締切を一覧で確認できます。"), encoding="utf-8")
        topic_urls.append(f"{SITE_URL}/{path}")
        links_p.append(f'<a href="{SITE_URL}/{path}">{esc(name)} <small>{len(sel)}</small></a>')
    areas = {}
    for d, e in items:
        areas.setdefault(area_of(d), []).append((d, e))
    for a, sel in sorted(areas.items(), key=lambda kv: -len(kv[1])):
        if a == "全国":
            slug, intro = "nationwide", "全国の事業者が対象の補助金・助成金です。国の制度や、広域で募集されているものを掲載しています。"
        elif a in PREF_SLUG and len(sel) >= 3:
            slug, intro = PREF_SLUG[a], f"{a}の事業者が対象の補助金・助成金です。県・市区町村などが実施するものを含みます。"
        else:
            continue
        path = f"area/{slug}.html"
        label = "全国対象" if a == "全国" else a
        (OUT_DIR / path).write_text(build_topic(
            path, f"{label}の補助金・助成金(募集中{len(sel)}件)", intro, sel, label,
            f"{label}で募集中の補助金・助成金{len(sel)}件を締切順に掲載。中小企業・個人事業主向けの情報を毎日更新しています。"), encoding="utf-8")
        topic_urls.append(f"{SITE_URL}/{path}")
        links_a.append(f'<a href="{SITE_URL}/{path}">{esc(label)} <small>{len(sel)}</small></a>')
    (OUT_DIR / "guide.html").write_text(page(f"補助金の探し方・申請の流れ|{SITE_NAME}", GUIDE_HTML.format(site=SITE_URL), "guide.html",
        desc="補助金・助成金とは何か、補助率や上限額の見方、申請の一般的な流れと注意点をやさしく解説します。"), encoding="utf-8")
    topic_html = (f'<section class="topics"><h2>目的から探す</h2><div class="tl">{"".join(links_p)}</div>'
                  f'<h2>地域から探す</h2><div class="tl">{"".join(links_a)}</div></section>')
    (OUT_DIR / "index.html").write_text(build_index(items, topic_html), encoding="utf-8")

    urls = [f"{SITE_URL}/", f"{SITE_URL}/deadline.html", f"{SITE_URL}/guide.html", f"{SITE_URL}/about.html", f"{SITE_URL}/privacy.html"] + topic_urls + [
        f"{SITE_URL}/s/{d['id']}.html" for d, _ in items]
    (OUT_DIR / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        + "".join(f"<url><loc>{u}</loc><lastmod>{NOW:%Y-%m-%d}</lastmod></url>" for u in urls) + "</urlset>",
        encoding="utf-8")
    (OUT_DIR / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {SITE_URL}/sitemap.xml\n")
    print(f"生成: {len(items)} 件 → {OUT_DIR}")


if __name__ == "__main__":
    main()
