#!/usr/bin/env bash
# sinov.sh — barcha holat kodlarini ketma-ket sinaydi.
# Ishlatilishi:  bash sinov.sh
API=${API:-http://localhost:8000}

TANA=$(mktemp)
trap 'rm -f "$TANA"' EXIT

# Xizmat ishlayotganini oldindan tekshiramiz. Aks holda barcha soʻrovlar 000
# qaytaradi va sabab noaniq boʻlib qoladi.
if ! curl -s -m 5 -o /dev/null "$API/salomat"; then
  cat >&2 <<XABAR
XATO: REST xizmatiga ulanib boʻlmadi ($API)

Xizmat hali koʻtarilmagan boʻlishi mumkin. Quyidagilarni ketma-ket bajaring:

  docker compose up -d --build     # xizmatlarni koʻtarish
  docker compose ps                # toʻrttasi ham running boʻlsinmi
  docker compose logs api          # API nima deyapti

Broker tayyor boʻlgunga qadar API kutadi — birinchi marta 20 soniyagacha ketadi.
XABAR
  exit 1
fi

kod() { curl -s -o "$TANA" -w "%{http_code}" "$@"; }

# Javob tanasidan maydon oladi. Javob JSON boʻlmasa, boʻsh satr qaytaradi.
maydon() {
  python3 -c "
import json, sys
try:
    print(json.load(open('$TANA')).get('$1', ''))
except Exception:
    print('')
" 2>/dev/null
}

# Oʻzbekcha apostrof koʻp baytli boʻlgani uchun printf %-46s notoʻgʻri tekislaydi.
# Shuning uchun boʻsh joy belgilar soni boʻyicha hisoblanadi.
kur() { local n=$(( 46 - ${#1} )); (( n < 1 )) && n=1; printf '%s%*s-> %s\n' "$1" "$n" "" "$2"; }

echo "=== Muvaffaqiyatli holatlar ==================================="
K=$(kod -X POST $API/buyurtmalar -H 'Content-Type: application/json' \
      -d '{"talaba_id":"2001","summa":150000}')
ID=$(maydon id)
kur "POST /buyurtmalar (yangi)" "$K  (201 kutilgan)"

if [ -z "$ID" ]; then
  echo >&2
  echo "XATO: buyurtma yaratilmadi, keyingi sinovlarni bajarib boʻlmaydi." >&2
  echo "Javob tanasi:" >&2
  cat "$TANA" >&2; echo >&2
  [ "$K" = "503" ] && echo "503 — broker ishlamayapti: docker compose ps bilan tekshiring." >&2
  exit 1
fi

K=$(kod $API/buyurtmalar/$ID);            kur "GET /buyurtmalar/{id}" "$K  (200 kutilgan)"
K=$(kod "$API/buyurtmalar?sahifa=1&limit=5"); kur "GET /buyurtmalar?sahifa=1&limit=5" "$K  (200 kutilgan)"
K=$(kod -X PATCH $API/buyurtmalar/$ID -H 'Content-Type: application/json' \
      -d '{"holat":"tolandi"}');          kur "PATCH holat: yaratildi -> tolandi" "$K  (200 kutilgan)"

echo
echo "=== Idempotentlik ============================================="
# Kalit har safar yangi boʻlishi kerak: API avvalgi ishdagi kalitni eslab qoladi
KALIT="k-$(date +%s%N)"
K=$(kod -X POST $API/buyurtmalar -H "Idempotency-Key: $KALIT" \
      -H 'Content-Type: application/json' -d '{"talaba_id":"2002","summa":300000}')
kur "POST idempotentlik kaliti (1-marta)" "$K  (201 kutilgan)"
K=$(kod -X POST $API/buyurtmalar -H "Idempotency-Key: $KALIT" \
      -H 'Content-Type: application/json' -d '{"talaba_id":"2002","summa":300000}')
kur "POST ayni kalit (2-marta, ayni tana)" "$K  (200 kutilgan)"
K=$(kod -X POST $API/buyurtmalar -H "Idempotency-Key: $KALIT" \
      -H 'Content-Type: application/json' -d '{"talaba_id":"9999","summa":1}')
kur "POST ayni kalit (boshqa tana)" "$K  (409 kutilgan)"

echo
echo "=== Xatolik holatlari ========================================="
K=$(kod $API/buyurtmalar/yoq-bunday-id);  kur "GET mavjud boʻlmagan id" "$K  (404 kutilgan)"
K=$(kod -X POST $API/buyurtmalar -H 'Content-Type: application/json' \
      -d '{"talaba_id":"3001","summa":-5}'); kur "POST manfiy summa" "$K  (400 kutilgan)"
K=$(kod -X POST $API/buyurtmalar -H 'Content-Type: application/json' \
      -d '{"summa":100}');                kur "POST talaba_id yoʻq" "$K  (400 kutilgan)"
K=$(kod -X PATCH $API/buyurtmalar/$ID -H 'Content-Type: application/json' \
      -d '{"holat":"yaratildi"}');        kur "PATCH tolandi -> yaratildi (orqaga)" "$K  (409 kutilgan)"
K=$(kod -X DELETE $API/buyurtmalar/$ID);  kur "DELETE mavjud buyurtma" "$K  (204 kutilgan)"
K=$(kod -X DELETE $API/buyurtmalar/$ID);  kur "DELETE oʻchirilgan buyurtma" "$K  (404 kutilgan)"

echo
echo "=== Problem Details namunasi =================================="
curl -s -X PATCH $API/buyurtmalar/yoq -H 'Content-Type: application/json' \
     -d '{"holat":"tolandi"}' | python3 -m json.tool
