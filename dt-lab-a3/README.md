# Amaliy mashgʻulot 3. REST API va xabar navbati orqali integratsiya

**Fan:** Taqsimlangan tizimlar · **Bogʻliq maʼruza:** M4–M5 · **Ajratilgan vaqt:** 4 soat · **Ball:** 3

Toʻliq nazariya, sxemalar va izohlar — `Amaliy_03_Qollanma.docx` faylida.

---

## 0. Ishni boshlash

1. Shu sahifada **Use this template** → **Create a new repository**. Nomi: `dt-a3-familiyangiz`, **Public**.
2. Oʻz repozitoriyingizda **Code** → **Codespaces** → **Create codespace on main**.
3. 3–5 daqiqa kuting. Terminal oxirida `---- tayyor ----` va versiyalar chiqadi.

Chiqmagan boʻlsa: `bash .devcontainer/setup.sh`

---

## 1. Infratuzilmani koʻtarish

```bash
docker compose up -d --build
docker compose ps
```

Toʻrtta xizmat koʻtariladi: `broker`, `api`, `tolov`, `bildirishnoma`.
Birinchi marta 2–4 daqiqa ketadi — obrazlar yuklab olinadi.

Davom etishdan oldin API javob berayotganini tekshiring:

```bash
curl -s localhost:8000/salomat
```

`{"holat":"ishlayapti","buyurtmalar":0}` chiqishi kerak. Chiqmasa, broker hali
tayyor emas — 20 soniya kutib qayta urinib koʻring yoki `docker compose logs api`
bilan sababini qarang.

RabbitMQ paneli: **PORTS** panelidagi 15672-portni oching (login `guest`, parol `guest`).
REST hujjati: 8000-port → `/docs`.

---

## 2. REST API ni sinash

```bash
curl -s localhost:8000/salomat
bash sinov.sh | tee natijalar/01-holat-kodlari.txt
```

`sinov.sh` 13 ta holatni ketma-ket tekshiradi: 200, 201, 204, 400, 404, 409.

---

## 3. Idempotentlik

```bash
bash idempotent_sinov.sh | tee natijalar/02-idempotentlik.txt
```

Bir xil kalit bilan 5 ta soʻrov → bazada 1 ta yozuv.

---

## 4. Pub/sub: bitta hodisa, ikki isteʼmolchi

```bash
curl -X POST localhost:8000/buyurtmalar \
     -H 'Content-Type: application/json' \
     -d '{"talaba_id":"1001","summa":250000}'

docker compose logs --tail 5 tolov bildirishnoma
```

Ikkala isteʼmolchi ham ayni bir hodisani oladi.

---

## 5. Dead letter queue

```bash
python buzuq_yubor.py
docker compose logs --tail 10 tolov
python navbat_kuzat.py --bir-marta
```

---

## 6. Navbat uzunligini kuzatish

Uch terminal kerak.

**1-terminal** — kuzatuvni yoqing:

```bash
python navbat_kuzat.py 60 --aniq | tee natijalar/03-navbat.txt
```

**2-terminal** — isteʼmolchilarni toʻxtatib, xabar yuboring:

```bash
docker compose stop tolov bildirishnoma
python yubor.py 200
```

30 soniyadan keyin qayta yoqing:

```bash
docker compose start tolov bildirishnoma
```

Navbat `natijalar/navbat.csv` fayliga ham yoziladi.

> **Diqqat:** boshqaruv panelidagi raqam haqiqiy holatdan ~7 soniya orqada qoladi.
> Aniq qiymat uchun `--aniq` bayrogʻini ishlating.

---

## 7. Isteʼmolchi nusxalarini koʻpaytirish

```bash
docker compose up -d --scale tolov=3
python yubor.py 30
docker compose logs tolov | grep -c "qayta ishlanmoqda"
```

Har bir nusxa taxminan teng ulush oladi — buni `prefetch_count=1` taʼminlaydi.

---

## 8. Broker oʻchganda nima boʻladi

```bash
docker compose stop broker
curl -i -X POST localhost:8000/buyurtmalar \
     -H 'Content-Type: application/json' \
     -d '{"talaba_id":"7001","summa":999000}'
```

503 qaytadi, lekin javobdagi `yaratilgan_id` boʻyicha yozuvni qidirib koʻring —
u bazada qolgan. Bu **dual-write** muammosi; outbox naqshi aynan shuni hal qiladi.

```bash
docker compose start broker
```

---

## Mustaqil topshiriq

Variantni oʻqituvchidan oling.

| Variant | Asosiy resurs | Hodisa nomi | Ikkinchi isteʼmolchi |
|---|---|---|---|
| 1 | Buyurtma | `buyurtma.yaratildi` | Ombor xizmati |
| 2 | Ariza | `ariza.qabul_qilindi` | Arxiv xizmati |
| 3 | Toʻlov | `tolov.tasdiqlandi` | Hisobot xizmati |
| 4 | Roʻyxatga olish | `talaba.royxatga_olindi` | Bildirishnoma xizmati |

1. REST API ga kamida toʻrtta manzil: roʻyxat (sahifalash bilan), bitta element, yaratish, yangilash.
2. Xatoliklarni Problem Details (`application/problem+json`) formatida qaytaring.
3. Idempotentlik kalitini toʻliq amalga oshiring va 5 ta soʻrov bilan sinang.
4. Ikkinchi isteʼmolchi qoʻshing va pub/sub ni koʻrsating.
5. DLQ ni sozlang va buzilgan xabar tushishini koʻrsating.
6. 200 ta xabar bilan navbat oʻsishini oʻlchang va grafik keltiring.
7. Isteʼmolchini uch nusxaga koʻpaytirib, taqsimlanishni koʻrsating.

---

## Topshirish

```bash
git add .
git commit -m "Amaliy 3 bajarildi"
git push
```

Soʻng **Stop Current Codespace** ni bosing.

---

## Tez-tez uchraydigan xatolar

| Xato | Sababi | Yechimi |
|---|---|---|
| `unknown flag: --builddocker` | Buyruq ikki marta yopishtirilgan | Buyruqni bir marta, qoʻlda yozing |
| Hamma joyda `-> 000` | Xizmatlar koʻtarilmagan | `docker compose ps` bilan tekshiring |
| `AMQPConnectionError` | Broker hali tayyor emas | 10 s kutib qayta urinish |
| `ModuleNotFoundError: fastapi` | Paketlar oʻrnatilmagan | `bash .devcontainer/setup.sh` |
| `port is already allocated` | Eski konteynerlar ishlayapti | `docker compose down` |
| Panelda raqam oʻzgarmayapti | Statistika ~7 s kechikadi | `--aniq` bayrogʻi |
| `sinov.sh` da 409 oʻrniga 200 | Kalit avvalgi ishdan qolgan | Skript kalitni oʻzi yangilaydi |
| Xabar DLQ ga tushmayapti | Navbat DLX siz yaratilgan | `docker compose down` soʻng qayta koʻtarish |
