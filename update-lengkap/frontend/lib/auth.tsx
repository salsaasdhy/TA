"use client";
import { createContext, useContext } from "react";
import type { User } from "./api";

type Ctx = { user: User; refresh: () => Promise<void> };
export const UserContext = createContext<Ctx | null>(null);

export function useUser() {
  const c = useContext(UserContext);
  if (!c) throw new Error("useUser harus dipakai di dalam layout aplikasi");
  return c;
}
