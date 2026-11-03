from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
from ipaddress import ip_address
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID


ROOT_DIR = Path(__file__).resolve().parents[1]
CERT_DIR = ROOT_DIR / "certs"
CERT_PATH = CERT_DIR / "localhost.crt"
KEY_PATH = CERT_DIR / "localhost.key"


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a self-signed localhost TLS certificate.")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Replace an existing localhost certificate and private key.",
    )
    args = parser.parse_args()

    if not args.force and (CERT_PATH.exists() or KEY_PATH.exists()):
        parser.error("A localhost certificate already exists; pass --force to replace it.")

    CERT_DIR.mkdir(exist_ok=True)
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "localhost")])
    now = datetime.now(timezone.utc)
    certificate = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(subject)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=5))
        .not_valid_after(now + timedelta(days=365))
        .add_extension(
            x509.SubjectAlternativeName(
                [
                    x509.DNSName("localhost"),
                    x509.IPAddress(ip_address("127.0.0.1")),
                    x509.IPAddress(ip_address("::1")),
                ]
            ),
            critical=False,
        )
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(
            x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]),
            critical=False,
        )
        .sign(private_key, hashes.SHA256())
    )

    KEY_PATH.write_bytes(
        private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    CERT_PATH.write_bytes(certificate.public_bytes(serialization.Encoding.PEM))
    KEY_PATH.chmod(0o600)
    print(f"Created {CERT_PATH} and {KEY_PATH}")


if __name__ == "__main__":
    main()
