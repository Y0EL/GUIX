from __future__ import annotations

import json
from typing import List, Optional

from kafka import KafkaConsumer, KafkaProducer
from redis import Redis

from orchestration.config import PengaturanRuntime


class TransportRuntime:
    """Lapisan transport nyata untuk Kafka dan Redis Streams."""

    def __init__(self, pengaturan: PengaturanRuntime):
        self.pengaturan = pengaturan
        self.redis = Redis.from_url(pengaturan.url_redis, decode_responses=True)
        self._producer: Optional[KafkaProducer] = None

    @property
    def producer(self) -> KafkaProducer:
        if self._producer is None:
            self._producer = KafkaProducer(
                bootstrap_servers=self.pengaturan.kafka_bootstrap_servers.split(","),
                value_serializer=lambda nilai: json.dumps(nilai, ensure_ascii=True).encode("utf-8"),
                linger_ms=20,
                retries=5,
            )
        return self._producer

    def buat_konsumer_kafka(self, topic: str, group_id: str) -> KafkaConsumer:
        return KafkaConsumer(
            topic,
            bootstrap_servers=self.pengaturan.kafka_bootstrap_servers.split(","),
            group_id=group_id,
            enable_auto_commit=False,
            auto_offset_reset="earliest",
            value_deserializer=lambda nilai: json.loads(nilai.decode("utf-8")),
            max_poll_interval_ms=1800000,  # 30 menit
            session_timeout_ms=45000,      # 45 detik
            max_poll_records=1,
        )

    def terbitkan_kafka(self, topic: str, payload: dict) -> None:
        self.producer.send(topic, payload)
        self.producer.flush()

    def terbitkan_redis_stream(self, nama_stream: str, payload: dict) -> str:
        return self.redis.xadd(nama_stream, {"payload": json.dumps(payload, ensure_ascii=True)})

    def terbitkan_dead_letter(self, nama_stream_asal: str, payload: dict) -> str:
        nama_stream_dead_letter = f"{nama_stream_asal}_dead_letter"
        return self.terbitkan_redis_stream(nama_stream_dead_letter, payload)

    def pastikan_grup_stream(self, nama_stream: str, nama_grup: str) -> None:
        try:
            self.redis.xgroup_create(name=nama_stream, groupname=nama_grup, id="0", mkstream=True)
        except Exception as exc:
            if "BUSYGROUP" not in str(exc):
                raise

    def baca_stream_grup(
        self,
        nama_stream: str,
        nama_grup: str,
        nama_konsumen: str,
        count: int = 10,
        block_ms: int = 5000,
    ) -> List:
        return self.redis.xreadgroup(
            groupname=nama_grup,
            consumername=nama_konsumen,
            streams={nama_stream: ">"},
            count=count,
            block=block_ms,
        )

    def akui_stream(self, nama_stream: str, nama_grup: str, *message_ids: str) -> None:
        if message_ids:
            self.redis.xack(nama_stream, nama_grup, *message_ids)

    def tutup(self) -> None:
        if self._producer is not None:
            self._producer.close()
        self.redis.close()
