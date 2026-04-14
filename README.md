# Orkestrasi OSINT TIA / NAA / PTA

Workspace ini memuat dua lapisan yang saling melengkapi:

1. Generator data uji berita dan persona yang sudah tersedia di root project.
2. Backend orkestrasi agent di folder `orchestration/` untuk memproses data tersebut dengan service nyata: OpenAI, LangChain, LangGraph, Kafka, Redis Streams, PostgreSQL, Neo4j, dan Celery.

Data yang ada di `news/` dan `dataset/` adalah data uji internal. Backend agent tetap diperlakukan sebagai runtime nyata: event masuk lewat Kafka, TIA memproses dengan LangGraph dan OpenAI, NAA membaca hasil lewat Redis Streams dan meng-upsert ke Neo4j, lalu PTA berjalan sebagai worker Celery terpisah untuk analitik prediktif.

Versi orkestrasi saat ini sudah memakai pola **graph terkontrol**:

- TIA: planner -> retrieval -> verifier -> threat assessment -> critic -> evidence ranking -> briefing review
- NAA: candidate relation extraction -> relation verifier -> graph analytics -> cluster interpreter
- PTA: scope planner -> feature builder -> anomaly/forecast -> uncertainty interpreter -> recommendation critic

## Stack Backend

- `OpenAI` untuk ekstraksi entitas, penilaian ancaman, ekstraksi relasi, dan rekomendasi aksi.
- `LangChain` untuk prompt orchestration dan structured output.
- `LangGraph` untuk state machine TIA.
- `Kafka` untuk ingestion OSINT.
- `Redis Streams` untuk A2A TIA -> NAA serta hasil ke jalur review.
- `Celery` untuk job PTA yang berat.
- `PostgreSQL` untuk store relasional, audit trail, briefing TIA, dan hasil PTA.
- `Neo4j` untuk graph persistence dan analitik jaringan.

## Struktur Modul

- `orchestration/config.py`: pemuatan env dan validasi fail-fast.
- `orchestration/schema.py`: kontrak event dan payload typed.
- `orchestration/openai_stack.py`: klien OpenAI nyata dan wrapper LangChain.
- `orchestration/mcp.py`: gateway tunggal ke PostgreSQL dan Neo4j.
- `orchestration/seed_data.py`: import data uji ke PostgreSQL dan Neo4j, plus publisher Kafka.
- `orchestration/tia_graph.py`: pipeline LangGraph untuk TIA.
- `orchestration/naa_worker.py`: worker Redis Streams untuk NAA.
- `orchestration/pta_tasks.py`: task Celery untuk PTA.
- `orchestration/hitl.py`: routing payload review.
- `orchestration/cli.py`: entrypoint operasi backend.

## Variabel Lingkungan

Konfigurasi utama ada di `.env` dan `.env.example`. Variabel wajib:

- `OPENAI_API_KEY`
- `OPENAI_MODEL`
- `KAFKA_BOOTSTRAP_SERVERS`
- `KAFKA_TOPIC_OSINT_RAW`
- `KAFKA_CONSUMER_GROUP_TIA`
- `REDIS_URL`
- `REDIS_STREAM_TIA_OUT`
- `REDIS_STREAM_NAA_OUT`
- `REDIS_STREAM_CLUSTER_ALERT`
- `REDIS_STREAM_HITL_REVIEW`
- `REDIS_STREAM_PTA_RESULT`
- `CELERY_BROKER_URL`
- `CELERY_RESULT_BACKEND`
- `POSTGRES_DSN`
- `NEO4J_URI`
- `NEO4J_USERNAME`
- `NEO4J_PASSWORD`
- `MCP_SHARED_TOKEN`

Startup backend akan gagal cepat bila `OPENAI_API_KEY` atau endpoint service inti belum diisi.

Untuk stack Docker bawaan repo ini, Neo4j dikonfigurasi dengan:

- `NEO4J_USERNAME=neo4j`
- `NEO4J_PASSWORD=123`

## Jalur Yang Disarankan

Untuk Windows lokal, jalur utama sekarang adalah **tanpa Docker**. Anda menyalakan service infrastruktur sendiri, lalu memakai launcher backend dari repo ini.

`npm run back` hanya:

1. mengecek service inti
2. menjalankan `seed`
3. menyalakan worker `TIA`, `NAA`, dan `PTA`
4. memverifikasi worker tidak mati di awal
5. menjalankan `publish-osint`

`npm run back` tidak:

1. mengunduh Java
2. menginstal PostgreSQL
3. menginstal Memurai
4. menginstal Neo4j
5. menginstal Kafka
6. membunuh service sistem Anda di port infrastruktur

## Instal Dependency Python

```bash
pip install -r requirements.txt
```

## Setup Manual Windows Tanpa Docker

Urutan yang disarankan:

1. Install Java JDK 21
2. Install PostgreSQL
3. Install Memurai
4. Install Neo4j
5. Install Apache Kafka
6. Isi `.env`
7. Jalankan seed dan worker backend

## Link Download Resmi

- Temurin JDK 21: `https://adoptium.net/`
- PostgreSQL Windows: `https://www.postgresql.org/download/windows/`
- Memurai: `https://www.memurai.com/`
- Neo4j: `https://neo4j.com/download/`
- Apache Kafka: `https://kafka.apache.org/downloads`

## 1. Install Java JDK 21

Install JDK 21 terlebih dahulu.

Langkah:

1. Buka halaman Temurin.
2. Pilih Windows.
3. Pilih JDK 21.
4. Install sampai selesai.
5. Tutup dan buka ulang terminal.
6. Verifikasi:

```powershell
java -version
```

Kalau `java -version` gagal, berarti `PATH` Java belum benar.

## 2. Install PostgreSQL

Install PostgreSQL untuk Windows, lalu buat user dan database untuk backend.

Nilai yang direkomendasikan:

- host: `localhost`
- port: `5432`
- database: `intel_orchestrator`
- user aplikasi: `123`
- password aplikasi: `123`

Setelah PostgreSQL terpasang, buka `psql` atau `pgAdmin`, lalu jalankan:

```sql
CREATE USER "123" WITH PASSWORD '123';
CREATE DATABASE intel_orchestrator OWNER "123";
```

Kalau user atau database sudah ada, cukup sesuaikan `.env`.

Contoh:

```env
POSTGRES_DSN=postgresql://123:123@localhost:5432/intel_orchestrator
```

## 3. Install Memurai

Untuk Windows native, gunakan Memurai sebagai server yang kompatibel dengan Redis.

Langkah:

1. Unduh installer Memurai.
2. Install sebagai Windows service.
3. Pastikan servicenya berjalan.
4. Pastikan port `6379` aktif.

Contoh:

```env
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2
```

## 4. Install Neo4j

Pilih salah satu:

- `Neo4j Desktop` jika ingin setup lebih cepat.
- `Neo4j Community` jika ingin service yang lebih langsung.

Yang wajib sesuai backend ini:

- Bolt aktif di `7687`
- username sesuai `.env`
- password sesuai `.env`

Contoh:

```env
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=123
```

## 5. Install Apache Kafka

Gunakan distribusi binary Kafka dan jalankan mode KRaft single node.

Contoh lokasi:

```text
C:\tools\kafka
```

Masuk ke folder Kafka:

```powershell
cd C:\tools\kafka
```

Buat UUID storage:

```powershell
.\bin\windows\kafka-storage.bat random-uuid
```

Ambil UUID yang keluar, lalu format storage:

```powershell
.\bin\windows\kafka-storage.bat format --standalone -t <UUID_HASIL> -c .\config\server.properties
```

Jalankan broker:

```powershell
.\bin\windows\kafka-server-start.bat .\config\server.properties
```

Contoh:

```env
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_TOPIC_OSINT_RAW=osint_raw
KAFKA_CONSUMER_GROUP_TIA=tia_group
```

## 6. Isi `.env`

Minimal isi nilai berikut:

```env
OPENAI_API_KEY=<KUNCI_VALID_ANDA>
OPENAI_MODEL=gpt-5-nano
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
REDIS_URL=redis://localhost:6379/0
POSTGRES_DSN=postgresql://123:123@localhost:5432/intel_orchestrator
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=123
```

Kalau user, password, host, atau port Anda berbeda, ubah `.env` agar sama persis.

## 7. Seed Data dan Jalankan Worker

Urutan yang benar untuk backend manual adalah:

1. `seed`
2. nyalakan worker `TIA`
3. nyalakan worker `NAA`
4. nyalakan worker `PTA`
5. baru `publish-osint`

Jangan membalik urutan ini jika tujuan Anda adalah melihat satu kasus diproses end-to-end saat itu juga.

Kalau Anda memakai launcher, jalur termudah tetap:

```bash
npm run back:docker
```

Perintah itu akan menghidupkan stack, seed, publish, dan menjalankan worker sekaligus.

Kalau ingin manual per terminal, gunakan urutan di bawah ini.

Setelah semua service hidup:

```bash
python -m orchestration.cli seed
```

Lalu buka tiga terminal terpisah dan jalankan:

```bash
python -m orchestration.cli run-tia
```

```bash
python -m orchestration.cli run-naa
```

```bash
python -m orchestration.cli run-pta-worker
```

Setelah ketiga worker hidup, baru terbitkan event OSINT:

```bash
python -m orchestration.cli publish-osint
```

Kalau ingin satu kasus saja:

```bash
python -m orchestration.cli publish-osint --id 94bc7039
```

Catatan penting:

log sukses dari `publish-osint` hanya berarti event berhasil dikirim ke Kafka.

Log itu belum membuktikan bahwa TIA, NAA, dan PTA sudah selesai memproses kasus.

Untuk memastikan kasus benar-benar jalan, Anda harus melihat hasilnya di PostgreSQL, Redis, atau Neo4j.

## Cara Cek Cepat Sebelum Menjalankan Worker

```powershell
java -version
```

```powershell
Test-NetConnection localhost -Port 5432
```

```powershell
Test-NetConnection localhost -Port 6379
```

```powershell
Test-NetConnection localhost -Port 7687
```

```powershell
Test-NetConnection localhost -Port 9092
```

Kalau semua port di atas merespons, launcher backend biasanya sudah bisa lanjut.

## Shortcut NPM

Menyalakan seluruh worker setelah service aktif:

```bash
npm run back
```

Script ini akan:

1. mengecek Kafka, Redis, PostgreSQL, dan Neo4j dari `.env`
2. menjalankan `seed`
3. menyalakan worker `TIA`, `NAA`, dan `PTA` sebagai proses background
4. menunggu beberapa detik untuk memastikan worker tidak langsung mati
5. menjalankan `publish-osint`
6. menyimpan PID proses ke `runtime_state/backend-processes.json`
7. menulis log ke folder `logs/`

Kalau ingin tetap memakai container:

```bash
npm run back:docker
```

Untuk melihat status proses:

```bash
npm run back:status
```

Untuk menghentikan worker yang dinyalakan launcher:

```bash
npm run back:stop
```

## Jika `npm run back` Masih Gagal

- Cek `.env`, biasanya masalah ada pada host, port, atau password yang tidak cocok.
- Cek apakah service benar-benar hidup, bukan hanya terpasang.
- Cek log worker di folder `logs/`.
- Jalankan `npm run back:status`.
- Jalankan `npm run back:stop` bila ada proses worker lama yang masih tertinggal.

## Urutan Operasional Manual

1. Seed relasional dan graf:

```bash
python -m orchestration.cli seed
```

2. Jalankan TIA di terminal pertama:

```bash
python -m orchestration.cli run-tia
```

3. Jalankan NAA di terminal kedua:

```bash
python -m orchestration.cli run-naa
```

4. Jalankan PTA worker di terminal ketiga:

```bash
python -m orchestration.cli run-pta-worker
```

5. Terbitkan berita OSINT dari dataset ke Kafka di terminal keempat:

```bash
python -m orchestration.cli publish-osint
```

Kalau ingin menerbitkan satu kasus saja:

```bash
python -m orchestration.cli publish-osint --id 94bc7039
```

Kalau ingin membatasi jumlah berita:

```bash
python -m orchestration.cli publish-osint --limit 5
```

### Arti log `publish-osint`

Jika terminal `publish-osint` hanya menampilkan log koneksi Kafka lalu selesai tanpa error, itu berarti:

- producer berhasil terkoneksi,
- event berhasil didorong ke topic,
- dan sekarang worker yang sedang hidup akan mengambil event tersebut.

Itu belum berarti:

- kasus sudah masuk ke `tia_briefings`,
- jaringan sudah masuk ke Neo4j,
- atau hasil PTA sudah selesai.

Karena itu, `publish-osint` harus selalu dipasangkan dengan worker yang memang sedang berjalan.

### Tanda bahwa TIA benar-benar sedang bekerja

- ada log `TIA deteksi_sinyal_awal selesai`
- ada request `POST https://api.openai.com/v1/chat/completions`
- tidak ada traceback di terminal TIA
- setelah selesai, ada data baru di PostgreSQL

### Tanda bahwa NAA benar-benar sedang bekerja

- worker NAA membaca stream Redis dari hasil TIA
- Neo4j mulai menerima node dan edge baru
- ada payload graf untuk kasus yang sama

### Tanda bahwa PTA benar-benar sedang bekerja

- worker Celery menerima tugas dari hasil NAA
- PostgreSQL menerima hasil baru di tabel PTA
- payload review ikut bertambah

## Alur Data

### TIA

- Kafka consumer membaca `osint_raw`.
- Relevance classifier menapis noise awal dan membuat sinyal aturan awal.
- Planner retrieval memilih tool MCP yang perlu dipanggil.
- OpenAI mengekstrak entitas terstruktur lalu memverifikasinya.
- Fuzzy watchlist matching dilakukan ke PostgreSQL melalui MCP.
- OpenAI membuat penilaian ancaman awal lalu menjalankan critic pass kedua.
- Bukti diperingkat sebelum penyusunan briefing.
- OpenAI menyusun intelligence briefing lalu briefing direview lagi sebelum publish.
- Hasil diterbitkan ke Redis Stream `tia_out` dan payload review dikirim ke jalur HITL.

### NAA

- Redis Stream consumer membaca `tia_out`.
- OpenAI mengekstrak relasi `subject-predicate-object` kandidat.
- Verifier relasi membuang relasi lemah atau terlalu inferensial.
- MCP meng-upsert relasi valid ke Neo4j.
- Worker menghitung Louvain communities, PageRank, betweenness, eigenvector, dan bridge score.
- Interpreter cluster menjelaskan broker utama, cluster penting, dan perubahan struktural.
- Backend mengeluarkan `viz-ready JSON` yang lebih kaya untuk UI di masa depan.
- Alert klaster diterbitkan ke `cluster_alert` jika ada perubahan struktur yang signifikan.
- Event NAA diterbitkan ke `naa_out` dan memicu PTA.

### PTA

- Celery menerima event dari NAA.
- Scope planner memilih retrieval historis yang paling relevan.
- MCP memuat konteks historis dari PostgreSQL dan Neo4j.
- Feature matrix dibangun dari domain temporal, spasial, relasional, dan transaksional.
- `IsolationForest` dan autoencoder dipakai untuk anomali.
- `RandomForestRegressor` dipakai untuk baseline forecast.
- OpenAI menginterpretasikan ketidakpastian model.
- OpenAI menyusun rekomendasi aksi lalu menjalankan critic pass untuk rekomendasi.
- Hasil diterbitkan ke `pta_result` dan juga diarahkan ke jalur review.

## Cara Memastikan Satu Kasus Benar-Benar Terdeteksi

Contoh kasus yang sering dipakai:

```bash
python -m orchestration.cli publish-osint --id 94bc7039
```

Setelah itu, jangan menilai keberhasilan hanya dari log Kafka.

Lakukan verifikasi berikut.

### Verifikasi TIA di PostgreSQL

Masuk ke PostgreSQL:

```bash
docker exec -it intel-postgres psql -U 123 -d intel_orchestrator
```

Lihat tabel yang tersedia:

```sql
\dt
```

Cek hasil TIA:

```sql
SELECT id_berita, level_ancaman, skor_agregat
FROM tia_briefings
WHERE id_berita = '94bc7039'
ORDER BY dibuat_pada DESC;
```

Kalau query ini mengembalikan baris, berarti TIA benar-benar memproses kasus tersebut.

### Verifikasi orang yang terhubung ke kasus

Masih di PostgreSQL, buka payload briefing:

```sql
SELECT briefing_json
FROM tia_briefings
WHERE id_berita = '94bc7039'
ORDER BY dibuat_pada DESC
LIMIT 1;
```

Di dalam JSON ini, fokus ke:

- `entitas`
- `hit_watchlist`

Jika `hit_watchlist` berisi data, berarti sistem tidak hanya mendeteksi kasus, tetapi juga menemukan orang yang cocok dengan watchlist.

### Verifikasi graph di Neo4j

Masuk ke Neo4j Browser:

- URL: `neo4j://localhost:7687`
- Username: `neo4j`
- Password: `123`

Cek apakah graf hidup:

```cypher
MATCH (n) RETURN count(n);
```

Cek relasi terbaru:

```cypher
MATCH (a)-[r]-(b)
RETURN a, r, b
LIMIT 50;
```

Kalau ingin fokus ke tiga kasus uji:

```cypher
MATCH (k:Kasus)
RETURN k;
```

### Verifikasi PTA

Masih di PostgreSQL:

```sql
SELECT trace_id, skor_ensemble, probabilitas_eskalasi, confidence_score
FROM pta_results
ORDER BY dibuat_pada DESC
LIMIT 10;
```

Kalau tabel ini bertambah setelah satu kasus diterbitkan, berarti rantai TIA -> NAA -> PTA berjalan.

### Verifikasi review manusia

```sql
SELECT trace_id, risk_level, approver_role
FROM hitl_reviews
ORDER BY dibuat_pada DESC
LIMIT 10;
```

Kalau tabel ini bertambah, berarti hasil akhir sudah mencapai jalur review.

## Tiga Cara Menjalankan Backend

### Cara 1 — Paling mudah

```bash
npm run back:docker
```

Gunakan ini jika ingin stack hidup sekaligus.

### Cara 2 — Manual penuh

Gunakan empat terminal:

- terminal 1: `python -m orchestration.cli run-tia`
- terminal 2: `python -m orchestration.cli run-naa`
- terminal 3: `python -m orchestration.cli run-pta-worker`
- terminal 4: `python -m orchestration.cli publish-osint --id 94bc7039`

### Cara 3 — Launcher tanpa Docker

```bash
npm run back
```

Gunakan ini hanya jika Kafka, Redis, PostgreSQL, dan Neo4j sudah Anda hidupkan sendiri di mesin lokal.

## Analisis Kasus Menjadi Artefak File

Jika tujuan Anda adalah melihat agent menalar satu kasus dari `dataset/kasus.json` lalu menghasilkan artefak yang bisa dibaca manusia, gunakan command berikut:

```bash
.venv\Scripts\python.exe -m orchestration.cli analisis-kasus --id kasus-pendanaan-mencurigakan
```

Atau untuk kasus lain:

```bash
.venv\Scripts\python.exe -m orchestration.cli analisis-kasus --id kasus-kebakaran-gudang
```

```bash
.venv\Scripts\python.exe -m orchestration.cli analisis-kasus --id kasus-propaganda-burst
```

Command ini:

1. mengambil bundel kasus dari PostgreSQL dan Neo4j melalui MCP
2. memuat laporan, skor risiko, transaksi, kampanye, profil, lokasi, postingan, dan graph terkait
3. meminta OpenAI melalui LangChain untuk menyusun dossier sindikat terstruktur
4. menulis hasil ke folder `analisa/`

Artefak yang dibuat:

- `JSON`
- `MD`
- `CSV` ringkasan
- `CSV` aktor
- `CSV` relasi
- `CSV` transaksi
- `XLSX`
- `DOCX`
- `PDF`
- `manifest.json`

Setiap run membuat direktori baru dengan pola:

```text
analisa/<id_kasus>/<id_kasus>_<timestamp>_<fingerprint>/
```

File tidak ditimpa.

Setiap artefak memiliki fingerprint berbasis `SHA-256`.

`manifest.json` menyimpan:

- fingerprint utama analisa
- nama file
- ukuran file
- fingerprint per file

Contoh hasil yang diharapkan:

```text
analisa/kasus-pendanaan-mencurigakan/kasus-pendanaan-mencurigakan_20260414_132500_ab12cd34ef56gh78/
```

Format ini dipilih agar:

- hasil lama tetap ada
- setiap analisa punya identitas kuat
- file mudah diaudit dan dibandingkan

Kasus yang paling cocok untuk uji dugaan sindikat adalah:

```text
kasus-pendanaan-mencurigakan
```

Karena dataset ini memiliki jejaring transaksi yang paling jelas untuk penalaran aktor inti, relasi kunci, dan pola koordinasi.

## Data Uji Yang Dipakai

Data uji tetap berasal dari file yang sudah ada:

- `news/dataset.jsonl`
- `dataset/profil.json`
- `dataset/kontak.json`
- `dataset/akun.json`
- `dataset/lokasi.json`
- `dataset/transaksi.json`
- `dataset/kampanye.json`
- `dataset/postingan.json`
- `dataset/laporan.json`
- `dataset/skor_risiko.json`
- `dataset/kasus.json`

Seed pipeline memindahkan data tersebut ke PostgreSQL dan Neo4j agar runtime agent tidak membaca file langsung saat memproses event.

## UI

UI belum dibangun pada tahap ini. Backend sudah menyiapkan keluaran yang bisa dipakai Flask atau React nantinya:

- briefing TIA
- payload review HITL
- event NAA
- `viz-ready JSON`
- hasil forecast PTA

## Catatan Operasional

- Tidak ada automated test harness pada fase ini.
- Fokus tahap ini adalah wiring backend nyata dan kontrak antar service.
- Jika ingin menambah UI setelah backend stabil, jalur yang paling natural adalah membaca `viz-ready JSON` dan payload HITL dari Redis atau PostgreSQL.
