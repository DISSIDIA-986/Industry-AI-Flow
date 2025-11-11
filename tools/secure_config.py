#!/usr/bin/env python3
"""
Utility helpers for managing encrypted/hashed secrets.

Examples:
  python tools/secure_config.py gen-key
  python tools/secure_config.py encrypt --key <FERNET_KEY> --secret "my-api-key"
  python tools/secure_config.py hash --secret "my-api-key" --salt "tenantA"
"""

from __future__ import annotations

import argparse
import sys

from cryptography.fernet import Fernet

from backend.security.secret_manager import SecretManager


def generate_key() -> None:
    print(Fernet.generate_key().decode())


def encrypt_secret(key: str, secret: str) -> None:
    if not key or not secret:
        raise ValueError("Both --key and --secret must be provided.")
    token = Fernet(key.encode()).encrypt(secret.encode())
    print(token.decode())


def hash_secret(secret: str, salt: str | None, iterations: int) -> None:
    manager = SecretManager(
        encryption_key=None, hash_salt=salt, hash_iterations=iterations
    )
    print(manager.hash_value(secret))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Secure configuration helper.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("gen-key", help="Generate a random Fernet key.")

    encrypt_parser = subparsers.add_parser(
        "encrypt", help="Encrypt a secret with a Fernet key."
    )
    encrypt_parser.add_argument(
        "--key", required=True, help="Base64 encoded Fernet key"
    )
    encrypt_parser.add_argument("--secret", required=True, help="Secret to encrypt")

    hash_parser = subparsers.add_parser(
        "hash", help="Create a salted PBKDF2 hash for a secret."
    )
    hash_parser.add_argument("--secret", required=True, help="Secret to hash")
    hash_parser.add_argument("--salt", default="", help="Optional salt value")
    hash_parser.add_argument(
        "--iterations",
        type=int,
        default=120_000,
        help="PBKDF2 iteration count (default: 120000)",
    )

    args = parser.parse_args(argv)

    if args.command == "gen-key":
        generate_key()
    elif args.command == "encrypt":
        encrypt_secret(args.key, args.secret)
    elif args.command == "hash":
        hash_secret(args.secret, args.salt, args.iterations)
    else:
        parser.error("Unknown command")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
