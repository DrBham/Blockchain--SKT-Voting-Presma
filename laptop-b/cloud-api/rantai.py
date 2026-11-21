# Rantai block di pusat rekap: setiap suara yang diterima dicatat ke block
# dengan proof of work. Diadaptasi dari project Blockchain (PB1/PB2), versi
# satu node tanpa tanda tangan. Hanya memakai pustaka standar.
import hashlib
import json
import logging
import os
import threading
import time

log = logging.getLogger("uvicorn.error")


def hitung_hash(block):
    isi = {k: block[k] for k in ("index", "timestamp", "transaksi", "previous_hash", "nonce")}
    return hashlib.sha256(json.dumps(isi, sort_keys=True).encode("utf-8")).hexdigest()


def buat_genesis():
    # timestamp tetap supaya genesis selalu sama
    block = {"index": 0, "timestamp": 0, "transaksi": [], "previous_hash": "0", "nonce": 0}
    block["hash"] = hitung_hash(block)
    return block


class Rantai:
    def __init__(self, path, difficulty):
        self.path = path
        self.difficulty = difficulty
        self._kunci = threading.Lock()
        self.pool = []
        self.chain = self._muat()
        # berkas yang diubah tangan tidak boleh membuat service mati; validasi() yang melaporkannya
        self._lokasi = {tx["bukti"]: b.get("index") for b in self.chain
                        if isinstance(b.get("transaksi"), list)
                        for tx in b["transaksi"] if isinstance(tx, dict) and isinstance(tx.get("bukti"), str)}

    def _muat(self):
        try:
            with open(self.path, encoding="utf-8") as f:
                chain = json.load(f)
            if isinstance(chain, list) and chain and all(isinstance(b, dict) for b in chain):
                return chain
        except FileNotFoundError:
            return [buat_genesis()]
        except (OSError, ValueError):
            pass
        # berkas rusak disimpan sebagai bukti, tidak ditimpa; validasi() terus melaporkannya
        os.replace(self.path, self.path + ".rusak")
        log.warning("rantai: berkas %s rusak, disimpan sebagai .rusak, mulai dari genesis", self.path)
        return [buat_genesis()]

    def _simpan(self, chain):
        sementara = self.path + ".tmp"
        with open(sementara, "w", encoding="utf-8") as f:
            json.dump(chain, f)
        os.replace(sementara, self.path)  # ganti utuh: tidak ada berkas setengah tertulis

    def tambah_pool(self, tx):
        """Masukkan suara ke pool. False bila kode buktinya sudah di pool atau di rantai."""
        with self._kunci:
            if tx["bukti"] in self._lokasi or self.di_pool(tx["bukti"]):
                return False
            self.pool.append(tx)
            return True

    def tambang(self):
        """Bentuk satu block dari isi pool. Mengembalikan block baru, atau None bila pool kosong."""
        with self._kunci:
            if not self.pool:
                return None
            transaksi = list(self.pool)
            induk = self.chain[-1]
        block = {"index": induk["index"] + 1, "timestamp": time.time(), "transaksi": transaksi,
                 "previous_hash": induk["hash"], "nonce": 0}
        target = "0" * self.difficulty
        block["hash"] = hitung_hash(block)
        while not block["hash"].startswith(target):  # PoW di luar kunci: suara tetap bisa masuk pool
            block["nonce"] += 1
            block["hash"] = hitung_hash(block)
        with self._kunci:
            chain_baru = self.chain + [block]
            self._simpan(chain_baru)  # tulis berkas dulu: bila gagal, memori tetap seperti semula
            self.chain = chain_baru
            masuk = {tx["bukti"] for tx in transaksi}
            self._lokasi.update((kode, block["index"]) for kode in masuk)  # sebelum pool, agar status tidak berkedip
            self.pool = [tx for tx in self.pool if tx["bukti"] not in masuk]
        return block

    def cari(self, kode):
        return self._lokasi.get(kode)

    def di_pool(self, kode):
        return any(tx["bukti"] == kode for tx in self.pool)

    def validasi(self):
        """(valid, index block pertama yang rusak, alasan)."""
        if os.path.exists(self.path + ".rusak"):
            return False, 0, f"berkas rantai rusak (disimpan di {os.path.basename(self.path)}.rusak), rantai dimulai ulang"
        with self._kunci:
            chain = list(self.chain)
        if chain[0] != buat_genesis():
            return False, 0, "genesis block tidak sah"
        target = "0" * self.difficulty
        for i in range(1, len(chain)):
            b = chain[i]
            try:
                if b["previous_hash"] != chain[i - 1]["hash"]:
                    return False, i, "previous hash tidak cocok dengan block sebelumnya"
                if b["hash"] != hitung_hash(b):
                    return False, i, "hash tidak cocok dengan isi block (data berubah)"
            except (KeyError, TypeError):
                return False, i, "struktur block tidak lengkap"
            if not str(b["hash"]).startswith(target):
                return False, i, f"proof of work tidak valid (hash tidak diawali {target})"
        return True, None, "rantai valid"

    def ringkas(self):
        with self._kunci:
            return {"panjang": len(self.chain), "difficulty": self.difficulty,
                    "pool": len(self.pool), "terakhir": str(self.chain[-1].get("hash", ""))[:16]}
