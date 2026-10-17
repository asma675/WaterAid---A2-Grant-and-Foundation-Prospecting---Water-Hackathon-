#!/usr/bin/env python3
"""Export GrantCurrent's auditable RAG corpus as JSONL.

Run from the repository root:
  PYTHONPATH=backend python backend/scripts/build_rag_corpus.py
"""
from __future__ import annotations
import json
from pathlib import Path
from app.rag import corpus

out=Path("challenge_pack/data/rag_corpus.jsonl")
with out.open("w",encoding="utf-8") as fh:
    for d in corpus():
        fh.write(json.dumps({"id":d.id,"title":d.title,"kind":d.kind,"url":d.url,"text":d.text,"metadata":d.metadata},ensure_ascii=False)+"\n")
print(f"Wrote {sum(1 for _ in out.open(encoding='utf-8'))} documents to {out}")
