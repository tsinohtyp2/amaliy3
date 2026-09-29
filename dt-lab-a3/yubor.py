# yubor.py — API ga bir necha buyurtma yuboradi va kechikishni oʻlchaydi.
# Ishlatilishi:  python yubor.py 200        (200 ta soʻrov)
import sys
import time

import httpx

API = "http://localhost:8000"
SONI = int(sys.argv[1]) if len(sys.argv) > 1 else 10


def foiz(v: list[float], p: float) -> float:
    v = sorted(v)
    return v[min(len(v) - 1, int(len(v) * p))]


def main() -> None:
    vaqtlar, xato = [], 0
    try:
        httpx.get(f"{API}/salomat", timeout=5)
    except httpx.HTTPError:
        raise SystemExit(
            f"XATO: REST xizmatiga ulanib boʻlmadi ({API})\n\n"
            "  docker compose up -d --build     # xizmatlarni koʻtarish\n"
            "  docker compose ps                # toʻrttasi ham running boʻlsinmi"
        )
    with httpx.Client(timeout=10) as m:
        for i in range(SONI):
            t0 = time.perf_counter()
            j = m.post(f"{API}/buyurtmalar",
                       json={"talaba_id": f"{1000 + i % 50}", "summa": 100000 + i})
            vaqtlar.append((time.perf_counter() - t0) * 1000)
            if j.status_code >= 400:
                xato += 1
    print(f"{SONI} ta soʻrov yuborildi, xato: {xato}")
    print(f"p50={foiz(vaqtlar, .5):.1f} ms   p95={foiz(vaqtlar, .95):.1f} ms   "
          f"jami={sum(vaqtlar) / 1000:.2f} s")


if __name__ == "__main__":
    main()
