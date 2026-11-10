from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class RegisterIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=6, max_length=72)
    nim: str = ""
    program_studi: str = ""
    angkatan: int | None = None


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    email: EmailStr
    nim: str
    program_studi: str
    angkatan: int | None
    sim_verified: bool
    peran: str = "mahasiswa"
    izin_pantau: bool = False
    created_at: datetime
    submission_count: int = 0


class UserUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    program_studi: str | None = None
    angkatan: int | None = None
    izin_pantau: bool | None = None


class OptionOut(BaseModel):
    id: str
    text: str


class QuestionOut(BaseModel):
    id: int
    order: int
    category: str
    text: str
    qtype: str = "choice"
    required: bool = True
    config: dict = {}
    options: list[OptionOut] = []


class SubmitIn(BaseModel):
    answers: dict[int, str]  # question_id -> option_id


class InsightOut(BaseModel):
    kind: str  # pola | diagnosis | rekomendasi
    title: str
    body: str
    reference: str | None = None


class ActionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    text: str
    done: bool


class DashboardOut(BaseModel):
    has_data: bool
    first_name: str
    submitted_at: datetime | None = None
    style: str | None = None
    consistency: int | None = None
    issue_count: int | None = None
    insights: list[InsightOut] = []
    actions: list[ActionOut] = []


class HistoryItem(BaseModel):
    id: int
    created_at: datetime
    style: str
    consistency: int
    issue_count: int


class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=2000)


class ChatMessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    role: str
    content: str
    source: str | None = None
    created_at: datetime


JAM_POLA = r"^([01]\d|2[0-3]):[0-5]\d$"


def _cek_hari(v: list[int] | None):
    if v is None:
        return v
    if not v or any(h < 1 or h > 7 for h in v):
        raise ValueError("hari harus berisi angka 1 (Senin) sampai 7 (Minggu)")
    return sorted(set(v))


class PengingatIn(BaseModel):
    jam: str = Field(pattern=JAM_POLA)
    hari: list[int]
    durasi_menit: int = Field(default=50, ge=10, le=240)
    pesan: str | None = Field(default=None, max_length=200)
    aktif: bool = True

    @field_validator("hari")
    @classmethod
    def _hari(cls, v):
        return _cek_hari(v)


class PengingatUpdate(BaseModel):
    jam: str | None = Field(default=None, pattern=JAM_POLA)
    hari: list[int] | None = None
    durasi_menit: int | None = Field(default=None, ge=10, le=240)
    pesan: str | None = Field(default=None, max_length=200)
    aktif: bool | None = None

    @field_validator("hari")
    @classmethod
    def _hari(cls, v):
        return _cek_hari(v)


class PengingatOut(BaseModel):
    id: int
    jam: str
    hari: list[int]
    durasi_menit: int
    pesan: str | None = None
    aktif: bool


class SaranOut(BaseModel):
    jam: str
    hari: list[int]
    durasi_menit: int
    pesan: str
    alasan: str


class PushKeys(BaseModel):
    p256dh: str
    auth: str


class PushIn(BaseModel):
    endpoint: str
    keys: PushKeys


class PushOut(BaseModel):
    endpoint: str


class MahasiswaRingkas(BaseModel):
    id: int
    nama: str
    nim: str
    program_studi: str
    angkatan: int | None = None
    izin: bool
    ada_hasil: bool
    terakhir_isi: datetime | None = None
    style: str | None = None
    konsistensi: int | None = None
    issue_count: int | None = None
    tren: int | None = None
    perlu_perhatian: bool = False


class DetailMahasiswa(BaseModel):
    mahasiswa: MahasiswaRingkas
    masalah: list[str]
    insights: list[InsightOut]
    aksi_selesai: int
    aksi_total: int
    riwayat: list[HistoryItem]


class RujukanIn(BaseModel):
    judul: str = Field(min_length=3, max_length=200)
    kategori: str | None = Field(default=None, max_length=80)
    isi: str = Field(min_length=20, max_length=4000)
    aktif: bool = True


class RujukanUpdate(BaseModel):
    judul: str | None = Field(default=None, min_length=3, max_length=200)
    kategori: str | None = Field(default=None, max_length=80)
    isi: str | None = Field(default=None, min_length=20, max_length=4000)
    aktif: bool | None = None


class RujukanOut(BaseModel):
    id: int
    judul: str
    kategori: str | None = None
    isi: str
    aktif: bool
    psikolog: str
    milik_saya: bool
    diubah: datetime

