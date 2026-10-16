# Daftar Pemilih Tetap (DPT) dan paslon Presma UNTAD. Data pemilih rekaan.
# Semua angkatan boleh memilih selama mahasiswa aktif (ada di DPT).
PEMILIH = {
    f"{fak}{prodi}{th}{n:03d}"
    for fak, prodi in (("A", "121"), ("C", "301"), ("F", "551"))
    for th in ("19", "22", "23", "24", "25")
    for n in range(1, 11)
}  # 150 pemilih: 3 fakultas x 5 angkatan x 10 orang
KANDIDAT = {1: "Paslon 1", 2: "Paslon 2"}  # nama calon tidak dicantumkan
