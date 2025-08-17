from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class AskReq(BaseModel):
    question: str

class AskRes(BaseModel):
    answer: str
    citations: list[dict]  # [{"doc":"work_rules.pdf","section":"第36条"}]

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/ask", response_model=AskRes)
def ask(req: AskReq):
    # まだモック（仮実装）
    return AskRes(
        answer="（ここに回答が入ります。後でRAGに差し替え）",
        citations=[{"doc": "work_rules.pdf", "section": "第1章"}],
    )
