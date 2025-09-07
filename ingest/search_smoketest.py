import os, sys, json, requests
from pathlib import Path
from dotenv import load_dotenv

# .env をプロジェクト直下から確実に読む
ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env", override=True)

endpoint = os.environ["AZURE_SEARCH_ENDPOINT"].rstrip("/")
index = os.environ["AZURE_SEARCH_INDEX"]
key = os.environ["AZURE_SEARCH_ADMIN_KEY"]
api = os.getenv("AZURE_SEARCH_API_VERSION", "2024-07-01")
provider = (os.getenv("PROVIDER", "local") or "local").strip().lower()

query = "有給 申請 期限" if len(sys.argv) < 2 else " ".join(sys.argv[1:])
topk = 3

def print_hits(title, hits):
    print(f"\n== {title} ==")
    for i, h in enumerate(hits, 1):
        sec = h.get("section")
        src = h.get("source")
        txt = (h.get("text") or "")[:120].replace("\\n", "⏎")
        print(f"{i}. {sec} - {src}\n   {txt}\n---")

def keyword_search(q):
    url = f"{endpoint}/indexes('{index}')/docs/search?api-version={api}"
    headers = {"Content-Type":"application/json","api-key":key}
    body = {"search": q, "top": topk}
    r = requests.post(url, headers=headers, data=json.dumps(body), timeout=30)
    r.raise_for_status()
    return r.json().get("value", [])

def hybrid_search(q):
    # 質問ベクトルを作成（providerごとに切替）
    if provider == "local":
        from sentence_transformers import SentenceTransformer
        model = os.getenv("LOCAL_EMBED_MODEL", "intfloat/multilingual-e5-small")
        st = SentenceTransformer(model)
        vec = st.encode([q], normalize_embeddings=True)[0].tolist()
    elif provider == "openai":
        from openai import OpenAI
        client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        model = os.getenv("OPENAI_EMBED_MODEL","text-embedding-3-small")
        vec = client.embeddings.create(model=model, input=[q]).data[0].embedding
    else:  # azure
        from openai import AzureOpenAI
        client = AzureOpenAI(
            api_key=os.environ["AZURE_OPENAI_API_KEY"],
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21"),
            azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        )
        model = os.environ["AZURE_OPENAI_EMBED_DEPLOYMENT"]
        vec = client.embeddings.create(model=model, input=[q]).data[0].embedding

    url = f"{endpoint}/indexes('{index}')/docs/search?api-version={api}"
    headers = {"Content-Type":"application/json","api-key":key}
    body = {
        "search": q,
        "vectorQueries": [
            {"kind":"vector", "vector": vec, "fields":"vector", "k": topk}
        ],
        "top": topk
    }
    r = requests.post(url, headers=headers, data=json.dumps(body), timeout=30)
    r.raise_for_status()
    return r.json().get("value", [])

if __name__ == "__main__":
    print(f"[query] {query}")
    kw = keyword_search(query)
    print_hits("keyword", kw)
    try:
        hy = hybrid_search(query)
        print_hits("hybrid", hy)
    except Exception as e:
        print(f"[warn] hybrid search failed: {e.__class__.__name__}: {e}")
