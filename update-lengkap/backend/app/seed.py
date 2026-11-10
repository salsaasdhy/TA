from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import OpsiJawaban, Pertanyaan, User
from .security import hash_password

# Tag pada opsi/aturan:
#   v/a/k = poin gaya belajar Visual/Auditori/Kinestetik
#   c     = skor konsistensi (0-3)
#   f     = penanda masalah: late_night, distraction, no_schedule, short_duration,
#           overload, procrastination, no_retrieval, stress
# config.key = nama data untuk ringkasan profil yang dikirim ke AI Coach.


def choice(cat, text, options, required=True, key=None, min_semester=None, maks_semester=None):
    return dict(category=cat, text=text, qtype="choice", required=required, config={"key": key} if key else {},
                options=options, min_semester=min_semester, maks_semester=maks_semester)


def number(cat, text, config, required=True):
    return dict(category=cat, text=text, qtype="number", required=required, config=config, options=[])


def short_text(cat, text, config, required=True):
    return dict(category=cat, text=text, qtype="text", required=required, config=config, options=[])


def scale(cat, text, config, required=True):
    return dict(category=cat, text=text, qtype="scale", required=required, config=config, options=[])


def freq(flag):
    return [("Selalu", {"c": 0, "f": flag}), ("Sering", {"c": 1, "f": flag}),
            ("Kadang", {"c": 2}), ("Jarang", {"c": 3}), ("Tidak pernah", {"c": 3})]


QUESTIONS = [
    choice("Manajemen Waktu", "Berapa rata-rata durasi belajar mandiri kamu per hari?", [
        ("Kurang dari 1 jam", {"c": 0, "f": "short_duration"}),
        ("1–2 jam", {"c": 2}), ("2–4 jam", {"c": 3}), ("Lebih dari 4 jam", {"c": 3})], key="durasi_harian"),
    choice("Manajemen Waktu", "Kapan waktu belajar yang paling sering kamu pilih?", [
        ("Pagi", {"c": 3}), ("Siang", {"c": 3}), ("Sore", {"c": 2}), ("Malam", {"c": 1}),
        ("Larut malam", {"c": 0, "f": "late_night"}), ("Tidak menentu", {"c": 0, "f": "no_schedule"})],
           key="waktu_belajar"),
    choice("Teknik Belajar", "Metode belajar apa yang paling sering kamu gunakan?", [
        ("Membaca ulang catatan", {"v": 1, "f": "no_retrieval"}),
        ("Membuat ringkasan", {"v": 1}),
        ("Belajar kelompok", {"a": 2}),
        ("Latihan soal", {"k": 2}),
        ("Menonton video", {"v": 2}),
        ("Mengajari orang lain", {"a": 1, "k": 1})]),
    choice("Konsistensi", "Seberapa sering kamu belajar mendekati deadline atau H-1 ujian?", freq("procrastination")),
    choice("Fokus & Distraksi", "Berapa lama rata-rata kamu bisa fokus sebelum terdistraksi?", [
        ("Kurang dari 15 menit", {"c": 0, "f": "distraction"}), ("15–30 menit", {"c": 1}),
        ("30–60 menit", {"c": 2}), ("Lebih dari 60 menit", {"c": 3})]),
    choice("Fokus & Distraksi", "Apa gangguan konsentrasi terbesar saat belajar?", [
        ("HP / media sosial", {"f": "distraction"}), ("Kebisingan", {}), ("Rasa kantuk", {}),
        ("Pikiran melayang", {}), ("Notifikasi kerja / organisasi", {"f": "distraction"})]),
    choice("Organisasi & Kegiatan", "Apakah kamu aktif di organisasi atau UKM kampus?", [
        ("Ya, sebagai pengurus inti", {}), ("Ya, sebagai anggota", {}), ("Tidak", {})], key="organisasi"),
    choice("Organisasi & Kegiatan", "Berapa jam per minggu waktu yang terpakai untuk kegiatan organisasi?", [
        ("Tidak ikut organisasi", {"c": 3}), ("1–5 jam", {"c": 3}), ("6–10 jam", {"c": 2}),
        ("11–20 jam", {"c": 1}), ("Lebih dari 20 jam", {"c": 0, "f": "overload"})]),
    choice("Manajemen Waktu", "Bagaimana kamu biasanya mengatur prioritas antara kuliah, kerja, dan organisasi?", [
        ("Pakai jadwal atau planner", {"c": 3}),
        ("Mengikuti mood", {"c": 1, "f": "no_schedule"}),
        ("Selalu mendahulukan deadline terdekat", {"c": 2}),
        ("Sering kewalahan mengatur ketiganya", {"c": 0, "f": "overload"})]),
    choice("Organisasi & Kegiatan", "Seberapa sering jadwal belajarmu terganggu karena kerja atau organisasi?", freq("overload")),
    choice("Akademik", "Jenis mata kuliah apa yang menurutmu paling menantang semester ini?", [
        ("Pemrograman atau logika", {}), ("Matematika atau statistika", {}), ("Desain atau kreatif", {}),
        ("Teori dan hafalan", {}), ("Praktikum atau proyek", {}), ("Bahasa atau komunikasi", {}),
        ("Lainnya", {})], required=False, key="matkul"),
    choice("Akademik", "Menurutmu, kenapa mata kuliah tersebut terasa sulit?", [
        ("Materinya abstrak", {}), ("Kurang waktu belajar", {}), ("Metode dosen kurang cocok", {}),
        ("Kurang praktik atau latihan", {}), ("Lainnya", {})], required=False, key="kesulitan"),
    choice("Akademik", "Di kisaran mana IPK kamu saat ini? (opsional)", [
        ("Di bawah 2,50", {}), ("2,50–2,99", {}), ("3,00–3,49", {}), ("3,50 ke atas", {}),
        ("Tidak ingin menyebutkan", {})], required=False, key="ipk", min_semester=2),
    choice("Prokrastinasi", "Seberapa sering kamu menunda memulai tugas walau sudah tahu deadline-nya?", freq("procrastination")),
    choice("Prokrastinasi", "Apa alasan utama kamu menunda tugas?", [
        ("Merasa masih ada waktu", {}), ("Tidak tahu harus mulai dari mana", {}), ("Merasa lelah", {}),
        ("Terganggu hiburan digital", {"f": "distraction"}), ("Tugas terasa terlalu berat", {})], key="alasan_tunda"),
    choice("Prokrastinasi", "Bagaimana perasaanmu saat tugas menumpuk karena tertunda?", [
        ("Sangat stres", {"f": "stress"}), ("Cukup stres", {}), ("Biasa saja", {}), ("Tidak terpengaruh", {})]),
    choice("Tujuan", "Apa tujuan belajarmu saat ini yang paling utama?", [
        ("Lulus tepat waktu", {}), ("IPK tinggi", {}), ("Menguasai skill untuk kerja", {}),
        ("Menyelesaikan proyek akhir", {}), ("Lainnya", {})], key="tujuan"),
    choice("Tujuan", "Dalam skala 1–5, seberapa yakin kamu bisa mengubah kebiasaan belajarmu jika diberi rekomendasi yang jelas?", [
        ("1 – Sangat tidak yakin", {}), ("2 – Kurang yakin", {}), ("3 – Cukup yakin", {}),
        ("4 – Yakin", {}), ("5 – Sangat yakin", {})], key="keyakinan"),
]


TIPE_ID = {"choice": "pilihan", "number": "angka", "text": "teks", "scale": "skala"}


def _opsi(urutan: int, teks, batas, tags: dict) -> OpsiJawaban:
    return OpsiJawaban(urutan=urutan, teks=teks, batas_atas=batas,
                       skor_visual=tags.get("v", 0), skor_auditori=tags.get("a", 0),
                       skor_kinestetik=tags.get("k", 0), skor_konsistensi=tags.get("c"),
                       penanda=tags.get("f"))


def seed_questions(db: Session) -> None:
    """Isi pertanyaan bawaan HANYA jika tabel masih kosong. Untuk mengganti: impor Excel atau edit di pgAdmin."""
    if db.scalar(select(Pertanyaan.id).limit(1)):
        return
    for i, q in enumerate(QUESTIONS, start=1):
        cfg = q["config"]
        labels = cfg.get("labels") or [None, None]
        p = Pertanyaan(urutan=i, kategori=q["category"], teks=q["text"], tipe=TIPE_ID[q["qtype"]],
                       wajib=q["required"], aktif=True, kunci=cfg.get("key"),
                       nilai_min=cfg.get("min"), nilai_maks=cfg.get("max"), langkah=cfg.get("step"),
                       satuan=cfg.get("unit"), placeholder=cfg.get("placeholder"),
                       label_min=labels[0], label_maks=labels[1],
                       min_semester=q.get("min_semester"), maks_semester=q.get("maks_semester"))
        if q["qtype"] == "choice":
            for j, (teks, tags) in enumerate(q["options"], start=1):
                p.opsi.append(_opsi(j, teks, None, tags))
        elif q["qtype"] == "number":
            for j, rule in enumerate(cfg.get("rules", []), start=1):
                p.opsi.append(_opsi(j, None, rule.get("lte"), rule.get("tags", {})))
        db.add(p)
    db.commit()


def seed_demo_user(db: Session) -> None:
    email = "demo@habitcoach.id"
    if db.scalar(select(User.id).where(User.email == email)):
        return
    db.add(User(
        name="Salsabila Nur Asad H.", email=email, password_hash=hash_password("demo1234"),
        nim="5323600021", program_studi="Teknologi Rekayasa Multimedia", angkatan=2023, semester=5,
        sim_verified=True, created_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
    ))
    db.commit()
