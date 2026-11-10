import asyncio
import logging
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from . import jadwal, rag
from .config import settings
from .database import Base, SessionLocal, engine
from .routers import auth, coach, pantau, pengingat
from .seed import seed_demo_user, seed_questions

log = logging.getLogger("habitcoach")


@asynccontextmanager
async def lifespan(_: FastAPI):
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        seed_questions(db)
        seed_demo_user(db)
    if settings.openrouter_api_key:
        def _ingest():  # di latar belakang supaya server cepat siap
            try:
                n = rag.ingest_knowledge()
                log.warning("Knowledge base: %s chunk baru di-ingest", n)
            except Exception as e:
                log.warning("Ingest knowledge base gagal: %s", e)
        threading.Thread(target=_ingest, daemon=True).start()
    tugas = asyncio.create_task(jadwal.loop_pengingat()) if jadwal.push_aktif() else None
    if tugas is None:
        log.warning("Pengingat belajar nonaktif: VAPID_PUBLIC_KEY / VAPID_PRIVATE_KEY belum diisi di .env")
    yield
    if tugas:
        tugas.cancel()


app = FastAPI(title="Habit Coach API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)
app.include_router(auth.router)
app.include_router(coach.router)
app.include_router(pengingat.router)
app.include_router(pantau.router)


@app.get("/health")
def health():
    return {"status": "ok"}
