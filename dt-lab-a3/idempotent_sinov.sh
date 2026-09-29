#!/usr/bin/env bash
# idempotent_sinov.sh — bir xil kalit bilan 5 marta soʻrov yuboradi (topshiriq 3).
API=${API:-http://localhost:8000}

TANA=$(mktemp)
trap 'rm -f "$TANA"' EXIT

if ! curl -s -m 5 -o /dev/null "$API/salomat"; then
  cat >&2 <<XABAR
XATO: REST xizmatiga ulanib boʻlmadi ($API)

  docker compose up -d --build     # xizmatlarni koʻtarish
  docker compose ps                # toʻrttasi ham running boʻlsinmi
XABAR
  exit 1
fi

soni() {
  curl -s "$API/buyurtmalar" | python3 -c "
import json, sys
try:
    print(json.load(sys.stdin).get('jami', '?'))
except Exception:
    print('?')
" 2>/dev/null
}

AVVAL=$(soni)
KALIT="k5-$(date +%s%N)"
echo "Kalit: $KALIT"
for i in 1 2 3 4 5; do
  KOD=$(curl -s -o "$TANA" -w "%{http_code}" -X POST $API/buyurtmalar \
        -H "Idempotency-Key: $KALIT" -H 'Content-Type: application/json' \
        -d '{"talaba_id":"5001","summa":450000}')
  ID=$(python3 -c "
import json
try:
    print(json.load(open('$TANA')).get('id', '—')[:8])
except Exception:
    print('—')
" 2>/dev/null)
  echo "  $i-soʻrov -> HTTP $KOD, id=$ID"
done
KEYIN=$(soni)
echo
if [ "$AVVAL" = "?" ] || [ "$KEYIN" = "?" ]; then
  echo "Yozuvlar sonini oʻqib boʻlmadi — API javobi kutilganday emas."
else
  echo "Bazadagi yozuvlar: avval=$AVVAL, keyin=$KEYIN, yangi yozuv=$((KEYIN-AVVAL))"
fi
echo "Kutilgan natija: 5 ta soʻrov, 1 ta yozuv."
