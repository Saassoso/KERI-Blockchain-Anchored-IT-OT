# gen_keys.py - Fixed for Windows
import sys
import os

# 1. Load Libsodium using your project's utility
# We must do this BEFORE importing pysodium
from scripts.utils import load_libsodium
load_libsodium()

# 2. NOW we can import pysodium
import pysodium

def generate_keys():
    # Generate a new Ed25519 Keypair
    public_key, secret_key = pysodium.crypto_sign_keypair()

    print("="*60)
    print("🔐 SCADA KEY PAIR GENERATED")
    print("="*60)
    print(f"PRIVATE KEY (Save this in scada_commander.py):")
    print(secret_key.hex())
    print("-" * 60)
    print(f"PUBLIC KEY  (Put this in gateway.py):")
    print(public_key.hex())
    print("="*60)

if __name__ == "__main__":
    generate_keys()