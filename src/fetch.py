"""Jグランツ公開APIから募集中の補助金を取得し、data/subsidies.json に保存する。"""
import json
import time
import urllib.parse
import urllib.request

from config import DATA_DIR, JGRANTS_API, KEYWORDS

UA = {"User-Agent": "hojokin-watch/1.0"}


def get_json(url, retries=3):
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except Exception as e:
            if i == retries - 1:
                raise
            print(f"retry {url}: {e}")
            time.sleep(3 * (i + 1))


ATTACHMENT_FIELDS = ("application_guidelines", "outline_of_grant", "application_form")


def strip_attachments(detail):
    """添付ファイル(base64の巨大データ)は使わないので保存しない。"""
    for k in ATTACHMENT_FIELDS:
        detail.pop(k, None)
    return detail


def list_ids():
    ids = {}
    for kw in KEYWORDS:
        q = urllib.parse.urlencode(
            {"keyword": kw, "sort": "acceptance_end_datetime", "order": "ASC", "acceptance": 1}
        )
        for item in get_json(f"{JGRANTS_API}?{q}")["result"]:
            ids[item["id"]] = item
        time.sleep(0.5)
    return ids


def main():
    DATA_DIR.mkdir(exist_ok=True)
    path = DATA_DIR / "subsidies.json"
    old = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    for v in old.values():
        strip_attachments(v)

    ids = list_ids()
    print(f"募集中: {len(ids)} 件")
    result = {}
    for sid in ids:
        # 詳細は毎回取り直す(締切や内容の変更に追随するため)
        try:
            detail = strip_attachments(get_json(f"{JGRANTS_API}/id/{sid}")["result"][0])
        except Exception as e:
            print(f"skip {sid}: {e}")
            if sid in old:
                result[sid] = old[sid]
            continue
        # 要約は再利用する
        if sid in old and "summary" in old[sid]:
            detail["summary"] = old[sid]["summary"]
            detail["summary_src_hash"] = old[sid].get("summary_src_hash")
        result[sid] = detail
        time.sleep(0.3)

    path.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"保存: {path} ({len(result)} 件)")


if __name__ == "__main__":
    main()
