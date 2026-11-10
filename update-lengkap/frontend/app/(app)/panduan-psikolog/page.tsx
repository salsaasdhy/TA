"use client";
import { Pencil, Trash2 } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { api, type Rujukan } from "@/lib/api";

const KOSONG = { id: 0, judul: "", kategori: "", isi: "", aktif: true };
const tgl = (iso: string) => new Date(iso).toLocaleDateString("id-ID", { day: "numeric", month: "short", year: "numeric" });

export default function PanduanPsikologPage() {
  const [list, setList] = useState<Rujukan[] | null>(null);
  const [f, setF] = useState(KOSONG);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [info, setInfo] = useState("");

  const muat = useCallback(() => api<Rujukan[]>("/api/psikolog/rujukan").then(setList).catch((e) => setErr(e.message)), []);
  useEffect(() => { muat(); }, [muat]);

  async function simpan(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true); setErr(""); setInfo("");
    try {
      const body = JSON.stringify({ judul: f.judul, kategori: f.kategori || null, isi: f.isi, aktif: f.aktif });
      await api(f.id ? `/api/psikolog/rujukan/${f.id}` : "/api/psikolog/rujukan", { method: f.id ? "PATCH" : "POST", body });
      setF(KOSONG);
      setInfo("Tersimpan. Panduan masuk ke pencarian AI dalam beberapa detik.");
      await muat();
    } catch (e2) { setErr(e2 instanceof Error ? e2.message : "Gagal menyimpan."); }
    finally { setBusy(false); }
  }

  async function hapus(r: Rujukan) {
    if (!window.confirm(`Hapus panduan "${r.judul}"?`)) return;
    setErr(""); setInfo("");
    try { await api(`/api/psikolog/rujukan/${r.id}`, { method: "DELETE" }); await muat(); setInfo("Panduan dihapus."); }
    catch (e) { setErr(e instanceof Error ? e.message : "Gagal menghapus."); }
  }

  return (
    <div className="max-w-3xl">
      <p className="eyebrow">Panduan psikolog</p>
      <h1 className="mt-1 text-2xl font-semibold">Rujukan dari psikolog</h1>
      <p className="mt-1 text-xs leading-relaxed text-mute">
        Tulis panduan praktis untuk mahasiswa. Panduan yang aktif dipakai AI Coach bersama jurnal, dan tampil sebagai rujukan &quot;Psikolog &lt;nama&gt;&quot; di dashboard dan chat mahasiswa. Jangan menuliskan data pribadi mahasiswa.
      </p>

      <form onSubmit={simpan} className="card mt-5 space-y-3 p-4">
        <p className="text-sm font-semibold">{f.id ? "Ubah panduan" : "Tambah panduan"}</p>
        <input className="input" placeholder="Judul panduan" required minLength={3} maxLength={200} value={f.judul} onChange={(e) => setF({ ...f, judul: e.target.value })} />
        <input className="input" placeholder="Kategori (opsional), mis. Prokrastinasi, Stres akademik" maxLength={80} value={f.kategori} onChange={(e) => setF({ ...f, kategori: e.target.value })} />
        <textarea className="input min-h-[140px]" placeholder="Isi panduan: apa yang perlu dipahami dan langkah yang bisa dicoba mahasiswa" required minLength={20} maxLength={4000} value={f.isi} onChange={(e) => setF({ ...f, isi: e.target.value })} />
        <label className="flex items-center gap-2 text-xs text-mute"><input type="checkbox" checked={f.aktif} onChange={(e) => setF({ ...f, aktif: e.target.checked })} /> Aktif (dipakai AI Coach)</label>
        <div className="flex gap-2">
          <button className="btn-accent" disabled={busy}>{busy ? "Menyimpan…" : "Simpan"}</button>
          {f.id !== 0 && <button type="button" className="btn-ghost" onClick={() => setF(KOSONG)}>Batal</button>}
        </div>
        {(err || info) && <p className={`text-xs ${err ? "text-coral" : "text-mint"}`} role="status">{err || info}</p>}
      </form>

      <div className="card mt-4 divide-y divide-line">
        {!list ? <p className="p-4 text-xs text-mute">Memuat…</p> : !list.length ? <p className="p-4 text-xs text-mute">Belum ada panduan.</p> : list.map((r) => (
          <div key={r.id} className="flex items-start justify-between gap-3 p-4">
            <div className={`min-w-0 ${r.aktif ? "" : "opacity-50"}`}>
              <p className="text-sm font-semibold">{r.judul}</p>
              <p className="font-mono text-[10px] text-mute">{r.psikolog}{r.kategori ? ` · ${r.kategori}` : ""} · {tgl(r.diubah)}{r.aktif ? "" : " · nonaktif"}</p>
              <p className="mt-1.5 line-clamp-3 whitespace-pre-wrap text-xs leading-relaxed text-mute">{r.isi}</p>
            </div>
            {r.milik_saya && (
              <div className="flex shrink-0 gap-3 text-mute">
                <button aria-label="Ubah" className="transition hover:text-ink" onClick={() => { setF({ id: r.id, judul: r.judul, kategori: r.kategori ?? "", isi: r.isi, aktif: r.aktif }); window.scrollTo({ top: 0, behavior: "smooth" }); }}><Pencil size={14} /></button>
                <button aria-label="Hapus" className="transition hover:text-coral" onClick={() => hapus(r)}><Trash2 size={14} /></button>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
