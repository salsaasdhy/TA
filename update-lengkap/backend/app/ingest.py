"""Ingest ulang knowledge base: python -m app.ingest"""
from . import rag

if __name__ == "__main__":
    print(f"{rag.ingest_knowledge(force=True)} chunk di-ingest")
