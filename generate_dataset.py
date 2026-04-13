import argparse

from synthetic_dataset import CASE_CONFIG, SyntheticDatasetGenerator


def parse_args():
    parser = argparse.ArgumentParser(description="Generate full persona + multi-case dataset pack.")
    parser.add_argument("--count", type=int, default=300, help="Jumlah persona.")
    parser.add_argument("--out-dir", default="out_profiles", help="Folder output dataset.")
    parser.add_argument("--seed", type=int, default=42, help="Seed untuk random generator.")
    parser.add_argument("--model", default="gpt-5-nano", help="Model OpenAI untuk generation teks natural.")
    parser.add_argument(
        "--cases",
        default="warehouse_fire,suspicious_funding,propaganda",
        help="Daftar kasus dipisah koma.",
    )
    parser.add_argument(
        "--with-images",
        action="store_true",
        help="Download avatar dari 100k-faces ke folder images.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    requested = [item.strip() for item in args.cases.split(",") if item.strip()]
    invalid = [item for item in requested if item not in CASE_CONFIG]
    if invalid:
        raise SystemExit(f"Kasus tidak dikenal: {', '.join(invalid)}")

    generator = SyntheticDatasetGenerator(seed=args.seed, openai_model=args.model)
    bundle = generator.build_profiles_bundle(count=args.count, out_dir=args.out_dir, with_images=args.with_images)
    bundle = generator.augment_bundle_with_cases(bundle=bundle, case_names=requested)
    generator.write_bundle(bundle, args.out_dir)
    print(
        f"Selesai generate dataset penuh: {len(bundle.profiles)} persona, "
        f"{len(bundle.cases)} kasus, {len(bundle.posts)} post."
    )


if __name__ == "__main__":
    main()
