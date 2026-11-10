const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";
const KEY = "hc_token";

export const token = {
  get: () => (typeof window === "undefined" ? null : localStorage.getItem(KEY)),
  set: (t: string) => localStorage.setItem(KEY, t),
  clear: () => localStorage.removeItem(KEY),
};

export type User = {
  id: number; name: string; email: string; nim: string; program_studi: string;
  angkatan: number | null; sim_verified: boolean; created_at: string; submission_count: number;
  peran: "mahasiswa" | "dosen_wali" | "psikolog"; izin_pantau: boolean;
};
export type Option = { id: string; text: string };
export type QConfig = { min?: number; max?: number; step?: number; unit?: string; placeholder?: string; labels?: string[] };
export type Question = {
  id: number; order: number; category: string; text: string;
  qtype: "choice" | "number" | "text" | "scale"; required: boolean; config: QConfig; options: Option[];
};
export type Insight = { kind: "pola" | "diagnosis" | "rekomendasi"; title: string; body: string; reference: string | null };
export type Action = { id: number; text: string; done: boolean };
export type Dashboard = {
  has_data: boolean; first_name: string; submitted_at: string | null; style: string | null;
  consistency: number | null; issue_count: number | null; insights: Insight[]; actions: Action[];
};
export type HistoryItem = { id: number; created_at: string; style: string; consistency: number; issue_count: number };
export type ChatMsg = { id: number; role: "user" | "assistant"; content: string; source: string | null; created_at: string };

export type Pengingat = { id: number; jam: string; hari: number[]; durasi_menit: number; pesan: string | null; aktif: boolean };
export type SaranPengingat = { jam: string; hari: number[]; durasi_menit: number; pesan: string; alasan: string };

export type Mhs = {
  id: number; nama: string; nim: string; program_studi: string; angkatan: number | null; izin: boolean; ada_hasil: boolean;
  terakhir_isi: string | null; style: string | null; konsistensi: number | null; issue_count: number | null;
  tren: number | null; perlu_perhatian: boolean;
};
export type DetailMhs = { mahasiswa: Mhs; masalah: string[]; insights: Insight[]; aksi_selesai: number; aksi_total: number; riwayat: HistoryItem[] };
export type Rujukan = { id: number; judul: string; kategori: string | null; isi: string; aktif: boolean; psikolog: string; milik_saya: boolean; diubah: string };

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const t = token.get();
  let res: Response;
  try {
    res = await fetch(`${BASE}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...(t ? { Authorization: `Bearer ${t}` } : {}), ...init.headers },
    });
  } catch {
    throw new Error(`Tidak bisa terhubung ke server (${BASE}). Pastikan backend berjalan.`);
  }
  if (res.status === 401 && !path.startsWith("/api/auth/login")) {
    token.clear();
    if (typeof window !== "undefined") window.location.href = "/login";
  }
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    const d = data.detail;
    const msg = typeof d === "string" ? d
      : Array.isArray(d) ? d.map((x: { msg?: string }) => x.msg).filter(Boolean).join("; ")
      : "";
    throw new Error(msg || `Server menjawab error ${res.status}. Cek jendela backend.`);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export const initials = (name: string) =>
  name.split(" ").filter(Boolean).slice(0, 2).map((s) => s[0]).join("").toUpperCase();
