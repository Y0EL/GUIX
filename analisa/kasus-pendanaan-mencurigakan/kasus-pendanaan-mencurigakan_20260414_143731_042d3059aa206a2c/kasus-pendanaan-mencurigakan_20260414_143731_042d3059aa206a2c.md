# Dossier Analisa Kasus - Pola Pendanaan Tersebar - Indikasi Koordinasi Finansial

- ID kasus: `kasus-pendanaan-mencurigakan`
- Fingerprint SHA-256: `042d3059aa206a2c1723aa44e25d151cc0563e38da4448319825dd89b21f8c0e`
- Indikasi sindikat: `ya`
- Confidence: `0.72`

## Ringkasan Eksekutif

Analisis menunjukkan jaringan 11 aktor yang saling terkait melalui serangkaian transfer kecil berulang (tunai, transfer bank, dompet digital) dengan pola konektivitas lintas klaster. Terdapat titik temu lokasi bersama dan korespondensi kampanye terkoordinasi yang merujuk pada skenario pendanaan serupa pada kasus lain. Data berbasis transaksi, lokasi pertemuan, dan aktivitas posting menunjukkan indikasi koordinasi finansial lintas aktor yang kemungkinan membentuk sindikat pendanaan, namun bukti belum cukup untuk atribusi pidana pasti tanpa validasi lintas sumber tambahan.

## Alasan Utama

- Aktor inti berperan sebagai hub pendanaan lintas akun
- Overlap perangkat/IP dan kedekatan lokasi antar aktor
- Titik temu lokasi sering dan klaster yang saling terkait
- Post terkait menunjukkan kampanye terkoordinasi dengan referensi kasus pendanaan serupa
- Tautan lintas kasus (kebakaran gudang, propaganda) memperkuat jaringan sirkulasi informasi/dana

## Pola Koordinasi

- Transfer kecil berulang antar profil melalui beberapa kanal (tunai, transfer bank, dompet digital)
- Hub pendanaan utama menghubungkan aktor-aktor lintas klaster (klaster-2)
- Kampanye konten terkoordinasi dengan referensi kasus terkait
- Spot_sering pertemuan di berbagai kota di Jawa Barat dan DKI Jakarta
- Tanda-tanda headquarter/bridge accounts yang muncul lintas kasus

## Aktor Inti

- **Galih Valentina** (`-`) | peran: aktor_pendanaan | confidence: 0.82 | alasan: Hub transisi pendanaan antar profil utama; menghubungkan transfer antar beberapa akun dan kanal
- **Wisnu Handoko** (`-`) | peran: aktor_pendanaan | confidence: 0.78 | alasan: Penghubung transfer antar akun utama; terlibat dalam jaringan klaster-2
- **Mamat Abdi Hamdani** (`-`) | peran: aktor_pendanaan | confidence: 0.75 | alasan: Aktivitas pendanaan berantai antara akun dalam graf
- **Jefri Firdaus** (`-`) | peran: aktor_pendanaan | confidence: 0.7 | alasan: Transaksi bridging antar akun dalam klaster pendanaan
- **Nani Nugroho** (`-`) | peran: aktor_pendanaan | confidence: 0.65 | alasan: Indikator sinyal pendanaan dalam jaringan lintas wilayah
- **Lutfi Junaedi** (`-`) | peran: aktor_pendanaan | confidence: 0.6 | alasan: Akun dengan koneksi lintas wilayah; bagian dari jaringan pendanaan
- **Hadi Didik Widodo** (`-`) | peran: aktor_pendanaan | confidence: 0.65 | alasan: Konektor jaringan pendanaan di wilayah Jawa Barat
- **Sandy Ramadhan** (`-`) | peran: aktor_pendanaan | confidence: 0.7 | alasan: Sinyal pendanaan dan keterkaitan transfer lintas akun
- **Adi Supriyanto** (`-`) | peran: aktor_pendanaan | confidence: 0.6 | alasan: Terlihat terhubung sebagai aktor pendanaan lintas kasus; bridging akun

## Relasi Kunci

- prof-b52f349a0c -> prof-7e364ba897 | MENTRANSFER | confidence: 0.85 | alasan: Hub utama transfer antar profil inti; kanal dompet digital; indikasi koordinasi finansial
- prof-739dafdf3b -> prof-8f45d00a8b | MENTRANSFER | confidence: 0.82 | alasan: Hub pendanaan lanjutan; transfer dompet digital
- prof-b52f349a0c -> prof-7e364ba897 | MENTRANSFER | confidence: 0.8 | alasan: Transfer bank yang menghubungkan profil inti
- prof-7e364ba897 -> prof-739dafdf3b | MENTRANSFER | confidence: 0.8 | alasan: Transfer tunai antar akun; sinyal koordinasi finansial
- prof-5d42267c65 -> prof-c1bd6e64bd | MENTRANSFER | confidence: 0.75 | alasan: Bridge ke akun pendanaan lain melalui transfer bank
- prof-044e991493 -> prof-76862d2c17 | MENTRANSFER | confidence: 0.8 | alasan: Transfer bank antara profil pendanaan; memperluas jaringan
- prof-8f45d00a8b -> prof-3708908c68 | MENTRANSFER | confidence: 0.78 | alasan: Dompet digital transfer; memperluas lingkup pendanaan
- prof-5d42267c65 -> prof-739dafdf3b | MENTRANSFER | confidence: 0.75 | alasan: Dompet digital transfer antar akun pendanaan
- prof-b52f349a0c -> prof-8f45d00a8b | MENTRANSFER | confidence: 0.85 | alasan: Transfer tunai sebagai hub antara akun pendanaan
- prof-739dafdf3b -> prof-5d42267c65 | MENTRANSFER | confidence: 0.8 | alasan: Transfer tunai antar akun pendanaan, memperkuat jaringan
- prof-7e364ba897 -> prof-6c0beb297b | MENTRANSFER | confidence: 0.75 | alasan: Transfer dompet digital antar klaster
- prof-3708908c68 -> prof-739dafdf3b | MENTRANSFER | confidence: 0.75 | alasan: Transfer bank; memperluas lingkup jaringan pendanaan

## Bukti Utama

- Transaksi pendanaan lintas profil dengan kanal berbeda (tunai, transfer_bank, dompet_digital) menunjukkan jaringan pendanaan terkoordinasi
- Hub pendanaan utama (Galih Valentina) mengaitkan beberapa aktor inti dan bridging akun
- Titik temu lokasi yang konsisten dan spot_sering mendukung sinyal koordinasi
- Posting terkoordinasi yang merujuk pada kasus pendanaan mencegah kebutuhan forced dispersal dana
- Sinyal lintas kasus (kebakaran gudang, propaganda) memperkuat jaringan sinyal pendanaan

## Bukti Lemah

- Transaksi relatif kecil dan tidak menandakan aktivitas ilegal eksplisit
- Beberapa akun memiliki informasi bios yang minim
- Perlu validasi lintas sumber untuk konfirmasi
- Kemungkinan dapat dimanfaatkan untuk aktivitas legal/legitimat seiring waktu

## Rekomendasi Lanjutan

- Uji graf transfer vs graf sosial untuk konfirmasi koordinasi
- Periksa overlap perangkat/IP dan titik temu lokasi bersama
- Prioritaskan bridge account lintas kasus untuk audit menyeluruh
- Audit forensik perangkat untuk klaster profil yang saling terkait
- Koordinasikan dengan tim cyber/forensik untuk analisis lanjutan
- Kaji potensi implikasi hukum dan pelaporan ke pihak terkait jika diperlukan

## Narasi Analisis

Dari data yang ada, terlihat jaringan aktor pendanaan yang terhubung lintas wilayah dengan hub utama dan beberapa akun bridging. Bukti utama berupa pola transfer berulang antar profil melalui berbagai kanal, serta adanya spot pertemuan yang sering. Kampanye konten terkoordinasi dan referensi kasus terkait memperkuat dugaan koordinasi. Namun, data masih bersifat indikatif dan perlu validasi lintas sumber untuk atribusi sindikat yang lebih tegas. Rekomendasi fokus pada konfirmasi koordinasi finansial melalui analisis graf dan forensik digital.

## Statistik Bundel

- jumlah_laporan: 1
- jumlah_skor_risiko: 1
- jumlah_transaksi: 12
- jumlah_kampanye: 0
- jumlah_profil: 10
- jumlah_lokasi: 42
- jumlah_postingan: 123
- jumlah_node_graf: 10
- jumlah_edge_graf: 12
