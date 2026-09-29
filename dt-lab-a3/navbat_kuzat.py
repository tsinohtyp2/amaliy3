# navbat_kuzat.py — navbat uzunligini kuzatadi.
#
# Ikki oʻlchov usuli bor:
#   1) Boshqaruv API (sukut boʻyicha) — veb-panel koʻrsatadigan qiymat.
#      Statistika ~5 soniyalik siklda yigʻilgani uchun bu qiymat
#      haqiqiy holatdan taxminan 6–8 soniya orqada qoladi.
#   2) --aniq — brokerning oʻzidan rabbitmqctl orqali. Kechikishsiz.
#
# Ishlatilishi:
#   python navbat_kuzat.py --bir-marta          holatni bir marta koʻrsatish
#   python navbat_kuzat.py 60                   60 soniya kuzatish, CSV yozish
#   python navbat_kuzat.py 60 --aniq            aniq qiymatlar bilan
import os
import subprocess
import sys
import time

import httpx

BROKER = os.environ.get("BROKER", "localhost")
PANEL = f"http://{BROKER}:15672/api/queues/%2F"
AUTH = ("guest", "guest")
CSV = "natijalar/navbat.csv"
ANIQ = "--aniq" in sys.argv


def holat_api() -> dict[str, int]:
    with httpx.Client(auth=AUTH, timeout=5) as m:
        j = m.get(PANEL).json()
    return {q["name"]: q.get("messages", 0) for q in j}


def holat_ctl() -> dict[str, int]:
    """Brokerdagi rabbitmqctl orqali — kechikishsiz, lekin Docker talab qiladi."""
    buyruq = ["docker", "compose", "exec", "-T", "broker",
              "rabbitmqctl", "list_queues", "name", "messages", "--quiet"]
    if not os.path.exists("/.dockerenv") and os.environ.get("BROKER", "localhost") == "localhost":
        # Broker shu mashinada oʻrnatilgan boʻlsa
        mahalliy = subprocess.run(["which", "rabbitmqctl"], capture_output=True)
        if mahalliy.returncode == 0:
            buyruq = ["sudo", "rabbitmqctl", "list_queues", "name", "messages", "--quiet"]
    n = subprocess.run(buyruq, capture_output=True, text=True)
    if n.returncode != 0:
        raise RuntimeError(n.stderr.strip()[:200] or "rabbitmqctl ishlamadi")
    natija = {}
    for qator in n.stdout.strip().splitlines():
        qism = qator.split("\t")
        if len(qism) == 2 and qism[1].isdigit():
            natija[qism[0]] = int(qism[1])
    return natija


def holat() -> dict[str, int]:
    try:
        return holat_ctl() if ANIQ else holat_api()
    except Exception as e:
        raise SystemExit(
            f"XATO: broker maʼlumotini oʻqib boʻlmadi ({e.__class__.__name__})\n\n"
            "  docker compose up -d --build     # xizmatlarni koʻtarish\n"
            "  docker compose ps                # broker running va healthy boʻlsinmi\n\n"
            "Boshqaruv paneli 15672-portda, login guest / guest."
        )


def main() -> None:
    usul = "rabbitmqctl (aniq)" if ANIQ else "boshqaruv API (~7 s kechikish bilan)"

    if "--bir-marta" in sys.argv:
        print(f"Oʻlchov usuli: {usul}")
        for nom, soni in sorted(holat().items()):
            print(f"  {nom:<16} {soni:>6} ta xabar")
        return

    raqamlar = [a for a in sys.argv[1:] if a.isdigit()]
    davomiylik = int(raqamlar[0]) if raqamlar else 60
    os.makedirs("natijalar", exist_ok=True)
    print(f"Oʻlchov usuli: {usul}\n")

    t0 = time.time()
    with open(CSV, "w", encoding="utf-8") as f:
        navbatlar = sorted(holat())
        f.write("soniya," + ",".join(navbatlar) + "\n")
        print(f"{'vaqt':>6} | " + " | ".join(f"{n:>14}" for n in navbatlar))
        while time.time() - t0 < davomiylik:
            h = holat()
            s = time.time() - t0
            f.write(f"{s:.1f}," + ",".join(str(h.get(n, 0)) for n in navbatlar) + "\n")
            f.flush()
            print(f"{s:6.1f} | " + " | ".join(f"{h.get(n, 0):>14}" for n in navbatlar))
            time.sleep(1)
    print(f"\nNatija saqlandi: {CSV}")


if __name__ == "__main__":
    main()
