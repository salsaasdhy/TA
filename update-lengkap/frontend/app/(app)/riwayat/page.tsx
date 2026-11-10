"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { api, type HistoryItem } from "@/lib/api";

const fmt = (iso: string) => new Date(iso).toLocaleDateString("id-ID", { day: "numeric", month: "short", year: "numeric" });

export default function RiwayatPage() {
  const [rows, setRows] = useState<HistoryItem[] | null>(null);
  useEffect(() => { api<HistoryItem[]>("/api/history").then(setRows).catch(() => setRows([])); }, []);

  if (!rows) return <p className="text-sm text-mute">Memuat…</p>;
  const chrono = [...rows].reverse();

  return (
    <div className="max-w-3xl">
      <p className="eyebrow">Riwayat & progres</p>
      <h1 className="mt-1 text-2xl font-semibold">Perkembangan kebiasaan belajarmu</h1>
      <p className="mt-1 text-xs text-mute">Bandingkan hasil tiap sesi kuisioner untuk melihat apakah konsistensimu membaik.</p>

      {!rows.length ? (
        <div className="card mt-5 p-8 text-center">
          <p className="text-sm font-semibold">Belum ada riwayat</p>
          <p className="mt-1 text-xs text-mute">Hasil akan muncul setelah kamu menyelesaikan kuisioner pertama.</p>
          <Link href="/kuisioner" className="btn-accent mt-4 inline-block">Isi kuisioner</Link>
        </div>
      ) : (
        <>
          <div className="card mt-5 p-4">
            <h2 className="mb-3 text-sm font-semibold">Konsistensi belajar per sesi</h2>
            <div className="flex h-36 items-end gap-3 border-b border-line">
              {chrono.map((r) => (
                <div key={r.id} className="flex h-full flex-1 flex-col items-center justify-end gap-1">
                  <span className="font-mono text-[10px] text-mint">{r.consistency}%</span>
                  <div className="w-full max-w-[44px] rounded-t bg-mint/70" style={{ height: `${Math.max(r.consistency, 4)}%` }} />
                </div>
              ))}
            </div>
            <div className="mt-1.5 flex gap-3">
              {chrono.map((r) => (
                <span key={r.id} className="flex-1 text-center font-mono text-[9px] text-mute">{fmt(r.created_at)}</span>
              ))}
            </div>
          </div>
          <div className="card mt-4 divide-y divide-line">
            {rows.map((r) => (
              <div key={r.id} className="flex flex-wrap items-center justify-between gap-x-4 gap-y-1 px-4 py-3 text-xs">
                <span className="text-ink">{fmt(r.created_at)}</span>
                <span className="text-accent">{r.style}</span>
                <span className="text-mint">{r.consistency}% konsisten</span>
                <span className="text-coral">{r.issue_count} isu</span>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
