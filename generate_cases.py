import argparse

from synthetic_dataset import CASE_CONFIG, SyntheticDatasetGenerator


def parse_args():
    parser = argparse.ArgumentParser(description="Augment existing personas with correlated cases.")
    parser.add_argument("--out-dir", default="out_profiles", help="Folder dataset yang sudah berisi profiles.json.")
    parser.add_argument("--seed", type=int, default=42, help="Seed untuk random generator.")
    parser.add_argument("--model", default="gpt-5-nano", help="Model OpenAI untuk generation teks natural.")
    parser.add_argument(
        "--cases",
        default="warehouse_fire,suspicious_funding,propaganda",
        help="Daftar kasus dipisah koma.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    requested = [item.strip() for item in args.cases.split(",") if item.strip()]
    invalid = [item for item in requested if item not in CASE_CONFIG]
    if invalid:
        raise SystemExit(f"Kasus tidak dikenal: {', '.join(invalid)}")

    generator = SyntheticDatasetGenerator(seed=args.seed, openai_model=args.model)
    bundle = generator.load_bundle(args.out_dir)
    if not bundle.profiles:
        raise SystemExit("profiles.json tidak ditemukan atau kosong. Jalankan generate_profiles.py dulu.")

    bundle = generator.augment_bundle_with_cases(bundle=bundle, case_names=requested)
    generator.write_bundle(bundle, args.out_dir)
    print(f"Selesai generate {len(bundle.cases)} kasus di {args.out_dir}")


if __name__ == "__main__":
    main()
