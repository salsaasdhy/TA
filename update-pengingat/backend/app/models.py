from datetime import date, datetime

from sqlalchemy import JSON, Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(100))
    nim: Mapped[str] = mapped_column(String(30), default="")
    program_studi: Mapped[str] = mapped_column(String(120), default="")
    angkatan: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sim_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Pertanyaan(Base):
    """Satu baris = satu pertanyaan kuisioner. Bisa diedit langsung di pgAdmin."""
    __tablename__ = "pertanyaan"

    id: Mapped[int] = mapped_column(primary_key=True)
    urutan: Mapped[int] = mapped_column(Integer, index=True)
    kategori: Mapped[str] = mapped_column(String(60), default="Umum", server_default="Umum")
    teks: Mapped[str] = mapped_column(Text)
    tipe: Mapped[str] = mapped_column(String(10), default="pilihan", server_default="pilihan")  # pilihan | angka | teks | skala
    wajib: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))
    aktif: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))  # false = disembunyikan tanpa dihapus
    kunci: Mapped[str | None] = mapped_column(String(30), nullable=True)  # nama data untuk ringkasan AI
    nilai_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    nilai_maks: Mapped[float | None] = mapped_column(Float, nullable=True)
    langkah: Mapped[float | None] = mapped_column(Float, nullable=True)
    satuan: Mapped[str | None] = mapped_column(String(40), nullable=True)
    placeholder: Mapped[str | None] = mapped_column(String(120), nullable=True)
    label_min: Mapped[str | None] = mapped_column(String(40), nullable=True)
    label_maks: Mapped[str | None] = mapped_column(String(40), nullable=True)

    opsi: Mapped[list["OpsiJawaban"]] = relationship(
        back_populates="pertanyaan", cascade="all, delete-orphan", passive_deletes=True,
        order_by="OpsiJawaban.urutan, OpsiJawaban.id")


class OpsiJawaban(Base):
    """Pilihan jawaban (tipe pilihan) atau aturan skor berdasarkan batas atas (tipe angka)."""
    __tablename__ = "opsi_jawaban"

    id: Mapped[int] = mapped_column(primary_key=True)
    pertanyaan_id: Mapped[int] = mapped_column(ForeignKey("pertanyaan.id", ondelete="CASCADE"), index=True)
    urutan: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"))
    teks: Mapped[str | None] = mapped_column(String(255), nullable=True)
    batas_atas: Mapped[float | None] = mapped_column(Float, nullable=True)  # khusus tipe angka
    skor_visual: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"))
    skor_auditori: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"))
    skor_kinestetik: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"))
    skor_konsistensi: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 0-3
    penanda: Mapped[str | None] = mapped_column(String(30), nullable=True)

    pertanyaan: Mapped[Pertanyaan] = relationship(back_populates="opsi")


class Submission(Base):
    __tablename__ = "submissions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    answers: Mapped[dict] = mapped_column(JSON)
    style: Mapped[str] = mapped_column(String(30))
    consistency: Mapped[int] = mapped_column(Integer)
    issue_count: Mapped[int] = mapped_column(Integer)
    flags: Mapped[list] = mapped_column(JSON)
    insights: Mapped[list] = mapped_column(JSON)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    facts: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    actions: Mapped[list["ActionItem"]] = relationship(back_populates="submission", order_by="ActionItem.id")


class ActionItem(Base):
    __tablename__ = "action_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    submission_id: Mapped[int] = mapped_column(ForeignKey("submissions.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    text: Mapped[str] = mapped_column(String(255))
    done: Mapped[bool] = mapped_column(Boolean, default=False)

    submission: Mapped[Submission] = relationship(back_populates="actions")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    role: Mapped[str] = mapped_column(String(10))  # "user" | "assistant"
    content: Mapped[str] = mapped_column(Text)
    source: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Pengingat(Base):
    """Jadwal pengingat belajar. hari = nomor hari ISO dipisah koma (1=Senin ... 7=Minggu)."""
    __tablename__ = "pengingat"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    jam: Mapped[str] = mapped_column(String(5))  # "HH:MM", zona waktu sesuai pengaturan TIMEZONE
    hari: Mapped[str] = mapped_column(String(20), default="1,2,3,4,5", server_default="1,2,3,4,5")
    durasi_menit: Mapped[int] = mapped_column(Integer, default=50, server_default=text("50"))
    pesan: Mapped[str | None] = mapped_column(String(200), nullable=True)
    aktif: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))
    terakhir_kirim: Mapped[date | None] = mapped_column(Date, nullable=True)
    dibuat: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class LanggananPush(Base):
    """Satu baris = satu browser/perangkat yang mengizinkan notifikasi."""
    __tablename__ = "langganan_push"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    endpoint: Mapped[str] = mapped_column(Text, unique=True)
    p256dh: Mapped[str] = mapped_column(String(200))
    auth: Mapped[str] = mapped_column(String(100))
    dibuat: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
