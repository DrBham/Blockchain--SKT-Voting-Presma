// Perilaku halaman pemilih (daftar, verifikasi, masuk, bilik, bukti). Semua aturan tetap
// diperiksa server lewat /api/*; skrip ini hanya memanggil API dan memberi umpan balik langsung.
// Pola diambil dari web project Blockchain kelompok (static/pemilih.js).
"use strict";

const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const esc = (t) => String(t).replace(/[&<>"']/g, (c) => `&#${c.charCodeAt(0)};`);
const LANGKAH = ["Daftar akun", "Verifikasi email", "Masuk", "Bilik suara", "Bukti suara"];
const langkah = Number(document.body.dataset.langkah);

async function api(url, data) {
  const r = await fetch(url, data === undefined ? {} : {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data),
  });
  let isi = {};
  try { isi = await r.json(); } catch { /* badan kosong */ }
  return { ok: r.ok, status: r.status, isi };
}

// pesan singkat yang dibawa ke halaman berikutnya
const pesan = (teks) => { try { sessionStorage.setItem("pesan", teks); } catch { /* abaikan */ } };
function ingat(k, v) { try { v === null ? sessionStorage.removeItem(k) : sessionStorage.setItem(k, v); } catch { /* abaikan */ } }
function baca(k) { try { return sessionStorage.getItem(k) || ""; } catch { return ""; } }

// ---------- kerangka: rel 5 langkah, bilah ponsel, status TPS ----------
const LOGO = '<img src="/static/logo-untad.png" alt="" width="30" height="31">';
$(".voter").insertAdjacentHTML("afterbegin", `
  <aside class="rail" aria-label="Perjalanan pemilih">
    <a class="brand" href="/pemilih/daftar">${LOGO}<span><b>Pemira Presma</b><small>Pemilihan Presiden Mahasiswa</small></span></a>
    <div>
      <p class="journey-label">Langkahmu</p>
      <ol class="journey">${LANGKAH.map((nama, i) => {
        const n = i + 1, kelas = n === langkah ? "now" : n < langkah ? "done" : "";
        return `<li><span class="step ${kelas}"${n === langkah ? ' aria-current="step"' : ""}><span class="n">${n < langkah ? "✓" : n}</span><span>${nama}</span></span></li>`;
      }).join("")}</ol>
    </div>
    <div class="window">
      <p class="small soft">Pemungutan suara</p>
      <p class="clock" id="rel-status" style="font-family:var(--font);font-size:18px">memuat</p>
      <p class="node-line"><span class="tag" id="rel-tag"></span><span id="rel-info">TPS di Laptop A</span></p>
    </div>
    <p class="rail-foot">Proyek mata kuliah Sistem Komputasi Terdistribusi. Bukan sistem resmi UNTAD.</p>
  </aside>
  <div class="mobilebar">
    <div class="spread"><a class="brand" href="/pemilih/daftar">${LOGO}<b>Pemira Presma</b></a>
    <span class="small soft">Langkah ${langkah} dari 5</span></div>
    <div class="bar"><i style="width:${langkah * 20}%"></i></div>
  </div>`);

let statusTps = null;
async function muatStatus() {
  try {
    const { isi } = await api("/status");
    statusTps = isi;
    $("#rel-status").textContent = isi.pemungutan;
    $("#rel-tag").className = `tag ${isi.pemungutan === "buka" ? "ok" : "wait"}`;
    $("#rel-info").textContent = `${isi.tps_id} · ${isi.akun_terdaftar} akun aktif · antre ${isi.antre} · disetor ${isi.terkirim}`;
  } catch {
    $("#rel-status").textContent = "TPS tidak terjangkau";
    $("#rel-tag").className = "tag bad";
  }
  return statusTps;
}
muatStatus();
setInterval(muatStatus, 3000);

const dibawa = baca("pesan");
if (dibawa) {
  ingat("pesan", null);
  $(".stage-inner").insertAdjacentHTML("afterbegin", `<div class="note" role="status" style="margin-bottom:16px"><p>${esc(dibawa)}</p></div>`);
}

// ---------- ikon ----------
const IKON = {
  key: '<circle cx="7.5" cy="15.5" r="5.5"/><path d="m21 2-9.6 9.6M15.5 7.5l3 3L22 7l-3-3"/>',
  mail: '<rect width="20" height="16" x="2" y="4" rx="2"/><path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"/>',
  lock: '<rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>',
};
$$("[data-icon]").forEach((el) => IKON[el.dataset.icon] &&
  el.insertAdjacentHTML("afterbegin", `<svg class="icon" viewBox="0 0 24 24" aria-hidden="true">${IKON[el.dataset.icon]}</svg>`));

// ---------- NIM ----------
const FAKULTAS = "ABCDEFGKLNP";
function cekNim(nim) {
  if (!nim) return ["", ""];
  if (!/^[A-Z]/.test(nim)) return ["bad", "Diawali satu huruf kode fakultas"];
  if (!FAKULTAS.includes(nim[0])) return ["bad", `Kode fakultas '${nim[0]}' tidak terdaftar di UNTAD`];
  if (!/^[A-Z]\d{7,8}$/.test(nim)) return ["bad", "1 huruf diikuti 7 atau 8 angka"];
  return ["good", "Format NIM valid. Kode dikirim ke email kampus NIM ini"];
}
function tandai(input, msg, [kelas, teks]) {
  if (input) {
    input.classList.remove("bad", "good");
    if (kelas) input.classList.add(kelas);
    input.toggleAttribute("aria-invalid", kelas === "bad");
  }
  msg.className = `msg ${kelas}`;
  msg.textContent = teks;
}
function rapikanNim(nim) {
  nim.addEventListener("input", () => { nim.value = nim.value.toUpperCase().replace(/\s/g, ""); });
}
function sibuk(btn, teks) {
  const asli = btn.textContent;
  btn.disabled = true;
  btn.textContent = teks;
  return () => { btn.disabled = false; btn.textContent = asli; };
}

// ---------- tampilkan password ----------
$$("[data-peek]").forEach((b) => b.addEventListener("click", () => {
  const inp = $(`#${b.dataset.peek}`);
  const lihat = inp.type === "password";
  inp.type = lihat ? "text" : "password";
  b.textContent = lihat ? "Sembunyikan" : "Tampilkan";
}));

// ---------- kode 6 kotak ----------
function kotakOtp(wadah, onLengkap) {
  const kotak = $$("input", wadah);
  const nilai = () => kotak.map((k) => k.value).join("");
  const isi = (kode) => {
    kotak.forEach((k, i) => { k.value = kode[i] || ""; k.classList.toggle("filled", !!k.value); });
    kotak[Math.min(kode.length, 5)].focus();
    if (kode.length === 6) onLengkap(kode);
  };
  kotak.forEach((k, i) => {
    k.addEventListener("input", () => {
      const angka = k.value.replace(/\D/g, "");
      if (angka.length > 1) return isi(angka.slice(0, 6));  // autofill memasukkan seluruh kode ke satu kotak
      k.value = angka;
      k.classList.toggle("filled", !!k.value);
      wadah.classList.remove("bad");
      if (k.value && i < 5) kotak[i + 1].focus();
      if (nilai().length === 6) onLengkap(nilai());
    });
    k.addEventListener("keydown", (e) => { if (e.key === "Backspace" && !k.value && i) kotak[i - 1].focus(); });
    k.addEventListener("paste", (e) => {
      const angka = (e.clipboardData.getData("text").match(/\d/g) || []).slice(0, 6);
      if (!angka.length) return;
      e.preventDefault();
      isi(angka.join(""));
    });
  });
  return { nilai, kosongkan: () => isi("") };
}

// tombol kirim ulang menunggu jeda 60 detik
function jedaUlang(btn, sisa) {
  const teks = btn.dataset.teks || (btn.dataset.teks = btn.textContent);
  btn.disabled = true;
  const tick = () => {
    if (sisa <= 0) { btn.disabled = false; btn.textContent = teks; return; }
    btn.textContent = `${teks} (${sisa} detik)`;
    sisa--;
    setTimeout(tick, 1000);
  };
  tick();
}
async function kirimUlang(nim, btn, msg) {
  const { ok, status, isi } = await api("/api/kirim-ulang", { nim });
  tandai(null, msg, ok ? ["good", "Kode baru dikirim. Kode lama sudah tidak berlaku"] : ["bad", isi.alasan || "Gagal mengirim ulang"]);
  const detik = ok ? 60 : status === 429 ? Number((isi.alasan.match(/\d+/) || [0])[0]) : 0;
  if (detik) jedaUlang(btn, detik);
}

// ---------- 1. daftar ----------
const formDaftar = $("#form-daftar");
if (formDaftar) {
  const nim = $("#nim"), email = $("#email"), pw = $("#pw"), pw2 = $("#pw2");
  rapikanNim(nim);
  // email kampus UNTAD selalu NIM@untad.ac.id, jadi tidak diketik sendiri
  nim.addEventListener("input", () => {
    tandai(nim, $("#nim-msg"), cekNim(nim.value));
    email.value = cekNim(nim.value)[0] === "good" ? `${nim.value}@untad.ac.id` : "";
  });
  pw.addEventListener("input", () => {
    const v = pw.value;
    const s = [v.length >= 8, /[A-Z]/.test(v) && /[a-z]/.test(v), /\d/.test(v), /[^A-Za-z0-9]/.test(v)].filter(Boolean).length;
    $("#meter").dataset.s = v ? s : 0;
    $("#pw-msg").className = "msg";
    $("#pw-msg").textContent = v ? ["Terlalu lemah", "Lemah", "Cukup", "Kuat", "Sangat kuat"][s] : "Minimal 8 karakter";
  });
  pw2.addEventListener("input", () => tandai(pw2, $("#pw2-msg"),
    !pw2.value ? ["", ""] : pw2.value === pw.value ? ["good", "Cocok"] : ["bad", "Belum sama dengan password"]));
  formDaftar.addEventListener("submit", async (e) => {
    e.preventDefault();
    const salah = [];
    if (cekNim(nim.value)[0] !== "good") { salah.push(nim); tandai(nim, $("#nim-msg"), nim.value ? cekNim(nim.value) : ["bad", "NIM wajib diisi"]); }
    if (pw.value.length < 8) { salah.push(pw); tandai(pw, $("#pw-msg"), ["bad", "Minimal 8 karakter"]); }
    if (!pw2.value || pw2.value !== pw.value) { salah.push(pw2); tandai(pw2, $("#pw2-msg"), ["bad", "Belum sama dengan password"]); }
    if (salah.length) return salah[0].focus();
    const selesai = sibuk($("button[type=submit]", formDaftar), "Mengirim kode…");
    const { ok, isi } = await api("/api/daftar", { nim: nim.value, password: pw.value });
    if (ok) {
      ingat("nim_daftar", nim.value);
      return location.assign("/pemilih/verifikasi");
    }
    selesai();
    const kePw = /password/i.test(isi.alasan || "");
    tandai(kePw ? pw : nim, $(kePw ? "#pw-msg" : "#nim-msg"), ["bad", isi.alasan || "Pendaftaran gagal"]);
    (kePw ? pw : nim).focus();
  });
}

// ---------- 2. verifikasi: kirim otomatis begitu 6 digit terisi ----------
const formKode = $("#form-kode");
if (formKode) {
  const nim = $("#nim"), msg = $("#otp-msg");
  rapikanNim(nim);
  nim.value = baca("nim_daftar");
  $("#email").textContent = nim.value ? `${nim.value}@untad.ac.id` : "email kampus NIM-mu";
  nim.addEventListener("input", () => { $("#email").textContent = `${nim.value}@untad.ac.id`; });
  const otp = kotakOtp($("#otp", formKode), async (kode) => {
    if (cekNim(nim.value)[0] !== "good") { tandai(nim, $("#nim-msg"), ["bad", "Isi NIM yang didaftarkan"]); return nim.focus(); }
    tandai(null, msg, ["", "Memeriksa kode…"]);
    const { ok, isi } = await api("/api/verifikasi", { nim: nim.value, kode });
    if (ok) {
      ingat("nim_daftar", nim.value);
      pesan("Akun aktif. Simpan kode pemilih ini untuk masuk dan memilih");
      return location.assign("/pemilih/masuk");
    }
    $("#otp", formKode).classList.add("bad");
    tandai(null, msg, ["bad", isi.alasan || "Kode tidak bisa diperiksa"]);
    otp.kosongkan();
  });
  formKode.addEventListener("submit", (e) => e.preventDefault());
  (nim.value ? $("#otp input", formKode) : nim).focus();
  const ulang = $("#kirim-ulang");
  if (nim.value) jedaUlang(ulang, 60);  // kode baru saja dikirim saat mendaftar
  ulang.addEventListener("click", () => kirimUlang(nim.value, ulang, msg));
}

// ---------- 3. masuk ----------
const formMasuk = $("#form-masuk");
if (formMasuk) {
  const nim = $("#nim"), pw = $("#pw"), msg = $("#otp-msg");
  rapikanNim(nim);
  nim.value = baca("nim_daftar");
  ingat("nim_daftar", null);  // diisikan sekali saja, supaya pemilih berikutnya tidak melihatnya
  const otp = kotakOtp($("#otp", formMasuk), () => tandai(null, msg, ["", "Kode lengkap"]));
  nim.addEventListener("input", () => tandai(nim, $("#nim-msg"), cekNim(nim.value)[0] === "bad" ? cekNim(nim.value) : ["", ""]));
  formMasuk.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (cekNim(nim.value)[0] !== "good") { tandai(nim, $("#nim-msg"), ["bad", "NIM tidak valid"]); return nim.focus(); }
    if (!pw.value) { tandai(pw, $("#pw-msg"), ["bad", "Password wajib diisi"]); return pw.focus(); }
    if (otp.nilai().length !== 6) {
      $("#otp", formMasuk).classList.add("bad");
      tandai(null, msg, ["bad", "Isi 6 digit kode pemilih"]);
      return $("#otp input", formMasuk).focus();
    }
    const selesai = sibuk($("button[type=submit]", formMasuk), "Memeriksa…");
    const { ok, isi } = await api("/api/masuk", { nim: nim.value, password: pw.value, kode: otp.nilai() });
    if (ok) return location.assign(isi.sudah_memilih ? "/pemilih/bukti" : "/bilik");
    selesai();
    const alasan = isi.alasan || "Gagal masuk";
    if (alasan.startsWith("Akun belum aktif")) {
      ingat("nim_daftar", nim.value);
      pesan(alasan);
      return location.assign("/pemilih/verifikasi");
    }
    if (alasan.startsWith("NIM atau password")) { tandai(pw, $("#pw-msg"), ["bad", alasan]); return pw.focus(); }
    $("#otp", formMasuk).classList.add("bad");
    tandai(null, msg, ["bad", alasan]);
    otp.kosongkan();
  });
  const ulang = $("#kirim-ulang");
  ulang.addEventListener("click", () => {
    if (cekNim(nim.value)[0] !== "good") { tandai(nim, $("#nim-msg"), ["bad", "Isi NIM dulu"]); return nim.focus(); }
    kirimUlang(nim.value, ulang, msg);
  });
}

// ---------- keluar ----------
$$("[data-keluar]").forEach((b) => b.addEventListener("click", async () => {
  await api("/api/keluar", {});
  pesan("Kamu sudah keluar");
  location.assign("/pemilih/masuk");
}));

// ---------- 4. bilik: surat suara, dialog Setuju / Batal ----------
const ALASAN_TUTUP = {
  tutup: "Pemungutan suara sudah ditutup. Suara baru tidak diterima lagi",
};
const formBilik = $("#form-bilik");
if (formBilik) {
  const kirim = $("#kirim"), dlg = $("#konfirmasi"), teks = $("#pilihan-teks");
  const dipilih = () => $("input[name=paslon]:checked", formBilik);
  const tampilTutup = (pemungutan) => {
    $("#tutup").hidden = false;
    $("#isi-bilik").hidden = true;
    $("#alasan-tutup").textContent = ALASAN_TUTUP[pemungutan] ||
      "Pemungutan suara belum dibuka panitia. Halaman ini terbuka sendiri begitu pemungutan dibuka";
  };
  const tampilBilik = async () => {
    const { isi } = await api("/daftar");
    $("#tutup").hidden = true;
    $("#isi-bilik").hidden = false;
    $(".ballot", formBilik).insertAdjacentHTML("beforeend", Object.entries(isi.kandidat).map(([no, nama]) => `
      <label class="choice">
        <input type="radio" name="paslon" value="${esc(no)}" data-nama="${esc(nama)}" aria-label="Paslon ${esc(no)}, ${esc(nama)}" required>
        <span class="paper"><span class="no">${esc(no)}<span class="hole"></span></span><span class="name">${esc(nama)}</span><span class="sub">Pasangan calon nomor urut ${esc(no)}</span></span>
      </label>`).join(""));
    $$("input[name=paslon]", formBilik).forEach((r) => r.addEventListener("change", () => {
      kirim.disabled = false;
      teks.textContent = `Paslon ${r.value} dipilih. Periksa lagi sebelum mengirim`;
    }));
  };
  (async () => {
    const saya = await api("/api/saya");
    if (!saya.ok) return location.assign("/pemilih/masuk");
    if (saya.isi.sudah_memilih) return location.assign("/pemilih/bukti");
    $("#nim-saya").textContent = saya.isi.nim;
    const st = await muatStatus();
    if (st && st.pemungutan === "buka") return tampilBilik();
    tampilTutup(st && st.pemungutan);
    const tunggu = setInterval(() => {
      if (statusTps && statusTps.pemungutan === "buka") { clearInterval(tunggu); tampilBilik(); }
      else if (statusTps) tampilTutup(statusTps.pemungutan);
    }, 1000);
  })();

  kirim.disabled = true;
  formBilik.addEventListener("submit", (e) => {
    e.preventDefault();
    const p = dipilih();
    if (!p) return;
    $("#dlg-no").textContent = p.value;
    $("#dlg-nama").textContent = p.dataset.nama;
    $("#dlg-foot").hidden = false;
    $("#dlg-teks").hidden = false;
    $("#langkah-kirim").hidden = true;
    dlg.showModal();
    $("#batal").focus();  // fokus awal di Batal agar Enter tidak langsung mengirim
  });
  // batal: surat suara dikosongkan lagi, pemilih bebas memilih ulang
  $("#batal").addEventListener("click", () => {
    dlg.close();
    $$("input[name=paslon]", formBilik).forEach((r) => (r.checked = false));
    kirim.disabled = true;
    teks.textContent = "Pilihan dibatalkan. Silakan pilih lagi";
  });
  let mengirim = false;
  dlg.addEventListener("cancel", (e) => { if (mengirim) e.preventDefault(); });
  $("#setuju").addEventListener("click", async () => {
    if (mengirim) return;
    mengirim = true;
    $("#dlg-foot").hidden = true;
    $("#dlg-teks").hidden = true;
    $("#langkah-kirim").hidden = false;
    const { isi } = await api("/suara", { pilihan: Number(dipilih().value) });
    if (isi.diterima) return location.assign("/pemilih/bukti");
    mengirim = false;
    dlg.close();
    if (isi.alasan === "belum masuk atau sesi habis") {
      pesan("Sesi bilik habis, masuk lagi");
      return location.assign("/pemilih/masuk");
    }
    if (isi.alasan === "pemilih sudah memilih") return location.assign("/pemilih/bukti");
    const galat = $("#galat-bilik");
    galat.hidden = false;
    $("p", galat).textContent = `Suara ditolak TPS: ${isi.alasan || "TPS tidak menjawab"}`;
  });
}

// ---------- 5. bukti: status kode bukti di TPS ----------
const bukti = $("#bukti");
if (bukti) {
  const li = $$("#proses li");
  (async () => {
    const saya = await api("/api/saya");
    if (!saya.ok) return location.assign("/pemilih/masuk");
    if (!saya.isi.bukti) {
      $("#ada").hidden = true;
      $("#belum").hidden = false;
      return;
    }
    const kode = saya.isi.bukti;
    $("#kode").textContent = kode;
    $("#nim-saya").textContent = saya.isi.nim;
    $("#salin").addEventListener("click", async () => {
      try { await navigator.clipboard.writeText(kode); $("#salin").textContent = "Tersalin"; } catch { /* abaikan */ }
    });
    const cek = async () => {
      let st;
      try { st = (await api(`/bukti/${encodeURIComponent(kode)}`)).isi.status; } catch { st = null; }
      if (st === "terkirim") {
        li.forEach((x) => (x.className = "ok"));
        $("#judul").textContent = "Suaramu sudah disetor ke pusat rekap";
        $("#tag-bukti").className = "tag ok";
        $("#tag-bukti").textContent = "Terkirim";
        return;
      }
      $("#tag-bukti").textContent = st === "antre di TPS" ? "Antre di TPS" : "Belum terlihat";
      setTimeout(cek, 2000);
    };
    cek();
  })();
}
