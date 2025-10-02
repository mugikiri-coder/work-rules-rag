# api/main.py
from pathlib import Path  # まだ無ければ追加
ROOT = Path(__file__).resolve().parents[1]  # リポジトリのルート
import os, json, requests
from pathlib import Path
from typing import List, Dict
from fastapi import FastAPI
from fastapi.responses import Response
from pydantic import BaseModel
from dotenv import load_dotenv
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
import logging
from logging.handlers import RotatingFileHandler

# FastAPI 初期化のすぐ下に、簡易ロガー設定を追加
app = FastAPI()

LOG_DIR = ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)
# ハンドラ & フォーマッタ
handler = RotatingFileHandler(LOG_DIR / "app.log", maxBytes=512_000, backupCount=2, encoding="utf-8")
formatter = logging.Formatter("%(asctime)s\t%(levelname)s\t%(name)s\t%(message)s")
handler.setFormatter(formatter)

# 重要：既存設定を強制リセット（Uvicornの設定も含めて）
logging.basicConfig(level=logging.INFO, handlers=[handler], force=True)

# アプリ用ロガー
logger = logging.getLogger("app")
logger.setLevel(logging.INFO)
logger.propagate = True

logger.info("startup: app logger configured")  # 起動確認ログ

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
    logger.info(f"ASK received: q={inp.question!r}, top_k={inp.top_k}")
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

@app.post("/ask")
def ask(inp: AskIn):
    logger.info(f"ASK received: q={inp.question!r}, top_k={inp.top_k}")
    try:
        hits = hybrid_search(inp.question, inp.top_k)
        # 上位ヒットの概要をログ
        summary = [{"source": h.get("source"), "section": h.get("section")} for h in hits[:3]]
        logger.info(f"ASK\tq={inp.question}\tK={inp.top_k}\thits={summary}")

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

    except Exception as e:
        # 失敗時も原因をログ
        logger.exception(f"ASK_ERROR\tq={getattr(inp,'question',None)}\terr={e}")
        payload = {"answer": "内部エラーが発生しました。時間をおいて再試行してください。", "citations": []}
        return Response(content=json.dumps(payload, ensure_ascii=False),
                        media_type="application/json; charset=utf-8", status_code=500)