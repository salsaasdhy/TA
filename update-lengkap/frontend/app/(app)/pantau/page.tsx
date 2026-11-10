"use client";
import { AlertTriangle, ArrowDown, ArrowUp } from "lucide-react";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { api, type Mhs } from "@/lib/api";
import { useUser } from "@/lib/auth";

const tgl = (iso: string) => new Date(iso).toLocaleDateString("id-ID", { day: "numeric", month: "short", year: "numeric" });

export default function PantauPage() {
  const { user } = useUser();
  const [rows, setRows] = useState<Mhs[] | null>(null);
  const [q, setQ] = useState("");
  const [hanya, setHanya] = useState(false);
  const [err, setErr] = useState("");

  useEffect(() => { api<Mhs[]>("/api/pantau/mahasiswa").then(setRows).catch((e) => setErr(e.message)); }, []);

  const tampil = useMemo(() => (rows ?? []).filter((r) =>
    (!hanya || r.perlu_perhatian) && `${r.nama} ${r.nim}`.toLowerCase().includes(q.toLowerCase())), [rows, q, hanya]);

  if (err) return <p className="text-sm text-coral">{err}</p>;
  if (!rows) return <p className="text-sm text-mute">Memuat…</p>;

  const stat = [
    ["Mahasiswa", rows.length, "text-ink"],
    ["Perlu perhatian", rows.filter((r) => r.perlu_perhatian).length, "text-coral"],
    ["Belum mengisi", rows.filter((r) => r.izin && !r.ada_hasil).length, "text-accent"],
    ["Belum memberi izin", rows.filter((r) => !r.izin).length, "text-mute"],
  ] as const;

  return (
    <div className="max-w-5xl">
      <p className="eyebrow">Pemantauan mahasiswa</p>
      <h1 className="mt-1 text-2xl font-semibold">{user.peran === "psikolog" ? "Mahasiswa yang memberi izin" : "Mahasiswa perwalian"}</h1>
      <p className="mt-1 text-xs text-mute">
        Tanda &quot;perlu perhatian&quot; dihitung otomatis dari kuisioner (konsistensi di bawah 40%, 4 isu atau lebih, atau stres tinggi). Itu penanda awal, bukan diagnosis.
      </p>

      <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
        {stat.map(([l, n, c]) => (
          <div key={l} className="card px-4 py-3"><p className="text-[11px] text-mute">{l}</p><p className={`mt-1 text-2xl font-semibold ${c}`}>{n}</p></div>
        ))}
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-3">
        <input className="input max-w-xs" placeholder="Cari nama atau NRP" value={q} onChange={(e) => setQ(e.target.value)} />
        <label className="flex items-center gap-2 text-xs text-mute">
          <input type="checkbox" checked={hanya} onChange={(e) => setHanya(e.target.checked)} /> Hanya yang perlu perhatian
        </label>
      </div>

      <div className="card mt-3 divide-y divide-line">
        {!tampil.length && <p className="p-4 text-xs text-mute">Tidak ada mahasiswa yang cocok.</p>}
        {tampil.map((r) => {
          const isi = (
            <div className="flex flex-wrap items-center justify-between gap-x-6 gap-y-2 px-4 py-3">
              <div className="min-w-0">
                <p className="flex items-center gap-2 text-sm font-semibold">
                  {r.nama}
                  {r.perlu_perhatian && <span className="flex items-center gap-1 rounded bg-coral/15 px-1.5 py-0.5 font-mono text-[10px] text-coral"><AlertTriangle size={10} /> perlu perhatian</span>}
                </p>
                <p className="text-[11px] text-mute">{r.nim || "-"} · {r.program_studi || "-"}{r.angkatan ? ` · ${r.angkatan}` : ""}</p>
              </div>
              {!r.izin ? <span className="text-xs text-mute">Belum memberi izin</span>
                : !r.ada_hasil ? <span className="text-xs text-accent">Belum mengisi kuisioner</span>
                : (
                  <div className="flex items-center gap-5 text-xs">
                    <span className="text-accent">{r.style}</span>
                    <span className="flex items-center gap-1 text-mint">{r.konsistensi}%
                      {r.tren !== null && r.tren !== 0 && (r.tren > 0 ? <ArrowUp size={11} /> : <ArrowDown size={11} className="text-coral" />)}
                    </span>
                    <span className="text-coral">{r.issue_count} isu</span>
                    <span className="text-mute">{r.terakhir_isi ? tgl(r.terakhir_isi) : ""}</span>
                  </div>
                )}
            </div>
          );
          return r.izin ? <Link key={r.id} href={`/pantau/${r.id}`} className="block transition hover:bg-card2">{isi}</Link> : <div key={r.id} className="opacity-70">{isi}</div>;
        })}
      </div>
    </div>
  );
}
