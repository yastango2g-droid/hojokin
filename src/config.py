import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
OUT_DIR = ROOT / "docs"  # GitHub Pages が配信するフォルダ

SITE_NAME = "補助金ウォッチ"
SITE_DESC = "中小企業・個人事業主向けの補助金・助成金の募集情報を毎日自動で更新しています。"
# 独自ドメイン取得後に書き換える(末尾スラッシュなし)。sitemap と canonical に使う
SITE_URL = os.environ.get("SITE_URL", "https://example.github.io/hojokin")

JGRANTS_API = "https://api.jgrants-portal.go.jp/exp/v1/public/subsidies"
# 募集中の案件を広く拾うためのキーワード(APIはキーワード必須)
KEYWORDS = ["補助金", "助成", "支援事業", "事業", "中小企業", "創業", "設備", "IT", "省エネ", "雇用"]

OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

# 1回の実行で新規に要約する上限(API費用の上限管理)
MAX_NEW_SUMMARIES_PER_RUN = int(os.environ.get("MAX_NEW_SUMMARIES", "30"))

# アフィリエイト枠。承認後にリンクを入れる。空なら枠を表示しない
AFFILIATE_LINKS = [
    # {"label": "補助金申請に強い専門家を探す", "url": "https://...", "note": "PR"},
]
ADSENSE_CLIENT = os.environ.get("ADSENSE_CLIENT", "")  # 例: ca-pub-XXXXXXXXXXXXXXXX

# アクセス解析(Cloudflare Web Analytics)。トークンを設定したときだけ計測タグを出す
CF_ANALYTICS_TOKEN = os.environ.get("CF_ANALYTICS_TOKEN", "")
