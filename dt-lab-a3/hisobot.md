# Amaliy mashgʻulot 3 — Hisobot

**Talaba:** ______________________  **Guruh:** __________  **Variant:** ____  **Sana:** __________

---

## 1. REST API ning resurs modeli va URI sxemasi

Resurs: ______________

| Metod va URI | Vazifasi | Muvaffaqiyatli kod | Xatolik kodlari |
|---|---|---|---|
| `POST /______` | | 201 | 400, 409 |
| `GET /______` | | 200 | — |
| `GET /______/{id}` | | 200 | 404 |
| `PATCH /______/{id}` | | 200 | 400, 404, 409 |
| `DELETE /______/{id}` | | 204 | 404 |

**Izoh:** _(nima uchun aynan shunday URI tanlandi; qaysi metod idempotent va nega)_

---

## 2. OpenAPI tavsifi

Swagger UI ekran nusxasi (`/docs`):

![swagger](natijalar/swagger.png)

`/openapi.json` dagi asosiy qism: ____________

---

## 3. Holat kodlari jadvali

`sinov.sh` natijasi asosida toʻldiring:

| Soʻrov | Kutilgan kod | Olingan kod | Izoh |
|---|---|---|---|
| POST yangi yozuv | 201 | | |
| GET mavjud yozuv | 200 | | |
| PATCH toʻgʻri oʻtish | 200 | | |
| DELETE mavjud yozuv | 204 | | |
| POST notoʻgʻri maʼlumot | 400 | | |
| GET mavjud boʻlmagan id | 404 | | |
| PATCH notoʻgʻri oʻtish | 409 | | |
| POST ayni kalit, boshqa tana | 409 | | |

---

## 4. Idempotentlik tajribasi

| Soʻrov raqami | HTTP kodi | Qaytgan `id` |
|---|---|---|
| 1 | | |
| 2 | | |
| 3 | | |
| 4 | | |
| 5 | | |

Bazadagi yozuvlar soni: avval ____ , keyin ____ , yangi yozuv ____ .

**Tahlil:** _(server kalitni qayerda va qancha muddat saqlashi kerak? Kalit boʻlmasa nima boʻlardi?)_

---

## 5. Broker konfiguratsiyasi

| Element | Nomi | Turi / parametri |
|---|---|---|
| Almashtirgich | | topic |
| 1-navbat | | `x-dead-letter-exchange` = |
| 2-navbat | | |
| Bogʻlanish kaliti | | |
| DLQ | | |

Isteʼmolchi kodining asosiy qismi va `basic_ack` qayerda chaqirilgani:

```python
# shu yerga joylang
```

---

## 6. Navbat uzunligi

`natijalar/navbat.csv` asosida grafik yoki jadval:

| Vaqt, s | Navbat uzunligi | Holat |
|---|---|---|
| 0 | | isteʼmolchi oʻchiq |
| 5 | | 200 ta xabar yuborildi |
| 20 | | isteʼmolchi yoqildi |
| 30 | | |
| 40 | | |

**Tahlil:** _(isteʼmolchi oʻchgan davrda xabarlar nima uchun yoʻqolmadi? Boʻshash tezligi nimaga bogʻliq?)_

---

## 7. Deduplikatsiya va DLQ

Zaharli xabar yuborilgandan keyingi log yozuvlari:

```
# shu yerga joylang
```

DLQ dagi xabarlar soni: ____

**Tahlil:** _(nega buzilgan xabarni qayta navbatga qoʻyish foydasiz? Ikkita isteʼmolchi boʻlsa DLQ ga nechta xabar tushadi va nega?)_

---

## 8. Isteʼmolchi nusxalari

| Nusxa | Qayta ishlangan xabarlar |
|---|---|
| 1 | |
| 2 | |
| 3 | |

**Tahlil:** _(taqsimlash nimaga bogʻliq? `prefetch_count` ni 50 ga oshirsangiz nima oʻzgaradi?)_

---

## 9. Broker oʻchgan holat

| Koʻrsatkich | Natija |
|---|---|
| Mijoz olgan HTTP kodi | |
| Javob kelgunga qadar oʻtgan vaqt | |
| Yozuv bazada qoldimi | |
| Hodisa yuborildimi | |

**Tahlil:** _(bu qanday nomuvofiqlik? Outbox naqshi uni qanday hal qiladi?)_

---

## 10. Xulosa

Kamida besh-yetti jumla:

- Sinxron (REST) va asinxron (navbat) aloqani qaysi holatda tanlaysiz?
- At-least-once semantikasi nimani kafolatlaydi va nimani kafolatlamaydi?
- Nima uchun exactly-once ni sof holda taʼminlab boʻlmaydi?
- Idempotentlik kaliti va isteʼmolchi deduplikatsiyasi — bir xil masalaning ikki tomonimi?

---

## 11. Nazorat savollariga javoblar

1. REST da resurs va amal qanday ifodalanadi? URI ni loyihalash qoidalari.
2. Xavfsiz va idempotent metodlarni ajrating. POST nima uchun idempotent emas?
3. Idempotentlik kaliti qanday ishlaydi? Uni server tomonida qanday saqlash kerak?
4. 201, 204, 409 va 429 holat kodlari qachon qaytariladi?
5. OpenAPI tavsifidan qanday foydalar olinadi?
6. Nuqta-nuqta va publish/subscribe modellarining farqi nimada?
7. At-least-once semantikasi qanday amalga oshiriladi? Ack qachon yuborilishi kerak?
8. Isteʼmolchi tomonidan deduplikatsiya nima uchun zarur?
9. Dead letter queue qanday muammoni yechadi? Poison message nima?
10. Outbox naqshi qanday nomuvofiqlikni oldini oladi?
11. Isteʼmolchi oʻchgan davrda xabarlar nima uchun yoʻqolmadi?
