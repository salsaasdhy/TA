"use client";
import { Send } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { api, type ChatMsg } from "@/lib/api";
import { useUser } from "@/lib/auth";

export default function ChatPage() {
  const { user } = useUser();
  const [msgs, setMsgs] = useState<ChatMsg[]>([]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const end = useRef<HTMLDivElement>(null);

  useEffect(() => { api<ChatMsg[]>("/api/chat").then(setMsgs).catch((e) => setErr(e.message)); }, []);
  useEffect(() => { end.current?.scrollIntoView({ behavior: "smooth" }); }, [msgs, busy]);

  async function send(e: React.FormEvent) {
    e.preventDefault();
    const content = text.trim();
    if (!content || busy) return;
    setText(""); setErr(""); setBusy(true);
    const mine: ChatMsg = { id: -Date.now(), role: "user", content, source: null, created_at: new Date().toISOString() };
    setMsgs((m) => [...m, mine]);
    try {
      const reply = await api<ChatMsg>("/api/chat", { method: "POST", body: JSON.stringify({ message: content }) });
      setMsgs((m) => [...m, reply]);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Pesan gagal terkirim.");
      setMsgs((m) => m.filter((x) => x.id !== mine.id));
      setText(content);
    } finally { setBusy(false); }
  }

  return (
    <div className="max-w-[640px]">
      <p className="eyebrow">Konsultasi</p>
      <h1 className="mt-1 text-2xl font-semibold">Ngobrol dengan AI Habit Coach</h1>
      <p className="mt-1 text-xs text-mute">Setiap jawaban didukung oleh referensi jurnal dan artikel ilmiah dari basis pengetahuan sistem.</p>

      <div className="card mt-4 flex h-[calc(100dvh-14rem)] max-h-[560px] min-h-[360px] flex-col overflow-hidden">
        <div className="flex items-center justify-between border-b border-line px-4 py-2.5 text-[11px]">
          <span className="flex items-center gap-2 font-semibold"><span className="h-1.5 w-1.5 rounded-full bg-mint" /> AI Habit Coach</span>
          <span className="text-mute">Terhubung ke DB Metode Belajar</span>
        </div>
        <div className="flex-1 space-y-3 overflow-y-auto p-4">
          {!msgs.length && (
            <Bubble role="assistant" content={`Halo ${user.name.split(" ")[0]}! Ceritakan kesulitan belajarmu, atau tanyakan hasil analisis kebiasaanmu. Aku bantu carikan caranya.`} />
          )}
          {msgs.map((m) => <Bubble key={m.id} role={m.role} content={m.content} source={m.source} />)}
          {busy && <p className="text-[11px] text-mute">AI Coach sedang mengetik…</p>}
          <div ref={end} />
        </div>
        {err && <p className="px-4 pb-2 text-[11px] text-coral">{err}</p>}
        <form onSubmit={send} className="flex gap-2 border-t border-line p-3">
          <input className="input rounded-full" placeholder="Tulis pertanyaanmu di sini…" value={text}
            onChange={(e) => setText(e.target.value)} maxLength={2000} />
          <button aria-label="Kirim" disabled={busy || !text.trim()}
            className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-accent text-[#1a1630] transition hover:brightness-110 disabled:opacity-50">
            <Send size={14} />
          </button>
        </form>
      </div>
    </div>
  );
}

function Bubble({ role, content, source }: { role: string; content: string; source?: string | null }) {
  const mine = role === "user";
  return (
    <div className={`flex ${mine ? "justify-end" : ""}`}>
      <div className={`max-w-[80%] whitespace-pre-wrap rounded-xl px-3.5 py-2.5 text-xs leading-relaxed ${mine ? "bg-accent/15" : "bg-card2"}`}>
        {content}
        {source && <p className="mt-2 inline-block rounded bg-accent/10 px-1.5 py-0.5 font-mono text-[10px] text-accent">§ {source}</p>}
      </div>
    </div>
  );
}
