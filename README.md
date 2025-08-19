# work-rules-rag

社内規程を引用つきで答えるRAGデモ（Azure AI Search + Azure OpenAI + FastAPI）

## 進捗と次の一手
- [x] W1–2: FastAPI骨組み + テスト + ツール
- [x] W3: 分割→ `data/processed/chunks.jsonl` 出力
- [ ] W4: インデックス作成（`python ingest/create_index.py`）
- [ ] W4: 埋め込み→Search投入（`python ingest/embed_and_index.py`）
**次の一手**: `.env` を作る（キー名だけ先に用意）