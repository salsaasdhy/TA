"use client";
import { Bell, BellOff, Plus, Send, Sparkles, Trash2 } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { api, type Pengingat, type SaranPengingat } from "@/lib/api";
import { aktifkanPush, langgananSaatIni, matikanPush, pushDidukung } from "@/lib/push";

const HARI = [
  { n: 1, s: "Sen" }, { n: 2, s: "Sel" }, { n: 3, s: "Rab" }, { n: 4, s: "Kam" },
  { n: 5, s: "Jum" }, { n: 6, s: "Sab" }, { n: 7, s: "Min" },
];

function HariChips({ value, onChange }: { value: number[]; onChange?: (v: number[]) => void }) {
  return (
    <div className="flex flex-wrap gap-1">
      {HARI.map((h) => {
        const on = value.includes(h.n);
        const cls = `rounded-md px-2 py-1 font-mono text-[10px] ${on ? "bg-accent text-[#1a1630]" : "bg-card2 text-mute"}`;
        return onChange ? (
          <button key={h.n} type="button" aria-pressed={on} className={`${cls} transition hover:brightness-110`}
            onClick={() => onChange(on ? value.filter((x) => x !== h.n) : [...value, h.n].sort())}>
            {h.s}
          </button>
        ) : (
          <span key={h.n} className={cls}>{h.s}</span>
        );
      })}
    </div>
  );
}

export default function PengingatPage() {
  const [list, setList] = useState<Pengingat[]>([]);
  const [saran, setSaran] = useState<SaranPengingat | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [didukung, setDidukung] = useState(true);
  const [pushOn, setPushOn] = useState(false);
  const [info, setInfo] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const [f, setF] = useState({ jam: "16:00", hari: [1, 2, 3, 4, 5] as number[], durasi: 50, pesan: "" });

  const muat = useCallback(async () => {
    try {
      const [l, s] = await Promise.all([
        api<Pengingat[]>("/api/reminders"),
        api<SaranPengingat | null>("/api/reminders/suggestion"),
      ]);
      setList(l);
      setSaran(s);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Gagal memuat pengingat.");
    } finally {
      setLoaded(true);
    }
  }, []);

  useEffect(() => {
    muat();
    const ok = pushDidukung();
    setDidukung(ok);
    if (ok) {
      langgananSaatIni()
        .then((s) => setPushOn(!!s && Notification.permission === "granted"))
        .catch(() => {});
    }
  }, [muat]);

  async function aksi(fn: () => Promise<void>) {
    setBusy(true); setErr(""); setInfo("");
    try { await fn(); }
    catch (e) { setErr(e instanceof Error ? e.message : "Terjadi kesalahan."); }
    finally { setBusy(false); }
  }

  const buat = (body: { jam: string; hari: number[]; durasi_menit: number; pesan: string | null }) =>
    aksi(async () => {
      if (!body.hari.length) throw new Error("Pilih minimal satu hari.");
      await api("/api/reminders", { method: "POST", body: JSON.stringify(body) });
      await muat();
    });
  const toggle = (p: Pengingat) =>
    aksi(async () => {
      await api(`/api/reminders/${p.id}`, { method: "PATCH", body: JSON.stringify({ aktif: !p.aktif }) });
      await muat();
    });
  const hapus = (p: Pengingat) =>
    aksi(async () => { await api(`/api/reminders/${p.id}`, { method: "DELETE" }); await muat(); });

  const nyalakan = () => aksi(async () => { await aktifkanPush(); setPushOn(true); setInfo("Notifikasi aktif di perangkat ini."); });
  const matikan = () => aksi(async () => { await matikanPush(); setPushOn(false); setInfo("Notifikasi dimatikan di perangkat ini."); });
  const uji = () => aksi(async () => {
    const r = await api<{ terkirim: number }>("/api/push/test", { method: "POST" });
    setInfo(`Notifikasi uji terkirim ke ${r.terkirim} perangkat. Lihat pojok layar.`);
  });

  const saranSudahDipakai = saran
    ? list.some((p) => p.jam === saran.jam && p.hari.join() === saran.hari.join())
    : false;

  return (
    <div className="max-w-3xl">
      <p className="eyebrow">Pengingat belajar</p>
      <h1 className="mt-1 text-2xl font-semibold">Kapan kamu mau diingatkan belajar?</h1>
      <p className="mt-1 text-xs text-mute">
        Atur jam belajar yang cocok denganmu. Pengingat muncul sebagai notifikasi di perangkat yang kamu izinkan.
      </p>

      <div className="card mt-5 flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between sm:gap-4">
        <div className="flex items-start gap-3">
          {pushOn ? <Bell size={18} className="mt-0.5 text-mint" /> : <BellOff size={18} className="mt-0.5 text-mute" />}
          <div>
            <p className="text-sm font-semibold">Notifikasi di perangkat ini: {pushOn ? "aktif" : "belum aktif"}</p>
            <p className="mt-0.5 text-[11px] text-mute">
              {didukung
                ? "Browser akan meminta izin saat kamu mengaktifkannya. Backend harus berjalan agar pengingat terkirim."
                : "Browser ini belum mendukung notifikasi push. Coba Chrome, Edge, atau Firefox."}
            </p>
          </div>
        </div>
        {didukung && (
          <div className="flex shrink-0 gap-2">
            {pushOn && <button className="btn-ghost flex items-center gap-1.5" disabled={busy} onClick={uji}><Send size={12} /> Uji</button>}
            {pushOn
              ? <button className="btn-ghost" disabled={busy} onClick={matikan}>Matikan</button>
              : <button className="btn-accent" disabled={busy} onClick={nyalakan}>Aktifkan</button>}
          </div>
        )}
      </div>

      {(err || info) && <p className={`mt-3 text-xs ${err ? "text-coral" : "text-mint"}`} role="status">{err || info}</p>}

      {loaded && (
        <div className="card mt-4 p-4">
          <p className="flex items-center gap-1.5 text-sm font-semibold"><Sparkles size={14} className="text-accent" /> Saran jadwal untukmu</p>
          {saran ? (
            <div className="mt-3">
              <div className="flex flex-wrap items-center gap-3">
                <span className="text-xl font-semibold">{saran.jam}</span>
                <HariChips value={saran.hari} />
                <span className="text-xs text-mute">{saran.durasi_menit} menit</span>
              </div>
              <p className="mt-2 text-xs leading-relaxed text-mute">{saran.alasan}</p>
              <button className="btn-accent mt-3" disabled={busy || saranSudahDipakai}
                onClick={() => buat({ jam: saran.jam, hari: saran.hari, durasi_menit: saran.durasi_menit, pesan: saran.pesan })}>
                {saranSudahDipakai ? "Sudah dipakai" : "Pakai saran ini"}
              </button>
            </div>
          ) : (
            <p className="mt-2 text-xs text-mute">
              Isi <Link href="/kuisioner" className="text-accent underline">kuisioner</Link> dulu supaya jam belajar yang disarankan sesuai kebiasaanmu.
            </p>
          )}
        </div>
      )}

      <div className="card mt-4 p-4">
        <p className="text-sm font-semibold">Pengingatmu</p>
        {!loaded ? <p className="mt-2 text-xs text-mute">Memuat…</p> : !list.length ? (
          <p className="mt-2 text-xs text-mute">Belum ada pengingat. Pakai saran di atas atau tambahkan sendiri di bawah.</p>
        ) : (
          <div className="mt-3 divide-y divide-line">
            {list.map((p) => (
              <div key={p.id} className="flex items-center justify-between gap-3 py-3">
                <div className={p.aktif ? "" : "opacity-50"}>
                  <div className="flex flex-wrap items-center gap-3">
                    <span className="text-lg font-semibold">{p.jam}</span>
                    <HariChips value={p.hari} />
                    <span className="text-xs text-mute">{p.durasi_menit} menit</span>
                  </div>
                  {p.pesan && <p className="mt-1 text-[11px] text-mute">{p.pesan}</p>}
                </div>
                <div className="flex shrink-0 items-center gap-3">
                  <button role="switch" aria-checked={p.aktif} aria-label="Aktifkan pengingat" disabled={busy} onClick={() => toggle(p)}
                    className={`h-5 w-9 rounded-full p-0.5 transition ${p.aktif ? "bg-mint" : "bg-card2"}`}>
                    <span className={`block h-4 w-4 rounded-full bg-white transition ${p.aktif ? "translate-x-4" : ""}`} />
                  </button>
                  <button aria-label="Hapus pengingat" disabled={busy} onClick={() => hapus(p)} className="text-mute transition hover:text-coral">
                    <Trash2 size={15} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <form className="card mt-4 space-y-3 p-4" onSubmit={(e) => {
        e.preventDefault();
        buat({ jam: f.jam, hari: f.hari, durasi_menit: f.durasi, pesan: f.pesan.trim() || null });
      }}>
        <p className="flex items-center gap-1.5 text-sm font-semibold"><Plus size={14} /> Tambah pengingat sendiri</p>
        <div className="flex flex-wrap items-center gap-3">
          <input className="input w-32" type="time" required value={f.jam} onChange={(e) => setF({ ...f, jam: e.target.value })} />
          <div className="flex items-center gap-2">
            <input className="input w-20" type="number" min={10} max={240} step={5} value={f.durasi}
              onChange={(e) => setF({ ...f, durasi: Number(e.target.value) })} />
            <span className="text-xs text-mute">menit</span>
          </div>
        </div>
        <HariChips value={f.hari} onChange={(hari) => setF({ ...f, hari })} />
        <input className="input" maxLength={200} placeholder="Pesan pengingat (opsional)" value={f.pesan}
          onChange={(e) => setF({ ...f, pesan: e.target.value })} />
        <button className="btn-accent" disabled={busy}>Simpan pengingat</button>
      </form>
    </div>
  );
}
