"use client";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api, type Question } from "@/lib/api";
import { useUser } from "@/lib/auth";

export default function KuisionerPage() {
  const router = useRouter();
  const { refresh } = useUser();
  const [qs, setQs] = useState<Question[]>([]);
  const [i, setI] = useState(0);
  const [answers, setAnswers] = useState<Record<number, string>>({});
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  useEffect(() => {
    api<Question[]>("/api/questions").then(setQs).catch((e) => setErr(e.message));
  }, []);

  if (err && !qs.length) return <p className="text-sm text-coral">{err}</p>;
  if (!qs.length) return <p className="text-sm text-mute">Memuat…</p>;

  const q = qs[i];
  const cfg = q.config ?? {};
  const last = i === qs.length - 1;
  const value = answers[q.id] ?? "";
  const answered = value.trim() !== "";

  let valid = true;
  if (answered && (q.qtype === "number" || q.qtype === "scale")) {
    const n = Number(value);
    valid = !Number.isNaN(n) && (cfg.min === undefined || n >= cfg.min) && (cfg.max === undefined || n <= cfg.max);
  }
  const canNext = valid && (answered || !q.required);

  function setAnswer(v: string) {
    setAnswers((prev) => {
      const next = { ...prev };
      if (v.trim() === "") delete next[q.id];
      else next[q.id] = v;
      return next;
    });
  }

  async function finish() {
    setBusy(true); setErr("");
    try {
      await api("/api/questionnaire/submit", { method: "POST", body: JSON.stringify({ answers }) });
      await refresh();
      router.push("/dashboard");
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Gagal mengirim jawaban.");
      setBusy(false);
    }
  }

  const scaleValues: number[] = [];
  if (q.qtype === "scale") for (let n = cfg.min ?? 1; n <= (cfg.max ?? 5); n++) scaleValues.push(n);

  return (
    <div className="max-w-[520px]">
      <p className="eyebrow">Kuisioner kebiasaan belajar</p>
      <h1 className="mt-1 text-2xl font-semibold">Ceritakan kebiasaan belajarmu</h1>
      <p className="mt-1 text-xs text-mute">Jawabanmu dipakai untuk memetakan pola belajar dan menyusun rekomendasi yang sesuai kondisimu.</p>

      <div className="my-4 flex items-center gap-3">
        <div className="h-1 flex-1 overflow-hidden rounded bg-card2">
          <div className="h-full bg-accent transition-all" style={{ width: `${((i + 1) / qs.length) * 100}%` }} />
        </div>
        <span className="font-mono text-[10px] text-mute">{i + 1} / {qs.length}</span>
      </div>

      <div className="card p-5">
        <p className="font-mono text-[10px] uppercase tracking-widest text-mint">
          {q.category}{!q.required && " · opsional"}
        </p>
        <h2 className="mb-4 mt-1.5 text-lg font-semibold leading-snug">{q.text}</h2>

        {q.qtype === "choice" && (
          <div role="radiogroup" className="space-y-2">
            {q.options.map((o) => {
              const on = value === o.id;
              return (
                <button key={o.id} role="radio" aria-checked={on} onClick={() => setAnswer(on && !q.required ? "" : o.id)}
                  className={`flex w-full items-center gap-3 rounded-lg border px-3 py-2.5 text-left text-xs transition ${
                    on ? "border-accent bg-card2" : "border-line hover:bg-card2"}`}>
                  <span className={`grid h-3.5 w-3.5 shrink-0 place-items-center rounded-full border ${on ? "border-accent" : "border-mute"}`}>
                    {on && <span className="h-1.5 w-1.5 rounded-full bg-accent" />}
                  </span>
                  {o.text}
                </button>
              );
            })}
          </div>
        )}

        {q.qtype === "number" && (
          <div>
            <div className="flex items-center gap-2">
              <input className="input max-w-[160px]" type="number" inputMode="decimal" value={value}
                min={cfg.min} max={cfg.max} step={cfg.step ?? 1} placeholder={cfg.placeholder}
                onChange={(e) => setAnswer(e.target.value)} />
              {cfg.unit && <span className="text-xs text-mute">{cfg.unit}</span>}
            </div>
            {!valid && <p className="mt-2 text-[11px] text-coral">Isi angka antara {cfg.min} dan {cfg.max}.</p>}
          </div>
        )}

        {q.qtype === "text" && (
          <input className="input" type="text" maxLength={200} value={value}
            placeholder={cfg.placeholder} onChange={(e) => setAnswer(e.target.value)} />
        )}

        {q.qtype === "scale" && (
          <div>
            <div className="flex gap-2">
              {scaleValues.map((n) => {
                const on = value === String(n);
                return (
                  <button key={n} onClick={() => setAnswer(String(n))} aria-pressed={on}
                    className={`h-11 flex-1 rounded-lg border text-sm font-semibold transition ${
                      on ? "border-accent bg-accent text-[#1a1630]" : "border-line hover:bg-card2"}`}>
                    {n}
                  </button>
                );
              })}
            </div>
            {cfg.labels && (
              <div className="mt-1.5 flex justify-between text-[10px] text-mute">
                <span>{cfg.labels[0]}</span><span>{cfg.labels[1]}</span>
              </div>
            )}
          </div>
        )}
      </div>

      {err && <p className="mt-3 text-xs text-coral">{err}</p>}
      <div className="mt-3 flex justify-between">
        <button className="btn-ghost" disabled={i === 0 || busy} onClick={() => setI(i - 1)}>← Sebelumnya</button>
        {last
          ? <button className="btn-accent" disabled={!canNext || busy} onClick={finish}>{busy ? "Menganalisis…" : "Selesai & Analisis"}</button>
          : <button className="btn-accent" disabled={!canNext} onClick={() => setI(i + 1)}>
              {!answered && !q.required ? "Lewati →" : "Selanjutnya →"}
            </button>}
      </div>
    </div>
  );
}
