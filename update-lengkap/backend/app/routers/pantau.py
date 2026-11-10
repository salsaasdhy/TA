"""Pemantauan mahasiswa oleh dosen wali dan psikolog + panduan tertulis dari psikolog."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import rag
from ..analysis import FLAG_LABELS
from ..database import get_db
from ..models import Perwalian, RujukanPsikolog, Submission, User
from ..schemas import (DetailMahasiswa, HistoryItem, MahasiswaRingkas, RujukanIn, RujukanOut, RujukanUpdate)
from ..security import butuh_peran

router = APIRouter(prefix="/api", tags=["pantau"])
STAF = butuh_peran("psikolog", "dosen_wali")
PSIKOLOG = butuh_peran("psikolog")


def perlu_perhatian(konsistensi: int, issue_count: int, flags: list[str]) -> bool:
    """Penanda otomatis dari kuisioner. Bukan diagnosis."""
    return konsistensi < 40 or issue_count >= 4 or "stress" in flags


def _ringkas(db: Session, m: User) -> MahasiswaRingkas:
    data = dict(id=m.id, nama=m.name, nim=m.nim, program_studi=m.program_studi,
                angkatan=m.angkatan, izin=m.izin_pantau, ada_hasil=False)
    if not m.izin_pantau:  # tanpa izin: hanya identitas, tidak ada hasil
        return MahasiswaRingkas(**data)
    subs = db.scalars(select(Submission).where(Submission.user_id == m.id)
                      .order_by(Submission.id.desc()).limit(2)).all()
    if not subs:
        return MahasiswaRingkas(**data)
    s = subs[0]
    data.update(ada_hasil=True, terakhir_isi=s.created_at, style=s.style, konsistensi=s.consistency,
                issue_count=s.issue_count,
                tren=(s.consistency - subs[1].consistency) if len(subs) > 1 else None,
                perlu_perhatian=perlu_perhatian(s.consistency, s.issue_count, s.flags or []))
    return MahasiswaRingkas(**data)


def _cakupan(db: Session, staf: User) -> list[User]:
    if staf.peran == "dosen_wali":  # hanya mahasiswa perwaliannya
        q = (select(User).join(Perwalian, Perwalian.mahasiswa_id == User.id)
             .where(Perwalian.dosen_id == staf.id, User.peran == "mahasiswa"))
    else:  # psikolog: semua mahasiswa yang memberi izin
        q = select(User).where(User.peran == "mahasiswa", User.izin_pantau.is_(True))
    return list(db.scalars(q.order_by(User.name)).all())


def _boleh(db: Session, staf: User, mid: int) -> User:
    m = db.get(User, mid)
    if not m or m.peran != "mahasiswa":
        raise HTTPException(404, "Mahasiswa tidak ditemukan.")
    if staf.peran == "dosen_wali" and not db.scalar(
            select(Perwalian.id).where(Perwalian.dosen_id == staf.id, Perwalian.mahasiswa_id == mid)):
        raise HTTPException(404, "Mahasiswa tidak ditemukan.")
    if not m.izin_pantau:
        raise HTTPException(403, "Mahasiswa ini belum memberi izin untuk dipantau.")
    return m


@router.get("/pantau/mahasiswa", response_model=list[MahasiswaRingkas])
def daftar_mahasiswa(staf: User = Depends(STAF), db: Session = Depends(get_db)):
    return [_ringkas(db, m) for m in _cakupan(db, staf)]


@router.get("/pantau/mahasiswa/{mid}", response_model=DetailMahasiswa)
def detail_mahasiswa(mid: int, staf: User = Depends(STAF), db: Session = Depends(get_db)):
    m = _boleh(db, staf, mid)
    ringkas = _ringkas(db, m)
    subs = db.scalars(select(Submission).where(Submission.user_id == m.id).order_by(Submission.id.desc())).all()
    if not subs:
        return DetailMahasiswa(mahasiswa=ringkas, masalah=[], insights=[], aksi_selesai=0, aksi_total=0, riwayat=[])
    s = subs[0]
    return DetailMahasiswa(
        mahasiswa=ringkas, masalah=[FLAG_LABELS.get(f, f) for f in (s.flags or [])], insights=s.insights,
        aksi_selesai=sum(1 for a in s.actions if a.done), aksi_total=len(s.actions),
        riwayat=[HistoryItem(id=x.id, created_at=x.created_at, style=x.style, consistency=x.consistency,
                             issue_count=x.issue_count) for x in subs])


# ---------- panduan dari psikolog ----------
def _rujukan_out(r: RujukanPsikolog, nama: str, uid: int) -> RujukanOut:
    return RujukanOut(id=r.id, judul=r.judul, kategori=r.kategori, isi=r.isi, aktif=r.aktif,
                      psikolog=nama, milik_saya=r.psikolog_id == uid, diubah=r.diubah)


def _milik(db: Session, user: User, rid: int) -> RujukanPsikolog:
    r = db.get(RujukanPsikolog, rid)
    if not r or r.psikolog_id != user.id:
        raise HTTPException(404, "Panduan tidak ditemukan, atau bukan milikmu.")
    return r


@router.get("/psikolog/rujukan", response_model=list[RujukanOut])
def daftar_rujukan(user: User = Depends(PSIKOLOG), db: Session = Depends(get_db)):
    rows = db.execute(select(RujukanPsikolog, User.name).join(User, User.id == RujukanPsikolog.psikolog_id)
                      .order_by(RujukanPsikolog.id.desc())).all()
    return [_rujukan_out(r, nama, user.id) for r, nama in rows]


@router.post("/psikolog/rujukan", response_model=RujukanOut, status_code=201)
def tambah_rujukan(body: RujukanIn, user: User = Depends(PSIKOLOG), db: Session = Depends(get_db)):
    r = RujukanPsikolog(psikolog_id=user.id, judul=body.judul.strip(), kategori=(body.kategori or "").strip() or None,
                        isi=body.isi.strip(), aktif=body.aktif)
    db.add(r)
    db.commit()
    db.refresh(r)
    rag.reindex_async()
    return _rujukan_out(r, user.name, user.id)


@router.patch("/psikolog/rujukan/{rid}", response_model=RujukanOut)
def ubah_rujukan(rid: int, body: RujukanUpdate, user: User = Depends(PSIKOLOG), db: Session = Depends(get_db)):
    r = _milik(db, user, rid)
    for k, v in body.model_dump(exclude_unset=True).items():
        if v is None and k != "kategori":
            continue
        setattr(r, k, v.strip() if isinstance(v, str) else v)
    db.commit()
    db.refresh(r)
    rag.reindex_async()
    return _rujukan_out(r, user.name, user.id)


@router.delete("/psikolog/rujukan/{rid}", status_code=204)
def hapus_rujukan(rid: int, user: User = Depends(PSIKOLOG), db: Session = Depends(get_db)):
    db.delete(_milik(db, user, rid))
    db.commit()
    rag.reindex_async()
