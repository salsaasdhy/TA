from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import jadwal
from ..config import settings
from ..database import get_db
from ..models import LanggananPush, Pengingat, Submission, User
from ..schemas import PengingatIn, PengingatOut, PengingatUpdate, PushIn, SaranOut
from ..security import current_user

router = APIRouter(prefix="/api", tags=["pengingat"])
MAKS_PENGINGAT = 10


def _out(p: Pengingat) -> PengingatOut:
    return PengingatOut(id=p.id, jam=p.jam, hari=[int(x) for x in p.hari.split(",") if x],
                        durasi_menit=p.durasi_menit, pesan=p.pesan, aktif=p.aktif)


def _milik(db: Session, user: User, pid: int) -> Pengingat:
    p = db.get(Pengingat, pid)
    if not p or p.user_id != user.id:
        raise HTTPException(404, "Pengingat tidak ditemukan.")
    return p


@router.get("/reminders", response_model=list[PengingatOut])
def daftar(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(Pengingat).where(Pengingat.user_id == user.id)
                      .order_by(Pengingat.jam, Pengingat.id)).all()
    return [_out(p) for p in rows]


@router.get("/reminders/suggestion", response_model=SaranOut | None)
def saran(user: User = Depends(current_user), db: Session = Depends(get_db)):
    sub = db.scalars(select(Submission).where(Submission.user_id == user.id)
                     .order_by(Submission.id.desc()).limit(1)).first()
    return jadwal.buat_saran(sub)


@router.post("/reminders", response_model=PengingatOut, status_code=201)
def tambah(body: PengingatIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    n = db.scalar(select(func.count(Pengingat.id)).where(Pengingat.user_id == user.id)) or 0
    if n >= MAKS_PENGINGAT:
        raise HTTPException(409, f"Maksimal {MAKS_PENGINGAT} pengingat. Hapus yang tidak dipakai dulu.")
    p = Pengingat(user_id=user.id, jam=body.jam, hari=",".join(str(h) for h in body.hari),
                  durasi_menit=body.durasi_menit, pesan=body.pesan, aktif=body.aktif)
    db.add(p)
    db.commit()
    return _out(p)


@router.patch("/reminders/{pid}", response_model=PengingatOut)
def ubah(pid: int, body: PengingatUpdate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    p = _milik(db, user, pid)
    data = body.model_dump(exclude_unset=True)
    if "hari" in data and data["hari"] is not None:
        data["hari"] = ",".join(str(h) for h in data["hari"])
    for k, v in data.items():
        if v is None and k != "pesan":
            continue
        setattr(p, k, v)
    if {"jam", "hari"} & data.keys():
        p.terakhir_kirim = None  # jadwal berubah, boleh terkirim lagi hari ini
    db.commit()
    return _out(p)


@router.delete("/reminders/{pid}", status_code=204)
def hapus(pid: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    db.delete(_milik(db, user, pid))
    db.commit()


@router.get("/push/key")
def kunci_publik(_: User = Depends(current_user)):
    return {"tersedia": jadwal.push_aktif(), "public_key": settings.vapid_public_key}


@router.post("/push/subscribe", status_code=201)
def langganan(body: PushIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    row = db.scalars(select(LanggananPush).where(LanggananPush.endpoint == body.endpoint)).first()
    if row:
        row.user_id, row.p256dh, row.auth = user.id, body.keys.p256dh, body.keys.auth
    else:
        db.add(LanggananPush(user_id=user.id, endpoint=body.endpoint,
                             p256dh=body.keys.p256dh, auth=body.keys.auth))
    db.commit()
    return {"ok": True}


@router.post("/push/unsubscribe")
def berhenti(body: dict, user: User = Depends(current_user), db: Session = Depends(get_db)):
    endpoint = str(body.get("endpoint", ""))
    row = db.scalars(select(LanggananPush).where(LanggananPush.endpoint == endpoint,
                                                 LanggananPush.user_id == user.id)).first()
    if row:
        db.delete(row)
        db.commit()
    return {"ok": True}


@router.post("/push/test")
def uji(user: User = Depends(current_user), db: Session = Depends(get_db)):
    if not jadwal.push_aktif():
        raise HTTPException(503, "Kunci VAPID belum diatur di backend/.env (jalankan python -m app.vapid).")
    payload = {"title": "Habit Coach", "body": "Notifikasi berfungsi. Pengingat belajarmu akan muncul seperti ini.",
               "tag": "uji", "url": "/pengingat"}
    try:
        n = jadwal.kirim_ke_user(db, user.id, payload)
    except RuntimeError as e:
        raise HTTPException(503, str(e))
    if n == 0:
        raise HTTPException(409, "Belum ada perangkat yang berlangganan, atau pengiriman gagal. Aktifkan notifikasi di perangkat ini dulu.")
    return {"terkirim": n}
