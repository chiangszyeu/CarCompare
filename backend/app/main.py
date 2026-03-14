import json
from contextlib import asynccontextmanager
from typing import Optional, List

from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from sqlalchemy import Column, Integer, String, Float, Boolean, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import Base, engine, get_db, init_db


class ChineseJSON(JSONResponse):
    def render(self, content) -> bytes:
        return json.dumps(content, ensure_ascii=False, indent=2).encode("utf-8")


class CarModel(Base):
    __tablename__ = "car_models"
    id = Column(Integer, primary_key=True, autoincrement=True)
    brand = Column(String(50), nullable=False)
    brand_zh = Column(String(50))
    series = Column(String(50), nullable=False)
    name = Column(String(200), nullable=False)
    year = Column(Integer, nullable=False)
    trim_level = Column(String(100))
    body_type = Column(String(50))
    msrp = Column(Integer)
    engine_type = Column(String(150))
    displacement_cc = Column(Integer)
    horsepower = Column(Integer)
    torque_kgm = Column(Float)
    fuel_type = Column(String(50))
    forced_induction = Column(String(50))
    transmission = Column(String(100))
    drivetrain = Column(String(20))
    length_mm = Column(Integer)
    width_mm = Column(Integer)
    height_mm = Column(Integer)
    wheelbase_mm = Column(Integer)
    curb_weight_kg = Column(Integer)
    cargo_volume_liters = Column(Integer)
    seats = Column(Integer, default=5)
    zero_to_hundred = Column(Float)
    fuel_economy_combined = Column(Float)
    airbag_count = Column(Integer)
    adas_level = Column(String(200))
    warranty_years = Column(Integer)
    features = Column(String(2000))
    image_url = Column(String(500))


from pydantic import BaseModel

class CarResponse(BaseModel):
    id: int
    brand: str
    brand_zh: Optional[str] = None
    series: str
    name: str
    year: int
    trim_level: Optional[str] = None
    body_type: Optional[str] = None
    msrp: Optional[int] = None
    engine_type: Optional[str] = None
    displacement_cc: Optional[int] = None
    horsepower: Optional[int] = None
    torque_kgm: Optional[float] = None
    fuel_type: Optional[str] = None
    forced_induction: Optional[str] = None
    transmission: Optional[str] = None
    drivetrain: Optional[str] = None
    length_mm: Optional[int] = None
    width_mm: Optional[int] = None
    height_mm: Optional[int] = None
    wheelbase_mm: Optional[int] = None
    curb_weight_kg: Optional[int] = None
    cargo_volume_liters: Optional[int] = None
    seats: Optional[int] = None
    zero_to_hundred: Optional[float] = None
    fuel_economy_combined: Optional[float] = None
    airbag_count: Optional[int] = None
    adas_level: Optional[str] = None
    warranty_years: Optional[int] = None
    features: Optional[str] = None
    image_url: Optional[str] = None
    class Config:
        from_attributes = True

class CompareRequest(BaseModel):
    car_ids: List[int]


COMPARE_FIELDS = [
    {"key": "msrp",                  "label": "建議售價",    "unit": "萬",    "direction": "lower",  "important": True},
    {"key": "engine_type",           "label": "引擎型式",    "unit": None,    "direction": "none",   "important": False},
    {"key": "displacement_cc",       "label": "排氣量",      "unit": "c.c.",  "direction": "none",   "important": False},
    {"key": "horsepower",            "label": "最大馬力",    "unit": "hp",    "direction": "higher", "important": True},
    {"key": "torque_kgm",            "label": "最大扭力",    "unit": "kg-m",  "direction": "higher", "important": True},
    {"key": "fuel_type",             "label": "燃料類型",    "unit": None,    "direction": "none",   "important": False},
    {"key": "forced_induction",      "label": "進氣方式",    "unit": None,    "direction": "none",   "important": False},
    {"key": "transmission",          "label": "變速箱",      "unit": None,    "direction": "none",   "important": False},
    {"key": "drivetrain",            "label": "驅動方式",    "unit": None,    "direction": "none",   "important": False},
    {"key": "zero_to_hundred",       "label": "0-100 km/h",  "unit": "秒",   "direction": "lower",  "important": True},
    {"key": "length_mm",             "label": "車長",        "unit": "mm",    "direction": "none",   "important": False},
    {"key": "width_mm",              "label": "車寬",        "unit": "mm",    "direction": "none",   "important": False},
    {"key": "height_mm",             "label": "車高",        "unit": "mm",    "direction": "none",   "important": False},
    {"key": "wheelbase_mm",          "label": "軸距",        "unit": "mm",    "direction": "higher", "important": False},
    {"key": "curb_weight_kg",        "label": "車重",        "unit": "kg",    "direction": "lower",  "important": False},
    {"key": "cargo_volume_liters",   "label": "行李箱容積",  "unit": "L",     "direction": "higher", "important": False},
    {"key": "seats",                 "label": "座位數",      "unit": "人",    "direction": "none",   "important": False},
    {"key": "fuel_economy_combined", "label": "平均油耗",    "unit": "km/L",  "direction": "higher", "important": True},
    {"key": "airbag_count",          "label": "氣囊數",      "unit": "具",    "direction": "higher", "important": True},
    {"key": "adas_level",            "label": "駕駛輔助",    "unit": None,    "direction": "none",   "important": True},
    {"key": "warranty_years",        "label": "保固年限",     "unit": "年",   "direction": "higher", "important": False},
]


def format_val(key, val):
    if val is None:
        return "-"
    if key == "msrp":
        return f"{val / 10000:.1f}"
    if key in ("displacement_cc", "length_mm", "width_mm", "height_mm", "wheelbase_mm", "curb_weight_kg"):
        return f"{val:,}"
    if key in ("torque_kgm", "zero_to_hundred", "fuel_economy_combined"):
        return f"{val:.1f}"
    if key == "fuel_type":
        return {"gasoline": "汽油", "diesel": "柴油", "hybrid": "油電混合", "phev": "插電油電", "bev": "純電動"}.get(val, str(val))
    if key == "forced_induction":
        return {"na": "自然進氣", "turbo": "渦輪增壓"}.get(val, str(val))
    return str(val)


def do_compare(cars):
    rows = []
    for field in COMPARE_FIELDS:
        key = field["key"]
        direction = field["direction"]
        raw_values = [getattr(car, key, None) for car in cars]
        display_values = [format_val(key, v) for v in raw_values]
        numeric = [v for v in raw_values if isinstance(v, (int, float))]
        cells = []
        for raw, display in zip(raw_values, display_values):
            hl = "neutral"
            diff = None
            if direction != "none" and numeric and isinstance(raw, (int, float)):
                if len(set(numeric)) == 1:
                    hl = "same"
                else:
                    best = max(numeric) if direction == "higher" else min(numeric)
                    if raw == best:
                        hl = "better"
                    else:
                        hl = "worse"
                        d = raw - best
                        if key == "msrp":
                            diff = f"{d / 10000:+.1f}萬"
                        elif isinstance(d, float):
                            diff = f"{d:+.1f}"
                        else:
                            diff = f"{d:+d}"
            cells.append({"display_value": display, "highlight": hl, "diff_text": diff})
        rows.append({"label": field["label"], "unit": field.get("unit"), "cells": cells, "is_important": field["important"]})
    return {
        "cars": [{"id": c.id, "brand": c.brand, "name": c.name, "year": c.year, "msrp": c.msrp} for c in cars],
        "rows": rows,
    }


BUYER_TYPES = [
    {"key": "family",     "name": "家庭用車",    "icon": "🏠", "color": "#4CAF50"},
    {"key": "commuter",   "name": "通勤代步",    "icon": "🚶", "color": "#2196F3"},
    {"key": "business",   "name": "商務形象",    "icon": "💼", "color": "#9C27B0"},
    {"key": "enthusiast", "name": "駕駛愛好者",  "icon": "🏎️", "color": "#F44336"},
    {"key": "first_car",  "name": "新手首購",    "icon": "🌟", "color": "#FF9800"},
    {"key": "outdoor",    "name": "戶外休閒",    "icon": "⛰️", "color": "#795548"},
    {"key": "eco",        "name": "環保節能",    "icon": "🌱", "color": "#009688"},
    {"key": "luxury",     "name": "豪華享受",    "icon": "👑", "color": "#E91E63"},
]

def analyze_buyer_type(car):
    results = []
    hp = car.horsepower or 0
    msrp_w = (car.msrp or 0) / 10000
    fuel_eco = car.fuel_economy_combined or 0
    airbags = car.airbag_count or 0
    cargo = car.cargo_volume_liters or 0
    brand = (car.brand or "").lower()
    dt = (car.drivetrain or "").upper()
    ft = car.fuel_type or ""
    is_lux = any(b in brand for b in ["lexus","mercedes-benz","bmw","audi","porsche","volvo"])
    is_rel = any(b in brand for b in ["toyota","lexus","honda","mazda"])
    trans = (car.transmission or "").lower()

    for bt in BUYER_TYPES:
        s = 50; pros = []; cons = []
        if bt["key"] == "family":
            if airbags >= 7: s += 15; pros.append(f"{airbags}具氣囊安全到位")
            if cargo >= 400: s += 12; pros.append(f"行李箱{cargo}L空間充裕")
            if car.adas_level: s += 10; pros.append("配備駕駛輔助系統")
            if fuel_eco >= 14: s += 8
            if fuel_eco < 10: cons.append("油耗偏高養車成本較高")
        elif bt["key"] == "commuter":
            if fuel_eco >= 18: s += 20; pros.append(f"油耗{fuel_eco}km/L超省油")
            elif fuel_eco >= 14: s += 12; pros.append(f"油耗{fuel_eco}km/L表現不錯")
            if msrp_w <= 120: s += 15; pros.append("入手門檻合理")
            elif msrp_w <= 180: s += 8
            if is_rel: s += 10; pros.append("品牌妥善率高")
            if msrp_w > 200: cons.append(f"售價{msrp_w:.0f}萬純通勤偏高")
        elif bt["key"] == "business":
            if is_lux: s += 25; pros.append("豪華品牌形象加分")
            if msrp_w >= 200: s += 10
            if car.adas_level: s += 8
            if not is_lux: cons.append("非豪華品牌商務場合稍弱")
        elif bt["key"] == "enthusiast":
            if hp >= 250: s += 25; pros.append(f"{hp}hp動力充沛")
            elif hp >= 200: s += 15; pros.append(f"{hp}hp動力堪用")
            elif hp < 150: s -= 10; cons.append(f"僅{hp}hp動力平庸")
            if car.zero_to_hundred and car.zero_to_hundred <= 7: s += 15; pros.append(f"0-100僅{car.zero_to_hundred}秒")
            if "cvt" in trans: s -= 10; cons.append("CVT缺乏駕駛樂趣")
            if dt in ("FR","MR","RR"): s += 8; pros.append(f"{dt}驅動操控佳")
        elif bt["key"] == "first_car":
            if msrp_w <= 150: s += 15; pros.append(f"售價{msrp_w:.0f}萬新手友善")
            elif msrp_w <= 200: s += 8
            if is_rel: s += 15; pros.append("品牌可靠好養")
            if airbags >= 6: s += 12; pros.append("安全配備完善")
            if car.adas_level: s += 10; pros.append("駕駛輔助讓新手更安心")
        elif bt["key"] == "outdoor":
            if dt in ("AWD","4WD"): s += 25; pros.append("四驅系統越野安心")
            else: s -= 10; cons.append("非四驅越野能力有限")
            if cargo >= 500: s += 10; pros.append("大空間裝載力強")
        elif bt["key"] == "eco":
            if ft == "bev": s += 30; pros.append("純電零排放")
            elif ft == "phev": s += 20; pros.append("插電油電超省油")
            elif ft == "hybrid": s += 15; pros.append("油電混合節能")
            if fuel_eco >= 20: s += 15; pros.append(f"油耗{fuel_eco}km/L非常優秀")
            elif fuel_eco >= 15: s += 8
            if ft == "gasoline" and fuel_eco < 12: cons.append("純燃油油耗偏高")
        elif bt["key"] == "luxury":
            if is_lux: s += 20; pros.append("豪華品牌質感保證")
            if msrp_w >= 250: s += 10; pros.append("高階定位配備豐富")
            if not is_lux: cons.append("非豪華品牌")
        s = max(0, min(100, s))
        g = "S" if s>=90 else "A+" if s>=82 else "A" if s>=74 else "B+" if s>=66 else "B" if s>=58 else "C+" if s>=50 else "C" if s>=40 else "D"
        if not pros: pros = ["表現中規中矩"]
        if not cons: cons = ["無明顯短板"]
        results.append({**bt, "score": s, "grade": g, "pros": pros[:3], "cons": cons[:2]})
    results.sort(key=lambda x: x["score"], reverse=True)
    return results


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("\n🚗 CarCompare API 啟動中...")
    await init_db()
    await seed_data()
    print("=" * 50)
    print("✅ API 已就緒！")
    print("👉 打開瀏覽器：http://localhost:8000/docs")
    print("=" * 50 + "\n")
    yield
    print("👋 API 關閉")


app = FastAPI(
    title="CarCompare API",
    description="台灣新車資訊搜集、比較、購車分析平台",
    version="1.0.0",
    lifespan=lifespan,
    default_response_class=ChineseJSON,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["首頁"])
async def root():
    return {
        "message": "🚗 歡迎使用 CarCompare API",
        "使用說明": "打開 /docs 查看完整 API 文件",
        "API列表": {
            "搜尋車型": "GET /api/cars/search?keyword=NX",
            "車型詳情": "GET /api/cars/{id}",
            "比較車型": "POST /api/compare (在 /docs 頁面操作)",
            "購車分析": "GET /api/analysis/{id}",
        }
    }


@app.get("/api/cars/search", tags=["車型"])
async def search_cars(keyword: str = Query(default=None, description="搜尋關鍵字"), db: AsyncSession = Depends(get_db)):
    query = select(CarModel)
    if keyword:
        kw = f"%{keyword}%"
        query = query.where(CarModel.name.like(kw) | CarModel.brand.like(kw) | CarModel.brand_zh.like(kw) | CarModel.series.like(kw))
    result = await db.execute(query.order_by(CarModel.msrp))
    cars = result.scalars().all()
    return {"total": len(cars), "items": [CarResponse.model_validate(c).model_dump() for c in cars]}


@app.get("/api/cars/{car_id}", tags=["車型"])
async def get_car(car_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CarModel).where(CarModel.id == car_id))
    car = result.scalar_one_or_none()
    if not car:
        raise HTTPException(status_code=404, detail="找不到此車型")
    return CarResponse.model_validate(car).model_dump()


@app.post("/api/compare", tags=["比較"])
async def compare_cars(request: CompareRequest, db: AsyncSession = Depends(get_db)):
    """比較車型（含差異色彩標記）：better=綠色較優 / worse=紅色較弱 / same=相同 / neutral=中性"""
    if len(request.car_ids) < 2:
        raise HTTPException(status_code=400, detail="至少需要2台車")
    if len(request.car_ids) > 4:
        raise HTTPException(status_code=400, detail="最多比較4台車")
    result = await db.execute(select(CarModel).where(CarModel.id.in_(request.car_ids)))
    cars = result.scalars().all()
    if len(cars) < 2:
        raise HTTPException(status_code=404, detail="找不到足夠的車型資料")
    id_order = {cid: i for i, cid in enumerate(request.car_ids)}
    cars = sorted(cars, key=lambda c: id_order.get(c.id, 0))
    return do_compare(cars)


@app.get("/api/compare/quick", tags=["比較"])
async def quick_compare(ids: str = Query(..., description="車型ID逗號分隔，例如: 1,3"), db: AsyncSession = Depends(get_db)):
    """快速比較（GET版本，可直接在瀏覽器網址列使用）"""
    try:
        car_ids = [int(x.strip()) for x in ids.split(",") if x.strip()]
    except ValueError:
        raise HTTPException(status_code=400, detail="ID格式錯誤，範例: ?ids=1,3")
    if len(car_ids) < 2 or len(car_ids) > 4:
        raise HTTPException(status_code=400, detail="需要2-4個車型ID")
    result = await db.execute(select(CarModel).where(CarModel.id.in_(car_ids)))
    cars = result.scalars().all()
    if len(cars) < 2:
        raise HTTPException(status_code=404, detail="找不到足夠的車型資料")
    id_order = {cid: i for i, cid in enumerate(car_ids)}
    cars = sorted(cars, key=lambda c: id_order.get(c.id, 0))
    return do_compare(cars)


@app.get("/api/analysis/{car_id}", tags=["分析"])
async def analyze_car(car_id: int, db: AsyncSession = Depends(get_db)):
    """分析車型適合的購車類型（8種類型評分）"""
    result = await db.execute(select(CarModel).where(CarModel.id == car_id))
    car = result.scalar_one_or_none()
    if not car:
        raise HTTPException(status_code=404, detail="找不到此車型")
    scores = analyze_buyer_type(car)
    fuel_eco = car.fuel_economy_combined or 12
    annual_fuel = int((15000 / fuel_eco) * 32)
    cc = car.displacement_cc or 1800
    annual_tax = (7120 + 4320) if cc <= 1800 else (11230 + 7120)
    is_euro = any(b in (car.brand or "").lower() for b in ["bmw","mercedes-benz","audi","porsche"])
    annual_maint = 25000 if is_euro else (15000 if "lexus" in (car.brand or "").lower() else 12000)
    annual_ins = int((car.msrp or 0) * 0.035)
    annual_total = annual_fuel + annual_tax + annual_maint + annual_ins
    return {
        "car": {"id": car.id, "brand": car.brand, "name": car.name, "year": car.year, "msrp": car.msrp},
        "buyer_scores": scores,
        "top_recommended": [s["name"] for s in scores[:3]],
        "ownership_cost": {
            "monthly_average": int(annual_total / 12),
            "annual": {"fuel": annual_fuel, "insurance": annual_ins, "tax": annual_tax, "maintenance": annual_maint, "total": annual_total},
            "five_year_total": annual_total * 5,
        },
    }



# ============ 爬蟲 API ============
from app.scraper.scheduler import scheduler as crawler_scheduler

@app.post("/api/crawler/run", tags=["爬蟲"])
async def run_crawler():
    """手動觸發爬蟲（背景執行）"""
    result = crawler_scheduler.run_in_background()
    return {"message": "爬蟲已啟動", **result}

@app.get("/api/crawler/status", tags=["爬蟲"])
async def crawler_status():
    """查看爬蟲執行狀態"""
    return crawler_scheduler.get_status()

@app.post("/api/crawler/update-prices", tags=["爬蟲"])
async def update_prices():
    """僅更新已知車款的最新價格（不爬網站）"""
    from app.scraper.crawler_official import update_latest_prices
    updated = update_latest_prices()
    return {"message": f"已更新 {updated} 筆價格", "updated": updated}

@app.get("/api/stats", tags=["統計"])
async def get_stats(db: AsyncSession = Depends(get_db)):
    """取得資料庫統計"""
    from sqlalchemy import func
    total = (await db.execute(select(func.count(CarModel.id)))).scalar()
    brands = (await db.execute(select(func.count(func.distinct(CarModel.brand))))).scalar()
    return {
        "total_cars": total,
        "total_brands": brands,
        "last_crawl": crawler_scheduler.last_run.isoformat() if crawler_scheduler.last_run else None,
    }



# ===== AI 智慧分析 =====
@app.get("/api/ai/recommend", tags=["AI 智慧分析"])
async def ai_recommend_endpoint(q: str = Query(..., description="購車問題，例如：預算150萬，家庭用，要省油")):
    """AI 智慧推薦 - 根據需求推薦車型"""
    try:
        from app.ai_advisor import ai_recommend
        result = ai_recommend(q)
        return result
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/ai/compare", tags=["AI 智慧分析"])
async def ai_compare_endpoint(ids: str = Query(..., description="車型ID逗號分隔，例如: 1,3,5"), q: str = Query(default=None, description="比較問題（可選）")):
    """AI 智慧比較 - 深度分析多台車的差異"""
    try:
        from app.ai_advisor import ai_compare
        car_ids = [int(x.strip()) for x in ids.split(",")]
        result = ai_compare(car_ids, q)
        return result
    except Exception as e:
        return {"error": str(e)}


async def seed_data():
    from app.database import async_session
    async with async_session() as db:
        result = await db.execute(select(CarModel).limit(1))
        if result.scalar_one_or_none():
            print("📦 資料庫已有資料，跳過")
            return
        cars = [
            CarModel(brand="Lexus", brand_zh="凌志", series="NX", name="NX 200 豪華版", year=2026, trim_level="豪華版", body_type="SUV", msrp=1810000, engine_type="2.0L 直列四缸 自然進氣", displacement_cc=1987, horsepower=173, torque_kgm=20.8, fuel_type="gasoline", forced_induction="na", transmission="Direct Shift-CVT 10速", drivetrain="FF", length_mm=4660, width_mm=1865, height_mm=1640, wheelbase_mm=2690, curb_weight_kg=1620, cargo_volume_liters=520, seats=5, zero_to_hundred=9.8, fuel_economy_combined=14.4, airbag_count=8, adas_level="Lexus Safety System+ 3.0 全速域ACC", warranty_years=4, features="全速域ACC,車道維持,AEB,BSM盲點偵測,電動尾門,8氣囊"),
            CarModel(brand="Lexus", brand_zh="凌志", series="NX", name="NX 350h 旗艦版", year=2026, trim_level="旗艦版", body_type="SUV", msrp=2520000, engine_type="2.5L 直列四缸 油電混合", displacement_cc=2487, horsepower=190, torque_kgm=24.8, fuel_type="hybrid", forced_induction="na", transmission="E-CVT", drivetrain="AWD", length_mm=4660, width_mm=1865, height_mm=1640, wheelbase_mm=2690, curb_weight_kg=1780, cargo_volume_liters=520, seats=5, zero_to_hundred=7.7, fuel_economy_combined=20.1, airbag_count=8, adas_level="Lexus Safety System+ 3.0 全速域ACC", warranty_years=4, features="全速域ACC,車道維持,AEB,BSM,HUD,全景天窗,Mark Levinson,通風座椅,14吋螢幕"),
            CarModel(brand="Mercedes-Benz", brand_zh="賓士", series="GLC", name="GLC 200 4MATIC", year=2026, trim_level="運動版", body_type="SUV", msrp=2660000, engine_type="2.0L 直列四缸 渦輪增壓+48V", displacement_cc=1999, horsepower=204, torque_kgm=32.6, fuel_type="hybrid", forced_induction="turbo", transmission="9G-TRONIC 9速手自排", drivetrain="AWD", length_mm=4730, width_mm=1890, height_mm=1640, wheelbase_mm=2888, curb_weight_kg=1830, cargo_volume_liters=620, seats=5, zero_to_hundred=7.9, fuel_economy_combined=13.4, airbag_count=9, adas_level="Intelligent Drive 全速域ACC", warranty_years=3, features="全速域ACC,車道維持,AEB,BSM,9氣囊,HUD,全景天窗,Burmester,通風座椅,環景影像"),
            CarModel(brand="Toyota", brand_zh="豐田", series="RAV4", name="RAV4 2.0 旗艦版", year=2026, trim_level="旗艦版", body_type="SUV", msrp=1130000, engine_type="2.0L 直列四缸 自然進氣", displacement_cc=1987, horsepower=173, torque_kgm=20.7, fuel_type="gasoline", forced_induction="na", transmission="Direct Shift-CVT", drivetrain="FF", length_mm=4600, width_mm=1855, height_mm=1685, wheelbase_mm=2690, curb_weight_kg=1570, cargo_volume_liters=580, seats=5, zero_to_hundred=10.5, fuel_economy_combined=15.2, airbag_count=7, adas_level="Toyota Safety Sense 3.0 全速域ACC", warranty_years=5, features="全速域ACC,車道維持,AEB,BSM,7氣囊,電動尾門,9吋螢幕"),
            CarModel(brand="BMW", brand_zh="寶馬", series="X3", name="X3 sDrive20i", year=2026, trim_level="標準版", body_type="SUV", msrp=2550000, engine_type="2.0L 直列四缸 渦輪增壓", displacement_cc=1998, horsepower=190, torque_kgm=31.6, fuel_type="gasoline", forced_induction="turbo", transmission="Steptronic 8速手自排", drivetrain="FR", length_mm=4755, width_mm=1920, height_mm=1660, wheelbase_mm=2865, curb_weight_kg=1790, cargo_volume_liters=570, seats=5, zero_to_hundred=8.0, fuel_economy_combined=13.0, airbag_count=7, adas_level="BMW Personal CoPilot 全速域ACC", warranty_years=3, features="全速域ACC,車道維持,AEB,BSM,7氣囊,電動尾門,HUD,環景影像,12.3吋螢幕"),
        ]
        db.add_all(cars)
        await db.commit()
        print(f"✅ 已灌入 {len(cars)} 筆車型資料：")
        for i, c in enumerate(cars, 1):
            print(f"   ID={i}: {c.brand} {c.name} - {c.msrp//10000}萬")
