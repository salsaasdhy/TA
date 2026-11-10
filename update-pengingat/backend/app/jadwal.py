"""Pengingat belajar: saran jadwal dari hasil kuisioner + pengiriman notifikasi (Web Push)."""
import asyncio
import json
import logging
from datetime import date, datetime
from zoneinfo import ZoneInfo

from sqlalchemy import select

from .config import settings
from .database import SessionLocal
from .models import LanggananPush, Pengingat, Submission

log = logging.getLogger(__name__)
NAMA_HARI = {1: "Senin", 2: "Selasa", 3: "Rabu", 4: "Kamis", 5: "Jumat", 6: "Sabtu", 7: "Minggu"}
TOLERANSI_MENIT = 10  # pengingat yang terlewat lebih lama dari ini tidak dikirim lagi


def push_aktif() -> bool:
    return bool(settings.vapid_public_key and settings.vapid_private_key)


# ---------- saran jadwal ----------
def _jam_dari_waktu(waktu: str) -> tuple[str, str]:
    w = waktu.lower()
    if "larut" in w:
        return "19:30", "Kamu biasa belajar larut malam. Jadwal digeser lebih awal agar waktu tidurmu terjaga, karena tidur membantu otak menyimpan materi."
    if "pagi" in w:
        return "07:00", "Kamu paling sering belajar di pagi hari, jadi pengingat dipasang di jam itu."
    if "siang" in w:
        return "13:00", "Kamu paling sering belajar di siang hari, jadi pengingat dipasang di jam itu."
    if "sore" in w:
        return "16:00", "Kamu paling sering belajar di sore hari, jadi pengingat dipasang di jam itu."
    if "malam" in w:
        return "19:30", "Kamu paling sering belajar malam hari. Pengingat dipasang sebelum pukul 20.00 agar sesi inti selesai lebih awal."
    return "16:00", "Jam belajarmu belum menentu. Mulai dengan satu slot tetap di sore hari, lalu sesuaikan setelah terbiasa."


def buat_saran(sub: Submission | None) -> dict | None:
    if sub is None:
        return None
    flags = sub.flags or []
    jam, alasan = _jam_dari_waktu((sub.facts or {}).get("waktu_belajar", ""))
    if "no_schedule" in flags or "overload" in flags:
        hari = [1, 3, 5]
        alasan += " Karena jadwalmu padat atau belum teratur, mulai dari 3 slot tetap dalam seminggu."
    else:
        hari = [1, 2, 3, 4, 5]
    if "distraction" in flags:
        pesan = "Waktunya belajar. Taruh HP di luar jangkauan dan mulai blok 25 menit pertama."
    elif "procrastination" in flags:
        pesan = "Waktunya belajar. Mulai dari 25 menit saja, langkah kecil sudah cukup."
    else:
        pesan = "Waktunya belajar. Siapkan catatanmu dan mulai sesi pertama."
    return {"jam": jam, "hari": hari, "durasi_menit": 50, "pesan": pesan, "alasan": alasan}


# ---------- pengiriman ----------
def jatuh_tempo(hari: str, jam: str, terakhir: date | None, now: datetime) -> bool:
    """True jika pengingat harus dikirim sekarang: hari cocok, belum terkirim hari ini, dalam jendela toleransi."""
    if str(now.isoweekday()) not in hari.split(","):
        return False
    if terakhir == now.date():
        return False
    h, m = (int(x) for x in jam.split(":"))
    selisih = now.hour * 60 + now.minute - (h * 60 + m)
    return 0 <= selisih <= TOLERANSI_MENIT


def _kirim(langganan: LanggananPush, payload: dict) -> bool | None:
    """True = terkirim, False = langganan sudah tidak berlaku, None = gagal sementara."""
    try:
        from pywebpush import WebPushException, webpush
    except ImportError as e:
        raise RuntimeError("Paket pywebpush belum terpasang (pip install -r requirements.txt).") from e
    try:
        webpush(
            subscription_info={"endpoint": langganan.endpoint,
                               "keys": {"p256dh": langganan.p256dh, "auth": langganan.auth}},
            data=json.dumps(payload), vapid_private_key=settings.vapid_private_key,
            vapid_claims={"sub": settings.vapid_subject}, ttl=3600)
        return True
    except WebPushException as e:
        status = getattr(getattr(e, "response", None), "status_code", None)
        if status in (404, 410):
            return False
        log.warning("Push gagal (status %s): %s", status, e)
        return None


def kirim_ke_user(db, user_id: int, payload: dict) -> int:
    terkirim = 0
    for langganan in db.scalars(select(LanggananPush).where(LanggananPush.user_id == user_id)).all():
        hasil = _kirim(langganan, payload)
        if hasil is True:
            terkirim += 1
        elif hasil is False:
            db.delete(langganan)
    db.commit()
    return terkirim


def proses_jatuh_tempo() -> int:
    now = datetime.now(ZoneInfo(settings.timezone))
    dikirim = 0
    with SessionLocal() as db:
        for p in db.scalars(select(Pengingat).where(Pengingat.aktif.is_(True))).all():
            if not jatuh_tempo(p.hari, p.jam, p.terakhir_kirim, now):
                continue
            isi = p.pesan or "Waktunya belajar. Siapkan catatanmu dan mulai sesi pertama."
            payload = {"title": "Habit Coach", "body": f"{isi} (sesi {p.durasi_menit} menit)",
                       "tag": f"belajar-{p.id}", "url": "/dashboard"}
            if kirim_ke_user(db, p.user_id, payload) > 0:
                p.terakhir_kirim = now.date()
                db.commit()
                dikirim += 1
    return dikirim


async def loop_pengingat() -> None:
    log.warning("Penjadwal pengingat aktif (zona waktu %s)", settings.timezone)
    while True:
        try:
            await asyncio.to_thread(proses_jatuh_tempo)
        except Exception:
            log.exception("Pengingat gagal diproses")
        await asyncio.sleep(30)
