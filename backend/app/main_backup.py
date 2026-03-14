"""
CarCompare API - 最小可運行版本
啟動方式：uvicorn app.main:app --reload
"""
from contextlib import asynccontextmanager
from typing import Optional, List
from decimal import Decimal

from fastapi import FastAPI
from fastapi.responses import JSONResponse
import json, HTTPException, Query
from fastapi.responses import JSONResponse
import json
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import Column, Integer, String, Float, Boolean, select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

from app.database import Base, engine, get_db, init_db


# ============================================================
# 1. 資料庫模型
# ============================================================
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

    # 價格
    msrp = Column(Integer)  # 建議售價（元）

    # 引擎
    engine_type = Column(String(150))
    displacement_cc = Column(Integer)
    horsepower = Column(Integer)
    torque_kgm = Column(Float)
    fuel_type = Column(String(50))
    forced_induction = Column(String(50))
    transmission = Column(String(100))
    drivetrain = Column(String(20))

    # 車身
    length_mm = Column(Integer)
    width_mm = Column(Integer)
    height_mm = Column(Integer)
    wheelbase_mm = Column(Integer)
    curb_weight_kg = Column(Integer)
    cargo_volume_liters = Column(Integer)
    seats = Column(Integer, default=5)

    # 性能
    zero_to_hundred = Column(Float)

    # 油耗
    fuel_economy_combined = Column(Float)

    # 安全
    airbag_count = Column(Integer)
    adas_level = Column(String(200))

    # 保固
    warranty_years = Column(Integer)

    # 配備（簡化版：用逗號分隔的字串）
    features = Column(String(2000))

    image_url = Column(String(500))


# ============================================================
# 2. API Schema
# ============================================================
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


class CompareCell(BaseModel):
    raw_value: Optional[str] = None
    display_value: str = "-"
    highlight: str = "neutral"  # better / worse / same / neutral
    diff_text: Optional[str] = None


class CompareRow(BaseModel):
    label: str
    unit: Optional[str] = None
    cells: List[CompareCell]
    is_important: bool = False


class CompareRequest(BaseModel):
    car_ids: List[int]


# ============================================================
# 3. 比較邏輯引擎
# ============================================================
# 定義每個比較欄位
COMPARE_FIELDS = [
    {"key": "msrp",          "label": "建議售價",   "unit": "萬",    "direction": "lower",  "important": True,
     "format": lambda v: f"{v/10000:.1f}" if v else "-"},
    {"key": "engine_type",   "label": "引擎型式",   "unit": None,    "direction": "none",   "important": False},
    {"key": "displacement_cc","label": "排氣量",    "unit": "c.c.",  "direction": "none",   "important": False,
     "format": lambda v: f"{v:,}" if v else "-"},
    {"key": "horsepower",    "label": "最大馬力",   "unit": "hp",    "direction": "higher", "important": True},
    {"key": "torque_kgm",    "label": "最大扭力",   "unit": "kg-m",  "direction": "higher", "important": True,
     "format": lambda v: f"{v:.1f}" if v else "-"},
    {"key": "fuel_type",     "label": "燃料類型",   "unit": None,    "direction": "none",   "important": False,
     "format": lambda v: {"gasoline":"汽油","diesel":"柴油","hybrid":"油電混合","phev":"插電油電","bev":"純電動"}.get(v,v) if v else "-"},
    {"key": "forced_induction","label": "進氣方式", "unit": None,    "direction": "none",   "important": False,
     "format": lambda v: {"na":"自然進氣","turbo":"渦輪增壓"}.get(v,v) if v else "-"},
    {"key": "transmission",  "label": "變速箱",     "unit": None,    "direction": "none",   "important": False},
    {"key": "drivetrain",    "label": "驅動方式",   "unit": None,    "direction": "none",   "important": False},
    {"key": "zero_to_hundred","label": "0-100 km/h","unit": "秒",   "direction": "lower",  "important": True,
     "format": lambda v: f"{v:.1f}" if v else "-"},
    {"key": "length_mm",     "label": "車長",       "unit": "mm",    "direction": "none",   "important": False,
     "format": lambda v: f"{v:,}" if v else "-"},
    {"key": "width_mm",      "label": "車寬",       "unit": "mm",    "direction": "none",   "important": False,
     "format": lambda v: f"{v:,}" if v else "-"},
    {"key": "height_mm",     "label": "車高",       "unit": "mm",    "direction": "none",   "important": False,
     "format": lambda v: f"{v:,}" if v else "-"},
    {"key": "wheelbase_mm",  "label": "軸距",       "unit": "mm",    "direction": "higher", "important": False,
     "format": lambda v: f"{v:,}" if v else "-"},
    {"key": "curb_weight_kg","label": "車重",       "unit": "kg",    "direction": "lower",  "important": False,
     "format": lambda v: f"{v:,}" if v else "-"},
    {"key": "cargo_volume_liters","label": "行李箱容積","unit": "L",  "direction": "higher", "important": False},
    {"key": "seats",         "label": "座位數",     "unit": "人",    "direction": "none",   "important": False},
    {"key": "fuel_economy_combined","label": "平均油耗","unit": "km/L","direction": "higher","important": True,
     "format": lambda v: f"{v:.1f}" if v else "-"},
    {"key": "airbag_count",  "label": "氣囊數",     "unit": "具",    "direction": "higher", "important": True},
    {"key": "adas_level",    "label": "駕駛輔助",   "unit": None,    "direction": "none",   "important": True},
    {"key": "warranty_years","label": "保固年限",    "unit": "年",    "direction": "higher", "important": False},
]


def do_compare(cars: list) -> dict:
    """核心比較函數：產生帶有差異標記的比較表格"""
    rows = []

    for field in COMPARE_FIELDS:
        key = field["key"]
        direction = field["direction"]
        fmt = field.get("format", lambda v: str(v) if v is not None else "-")

        # 取得每台車的值
        raw_values = [getattr(car, key, None) for car in cars]
        display_values = [fmt(v) for v in raw_values]

        # 計算差異標記
        numeric_values = [v for v in raw_values if isinstance(v, (int, float))]
        cells = []

        for i, (raw, display) in enumerate(zip(raw_values, display_values)):
            highlight = "neutral"
            diff_text = None

            if direction != "none" and numeric_values and isinstance(raw, (int, float)):
                if len(set(numeric_values)) == 1:
                    highlight = "same"
                else:
                    if direction == "higher":
                        best = max(numeric_values)
                    else:
                        best = min(numeric_values)

                    if raw == best:
                        highlight = "better"
                    else:
                        highlight = "worse"
                        diff = raw - best
                        if key == "msrp":
                            diff_text = f"{diff/10000:+.1f}萬"
                        elif isinstance(diff, float):
                            diff_text = f"{diff:+.1f}"
                        else:
                            diff_text = f"{diff:+d}"

            cells.append(CompareCell(
                raw_value=str(raw) if raw is not None else None,
                display_value=display,
                highlight=highlight,
                diff_text=diff_text,
            ))

        rows.append(CompareRow(
            label=field["label"],
            unit=field.get("unit"),
            cells=cells,
            is_important=field.get("important", False),
        ))

    return {
        "cars": [
            {"id": c.id, "brand": c.brand, "name": c.name,
             "year": c.year, "msrp": c.msrp, "image_url": c.image_url}
            for c in cars
        ],
        "rows": [r.model_dump() for r in rows],
    }


# ============================================================
# 4. 購車類型分析
# ============================================================
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


def analyze_buyer_type(car) -> list:
    """簡易版購車類型分析"""
    results = []
    hp = car.horsepower or 0
    msrp_wan = (car.msrp or 0) / 10000
    fuel_eco = car.fuel_economy_combined or 0
    airbags = car.airbag_count or 0
    cargo = car.cargo_volume_liters or 0
    brand = (car.brand or "").lower()
    drivetrain = (car.drivetrain or "").upper()
    fuel = car.fuel_type or ""

    luxury_brands = ["lexus", "mercedes-benz", "bmw", "audi", "porsche", "volvo"]
    is_luxury = any(b in brand for b in luxury_brands)
    reliable_brands = ["toyota", "lexus", "honda", "mazda"]
    is_reliable = any(b in brand for b in reliable_brands)

    for bt in BUYER_TYPES:
        score = 50  # 基礎分
        pros = []
        cons = []

        if bt["key"] == "family":
            if airbags >= 7: score += 15; pros.append(f"{airbags}具氣囊，安全到位")
            if cargo >= 400: score += 12; pros.append(f"行李箱{cargo}L空間充裕")
            if car.adas_level: score += 10; pros.append("具備駕駛輔助系統")
            if fuel_eco >= 14: score += 8
            if car.seats and car.seats >= 5: score += 5
            if fuel_eco < 10: cons.append("油耗偏高養車成本較高")

        elif bt["key"] == "commuter":
            if fuel_eco >= 18: score += 20; pros.append(f"油耗{fuel_eco}km/L 非常省油")
            elif fuel_eco >= 14: score += 12; pros.append(f"油耗{fuel_eco}km/L 表現不錯")
            if msrp_wan <= 120: score += 15; pros.append("入手門檻合理")
            elif msrp_wan <= 180: score += 8
            if is_reliable: score += 10; pros.append("品牌妥善率高")
            if msrp_wan > 200: cons.append(f"售價{msrp_wan:.0f}萬 純通勤偏高")

        elif bt["key"] == "business":
            if is_luxury: score += 25; pros.append("豪華品牌形象加分")
            if msrp_wan >= 200: score += 10
            if car.adas_level: score += 8
            if not is_luxury: cons.append("非豪華品牌，商務場合稍弱")

        elif bt["key"] == "enthusiast":
            if hp >= 250: score += 25; pros.append(f"{hp}hp 動力充沛")
            elif hp >= 200: score += 15; pros.append(f"{hp}hp 動力堪用")
            elif hp < 150: score -= 10; cons.append(f"僅{hp}hp 動力不足")
            if car.zero_to_hundred and car.zero_to_hundred <= 7: score += 15; pros.append(f"0-100僅{car.zero_to_hundred}秒")
            trans = (car.transmission or "").lower()
            if "cvt" in trans: score -= 10; cons.append("CVT缺乏駕駛樂趣")
            if drivetrain in ("FR", "MR", "RR"): score += 8; pros.append(f"{drivetrain}驅動操控佳")

        elif bt["key"] == "first_car":
            if msrp_wan <= 150: score += 15; pros.append(f"售價{msrp_wan:.0f}萬 新手友善")
            elif msrp_wan <= 200: score += 8
            if is_reliable: score += 15; pros.append("品牌可靠好養")
            if airbags >= 6: score += 12; pros.append("安全配備完善")
            if car.adas_level: score += 10; pros.append("駕駛輔助讓新手更安心")

        elif bt["key"] == "outdoor":
            if drivetrain in ("AWD", "4WD"): score += 25; pros.append("四驅系統越野更安心")
            else: score -= 10; cons.append("非四驅，越野能力有限")
            if cargo >= 500: score += 10; pros.append("大空間裝載能力強")

        elif bt["key"] == "eco":
            if fuel in ("bev",): score += 30; pros.append("純電零排放")
            elif fuel in ("phev",): score += 20; pros.append("插電油電超省油")
            elif fuel in ("hybrid",): score += 15; pros.append("油電混合節能")
            if fuel_eco >= 20: score += 15; pros.append(f"油耗{fuel_eco}km/L 非常優秀")
            elif fuel_eco >= 15: score += 8
            if fuel in ("gasoline", "diesel") and fuel_eco < 12: cons.append("純燃油車油耗偏高")

        elif bt["key"] == "luxury":
            if is_luxury: score += 20; pros.append("豪華品牌質感保證")
            if msrp_wan >= 250: score += 10; pros.append("高階定位配備豐富")
            if car.features and len(car.features) > 100: score += 8
            if not is_luxury: cons.append("非豪華品牌")

        score = max(0, min(100, score))

        # 分數轉等級
        if score >= 90: grade = "S"
        elif score >= 82: grade = "A+"
        elif score >= 74: grade = "A"
        elif score >= 66: grade = "B+"
        elif score >= 58: grade = "B"
        elif score >= 50: grade = "C+"
        elif score >= 40: grade = "C"
        else: grade = "D"

        if not pros: pros.append("表現中規中矩")
        if not cons: cons.append("無明顯短板")

        results.append({
            **bt,
            "score": score,
            "grade": grade,
            "pros": pros[:3],
            "cons": cons[:2],
        })

    results.sort(key=lambda x: x["score"], reverse=True)
    return results


# ============================================================
# 5. FastAPI 應用程式
# ============================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚗 CarCompare API 啟動中...")
    await init_db()
    # 自動灌入種子資料
    await seed_data()
    print("✅ API 已就緒！打開 http://localhost:8000/docs 查看")
    yield
    print("👋 API 關閉")


class PrettyJSONResponse(JSONResponse):
    def render(self, content) -> bytes:
        return json.dumps(content, ensure_ascii=False, indent=2).encode("utf-8")

class PrettyJSONResponse(JSONResponse):
    def render(self, content) -> bytes:
        return json.dumps(content, ensure_ascii=False, indent=2).encode("utf-8")

app = FastAPI(
    default_response_class=PrettyJSONResponse,
    default_response_class=PrettyJSONResponse,
    title="🚗 CarCompare API",
    description="台灣新車資訊搜集、比較、購車分析平台",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ------ API 端點 ------

@app.get("/", tags=["首頁"])
async def root():
    return {
        "message": "🚗 歡迎使用 CarCompare API",
        "docs": "http://localhost:8000/docs",
        "endpoints": {
            "搜尋車型": "GET /api/cars/search?keyword=NX",
            "車型詳情": "GET /api/cars/{id}",
            "比較車型": "POST /api/compare",
            "購車分析": "GET /api/analysis/{id}",
        }
    }


@app.get("/api/cars/search", tags=["車型"])
async def search_cars(
    keyword: str = Query(default=None, description="搜尋關鍵字，例如：NX200、GLC"),
    brand: str = Query(default=None, description="品牌篩選，例如：Lexus"),
    body_type: str = Query(default=None, description="車型篩選，例如：SUV"),
    db: AsyncSession = Depends(get_db),
):
    """搜尋車型"""
    query = select(CarModel)

    if keyword:
        query = query.where(
            CarModel.name.contains(keyword) |
            CarModel.brand.contains(keyword) |
            CarModel.brand_zh.contains(keyword) |
            CarModel.series.contains(keyword)
        )
    if brand:
        query = query.where(CarModel.brand.contains(brand))
    if body_type:
        query = query.where(CarModel.body_type == body_type)

    result = await db.execute(query.order_by(CarModel.msrp))
    cars = result.scalars().all()

    return {
        "total": len(cars),
        "items": [CarResponse.model_validate(c).model_dump() for c in cars]
    }


@app.get("/api/cars/{car_id}", tags=["車型"])
async def get_car(car_id: int, db: AsyncSession = Depends(get_db)):
    """取得車型詳細資料"""
    result = await db.execute(select(CarModel).where(CarModel.id == car_id))
    car = result.scalar_one_or_none()
    if not car:
        raise HTTPException(status_code=404, detail="找不到此車型")
    return CarResponse.model_validate(car).model_dump()


@app.post("/api/compare", tags=["比較"])
async def compare_cars(
    request: CompareRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    🔥 核心功能：比較多台車型

    傳入車型 ID 列表，回傳帶有差異色彩標記的比較表格。

    highlight 值說明：
    - better（綠色）：該項目較優
    - worse（紅色）：該項目較弱
    - same（灰色）：相同
    - neutral（藍色）：無好壞之分
    """
    if len(request.car_ids) < 2:
        raise HTTPException(status_code=400, detail="至少需要 2 台車才能比較")
    if len(request.car_ids) > 4:
        raise HTTPException(status_code=400, detail="最多比較 4 台車")

    result = await db.execute(
        select(CarModel).where(CarModel.id.in_(request.car_ids))
    )
    cars = result.scalars().all()

    if len(cars) < 2:
        raise HTTPException(status_code=404, detail="找不到足夠的車型資料")

    # 按照傳入的 ID 順序排序
    id_order = {cid: i for i, cid in enumerate(request.car_ids)}
    cars = sorted(cars, key=lambda c: id_order.get(c.id, 0))

    return do_compare(cars)


@app.get("/api/analysis/{car_id}", tags=["分析"])
async def analyze_car(car_id: int, db: AsyncSession = Depends(get_db)):
    """
    🧠 分析車型適合的購車類型

    回傳 8 種購車類型的適合度評分（0-100）
    """
    result = await db.execute(select(CarModel).where(CarModel.id == car_id))
    car = result.scalar_one_or_none()
    if not car:
        raise HTTPException(status_code=404, detail="找不到此車型")

    scores = analyze_buyer_type(car)

    # 養車成本估算
    fuel_eco = car.fuel_economy_combined or 12
    annual_fuel = int((15000 / fuel_eco) * 32)
    annual_tax = 7120 + 4320 if (car.displacement_cc or 0) <= 1800 else 11230 + 7120
    is_luxury_brand = any(b in (car.brand or "").lower() for b in ["bmw", "mercedes-benz", "audi", "porsche"])
    annual_maintenance = 25000 if is_luxury_brand else 15000 if "lexus" in (car.brand or "").lower() else 12000
    annual_insurance = int((car.msrp or 0) * 0.035)
    annual_total = annual_fuel + annual_tax + annual_maintenance + annual_insurance

    return {
        "car": {"id": car.id, "brand": car.brand, "name": car.name, "year": car.year},
        "buyer_scores": scores,
        "top_recommended": [s["name"] for s in scores[:3]],
        "ownership_cost": {
            "monthly_average": int(annual_total / 12),
            "annual": {
                "fuel": annual_fuel,
                "insurance": annual_insurance,
                "tax": annual_tax,
                "maintenance": annual_maintenance,
                "total": annual_total,
            },
            "five_year_total": annual_total * 5,
        },
    }


# ============================================================
# 6. 種子資料
# ============================================================
async def seed_data():
    """自動灌入範例車型（如果資料庫是空的）"""
    from app.database import async_session
    async with async_session() as db:
        result = await db.execute(select(CarModel).limit(1))
        if result.scalar_one_or_none():
            print("📦 資料庫已有資料，跳過種子資料")
            return

        cars = [
            CarModel(
                brand="Lexus", brand_zh="凌志", series="NX",
                name="NX 200 豪華版", year=2026, trim_level="豪華版",
                body_type="SUV", msrp=1810000,
                engine_type="2.0L 直列四缸 自然進氣",
                displacement_cc=1987, horsepower=173, torque_kgm=20.8,
                fuel_type="gasoline", forced_induction="na",
                transmission="Direct Shift-CVT 10速", drivetrain="FF",
                length_mm=4660, width_mm=1865, height_mm=1640,
                wheelbase_mm=2690, curb_weight_kg=1620,
                cargo_volume_liters=520, seats=5,
                zero_to_hundred=9.8, fuel_economy_combined=14.4,
                airbag_count=8, adas_level="Lexus Safety System+ 3.0 全速域ACC",
                warranty_years=4,
                features="全速域ACC,車道維持,車道偏離警示,AEB自動緊急煞車,BSM盲點偵測,RCTA後方車側警示,電動尾門,雙前座電動椅,9.8吋觸控螢幕,無線Apple CarPlay,8具氣囊",
            ),
            CarModel(
                brand="Lexus", brand_zh="凌志", series="NX",
                name="NX 350h 旗艦版", year=2026, trim_level="旗艦版",
                body_type="SUV", msrp=2520000,
                engine_type="2.5L 直列四缸 油電混合",
                displacement_cc=2487, horsepower=190, torque_kgm=24.8,
                fuel_type="hybrid", forced_induction="na",
                transmission="E-CVT", drivetrain="AWD",
                length_mm=4660, width_mm=1865, height_mm=1640,
                wheelbase_mm=2690, curb_weight_kg=1780,
                cargo_volume_liters=520, seats=5,
                zero_to_hundred=7.7, fuel_economy_combined=20.1,
                airbag_count=8, adas_level="Lexus Safety System+ 3.0 全速域ACC",
                warranty_years=4,
                features="全速域ACC,車道維持,車道偏離警示,AEB自動緊急煞車,BSM盲點偵測,RCTA後方車側警示,電動尾門,雙前座電動椅,14吋觸控螢幕,無線Apple CarPlay,8具氣囊,HUD抬頭顯示,全景天窗,Mark Levinson音響,通風座椅,電動方向盤調整",
            ),
            CarModel(
                brand="Mercedes-Benz", brand_zh="賓士", series="GLC",
                name="GLC 200 4MATIC", year=2026, trim_level="運動版",
                body_type="SUV", msrp=2660000,
                engine_type="2.0L 直列四缸 渦輪增壓 + 48V輕油電",
                displacement_cc=1999, horsepower=204, torque_kgm=32.6,
                fuel_type="hybrid", forced_induction="turbo",
                transmission="9G-TRONIC 9速手自排", drivetrain="AWD",
                length_mm=4730, width_mm=1890, height_mm=1640,
                wheelbase_mm=2888, curb_weight_kg=1830,
                cargo_volume_liters=620, seats=5,
                zero_to_hundred=7.9, fuel_economy_combined=13.4,
                airbag_count=9, adas_level="Intelligent Drive 全速域ACC",
                warranty_years=3,
                features="全速域ACC,車道維持,AEB自動緊急煞車,BSM盲點偵測,9具氣囊,HUD抬頭顯示,全景天窗,Burmester音響,通風座椅,電動尾門,雙前座電動椅,11.9吋觸控螢幕,無線Apple CarPlay,環景影像,氣氛燈",
            ),
            CarModel(
                brand="Toyota", brand_zh="豐田", series="RAV4",
                name="RAV4 2.0 旗艦版", year=2026, trim_level="旗艦版",
                body_type="SUV", msrp=1130000,
                engine_type="2.0L 直列四缸 自然進氣",
                displacement_cc=1987, horsepower=173, torque_kgm=20.7,
                fuel_type="gasoline", forced_induction="na",
                transmission="Direct Shift-CVT", drivetrain="FF",
                length_mm=4600, width_mm=1855, height_mm=1685,
                wheelbase_mm=2690, curb_weight_kg=1570,
                cargo_volume_liters=580, seats=5,
                zero_to_hundred=10.5, fuel_economy_combined=15.2,
                airbag_count=7, adas_level="Toyota Safety Sense 3.0 全速域ACC",
                warranty_years=5,
                features="全速域ACC,車道維持,AEB自動緊急煞車,BSM盲點偵測,7具氣囊,電動尾門,雙前座電動椅,9吋觸控螢幕,無線Apple CarPlay,倒車影像",
            ),
            CarModel(
                brand="BMW", brand_zh="寶馬", series="X3",
                name="X3 sDrive20i", year=2026, trim_level="標準版",
                body_type="SUV", msrp=2550000,
                engine_type="2.0L 直列四缸 渦輪增壓",
                displacement_cc=1998, horsepower=190, torque_kgm=31.6,
                fuel_type="gasoline", forced_induction="turbo",
                transmission="Steptronic 8速手自排", drivetrain="FR",
                length_mm=4755, width_mm=1920, height_mm=1660,
                wheelbase_mm=2865, curb_weight_kg=1790,
                cargo_volume_liters=570, seats=5,
                zero_to_hundred=8.0, fuel_economy_combined=13.0,
                airbag_count=7, adas_level="BMW Personal CoPilot 全速域ACC",
                warranty_years=3,
                features="全速域ACC,車道維持,AEB自動緊急煞車,BSM盲點偵測,7具氣囊,電動尾門,雙前座電動椅,12.3吋觸控螢幕,無線Apple CarPlay,環景影像,HUD抬頭顯示",
            ),
        ]

        db.add_all(cars)
        await db.commit()
        print(f"✅ 已灌入 {len(cars)} 筆車型資料！")
        for i, c in enumerate(cars, 1):
            print(f"   ID={i}: {c.brand} {c.name} - {c.msrp/10000:.0f}萬")


# 讓 uvicorn 可以直接 python app/main.py 啟動
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
