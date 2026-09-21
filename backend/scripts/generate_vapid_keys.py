"""Print a fresh VAPID key pair for .env.

    python scripts/generate_vapid_keys.py

The public key is the raw uncompressed EC point the browser expects in
`applicationServerKey`; the private key is base64url PKCS8 DER, which is what
pywebpush accepts as a string.
"""

import base64

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec


def b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def main() -> None:
    key = ec.generate_private_key(ec.SECP256R1())
    private_der = key.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_point = key.public_key().public_bytes(
        encoding=serialization.Encoding.X962,
        format=serialization.PublicFormat.UncompressedPoint,
    )
    print(f"VAPID_PUBLIC_KEY={b64url(public_point)}")
    print(f"VAPID_PRIVATE_KEY={b64url(private_der)}")


if __name__ == "__main__":
    main()
