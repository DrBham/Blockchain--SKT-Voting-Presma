# Aturan unik "bukti suara": kode bukti dihitung dari isi suara yang disetor.
# File ini identik di edge-api (Laptop A) dan cloud-api (Laptop B).
import hashlib
import json
import re

FIELD = ("request_id", "tps_id", "seq", "pemilih_id", "pilihan", "waktu")
POLA = re.compile(r"[0-9a-f]{16}")


def hitung(pesan):
    """16 karakter hex pertama SHA-256 atas enam field suara (urutan kunci tetap)."""
    isi = json.dumps({k: pesan[k] for k in FIELD}, sort_keys=True)
    return hashlib.sha256(isi.encode("utf-8")).hexdigest()[:16]


def rapikan(kode):
    """Kode bukti yang diketik pemilih: buang spasi, huruf kecil. None bila bukan 16 hex."""
    kode = str(kode).strip().lower()
    return kode if POLA.fullmatch(kode) else None
