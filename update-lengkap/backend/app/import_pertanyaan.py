"""Impor pertanyaan dari Excel/CSV, menggantikan SEMUA pertanyaan yang ada.

Pemakaian (dari folder backend):
    python -m app.import_pertanyaan pertanyaan.xlsx
"""
import csv
import io
import sys
from pathlib import Path

TIPE_VALID = ("pilihan", "angka", "teks", "skala")
YA = ("ya", "y", "yes", "true", "1", "wajib", "aktif")
TIDAK = ("tidak", "t", "no", "false", "0", "n")


def _txt(v):
    if v is None:
        return None
    s = str(v).strip()
    return s or None


def _num(v):
    s = _txt(v)
    return None if s is None else float(s.replace(",", "."))


def _int(v):
    s = _txt(v)
    return None if s is None else int(float(s.replace(",", ".")))


def _bool(v, default):
    s = _txt(v)
    if s is None:
        return default
    s = s.lower()
    if s in YA:
        return True
    if s in TIDAK:
        return False
    raise ValueError(f"'{v}' bukan ya/tidak")


def read_rows(path: Path) -> list[dict]:
    if path.suffix.lower() in (".xlsx", ".xlsm"):
        from openpyxl import load_workbook
        wb = load_workbook(path, data_only=True)
        ws = wb["pertanyaan"] if "pertanyaan" in wb.sheetnames else wb.active
        grid = list(ws.iter_rows(values_only=True))
    else:
        text = path.read_text(encoding="utf-8-sig")
        first = text.splitlines()[0] if text else ""
        delim = max(",;\t", key=first.count)
        grid = list(csv.reader(io.StringIO(text), delimiter=delim))
    if not grid:
        return []
    header = [(_txt(h) or "").lower() for h in grid[0]]
    return [{h: v for h, v in zip(header, row) if h} for row in grid[1:]]


def parse_rows(rows: list[dict]) -> tuple[list[dict], list[str]]:
    from .analysis import FLAG_LABELS
    errors: list[str] = []
    groups: dict[int, list[tuple[int, dict]]] = {}
    for n, row in enumerate(rows, start=2):  # baris 1 = header
        if all(_txt(v) is None for v in row.values()):
            continue
        try:
            u = _num(row.get("urutan"))
        except ValueError:
            u = None
        if u is None:
            errors.append(f"Baris {n}: kolom 'urutan' harus berisi angka.")
            continue
        groups.setdefault(int(u), []).append((n, row))

    result: list[dict] = []
    for urutan in sorted(groups):
        items = groups[urutan]
        first_row = items[0][0]

        def pick(col):
            return next((_txt(r.get(col)) for _, r in items if _txt(r.get(col)) is not None), None)

        def err(msg):
            errors.append(f"Pertanyaan urutan {urutan} (baris {first_row}): {msg}")

        teks = pick("pertanyaan")
        tipe = (pick("tipe") or "pilihan").lower()
        if not teks:
            err("kolom 'pertanyaan' kosong.")
        if tipe not in TIPE_VALID:
            err(f"tipe '{tipe}' tidak dikenal. Pilihan: {', '.join(TIPE_VALID)}.")
            continue
        try:
            q = dict(
                urutan=urutan, kategori=pick("kategori") or "Umum", teks=teks or "", tipe=tipe,
                wajib=_bool(pick("wajib"), True), aktif=_bool(pick("aktif"), True),
                kunci=pick("kunci"), min_semester=_int(pick("min_semester")),
                maks_semester=_int(pick("maks_semester")), nilai_min=_num(pick("min")), nilai_maks=_num(pick("maks")),
                langkah=_num(pick("langkah")), satuan=pick("satuan"), placeholder=pick("placeholder"),
                label_min=pick("label_min"), label_maks=pick("label_maks"), opsi=[])
        except ValueError as e:
            err(str(e))
            continue
        if tipe == "skala":
            q["nilai_min"] = 1 if q["nilai_min"] is None else q["nilai_min"]
            q["nilai_maks"] = 5 if q["nilai_maks"] is None else q["nilai_maks"]
        if tipe in ("pilihan", "angka"):
            for j, (n, r) in enumerate(items, start=1):
                try:
                    opsi_teks = _txt(r.get("opsi"))
                    batas = _num(r.get("batas_atas"))
                    skor = {k: int(_num(r.get(c)) or 0) for k, c in (
                        ("skor_visual", "skor_visual"), ("skor_auditori", "skor_auditori"),
                        ("skor_kinestetik", "skor_kinestetik"))}
                    kons = _num(r.get("skor_konsistensi"))
                    flag = _txt(r.get("penanda"))
                except ValueError as e:
                    errors.append(f"Baris {n}: {e}.")
                    continue
                if flag and flag not in FLAG_LABELS:
                    errors.append(f"Baris {n}: penanda '{flag}' tidak dikenal. Pilihan: {', '.join(FLAG_LABELS)}.")
                    continue
                ada_isi = tipe == "pilihan" and opsi_teks or tipe == "angka" and (
                    batas is not None or kons is not None or flag or any(skor.values()))
                if not ada_isi:
                    continue
                q["opsi"].append(dict(urutan=j, teks=opsi_teks if tipe == "pilihan" else None,
                                      batas_atas=batas if tipe == "angka" else None,
                                      skor_konsistensi=None if kons is None else int(kons),
                                      penanda=flag, **skor))
            if tipe == "pilihan" and len(q["opsi"]) < 2:
                err("tipe 'pilihan' butuh minimal 2 baris dengan kolom 'opsi' terisi.")
        result.append(q)
    return result, errors


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("Pemakaian: python -m app.import_pertanyaan pertanyaan.xlsx")
        return 1
    path = Path(argv[1])
    if not path.exists():
        print(f"File tidak ditemukan: {path}")
        return 1
    data, errors = parse_rows(read_rows(path))
    if errors:
        print("Impor dibatalkan, perbaiki dulu di file Excel:")
        for e in errors:
            print(" -", e)
        return 1
    if not data:
        print("Tidak ada pertanyaan yang terbaca di file.")
        return 1

    from sqlalchemy import delete
    from .database import Base, SessionLocal, engine
    from .models import OpsiJawaban, Pertanyaan

    Base.metadata.create_all(engine)
    n_opsi = 0
    with SessionLocal() as db:
        db.execute(delete(OpsiJawaban))
        db.execute(delete(Pertanyaan))
        for q in data:
            opsi = q.pop("opsi")
            p = Pertanyaan(**q)
            p.opsi = [OpsiJawaban(**o) for o in opsi]
            n_opsi += len(opsi)
            db.add(p)
        db.commit()
    aktif = sum(1 for q in data if q["aktif"])
    print(f"Selesai: {len(data)} pertanyaan ({aktif} aktif), {n_opsi} baris opsi/aturan diimpor.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
