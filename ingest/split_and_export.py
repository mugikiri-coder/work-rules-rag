# ingest/split_and_export.py
import re, sys, uuid
from pathlib import Path
from typing import List, Dict
import jsonlines
from tqdm import tqdm

# ---------- 読み取り ----------
def read_pdf(path: Path) -> str:
    from pypdf import PdfReader
    texts = []
    for p in PdfReader(str(path)).pages:
        texts.append(p.extract_text() or "")
    return "\n".join(texts)

def read_docx(path: Path) -> str:
    from docx import Document
    d = Document(str(path))
    return "\n".join([p.text for p in d.paragraphs])

def read_txt(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")

def load_text(path: Path) -> str:
    ext = path.suffix.lower()
    if ext == ".pdf":  return read_pdf(path)
    if ext == ".docx": return read_docx(path)
    return read_txt(path)

def normalize(s: str) -> str:
    s = s.replace("\t", " ").replace("\u3000", " ")
    s = re.sub(r"[ ]{2,}", " ", s)
    s = re.sub(r"\n{3,}", "\n\n", s).strip()
    return s

# ---------- 分割 ----------
# 「第十条」「第10条」「付則」などに反応
KANJI_NUM = "一二三四五六七八九十百千"
SEC_RE = re.compile(rf"(第[{KANJI_NUM}\d]+章|第\s*[\d{KANJI_NUM}]+\s*条|付則)", re.MULTILINE)

def split_by_headings(text: str) -> List[Dict]:
    parts = []
    anchors = [m.start() for m in SEC_RE.finditer(text)]
    if not anchors:
        return parts
    anchors.append(len(text))
    for i in range(len(anchors) - 1):
        chunk = text[anchors[i]:anchors[i + 1]].strip()
        if not chunk:
            continue
        m = SEC_RE.search(chunk)
        section = m.group(0) if m else f"sec-{i+1}"
        parts.append({"section": section, "text": chunk})
    return parts

def window_chunks(text: str, size=900, overlap=160) -> List[str]:
    text = text.strip()
    if len(text) <= size:
        return [text] if text else []
    out, start = [], 0
    while start < len(text):
        end = min(start + size, len(text))
        out.append(text[start:end].strip())
        if end >= len(text): break
        start = max(0, end - overlap)
    return out

def chunk_text(full: str) -> List[Dict]:
    parts = split_by_headings(full)
    out: List[Dict] = []
    if parts:
        for p in parts:
            for c in window_chunks(p["text"]):
                out.append({"section": p["section"], "text": c})
    else:
        for c in window_chunks(full):
            out.append({"section": "chunk", "text": c})
    return out

# ---------- 実行 ----------
def main(raw_dir: Path, out_path: Path):
    raw_dir = raw_dir if raw_dir else Path("data/raw")
    out_path = out_path if out_path else Path("data/processed/chunks.jsonl")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    files = [p for p in sorted(raw_dir.glob("*")) if p.suffix.lower() in {".pdf",".docx",".txt"}]
    if not files:
        print(f"[warn] no input files under {raw_dir}. put PDF/DOCX/TXT there.")
        return

    count = 0
    with jsonlines.open(out_path, mode="w") as w:
        for fp in tqdm(files, desc="chunking"):
            try:
                txt = normalize(load_text(fp))
                for piece in chunk_text(txt):
                    w.write({
                        "id": str(uuid.uuid4()),
                        "text": piece["text"],
                        "section": piece["section"],
                        "source": fp.name,
                    })
                    count += 1
            except Exception as e:
                print(f"[skip] {fp.name}: {e}")
    print(f"done -> {out_path}  ({count} chunks)")

if __name__ == "__main__":
    raw = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data/raw")
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("data/processed/chunks.jsonl")
    main(raw, out)
