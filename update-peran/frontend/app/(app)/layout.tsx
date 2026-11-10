"use client";
import { Menu } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import Sidebar from "@/components/Sidebar";
import { api, token, type User } from "@/lib/api";
import { UserContext } from "@/lib/auth";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const path = usePathname();
  const [user, setUser] = useState<User | null>(null);
  const [menuOpen, setMenuOpen] = useState(false);

  const refresh = useCallback(async () => {
    setUser(await api<User>("/api/auth/me"));
  }, []);

  useEffect(() => {
    if (!token.get()) { router.replace("/login"); return; }
    refresh().catch(() => router.replace("/login"));
  }, [refresh, router]);

  useEffect(() => {
    if (!user) return;
    const staf = user.peran !== "mahasiswa";
    const areaStaf = path.startsWith("/pantau") || path.startsWith("/panduan-psikolog") || path === "/profil";
    if (staf && !areaStaf) router.replace("/pantau");
    if (!staf && (path.startsWith("/pantau") || path.startsWith("/panduan-psikolog"))) router.replace("/dashboard");
  }, [user, path, router]);

  if (!user) return <div className="grid min-h-screen place-items-center text-sm text-mute">Memuat…</div>;

  return (
    <UserContext.Provider value={{ user, refresh }}>
      <div className="min-h-screen md:flex">
        <Sidebar open={menuOpen} onClose={() => setMenuOpen(false)} />
        <div className="min-w-0 flex-1">
          <header className="sticky top-0 z-30 flex items-center gap-3 border-b border-line bg-side px-4 py-3 md:hidden">
            <button aria-label="Buka menu" onClick={() => setMenuOpen(true)} className="text-ink"><Menu size={20} /></button>
            <span className="text-sm font-semibold">Habit Coach</span>
          </header>
          <main className="px-4 py-5 sm:px-8 sm:py-7">{children}</main>
        </div>
      </div>
    </UserContext.Provider>
  );
}
