# work-rules-rag

社内規程を引用つきで答えるRAGデモ（Azure AI Search + Azure OpenAI + FastAPI）

## 進捗と次の一手
- [x] W1–2: FastAPI骨組み + テスト + ツール
- [x] W3: 分割→ `data/processed/chunks.jsonl` 出力
- [ ] W4: インデックス作成（`python ingest/create_index.py`）
- [ ] W4: 埋め込み→Search投入（`python ingest/embed_and_index.py`）
**次の一手**: `.env` を作る（キー名だけ先に用意）

# Prompt policy (draft)
- 必ず回答の最後に「根拠: <source> の <section>」を付ける
- 不確実なら「わからない」と返す（推測しない）
- 日本語の敬体、簡潔な2–3文
- 箇条書きは最大3点

# Error/fallback messages
- 参照が見つからない: 「関連する規程が見つかりませんでした。◯◯や◯◯の語で再検索してください。」
- 質問が長すぎ: 「質問を1点に絞って再入力してください。（例: 有給の申請期限）」
- システム障害: 「現在、検索システムが一時停止しています。時間をおいて再試行してください。」