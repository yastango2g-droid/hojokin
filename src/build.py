"""data/subsidies.json から静的サイトを docs/ に生成する。事実項目はAPIの値をそのまま出す。"""
import html
import json
import shutil
from datetime import datetime, timedelta, timezone

from config import (ADSENSE_CLIENT, AFFILIATE_LINKS, DATA_DIR, OUT_DIR, SITE_DESC,
                    SITE_NAME, SITE_URL)

JST = timezone(timedelta(hours=9))
NOW = datetime.now(JST)
TODAY = NOW.strftime("%Y年%m月%d日")
esc = html.escape

CSS = """
:root{--bg:#fff;--fg:#1f2933;--mut:#616e7c;--line:#e4e7eb;--acc:#0b6bcb;--soft:#f5f7fa}
@media(prefers-color-scheme:dark){:root{--bg:#14181d;--fg:#e4e7eb;--mut:#9aa5b1;--line:#2b323a;--acc:#6cb2ff;--soft:#1c2229}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.75 system-ui,"Hiragino Sans","Yu Gothic",sans-serif}
a{color:var(--acc)}.w{max-width:820px;margin:0 auto;padding:0 16px}
header{border-bottom:1px solid var(--line)}header .w{display:flex;justify-content:space-between;align-items:center;padding:14px 16px}
header a{text-decoration:none;color:var(--fg);font-weight:700}
h1{font-size:1.5rem;line-height:1.4}h2{font-size:1.15rem;margin-top:2rem}
.card{display:block;border:1px solid var(--line);border-radius:10px;padding:14px 16px;margin:12px 0;text-decoration:none;color:var(--fg);background:var(--soft)}
.card b{display:block}.meta{color:var(--mut);font-size:.88rem}
.tag{display:inline-block;border:1px solid var(--line);border-radius:99px;padding:0 10px;font-size:.8rem;margin-right:6px;background:var(--bg)}
table{width:100%;border-collapse:collapse}th,td{border-bottom:1px solid var(--line);padding:10px 8px;text-align:left;vertical-align:top}
th{width:9em;color:var(--mut);font-weight:600}
.note{background:var(--soft);border-left:4px solid var(--acc);padding:10px 14px;font-size:.9rem;margin:1.5rem 0}
.btn{display:inline-block;background:var(--acc);color:#fff;padding:10px 18px;border-radius:8px;text-decoration:none;font-weight:700}
select{font:inherit;padding:6px;border:1px solid var(--line);border-radius:6px;background:var(--bg);color:var(--fg)}
footer{border-top:1px solid var(--line);margin-top:3rem;padding:20px 0;color:var(--mut);font-size:.85rem}
"""

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


def page(title, body, path, desc="", extra_head=""):
    ads = (
        f'<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={esc(ADSENSE_CLIENT)}" crossorigin="anonymous"></script>'
        if ADSENSE_CLIENT else ""
    )
    return f"""<!doctype html><html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title><meta name="description" content="{esc(desc or SITE_DESC)}">
<link rel="canonical" href="{SITE_URL}/{path}">{extra_head}{ads}<style>{CSS}</style></head><body>
<header><div class="w"><a href="{SITE_URL}/">{esc(SITE_NAME)}</a><span class="meta">最終更新 {TODAY}</span></div></header>
<main class="w">{body}</main>
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


def build_detail(d, end):
    sid = d["id"]
    area = area_of(d)
    title = d["title"]
    summary = d.get("summary")
    rows = [
        ("申請受付期間", f'{fmt_dt(jst(d.get("acceptance_start_datetime")))} 〜 {fmt_dt(end)}'),
        ("補助上限額", fmt_yen(d.get("subsidy_max_limit"))),
        ("補助率", d.get("subsidy_rate") or "公式ページで確認"),
        ("対象地域", area),
        ("従業員数", d.get("target_number_of_employees") or "公式ページで確認"),
        ("利用目的", d.get("use_purpose") or "公式ページで確認"),
        ("実施機関", d.get("institution_name") or "公式ページで確認"),
    ]
    tbl = "".join(f"<tr><th>{k}</th><td>{esc(str(v))}</td></tr>" for k, v in rows)
    url = d.get("front_subsidy_detail_page_url") or f"https://www.jgrants-portal.go.jp/subsidy/{sid}"
    catch = d.get("subsidy_catch_phrase")
    body = f"""<h1>{esc(title)}</h1>
<p><span class="tag">{esc(area)}</span><span class="tag">締切 {fmt_dt(end)}</span></p>
{f'<p>{esc(catch)}</p>' if catch else ''}
{f'<h2>概要(AIによる要約)</h2><p>{esc(summary)}</p><p class="meta">公募要領をもとにAIが要約したものです。詳細は必ず公式ページをご確認ください。</p>' if summary else ''}
<h2>募集情報</h2><table>{tbl}</table>
<p style="margin-top:1.5rem"><a class="btn" href="{esc(url)}" rel="noopener">公式ページで詳細を見る</a></p>
<div class="note">情報の最終確認日: {TODAY}(Jグランツのデータを自動取得)。{esc(DISCLAIMER)}</div>
{affiliate_block()}
<p><a href="{SITE_URL}/">← 募集中の補助金一覧へ</a></p>"""
    return page(f"{title}|{SITE_NAME}", body, f"s/{sid}.html",
                desc=f"{area}|上限{fmt_yen(d.get('subsidy_max_limit'))}|締切{fmt_dt(end)}。{catch or title}")


def card_html(d, end):
    area = area_of(d)
    days = (end - NOW).days if end else None
    soon = f' <span class="tag">あと{days}日</span>' if days is not None and days <= 14 else ""
    return (
        f'<a class="card" data-area="{esc(area)}" href="{SITE_URL}/s/{d["id"]}.html"><b>{esc(d["title"])}</b>'
        f'<span class="meta">{esc(area)} ／ 上限 {fmt_yen(d.get("subsidy_max_limit"))} ／ 締切 {fmt_dt(end)}{soon}</span></a>'
    )


def build_deadline(items):
    """今月中に締切を迎える案件の集約ページ(検索されやすい切り口)。"""
    month_items = [(d, e) for d, e in items if e and (e.year, e.month) == (NOW.year, NOW.month)]
    label = f"{NOW.year}年{NOW.month}月"
    if month_items:
        listing = "".join(card_html(d, e) for d, e in month_items)
    else:
        listing = "<p>今月締切の案件は現在ありません。</p>"
    body = f"""<h1>{label}に締切を迎える補助金・助成金</h1>
<p>{label}中に申請受付が終了する、募集中の補助金・助成金の一覧です(締切が近い順、{len(month_items)}件)。
締切間際は変更・早期終了もあるため、必ず公式ページで最新情報をご確認ください。</p>
{listing}<p><a href="{SITE_URL}/">← 募集中の補助金一覧へ</a></p>"""
    return page(f"{label}締切の補助金・助成金一覧|{SITE_NAME}", body, "deadline.html",
                desc=f"{label}に申請締切を迎える補助金・助成金の一覧。中小企業・個人事業主向けの募集中案件を締切順に掲載。")


def build_index(items):
    areas = sorted({area_of(d) for d, _ in items})
    opts = "".join(f'<option value="{esc(a)}">{esc(a)}</option>' for a in areas)
    cards = [card_html(d, end) for d, end in items]
    js = """<script>
const s=document.getElementById('area'),c=[...document.querySelectorAll('.card')],n=document.getElementById('n');
s.onchange=()=>{let k=0;c.forEach(e=>{const v=!s.value||e.dataset.area===s.value;e.style.display=v?'':'none';k+=v});n.textContent=k};
</script>"""
    body = f"""<h1>募集中の補助金・助成金一覧</h1><p>{esc(SITE_DESC)}締切が近い順に表示しています。</p>
<p><a href="{SITE_URL}/deadline.html">→ 今月締切の補助金だけ見る</a></p>
<p>地域: <select id="area"><option value="">すべて</option>{opts}</select> <span class="meta"><span id="n">{len(items)}</span> 件</span></p>
{"".join(cards)}{js}"""
    return page(f"募集中の補助金・助成金一覧|{SITE_NAME}", body, "")


def static_pages():
    about = f"""<h1>運営者情報・免責事項</h1>
<p>{esc(SITE_NAME)}は、Jグランツ(デジタル庁)が公開する補助金データをもとに、募集情報を自動で収集・整理して掲載するサイトです。
一部の概要文は生成AIによる要約です。</p><h2>免責事項</h2><p>{esc(DISCLAIMER)}</p>
<p>掲載内容の誤りや古い情報にお気づきの場合は、公式ページの情報を優先してください。</p>
<h2>広告について</h2><p>当サイトは広告(Google AdSense、アフィリエイトプログラム)を利用する場合があります。広告を含むリンクにはその旨を明記します。</p>"""
    priv = """<h1>プライバシーポリシー</h1>
<p>当サイトは、アクセス解析や広告配信のためにCookie等を利用する場合があります。広告配信事業者(Google等)は、
Cookieを使用して利用者の過去のアクセス情報に基づく広告を配信することがあります。
Cookieはブラウザの設定で無効にできます。個人を特定する情報を当サイトが直接収集することはありません。</p>"""
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
