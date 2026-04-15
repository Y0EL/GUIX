# Continue Log Frontend UIX

> **Update: 16 April 2026**

## Ringkasan Sistem
Frontend command center — TypeScript + React + Vite + react-router-dom. Implementasi berjalan per halaman, data aktual dari `/public/data/*.json`. Tidak ada backend stream aktif (simulasi LiveIntelFeed dari dataset lokal).

## Status Global
- **Progress:** ~67% (10 dari 15 halaman selesai)
- **Stack:** React + TypeScript + Vite + react-router-dom + ReactFlow + D3 + Leaflet
- **Routes aktif:** `/` · `/alert-center` · `/incident-queue` · `/map-intelligence` · `/search` · `/link-analysis` · `/timeline` · `/canvas` · `/narrative`

---

## Status Per Halaman (Total: 15)

| No | Nama | Route | Status |
|---|---|---|---|
| H1 | Global Overview | `/` | ✅ |
| H2 | Alert Center | `/alert-center` | ✅ |
| H3 | Incident Queue | `/incident-queue` | ✅ |
| H4 | Map Intelligence | `/map-intelligence` | ✅ |
| H5 | Search & Discovery | `/search` | ✅ |
| H6 | Entity Profile | *(modal di H5, H7)* | ✅ |
| H7 | Link Analysis | `/link-analysis` | ✅ |
| H8 | Timeline | `/timeline` | ✅ |
| H9 | Kanvas Investigasi | `/canvas` | ✅ |
| H10 | Narrative & Trend | `/narrative` | ✅ |
| H11 | Content Evidence & Media | `/content` | ⏳ next |
| H12 | Case Workspace | `/case-workspace` | ⏳ |
| H13 | Briefing & Reporting | `/briefing` | ⏳ |
| H14 | Fusion Board | `/fusion` | ⏳ |
| H15 | System Health & Audit | `/admin` | ⏳ |

---

## Detail Halaman Selesai

### H1 — Global Overview (`/`)
**Komponen:** PetaOverview (Leaflet + GeoJSON), BarMetrik, JamDisplay, PanelAlert, PanelKasus, PanelBerita  
**Data:** kasus, peringatan, skor_risiko, lokasi, news.jsonl  
**Fitur:** Leaflet fullscreen + heatmap hotspot, metrik animasi, rotasi panel tiap 1 menit, footer telemetry, `useArrowNav`

---

### H2 — Alert Center (`/alert-center`)
**Komponen:** AlertTopBar, AlertListPanel, AlertDetailPanel, AlertInsightPanel, InsightMiniMap, LiveIntelFeed  
**Data:** peringatan, kasus, lokasi, entitas, transaksi, postingan, laporan  
**Fitur:** 3-kolom; triase (ack/valid/FP/eskalasi); widget drag-swap max 2; InsightMiniMap per provinsi aktif; LiveIntelFeed 5 dataset  
**Gap:** State triase hilang saat navigasi (belum Zustand)

---

### H3 — Incident Queue (`/incident-queue`)
**Komponen:** IncidentTopBar, IncidentListPanel, IncidentDetailPanel, RiskGauge, LiveIntelFeed  
**Data:** kasus, skor_risiko, peringatan  
**Fitur:** 2-kolom list+detail; RiskGauge SVG 240° animated; SLA timer; 4-tab detail; status update; assign analis  
**Link keluar:** tombol "Analisis Lanjutan" → `/narrative` dan `/timeline` di panel detail  
**Gap:** State runtime hilang saat navigasi

---

### H4 — Map Intelligence (`/map-intelligence`)
**Komponen:** MapCanvas (Leaflet), MapTopBar, MapFilterPanel, LocationDetailPanel  
**Data:** lokasi, kasus  
**Fitur:** Fullscreen Leaflet; markers per tipe; filter by tipe/provinsi/kepercayaan; LocationDetailPanel slide-in  
**Gap:** Heatmap density, trajectory lines

---

### H5 — Search & Discovery (`/search`)
**Komponen:** SearchBar, SearchTopBar, SearchFilterBar, SearchResultsPanel, SearchSuggestions, ProfilCard, KasusCard, LokasiCard, PostinganCard  
**Data:** profil, kasus, lokasi, postingan  
**Fitur:** Full-text search 4 tipe; suggestions dropdown; ProfilCard (platform icons CDN); watchlist localStorage; tombol Analisis → EntityProfileModal  
**Gap:** Filter lanjut per field, sorting

---

### H6 — Entity Profile *(embedded modal)*
**Komponen:** EntityProfileModal (fullscreen overlay)  
**Data:** profil, postingan, pertemanan, kasus  
**Fitur:** 4-tab (Postingan/Koneksi/Kasus/Intel); watchlist toggle; buka dari H5, H7, H9, H10  
**Catatan:** Tidak butuh route sendiri — sudah cukup sebagai modal

---

### H7 — Link Analysis (`/link-analysis`)
**Komponen:** LinkAnalysis, NodeElement, NodeInfoPanel, EntityProfileModal  
**Data:** profil, pertemanan, postingan, kasus  
**Fitur:** D3 force-directed; kasus selector; subgraph direct+1-hop; highlight/dim; NodeInfoPanel slide-in; D3 drag+zoom; auto-fit  
**Gap:** Cluster color, export subgraph

---

### H8 — Timeline (`/timeline`)
**Komponen:** Timeline (monolitik + portal)  
**Data:** kasus, peringatan, postingan, transaksi, laporan, lokasi  
**Fitur:**
- 6 tipe event (alert/kasus/postingan/transaksi/laporan/lokasi) dengan warna + ikon per tipe
- Vertical swimlane timeline; event di-cluster per 5 menit
- Filter by tipe, severity, kasus, profil; date range
- Expand inline per event; portal overlay detail transaksi
- Terima context nav-state `{ filterKasus, filterProfil }` dari H3/H6/H7
- EntityProfileModal dibuka dari event profil
- `useArrowNav`

---

### H9 — Kanvas Investigasi (`/canvas`)
**Komponen:** KanvasInvestigasi (monolitik), WorkspaceManager, SearchModal  
**Data:** semua dataset (profil, transaksi, lokasi, akun, kontak, postingan, kasus, peringatan, jaringan)  
**Fitur:**
- **WorkspaceManager:** infinite canvas (ReactFlow) dengan folder icons; hierarki Folder → Kanvas; popup detail; drag positioning; localStorage `uix-workspace`
- **Entity palette:** 9 tipe node (profil/transaksi/lokasi/akun/kontak/postingan/kasus/peringatan/jaringan)
- **SearchModal:** filter parameter-based → Deploy → node muncul di canvas
- **Pivot/ekspansi:** klik tombol tipe dari node terpilih → tambah koneksi
- **AutoEdge:** `buatAutoEdges()` — 8 relasi otomatis saat deployNodes
- **Co-lokasi edges:** merah animated untuk profil dengan titik lokasi < 250m (Haversine)
- **Panel kanan 3-tab:** DETAIL · TIMELINE · PETA
- **PanelPetaLokasi:** slide-in overlay Leaflet 2D + MapLibre 2.5D + Nominatim
- **Link keluar:** panel BUKA DI → `/timeline` dan `/narrative`
- localStorage persist per kanvas

---

### H10 — Narrative & Trend (`/narrative`)
**Komponen:** NarrativeTrend (monolitik), BarChart (SVG), WordCloud (SVG spiral), KlasterCard, AvatarProfil, BeritaCard  
**Data:** postingan, kasus, profil, klaster_pesan, news.dataset.jsonl  
**Fitur:**
- **Strip intelijen:** ringkasan jumlah klaster kritis, akun aktif, puncak aktivitas
- **Bar chart SVG:** volume posting per hari, tooltip hover, responsive
- **Word cloud SVG:** spiral deterministik, 40 kata teratas, klik = filter klaster, skala merah by frekuensi
- **Klaster card:** severity tier (Kritis/Tinggi/Sedang) otomatis dari kemiripan + jumlah; avatar inisial fallback; action "Jaringan" → `/canvas`, "Kasus" → `/incident-queue`
- **Feed berita panel kanan:** thumbnail dari `news/images/` (Vite middleware), badge kategori berwarna
- **Filter aktif:** kasus pill di topbar (terima nav-state dari H3/H9), klik kata di word cloud
- **Terima nav-state:** `{ filterKasus?, filterProfil? }` dari H3 (Analisis Lanjutan) dan H9 (BUKA DI)
- `useArrowNav` di urutan: `/timeline` → `/narrative` → `/canvas`
- **CSS prefix:** `nt-*`

---

## Komponen & Hook Global

| Nama | Lokasi | Dipakai di |
|---|---|---|
| `RiskGauge` | components/ | H3 |
| `LiveIntelFeed` | components/ | H2, H3, H6 |
| `InsightMiniMap` | components/ | H2, H9 |
| `PanelPetaLokasi` | components/ | H4, H9 |
| `PlatformIcon` | components/ | H5, H6, H7 |
| `EntityProfileModal` | components/ | H5, H7, H8, H9, H10 |
| `useWatchlist` | hooks/ | H5, H6 |
| `useArrowNav` | hooks/ | semua halaman |
| `useLinkGraph` | hooks/ | H7 |
| `muatJson` | utils.ts | semua |

---

## Dataset Tersedia di `/public/data/`
`kasus` · `peringatan` · `skor_risiko` · `profil` · `pertemanan` · `postingan` · `lokasi` · `entitas` · `transaksi` · `laporan` · `klaster_pesan` · `news.dataset.jsonl`

> Dataset tambahan di `/dataset/`: akun, jaringan, kampanye, kontak, foto, crawling, preferensi — belum di-copy ke `/public/data/`

---

## CSS Architecture
- Semua class di `src/index.css` dengan prefix per fitur:
  `sd-*` · `ac-*` · `iq-*` · `la-*` · `tl-*` · `ki-*` · `wm-*` · `lif-*` · `ppl-*` · `imm-*` · `nt-*`
- Dedicated: `src/styles/epm.css` — EntityProfileModal

---

## Next: H11 — Content Evidence & Media (`/content`)
**Tujuan:** Analis melihat, mengelola, dan menandai konten digital sebagai barang bukti (foto, postingan, screenshot, video)  
**Data:** foto.json, postingan.json, crawling.json, kasus.json, profil.json  
**Konsep:**
- Grid galeri media (foto/screenshot) dengan metadata OSINT: koordinat, timestamp, platform, profil sumber
- Panel detail: preview media + chain of custody (kasus terkait, tanggal capture, hash)
- Filter: per kasus, tipe media, platform, tanggal
- Tombol aksi: "Tambahkan ke Kasus", "Buka Profil Sumber", "Buka di Kanvas"
- Terima nav-state `{ filterKasus?, filterProfil? }` dari H3/H9


## Ringkasan Sistem
Frontend command center — TypeScript + React + Vite + react-router-dom. Implementasi berjalan per halaman, data aktual dari `/public/data/*.json`. Tidak ada backend stream aktif (simulasi LiveIntelFeed dari dataset lokal).

## Status Global
- **Progress:** ~58% (9 dari 15 halaman selesai)
- **Stack:** React + TypeScript + Vite + react-router-dom + ReactFlow + D3 + Leaflet
- **Routes aktif:** `/` · `/alert-center` · `/incident-queue` · `/map-intelligence` · `/search` · `/link-analysis` · `/timeline` · `/canvas`

---

## Status Per Halaman (Total: 15)

| No | Nama | Route | Status |
|---|---|---|---|
| H1 | Global Overview | `/` | ✅ |
| H2 | Alert Center | `/alert-center` | ✅ |
| H3 | Incident Queue | `/incident-queue` | ✅ |
| H4 | Map Intelligence | `/map-intelligence` | ✅ |
| H5 | Search & Discovery | `/search` | ✅ |
| H6 | Entity Profile | *(modal di H5, H7)* | ✅ |
| H7 | Link Analysis | `/link-analysis` | ✅ |
| H8 | Timeline | `/timeline` | ✅ |
| H9 | Kanvas Investigasi | `/canvas` | ✅ |
| H10 | Narrative & Trend | `/narrative` | ⏳ next |
| H11 | Content Evidence & Media | `/content` | ⏳ |
| H12 | Case Workspace | `/case-workspace` | ⏳ |
| H13 | Briefing & Reporting | `/briefing` | ⏳ |
| H14 | Fusion Board | `/fusion` | ⏳ |
| H15 | System Health & Audit | `/admin` | ⏳ |

---

## Detail Halaman Selesai

### H1 — Global Overview (`/`)
**Komponen:** PetaOverview (Leaflet + GeoJSON), BarMetrik, JamDisplay, PanelAlert, PanelKasus, PanelBerita  
**Data:** kasus, peringatan, skor_risiko, lokasi, news.jsonl  
**Fitur:** Leaflet fullscreen + heatmap hotspot, metrik animasi, rotasi panel tiap 1 menit, footer telemetry, `useArrowNav`

---

### H2 — Alert Center (`/alert-center`)
**Komponen:** AlertTopBar, AlertListPanel, AlertDetailPanel, AlertInsightPanel, InsightMiniMap, LiveIntelFeed  
**Data:** peringatan, kasus, lokasi, entitas, transaksi, postingan, laporan  
**Fitur:** 3-kolom; triase (ack/valid/FP/eskalasi); widget drag-swap max 2; InsightMiniMap per provinsi aktif; LiveIntelFeed 5 dataset  
**Gap:** State triase hilang saat navigasi (belum Zustand)

---

### H3 — Incident Queue (`/incident-queue`)
**Komponen:** IncidentTopBar, IncidentListPanel, IncidentDetailPanel, RiskGauge, LiveIntelFeed  
**Data:** kasus, skor_risiko, peringatan  
**Fitur:** 2-kolom list+detail; RiskGauge SVG 240° animated; SLA timer; 4-tab detail; status update; assign analis  
**Gap:** State runtime hilang saat navigasi

---

### H4 — Map Intelligence (`/map-intelligence`)
**Komponen:** MapCanvas (Leaflet), MapTopBar, MapFilterPanel, LocationDetailPanel  
**Data:** lokasi, kasus  
**Fitur:** Fullscreen Leaflet; markers per tipe; filter by tipe/provinsi/kepercayaan; LocationDetailPanel slide-in  
**Gap:** Heatmap density, trajectory lines

---

### H5 — Search & Discovery (`/search`)
**Komponen:** SearchBar, SearchTopBar, SearchFilterBar, SearchResultsPanel, SearchSuggestions, ProfilCard, KasusCard, LokasiCard, PostinganCard  
**Data:** profil, kasus, lokasi, postingan  
**Fitur:** Full-text search 4 tipe; suggestions dropdown; ProfilCard (platform icons CDN); watchlist localStorage; tombol Analisis → EntityProfileModal  
**Gap:** Filter lanjut per field, sorting

---

### H6 — Entity Profile *(embedded modal)*
**Komponen:** EntityProfileModal (fullscreen overlay)  
**Data:** profil, postingan, pertemanan, kasus  
**Fitur:** 4-tab (Postingan/Koneksi/Kasus/Intel); watchlist toggle; buka dari H5, H7, H9  
**Catatan:** Tidak butuh route sendiri — sudah cukup sebagai modal

---

### H7 — Link Analysis (`/link-analysis`)
**Komponen:** LinkAnalysis, NodeElement, NodeInfoPanel, EntityProfileModal  
**Data:** profil, pertemanan, postingan, kasus  
**Fitur:** D3 force-directed; kasus selector; subgraph direct+1-hop; highlight/dim; NodeInfoPanel slide-in; D3 drag+zoom; auto-fit  
**Gap:** Cluster color, export subgraph

---

### H8 — Timeline (`/timeline`)
**Komponen:** Timeline (monolitik + portal)  
**Data:** kasus, peringatan, postingan, transaksi, laporan, lokasi  
**Fitur:**
- 6 tipe event (alert/kasus/postingan/transaksi/laporan/lokasi) dengan warna + ikon per tipe
- Vertical swimlane timeline; event di-cluster per 5 menit
- Filter by tipe, severity, kasus, profil; date range
- Expand inline per event; portal overlay detail transaksi
- Terima context nav-state `{ filterKasus, filterProfil }` dari H3/H6/H7
- EntityProfileModal dibuka dari event profil
- `useArrowNav`

---

### H9 — Kanvas Investigasi (`/canvas`)
**Komponen:** KanvasInvestigasi (monolitik), WorkspaceManager, SearchModal  
**Data:** semua dataset (profil, transaksi, lokasi, akun, kontak, postingan, kasus, peringatan, jaringan)  
**Fitur:**
- **WorkspaceManager:** infinite canvas (ReactFlow) dengan folder icons; hierarki Folder → Kanvas; popup detail; drag positioning; localStorage `uix-workspace`
- **Entity palette:** 9 tipe node (profil/transaksi/lokasi/akun/kontak/postingan/kasus/peringatan/jaringan)
- **SearchModal:** filter parameter-based → Deploy → node muncul di canvas
- **Pivot/ekspansi:** klik tombol tipe dari node terpilih → tambah koneksi
- **AutoEdge:** `buatAutoEdges()` — 8 relasi otomatis saat deployNodes (jaringan, transaksi, lokasi, akun, kontak, postingan, kasus→profil, kasus→peringatan)
- **Co-lokasi edges:** merah animated untuk profil dengan titik lokasi < 250m (Haversine), tanpa label box
- **Panel kanan 3-tab:** DETAIL · TIMELINE · PETA
  - Timeline: events kronologis dari node di kanvas
  - Peta: embedded InsightMiniMap (Leaflet CartoDB dark) + daftar lokasi; tombol buka PanelPetaLokasi
- **PanelPetaLokasi:** slide-in overlay Leaflet 2D + MapLibre 2.5D + Nominatim reverse geocode
- localStorage persist per kanvas

---

## Komponen & Hook Global

| Nama | Lokasi | Dipakai di |
|---|---|---|
| `RiskGauge` | components/ | H3 |
| `LiveIntelFeed` | components/ | H2, H3, H6 |
| `InsightMiniMap` | components/ | H2, H9 |
| `PanelPetaLokasi` | components/ | H4, H9 |
| `PlatformIcon` | components/ | H5, H6, H7 |
| `EntityProfileModal` | components/ | H5, H7, H8, H9 |
| `useWatchlist` | hooks/ | H5, H6 |
| `useArrowNav` | hooks/ | semua halaman |
| `useLinkGraph` | hooks/ | H7 |
| `muatJson` | utils.ts | semua |

---

## Dataset Tersedia di `/public/data/`
`kasus` · `peringatan` · `skor_risiko` · `profil` · `pertemanan` · `postingan` · `lokasi` · `entitas` · `transaksi` · `laporan` · `news.dataset.jsonl`

> Dataset tambahan di `/dataset/`: akun, jaringan, klaster_pesan, kampanye, kontak, foto, crawling, preferensi, skor_risiko — belum di-copy ke `/public/data/`

---

## CSS Architecture
- Semua class di `src/index.css` dengan prefix per fitur:
  `sd-*` (search) · `ac-*` (alert) · `iq-*` (incident) · `la-*` (link analysis) · `tl-*` (timeline) · `ki-*` (kanvas) · `wm-*` (workspace manager) · `lif-*` (live intel feed) · `ppl-*` (panel peta lokasi) · `imm-*` (insight mini map)
- Dedicated: `src/styles/epm.css` — EntityProfileModal

---

## Next: H10 — Narrative & Trend (`/narrative`)
**Tujuan:** Analisis pergeseran narasi dan trend dari postingan + berita  
**Data:** postingan.json, klaster_pesan (di `/dataset/klaster_pesan.json`), news.dataset.jsonl  
**Konsep:**
- Word cloud atau bar frekuensi per kata kunci dari klaster pesan
- Trend line sederhana: volume postingan per hari (dari `dibuat_pada`)
- Top klaster pesan: judul + ukuran klaster + sentimen
- Top berita: headline + kategori + sumber
- Filter by kasus atau profil (terima nav context seperti H8)
- **Tidak butuh dataset baru** — semua dari data yang sudah ada
