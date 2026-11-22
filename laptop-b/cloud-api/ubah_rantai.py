# HANYA UNTUK DEMO: ubah pilihan pada suara pertama di block tertentu langsung di
# berkas rantai, tanpa menghitung ulang hash. Setelah cloud-api di-restart,
# /rantai/validasi harus melaporkan block itu sebagai block pertama yang rusak.
#   docker compose exec cloud-api python ubah_rantai.py 1
import json
import os
import sys

PATH = os.getenv("RANTAI_PATH", "/data/rantai.json")
index = int(sys.argv[1]) if len(sys.argv) > 1 else 1

with open(PATH, encoding="utf-8") as f:
    rantai = json.load(f)
if not 1 <= index < len(rantai) or not rantai[index]["transaksi"]:
    sys.exit(f"block {index} tidak ada atau kosong (panjang rantai {len(rantai)})")
suara = rantai[index]["transaksi"][0]
lama = suara["pilihan"]
suara["pilihan"] = 2 if lama == 1 else 1
with open(PATH, "w", encoding="utf-8") as f:
    json.dump(rantai, f)
print(f"block {index}: pilihan {lama} -> {suara['pilihan']} (hash tidak dihitung ulang)")
print("jalankan: docker compose restart cloud-api, lalu buka /rantai/validasi")
