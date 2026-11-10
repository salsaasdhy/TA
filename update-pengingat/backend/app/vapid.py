"""Buat pasangan kunci VAPID untuk notifikasi push.  Pemakaian: python -m app.vapid"""
import base64

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def buat_kunci() -> tuple[str, str]:
    key = ec.generate_private_key(ec.SECP256R1())
    priv = key.private_numbers().private_value.to_bytes(32, "big")
    pub = key.public_key().public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
    return _b64(pub), _b64(priv)


if __name__ == "__main__":
    pub, priv = buat_kunci()
    print("Salin tiga baris ini ke backend/.env:\n")
    print(f"VAPID_PUBLIC_KEY={pub}")
    print(f"VAPID_PRIVATE_KEY={priv}")
    print("VAPID_SUBJECT=mailto:emailkamu@contoh.com")
