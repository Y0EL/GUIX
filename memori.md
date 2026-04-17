# Memori Proyek - Orkestrasi Intelijen
Diperbarui: 2026-04-17 11:50

## Ringkasan Proyek
Membangun backend orkestrasi agent TIA, NAA, dan PTA untuk analisis OSINT berbasis data uji internal dengan runtime nyata: OpenAI, LangChain, LangGraph, Kafka, Redis Streams, PostgreSQL, Neo4j, dan Celery.

## Stack Teknologi
- Backend: Python
- Orkestrasi Agent: LangChain, LangGraph
- LLM: OpenAI `gpt-5-nano`
- Queue/Stream: Kafka, Redis Streams, Celery
- Database: PostgreSQL, Neo4j
- Analitik: NetworkX, scikit-learn, numpy

## Progres Terakhir
- [x] Konfigurasi env fail-fast untuk seluruh service inti
- [x] Kontrak event typed untuk TIA, NAA, PTA, dan HITL
- [x] Gateway MCP ke PostgreSQL dan Neo4j
- [x] Seed data uji ke PostgreSQL dan Neo4j
- [x] LangGraph untuk TIA
- [x] Worker Redis Streams untuk NAA
- [x] Task Celery untuk PTA
- [x] Routing HITL dan payload review
- [x] Docker Compose untuk service lokal
- [x] Dokumentasi setup manual Windows tanpa Docker
- [x] README diperjelas untuk jalur Windows native, download resmi, verifikasi port, dan peran `npm run back`
- [x] TIA di-upgrade ke graph multi-pass dengan planner, retrieval executor, verifier, critic, evidence ranking, dan briefing review
- [x] NAA di-upgrade ke relation extraction dua tahap dan interpreter cluster
- [x] PTA di-upgrade ke scope planner, interpretasi ketidakpastian, dan critic rekomendasi
- [x] Prompt registry dan schema reasoning baru ditambahkan
- [x] Dead-letter stream ditambahkan untuk kegagalan validasi utama
- [x] Launcher Docker bisa reset volume otomatis saat seed gagal karena drift kredensial
- [x] Kredensial Neo4j Docker disederhanakan menjadi `neo4j/123`
- [x] Dokumen produk `UIX.md` dibuat sangat rinci untuk command center delapan operator dengan 18 halaman, hubungan antarlayar, pola ruangan, library utama, dan alternatif stack UI
- [x] Schema output LLM dibuat lebih tahan variasi format agar TIA tidak jatuh saat model mengembalikan list pada field teks seperti `confidence_reasoning`
- [x] README diperjelas untuk urutan manual yang benar: seed -> worker TIA/NAA/PTA -> publish, plus cara verifikasi hasil kasus di PostgreSQL dan Neo4j
- [x] Worker TIA dan NAA sekarang tidak mati total saat satu event gagal; event bermasalah diarahkan ke dead-letter dan loop tetap lanjut
- [x] Launcher backend diubah agar start worker lebih dulu, memvalidasi worker tetap hidup, lalu baru publish event
- [x] Launcher backend sekarang menimpa log worker setiap start agar log run baru tidak tercampur dengan run lama
- [x] Launcher backend sekarang menyembunyikan jendela console worker di Windows agar `npm run back:docker` tetap rapi
- [x] README diselaraskan dengan kredensial PostgreSQL Docker yang aktif yaitu `123/123`
- [x] Mode `npm run back:live` ditambahkan untuk menjalankan TIA, NAA, dan PTA secara live dalam satu terminal dengan prefix log
- [x] Bug HITL diperbaiki: `trace_id` review sekarang dibaca dari payload event dengan benar saat disimpan ke PostgreSQL
- [x] Kafka consumer TIA diperpanjang `max_poll_interval_ms` dan dibatasi `max_poll_records=1` agar proses LLM panjang tidak membuat consumer dikeluarkan dari group terlalu cepat
- [x] Command `analisis-kasus --id <id_kasus>` ditambahkan untuk menghasilkan artefak `JSON`, `MD`, `CSV`, `XLSX`, `DOCX`, dan `PDF` di folder `analisa/` dengan fingerprint `SHA-256`
- [x] Schema dossier sindikat dibuat lebih tahan variasi output OpenAI pada bagian `relasi_kunci`, termasuk fallback field `sumber_id`/`target_id` dan default `confidence`
- [x] Command `analisis-kasus` sekarang menampilkan progres eksplisit di terminal: ambil bundel -> reasoning OpenAI -> tulis artefak
- [x] Serializer fingerprint artefak diperbaiki agar `datetime` dan path dari bundel kasus bisa diubah aman ke JSON stabil
- [x] Ekspor file `.json` dan `manifest.json` sekarang memakai serializer aman yang sama agar `datetime` dari bundel MCP tidak menjatuhkan proses penulisan artefak
- [x] Payload OpenAI untuk `analisis-kasus` dipadatkan agar `isi_json` profil yang sangat besar tidak dikirim ganda bersama `postingan` dan `lokasi`
- [x] `analisis-kasus` sekarang memakai timeout khusus minimal 180 detik untuk dossier sindikat, tetapi panggilan lain tetap memakai timeout runtime biasa
- [x] Generator `XLSX`, `DOCX`, dan `PDF` untuk `analisis-kasus` dimigrasikan ke layout bergaya dengan tema terang-oranye, heading 1-3, tabel, dan box konten
- [x] Custom agent workspace ditambahkan untuk operasional coding: agen utama berbahasa Indonesia, `Auditor Ketat` untuk audit read-only, dan `Autocompacter Memori` untuk menjaga ringkasan sesi tetap utuh
- [ ] Validasi runtime dengan API key dan service aktif
- [ ] UI Flask atau React

## Keputusan Teknis Penting
| Tanggal | Keputusan | Alasan |
|---|---|---|
| 2026-04-14 | PTA dijalankan lewat Celery | PTA lebih berat dan tidak boleh menghambat TIA/NAA |
| 2026-04-14 | Data uji di-seed ke PostgreSQL dan Neo4j | Runtime agent tidak membaca file langsung |
| 2026-04-14 | TIA memakai LangGraph, NAA/PTA worker event-driven | Kontrol state tetap ketat sambil menjaga pipeline asynchronous |
| 2026-04-14 | Enhancement agent memakai graph terkontrol | Audit trail lebih jelas daripada agent loop bebas |
| 2026-04-14 | UI utama diarahkan ke React command center dengan tema gelap operasional | Kebutuhan peta, graph, chart, sinkronisasi delapan layar, dan interaksi lintas panel lebih cocok daripada shell Flask murni |
| 2026-04-14 | Payload dossier sindikat dipadatkan sebelum dikirim ke OpenAI | Bundel kasus mentah memuat duplikasi besar dari `profil.isi_json`, `postingan`, dan `lokasi` yang memicu timeout |
| 2026-04-14 | Artefak office dipindahkan ke library dokumen nyata | Writer manual XML/PDF terlalu mentah dan tidak cukup human readable untuk konsumsi analis |
| 2026-04-14 | Workflow agent dipisah menjadi agen operasional, auditor, dan autocompacter | Analisis, audit read-only, dan pemadatan memori perlu fokus tool dan peran yang berbeda agar konteks tidak buyar |
| 2026-04-17 | Atlas Live mode diubah menjadi trigger suara sekali-klik globe (tanpa input teks) | Mencegah kebocoran audio dan menyederhanakan alur interaksi live voice |
| 2026-04-17 | Preload Whisper Atlas dibuat non-blocking + mode aman CPU dan timeout ASR frontend | Startup tidak macet saat model berat, UI tidak menggantung saat ASR lambat, dan respons tetap stabil di perangkat CPU |
| 2026-04-17 | Atlas memakai memori sesi lokal persisten untuk konteks percakapan lanjutan | Permintaan ambigu seperti "lebih detail" dapat diresolusikan ke halaman terakhir dan langsung membuka navigasi yang relevan |

## Catatan Aktif
- Isi `OPENAI_API_KEY` yang valid sebelum menjalankan worker.
- Jalankan `python -m orchestration.cli seed` sebelum publish ke Kafka.
- Worker TIA dan NAA membaca service nyata, bukan fallback lokal.
- Untuk mode non-Docker, README sekarang memuat urutan download, instalasi, verifikasi port, dan startup worker.
- TIA sekarang bisa loop retrieval terbatas hingga dua putaran sebelum publish atau dead-letter.
- NAA menolak relasi lemah sebelum masuk Neo4j.
- PTA menyimpan scope retrieval, fitur per domain, dan kritik rekomendasi ke hasil JSON.
- Docker Neo4j sekarang menurunkan minimum password length ke `3` agar password `123` valid untuk lingkungan uji.
- `.env` diselaraskan dengan kredensial Docker Compose untuk Neo4j.
- `UIX.md` sekarang menjadi dokumen acuan UI/UX utama untuk fase frontend dan memuat detail 18 halaman, pola 8 layar, serta library dan alternatifnya.
- `openai_stack.py` sekarang memakai temperature lebih rendah agar structured output lebih stabil saat worker berjalan lama.
- `analisis-kasus` sekarang merangkum `profil`, `lokasi`, `postingan`, `transaksi`, dan `graf` sebelum panggilan dossier; ukuran payload kasus uji turun dari sekitar 290 KB menjadi sekitar 34 KB.
- `analisis-kasus` sekarang memakai `openpyxl`, `python-docx`, dan `reportlab` untuk keluaran `XLSX`, `DOCX`, dan `PDF` yang lebih presentabel.
- Artefak baru tervalidasi pada kasus `kasus-pendanaan-mencurigakan` dengan ukuran sekitar `12 KB` (`XLSX`), `40 KB` (`DOCX`), dan `50 KB` (`PDF`) setelah styling diterapkan.
- README sekarang menjelaskan bahwa log `publish-osint` hanya berarti event terkirim ke Kafka, bukan bukti pipeline penuh selesai.
- `scripts/jalankan-backend.js` sekarang lebih cocok untuk pembuktian runtime karena event baru diterbitkan setelah worker benar-benar hidup.
- Folder `.github/agents/` sekarang memuat agen `asisten-operasional-indonesia`, `auditor-ketat`, dan `autocompacter-memori` untuk workflow coding, audit, dan compacting.
- Arah identitas visual di layer agent/workflow sekarang mendukung dua mode, terang dan gelap, dengan basis warna merah-hitam sebagai identitas utama proyek.
- `atlas/atlas_web.py` sekarang default ke Ollama lokal dengan model `qwen3.5:latest`; mode cloud hanya aktif jika `ATLAS_OLLAMA_MODE=cloud` dan `OLLAMA_API_KEY` valid.
- `atlas/atlas_web.py` sekarang default ke `edge-tts` dengan voice `id-ID-ArdiNeural`; Piper hanya aktif jika `ATLAS_TTS_MODE=piper`.
- UI Atlas dipindah ke template Flask `atlas/templates/index.html` dengan layout fullscreen 2:2, visual Lottie `globe.json` + soundwave amplitudo aktual, chat panel hidden default dengan tombol toggle kanan bawah, dan heading kanan disederhanakan menjadi "ATLAS Intelligence".
- Mode interaksi Atlas kini voice-trigger only: input teks frontend dihapus, endpoint `/api/chat` dinonaktifkan (`410`), dan rekam dimulai dari klik globe.
- Kebocoran suara dikurangi dengan `echoCancellation`, `noiseSuppression`, `autoGainControl` pada `getUserMedia`, serta auto-relisten dimatikan.
- Prompt chat Atlas diperketat: tetap bisa menjawab topik umum, tetapi wajib menjadikan konteks database UIX sebagai rujukan utama saat relevan.
- `atlas/atlas_web.py` sekarang mendukung preload Whisper di background (`ATLAS_WHISPER_PRELOAD`) dan mode aman CPU (`ATLAS_WHISPER_CPU_SAFE`) yang otomatis memilih model lebih ringan saat target `turbo` dijalankan di CPU.
- `atlas/templates/index.html` kini memberi timeout 30 detik untuk `/api/listen` agar status `processing` tidak menggantung saat model ASR belum siap.
- `atlas/atlas_web.py` kini menyimpan memori sesi Atlas secara lokal di `runtime_state/atlas_session_memory.json` dan memakainya untuk follow-up kontekstual seperti "lanjut" atau "lebih detail" agar tetap membuka halaman yang dimaksud.

## Bug & Workaround Diketahui
| Bug | Workaround / Status |
|---|---|
| Belum divalidasi terhadap service lokal hidup | Tunggu user mengisi env dan menyalakan stack |
| Akurasi model baseline PTA masih tergantung kualitas data uji | Akan dipertajam setelah backend stabil |
| Structured output GPT bisa bervariasi bila prompt terlalu longgar | Perlu evaluasi manual setelah API key aktif |
| `DossierSindikat.relasi_kunci` sempat gagal saat model tidak mengirim `confidence` | Sudah diperlunak di schema dan dinormalisasi sebelum validasi |
| Pembuatan fingerprint artefak sempat gagal karena `datetime` dari bundel MCP tidak serializable | Sudah dipaksa ke format ISO saat serialisasi JSON stabil |
| Penulisan file artefak JSON sempat masih memakai `json.dumps` mentah | Sudah disatukan ke helper serializer aman `_json_rapi()` |
| `analisis-kasus` sempat gagal dengan `openai.APITimeoutError` | Sudah diperbaiki dengan payload ringkas dan timeout khusus dossier; tervalidasi sukses pada `kasus-pendanaan-mencurigakan` |
| Artefak `XLSX`/`DOCX`/`PDF` sempat terlihat mentah dan tidak human readable | Sudah diperbaiki dengan layout bergaya, heading, tabel, dan box; ada test regresi dokumen |

## Konteks Penting Lainnya
User menekankan bahwa runtime agent harus nyata dan serius; hanya isi data yang bersifat uji internal.
