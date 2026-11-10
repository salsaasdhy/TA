import { api } from "./api";

export function pushDidukung(): boolean {
  return typeof window !== "undefined" && "serviceWorker" in navigator && "PushManager" in window && "Notification" in window;
}

function kunciKeBytes(base64: string): Uint8Array {
  const pad = "=".repeat((4 - (base64.length % 4)) % 4);
  const raw = atob((base64 + pad).replace(/-/g, "+").replace(/_/g, "/"));
  return Uint8Array.from(raw, (c) => c.charCodeAt(0));
}

async function daftarSW(): Promise<ServiceWorkerRegistration> {
  await navigator.serviceWorker.register("/sw.js");
  return navigator.serviceWorker.ready;
}

export async function langgananSaatIni(): Promise<PushSubscription | null> {
  if (!pushDidukung()) return null;
  const reg = await daftarSW();
  return reg.pushManager.getSubscription();
}

export async function aktifkanPush(): Promise<void> {
  if (!pushDidukung()) throw new Error("Browser ini belum mendukung notifikasi push.");
  const { tersedia, public_key } = await api<{ tersedia: boolean; public_key: string }>("/api/push/key");
  if (!tersedia) throw new Error("Server belum dikonfigurasi untuk notifikasi (kunci VAPID di backend/.env masih kosong).");
  const izin = await Notification.requestPermission();
  if (izin !== "granted") throw new Error("Izin notifikasi ditolak. Aktifkan lewat ikon gembok di sebelah alamat situs, lalu coba lagi.");
  const reg = await daftarSW();
  const sub =
    (await reg.pushManager.getSubscription()) ??
    (await reg.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: kunciKeBytes(public_key) as unknown as BufferSource,
    }));
  const j = sub.toJSON();
  await api("/api/push/subscribe", { method: "POST", body: JSON.stringify({ endpoint: j.endpoint, keys: j.keys }) });
}

export async function matikanPush(): Promise<void> {
  const reg = await daftarSW();
  const sub = await reg.pushManager.getSubscription();
  if (!sub) return;
  await api("/api/push/unsubscribe", { method: "POST", body: JSON.stringify({ endpoint: sub.endpoint }) });
  await sub.unsubscribe();
}
