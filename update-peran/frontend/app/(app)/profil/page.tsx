"use client";
import { useState } from "react";
import { api, initials } from "@/lib/api";
import { useUser } from "@/lib/auth";

export default function ProfilPage() {
  const { user, refresh } = useUser();
  const [edit, setEdit] = useState(false);
  const [f, setF] = useState({ name: user.name, program_studi: user.program_studi, angkatan: String(user.angkatan ?? "") });
  const [err, setErr] = useState("");

  async function ubahIzin(izin: boolean) {
    setErr("");
    try {
      await api("/api/auth/me", { method: "PATCH", body: JSON.stringify({ izin_pantau: izin }) });
      await refresh();
    } catch (e) { setErr(e instanceof Error ? e.message : "Gagal menyimpan pengaturan."); }
  }

  async function save() {
    setErr("");
    try {
      await api("/api/auth/me", { method: "PATCH", body: JSON.stringify({ name: f.name, program_studi: f.program_studi, angkatan: f.angkatan ? Number(f.angkatan) : null }) });
      await refresh();
      setEdit(false);
    } catch (e) { setErr(e instanceof Error ? e.message : "Gagal menyimpan."); }
  }

  const rows: [string, React.ReactNode][] = [
    ["Program Studi", edit ? <input className="input w-40 py-1 sm:w-64" value={f.program_studi} onChange={(e) => setF({ ...f, program_studi: e.target.value })} /> : user.program_studi || "-"],
    ["Angkatan", edit ? <input className="input w-24 py-1" inputMode="numeric" value={f.angkatan} onChange={(e) => setF({ ...f, angkatan: e.target.value })} /> : user.angkatan ?? "-"],
    ["Status SIM", user.sim_verified ? <span className="text-mint">✓ Terverifikasi</span> : <span className="text-mute">Belum terverifikasi</span>],
    ["Kuisioner Terisi", `${user.submission_count} sesi`],
    ["Bergabung Sejak", new Date(user.created_at).toLocaleDateString("id-ID", { month: "long", year: "numeric" })],
  ];

  return (
    <div className="max-w-3xl">
      <p className="eyebrow">Akun saya</p>
      <h1 className="mt-1 text-2xl font-semibold">Profil Mahasiswa</h1>
      <p className="mt-1 text-xs text-mute">Data ini disinkronkan dari Sistem Informasi Manajemen (SIM) Perguruan Tinggi.</p>

      {user.peran === "mahasiswa" && (
        <div className="card mt-5 flex items-start justify-between gap-4 p-4">
          <div>
            <p className="text-sm font-semibold">Izinkan dosen wali dan psikolog memantau hasilku</p>
            <p className="mt-1 text-xs leading-relaxed text-mute">
              Jika aktif, mereka bisa melihat gaya belajar, konsistensi, masalah yang terdeteksi, dan rencana aksimu. Isi chat dan jawaban mentah kuisioner tidak pernah dibagikan. Kamu bisa mematikannya kapan saja.
            </p>
          </div>
          <button role="switch" aria-checked={user.izin_pantau} aria-label="Izin pemantauan" onClick={() => ubahIzin(!user.izin_pantau)}
            className={`mt-0.5 h-5 w-9 shrink-0 rounded-full p-0.5 transition ${user.izin_pantau ? "bg-mint" : "bg-card2"}`}>
            <span className={`block h-4 w-4 rounded-full bg-white transition ${user.izin_pantau ? "translate-x-4" : ""}`} />
          </button>
        </div>
      )}

      <div className="mt-5 grid items-start gap-4 sm:grid-cols-[200px_1fr]">
        <div className="card flex flex-col items-center p-5 text-center">
          <div className="grid h-14 w-14 place-items-center rounded-xl bg-gradient-to-br from-accent to-mint text-lg font-bold text-[#1a1630]">{initials(user.name)}</div>
          {edit
            ? <input className="input mt-3 py-1 text-center text-xs" value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} />
            : <p className="mt-3 text-sm font-semibold">{user.name}</p>}
          <p className="font-mono text-[10px] text-mute">NRP {user.nim || "-"}</p>
          {edit ? (
            <div className="mt-3 flex w-full gap-2">
              <button className="btn-accent flex-1" onClick={save}>Simpan</button>
              <button className="btn-ghost flex-1" onClick={() => setEdit(false)}>Batal</button>
            </div>
          ) : <button className="btn-ghost mt-3 w-full" onClick={() => setEdit(true)}>Edit Profil</button>}
          {err && <p className="mt-2 text-[11px] text-coral">{err}</p>}
        </div>
        <div className="card divide-y divide-line px-4">
          {rows.map(([k, v]) => (
            <div key={k} className="flex items-center justify-between gap-3 py-3 text-xs">
              <span className="text-mute">{k}</span>
              <span className="font-semibold">{v}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
