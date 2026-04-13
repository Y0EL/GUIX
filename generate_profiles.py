import argparse

from synthetic_dataset import SyntheticDatasetGenerator


def parse_args():
    parser = argparse.ArgumentParser(description="Generate Indonesian persona dataset.")
    parser.add_argument("--count", type=int, default=300, help="Jumlah persona yang akan dibuat.")
    parser.add_argument("--out-dir", default="out_profiles", help="Folder output dataset.")
    parser.add_argument("--seed", type=int, default=42, help="Seed untuk random generator.")
    parser.add_argument("--model", default="gpt-5-nano", help="Model OpenAI untuk generation teks natural.")
    parser.add_argument(
        "--with-images",
        action="store_true",
        help="Download avatar dari 100k-faces ke folder images.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    generator = SyntheticDatasetGenerator(seed=args.seed, openai_model=args.model)
    bundle = generator.build_profiles_bundle(count=args.count, out_dir=args.out_dir, with_images=args.with_images)
    generator.write_bundle(bundle, args.out_dir)
    print(f"Selesai generate {len(bundle.profiles)} persona ke {args.out_dir}")


if __name__ == "__main__":
    main()
