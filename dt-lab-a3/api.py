# api.py — Buyurtmalar REST xizmati (FastAPI)
# Ishga tushirish:  uvicorn api:app --host 0.0.0.0 --port 8000
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Header, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from broker import Nashriyotchi

# --- Maʼlumotlar ombori (soddalik uchun xotirada) ---
BAZA: dict[str, dict] = {}
IDEMPOTENT: dict[str, dict] = {}        # kalit -> {"javob": ..., "barmoq": ...}

# Holatlar oʻtishi: qaysi holatdan qaysisiga oʻtish mumkin
OTISHLAR = {
    "yaratildi": {"tolandi", "bekor_qilindi"},
    "tolandi": {"yetkazildi", "bekor_qilindi"},
    "yetkazildi": set(),
    "bekor_qilindi": set(),
}

nashriyotchi = Nashriyotchi()


@asynccontextmanager
async def hayot(app: FastAPI):
    yield
    nashriyotchi.yop()


app = FastAPI(
    title="Buyurtmalar API",
    version="1.0.0",
    description="Taqsimlangan tizimlar, 3-amaliy mashgʻulot: REST va xabar navbati",
    lifespan=hayot,
)


# ---------- Problem Details (RFC 9457) ----------
def muammo(status: int, sarlavha: str, tafsilot: str, yol: str, **qoshimcha) -> JSONResponse:
    """Xatolikni application/problem+json koʻrinishida qaytaradi."""
    tana = {
        "type": f"https://buxdu.uz/xatolar/{sarlavha}",
        "title": sarlavha,
        "status": status,
        "detail": tafsilot,
        "instance": yol,
        **qoshimcha,
    }
    return JSONResponse(tana, status_code=status, media_type="application/problem+json")


@app.exception_handler(RequestValidationError)
async def tekshiruv_xatosi(sorov: Request, xato: RequestValidationError):
    """FastAPI sukut boʻyicha 422 qaytaradi; topshiriq 400 ni talab qiladi."""
    maydonlar = [
        {"maydon": ".".join(str(q) for q in x["loc"][1:]), "sabab": x["msg"]}
        for x in xato.errors()
    ]
    return muammo(400, "notogri-sorov", "Soʻrov tanasi talabga mos emas",
                  sorov.url.path, maydonlar=maydonlar)


# ---------- Modellar ----------
class Buyurtma(BaseModel):
    talaba_id: str = Field(min_length=1, max_length=32)
    summa: float = Field(gt=0, description="Musbat son boʻlishi shart")


class Yangilash(BaseModel):
    holat: str


# ---------- Manzillar ----------
@app.post("/buyurtmalar", status_code=201, summary="Yangi buyurtma yaratish")
def yarat(b: Buyurtma, sorov: Request, javob: Response,
          idempotency_key: str | None = Header(default=None)):
    barmoq = b.model_dump_json()          # soʻrov tanasining barmoq izi

    if idempotency_key:
        avvalgi = IDEMPOTENT.get(idempotency_key)
        if avvalgi is not None:
            if avvalgi["barmoq"] != barmoq:
                # Bir xil kalit, boshqa tana — bu mijoz xatosi
                return muammo(409, "kalit-band",
                              "Bu idempotentlik kaliti boshqa maʼlumot bilan ishlatilgan",
                              sorov.url.path)
            javob.status_code = 200        # takroriy soʻrov: yangi yozuv yaratilmaydi
            return avvalgi["javob"]

    bid = str(uuid.uuid4())
    yozuv = {"id": bid, "holat": "yaratildi", **b.model_dump()}
    BAZA[bid] = yozuv

    try:
        nashriyotchi.yubor("buyurtma.yaratildi", yozuv)
    except Exception as e:
        # Diqqat: yozuv bazaga allaqachon tushdi, hodisa esa yuborilmadi.
        # Aynan shu nomuvofiqlikni outbox naqshi hal qiladi (qoʻllanmaning 5.7-bosqichi).
        return muammo(503, "broker-ishlamayapti",
                      f"Hodisa yuborilmadi: {e.__class__.__name__}",
                      sorov.url.path, yaratilgan_id=bid)

    if idempotency_key:
        IDEMPOTENT[idempotency_key] = {"javob": yozuv, "barmoq": barmoq}
    javob.headers["Location"] = f"/buyurtmalar/{bid}"
    return yozuv


@app.get("/buyurtmalar", summary="Buyurtmalar roʻyxati")
def royxat(sahifa: int = 1, limit: int = 20):
    hammasi = list(BAZA.values())
    sahifa = max(1, sahifa)
    limit = min(max(1, limit), 100)
    b = (sahifa - 1) * limit
    return {"jami": len(hammasi), "sahifa": sahifa, "limit": limit,
            "elementlar": hammasi[b:b + limit]}


@app.get("/buyurtmalar/{bid}", summary="Bitta buyurtma")
def ol(bid: str, sorov: Request):
    if bid not in BAZA:
        return muammo(404, "topilmadi", f"{bid} identifikatorli buyurtma yoʻq",
                      sorov.url.path)
    return BAZA[bid]


@app.patch("/buyurtmalar/{bid}", summary="Buyurtma holatini oʻzgartirish")
def yangila(bid: str, y: Yangilash, sorov: Request):
    if bid not in BAZA:
        return muammo(404, "topilmadi", f"{bid} identifikatorli buyurtma yoʻq",
                      sorov.url.path)
    joriy = BAZA[bid]["holat"]
    if y.holat not in OTISHLAR:
        return muammo(400, "notogri-holat",
                      f"Nomaʼlum holat: {y.holat}. Mumkin: {', '.join(OTISHLAR)}",
                      sorov.url.path)
    if y.holat not in OTISHLAR[joriy]:
        return muammo(409, "otish-mumkin-emas",
                      f"“{joriy}” holatidan “{y.holat}” holatiga oʻtib boʻlmaydi",
                      sorov.url.path, joriy_holat=joriy)

    BAZA[bid]["holat"] = y.holat
    try:
        nashriyotchi.yubor(f"buyurtma.{y.holat}", BAZA[bid])
    except Exception as e:
        return muammo(503, "broker-ishlamayapti",
                      f"Hodisa yuborilmadi: {e.__class__.__name__}", sorov.url.path)
    return BAZA[bid]


@app.delete("/buyurtmalar/{bid}", status_code=204, summary="Buyurtmani oʻchirish")
def ochir(bid: str, sorov: Request):
    if bid not in BAZA:
        return muammo(404, "topilmadi", f"{bid} identifikatorli buyurtma yoʻq",
                      sorov.url.path)
    del BAZA[bid]
    return Response(status_code=204)      # 204 da tana boʻlmaydi


@app.get("/salomat", summary="Xizmat holati")
def salomat():
    return {"holat": "ishlayapti", "buyurtmalar": len(BAZA)}
