"""RAG: LangChain + PGVector (PostgreSQL) + OpenRouter (Qwen)."""
import logging
import re
import threading
from functools import lru_cache
from pathlib import Path

from langchain_core.documents import Document
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_postgres import PGVector
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sqlalchemy import create_engine, select, text

from .config import settings
from .database import SessionLocal
from .models import RujukanPsikolog, User

log = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "Kamu AI Habit Coach, asisten kebiasaan belajar untuk mahasiswa. Gunakan bahasa Indonesia "
    "yang santai tapi sopan, ringkas (maksimal sekitar 120 kata), dan beri langkah kecil yang bisa langsung dicoba. "
    "Dasarkan saran pada KONTEKS yang diberikan. Jika konteks tidak memuat jawabannya, katakan terus terang "
    "dan beri saran umum yang aman tanpa mengarang kutipan atau data. "
    "Sumber yang berawalan 'Psikolog' adalah panduan praktis dari psikolog kampus: bila relevan, sampaikan sebagai saran psikolog "
    "dan jadikan jurnal sebagai dasar ilmiahnya. Kamu bukan pengganti psikolog; untuk keluhan emosional yang berat, "
    "sarankan mahasiswa menemui psikolog kampus."
)


@lru_cache
def _llm() -> ChatOpenAI:
    return ChatOpenAI(model=settings.llm_model, api_key=settings.openrouter_api_key,
                      base_url=settings.openrouter_base_url, temperature=0.4, timeout=60)


@lru_cache
def _store() -> PGVector:
    emb = OpenAIEmbeddings(model=settings.embedding_model, api_key=settings.openrouter_api_key,
                           base_url=settings.openrouter_base_url, check_embedding_ctx_length=False)
    return PGVector(embeddings=emb, collection_name=settings.collection_name,
                    connection=settings.database_url, use_jsonb=True)


def _sumber(penulis: str | None, tahun: int | None, judul: str) -> str:
    kepala = (penulis or "").strip()
    if tahun:
        kepala = f"{kepala} ({tahun})".strip()
    ref = f"{kepala}, {judul}" if kepala else judul
    return ref if len(ref) <= 240 else ref[:237] + "..."


def _jurnal_documents() -> list[Document]:
    """Baca tabel `jurnal` (hanya SELECT, tabel tidak diubah)."""
    eng = create_engine(settings.jurnal_database_url)
    try:
        with eng.connect() as conn:
            rows = conn.execute(text(
                "SELECT id, judul, penulis, tahun, kategori, abstrak FROM jurnal ORDER BY id"
            )).mappings().all()
    finally:
        eng.dispose()
    docs = []
    for r in rows:
        isi = (r["abstrak"] or "").strip()
        docs.append(Document(
            page_content=f"{r['judul']}\n{isi}" if isi else r["judul"],
            metadata={"judul": r["judul"], "sumber": _sumber(r["penulis"], r["tahun"], r["judul"]),
                      "kategori": r["kategori"] or "", "jurnal_id": r["id"]}))
    return docs


def _psikolog_documents() -> list[Document]:
    """Panduan dari psikolog (tabel rujukan_psikolog di database aplikasi)."""
    try:
        with SessionLocal() as db:
            rows = db.execute(select(RujukanPsikolog, User.name)
                              .join(User, User.id == RujukanPsikolog.psikolog_id)
                              .where(RujukanPsikolog.aktif.is_(True))).all()
    except Exception as e:
        log.warning("Panduan psikolog tidak terbaca: %s", e)
        return []
    docs = []
    for r, nama in rows:
        sumber = f"Psikolog {nama}: {r.judul}"
        docs.append(Document(page_content=f"{r.judul}\n{r.isi}",
                             metadata={"judul": r.judul, "sumber": sumber[:240], "jenis": "psikolog",
                                       "kategori": r.kategori or "", "rujukan_id": r.id}))
    return docs


def _builtin_documents() -> list[Document]:
    """Format file .md: baris 1 '# Judul', baris 2 'Sumber: ...', sisanya isi."""
    docs = []
    for path in sorted(Path(settings.knowledge_dir).glob("*.md")):
        lines = path.read_text(encoding="utf-8").strip().splitlines()
        title = lines[0].lstrip("# ").strip()
        source = lines[1].removeprefix("Sumber:").strip()
        docs.append(Document(page_content=f"{title}\n" + "\n".join(lines[2:]).strip(),
                             metadata={"judul": title, "sumber": source, "file": path.name}))
    return docs


def _load_documents() -> list[Document]:
    docs: list[Document] = []
    if settings.jurnal_database_url:
        docs += _jurnal_documents()
        log.info("Memuat %s jurnal dari tabel jurnal", len(docs))
    docs += _psikolog_documents()
    if settings.use_builtin_knowledge or not docs:
        docs += _builtin_documents()
    return RecursiveCharacterTextSplitter(chunk_size=900, chunk_overlap=100).split_documents(docs)


def ingest_knowledge(force: bool = False) -> int:
    store = _store()
    if not force and store.similarity_search("belajar", k=1):
        return 0
    if force:
        store.delete_collection()
        store.create_collection()
    chunks = _load_documents()
    if chunks:
        store.add_documents(chunks)
    return len(chunks)


def _retrieve(query: str, k: int = 4) -> list[Document]:
    return _store().similarity_search(query, k=k)


def _context(docs: list[Document]) -> str:
    """Konteks bernomor: model diminta menyebut nomor sumber yang benar-benar dipakai."""
    return "\n\n".join(f"[{i}] ({d.metadata['sumber']})\n{d.page_content}" for i, d in enumerate(docs, 1))


_SUMBER_RE = re.compile(r"^[\s\*\[\(]*SUMBER\s*[:\-]?\s*\[?(\d+)\]?[\s\*\)]*\n?", re.IGNORECASE)
ATURAN_SUMBER = ("Baris pertama jawabanmu WAJIB berbentuk 'SUMBER: <nomor>', yaitu nomor konteks yang benar-benar kamu pakai, "
                 "atau 'SUMBER: 0' jika tidak ada konteks yang relevan. Tulis jawabannya mulai baris kedua.")


def pisah_sumber(teks: str, docs: list[Document]) -> tuple[str, str | None]:
    """Pisahkan baris 'SUMBER: n' dari jawaban model. n = 0, tidak valid, atau format tak dikenal -> tanpa rujukan."""
    m = _SUMBER_RE.match(teks)
    if not m:
        return teks.strip(), None
    n = int(m.group(1))
    sumber = docs[n - 1].metadata["sumber"] if 1 <= n <= len(docs) else None
    return teks[m.end():].strip(), sumber


def explain(query: str, title: str, base_body: str, summary: str) -> tuple[str, str | None]:
    docs = _retrieve(query, k=4)
    if not docs:
        return base_body, None
    msg = (f"Profil mahasiswa: {summary}\nTemuan: {title}\nKonteks:\n{_context(docs)}\n\n{ATURAN_SUMBER} "
           "Jawabannya 2 kalimat (maksimal 45 kata) yang menjelaskan temuan ini kepada mahasiswa berdasarkan konteks tersebut. "
           "Jangan menambah fakta di luar konteks.")
    out = _llm().invoke([SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=msg)])
    body, sumber = pisah_sumber(str(out.content), docs)
    if sumber is None:  # tidak ada jurnal yang relevan: pakai teks bawaan, tanpa rujukan
        return base_body, None
    return body or base_body, sumber


def answer(question: str, history: list[tuple[str, str]], summary: str) -> tuple[str, str | None]:
    docs = _retrieve(question, k=4)
    system = (f"{SYSTEM_PROMPT}\n\nProfil mahasiswa: {summary}\n\nKONTEKS:\n{_context(docs) if docs else '(kosong)'}\n\n{ATURAN_SUMBER}")
    msgs = [SystemMessage(content=system)]
    for role, content in history[-8:]:
        msgs.append(HumanMessage(content=content) if role == "user" else AIMessage(content=content))
    msgs.append(HumanMessage(content=question))
    out = _llm().invoke(msgs)
    return pisah_sumber(str(out.content), docs)


_reindex_lock = threading.Lock()


def reindex_async() -> None:
    """Bangun ulang pencarian vektor di latar belakang (dipanggil setelah psikolog mengubah panduan)."""
    if not settings.openrouter_api_key:
        log.warning("OPENROUTER_API_KEY kosong: panduan psikolog tersimpan tapi belum masuk pencarian.")
        return

    def _run():
        with _reindex_lock:
            try:
                log.warning("Pencarian vektor diperbarui: %s chunk", ingest_knowledge(force=True))
            except Exception:
                log.exception("Gagal memperbarui pencarian vektor")

    threading.Thread(target=_run, daemon=True).start()

