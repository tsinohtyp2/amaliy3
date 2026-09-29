# consumer.py — hodisalarni qabul qiluvchi isteʼmolchi.
# Bitta fayl, ikki xizmat: navbat nomi muhit oʻzgaruvchisidan olinadi.
#   NAVBAT=tolov         python consumer.py
#   NAVBAT=bildirishnoma python consumer.py
import json
import os
import signal
import socket
import sys
import time
from datetime import datetime

import pika

from broker import DLX, EXCHANGE, sxemani_yarat, ulanish

NAVBAT = os.environ.get("NAVBAT", "tolov")
# Nusxa belgisi: bir necha nusxa ishlaganda kim nima qilganini ajratish uchun.
# Docker Compose da har bir nusxaning xost nomi boshqacha boʻladi.
NUSXA = os.environ.get("NUSXA", socket.gethostname()[:8])
YOL = os.environ.get("YOL", "buyurtma.*")           # qaysi hodisalarga obuna
ISH_VAQTI = float(os.environ.get("ISH_VAQTI_MS", "500")) / 1000

QAYTA_ISHLANGAN: set[str] = set()                    # deduplikatsiya uchun
SANOQ = {"qabul": 0, "takror": 0, "dlq": 0}


def chiqar(*matn) -> None:
    vaqt = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"[{vaqt}] [{NAVBAT}/{NUSXA}]", *matn, flush=True)


def qayta_ishla(kanal, metod, xos, tana: bytes) -> None:
    # 1) Xabarni oʻqib boʻlmasa — bu zaharli xabar (poison message).
    #    Qayta navbatga qoʻyish foydasiz: u yana buziq boʻladi va cheksiz aylanadi.
    try:
        h = json.loads(tana)
        hid = h["id"]
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        SANOQ["dlq"] += 1
        chiqar(f"ZAHARLI XABAR ({e.__class__.__name__}) -> DLQ:", tana[:60])
        kanal.basic_nack(metod.delivery_tag, requeue=False)   # DLX orqali DLQ ga
        return

    # 2) Deduplikatsiya: at-least-once yetkazishda bir xabar ikki marta kelishi mumkin
    if hid in QAYTA_ISHLANGAN:
        SANOQ["takror"] += 1
        chiqar("takroriy xabar, oʻtkazib yuborildi:", hid[:8])
        kanal.basic_ack(metod.delivery_tag)
        return

    # 3) Asosiy ish
    try:
        chiqar(f"qayta ishlanmoqda: {hid[:8]} | {metod.routing_key} | summa={h.get('summa')}")
        if h.get("buzuq"):                    # sinov uchun: atayin xatolik
            raise ValueError("maʼlumot mantiqan buzuq")
        time.sleep(ISH_VAQTI)                 # ish imitatsiyasi
        QAYTA_ISHLANGAN.add(hid)
        SANOQ["qabul"] += 1
        # Tasdiq ish tugagandan keyin yuboriladi — at-least-once semantikasi.
        # Agar isteʼmolchi shu satrga yetmay qulasa, broker xabarni boshqasiga beradi.
        kanal.basic_ack(metod.delivery_tag)
    except Exception as e:
        SANOQ["dlq"] += 1
        chiqar(f"XATO ({e}) -> DLQ:", hid[:8])
        kanal.basic_nack(metod.delivery_tag, requeue=False)


def main() -> None:
    ul = ulanish()
    kn = ul.channel()
    sxemani_yarat(kn)

    # Navbat oʻlik xabarlar almashtirgichiga bogʻlanadi: nack qilingan xabar DLQ ga tushadi
    kn.queue_declare(queue=NAVBAT, durable=True,
                     arguments={"x-dead-letter-exchange": DLX})
    kn.queue_bind(queue=NAVBAT, exchange=EXCHANGE, routing_key=YOL)

    # Bir vaqtda faqat bitta xabar beriladi — nusxalar orasida adolatli taqsimlash
    kn.basic_qos(prefetch_count=1)
    kn.basic_consume(queue=NAVBAT, on_message_callback=qayta_ishla)

    def toxtat(*_):
        chiqar(f"toʻxtatilmoqda. Hisob: {SANOQ}")
        kn.stop_consuming()
        ul.close()
        sys.exit(0)

    signal.signal(signal.SIGTERM, toxtat)
    signal.signal(signal.SIGINT, toxtat)

    chiqar(f"kutilmoqda... (navbat={NAVBAT}, yoʻl={YOL}, ish={ISH_VAQTI * 1000:.0f} ms)")
    kn.start_consuming()


if __name__ == "__main__":
    main()
