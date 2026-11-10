"use client";
import { Bell, ClipboardCheck, History, LayoutDashboard, LogOut, MessageCircle, User as UserIcon } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { initials, token } from "@/lib/api";
import { useUser } from "@/lib/auth";

const MAIN = [
  { href: "/dashboard", label: "Dashboard", Icon: LayoutDashboard },
  { href: "/kuisioner", label: "Isi Kuisioner", Icon: ClipboardCheck },
  { href: "/riwayat", label: "Riwayat & Progres", Icon: History },
  { href: "/pengingat", label: "Pengingat Belajar", Icon: Bell },
  { href: "/chat", label: "Chat AI Coach", Icon: MessageCircle },
];

export default function Sidebar() {
  const path = usePathname();
  const router = useRouter();
  const { user } = useUser();

  const item = (href: string, label: string, Icon: typeof UserIcon) => {
    const active = path === href;
    return (
      <Link key={href} href={href}
        className={`relative flex items-center gap-2.5 rounded-lg px-3 py-2 text-[13px] transition ${
          active ? "bg-card2 text-ink" : "text-mute hover:bg-card hover:text-ink"}`}>
        {active && <span className="absolute -left-3 top-1.5 h-6 w-[3px] rounded-r bg-accent" />}
        <Icon size={15} /> {label}
      </Link>
    );
  };

  return (
    <aside className="sticky top-0 flex h-screen w-[220px] shrink-0 flex-col border-r border-line bg-side px-3 py-4">
      <div className="mb-6 flex items-center gap-2.5 px-1">
        <div className="grid h-8 w-8 place-items-center rounded-lg bg-accent text-xs font-bold text-[#1a1630]">AH</div>
        <div className="leading-tight">
          <div className="text-sm font-semibold">Habit Coach</div>
          <div className="text-[10px] text-mute">RAG Learning Assistant</div>
        </div>
      </div>
      <p className="mb-1.5 px-3 font-mono text-[9px] tracking-widest text-mute">MENU UTAMA</p>
      <nav className="mb-5 space-y-0.5">{MAIN.map((m) => item(m.href, m.label, m.Icon))}</nav>
      <p className="mb-1.5 px-3 font-mono text-[9px] tracking-widest text-mute">AKUN</p>
      <nav className="space-y-0.5">
        {item("/profil", "Profil", UserIcon)}
        <button onClick={() => { token.clear(); router.replace("/login"); }}
          className="flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-[13px] text-mute transition hover:bg-card hover:text-ink">
          <LogOut size={15} /> Keluar
        </button>
      </nav>
      <div className="mt-auto flex items-center gap-2.5 border-t border-line px-1 pt-3">
        <div className="grid h-8 w-8 place-items-center rounded-lg bg-card2 text-[11px] font-semibold">{initials(user.name)}</div>
        <div className="min-w-0 leading-tight">
          <div className="truncate text-xs font-semibold">{user.name.split(" ").slice(0, 2).join(" ")}</div>
          <div className="truncate text-[10px] text-mute">{user.program_studi || "Mahasiswa"}</div>
        </div>
      </div>
    </aside>
  );
}
