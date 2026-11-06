"""公募要領の本文をAIで短く要約する。原文に無い数字が混ざった要約は破棄する(誤情報対策)。"""
import hashlib
import html
import json
import re
import unicodedata
import urllib.request

from config import DATA_DIR, MAX_NEW_SUMMARIES_PER_RUN, OPENAI_API_KEY, OPENAI_MODEL

PROMPT = """あなたは補助金情報の抜き出し担当です。次の公募情報の本文だけを根拠に、
「どんな事業に使える補助金か」を日本語で100〜150字にまとめてください。
ルール:
- 本文に書かれている内容のみを使う。推測・補足・評価は禁止。
- 金額・日付・割合などの数字は、本文にあるものだけを書く。迷うなら数字は書かない。
- 「必ず」「確実に」「おすすめ」など断定・勧誘の表現は禁止。
- 出力は要約文のみ。"""


def html_to_text(s):
    s = re.sub(r"<(script|style).*?</\1>", " ", s or "", flags=re.S)
    s = re.sub(r"<br\s*/?>|</p>|</li>|</tr>", "\n", s)
    s = re.sub(r"<[^>]+>", " ", s)
    s = html.unescape(s)
    return re.sub(r"[ \t　]+", " ", s).strip()


def source_text(d):
    parts = [d.get("subsidy_catch_phrase") or "", html_to_text(d.get("detail"))]
    return "\n".join(p for p in parts if p)[:6000]


def norm_digits(s):
    return unicodedata.normalize("NFKC", s).replace(",", "")


def numbers_ok(summary, source):
    """要約中の数字がすべて原文に存在するか。"""
    src = norm_digits(source)
    return all(n in src for n in re.findall(r"\d+(?:\.\d+)?", norm_digits(summary)))


NG_WORDS = ["必ず", "確実", "おすすめ", "絶対", "誰でも"]
# AIの断り文・質問返しを公開しないための語句
REFUSAL_WORDS = ["情報が不足", "提供して", "まとめることができません", "要約できません", "お知らせください", "申し訳"]


def summary_ok(summary, source):
    return (
        40 <= len(summary) <= 300
        and numbers_ok(summary, source)
        and not any(w in summary for w in NG_WORDS + REFUSAL_WORDS)
    )


def call_openai(text):
    body = json.dumps(
        {
            "model": OPENAI_MODEL,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": PROMPT},
                {"role": "user", "content": text},
            ],
        }
    ).encode()
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=body,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {OPENAI_API_KEY}"},
    )
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.load(r)["choices"][0]["message"]["content"].strip()


def main():
    path = DATA_DIR / "subsidies.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    if not OPENAI_API_KEY:
        print("OPENAI_API_KEY 未設定のため要約をスキップ(事実項目のみでサイトを作ります)")
        return

    # 既存の要約も今の基準で再検証(基準強化前に保存されたものを除去)
    for sid, d in data.items():
        if d.get("summary") and not summary_ok(d["summary"], source_text(d)):
            d.pop("summary")
            d.pop("summary_src_hash", None)  # 再要約の対象に戻す

    done = rejected = 0
    # 締切が近い案件から優先して要約する
    for sid, d in sorted(data.items(), key=lambda kv: kv[1].get("acceptance_end_datetime") or "9999"):
        src = source_text(d)
        h = hashlib.sha1(src.encode()).hexdigest()
        if d.get("summary_src_hash") == h:
            continue  # 原文が変わっていなければ再要約しない
        if len(src) < 60:
            continue
        if done >= MAX_NEW_SUMMARIES_PER_RUN:
            break
        try:
            s = call_openai(src)
        except Exception as e:
            print(f"要約失敗 {sid}: {e}")
            continue
        done += 1
        d["summary_src_hash"] = h
        if summary_ok(s, src):
            d["summary"] = s
        else:
            d.pop("summary", None)
            rejected += 1
            print(f"検証NGで破棄: {sid}")

    path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"要約 {done} 件 (検証NG {rejected} 件)")


if __name__ == "__main__":
    main()
