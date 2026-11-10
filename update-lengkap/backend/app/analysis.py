"""Skoring kuisioner (rule-based) + pembuatan insight yang diperkaya RAG."""
import logging

from . import rag
from .config import settings

log = logging.getLogger(__name__)

STYLE_NAMES = {"v": "Visual", "a": "Auditori", "k": "Kinestetik"}
PRIORITY = ["procrastination", "stress", "overload", "no_retrieval", "distraction",
            "short_duration", "late_night", "no_schedule"]
POLA = {"late_night", "distraction", "no_schedule", "short_duration", "overload"}
DIAG = {"procrastination", "no_retrieval", "stress"}

FLAG_LABELS = {
    "late_night": "belajar larut malam",
    "distraction": "mudah terdistraksi gawai atau notifikasi",
    "no_schedule": "jadwal belajar tidak teratur",
    "short_duration": "durasi belajar mandiri pendek",
    "overload": "kewalahan membagi waktu dengan organisasi atau kerja",
    "procrastination": "sering menunda tugas dan belajar H-1",
    "no_retrieval": "mengulang materi tanpa menguji diri",
    "stress": "stres tinggi saat tugas menumpuk",
}

INFO = {
    "late_night": dict(
        title="Belajar larut malam, fokus mudah menurun",
        body="Sesi belajar utamamu dimulai setelah pukul 21.00. Jam ini sering bertabrakan dengan rasa kantuk dan memangkas waktu tidur, padahal tidur membantu otak menyimpan materi.",
        query="tidur konsolidasi memori belajar malam",
        ref="Diekelmann & Born (2010), Nature Reviews Neuroscience",
        action="Pindahkan sesi belajar utama ke sebelum pukul 20.00",
        reco=("Geser sesi belajar lebih awal", "Mulai sesi inti sebelum pukul 20.00 dan sisakan malam untuk mengulang ringan, supaya tidurmu tidak terpotong.")),
    "distraction": dict(
        title="Sesi belajar sering terputus gawai",
        body="Kamu sering mengecek HP saat belajar. Ponsel yang berada di dekatmu saja sudah bisa menyedot sebagian kapasitas fokus.",
        query="smartphone distraksi fokus kapasitas kognitif",
        ref="Ward et al. (2017), Journal of the Association for Consumer Research",
        action="Aktifkan mode senyap dan jauhkan HP saat sesi fokus",
        reco=("Terapkan Pomodoro 25 menit tanpa HP", "Belajar dalam blok 25 menit dengan HP di luar jangkauan, lalu jeda 5 menit untuk mengecek notifikasi.")),
    "no_schedule": dict(
        title="Jadwal belajar belum teratur",
        body="Belajarmu lebih mengikuti suasana hati atau ujian, sehingga kebiasaan sulit terbentuk.",
        query="implementation intentions rencana jadwal belajar",
        ref="Gollwitzer (1999), American Psychologist",
        action="Tetapkan 3 slot belajar tetap dalam seminggu",
        reco=("Buat jadwal 'jika-maka'", "Tulis rencana spesifik, misalnya: jika kelas selesai pukul 15.00, maka aku belajar 25 menit di perpustakaan.")),
    "procrastination": dict(
        title="Indikasi prokrastinasi tinggi",
        body="Tugas cenderung kamu kerjakan mendekati tenggat. Pola ini umum, dan penelitian mengaitkannya dengan performa akademik yang lebih rendah.",
        query="prokrastinasi akademik tenggat tugas",
        ref="Steel (2007), Psychological Bulletin",
        action="Kerjakan tugas 25 menit per hari sejak tugas diberikan",
        reco=("Mulai dari langkah kecil dengan Pomodoro", "Pecah tugas menjadi blok 25 menit. Memulai yang kecil biasanya lebih mudah daripada menunggu mood datang.")),
    "no_retrieval": dict(
        title="Minim teknik retrieval",
        body="Kamu mengulang materi dengan membaca ulang atau menyorot. Menguji diri (active recall) terbukti lebih kuat tetapi belum kamu terapkan secara konsisten.",
        query="active recall testing effect flashcard spaced repetition",
        ref="Roediger & Karpicke (2006), Psychological Science",
        action="Ulangi materi dengan flashcard atau soal latihan",
        reco=("Terapkan Active Recall + Spaced Repetition", "Uji diri dengan flashcard, lalu ulangi pada hari ke-1, ke-3, dan ke-7 setelah belajar pertama.")),
}

INFO.update({
    "short_duration": dict(
        title="Durasi belajar mandiri masih pendek",
        body="Waktu belajar mandirimu kurang dari 1 jam per hari. Durasi sesingkat itu menyulitkan materi diulang dan diperdalam sebelum ujian.",
        query="durasi belajar mandiri manajemen waktu self-regulated learning",
        ref=None,
        action="Sisihkan 2 blok belajar 25 menit setiap hari, lalu tambah bertahap",
        reco=("Bangun durasi belajar secara bertahap", "Mulai dari 2 blok 25 menit per hari, lalu tambah 10 menit tiap minggu sampai mencapai 1–2 jam.")),
    "overload": dict(
        title="Waktu terbagi, jadwal belajar mudah terganggu",
        body="Kegiatan organisasi atau kerja sering menggeser jadwal belajarmu, dan kamu merasa kewalahan membagi prioritas.",
        query="manajemen waktu organisasi kerja prioritas self-regulated learning prokrastinasi",
        ref=None,
        action="Blokir 3 slot belajar di kalender dan perlakukan seperti jadwal rapat",
        reco=("Lindungi jam belajar di jadwal mingguan", "Tuliskan semua komitmen di satu planner, blokir jam belajar lebih dulu, lalu atur kegiatan lain di sekitarnya.")),
    "stress": dict(
        title="Tugas menumpuk memicu stres tinggi",
        body="Kamu merasa sangat tertekan saat tugas menumpuk karena tertunda. Tekanan ini bisa memperkuat kebiasaan menunda berikutnya.",
        query="stres kecemasan prokrastinasi akademik mahasiswa",
        ref=None,
        action="Daftar semua tugas beserta tenggatnya, lalu kerjakan satu langkah kecil hari ini",
        reco=("Pecah tugas agar tekanan turun", "Daftar semua tugas, urutkan menurut tenggat, lalu kerjakan satu langkah kecil lebih dulu supaya rasa kewalahan berkurang.")),
})

DEFAULTS = {
    "pola": dict(title="Pola belajarmu relatif sehat", body="Waktu, durasi, dan fokus belajarmu cukup terjaga. Pertahankan, dan pantau lewat kuisioner berkala.", ref=None),
    "diagnosis": dict(title="Tidak ada masalah utama terdeteksi", body="Dari jawabanmu belum terlihat kebiasaan yang perlu diperbaiki segera.", ref=None),
    "rekomendasi": dict(title="Pertahankan dan tingkatkan", body="Coba variasikan teknik belajar dan isi ulang kuisioner dua minggu lagi untuk melihat perubahannya.", ref=None),
}
DEFAULT_ACTION = "Isi ulang kuisioner dua minggu lagi untuk memantau perkembangan"


def _rule_tags(cfg: dict, value: float) -> dict:
    for rule in cfg.get("rules", []):
        if "lte" not in rule or value <= rule["lte"]:
            return rule.get("tags", {})
    return {}


def _num(val: float):
    return int(val) if val == int(val) else round(val, 2)


def analyze(questions: list, answers: dict[int, str], profil: dict | None = None) -> dict:
    style = {"v": 0, "a": 0, "k": 0}
    c_sum = c_max = 0
    flags: list[str] = []
    facts: dict = {}
    for q in questions:
        raw = answers.get(q.id)
        raw = raw.strip() if isinstance(raw, str) else raw
        if raw in (None, ""):
            if q.required:
                raise ValueError(f"Pertanyaan {q.order} belum dijawab.")
            continue
        cfg = q.config or {}
        key = cfg.get("key")
        tags: dict = {}
        c_possible = 0
        if q.qtype == "choice":
            opt = next((o for o in q.options if o["id"] == raw), None)
            if opt is None:
                raise ValueError(f"Jawaban pertanyaan {q.order} tidak valid.")
            tags = opt["tags"]
            c_possible = max(o["tags"].get("c", 0) for o in q.options)
            if key:
                facts[key] = opt["text"]
        elif q.qtype in ("number", "scale"):
            try:
                val = float(raw)
            except ValueError:
                raise ValueError(f"Jawaban pertanyaan {q.order} harus berupa angka.")
            lo, hi = cfg.get("min"), cfg.get("max")
            if (lo is not None and val < lo) or (hi is not None and val > hi):
                raise ValueError(f"Jawaban pertanyaan {q.order} harus antara {lo} dan {hi}.")
            tags = _rule_tags(cfg, val)
            c_possible = max([r.get("tags", {}).get("c", 0) for r in cfg.get("rules", [])] or [0])
            if key:
                facts[key] = _num(val)
        elif key:  # text
            facts[key] = str(raw)[:200]
        for k in style:
            style[k] += tags.get(k, 0)
        if c_possible > 0:
            c_sum += tags.get("c", 0)
            c_max += c_possible
        f = tags.get("f")
        if f and f not in flags:
            flags.append(f)
    for k, v in (profil or {}).items():  # data dari pendaftaran ikut masuk ringkasan untuk AI
        if v not in (None, ""):
            facts[k] = v
    top = max(style.values())
    winners = [k for k, v in style.items() if v == top]
    style_name = STYLE_NAMES[winners[0]] if top > 0 and len(winners) == 1 else "Campuran"
    consistency = round(c_sum / c_max * 100) if c_max else 0
    return {
        "style": style_name,
        "consistency": consistency,
        "flags": flags,
        "issue_count": len(flags),
        "summary": _summary(style_name, consistency, flags, facts),
        "facts": facts,
    }


def _summary(style: str, consistency: int, flags: list[str], facts: dict) -> str:
    parts = [f"gaya belajar dominan {style}", f"skor konsistensi {consistency}%",
             "masalah terdeteksi: " + (", ".join(FLAG_LABELS[f] for f in flags) or "tidak ada")]
    if "waktu_belajar" in facts:
        parts.append(f"waktu belajar yang paling sering: {facts['waktu_belajar']}")
    if "durasi_harian" in facts:
        parts.append(f"durasi belajar mandiri per hari: {facts['durasi_harian']}")
    if "prodi" in facts:
        parts.append(f"program studi {facts['prodi']}")
    if "semester" in facts:
        parts.append(f"semester {facts['semester']}")
    if "ipk" in facts:
        parts.append(f"IPK {facts['ipk']}")
    if "organisasi" in facts:
        org = f"organisasi: {facts['organisasi']}"
        if "jam_org" in facts:
            org += f", {facts['jam_org']} jam per minggu"
        parts.append(org)
    if "matkul" in facts:
        sulit = f"mata kuliah tersulit: {facts['matkul']}"
        if "kesulitan" in facts:
            sulit += f" (kendala: {facts['kesulitan']})"
        parts.append(sulit)
    if "alasan_tunda" in facts:
        parts.append(f"alasan utama menunda: {facts['alasan_tunda']}")
    if "tujuan" in facts:
        parts.append(f"tujuan belajar: {facts['tujuan']}")
    if "keyakinan" in facts:
        v = facts["keyakinan"]
        parts.append("keyakinan bisa mengubah kebiasaan: " + (f"{v} dari 5" if isinstance(v, (int, float)) else str(v)))
    return "; ".join(parts)


def _first(group: set[str], flags: list[str]) -> str | None:
    return next((f for f in PRIORITY if f in group and f in flags), None)


def _card(kind: str, title: str, body: str, ref: str | None, query: str | None, summary: str) -> dict:
    if not settings.use_builtin_knowledge:
        ref = None  # rujukan hanya boleh berasal dari tabel jurnal, bukan teks bawaan
    if query and settings.openrouter_api_key:
        try:
            body, found = rag.explain(query, title, body, summary)
            ref = found or ref
        except Exception as e:  # tetap beri hasil rule-based jika LLM/embedding gagal
            log.warning("RAG explain gagal: %s", e)
    return {"kind": kind, "title": title, "body": body, "reference": ref}


def build_insights(result: dict) -> tuple[list[dict], list[str]]:
    flags = result["flags"]
    summary = result["summary"]
    cards = []
    pf, df = _first(POLA, flags), _first(DIAG, flags)
    rf = next((f for f in PRIORITY if f in flags), None)
    for kind, f in (("pola", pf), ("diagnosis", df)):
        if f:
            i = INFO[f]
            cards.append(_card(kind, i["title"], i["body"], i["ref"], i["query"], summary))
        else:
            d = DEFAULTS[kind]
            cards.append(_card(kind, d["title"], d["body"], d["ref"], None, summary))
    if rf:
        i = INFO[rf]
        cards.append(_card("rekomendasi", i["reco"][0], i["reco"][1], i["ref"], i["query"], summary))
    else:
        d = DEFAULTS["rekomendasi"]
        cards.append(_card("rekomendasi", d["title"], d["body"], d["ref"], None, summary))
    actions = [INFO[f]["action"] for f in PRIORITY if f in flags][:3] or [DEFAULT_ACTION]
    return cards, actions
