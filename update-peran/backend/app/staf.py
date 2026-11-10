"""Kelola akun staf (psikolog dan dosen wali). Dijalankan dari folder backend:

  python -m app.staf buat --email psikolog@kampus.ac.id --nama "Nama Psikolog" --peran psikolog
  python -m app.staf buat --email dosen@kampus.ac.id --nama "Nama Dosen" --peran dosen_wali
  python -m app.staf ubah-peran --email akun@kampus.ac.id --peran dosen_wali     (akun yang sudah ada)
  python -m app.staf tugaskan --dosen dosen@kampus.ac.id 5323600021 5323600022   (NRP atau email mahasiswa)
  python -m app.staf daftar
"""
import argparse
import getpass
import sys

from sqlalchemy import func, select

from .database import Base, SessionLocal, engine
from .models import Perwalian, User
from .security import hash_password

PERAN_STAF = ("psikolog", "dosen_wali")


def buat(db, a) -> int:
    if db.scalar(select(User.id).where(User.email == a.email)):
        print(f"Email {a.email} sudah terdaftar. Untuk mengubah perannya: ubah-peran --email {a.email} --peran {a.peran}")
        return 1
    sandi = getpass.getpass("Sandi akun (min. 6 karakter): ")
    if len(sandi) < 6 or sandi != getpass.getpass("Ulangi sandi: "):
        print("Sandi terlalu pendek atau tidak sama.")
        return 1
    db.add(User(name=a.nama, email=a.email, password_hash=hash_password(sandi), peran=a.peran))
    db.commit()
    print(f"Akun {a.peran} dibuat: {a.email}")
    return 0


def ubah_peran(db, a) -> int:
    u = db.scalar(select(User).where(User.email == a.email))
    if not u:
        print("Akun tidak ditemukan.")
        return 1
    u.peran = a.peran
    db.commit()
    print(f"{a.email} sekarang berperan {a.peran}.")
    return 0


def tugaskan(db, a) -> int:
    dosen = db.scalar(select(User).where(User.email == a.dosen, User.peran == "dosen_wali"))
    if not dosen:
        print("Dosen wali tidak ditemukan (periksa email dan perannya).")
        return 1
    baru = lewat = 0
    tidak_ada = []
    for ident in a.mahasiswa:
        m = db.scalar(select(User).where((User.nim == ident) | (User.email == ident), User.peran == "mahasiswa"))
        if not m:
            tidak_ada.append(ident)
        elif db.scalar(select(Perwalian.id).where(Perwalian.dosen_id == dosen.id, Perwalian.mahasiswa_id == m.id)):
            lewat += 1
        else:
            db.add(Perwalian(dosen_id=dosen.id, mahasiswa_id=m.id))
            baru += 1
    db.commit()
    print(f"{baru} mahasiswa ditambahkan, {lewat} sudah terdaftar sebelumnya.")
    if tidak_ada:
        print("Tidak ditemukan (belum mendaftar?):", ", ".join(tidak_ada))
    return 0


def daftar(db, _a) -> int:
    for u in db.scalars(select(User).where(User.peran.in_(PERAN_STAF)).order_by(User.peran, User.name)).all():
        n = db.scalar(select(func.count(Perwalian.id)).where(Perwalian.dosen_id == u.id)) or 0
        print(f"{u.peran:10s} {u.email:35s} {u.name}" + (f"  ({n} mahasiswa)" if u.peran == "dosen_wali" else ""))
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Kelola akun staf Habit Coach")
    sub = p.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("buat"); b.add_argument("--email", required=True); b.add_argument("--nama", required=True)
    b.add_argument("--peran", required=True, choices=PERAN_STAF)
    o = sub.add_parser("ubah-peran"); o.add_argument("--email", required=True)
    o.add_argument("--peran", required=True, choices=PERAN_STAF + ("mahasiswa",))
    t = sub.add_parser("tugaskan"); t.add_argument("--dosen", required=True); t.add_argument("mahasiswa", nargs="+")
    sub.add_parser("daftar")
    a = p.parse_args()
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        return {"buat": buat, "ubah-peran": ubah_peran, "tugaskan": tugaskan, "daftar": daftar}[a.cmd](db, a)


if __name__ == "__main__":
    sys.exit(main())
