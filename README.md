# 補助金ウォッチ

Jグランツ公開APIから募集中の補助金を取得 → OpenAIで短く要約(数字検証あり)→ 静的サイトを `docs/` に生成。

```
python src/run_all.py   # fetch → summarize → build
```

## 公開手順(GitHub Pages)
1. GitHubにリポジトリを作成して push
2. Settings → Pages → Branch: `main` / フォルダ: `/docs`
3. Settings → Secrets → `OPENAI_API_KEY` を登録
4. Settings → Variables → `SITE_URL`(例 `https://<user>.github.io/<repo>`)を登録
5. Actions → daily-update を手動実行して動作確認。以後は毎朝6時に自動更新

## 安全策
- 締切・金額・補助率などはAPIの値をそのまま表示(AIは触らない)
- AI要約は、原文に無い数字を含む場合と断定語を含む場合は破棄
- 全ページに公式リンク・最終確認日・免責を表示
- 要約の新規生成は1回あたり `MAX_NEW_SUMMARIES`(既定30件)まで = API費用の上限
