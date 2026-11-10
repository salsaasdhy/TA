"""Membaca pertanyaan dari tabel `pertanyaan` + `opsi_jawaban` menjadi bentuk yang dipakai analisis dan API."""
import logging
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .analysis import FLAG_LABELS
from .models import Pertanyaan

log = logging.getLogger(__name__)
TIPE = {"pilihan": "choice", "angka": "number", "teks": "text", "skala": "scale"}


@dataclass
class Soal:
    id: int
    order: int  # nomor tampil (1, 2, 3, ...) setelah pertanyaan nonaktif dilewati
    category: str
    text: str
    qtype: str
    required: bool
    config: dict = field(default_factory=dict)
    options: list = field(default_factory=list)


def _tags(o) -> dict:
    tags = {}
    for k, v in (("v", o.skor_visual), ("a", o.skor_auditori), ("k", o.skor_kinestetik)):
        if v:
            tags[k] = v
    if o.skor_konsistensi is not None:
        tags["c"] = o.skor_konsistensi
    flag = (o.penanda or "").strip()
    if flag:
        if flag in FLAG_LABELS:
            tags["f"] = flag
        else:
            log.warning("Penanda '%s' tidak dikenal dan diabaikan. Pilihan: %s", flag, ", ".join(FLAG_LABELS))
    return tags


def cocok_semester(p, semester: int | None) -> bool:
    """Pertanyaan tampil bila semester mahasiswa berada dalam rentang min_semester..maks_semester.
    Semester belum diketahui (akun lama) = semua pertanyaan tampil."""
    if semester is None:
        return True
    if p.min_semester is not None and semester < p.min_semester:
        return False
    return p.maks_semester is None or semester <= p.maks_semester


def soal_dari_pertanyaan(p, nomor: int) -> Soal | None:
    qtype = TIPE.get((p.tipe or "").strip().lower())
    if not qtype:
        log.warning("Pertanyaan id=%s dilewati: tipe '%s' tidak dikenal", p.id, p.tipe)
        return None
    cfg: dict = {}
    if p.kunci:
        cfg["key"] = p.kunci
    for k, v in (("min", p.nilai_min), ("max", p.nilai_maks), ("step", p.langkah),
                 ("unit", p.satuan), ("placeholder", p.placeholder)):
        if v not in (None, ""):
            cfg[k] = v
    if qtype == "scale":
        cfg.setdefault("min", 1)
        cfg.setdefault("max", 5)
    if p.label_min or p.label_maks:
        cfg["labels"] = [p.label_min or "", p.label_maks or ""]
    options: list = []
    if qtype == "choice":
        options = [{"id": str(o.id), "text": o.teks, "tags": _tags(o)} for o in p.opsi if o.teks]
        if len(options) < 2:
            log.warning("Pertanyaan id=%s dilewati: tipe pilihan butuh minimal 2 opsi", p.id)
            return None
    elif qtype == "number":
        rules = sorted(p.opsi, key=lambda o: (o.batas_atas is None, o.batas_atas or 0))
        cfg["rules"] = [({"lte": o.batas_atas} if o.batas_atas is not None else {}) | {"tags": _tags(o)}
                        for o in rules]
    return Soal(id=p.id, order=nomor, category=p.kategori or "Umum", text=p.teks, qtype=qtype,
                required=bool(p.wajib), config=cfg, options=options)


def load_soal(db: Session, semester: int | None = None) -> list[Soal]:
    rows = db.scalars(select(Pertanyaan).where(Pertanyaan.aktif.is_(True))
                      .options(selectinload(Pertanyaan.opsi))
                      .order_by(Pertanyaan.urutan, Pertanyaan.id)).all()
    out: list[Soal] = []
    for p in rows:
        if not cocok_semester(p, semester):
            continue
        soal = soal_dari_pertanyaan(p, len(out) + 1)
        if soal:
            out.append(soal)
    return out
