"use client";
import { BookOpen } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { api, type DetailMhs, type Insight } from "@/lib/api";

const KIND: Record<Insight["kind"], { label: string; cls: string }> = {
  pola: { label: "Pemetaan Pola Belajar", cls: "bg-sky/15 text-sky" },
  diagnosis: { label: "Temuan Masalah", cls: "bg-coral/15 text-coral" },
  rekomendasi: { label: "Rekomendasi Belajar", cls: "bg-accent/15 text-accent" },
};
const tgl = (iso: string) => new Date(iso).toLocaleDateString("id-ID", { day: "numeric", month: "short", year: "numeric" });

export default function DetailMahasiswaPage() {
  const { id } = useParams<{ id: string }>();
  const [d, setD] = useState<DetailMhs | null>(null);
  const [err, setErr] = useState("");

  useEffect(() => { api<DetailMhs>(`/api/pantau/mahasiswa/${id}`).then(setD).catch((e) => setErr(e.message)); }, [id]);

  const kembali = <Link href="/pantau" className="text-xs text-mute hover:text-ink">← Kembali ke daftar</Link>;
  if (err) return <div>{kembali}<p className="mt-3 text-sm text-coral">{err}</p></div>;
  if (!d) return <p className="text-sm text-mute">Memuat…</p>;

  const m = d.mahasiswa;
  const kronologis = [...d.riwayat].reverse();
  return (
    <div className="max-w-4xl">
      {kembali}
      <h1 className="mt-2 text-2xl font-semibold">{m.nama}</h1>
      <p className="text-xs text-mute">{m.nim || "-"} · {m.program_studi || "-"}{m.angkatan ? ` · angkatan ${m.angkatan}` : ""}</p>

      {!m.ada_hasil ? <p className="card mt-5 p-4 text-sm text-mute">Mahasiswa ini belum mengisi kuisioner.</p> : (
        <>
          <div className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-4">
            {[["Gaya belajar", m.style ?? "-", "text-accent"], ["Konsistensi", `${m.konsistensi}%`, "text-mint"],
              ["Masalah", `${m.issue_count} isu`, "text-coral"], ["Rencana aksi", `${d.aksi_selesai}/${d.aksi_total}`, "text-ink"]].map(([l, v, c]) => (
              <div key={l} className="card px-4 py-3"><p className="text-[11px] text-mute">{l}</p><p className={`mt-1 text-xl font-semibold ${c}`}>{v}</p></div>
            ))}
          </div>
          {m.perlu_perhatian && <p className="mt-3 rounded-lg bg-coral/10 px-3 py-2 text-xs text-coral">Ditandai perlu perhatian secara otomatis. Ini penanda awal dari kuisioner, bukan diagnosis.</p>}

          {!!d.masalah.length && (
            <div className="card mt-4 p-4">
              <p className="text-sm font-semibold">Masalah yang terdeteksi</p>
              <div className="mt-2 flex flex-wrap gap-2">{d.masalah.map((x) => <span key={x} className="rounded-md bg-coral/15 px-2 py-1 text-[11px] text-coral">{x}</span>)}</div>
            </div>
          )}

          <div className="card mt-4 p-4">
            <p className="mb-3 text-sm font-semibold">Konsistensi belajar per sesi</p>
            <div className="flex h-32 items-end gap-3 border-b border-line">
              {kronologis.map((r) => (
                <div key={r.id} className="flex h-full flex-1 flex-col items-center justify-end gap-1">
                  <span className="font-mono text-[10px] text-mint">{r.consistency}%</span>
                  <div className="w-full max-w-[40px] rounded-t bg-mint/70" style={{ height: `${Math.max(r.consistency, 4)}%` }} />
                </div>
              ))}
            </div>
            <div className="mt-1.5 flex gap-3">{kronologis.map((r) => <span key={r.id} className="flex-1 text-center font-mono text-[9px] text-mute">{tgl(r.created_at)}</span>)}</div>
          </div>

          <p className="mb-2 mt-5 text-sm font-semibold">Hasil analisis terbaru</p>
          <div className="space-y-3">
            {d.insights.map((i) => (
              <article key={i.title} className="card p-4">
                <span className={`inline-block rounded px-2 py-0.5 font-mono text-[10px] ${KIND[i.kind].cls}`}>{KIND[i.kind].label}</span>
                <h2 className="mt-2 text-[15px] font-semibold">{i.title}</h2>
                <p className="mt-1 text-xs leading-relaxed text-mute">{i.body}</p>
                {i.reference && <p className="mt-3 flex items-center gap-1.5 border-t border-line pt-2.5 font-mono text-[10px] text-mute"><BookOpen size={11} /> Rujukan: {i.reference}</p>}
              </article>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
