# api/main.py
import os, json, requests
from pathlib import Path
from typing import List, Dict
from fastapi import FastAPI
from fastapi.responses import Response
from pydantic import BaseModel
from dotenv import load_dotenv

# .env をプロジェクト直下から確実に読む（上書き）
ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env", override=True)

# ---- 設定 ----
PROVIDER = (os.getenv("PROVIDER", "local") or "local").strip().lower()
if PROVIDER != "local":
    raise RuntimeError("This /ask expects PROVIDER=local for now.")

from sentence_transformers import SentenceTransformer
ST = SentenceTransformer(os.getenv("LOCAL_EMBED_MODEL", "intfloat/multilingual-e5-small"))

SEARCH_ENDPOINT = os.environ["AZURE_SEARCH_ENDPOINT"].rstrip("/")
SEARCH_KEY = os.environ["AZURE_SEARCH_ADMIN_KEY"]
INDEX = os.environ["AZURE_SEARCH_INDEX"]
API_VERSION = os.getenv("AZURE_SEARCH_API_VERSION", "2024-07-01")

app = FastAPI()

# ---- 入力モデル（※関数より前に定義）----
class AskIn(BaseModel):
    question: str
    top_k: int = 5

# ---- 検索 ----
def hybrid_search(question: str, top_k: int = 5) -> List[Dict]:
    qvec = ST.encode([question], normalize_embeddings=True)[0].tolist()
    url = f"{SEARCH_ENDPOINT}/indexes('{INDEX}')/docs/search?api-version={API_VERSION}"
    headers = {"Content-Type": "application/json", "api-key": SEARCH_KEY}
    body = {
        "search": question,
        "vectorQueries": [{"kind": "vector", "vector": qvec, "fields": "vector", "k": top_k}],
        "top": top_k,
    }
    r = requests.post(url, headers=headers, data=json.dumps(body), timeout=30)
    r.raise_for_status()
    return r.json().get("value", [])

# ---- エンドポイント ----
@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/ask")
def ask(inp: AskIn):
    hits = hybrid_search(inp.question, inp.top_k)
    if not hits:
        payload = {
            "answer": "関連する規程が見つかりませんでした。キーワードを絞って再検索してください。",
            "citations": [],
        }
        return Response(content=json.dumps(payload, ensure_ascii=False),
                        media_type="application/json; charset=utf-8")

    top = hits[0]
    answer = (top.get("text") or "")[:500]
    citations = [{"source": h.get("source"), "section": h.get("section")} for h in hits[:3]]

    payload = {"answer": answer, "citations": citations}
    return Response(content=json.dumps(payload, ensure_ascii=False),
                    media_type="application/json; charset=utf-8")
