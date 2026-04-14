import sys
from synthetic_dataset import SyntheticDatasetGenerator

print("[1/3] Inisialisasi generator...", flush=True)
generator = SyntheticDatasetGenerator(seed=42)

print("[2/3] Membuat profil... (ini yang paling lama)", flush=True)
COUNT = 250
bundle = generator.build_profiles_bundle(count=COUNT, out_dir="profiles")
print(f"      OK — {len(bundle.profiles)} profil, {len(bundle.accounts)} akun, {len(bundle.posts)} posts awal", flush=True)

print("[3/3] Generate kasus intelijen...", flush=True)
for nama_kasus in ["warehouse_fire", "suspicious_funding", "propaganda"]:
    print(f"      > proses kasus: {nama_kasus}...", end=" ", flush=True)
    bundle = generator.augment_bundle_with_cases(bundle=bundle, case_names=[nama_kasus])
    print("selesai", flush=True)

print("\nMenyimpan ke disk...", flush=True)
generator.write_bundle(bundle=bundle, out_dir="profiles")

print(f"""
=======================================
SELESAI
=======================================
Profil     : {len(bundle.profiles)}
Akun       : {len(bundle.accounts)}
Posts      : {len(bundle.posts)}
Kasus      : {len(bundle.cases)}
Transaksi  : {len(bundle.transactions)}
Alerts     : {len(bundle.alerts)}
Crawling   : {len(bundle.crawling)}
Output     : profiles/
=======================================""", flush=True)