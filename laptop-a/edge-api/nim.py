# Aturan NIM dari project Blockchain (PB1/PB2): format dan kode fakultas UNTAD.
# Tidak ada batas angkatan: semester 3-7 (Peraturan Rektor No. 1/2021 Pasal 20)
# hanya syarat calon, bukan pemilih.
import re

POLA_NIM = re.compile(r"[A-Z]\d{7,8}")
FAKULTAS_UNTAD = set("ABCDEFGKLNP")


def periksa_nim(nim):
    """Kembalikan alasan penolakan, atau None bila NIM sah."""
    if not POLA_NIM.fullmatch(nim):
        return "format NIM salah (1 huruf kapital + 7-8 digit)"
    if nim[0] not in FAKULTAS_UNTAD:
        return f"Kode Fakultas '{nim[0]}' tidak terdaftar di UNTAD!"
    return None
