"use client";
import { Bell, X } from "lucide-react";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { api, type Notif } from "@/lib/api";
import { useUser } from "@/lib/auth";

const BATAS_SIMPAN = 200;
const TITIK: Record<Notif["tipe"], string> = { sekarang: "bg-accent", saran: "bg-sky", info: "bg-mute" };

export default function NotifikasiBell() {
  const { user } = useUser();
  const router = useRouter();
  const simpanKey = `hc_notif_dibaca_${user.id}`;
  const [items, setItems] = useState<Notif[]>([]);
  const [dibaca, setDibaca] = useState<string[]>([]);
  const [buka, setBuka] = useState(false);
  const [toast, setToast] = useState<Notif[]>([]);
  const dibacaRef = useRef<string[]>([]);
  const sudahToast = useRef<Set<string>>(new Set());
  const pertama = useRef(true);
  const wadah = useRef<HTMLDivElement>(null);

  const muat = useCallback(async () => {
    try {
      const data = await api<Notif[]>("/api/notifications");
      setItems(data);
      const awal = pertama.current;
      pertama.current = false;
      const baru = data.filter((n) => !dibacaRef.current.includes(n.key) && !sudahToast.current.has(n.key));
      const tampil: Notif[] = baru.filter((n) => n.tipe === "sekarang");
      const lain = baru.filter((n) => n.tipe !== "sekarang");
      if (awal && lain.length) {  // saat baru login: satu ringkasan, bukan banyak popup
        tampil.push(lain.length === 1 ? lain[0]
          : { key: "ringkasan", tipe: "info", judul: `Kamu punya ${lain.length} notifikasi`, isi: lain.map((n) => n.judul).join(" · "), href: null });
      }
      baru.forEach((n) => sudahToast.current.add(n.key));
      if (!tampil.length) return;
      setToast((t) => [...t, ...tampil]);
      tampil.forEach((n) => setTimeout(() => setToast((t) => t.filter((x) => x.key !== n.key)), 9000));
    } catch { /* bel tetap tampil tanpa isi */ }
  }, []);

  useEffect(() => {
    try { dibacaRef.current = JSON.parse(localStorage.getItem(simpanKey) ?? "[]"); } catch { dibacaRef.current = []; }
    setDibaca(dibacaRef.current);
    muat();
    const t = setInterval(muat, 60000);
    window.addEventListener("focus", muat);
    return () => { clearInterval(t); window.removeEventListener("focus", muat); };
  }, [muat, simpanKey]);

  useEffect(() => {
    if (!buka) return;
    const klik = (e: MouseEvent) => { if (wadah.current && !wadah.current.contains(e.target as Node)) setBuka(false); };
    const esc = (e: KeyboardEvent) => { if (e.key === "Escape") setBuka(false); };
    document.addEventListener("mousedown", klik);
    document.addEventListener("keydown", esc);
    return () => { document.removeEventListener("mousedown", klik); document.removeEventListener("keydown", esc); };
  }, [buka]);

  function tandai(keys: string[]) {
    const gabung = Array.from(new Set([...dibacaRef.current, ...keys])).slice(-BATAS_SIMPAN);
    dibacaRef.current = gabung;
    setDibaca(gabung);
    try { localStorage.setItem(simpanKey, JSON.stringify(gabung)); } catch { /* penyimpanan penuh atau dimatikan */ }
  }

  function bukaItem(n: Notif) {
    tandai([n.key]);
    setBuka(false);
    setToast((t) => t.filter((x) => x.key !== n.key));
    if (n.href) router.push(n.href);
  }

  const belumBaca = items.filter((n) => !dibaca.includes(n.key));

  return (
    <>
      <div ref={wadah} className="relative">
        <button aria-label={`Notifikasi, ${belumBaca.length} belum dibaca`} aria-expanded={buka} onClick={() => setBuka((b) => !b)}
          className="relative grid h-9 w-9 place-items-center rounded-lg text-mute transition hover:bg-card hover:text-ink">
          <Bell size={18} />
          {belumBaca.length > 0 && (
            <span className="absolute -right-0.5 -top-0.5 grid h-4 min-w-4 place-items-center rounded-full bg-coral px-1 font-mono text-[9px] font-bold text-white">
              {belumBaca.length}
            </span>
          )}
        </button>
        {buka && (
          <div className="card absolute right-0 z-40 mt-2 max-h-96 w-80 max-w-[calc(100vw-2rem)] overflow-y-auto shadow-xl">
            <div className="flex items-center justify-between border-b border-line px-4 py-2.5">
              <p className="text-sm font-semibold">Notifikasi</p>
              {belumBaca.length > 0 && <button className="text-[11px] text-accent hover:underline" onClick={() => tandai(items.map((n) => n.key))}>Tandai semua dibaca</button>}
            </div>
            {!items.length ? <p className="px-4 py-6 text-center text-xs text-mute">Belum ada notifikasi.</p> : (
              <ul className="divide-y divide-line">
                {items.map((n) => {
                  const baru = !dibaca.includes(n.key);
                  return (
                    <li key={n.key}>
                      <button onClick={() => bukaItem(n)} className="flex w-full items-start gap-3 px-4 py-3 text-left transition hover:bg-card2">
                        <span className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${baru ? TITIK[n.tipe] : "bg-line"}`} />
                        <span className="min-w-0">
                          <span className={`block text-xs ${baru ? "font-semibold text-ink" : "text-mute"}`}>{n.judul}</span>
                          <span className="mt-0.5 block text-[11px] leading-relaxed text-mute">{n.isi}</span>
                        </span>
                      </button>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
        )}
      </div>

      <div className="pointer-events-none fixed right-4 top-16 z-50 flex w-[min(22rem,calc(100vw-2rem))] flex-col gap-2" aria-live="polite">
        {toast.map((n) => (
          <div key={n.key} role="status"
            className={`card pointer-events-auto flex items-start gap-3 p-3 shadow-xl ${n.tipe === "sekarang" ? "border-accent" : ""}`}>
            <button className="min-w-0 flex-1 text-left" onClick={() => bukaItem(n)}>
              <span className="block text-sm font-semibold">{n.judul}</span>
              <span className="mt-0.5 block text-xs leading-relaxed text-mute">{n.isi}</span>
            </button>
            <button aria-label="Tutup" className="text-mute transition hover:text-ink" onClick={() => setToast((t) => t.filter((x) => x.key !== n.key))}><X size={14} /></button>
          </div>
        ))}
      </div>
    </>
  );
}
