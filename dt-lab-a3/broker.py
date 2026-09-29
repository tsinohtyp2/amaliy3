# broker.py — RabbitMQ bilan ishlash uchun umumiy qism.
# api.py ham, isteʼmolchilar ham shu fayldan foydalanadi.
import json
import os
import threading
import pika

BROKER = os.environ.get("BROKER", "localhost")
EXCHANGE = "hodisalar"          # topic turidagi almashtirgich
DLX = "dlx"                     # oʻlik xabarlar almashtirgichi (fanout)
DLQ = "dlq"                     # oʻlik xabarlar navbati

# Har bir soʻrovda yangi ulanish ochish — sodda, lekin sekin.
# 1 ga teng boʻlsa, api.py shu usulga oʻtadi (qoʻllanmadagi tajriba uchun).
HAR_SAFAR_ULAN = os.environ.get("HAR_SAFAR_ULAN", "0") == "1"


def ulanish() -> pika.BlockingConnection:
    """Brokerga yangi ulanish ochadi."""
    return pika.BlockingConnection(
        pika.ConnectionParameters(
            host=BROKER,
            heartbeat=60,
            blocked_connection_timeout=10,
            connection_attempts=3,
            retry_delay=2,
        )
    )


def sxemani_yarat(kanal) -> None:
    """Almashtirgich va oʻlik xabarlar navbatini eʼlon qiladi.

    Eʼlon qilish idempotent: bir necha marta chaqirilsa ham xato boʻlmaydi.
    """
    kanal.exchange_declare(exchange=EXCHANGE, exchange_type="topic", durable=True)
    kanal.exchange_declare(exchange=DLX, exchange_type="fanout", durable=True)
    kanal.queue_declare(queue=DLQ, durable=True)
    kanal.queue_bind(queue=DLQ, exchange=DLX)


class Nashriyotchi:
    """Doimiy ulanish orqali hodisa yuboradi.

    Nima uchun qulf kerak: uvicorn sinxron funksiyalarni bir necha oqimda
    bajaradi, pika ning BlockingConnection obyekti esa oqim-xavfsiz emas.
    Qulfsiz ikkita oqim bitta kanalga bir vaqtda yozsa, ulanish buziladi.
    """

    def __init__(self) -> None:
        self._qulf = threading.Lock()
        self._ulanish = None
        self._kanal = None

    def _kanal_ol(self):
        if self._ulanish is None or self._ulanish.is_closed:
            self._ulanish = ulanish()
            self._kanal = self._ulanish.channel()
            sxemani_yarat(self._kanal)
        return self._kanal

    def yubor(self, yol: str, malumot: dict) -> None:
        """Hodisani yuboradi. Broker ishlamasa, istisno koʻtaradi."""
        tana = json.dumps(malumot, ensure_ascii=False).encode()
        xos = pika.BasicProperties(
            delivery_mode=2,                 # xabar diskka yoziladi
            content_type="application/json",
            message_id=str(malumot.get("id", "")),
        )
        with self._qulf:
            if HAR_SAFAR_ULAN:
                # Har bir hodisa uchun alohida ulanish — sekin usul
                ul = ulanish()
                try:
                    kn = ul.channel()
                    sxemani_yarat(kn)
                    kn.basic_publish(EXCHANGE, yol, tana, xos)
                finally:
                    ul.close()
                return
            try:
                self._kanal_ol().basic_publish(EXCHANGE, yol, tana, xos)
            except (pika.exceptions.AMQPError, OSError):
                # Ulanish uzilgan boʻlishi mumkin — bir marta qayta urinamiz
                self._ulanish = None
                self._kanal_ol().basic_publish(EXCHANGE, yol, tana, xos)

    def yop(self) -> None:
        with self._qulf:
            if self._ulanish is not None and self._ulanish.is_open:
                self._ulanish.close()
            self._ulanish = None
            self._kanal = None
