"""一覧・詳細・今月締切ページのHTML生成。共通部品は build.py 側(page, fmt_*, area_of など)。"""
from datetime import datetime, timedelta, timezone
import html

from config import SITE_DESC, SITE_NAME, SITE_URL

JST = timezone(timedelta(hours=9))
esc = html.escape


def make_views(page, fmt_dt, fmt_yen, area_of, jst, affiliate_block, DISCLAIMER, now):
    """build.py から共通部品を受け取り、各ページ生成関数を返す(循環importを避けるため)。"""
    today = now.strftime("%Y年%m月%d日")

    def val(text, missing=False):
        """値があれば通常表示、無ければ薄いグレーで「記載なし」と区別する。"""
        if missing or not text:
            return '<b class="na">記載なし<small>詳細は公式ページで確認</small></b>'
        return f"<b>{esc(str(text))}</b>"

    def days_left(end):
        return max(0, (end.date() - now.date()).days) if end else None

    def days_tag(days):
        if days is None:
            return ""
        if days == 0:
            return '<span class="tag urg">本日締切</span>'
        if days <= 7:
            return f'<span class="tag urg">あと{days}日</span>'
        if days <= 14:
            return f'<span class="tag soon">あと{days}日</span>'
        return ""

    def build_detail(d, end):
        sid = d["id"]
        area = area_of(d)
        title = d["title"]
        summary = d.get("summary")
        days = days_left(end)
        rows = [
            ("申請受付期間", f'{fmt_dt(jst(d.get("acceptance_start_datetime")))} 〜 {fmt_dt(end)}'),
            ("対象地域", area),
            ("従業員数", d.get("target_number_of_employees") or "公式ページで確認"),
            ("利用目的", d.get("use_purpose") or "公式ページで確認"),
            ("実施機関", d.get("institution_name") or "公式ページで確認"),
        ]
        tbl = "".join(f"<tr><th>{k}</th><td>{esc(str(v))}</td></tr>" for k, v in rows)
        url = d.get("front_subsidy_detail_page_url") or f"https://www.jgrants-portal.go.jp/subsidy/{sid}"
        catch = d.get("subsidy_catch_phrase")
        urg = " urg" if days is not None and days <= 7 else ""
        left = f"(あと{days}日)" if days is not None else ""
        facts = f"""<div class="facts">
<div class="fact hi"><span>補助上限額</span>{val(fmt_yen(d.get("subsidy_max_limit")), not d.get("subsidy_max_limit"))}</div>
<div class="fact"><span>補助率</span>{val(d.get("subsidy_rate"))}</div>
<div class="fact{urg}"><span>申請締切</span><b>{fmt_dt(end)}{left}</b></div>
<div class="fact"><span>対象地域</span><b>{esc(area)}</b></div></div>"""
        ai = (f'<div class="ai"><b>概要(AIによる要約)</b><p>{esc(summary)}</p>'
              f'<p class="meta">公募要領をもとにAIが要約したものです。詳細は必ず公式ページをご確認ください。</p></div>'
              if summary else "")
        body = f"""<p class="crumb"><a href="{SITE_URL}/">補助金一覧</a> › {esc(area)}</p>
<h1 class="t">{esc(title)}</h1>
<div class="badges">{days_tag(days)}<span class="tag">{esc(area)}</span></div>
{f'<p>{esc(catch)}</p>' if catch else ''}
{facts}
<div class="cta"><a class="btn" href="{esc(url)}" rel="noopener">公式ページで詳細・申請方法を見る</a>
<a class="btn sub" href="{SITE_URL}/">他の補助金を探す</a></div>
{ai}
<div class="box"><h2>募集情報</h2><table>{tbl}</table></div>
<div class="note">情報の最終確認日: {today}(Jグランツのデータを自動取得)。{esc(DISCLAIMER)}</div>
{affiliate_block()}
<div class="sticky"><a class="btn" href="{esc(url)}" rel="noopener">公式ページで詳細を見る</a></div>"""
        return page(f"{title}|{SITE_NAME}", body, f"s/{sid}.html",
                    desc=f"{area}|上限{fmt_yen(d.get('subsidy_max_limit'))}|締切{fmt_dt(end)}。{catch or title}")

    def card_html(d, end, idx=0):
        area = area_of(d)
        days = days_left(end)
        rate = d.get("subsidy_rate") or ""
        rate = rate if len(rate) <= 22 else rate[:21] + "…"
        hay = " ".join(filter(None, [d["title"], d.get("subsidy_catch_phrase"), d.get("use_purpose"), area])).lower()
        kv = (f'<div class="amt">上限額{val(fmt_yen(d.get("subsidy_max_limit")), not d.get("subsidy_max_limit"))}</div>'
              f'<div>補助率{val(rate)}</div>'
              f'<div>締切<b>{fmt_dt(end)}</b></div>')
        return (
            f'<a class="card" data-t="{esc(hay)}" data-area="{esc(area)}" '
            f'data-days="{days if days is not None else 9999}" data-max="{int(d.get("subsidy_max_limit") or 0)}" '
            f'data-i="{idx}" href="{SITE_URL}/s/{d["id"]}.html">'
            f'<div class="badges">{days_tag(days)}<span class="tag">{esc(area)}</span></div>'
            f'<h3>{esc(d["title"])}</h3><div class="kv">{kv}</div></a>'
        )

    def build_deadline(items):
        month_items = [(d, e) for d, e in items if e and (e.year, e.month) == (now.year, now.month)]
        label = f"{now.year}年{now.month}月"
        if month_items:
            listing = '<div class="list">' + "".join(
                card_html(d, e, i) for i, (d, e) in enumerate(month_items)) + "</div>"
        else:
            listing = '<p class="empty">今月締切の案件は現在ありません。</p>'
        body = f"""<p class="crumb"><a href="{SITE_URL}/">補助金一覧</a> › 今月締切</p>
<h1 class="t">{label}に締切を迎える補助金・助成金</h1>
<p>{label}中に申請受付が終了する、募集中の補助金・助成金です(締切が近い順、<b>{len(month_items)}件</b>)。
締切間際は変更・早期終了もあるため、必ず公式ページで最新情報をご確認ください。</p>
{listing}<p style="margin-top:24px"><a href="{SITE_URL}/">← 募集中の補助金一覧へ</a></p>"""
        return page(f"{label}締切の補助金・助成金一覧|{SITE_NAME}", body, "deadline.html",
                    desc=f"{label}に申請締切を迎える補助金・助成金の一覧。中小企業・個人事業主向けの募集中案件を締切順に掲載。")

    def build_topic(path, h1, intro, items, crumb_label, desc):
        """目的別・地域別の一覧ページ(静的に全件を並べる)。"""
        listing = '<div class="list">' + "".join(card_html(d, e, i) for i, (d, e) in enumerate(items)) + "</div>"
        body = f"""<p class="crumb"><a href="{SITE_URL}/">補助金一覧</a> › {esc(crumb_label)}</p>
<h1 class="t">{esc(h1)}</h1><p>{esc(intro)}</p>
<p class="count"><b>{len(items)}</b> 件(締切が近い順・{today}時点)</p>{listing}
<p style="margin-top:24px"><a href="{SITE_URL}/">← 募集中の補助金一覧へ</a> / <a href="{SITE_URL}/guide.html">補助金の探し方・申請の流れ</a></p>"""
        return page(f"{h1}|{SITE_NAME}", body, path, desc=desc)

    def build_index(items, topic_links=""):
        areas = sorted({area_of(d) for d, _ in items}, key=lambda a: (a != "全国", a))
        opts = "".join(f'<option value="{esc(a)}">{esc(a)}</option>' for a in areas)
        cards = "".join(card_html(d, end, i) for i, (d, end) in enumerate(items))
        month_n = sum(1 for _, e in items if e and (e.year, e.month) == (now.year, now.month))
        soon_n = sum(1 for _, e in items if e and days_left(e) <= 14)
        hero = f"""<section class="hero"><div class="w">
<h1>あなたの事業に使える補助金を、<br>かんたんに探せます</h1>
<p>{esc(SITE_DESC)}</p>
<div class="stats"><div class="stat"><b>{len(items)}</b><span>募集中の補助金</span></div>
<div class="stat"><b>{soon_n}</b><span>14日以内に締切</span></div>
<div class="stat"><b>{month_n}</b><span>今月締切</span></div>
<div class="stat"><b>{now.month}/{now.day}</b><span>最終更新</span></div></div></div></section>"""
        body = f"""<section class="panel" aria-label="補助金を探す">
<div class="row"><div class="fld"><input id="q" type="search" placeholder="キーワードで探す(例: IT導入、創業、省エネ)" aria-label="キーワード"></div>
<div class="fld" style="flex-basis:150px"><select id="area" aria-label="地域"><option value="">すべての地域</option>{opts}</select></div>
<div class="fld" style="flex-basis:150px"><select id="sort" aria-label="並び順"><option value="deadline">締切が近い順</option><option value="amount">上限額が大きい順</option></select></div></div>
<div class="chips"><button class="chip" data-c="soon" aria-pressed="false">締切14日以内</button>
<button class="chip" data-c="big" aria-pressed="false">上限1,000万円以上</button>
<button class="chip" id="reset" type="button">条件をリセット</button>
<a class="chip" style="text-decoration:none" href="{SITE_URL}/deadline.html">今月締切の一覧 →</a></div></section>
<p class="count"><b id="n">{len(items)}</b> 件の補助金が見つかりました</p>
<div class="list" id="list">{cards}</div>
<p class="empty" id="empty" hidden>条件に合う補助金は見つかりませんでした。<br>キーワードを短くするか、地域を「すべての地域」にして、もう一度お試しください。<br><button class="chip" type="button" onclick="document.getElementById('reset').click()">条件をリセットする</button></p>{topic_links}{INDEX_JS}"""
        return page(f"募集中の補助金・助成金一覧|{SITE_NAME}", body, "", hero=hero)

    return build_detail, build_deadline, build_index, build_topic


INDEX_JS = """<script>
(()=>{const q=document.getElementById('q'),ar=document.getElementById('area'),so=document.getElementById('sort'),
n=document.getElementById('n'),em=document.getElementById('empty'),list=document.getElementById('list'),
cards=[...list.children],chips={soon:false,big:false};
let run;function _r(){const k=q.value.trim().toLowerCase().split(/\\s+/).filter(Boolean);let c=0;
cards.forEach(e=>{const ok=k.every(w=>e.dataset.t.includes(w))&&(!ar.value||e.dataset.area===ar.value)
&&(!chips.soon||+e.dataset.days<=14)&&(!chips.big||+e.dataset.max>=10000000);e.hidden=!ok;c+=ok});
n.textContent=c;em.hidden=c>0;
[...cards].sort((a,b)=>so.value==='amount'?(+b.dataset.max-+a.dataset.max)||(+a.dataset.i-+b.dataset.i):(+a.dataset.i-+b.dataset.i)).forEach(e=>list.appendChild(e))}
const KEY='hojokin_filters';
function save(){try{sessionStorage.setItem(KEY,JSON.stringify({q:q.value,a:ar.value,s:so.value,c:chips}))}catch(e){}}
function load(){try{const j=JSON.parse(sessionStorage.getItem(KEY)||'null');if(!j)return;q.value=j.q||'';ar.value=j.a||'';so.value=j.s||'deadline';
Object.assign(chips,j.c||{});document.querySelectorAll('.chip[data-c]').forEach(b=>b.setAttribute('aria-pressed',!!chips[b.dataset.c]))}catch(e){}}
run=function(){_r();save()};
q.oninput=ar.onchange=so.onchange=()=>run();
document.querySelectorAll('.chip[data-c]').forEach(b=>b.onclick=()=>{const c=b.dataset.c;chips[c]=!chips[c];b.setAttribute('aria-pressed',chips[c]);run()});
load();run();
document.getElementById('reset').onclick=()=>{q.value='';ar.value='';so.value='deadline';chips.soon=chips.big=false;
document.querySelectorAll('.chip[data-c]').forEach(b=>b.setAttribute('aria-pressed',false));run()};})();
</script>"""
