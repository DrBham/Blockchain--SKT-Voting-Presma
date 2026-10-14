import sys

from gabung_log import ambil_event, pasangkan

ARAH = ["voter-sim -> edge-api", "edge-api -> cloud-api",
        "cloud-api -> edge-api", "edge-api -> voter-sim"]
hitung = {}

for kirim, terima in pasangkan(ambil_event()):
    h = hitung.setdefault(f"{kirim['service']} -> {terima['service']}", [0, 0, 0])
    h[0] += 1
    h[1] += terima["fisik"] < kirim["fisik"]       # terima tercatat lebih awal
    h[2] += terima["lamport"] <= kirim["lamport"]  # melanggar aturan Lamport

if not hitung:
    sys.exit("Belum ada pasangan kirim-terima. Periksa SERVICE dan volume /log.")

print(f"{'arah pesan':<26}{'pasangan':>9}"
      f"{'terbalik (fisik)':>18}{'terbalik (Lamport)':>20}")
for a in ARAH + [a for a in hitung if a not in ARAH]:
    n, fisik, lamport = hitung.get(a, [0, 0, 0])
    print(f"{a:<26}{n:>9}{fisik:>18}{lamport:>20}")

salah_fisik = sum(h[1] for h in hitung.values())
salah_lamport = sum(h[2] for h in hitung.values())
print()
print("Timestamp fisik :", "LULUS" if salah_fisik == 0
      else f"GAGAL, {salah_fisik} pesan tercatat diterima sebelum dikirim")
print("Lamport clock   :", "LULUS" if salah_lamport == 0
      else f"GAGAL, {salah_lamport} pesan melanggar urutan kirim lalu terima")
sys.exit(1 if salah_lamport else 0)
