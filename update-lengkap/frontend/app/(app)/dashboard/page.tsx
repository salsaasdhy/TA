"use client";
import { BookOpen, Check } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { api, type Action, type Dashboard, type Insight } from "@/lib/api";

const KIND: Record<Insight["kind"], { label: string; cls: string }> = {
  pola: { label: "Pemetaan Pola Belajar", cls: "bg-sky/15 text-sky" },
  diagnosis: { label: "Diagnosis Masalah", cls: "bg-coral/15 text-coral" },
  rekomendasi: { label: "Rekomendasi Belajar", cls: "bg-accent/15 text-accent" },
};

function Stat({ label, value, cls }: { label: string; value: string; cls: string }) {
  return (
    <div className="card px-4 py-3">
      <p className="text-[11px] text-mute">{label}</p>
      <p className={`mt-1 text-2xl font-semibold ${cls}`}>{value}</p>
    </div>
  );
}

export default function DashboardPage() {
  const [d, setD] = useState<Dashboard | null>(null);
  const [actions, setActions] = useState<Action[]>([]);
  const [err, setErr] = useState("");

  useEffect(() => {
    api<Dashboard>("/api/dashboard").then((r) => { setD(r); setActions(r.actions); }).catch((e) => setErr(e.message));
  }, []);

  async function toggle(id: number) {
    setActions((a) => a.map((x) => (x.id === id ? { ...x, done: !x.done } : x)));
    try { await api(`/api/actions/${id}`, { method: "PATCH" }); }
    catch { setActions((a) => a.map((x) => (x.id === id ? { ...x, done: !x.done } : x))); }
  }

  if (err) return <p className="text-sm text-coral">{err}</p>;
  if (!d) return <p className="text-sm text-mute">Memuat…</p>;

  const date = d.submitted_at
    ? new Date(d.submitted_at).toLocaleDateString("id-ID", { day: "numeric", month: "short", year: "numeric" }).toUpperCase()
    : "";

  return (
    <div className="mx-auto max-w-5xl">
      <div className="mb-5 flex flex-col items-start gap-3 sm:flex-row sm:justify-between sm:gap-4">
        <div>
          <p className="eyebrow">Dashboard{date && ` · diperbarui ${date}`}</p>
          <h1 className="mt-1 text-2xl font-semibold">Halo, {d.first_name} 👋</h1>
          <p className="mt-1 max-w-md text-xs text-mute">
            Berikut hasil analisis kebiasaan belajarmu, disusun dari kuisioner dan referensi ilmiah terverifikasi.
          </p>
        </div>
        <Link href="/kuisioner" className="btn-accent shrink-0">{d.has_data ? "Isi Ulang Kuisioner" : "Mulai Kuisioner"}</Link>
      </div>

      {!d.has_data ? (
        <div className="card p-8 text-center">
          <p className="font-semibold">Belum ada hasil analisis</p>
          <p className="mx-auto mt-1 max-w-sm text-xs text-mute">
            Jawab sekitar 10 pertanyaan singkat untuk melihat gaya belajar, tingkat konsistensi, dan rekomendasi untukmu.
          </p>
          <Link href="/kuisioner" className="btn-accent mt-4 inline-block">Isi kuisioner sekarang</Link>
        </div>
      ) : (
        <>
          <div className="mb-4 grid grid-cols-1 gap-3 sm:grid-cols-3">
            <Stat label="Gaya Belajar Dominan" value={d.style ?? "-"} cls="text-accent" />
            <Stat label="Konsistensi Belajar" value={`${d.consistency}%`} cls="text-mint" />
            <Stat label="Masalah Teridentifikasi" value={`${d.issue_count} isu`} cls="text-coral" />
          </div>
          <div className="grid items-start gap-4 lg:grid-cols-[1.4fr_1fr]">
            <div className="space-y-3">
              {d.insights.map((i) => (
                <article key={i.title} className="card p-4">
                  <span className={`inline-block rounded px-2 py-0.5 font-mono text-[10px] ${KIND[i.kind].cls}`}>{KIND[i.kind].label}</span>
                  <h2 className="mt-2 text-[15px] font-semibold">{i.title}</h2>
                  <p className="mt-1 text-xs leading-relaxed text-mute">{i.body}</p>
                  {i.reference && (
                    <p className="mt-3 flex items-center gap-1.5 border-t border-line pt-2.5 font-mono text-[10px] text-mute">
                      <BookOpen size={11} /> Rujukan: {i.reference}
                    </p>
                  )}
                </article>
              ))}
            </div>
            <div className="space-y-3">
              <div className="card p-4">
                <h2 className="mb-3 text-sm font-semibold">Rencana Aksi Minggu Ini</h2>
                <div className="space-y-2">
                  {actions.map((a) => (
                    <button key={a.id} onClick={() => toggle(a.id)}
                      className={`flex w-full items-center gap-2.5 rounded-lg border px-3 py-2 text-left text-xs transition ${
                        a.done ? "border-accent bg-card2" : "border-line hover:bg-card2"}`}>
                      <span className={`grid h-3.5 w-3.5 shrink-0 place-items-center rounded-full border ${
                        a.done ? "border-accent bg-accent text-[#1a1630]" : "border-mute"}`}>
                        {a.done && <Check size={9} strokeWidth={4} />}
                      </span>
                      <span className={a.done ? "text-ink" : "text-mute"}>{a.text}</span>
                    </button>
                  ))}
                </div>
              </div>
              <div className="card p-4 text-center">
                <h2 className="text-sm font-semibold">Ada yang ingin didiskusikan?</h2>
                <p className="mb-3 mt-1 text-[11px] text-mute">Tanyakan langsung ke AI Habit Coach soal hasil analisis ini.</p>
                <Link href="/chat" className="btn-accent block py-2.5">Mulai Konsultasi →</Link>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
