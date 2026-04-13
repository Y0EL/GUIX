# News + Persona Dataset Generator

Workspace ini sekarang punya dua jalur generator:

1. `generate.py` + `render.py` untuk dataset berita dan portal HTML.
2. `generate_profiles.py`, `generate_cases.py`, dan `generate_dataset.py` untuk paket **persona Indonesia + multi-case correlation dataset**.

Semua data di repo ini ditujukan untuk **demo internal, testing agent, dan simulasi workflow**. Bukan untuk identifikasi orang nyata, doxxing, deep web lookup, atau atribusi final terhadap pihak sungguhan.

## Setup

```bash
pip install -r requirements.txt
```

Untuk generator berita lama, set `OPENAI_API_KEY` sesuai kebutuhan. Generator persona/case baru bisa pakai dua cara:

1. Hardcode langsung di [synthetic_dataset.py](C:/Users/WIN10/Desktop/GUIX/synthetic_dataset.py) pada `HARDCODED_OPENAI_API_KEY` dan `HARDCODED_OPENAI_MODEL`.
2. Pakai environment variable `OPENAI_API_KEY` dan `OPENAI_MODEL`.

Kalau key tidak diisi, generator persona/case akan fallback ke generator lokal.

## Generator Berita

```bash
# Generate artikel
python generate.py --count 20 --out-dir out_news

# Render portal berita statis
python render.py
```

Output utamanya ada di `out_news/`:

```text
out_news/
|-- index.html
|-- berita/
|-- images/
`-- dataset.jsonl
```

## Generator Persona + Kasus

### 1. Generate persona

```bash
python generate_profiles.py --count 300 --out-dir out_profiles
```

Kalau ingin download avatar dari 100k-faces:

```bash
python generate_profiles.py --count 300 --out-dir out_profiles --with-images --model gpt-5-nano
```

Avatar memakai sumber:
- `https://100k-faces.vercel.app/api/random-image`
- provider: `100k-faces`

### 2. Tambahkan kasus ke dataset yang sudah ada

```bash
python generate_cases.py --out-dir out_profiles --cases warehouse_fire,suspicious_funding,propaganda
```

### 3. Generate dataset penuh sekaligus

```bash
python generate_dataset.py --count 300 --out-dir out_profiles
```

Atau dengan avatar lokal:

```bash
python generate_dataset.py --count 300 --out-dir out_profiles --with-images
```

## Struktur Output Persona

```text
out_profiles/
|-- profiles.json
|-- accounts.json
|-- contacts.json
|-- preferences.json
|-- photos.json
|-- posts.json
|-- friends.json
|-- network.json
|-- locations.json
|-- cases.json
|-- transactions.json
|-- funding_alerts.json
|-- campaigns.json
|-- message_clusters.json
|-- crawling.json
|-- entities.json
|-- alerts.json
|-- risk_scores.json
|-- reports.json
`-- images/
```

## Contoh Kasus

Dataset default saat menjalankan `generate_dataset.py` berisi 3 kasus utama:

1. `warehouse_fire`
   Kebakaran gudang logistik di area industri, dengan sinyal ledakan awal, pergerakan kendaraan sebelum api membesar, narasi saksi yang tidak sepenuhnya konsisten, dan akun yang aktif hampir bersamaan setelah kejadian.

2. `suspicious_funding`
   Pola pendanaan tersebar dengan transfer kecil berulang, shared device atau shared IP, titik temu lokasi yang sama, dan hubungan antar akun yang tidak selalu terlihat dari graf pertemanan biasa.

3. `propaganda`
   Satu akun pusat memunculkan narasi, lalu beberapa akun lain mengamplifikasi dengan wording mirip, jeda waktu sempit, dan overlap dengan aktor dari kasus lain.

## Isi Dataset Baru

Dataset persona baru berisi:
- persona Indonesia dengan `email`, nomor Indonesia dummy, `latitude`, `longitude`, akun sosial, minat, dan ringkasan profil
- graph sosial yang **tidak fully connected**
- mayoritas akun berdiri sendiri atau punya koneksi tipis
- beberapa cluster kecil yang rapat
- 1-2 bridge account yang menghubungkan cluster
- shared meeting points agar agent bisa menguji korelasi lokasi + waktu

Kasus default v1:
- `warehouse_fire`
- `suspicious_funding`
- `propaganda`

Secara praktis, dataset ini memuat 3 lapisan:
- `persona layer`: identitas, kontak, minat, akun, aktivitas, dan lokasi dasar
- `network layer`: friendship edges, bridge accounts, meeting point overlap, amplifikasi pesan, dan transfer edge
- `case layer`: crawling data, entity extraction, alerts, risk scores, reports, campaigns, transactions, dan message clusters

## Contoh Field Persona

```json
{
  "profile_id": "prof-1234567890",
  "full_name": "Nama Pengguna",
  "city": "Bekasi",
  "province": "Jawa Barat",
  "latitude": -6.234901,
  "longitude": 106.989611,
  "avatar_source": "100k-faces",
  "case_links": []
}
```

Kontak dibuat dummy tetapi konsisten lintas file:
- email domain aman seperti `example.com` dan `mail.test`
- nomor Indonesia format lokal `08...`
- nomor internasional format `+62...`

## Extraction Schema

Setiap persona punya blok `extracted_profile` yang mengikuti kebutuhan metadata ala profiler secara aman:
- `personal_information`
- `locations`
- `accounts`
- `statistics`
- `friends`
- `photos`
- `posts`
- `web_search_results`
- `preferences`
- `contact_info`
- `synopsis`
- `case_links`

Field sensitif yang sengaja **tidak** dibuat:
- password
- IMSI
- deep web lookup nyata
- data breach nyata
- doxxing field
- identitas orang riil

## Cara Uji Pengkajian Kasus

Berikut alur uji yang disarankan kalau kamu ingin menilai apakah agent atau dashboard bisa membaca kasus dengan baik:

1. Mulai dari `reports.json` dan `risk_scores.json`
   Lihat ringkasan tiap kasus, skor risiko, dan driver utamanya.

2. Turun ke `alerts.json`, `entities.json`, dan `crawling.json`
   Cek apakah agent bisa menjelaskan kenapa suatu kasus naik ke medium atau high, misalnya karena ledakan awal, copy-paste wording, shared device, atau overlap lokasi.

3. Validasi aktor utama lewat `profiles.json` dan `case_links`
   Cari siapa saja profil yang terhubung ke satu kasus, lalu cek apakah ada profil yang muncul di lebih dari satu kasus.

4. Uji korelasi jaringan lewat `friends.json`, `network.json`, dan `transactions.json`
   Pastikan agent bisa membedakan:
   - koneksi langsung
   - bridge account
   - overlap lokasi tanpa pertemanan langsung
   - hubungan finansial tanpa relasi sosial yang jelas

5. Uji korelasi lokasi lewat `locations.json`
   Bandingkan `meeting_point_id`, `latitude`, `longitude`, dan `observed_at` untuk melihat apakah beberapa aktor pernah berada di titik yang sama dalam rentang waktu yang dekat.

6. Uji narasi dan amplifikasi lewat `posts.json`, `campaigns.json`, dan `message_clusters.json`
   Cek apakah agent bisa menemukan akun pusat, akun pengikut, kemiripan frasa, dan pola waktu posting.

7. Susun ulang kesimpulan
   Agent yang bagus harus bisa menulis ulang:
   - kronologi
   - aktor terkait
   - sinyal penguat
   - korelasi lintas kasus
   - prioritas tindak lanjut

Contoh pertanyaan uji:
- siapa akun penghubung antara kasus warehouse fire dan propaganda?
- siapa saja yang tidak berteman langsung tapi pernah muncul di titik lokasi yang sama?
- akun mana yang terkait transfer berulang dan juga aktif di kampanye narasi?
- sinyal apa yang paling kuat menaikkan risk score suatu kasus?
- dari semua kasus, siapa aktor yang paling sering overlap?

## Stack Agentic Yang Direkomendasikan

Untuk use case kita, arsitektur agentic yang paling cocok adalah:

1. `TIA` - Threat Intelligence Agent
   Fokus ke pengumpulan dan normalisasi data OSINT, crawling, entity extraction, timeline awal, dan penandaan sinyal.

2. `NAA` - Network Analysis Agent
   Fokus ke graph reasoning: relasi akun, bridge account, overlap lokasi, transfer edge, amplifikasi pesan, dan cluster detection.

3. `PTA` - Predictive Threat Agent
   Fokus ke risk scoring, escalation logic, early warning, dan penyusunan daily intelligence brief.

### Pilihan stack

#### LangChain + LangGraph

Ini yang paling direkomendasikan untuk project kita.

Kenapa cocok:
- mudah mulai cepat dengan agent abstraction
- tetap bisa turun ke orchestration graph yang rigid saat workflow makin kompleks
- cocok untuk stateful pipeline yang panjang
- enak untuk multi-step reasoning, tool calling, checkpointing, dan human-in-the-loop
- paling pas untuk arsitektur 3 agent yang saling kirim state lalu berujung ke laporan harian

Cara pakainya untuk kasus kita:
- TIA jalan dulu untuk ingest data, extraction, dan summarization
- output TIA masuk ke NAA untuk graph linking dan network scoring
- output NAA masuk ke PTA untuk threat scoring, escalation, dan daily brief
- semua state disimpan per case/day supaya rerun dan audit trail mudah

#### CrewAI

CrewAI cocok kalau kamu ingin framing multi-agent yang lebih eksplisit sejak awal, dengan role, task, memory, dan flow yang sudah terasa “crew-like”.

Nilainya untuk kita:
- bagus untuk demo multi-agent yang mudah dipahami stakeholder
- cocok untuk assignment role TIA/NAA/PTA secara eksplisit
- cepat untuk proof-of-concept dan task delegation

Tapi buat use case kita, aku lihat CrewAI lebih cocok sebagai opsi kedua:
- bagus untuk menunjukkan “ada 3 agent yang kerja bareng”
- kurang ideal kalau kita ingin graph orchestration yang sangat ketat, stateful, dan mudah diaudit per tahap

#### OpenHands

OpenHands menurutku bukan stack utama untuk kasus ini.

Alasannya:
- kekuatan utamanya ada di coding agents, SDK/CLI/cloud coding workflow, dan autonomous software tasks
- sangat bagus untuk bantu engineering automation, code review, patching, evaluasi, atau outer-loop development
- tapi bukan pilihan paling natural untuk intelligence workflow yang butuh orchestrated analysis pipeline lintas OSINT, graph, scoring, dan reporting

Posisi OpenHands yang masuk akal di project ini:
- dipakai tim engineering untuk mempercepat development agentic platform
- dipakai bantu generate evaluasi, test harness, ingestion adapters, atau analytics code
- bukan engine utama untuk TIA/NAA/PTA

### Keputusan yang disarankan

Kalau kamu memang prefer LangChain, menurutku itu keputusan yang benar, dengan catatan:
- pakai `LangChain` untuk high-level agent interface dan tool wiring
- pakai `LangGraph` untuk orchestration utama production

Jadi bukan “LangChain saja”, tapi:

`LangChain untuk ergonomics`  
`LangGraph untuk runtime dan control`

Dengan kombinasi itu, kita bisa tetap cepat waktu bikin demo, tapi tidak mentok saat masuk ke pipeline harian yang stateful dan terus berjalan.

## Manfaat Stack Ini Untuk Use Case Kita

Kalau stack utamanya LangChain + LangGraph, manfaat langsungnya untuk TIA/NAA/PTA adalah:

- workflow antar agent bisa dibuat jelas dan berurutan
- state per kasus bisa disimpan, dilanjutkan, atau diulang
- hasil tiap tahap mudah diaudit
- gampang nambah human review sebelum escalation
- mudah bikin output terstruktur untuk daily intelligence brief
- fleksibel kalau nanti mau tambah agent lain seperti Geo Agent, Finance Signal Agent, atau Report QA Agent

## Next Steps Ke Production Yang Kontinyu

Kalau target akhirnya adalah production yang jalan terus dan menghasilkan laporan intelligence harian, next step yang aku sarankan adalah:

1. Tetapkan state model per kasus
   Definisikan schema baku untuk input, intermediate state, alert state, dan final report state.

2. Pisahkan tool layer dari agent layer
   Tool OSINT, graph analysis, geospatial correlation, report renderer, dan risk scorer harus modular.

3. Bangun workflow graph resmi
   Minimal node production:
   - ingest
   - normalize
   - extract entities
   - correlate network
   - score risk
   - generate brief
   - QA / approval

4. Tambahkan evaluation harness
   Ukur apakah agent:
   - menemukan aktor overlap
   - menemukan bridge account
   - menemukan shared location
   - menjelaskan alasan risk score
   - menghasilkan laporan yang konsisten

5. Tambahkan observability
   Log tiap step, latency, tool calls, confidence, dan perubahan skor antar rerun.

6. Tambahkan scheduled run harian
   Jalankan pipeline per hari atau per batch kasus, lalu simpan hasilnya sebagai daily brief archive.

7. Tambahkan human review gate
   Sebelum laporan final dipublish, sediakan approval step untuk analyst lead.

8. Siapkan regression dataset
   Dataset yang sekarang bisa jadi benchmark awal. Nanti tambahkan case pack baru agar agent tidak overfit ke 3 kasus yang sama.

### Urutan implementasi yang paling masuk akal

Kalau mau production bergerak terus, urutannya menurutku:

1. finalkan schema dataset dan output report
2. bangun TIA di atas tool ingestion + extraction
3. bangun NAA untuk graph dan co-location analysis
4. bangun PTA untuk scoring + escalation + brief
5. bungkus semuanya dalam LangGraph workflow
6. tambah evaluation + monitoring
7. baru setelah itu deploy scheduled daily runs

## Apa Yang Bisa Diuji

Beberapa skenario test yang cocok untuk agent atau dashboard:

- deteksi akun cluster vs akun umum
- cari persona yang punya shared meeting point berdasarkan `lat/lon` + `observed_at`
- temukan pasangan akun yang tidak berteman langsung tetapi muncul di lokasi sama
- cari bridge account yang muncul di lebih dari satu kasus
- hitung pola copy-paste atau posting sinkron
- cocokkan transaksi dengan edge sosial dan lokasi pertemuan
- cek overlap antara `campaigns.json`, `transactions.json`, dan `reports.json`
- uji risk scoring untuk indikator koordinasi berbahaya atau indikator aktivitas ekstrem yang terduga

Yang perlu dicari agent:
- pola
- korelasi
- prioritas investigasi
- indikator awal

Bukan:
- identifikasi ekstremis nyata
- bukti kriminal
- vonis
- atribusi final

## Catatan Multi-Case Correlation

Korelasi lintas kasus bisa muncul lewat:
- `phone_local`, `phone_e164`, atau `email` yang konsisten
- `meeting_point_id`
- kedekatan `latitude/longitude` dan waktu check-in
- repost atau amplifikasi narasi
- transfer edge di `transactions.json`
- `case_links` dalam profil

Dengan desain ini, agent bisa menemukan:
- siapa yang benar-benar terhubung langsung
- siapa yang hanya overlap di lokasi
- siapa yang jadi penghubung narasi atau pendanaan
- siapa yang muncul di beberapa kasus sekaligus

## Catatan Keamanan

Catatan penggunaan:
- tidak mewakili orang riil
- tidak dibuat untuk profiling dunia nyata
- tidak boleh dipakai untuk doxxing, investigasi nyata, atau pelabelan individu
- cocok untuk benchmark extraction, correlation, graph analysis, dan report generation internal
