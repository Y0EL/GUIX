"""
Synthetic persona and incident dataset generator for internal testing.
"""

from __future__ import annotations

import json
import math
import os
import random
import re
import string
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from faker import Faker

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover
    OpenAI = None


INDONESIA_TZ = timezone(timedelta(hours=7))
AVATAR_ENDPOINT = "https://100k-faces.vercel.app/api/random-image"
AVATAR_SOURCE = "100k-faces"
DEFAULT_OPENAI_MODEL = "gpt-5-nano"

# Optional local overrides.
# If you want to hardcode credentials instead of using environment variables,
# paste your values here.
HARDCODED_OPENAI_API_KEY = ""
HARDCODED_OPENAI_MODEL = "gpt-5-nano"

CITY_CLUSTERS = [
    {"city": "Bekasi", "province": "Jawa Barat", "lat": -6.2349, "lon": 106.9896, "radius_km": 8.0},
    {"city": "Karawang", "province": "Jawa Barat", "lat": -6.3054, "lon": 107.2961, "radius_km": 9.0},
    {"city": "Cikarang", "province": "Jawa Barat", "lat": -6.2615, "lon": 107.1522, "radius_km": 7.5},
    {"city": "Jakarta", "province": "DKI Jakarta", "lat": -6.2088, "lon": 106.8456, "radius_km": 12.0},
    {"city": "Depok", "province": "Jawa Barat", "lat": -6.4025, "lon": 106.7942, "radius_km": 7.0},
    {"city": "Bogor", "province": "Jawa Barat", "lat": -6.5950, "lon": 106.8166, "radius_km": 8.5},
]

CLUSTER_WEIGHTS = [0.20, 0.16, 0.18, 0.22, 0.12, 0.12]
MEETING_POINT_TYPES = ["coworking_space", "cafe", "rest_area", "warehouse_hub", "rental_house", "industrial_parking"]
PLATFORMS = ["twitter", "instagram", "facebook", "tiktok", "telegram", "forum"]
LANGUAGE_SETS = [["id", "en"], ["id"], ["id", "jv"], ["id", "su"], ["id", "en", "jv"]]
INTEREST_GROUPS = [
    "otomotif",
    "fotografi",
    "kuliner",
    "logistik",
    "teknologi",
    "gaming",
    "komunitas_lokal",
    "musik",
    "olahraga",
    "politik",
    "aktivisme",
    "bisnis_online",
]

BIO_TEMPLATES = [
    "Aktif di komunitas {interest}. Sering mobile antara {city} dan sekitarnya.",
    "Suka ngobrol soal {interest}, kerja fleksibel, dan sering nongkrong di {city}.",
    "Tertarik pada {interest}, update isu lokal, dan sering dokumentasi kegiatan harian.",
    "Ngurus operasional kecil-kecilan, hobi {interest}, dan punya circle terbatas di {city}.",
    "Akun personal untuk catatan kegiatan, minat {interest}, dan koneksi komunitas lokal.",
]

POST_TEMPLATES = [
    "Lagi fokus urus agenda minggu ini. {tagline}",
    "Baru kelar ketemu teman lama di {city}. {tagline}",
    "Kalau malam begini enak buat beresin kerjaan sambil pantau update {interest}.",
    "Hari ini ramai juga di sekitar {city}.",
    "Masih cari referensi soal {interest}. Ada yang punya rekomendasi?",
    "Nanti malam kumpul singkat, semoga semua lancar.",
    "Kadang insight paling bagus datang pas lagi perjalanan pulang.",
    "Weekend begini biasanya santai, tapi timeline malah ramai.",
]

SEARCH_RESULT_SNIPPETS = [
    "Menampilkan hasil profil terkait aktivitas komunitas lokal.",
    "Akun ini beberapa kali muncul dalam percakapan publik dan forum komunitas.",
    "Jejak akun memperlihatkan aktivitas lintas platform dengan intensitas menengah.",
    "Hasil pencarian menemukan kemiripan username dan lokasi kegiatan.",
]

PHONE_PREFIXES = [
    "811",
    "812",
    "813",
    "821",
    "822",
    "823",
    "851",
    "852",
    "853",
    "855",
    "856",
    "857",
    "858",
    "877",
    "878",
    "881",
    "882",
    "895",
    "896",
    "897",
    "898",
    "899",
]

FUNDING_PURPOSES = [
    "iuran logistik",
    "dukungan operasional",
    "pengadaan alat komunikasi",
    "dana perjalanan",
    "paket konsumsi",
]

CASE_CONFIG = {
    "warehouse_fire": {
        "case_id": "case-warehouse-fire",
        "title": "Kebakaran Gudang Logistik - Indikasi Sabotase Terkoordinasi",
        "city": "Bekasi",
        "province": "Jawa Barat",
        "incident_at": datetime(2026, 4, 11, 2, 30, tzinfo=INDONESIA_TZ),
        "meeting_type": "warehouse_hub",
    },
    "suspicious_funding": {
        "case_id": "case-suspicious-funding",
        "title": "Pola Pendanaan Tersebar - Indikasi Koordinasi Finansial",
        "city": "Jakarta",
        "province": "DKI Jakarta",
        "incident_at": datetime(2026, 4, 7, 20, 0, tzinfo=INDONESIA_TZ),
        "meeting_type": "coworking_space",
    },
    "propaganda": {
        "case_id": "case-propaganda-burst",
        "title": "Amplifikasi Narasi Terkoordinasi - Indikasi Propaganda",
        "city": "Cikarang",
        "province": "Jawa Barat",
        "incident_at": datetime(2026, 4, 12, 19, 15, tzinfo=INDONESIA_TZ),
        "meeting_type": "cafe",
    },
}


@dataclass
class Bundle:
    profiles: list
    accounts: list
    contacts: list
    preferences: list
    photos: list
    posts: list
    friends: list
    network: list
    locations: list
    cases: list
    transactions: list
    funding_alerts: list
    campaigns: list
    message_clusters: list
    crawling: list
    entities: list
    alerts: list
    risk_scores: list
    reports: list


def now_iso() -> str:
    return datetime.now(INDONESIA_TZ).replace(microsecond=0).isoformat()


def dt_to_iso(value: datetime) -> str:
    return value.astimezone(INDONESIA_TZ).replace(microsecond=0).isoformat()


def slugify(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")


def rand_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}"


def rounded(value: float) -> float:
    return round(value, 6)


def random_point(rng: random.Random, lat: float, lon: float, radius_km: float) -> tuple[float, float]:
    distance = radius_km * math.sqrt(rng.random())
    bearing = rng.random() * math.pi * 2
    lat_offset = (distance / 111.0) * math.cos(bearing)
    lon_offset = (distance / (111.0 * math.cos(math.radians(lat)))) * math.sin(bearing)
    return rounded(lat + lat_offset), rounded(lon + lon_offset)


def random_time_between(rng: random.Random, start: datetime, end: datetime) -> datetime:
    total = int((end - start).total_seconds())
    if total <= 0:
        return start
    return start + timedelta(seconds=rng.randint(0, total))


def ensure_dirs(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "images").mkdir(parents=True, exist_ok=True)


def dump_json(path: Path, payload) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)


def load_json(path: Path, default):
    if not path.exists():
        return default
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def build_phone_number(rng: random.Random) -> tuple[str, str]:
    prefix = rng.choice(PHONE_PREFIXES)
    remaining = 8 if rng.random() < 0.7 else 9
    subscriber = "".join(rng.choices(string.digits, k=remaining))
    local = f"0{prefix}{subscriber}"
    e164 = f"+62{local[1:]}"
    return local, e164


def build_email(rng: random.Random, full_name: str) -> str:
    domains = ["example.com", "mail.test"]
    tokens = [t for t in re.split(r"[^a-zA-Z0-9]+", full_name.lower()) if t]
    base = "".join(tokens[:2])[:16] or "user"
    suffix = rng.randint(100, 9999)
    return f"{base}{suffix}@{rng.choice(domains)}"


def build_username(rng: random.Random, full_name: str) -> str:
    tokens = [t for t in re.split(r"[^a-zA-Z0-9]+", full_name.lower()) if t]
    base = "".join(tokens[:2])[:14] or "user"
    if rng.random() < 0.4:
        base = f"{tokens[0]}_{tokens[-1]}"[:18]
    suffix = str(rng.randint(10, 9999)) if rng.random() < 0.65 else ""
    return f"{base}{suffix}"


def avatar_url_for(profile_id: str) -> str:
    return f"{AVATAR_ENDPOINT}?seed={profile_id}"


def maybe_download_avatar(url: str, local_path: Path) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=20) as response:
            data = response.read()
        with open(local_path, "wb") as handle:
            handle.write(data)
        return True
    except (urllib.error.URLError, TimeoutError, ValueError):
        return False


class SyntheticDatasetGenerator:
    def __init__(self, seed: int = 42, openai_model: str | None = None):
        self.seed = seed
        self.rng = random.Random(seed)
        self.faker = Faker("id_ID")
        self.faker.seed_instance(seed)
        self.openai_model = openai_model or HARDCODED_OPENAI_MODEL or os.getenv("OPENAI_MODEL", DEFAULT_OPENAI_MODEL)
        api_key = (HARDCODED_OPENAI_API_KEY or os.getenv("OPENAI_API_KEY", "")).strip()
        self.openai_client = OpenAI(api_key=api_key) if api_key and OpenAI is not None else None

    @property
    def can_use_openai(self) -> bool:
        return self.openai_client is not None

    def _openai_json(self, system_prompt: str, user_prompt: str, fallback: dict) -> dict:
        if not self.can_use_openai:
            return fallback
        try:
            response = self.openai_client.responses.create( # pyright: ignore[reportOptionalMemberAccess]
                model=self.openai_model,
                reasoning={"effort": "minimal"},
                input=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            text = (response.output_text or "").strip()
            if text.startswith("```"):
                text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.DOTALL).strip()
            if not text:
                return fallback
            return json.loads(text)
        except Exception:
            return fallback

    def build_profiles_bundle(self, count: int, out_dir: str, with_images: bool = False) -> Bundle:
        out_path = Path(out_dir)
        ensure_dirs(out_path)

        profiles = []
        accounts = []
        contacts = []
        preferences = []
        photos = []
        posts = []
        friends = []
        network = []
        locations = []

        meeting_points = self._build_meeting_points()
        cluster_membership = self._assign_social_clusters(count)
        profile_cluster_ids = {idx: [] for idx in range(count)}
        for cluster in cluster_membership["clusters"]:
            for idx in cluster["member_indices"]:
                profile_cluster_ids[idx].append(cluster["cluster_id"])
        for bridge in cluster_membership["bridges"]:
            profile_cluster_ids[bridge["index"]].extend(bridge["cluster_ids"])

        account_by_profile: dict[str, list] = {}
        photo_by_profile: dict[str, list] = {}
        post_by_profile: dict[str, list] = {}

        now = datetime.now(INDONESIA_TZ)
        for idx in range(count):
            cluster = self.rng.choices(CITY_CLUSTERS, weights=CLUSTER_WEIGHTS, k=1)[0]
            lat, lon = random_point(self.rng, cluster["lat"], cluster["lon"], cluster["radius_km"])
            gender = self.rng.choice(["male", "female"])
            full_name = self.faker.name_male() if gender == "male" else self.faker.name_female()
            birth_start = self.rng.randint(1984, 2002)
            birth_range = f"{birth_start}-{birth_start + self.rng.randint(0, 2)}"
            interests = self.rng.sample(INTEREST_GROUPS, k=self.rng.randint(2, 4))
            persona_copy = self._persona_copy(full_name, cluster["city"], cluster["province"], interests, birth_range)
            display_name = persona_copy.get("display_name") or (full_name.split()[0] if self.rng.random() < 0.5 else full_name)
            bio = persona_copy.get("bio") or self.rng.choice(BIO_TEMPLATES).format(
                interest=self.rng.choice(interests),
                city=cluster["city"],
            )
            profile_id = rand_id("prof")
            local_phone, e164_phone = build_phone_number(self.rng)
            email = build_email(self.rng, full_name)
            avatar_url = avatar_url_for(profile_id)
            avatar_local = None
            if with_images:
                local_path = out_path / "images" / f"{profile_id}.jpg"
                if maybe_download_avatar(avatar_url, local_path):
                    avatar_local = f"images/{profile_id}.jpg"

            created_at = now - timedelta(days=self.rng.randint(150, 1800))
            profile = {
                "profile_id": profile_id,
                "full_name": full_name,
                "display_name": display_name,
                "gender": gender,
                "birth_year_range": birth_range,
                "bio": bio,
                "avatar_url": avatar_url,
                "avatar_local": avatar_local,
                "avatar_source": AVATAR_SOURCE,
                "country_code": "ID",
                "city": cluster["city"],
                "province": cluster["province"],
                "latitude": lat,
                "longitude": lon,
                "languages": self.rng.choice(LANGUAGE_SETS),
                "generated_at": now_iso(),
                "created_at": dt_to_iso(created_at),
                "cluster_ids": sorted(set(profile_cluster_ids[idx])),
                "risk_tags": [],
                "case_links": [],
            }
            profiles.append(profile)

            contact = {
                "contact_id": rand_id("ctc"),
                "profile_id": profile_id,
                "email": email,
                "phone_local": local_phone,
                "phone_e164": e164_phone,
                "city": cluster["city"],
                "province": cluster["province"],
                "is_primary": True,
            }
            contacts.append(contact)

            preference_entry = {
                "preference_id": rand_id("pref"),
                "profile_id": profile_id,
                "interests": interests,
                "activity_window": self.rng.choice(["pagi", "siang", "malam", "campuran"]),
                "device_usage": self.rng.choice(["android", "android+desktop", "ios", "android+tablet"]),
                "mobility_level": self.rng.choice(["rendah", "menengah", "tinggi"]),
                "copy_seed": persona_copy,
            }
            preferences.append(preference_entry)

            profile_locations = self._build_profile_locations(profile, cluster, meeting_points)
            locations.extend(profile_locations)

            accounts_for_profile = self._build_accounts(profile, interests)
            accounts.extend(accounts_for_profile)
            account_by_profile[profile_id] = accounts_for_profile

            photos_for_profile = self._build_photos(profile, cluster)
            photos.extend(photos_for_profile)
            photo_by_profile[profile_id] = photos_for_profile

        friends, network = self._build_social_graph(profiles, cluster_membership)
        posts = self._build_baseline_posts(profiles, account_by_profile, preferences)

        for post in posts:
            post_by_profile.setdefault(post["profile_id"], []).append(post)

        for profile in profiles:
            profile["extracted_profile"] = self._build_extracted_profile(
                profile=profile,
                contacts=next(item for item in contacts if item["profile_id"] == profile["profile_id"]),
                preferences=next(item for item in preferences if item["profile_id"] == profile["profile_id"]),
                accounts=account_by_profile.get(profile["profile_id"], []),
                friends=friends,
                photos=photo_by_profile.get(profile["profile_id"], []),
                posts=post_by_profile.get(profile["profile_id"], []),
                locations=locations,
            )

        return Bundle(
            profiles=profiles,
            accounts=accounts,
            contacts=contacts,
            preferences=preferences,
            photos=photos,
            posts=posts,
            friends=friends,
            network=network,
            locations=locations,
            cases=[],
            transactions=[],
            funding_alerts=[],
            campaigns=[],
            message_clusters=[],
            crawling=[],
            entities=[],
            alerts=[],
            risk_scores=[],
            reports=[],
        )

    def augment_bundle_with_cases(self, bundle: Bundle, case_names: list[str] | None = None) -> Bundle:
        requested = case_names or list(CASE_CONFIG.keys())
        requested = [name for name in requested if name in CASE_CONFIG]
        if not requested:
            return bundle

        self._reset_case_outputs(bundle)

        profiles_by_id = {profile["profile_id"]: profile for profile in bundle.profiles}
        accounts_by_profile: dict[str, list] = {}
        for account in bundle.accounts:
            accounts_by_profile.setdefault(account["profile_id"], []).append(account)

        social_clusters = self._group_profiles_by_cluster(bundle.profiles)
        shared_case_profiles = self._pick_case_actors(bundle.profiles, social_clusters)
        meeting_points = self._build_meeting_points()

        for case_name in requested:
            case_config = CASE_CONFIG[case_name]
            if case_name == "warehouse_fire":
                case_result = self._build_warehouse_fire_case(
                    bundle=bundle,
                    case_config=case_config,
                    accounts_by_profile=accounts_by_profile,
                    actor_pool=shared_case_profiles,
                    meeting_points=meeting_points,
                )
            elif case_name == "suspicious_funding":
                case_result = self._build_funding_case(
                    case_config=case_config,
                    accounts_by_profile=accounts_by_profile,
                    actor_pool=shared_case_profiles,
                    meeting_points=meeting_points,
                )
            else:
                case_result = self._build_propaganda_case(
                    case_config=case_config,
                    accounts_by_profile=accounts_by_profile,
                    actor_pool=shared_case_profiles,
                    meeting_points=meeting_points,
                )

            bundle.cases.append(case_result["case"])
            bundle.posts.extend(case_result["posts"])
            bundle.locations.extend(case_result["locations"])
            bundle.network.extend(case_result["network"])
            bundle.crawling.extend(case_result["crawling"])
            bundle.entities.extend(case_result["entities"])
            bundle.alerts.extend(case_result["alerts"])
            bundle.risk_scores.append(case_result["risk_score"])
            bundle.reports.append(case_result["report"])
            bundle.transactions.extend(case_result.get("transactions", []))
            bundle.funding_alerts.extend(case_result.get("funding_alerts", []))
            bundle.campaigns.extend(case_result.get("campaigns", []))
            bundle.message_clusters.extend(case_result.get("message_clusters", []))

            for link in case_result["case_links"]:
                profile = profiles_by_id[link["profile_id"]]
                profile["case_links"].append(link)
                if link["signal"] not in profile["risk_tags"]:
                    profile["risk_tags"].append(link["signal"])

        self._refresh_profile_extractions(bundle)
        return bundle

    def write_bundle(self, bundle: Bundle, out_dir: str) -> None:
        out_path = Path(out_dir)
        ensure_dirs(out_path)
        file_map = {
            "profiles.json": bundle.profiles,
            "accounts.json": bundle.accounts,
            "contacts.json": bundle.contacts,
            "preferences.json": bundle.preferences,
            "photos.json": bundle.photos,
            "posts.json": bundle.posts,
            "friends.json": bundle.friends,
            "network.json": bundle.network,
            "locations.json": bundle.locations,
            "cases.json": bundle.cases,
            "transactions.json": bundle.transactions,
            "funding_alerts.json": bundle.funding_alerts,
            "campaigns.json": bundle.campaigns,
            "message_clusters.json": bundle.message_clusters,
            "crawling.json": bundle.crawling,
            "entities.json": bundle.entities,
            "alerts.json": bundle.alerts,
            "risk_scores.json": bundle.risk_scores,
            "reports.json": bundle.reports,
        }
        for file_name, payload in file_map.items():
            dump_json(out_path / file_name, payload)

    def load_bundle(self, out_dir: str) -> Bundle:
        out_path = Path(out_dir)
        return Bundle(
            profiles=load_json(out_path / "profiles.json", []),
            accounts=load_json(out_path / "accounts.json", []),
            contacts=load_json(out_path / "contacts.json", []),
            preferences=load_json(out_path / "preferences.json", []),
            photos=load_json(out_path / "photos.json", []),
            posts=load_json(out_path / "posts.json", []),
            friends=load_json(out_path / "friends.json", []),
            network=load_json(out_path / "network.json", []),
            locations=load_json(out_path / "locations.json", []),
            cases=load_json(out_path / "cases.json", []),
            transactions=load_json(out_path / "transactions.json", []),
            funding_alerts=load_json(out_path / "funding_alerts.json", []),
            campaigns=load_json(out_path / "campaigns.json", []),
            message_clusters=load_json(out_path / "message_clusters.json", []),
            crawling=load_json(out_path / "crawling.json", []),
            entities=load_json(out_path / "entities.json", []),
            alerts=load_json(out_path / "alerts.json", []),
            risk_scores=load_json(out_path / "risk_scores.json", []),
            reports=load_json(out_path / "reports.json", []),
        )

    def _build_meeting_points(self) -> list[dict]:
        points = []
        for cluster in CITY_CLUSTERS:
            for point_type in MEETING_POINT_TYPES:
                lat, lon = random_point(self.rng, cluster["lat"], cluster["lon"], min(cluster["radius_km"], 3.0))
                point_id = f"meet-{slugify(cluster['city'])}-{point_type}"
                points.append(
                    {
                        "meeting_point_id": point_id,
                        "city": cluster["city"],
                        "province": cluster["province"],
                        "type": point_type,
                        "label": f"{cluster['city']} {point_type.replace('_', ' ')}",
                        "latitude": lat,
                        "longitude": lon,
                    }
                )
        return points

    def _persona_copy(self, full_name: str, city: str, province: str, interests: list[str], birth_range: str) -> dict:
        fallback = {
            "display_name": full_name.split()[0],
            "bio": self.rng.choice(BIO_TEMPLATES).format(interest=self.rng.choice(interests), city=city),
            "search_results": self.rng.sample(SEARCH_RESULT_SNIPPETS, k=3),
            "post_samples": [
                self.rng.choice(POST_TEMPLATES).format(city=city, interest=self.rng.choice(interests), tagline="#catatan"),
                self.rng.choice(POST_TEMPLATES).format(city=city, interest=self.rng.choice(interests), tagline="#update"),
                self.rng.choice(POST_TEMPLATES).format(city=city, interest=self.rng.choice(interests), tagline="#komunitas"),
            ],
        }
        return self._openai_json(
            system_prompt=(
                "You create realistic Indonesian persona copy for product testing. "
                "Return compact JSON with keys display_name, bio, search_results, post_samples. "
                "Do not mention testing, synthetic, simulation, mock, or fictional framing."
            ),
            user_prompt=(
                f"Name: {full_name}\n"
                f"City: {city}\nProvince: {province}\n"
                f"Interest tags: {', '.join(interests)}\n"
                f"Birth year range: {birth_range}\n"
                "Write natural everyday Indonesian. search_results and post_samples should each contain 3 short strings."
            ),
            fallback=fallback,
        )

    def _case_copy(self, case_key: str, city: str, province: str) -> dict:
        fallback_map = {
            "warehouse_fire": {
                "summary": "Data lapangan memperlihatkan ledakan awal, narasi seragam, dan sinyal kehadiran bersama sebelum kejadian.",
                "analysis": "Pola ini masih indikatif, tetapi cukup kuat untuk diuji sebagai koordinasi terorganisir.",
                "recommendations": [
                    "Bandingkan check-in lokasi dengan data posting.",
                    "Uji ulang akun penghubung dan pola waktu posting.",
                    "Kelompokkan saksi, narasi, dan edge jaringan per window waktu.",
                ],
            },
            "suspicious_funding": {
                "summary": "Transaksi kecil berulang, overlap perangkat, dan pertemuan terbatas memberi sinyal koordinasi finansial.",
                "analysis": "Belum konklusif, namun pola transfer dan lokasi mengarah pada hubungan yang perlu diprioritaskan.",
                "recommendations": [
                    "Uji graf transfer terhadap graf pertemanan.",
                    "Bandingkan device overlap dengan meeting point.",
                    "Prioritaskan akun yang muncul lintas kasus.",
                ],
            },
            "propaganda": {
                "summary": "Satu sumber narasi diikuti amplifikasi cepat dari sejumlah akun dengan wording berdekatan.",
                "analysis": "Pola waktu dan kemiripan pesan mengindikasikan koordinasi narasi, meski belum bersifat final.",
                "recommendations": [
                    "Kelompokkan posting berdasarkan similarity dan timestamp.",
                    "Pisahkan akun baru dan akun lama.",
                    "Bandingkan overlap dengan sinyal pendanaan dan lokasi.",
                ],
            },
        }
        fallback = fallback_map[case_key]
        return self._openai_json(
            system_prompt=(
                "You write concise Indonesian intelligence-style summaries for an internal analytics product. "
                "Return JSON with keys summary, analysis, recommendations. "
                "Do not mention synthetic, mock, simulation, fictional, or testing."
            ),
            user_prompt=(
                f"Case: {case_key}\nCity: {city}\nProvince: {province}\n"
                "Tone: cautious, analytical, non-final. recommendations must contain 3 short Indonesian strings."
            ),
            fallback=fallback,
        )

    def _assign_social_clusters(self, count: int) -> dict:
        indices = list(range(count))
        self.rng.shuffle(indices)
        cluster_count = 3 if count < 150 else 4
        cursor = 0
        clusters = []
        for cluster_idx in range(cluster_count):
            size = min(max(6, count // 18), 12)
            if cursor + size > len(indices):
                size = max(4, len(indices) - cursor)
            if size <= 0:
                break
            members = indices[cursor : cursor + size]
            cursor += size
            clusters.append({"cluster_id": f"cluster-{cluster_idx + 1}", "member_indices": members})
        bridges = []
        if len(clusters) >= 2 and cursor < len(indices):
            bridge_count = min(2, len(indices) - cursor)
            for bridge_idx in range(bridge_count):
                index = indices[cursor + bridge_idx]
                linked = self.rng.sample([cluster["cluster_id"] for cluster in clusters], k=2)
                bridges.append({"index": index, "cluster_ids": linked})
        return {"clusters": clusters, "bridges": bridges}

    def _build_profile_locations(self, profile: dict, cluster: dict, meeting_points: list[dict]) -> list[dict]:
        entries = [
            {
                "location_id": rand_id("loc"),
                "profile_id": profile["profile_id"],
                "location_type": "home_base",
                "label": f"Area tinggal {cluster['city']}",
                "city": cluster["city"],
                "province": cluster["province"],
                "latitude": profile["latitude"],
                "longitude": profile["longitude"],
                "observed_at": profile["created_at"],
                "confidence": 0.88,
            }
        ]
        matching_points = [point for point in meeting_points if point["city"] == cluster["city"]]
        self.rng.shuffle(matching_points)
        for point in matching_points[: self.rng.randint(1, 2)]:
            entries.append(
                {
                    "location_id": rand_id("loc"),
                    "profile_id": profile["profile_id"],
                    "location_type": "frequent_spot",
                    "meeting_point_id": point["meeting_point_id"],
                    "label": point["label"],
                    "city": point["city"],
                    "province": point["province"],
                    "latitude": point["latitude"],
                    "longitude": point["longitude"],
                    "observed_at": profile["generated_at"],
                    "confidence": round(self.rng.uniform(0.55, 0.83), 2),
                }
            )
        return entries

    def _build_accounts(self, profile: dict, interests: list[str]) -> list[dict]:
        now = datetime.now(INDONESIA_TZ)
        account_count = self.rng.randint(2, 4)
        selected_platforms = self.rng.sample(PLATFORMS, k=account_count)
        accounts = []
        for platform in selected_platforms:
            username = build_username(self.rng, profile["full_name"])
            created_at = now - timedelta(days=self.rng.randint(7, 1600))
            accounts.append(
                {
                    "account_id": rand_id("acct"),
                    "profile_id": profile["profile_id"],
                    "platform": platform,
                    "username": username,
                    "profile_url": f"https://social.local/{platform}/{username}",
                    "created_at": dt_to_iso(created_at),
                    "followers_count": self.rng.randint(20, 8500),
                    "following_count": self.rng.randint(15, 2200),
                    "post_count": self.rng.randint(8, 420),
                    "verified_status": self.rng.random() < 0.03,
                    "last_active_at": dt_to_iso(now - timedelta(hours=self.rng.randint(1, 240))),
                    "interest_hint": self.rng.choice(interests),
                }
            )
        return accounts

    def _build_photos(self, profile: dict, cluster: dict) -> list[dict]:
        photos = []
        for _ in range(self.rng.randint(1, 3)):
            lat, lon = random_point(self.rng, profile["latitude"], profile["longitude"], 2.0)
            photos.append(
                {
                    "photo_id": rand_id("photo"),
                    "profile_id": profile["profile_id"],
                    "caption": self.rng.choice(
                        [
                            f"Sudut lain dari {cluster['city']}.",
                            "Dokumentasi kegiatan harian.",
                            "Lagi keliling sebentar sambil cek suasana.",
                            "Arsip foto kegiatan.",
                        ]
                    ),
                    "taken_at": dt_to_iso(datetime.now(INDONESIA_TZ) - timedelta(days=self.rng.randint(1, 600))),
                    "city": cluster["city"],
                    "province": cluster["province"],
                    "latitude": lat,
                    "longitude": lon,
                    "content_type": self.rng.choice(["street", "selfie", "group", "food", "event"]),
                }
            )
        return photos

    def _build_social_graph(self, profiles: list[dict], cluster_membership: dict) -> tuple[list, list]:
        friends = []
        network = []
        profiles_by_index = {idx: profile for idx, profile in enumerate(profiles)}
        existing_pairs = set()

        for cluster in cluster_membership["clusters"]:
            members = [profiles_by_index[idx] for idx in cluster["member_indices"]]
            for i, left in enumerate(members):
                for right in members[i + 1 :]:
                    if self.rng.random() > 0.42:
                        continue
                    pair = tuple(sorted((left["profile_id"], right["profile_id"])))
                    if pair in existing_pairs:
                        continue
                    existing_pairs.add(pair)
                    since = dt_to_iso(datetime.now(INDONESIA_TZ) - timedelta(days=self.rng.randint(90, 1200)))
                    friends.append(
                        {
                            "friendship_id": rand_id("fr"),
                            "profile_a": pair[0],
                            "profile_b": pair[1],
                            "strength": round(self.rng.uniform(0.52, 0.94), 2),
                            "cluster_id": cluster["cluster_id"],
                            "since": since,
                        }
                    )
                    network.append(
                        {
                            "edge_id": rand_id("edge"),
                            "source_profile_id": pair[0],
                            "target_profile_id": pair[1],
                            "edge_type": "social_connection",
                            "weight": round(self.rng.uniform(0.5, 0.95), 2),
                            "cluster_id": cluster["cluster_id"],
                        }
                    )

        for bridge in cluster_membership["bridges"]:
            bridge_profile = profiles_by_index[bridge["index"]]
            for cluster_id in bridge["cluster_ids"]:
                cluster = next(item for item in cluster_membership["clusters"] if item["cluster_id"] == cluster_id)
                members = [profiles_by_index[idx] for idx in cluster["member_indices"]]
                for target in self.rng.sample(members, k=min(4, len(members))):
                    pair = tuple(sorted((bridge_profile["profile_id"], target["profile_id"])))
                    if pair in existing_pairs:
                        continue
                    existing_pairs.add(pair)
                    friends.append(
                        {
                            "friendship_id": rand_id("fr"),
                            "profile_a": pair[0],
                            "profile_b": pair[1],
                            "strength": round(self.rng.uniform(0.61, 0.97), 2),
                            "cluster_id": cluster_id,
                            "since": dt_to_iso(datetime.now(INDONESIA_TZ) - timedelta(days=self.rng.randint(60, 800))),
                            "is_bridge": True,
                        }
                    )
                    network.append(
                        {
                            "edge_id": rand_id("edge"),
                            "source_profile_id": bridge_profile["profile_id"],
                            "target_profile_id": target["profile_id"],
                            "edge_type": "bridge_connection",
                            "weight": round(self.rng.uniform(0.62, 0.98), 2),
                            "cluster_id": cluster_id,
                        }
                    )

        non_cluster_profiles = [p for p in profiles if not p["cluster_ids"]]
        for _ in range(max(3, len(profiles) // 35)):
            if len(non_cluster_profiles) < 2:
                break
            left, right = self.rng.sample(non_cluster_profiles, 2)
            if left["city"] != right["city"] and self.rng.random() < 0.7:
                continue
            pair = tuple(sorted((left["profile_id"], right["profile_id"])))
            if pair in existing_pairs:
                continue
            existing_pairs.add(pair)
            friends.append(
                {
                    "friendship_id": rand_id("fr"),
                    "profile_a": pair[0],
                    "profile_b": pair[1],
                    "strength": round(self.rng.uniform(0.22, 0.55), 2),
                    "cluster_id": None,
                    "since": dt_to_iso(datetime.now(INDONESIA_TZ) - timedelta(days=self.rng.randint(30, 500))),
                }
            )
            network.append(
                {
                    "edge_id": rand_id("edge"),
                    "source_profile_id": pair[0],
                    "target_profile_id": pair[1],
                    "edge_type": "light_connection",
                    "weight": round(self.rng.uniform(0.2, 0.45), 2),
                }
            )
        return friends, network

    def _build_baseline_posts(self, profiles: list[dict], accounts_by_profile: dict[str, list], preferences: list[dict]) -> list[dict]:
        pref_map = {item["profile_id"]: item for item in preferences}
        posts = []
        now = datetime.now(INDONESIA_TZ)
        for profile in profiles:
            accounts = accounts_by_profile.get(profile["profile_id"], [])
            if not accounts:
                continue
            pref = pref_map[profile["profile_id"]]
            seeded_posts = pref.get("copy_seed", {}).get("post_samples", [])
            count = self.rng.randint(5, 12)
            for idx in range(count):
                account = self.rng.choice(accounts)
                created_at = random_time_between(self.rng, now - timedelta(days=365), now - timedelta(hours=4))
                interest = self.rng.choice(pref["interests"])
                content = seeded_posts[idx % len(seeded_posts)] if seeded_posts else self.rng.choice(POST_TEMPLATES).format(
                    city=profile["city"],
                    interest=interest,
                    tagline=self.rng.choice(["#catatan", "#harian", "#komunitas", "#update", "#local"]),
                )
                posts.append(
                    {
                        "post_id": rand_id("post"),
                        "profile_id": profile["profile_id"],
                        "account_id": account["account_id"],
                        "platform": account["platform"],
                        "content": content,
                        "timestamp": dt_to_iso(created_at),
                        "city": profile["city"],
                        "province": profile["province"],
                        "latitude": profile["latitude"],
                        "longitude": profile["longitude"],
                        "content_type": self.rng.choice(["text", "image", "comment", "repost"]),
                        "engagement": {
                            "likes": self.rng.randint(0, 250),
                            "comments": self.rng.randint(0, 80),
                            "shares": self.rng.randint(0, 45),
                        },
                        "hashtags": self.rng.sample(
                            ["#lokal", "#malam", "#jalan", "#update", "#komunitas", "#fokus"],
                            k=self.rng.randint(1, 3),
                        ),
                        "keywords": self.rng.sample(pref["interests"], k=min(2, len(pref["interests"]))),
                        "mention_refs": [],
                        "reply_to_post_id": None,
                        "repost_of_post_id": None,
                        "source_type": "organic",
                        "scenario_refs": [],
                    }
                )
        return posts

    def _build_extracted_profile(
        self,
        profile: dict,
        contacts: dict,
        preferences: dict,
        accounts: list[dict],
        friends: list[dict],
        photos: list[dict],
        posts: list[dict],
        locations: list[dict],
    ) -> dict:
        related_locations = [item for item in locations if item["profile_id"] == profile["profile_id"]][:5]
        related_friends = [
            item for item in friends if profile["profile_id"] in (item["profile_a"], item["profile_b"])
        ][:8]
        search_results = []
        for idx in range(self.rng.randint(2, 4)):
            search_results.append(
                {
                    "rank": idx + 1,
                    "source": self.rng.choice(["search", "forum", "social"]),
                    "title": f"Hasil pencarian untuk {profile['display_name']}",
                    "snippet": self.rng.choice(preferences.get("copy_seed", {}).get("search_results", SEARCH_RESULT_SNIPPETS)),
                }
            )
        return {
            "personal_information": {
                "full_name": profile["full_name"],
                "display_name": profile["display_name"],
                "gender": profile["gender"],
                "birth_year_range": profile["birth_year_range"],
                "country_code": profile["country_code"],
            },
            "locations": related_locations,
            "accounts": [
                {
                    "platform": account["platform"],
                    "username": account["username"],
                    "created_at": account["created_at"],
                    "last_active_at": account["last_active_at"],
                }
                for account in accounts
            ],
            "statistics": {
                "account_count": len(accounts),
                "friend_count": len(related_friends),
                "photo_count": len(photos),
                "post_count": len(posts),
            },
            "friends": related_friends,
            "photos": photos[:6],
            "posts": posts[:10],
            "web_search_results": search_results,
            "preferences": preferences,
            "contact_info": contacts,
            "synopsis": f"{profile['display_name']} berbasis di {profile['city']} dengan minat utama {', '.join(preferences['interests'][:2])}.",
            "case_links": profile.get("case_links", []),
        }

    def _group_profiles_by_cluster(self, profiles: list[dict]) -> dict[str, list[str]]:
        grouped: dict[str, list[str]] = {}
        for profile in profiles:
            for cluster_id in profile["cluster_ids"]:
                grouped.setdefault(cluster_id, []).append(profile["profile_id"])
        return grouped

    def _pick_case_actors(self, profiles: list[dict], social_clusters: dict[str, list[str]]) -> dict[str, list[str]]:
        all_profile_ids = [profile["profile_id"] for profile in profiles]
        cluster_ids = sorted(social_clusters)
        actor_pool = {
            "overlap": self.rng.sample(all_profile_ids, k=min(5, len(all_profile_ids))),
            "isolated_noise": [profile["profile_id"] for profile in profiles if not profile["cluster_ids"]][: max(8, len(profiles) // 15)],
        }
        if cluster_ids:
            actor_pool["cluster_a"] = social_clusters[cluster_ids[0]][:]
            actor_pool["cluster_b"] = social_clusters[cluster_ids[1]][:] if len(cluster_ids) > 1 else social_clusters[cluster_ids[0]][:]
            actor_pool["cluster_c"] = social_clusters[cluster_ids[2]][:] if len(cluster_ids) > 2 else social_clusters[cluster_ids[0]][:]
        else:
            actor_pool["cluster_a"] = self.rng.sample(all_profile_ids, k=min(8, len(all_profile_ids)))
            actor_pool["cluster_b"] = self.rng.sample(all_profile_ids, k=min(8, len(all_profile_ids)))
            actor_pool["cluster_c"] = self.rng.sample(all_profile_ids, k=min(8, len(all_profile_ids)))
        return actor_pool

    def _pick_meeting_point(self, meeting_points: list[dict], city: str, point_type: str) -> dict:
        matches = [item for item in meeting_points if item["city"] == city and item["type"] == point_type]
        return self.rng.choice(matches)

    def _append_case_checkins(
        self,
        profile_ids: list[str],
        meeting_point: dict,
        incident_at: datetime,
        case_id: str,
    ) -> tuple[list, list]:
        location_entries = []
        network_entries = []
        for profile_id in profile_ids:
            observed_at = incident_at - timedelta(hours=self.rng.randint(4, 56), minutes=self.rng.randint(0, 55))
            location_entries.append(
                {
                    "location_id": rand_id("loc"),
                    "profile_id": profile_id,
                    "location_type": "case_checkin",
                    "meeting_point_id": meeting_point["meeting_point_id"],
                    "label": meeting_point["label"],
                    "city": meeting_point["city"],
                    "province": meeting_point["province"],
                    "latitude": meeting_point["latitude"],
                    "longitude": meeting_point["longitude"],
                    "observed_at": dt_to_iso(observed_at),
                    "confidence": round(self.rng.uniform(0.64, 0.94), 2),
                    "case_id": case_id,
                }
            )
        for idx, left in enumerate(profile_ids):
            for right in profile_ids[idx + 1 :]:
                if self.rng.random() > 0.33:
                    continue
                network_entries.append(
                    {
                        "edge_id": rand_id("edge"),
                        "source_profile_id": left,
                        "target_profile_id": right,
                        "edge_type": "shared_meeting_point",
                        "weight": round(self.rng.uniform(0.55, 0.9), 2),
                        "meeting_point_id": meeting_point["meeting_point_id"],
                        "case_id": case_id,
                    }
                )
        return location_entries, network_entries

    def _build_warehouse_fire_case(self, bundle: Bundle, case_config: dict, accounts_by_profile: dict, actor_pool: dict, meeting_points: list[dict]) -> dict:
        case_id = case_config["case_id"]
        incident_at = case_config["incident_at"]
        cluster_members = actor_pool["cluster_a"][:]
        bridge_candidates = [profile["profile_id"] for profile in bundle.profiles if len(profile["cluster_ids"]) > 1]
        self.rng.shuffle(cluster_members)
        actors = list(dict.fromkeys(cluster_members[:8] + bridge_candidates[:2] + actor_pool["overlap"][:2]))
        meeting_point = self._pick_meeting_point(meeting_points, case_config["city"], case_config["meeting_type"])

        posts = []
        for idx, profile_id in enumerate(actors[:10]):
            account = self.rng.choice(accounts_by_profile[profile_id])
            if idx == 0:
                content = "Akan ada kejutan besar di kawasan industri itu. #pengingat"
                timestamp = incident_at - timedelta(days=2, hours=1)
            elif idx < 4:
                content = self.rng.choice(
                    [
                        "Baru aja denger ledakan sebelum api gede naik. #bekasi #malam",
                        "Ini bukan kebakaran biasa, tadi ada bunyi keras duluan.",
                        "Asap hitamnya tebal banget, kayak ada bahan lain ikut kebakar.",
                    ]
                )
                timestamp = incident_at + timedelta(minutes=self.rng.randint(5, 80))
            else:
                content = self.rng.choice(
                    [
                        "Info awal katanya korsleting, tapi saksi pada beda cerita.",
                        "Motor sempat keluar dari area sebelum api membesar.",
                        "Timeline rame, banyak yang bilang ada bau bahan kimia.",
                    ]
                )
                timestamp = incident_at + timedelta(minutes=self.rng.randint(20, 240))
            posts.append(
                {
                    "post_id": rand_id("post"),
                    "profile_id": profile_id,
                    "account_id": account["account_id"],
                    "platform": account["platform"],
                    "content": content,
                    "timestamp": dt_to_iso(timestamp),
                    "city": case_config["city"],
                    "province": case_config["province"],
                    "latitude": meeting_point["latitude"],
                    "longitude": meeting_point["longitude"],
                    "content_type": self.rng.choice(["text", "image", "video", "comment"]),
                    "engagement": {
                        "likes": self.rng.randint(4, 460),
                        "comments": self.rng.randint(0, 140),
                        "shares": self.rng.randint(0, 120),
                    },
                    "hashtags": ["#gudang", "#kebakaran", "#industri"],
                    "keywords": ["ledakan", "bau_kimia", "motor_mencurigakan"],
                    "mention_refs": [],
                    "reply_to_post_id": None,
                    "repost_of_post_id": None,
                    "source_type": "case_signal",
                    "scenario_refs": [case_id],
                }
            )

        locations, meeting_network = self._append_case_checkins(actors[:7], meeting_point, incident_at, case_id)
        entities = [
            {"case_id": case_id, "entity_type": "location", "value": "kawasan industri Bekasi", "count": 132},
            {"case_id": case_id, "entity_type": "keyword", "value": "ledakan", "count": 188},
            {"case_id": case_id, "entity_type": "keyword", "value": "bau kimia", "count": 87},
            {"case_id": case_id, "entity_type": "keyword", "value": "motor mencurigakan", "count": 53},
            {"case_id": case_id, "entity_type": "time_anchor", "value": "02:30 WIB", "count": 241},
        ]
        alerts = [
            {
                "alert_id": rand_id("alert"),
                "case_id": case_id,
                "severity": "high",
                "signal_type": "pre_event_post",
                "description": "Terdapat post 2 hari sebelum kejadian yang menyebut kejutan besar di kawasan industri.",
                "confidence": 0.82,
            },
            {
                "alert_id": rand_id("alert"),
                "case_id": case_id,
                "severity": "medium",
                "signal_type": "copy_paste_narrative",
                "description": "Sekelompok akun menyebarkan wording mirip soal ledakan dan bau kimia dalam rentang waktu sempit.",
                "confidence": 0.79,
            },
            {
                "alert_id": rand_id("alert"),
                "case_id": case_id,
                "severity": "medium",
                "signal_type": "co_location",
                "description": "Beberapa profil terlihat check-in di titik logistik yang sama sebelum insiden.",
                "confidence": 0.74,
            },
        ]
        risk_score = {
            "case_id": case_id,
            "risk_label": "high",
            "risk_score": 78,
            "accident_probability": 0.58,
            "organized_sabotage_probability": 0.42,
            "drivers": ["ledakan_awal", "akun_sinkron", "pre_event_post", "co_location_signal"],
            "disclaimer": "Penilaian ini indikatif dan bukan atribusi final.",
        }
        report = {
            "report_id": rand_id("rpt"),
            "case_id": case_id,
            "title": case_config["title"],
            "summary": "Data crawling menunjukkan indikasi ledakan awal, narasi seragam, dan sinyal kehadiran bersama sebelum kejadian.",
            "findings": [
                "Sekitar 30% mention menyebut ledakan sebelum api besar.",
                "Sebagian akun menyebarkan narasi seragam dalam waktu hampir bersamaan.",
                "Terdapat post pra-insiden dan sinyal shared meeting point.",
            ],
            "analysis": "Belum cukup dasar untuk atribusi final, namun pola konsisten dengan sabotase terorganisir atau koordinasi narasi pasca-insiden.",
            "recommendations": [
                "Monitor akun dan bridge account yang overlap dengan kasus lain.",
                "Bandingkan check-in lokasi dengan data posting dan edge jaringan.",
                "Uji kembali wording copy-paste dan kedekatan timestamp.",
            ],
            "generated_at": now_iso(),
            "disclaimer": "Laporan ini bersifat indikatif untuk kebutuhan analisis internal.",
        }
        case_links = [
            {"case_id": case_id, "profile_id": profile_id, "role": "observed_actor" if idx < 7 else "signal_account", "signal": "warehouse_fire_signal"}
            for idx, profile_id in enumerate(actors[:10])
        ]
        case = {
            "case_id": case_id,
            "case_type": "warehouse_fire",
            "title": case_config["title"],
            "city": case_config["city"],
            "province": case_config["province"],
            "incident_at": dt_to_iso(incident_at),
            "meeting_point_id": meeting_point["meeting_point_id"],
            "actor_count": len(actors[:10]),
            "status": "monitoring",
        }
        return {
            "case": case,
            "posts": posts,
            "locations": locations,
            "network": meeting_network,
            "crawling": self._build_warehouse_crawling(case_id, case_config, actors),
            "entities": entities,
            "alerts": alerts,
            "risk_score": risk_score,
            "report": report,
            "case_links": case_links,
        }

    def _build_funding_case(self, case_config: dict, accounts_by_profile: dict, actor_pool: dict, meeting_points: list[dict]) -> dict:
        case_id = case_config["case_id"]
        incident_at = case_config["incident_at"]
        actors = list(dict.fromkeys(actor_pool["cluster_b"][:7] + actor_pool["overlap"][:3]))
        meeting_point = self._pick_meeting_point(meeting_points, case_config["city"], case_config["meeting_type"])

        transactions = []
        network = []
        posts = []
        for idx in range(max(8, len(actors) - 1)):
            source, target = self.rng.sample(actors, 2)
            amount = self.rng.randint(350000, 2900000)
            ts = incident_at - timedelta(days=self.rng.randint(1, 18), hours=self.rng.randint(0, 10))
            transactions.append(
                {
                    "transaction_id": rand_id("txn"),
                    "case_id": case_id,
                    "source_profile_id": source,
                    "target_profile_id": target,
                    "amount_idr": amount,
                    "timestamp": dt_to_iso(ts),
                    "channel": self.rng.choice(["bank_transfer", "ewallet", "cash_note"]),
                    "reference": f"REF-{self.rng.randint(100000, 999999)}",
                    "purpose_hint": self.rng.choice(FUNDING_PURPOSES),
                    "shared_device_id": f"DEV-{self.rng.randint(1000, 9999)}" if idx < 4 else None,
                    "shared_ip": f"10.42.{self.rng.randint(1, 200)}.{self.rng.randint(2, 220)}" if idx < 5 else None,
                }
            )
            network.append(
                {
                    "edge_id": rand_id("edge"),
                    "source_profile_id": source,
                    "target_profile_id": target,
                    "edge_type": "financial_transfer",
                    "weight": round(min(amount / 3000000, 0.99), 2),
                    "case_id": case_id,
                }
            )

        for profile_id in actors[:6]:
            account = self.rng.choice(accounts_by_profile[profile_id])
            posts.append(
                {
                    "post_id": rand_id("post"),
                    "profile_id": profile_id,
                    "account_id": account["account_id"],
                    "platform": account["platform"],
                    "content": self.rng.choice(
                        [
                            "Siapkan dana operasional kecil-kecilan dulu, nanti disesuaikan.",
                            "Drop dulu yang urgent. Rincian menyusul di jalur aman.",
                            "Kebutuhan minggu ini jangan sampai telat, sisanya nanti dibahas.",
                        ]
                    ),
                    "timestamp": dt_to_iso(incident_at - timedelta(days=self.rng.randint(2, 11))),
                    "city": case_config["city"],
                    "province": case_config["province"],
                    "latitude": meeting_point["latitude"],
                    "longitude": meeting_point["longitude"],
                    "content_type": "text",
                    "engagement": {"likes": self.rng.randint(0, 48), "comments": self.rng.randint(0, 18), "shares": self.rng.randint(0, 6)},
                    "hashtags": ["#support", "#koordinasi"],
                    "keywords": ["transfer", "operasional", "drop"],
                    "mention_refs": [],
                    "reply_to_post_id": None,
                    "repost_of_post_id": None,
                    "source_type": "case_signal",
                    "scenario_refs": [case_id],
                }
            )

        crawling = []
        for _ in range(220):
            crawling.append(
                {
                    "data_point_id": rand_id("crawl"),
                    "case_id": case_id,
                    "source_type": self.rng.choice(["forum", "chat", "transaction_note", "social_media"]),
                    "platform": self.rng.choice(["telegram", "forum", "twitter", "bank_log"]),
                    "profile_ref": self.rng.choice(actors) if self.rng.random() < 0.55 else None,
                    "content": self.rng.choice(
                        [
                            "Transfer kecil berulang muncul pada rentang waktu berdekatan.",
                            "Akun forum membahas iuran logistik tanpa rincian jelas.",
                            "Komentar komunitas menyebut pengumpulan dana mendadak.",
                            "Ada catatan tentang rekening perantara dan pertemuan singkat.",
                            "Sebagian sinyal bisa saja sekadar iuran komunitas biasa.",
                        ]
                    ),
                    "timestamp": dt_to_iso(incident_at - timedelta(days=self.rng.randint(1, 20), hours=self.rng.randint(0, 23))),
                    "city": case_config["city"],
                    "province": case_config["province"],
                    "latitude": meeting_point["latitude"],
                    "longitude": meeting_point["longitude"],
                    "signal_tags": self.rng.sample(["transfer", "iuran", "meeting", "wallet", "noise"], k=2),
                    "reliability": round(self.rng.uniform(0.22, 0.89), 2),
                }
            )

        locations, meeting_network = self._append_case_checkins(actors[:6], meeting_point, incident_at, case_id)
        entities = [
            {"case_id": case_id, "entity_type": "keyword", "value": "transfer kecil berulang", "count": 78},
            {"case_id": case_id, "entity_type": "location", "value": meeting_point["label"], "count": 34},
            {"case_id": case_id, "entity_type": "keyword", "value": "shared_device", "count": 12},
        ]
        alerts = [
            {
                "alert_id": rand_id("alert"),
                "case_id": case_id,
                "severity": "medium",
                "signal_type": "financial_pattern",
                "description": "Pola transfer menunjukkan distribusi dana kecil berulang ke cluster terbatas.",
                "confidence": 0.76,
            }
        ]
        risk_score = {
            "case_id": case_id,
            "risk_label": "medium",
            "risk_score": 67,
            "routine_support_probability": 0.54,
            "coordinated_funding_probability": 0.46,
            "drivers": ["repeated_transfer", "shared_device", "co_location"],
            "disclaimer": "Penilaian ini indikatif dan bukan atribusi final.",
        }
        report = {
            "report_id": rand_id("rpt"),
            "case_id": case_id,
            "title": case_config["title"],
            "summary": "Data memperlihatkan transaksi kecil berulang, kedekatan lokasi antar aktor, dan penggunaan device/IP yang tumpang tindih.",
            "findings": [
                "Transfer tersebar muncul menjelang aktivitas lapangan tertentu.",
                "Beberapa profil yang sama juga terlihat pada cluster propaganda atau warehouse fire.",
                "Shared meeting point memperkuat sinyal korelasi lintas kasus.",
            ],
            "analysis": "Pola dapat dibaca sebagai koordinasi finansial, namun masih butuh validasi lintas sumber.",
            "recommendations": [
                "Uji graf transfer versus graf sosial.",
                "Periksa device/IP overlap dan titik temu lokasi bersama.",
                "Prioritaskan bridge account yang muncul lintas kasus.",
            ],
            "generated_at": now_iso(),
            "disclaimer": "Laporan ini bersifat indikatif untuk kebutuhan analisis internal.",
        }
        case_links = [{"case_id": case_id, "profile_id": profile_id, "role": "funding_actor", "signal": "funding_signal"} for profile_id in actors]
        case = {
            "case_id": case_id,
            "case_type": "suspicious_funding",
            "title": case_config["title"],
            "city": case_config["city"],
            "province": case_config["province"],
            "incident_at": dt_to_iso(incident_at),
            "meeting_point_id": meeting_point["meeting_point_id"],
            "actor_count": len(actors),
            "status": "analysis",
        }
        return {
            "case": case,
            "posts": posts,
            "locations": locations,
            "network": network + meeting_network,
            "crawling": crawling,
            "entities": entities,
            "alerts": alerts,
            "risk_score": risk_score,
            "report": report,
            "transactions": transactions,
            "funding_alerts": [
                {
                    "funding_alert_id": rand_id("falert"),
                    "case_id": case_id,
                    "severity": "medium",
                    "description": "Sejumlah transfer kecil berulang mengarah ke penerima yang sama dalam jendela waktu sempit.",
                    "confidence": 0.77,
                },
                {
                    "funding_alert_id": rand_id("falert"),
                    "case_id": case_id,
                    "severity": "medium",
                    "description": "Sebagian transaksi berbagi device atau IP yang sama.",
                    "confidence": 0.71,
                },
            ],
            "case_links": case_links,
        }

    def _build_propaganda_case(self, case_config: dict, accounts_by_profile: dict, actor_pool: dict, meeting_points: list[dict]) -> dict:
        case_id = case_config["case_id"]
        incident_at = case_config["incident_at"]
        actors = list(dict.fromkeys(actor_pool["cluster_c"][:10] + actor_pool["overlap"][:2]))
        meeting_point = self._pick_meeting_point(meeting_points, case_config["city"], case_config["meeting_type"])
        central = actors[0]
        variants = [
            "disrupsi supply chain bikin pihak tertentu kelabakan malam ini",
            "gangguan rantai pasok bikin situasi cepat berubah malam ini",
            "jalur distribusi lagi terganggu, efeknya bakal terasa cepat",
            "supply chain yang terguncang bisa bikin respons mereka terlambat",
        ]

        posts = []
        message_clusters = []
        campaigns = [
            {
                "campaign_id": rand_id("camp"),
                "case_id": case_id,
                "central_profile_id": central,
                "objective": "amplifikasi narasi terkait gangguan distribusi",
                "start_at": dt_to_iso(incident_at - timedelta(hours=8)),
            }
        ]
        base_post_id = None
        for idx, profile_id in enumerate(actors[:12]):
            account = self.rng.choice(accounts_by_profile[profile_id])
            post_id = rand_id("post")
            if idx == 0:
                base_post_id = post_id
            posts.append(
                {
                    "post_id": post_id,
                    "profile_id": profile_id,
                    "account_id": account["account_id"],
                    "platform": account["platform"],
                    "content": variants[0] if idx == 0 else self.rng.choice(variants),
                    "timestamp": dt_to_iso(incident_at - timedelta(minutes=self.rng.randint(2, 70))),
                    "city": case_config["city"],
                    "province": case_config["province"],
                    "latitude": meeting_point["latitude"],
                    "longitude": meeting_point["longitude"],
                    "content_type": "text",
                    "engagement": {
                        "likes": self.rng.randint(5, 220),
                        "comments": self.rng.randint(0, 44),
                        "shares": self.rng.randint(0, 90),
                    },
                    "hashtags": ["#supplychain", "#update", "#situasi"],
                    "keywords": ["disrupsi", "rantai_pasok", "sinkron"],
                    "mention_refs": [central] if idx > 0 and self.rng.random() < 0.45 else [],
                    "reply_to_post_id": None,
                    "repost_of_post_id": base_post_id if idx > 0 and self.rng.random() < 0.55 else None,
                    "source_type": "coordinated" if idx > 0 else "organic_seed",
                    "scenario_refs": [case_id],
                }
            )
        for cluster_idx, phrase in enumerate(variants[:3]):
            message_clusters.append(
                {
                    "message_cluster_id": rand_id("msg"),
                    "case_id": case_id,
                    "canonical_phrase": phrase,
                    "profile_ids": actors[cluster_idx * 3 : cluster_idx * 3 + 4],
                    "post_count": self.rng.randint(4, 10),
                    "copy_similarity": round(self.rng.uniform(0.74, 0.96), 2),
                }
            )

        locations, meeting_network = self._append_case_checkins(actors[:5], meeting_point, incident_at, case_id)
        network = meeting_network
        for profile_id in actors[1:10]:
            network.append(
                {
                    "edge_id": rand_id("edge"),
                    "source_profile_id": central,
                    "target_profile_id": profile_id,
                    "edge_type": "message_amplification",
                    "weight": round(self.rng.uniform(0.61, 0.96), 2),
                    "case_id": case_id,
                }
            )

        crawling = []
        for _ in range(260):
            crawling.append(
                {
                    "data_point_id": rand_id("crawl"),
                    "case_id": case_id,
                    "source_type": self.rng.choice(["social_media", "forum", "news_comment", "community_note"]),
                    "platform": self.rng.choice(["twitter", "instagram", "forum", "tiktok"]),
                    "profile_ref": self.rng.choice(actors) if self.rng.random() < 0.65 else None,
                    "content": self.rng.choice(
                        [
                            "Sekelompok akun baru membagikan narasi yang sangat mirip.",
                            "Posting serempak muncul dalam rentang menit yang sempit.",
                            "Ada akun yang hanya aktif untuk satu topik lalu diam lagi.",
                            "Sebagian posting bisa dianggap opini biasa, tidak semua terkoordinasi.",
                            "Komentar forum menyebut pola copy-paste dan akun yang baru dibuat.",
                        ]
                    ),
                    "timestamp": dt_to_iso(incident_at - timedelta(hours=self.rng.randint(0, 24), minutes=self.rng.randint(0, 59))),
                    "city": case_config["city"],
                    "province": case_config["province"],
                    "latitude": meeting_point["latitude"],
                    "longitude": meeting_point["longitude"],
                    "signal_tags": self.rng.sample(["copy_paste", "new_account", "narrative", "sync", "noise"], k=2),
                    "reliability": round(self.rng.uniform(0.21, 0.86), 2),
                }
            )

        entities = [
            {"case_id": case_id, "entity_type": "keyword", "value": "disrupsi supply chain", "count": 49},
            {"case_id": case_id, "entity_type": "keyword", "value": "copy-paste wording", "count": 26},
            {"case_id": case_id, "entity_type": "account_cluster", "value": "12 akun sinkron", "count": 1},
        ]
        alerts = [
            {
                "alert_id": rand_id("alert"),
                "case_id": case_id,
                "severity": "high",
                "signal_type": "synchronized_posting",
                "description": "Terdapat klaster akun dengan pola posting hampir serentak dan wording serupa.",
                "confidence": 0.84,
            },
            {
                "alert_id": rand_id("alert"),
                "case_id": case_id,
                "severity": "medium",
                "signal_type": "bridge_overlap",
                "description": "Sebagian akun juga muncul dalam sinyal funding atau warehouse fire.",
                "confidence": 0.72,
            },
        ]
        risk_score = {
            "case_id": case_id,
            "risk_label": "high",
            "risk_score": 74,
            "organic_discourse_probability": 0.49,
            "coordinated_propagation_probability": 0.51,
            "drivers": ["copy_paste", "timing_sync", "bridge_overlap"],
            "disclaimer": "Penilaian ini indikatif dan bukan atribusi final.",
        }
        report = {
            "report_id": rand_id("rpt"),
            "case_id": case_id,
            "title": case_config["title"],
            "summary": "Narasi beredar melalui akun pusat dan akun amplifikasi dengan jeda waktu pendek, termasuk akun yang juga muncul di kasus lain.",
            "findings": [
                "Pola posting serempak menguat pada window kurang dari satu jam.",
                "Message clusters menunjukkan kemiripan frasa yang tinggi.",
                "Bridge account memperluas korelasi lintas kasus.",
            ],
            "analysis": "Sinyal konsisten dengan koordinasi narasi, namun masih bersifat indikatif.",
            "recommendations": [
                "Kelompokkan akun berdasarkan copy similarity dan waktu posting.",
                "Bandingkan overlap dengan edge transfer serta meeting point.",
                "Pisahkan akun baru dari akun lama untuk menguji pola bootstrap.",
            ],
            "generated_at": now_iso(),
            "disclaimer": "Laporan ini bersifat indikatif untuk kebutuhan analisis internal.",
        }
        case_links = [
            {"case_id": case_id, "profile_id": profile_id, "role": "amplifier" if profile_id != central else "seed_account", "signal": "propaganda_signal"}
            for profile_id in actors[:12]
        ]
        case = {
            "case_id": case_id,
            "case_type": "propaganda",
            "title": case_config["title"],
            "city": case_config["city"],
            "province": case_config["province"],
            "incident_at": dt_to_iso(incident_at),
            "meeting_point_id": meeting_point["meeting_point_id"],
            "actor_count": len(actors[:12]),
            "status": "monitoring",
        }
        return {
            "case": case,
            "posts": posts,
            "locations": locations,
            "network": network,
            "crawling": crawling,
            "entities": entities,
            "alerts": alerts,
            "risk_score": risk_score,
            "report": report,
            "campaigns": campaigns,
            "message_clusters": message_clusters,
            "case_links": case_links,
        }

    def _build_warehouse_crawling(self, case_id: str, case_config: dict, actors: list[str]) -> list[dict]:
        incident_at = case_config["incident_at"]
        content_pool = [
            ("social_media", "twitter", "Baru aja denger ledakan sebelum kebakaran."),
            ("social_media", "instagram", "Video api gede, orang-orang panik di lokasi."),
            ("social_media", "tiktok", "Asap hitam tebal kelihatan dari arah gudang."),
            ("forum", "forum", "Ini bukan kebakaran biasa, ada bau bahan kimia."),
            ("forum", "forum", "Katanya sempat ada ancaman sebelumnya."),
            ("news", "portal", "Gudang terbakar, dugaan awal korsleting listrik."),
            ("news", "portal", "Saksi menyebut ada ledakan sebelum api membesar."),
            ("sensor", "weather", "Cuaca normal, tidak ada petir di area sekitar."),
            ("cctv", "cctv", "Terlihat motor keluar beberapa menit sebelum api besar."),
        ]
        crawling = []
        for idx in range(520):
            source_type, platform, seed_content = self.rng.choice(content_pool)
            noisy_variant = seed_content
            if idx % 11 == 0:
                noisy_variant = "Info masih simpang siur, bisa jadi cuma korsleting biasa."
            elif idx % 13 == 0:
                noisy_variant = "Posting ini copy-paste dari akun lain, konteks belum jelas."
            crawling.append(
                {
                    "data_point_id": rand_id("crawl"),
                    "case_id": case_id,
                    "source_type": source_type,
                    "platform": platform,
                    "profile_ref": self.rng.choice(actors) if self.rng.random() < 0.48 else None,
                    "content": noisy_variant,
                    "timestamp": dt_to_iso(incident_at + timedelta(minutes=self.rng.randint(-150, 600))),
                    "city": case_config["city"],
                    "province": case_config["province"],
                    "latitude": rounded(-6.24 + self.rng.uniform(-0.05, 0.05)),
                    "longitude": rounded(107.0 + self.rng.uniform(-0.07, 0.07)),
                    "signal_tags": self.rng.sample(["ledakan", "api", "bau_kimia", "motor", "noise", "korsleting"], k=2),
                    "reliability": round(self.rng.uniform(0.18, 0.91), 2),
                }
            )
        return crawling

    def _reset_case_outputs(self, bundle: Bundle) -> None:
        bundle.cases = []
        bundle.transactions = []
        bundle.funding_alerts = []
        bundle.campaigns = []
        bundle.message_clusters = []
        bundle.crawling = []
        bundle.entities = []
        bundle.alerts = []
        bundle.risk_scores = []
        bundle.reports = []
        bundle.posts = [item for item in bundle.posts if not item.get("scenario_refs")]
        bundle.locations = [item for item in bundle.locations if not item.get("case_id")]
        bundle.network = [item for item in bundle.network if not item.get("case_id")]
        for profile in bundle.profiles:
            profile["case_links"] = []
            profile["risk_tags"] = []

    def _refresh_profile_extractions(self, bundle: Bundle) -> None:
        contacts_by_profile = {item["profile_id"]: item for item in bundle.contacts}
        preferences_by_profile = {item["profile_id"]: item for item in bundle.preferences}
        accounts_by_profile: dict[str, list] = {}
        photos_by_profile: dict[str, list] = {}
        posts_by_profile: dict[str, list] = {}
        for item in bundle.accounts:
            accounts_by_profile.setdefault(item["profile_id"], []).append(item)
        for item in bundle.photos:
            photos_by_profile.setdefault(item["profile_id"], []).append(item)
        for item in bundle.posts:
            posts_by_profile.setdefault(item["profile_id"], []).append(item)

        for profile in bundle.profiles:
            profile["extracted_profile"] = self._build_extracted_profile(
                profile=profile,
                contacts=contacts_by_profile[profile["profile_id"]],
                preferences=preferences_by_profile[profile["profile_id"]],
                accounts=accounts_by_profile.get(profile["profile_id"], []),
                friends=bundle.friends,
                photos=photos_by_profile.get(profile["profile_id"], []),
                posts=sorted(posts_by_profile.get(profile["profile_id"], []), key=lambda item: item["timestamp"], reverse=True),
                locations=bundle.locations,
            )


def build_profiles_dataset(count: int, out_dir: str, seed: int = 42, with_images: bool = False) -> Bundle:
    generator = SyntheticDatasetGenerator(seed=seed)
    return generator.build_profiles_bundle(count=count, out_dir=out_dir, with_images=with_images)


def build_case_dataset(out_dir: str, seed: int = 42, case_names: list[str] | None = None) -> Bundle:
    generator = SyntheticDatasetGenerator(seed=seed)
    bundle = generator.load_bundle(out_dir)
    if not bundle.profiles:
        raise ValueError("profiles.json tidak ditemukan atau kosong. Jalankan generate_profiles.py dulu.")
    return generator.augment_bundle_with_cases(bundle=bundle, case_names=case_names)


def build_full_dataset(count: int, out_dir: str, seed: int = 42, with_images: bool = False, case_names: list[str] | None = None) -> Bundle:
    generator = SyntheticDatasetGenerator(seed=seed)
    bundle = generator.build_profiles_bundle(count=count, out_dir=out_dir, with_images=with_images)
    return generator.augment_bundle_with_cases(bundle=bundle, case_names=case_names)
