"use client";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { api, token } from "@/lib/api";

const TAHUN = new Date().getFullYear();
type Form = { name: string; email: string; password: string; nim: string; program_studi: string; angkatan: string; semester: string };
const DEMO: Form = { name: "", email: "demo@habitcoach.id", password: "demo1234", nim: "", program_studi: "", angkatan: "", semester: "" };
const EMPTY: Form = { ...DEMO, email: "", password: "" };

export default function LoginPage() {
  const router = useRouter();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [f, setF] = useState<Form>(DEMO);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  const set = (k: keyof Form) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
    setF((p) => ({ ...p, [k]: e.target.value }));

  function switchMode() {
    const next = mode === "login" ? "register" : "login";
    setMode(next);
    setF(next === "login" ? DEMO : EMPTY);
    setErr("");
  }

  async function submit(ev: React.FormEvent<HTMLFormElement>) {
    ev.preventDefault();
    setErr("");
    if (mode === "register" && (!f.program_studi.trim() || !f.angkatan || !f.semester)) {
      setErr("Lengkapi program studi, angkatan, dan semester dulu.");
      return;
    }
    setBusy(true);
    try {
      const email = f.email.trim();
      const body = mode === "login"
        ? { email, password: f.password }
        : { name: f.name.trim(), email, password: f.password, nim: f.nim.trim(),
            program_studi: f.program_studi.trim(), angkatan: Number(f.angkatan), semester: Number(f.semester) };
      const res = await api<{ access_token: string }>(`/api/auth/${mode}`, { method: "POST", body: JSON.stringify(body) });
      token.set(res.access_token);
      router.replace("/dashboard");
    } catch (error) {
      setErr(error instanceof Error ? error.message : "Gagal masuk.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid min-h-screen place-items-center px-4 py-8">
      <form onSubmit={submit} className="card w-full max-w-sm space-y-3 p-6">
        <div className="mb-2 flex items-center gap-2.5">
          <div className="grid h-9 w-9 place-items-center rounded-lg bg-accent text-sm font-bold text-[#1a1630]">AH</div>
          <div>
            <h1 className="text-lg font-semibold leading-tight">{mode === "login" ? "Masuk ke Habit Coach" : "Daftar akun mahasiswa"}</h1>
            <p className="text-xs text-mute">{mode === "login" ? "Pahami kebiasaan belajarmu, dibantu AI." : "Datamu dipakai agar pertanyaan dan saran sesuai kondisimu."}</p>
          </div>
        </div>
        {mode === "register" && (
          <>
            <input className="input" placeholder="Nama lengkap" value={f.name} onChange={set("name")} required minLength={2} />
            <input className="input" placeholder="NIM/NRP (opsional)" value={f.nim} onChange={set("nim")} />
            <input className="input" placeholder="Program studi" value={f.program_studi} onChange={set("program_studi")} required />
            <div className="grid grid-cols-2 gap-3">
              <select className="input" value={f.angkatan} onChange={set("angkatan")} required aria-label="Angkatan">
                <option value="">Angkatan</option>
                {Array.from({ length: 11 }, (_, i) => TAHUN - i).map((t) => <option key={t} value={t}>{t}</option>)}
              </select>
              <select className="input" value={f.semester} onChange={set("semester")} required aria-label="Semester saat ini">
                <option value="">Semester</option>
                {Array.from({ length: 14 }, (_, i) => i + 1).map((n) => <option key={n} value={n}>Semester {n}</option>)}
              </select>
            </div>
          </>
        )}
        <input className="input" type="email" autoComplete="email" placeholder="Email" value={f.email} onChange={set("email")} required />
        <input className="input" type="password" autoComplete={mode === "login" ? "current-password" : "new-password"}
          placeholder="Kata sandi (min. 6 karakter)" value={f.password} onChange={set("password")} required minLength={6} maxLength={72} />
        {err && <p role="alert" className="text-xs text-coral">{err}</p>}
        <button className="btn-accent w-full py-2.5" disabled={busy}>
          {busy ? "Memproses…" : mode === "login" ? "Masuk" : "Daftar"}
        </button>
        <button type="button" className="w-full text-xs text-mute hover:text-ink" onClick={switchMode}>
          {mode === "login" ? "Belum punya akun? Daftar" : "Sudah punya akun? Masuk"}
        </button>
      </form>
    </div>
  );
}
