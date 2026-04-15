# Copilot Instructions — Proyek UIX

Instruksi ini berlaku otomatis di seluruh sesi Copilot pada workspace ini.

## Bahasa

Semua kode, komentar, docstring, log, pesan error, dan teks UI menggunakan Bahasa Indonesia. Pengecualian: keyword bahasa pemrograman, nama library, dan method bawaan SDK tidak perlu diterjemahkan.

## Identitas Visual

Proyek ini memakai identitas **merah-hitam dual mode**. Saat menghasilkan kode frontend atau CSS, gunakan token berikut:

**Mode terang**: `--warna-utama: #B31818` · `--warna-sekunder: #E04B4B` · `--warna-latar: #F7F3F2` · `--warna-permukaan: #FFF8F7` · `--warna-aksen-gelap: #1A1A1A`

**Mode gelap**: `--warna-utama: #D62828` · `--warna-sekunder: #FF6B6B` · `--warna-latar: #090909` · `--warna-permukaan: #141414` · `--warna-aksen-terang: #F3EAEA`

**Semantik (kedua mode)**: sukses `#2E7D32` · peringatan `#D96C06` · bahaya `#C62828`

## Aturan Kerja

- Jangan mengarang method, versi library, endpoint, angka, atau kemampuan API. Kalau tidak yakin, tulis `[PERLU VERIFIKASI]`.
- Jangan gunakan kata `palsu`, `fake`, `fiktif`, atau padanan serupa. Gunakan `uji`, `demo`, atau `simulasi`.
- Kode lebih dari ~100 baris dibuat dalam potongan kecil dengan penanda `[SELESAI]` dan `[SELANJUTNYA: ...]`.
- Baca dan perbarui `memori.md` saat memulai sesi baru dan saat ada perubahan arsitektur atau keputusan teknis penting.
- Untuk jawaban faktual non-kode, sertakan sumber yang bisa diverifikasi.

## Agen Khusus

| Agen | Gunakan Untuk |
|------|--------------|
| `Asisten Operasional Indonesia` | Coding, implementasi, refactor, dokumentasi |
| `Auditor Ketat` | Review, audit, bug risk, root cause — tanpa edit file |
| `Autocompacter Memori` | Rangkum state dan perbarui `memori.md` saat konteks hampir penuh |
| `rules` | Referensi lengkap semua 13 aturan operasional |
