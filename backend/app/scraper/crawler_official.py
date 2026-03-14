"""
台灣汽車官網爬蟲 - 從各品牌官方網站抓取車款與價格
支援: Toyota, Mazda, Kia + 手動維護其他品牌
"""
import re
import json
import sqlite3
import urllib.request
import time
from datetime import datetime

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.read().decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"  ❌ {url}: {e}")
        return None

# ============ Toyota ============
def crawl_toyota():
    print("\n🔍 [Toyota] 抓取官網...")
    html = fetch("https://www.toyota.com.tw/showroom/")
    if not html:
        return []
    cars = []
    pattern = r'<h4>(.*?)</h4>\s*<span\s+class=["\']price["\']>\s*\$?([\d\.]+)\s*[~\-]\s*([\d\.]+)\s*萬'
    seen = set()
    for m in re.finditer(pattern, html, re.DOTALL):
        name = m.group(1).strip()
        if name in seen:
            continue
        seen.add(name)
        low = float(m.group(2))
        high = float(m.group(3))
        cars.append({"brand": "Toyota", "brand_zh": "豐田", "series": name,
                      "name": f"Toyota {name}", "price_low": low, "price_high": high})
    print(f"  ✅ 找到 {len(cars)} 款")
    return cars

# ============ Mazda ============
def crawl_mazda():
    print("\n🔍 [Mazda] 抓取官網...")
    html = fetch("https://www.mazda.com.tw/cars/")
    if not html:
        return []
    cars = []
    seen = set()
    # Mazda 頁面有 JSON: "model":"MAZDA CX-5","category":"","price":1049000.0
    for m in re.finditer(r'"model"\s*:\s*"([^"]+)"[^}]*?"price"\s*:\s*([\d\.]+)', html):
        name = m.group(1).strip()
        price = float(m.group(2))
        # 用大寫版本去重
        key = name.upper()
        if key in seen or price < 100000:
            continue
        seen.add(key)
        price_wan = price / 10000
        # 標準化名稱
        display_name = name.upper() if name[0].islower() else name
        cars.append({"brand": "Mazda", "brand_zh": "馬自達", "series": display_name,
                      "name": f"Mazda {display_name}", "price_low": price_wan, "price_high": price_wan})
    print(f"  ✅ 找到 {len(cars)} 款")
    return cars

# ============ Kia ============
def crawl_kia():
    print("\n🔍 [Kia] 抓取官網...")
    html = fetch("https://www.kia.com/tw/cars.html")
    if not html:
        return []
    cars = []
    # Kia 的車名能抓到，價格從已知資料補充
    kia_prices = {
        "Picanto": 59.9, "Stonic": 79.9, "Sportage": 109.9,
        "Carnival": 169.9, "EV6": 199.9, "EV9": 249.9,
    }
    seen = set()
    for m in re.finditer(r'(?:Sportage|Stonic|EV\d|Carnival|Picanto|Sorento|Niro)', html, re.I):
        name = m.group(0).title()
        if name in seen:
            continue
        seen.add(name)
        price = kia_prices.get(name, 0)
        if price > 0:
            cars.append({"brand": "Kia", "brand_zh": "起亞", "series": name,
                          "name": f"Kia {name}", "price_low": price, "price_high": price})
    print(f"  ✅ 找到 {len(cars)} 款")
    return cars

# ============ 手動維護的品牌最新價格 ============
# BMW, Benz, Audi, Volvo 官網都是 JS 動態渲染，無法靜態爬取
# 使用 2026 年 3 月台灣官方售價（來源: 8891, U-CAR, 各品牌官網公告）
MANUAL_CATALOG = [
    # === BMW ===
    {"brand": "BMW", "brand_zh": "寶馬", "series": "1 Series", "name": "BMW 120i M Sport", "price_low": 175.0, "price_high": 175.0,
     "body_type": "掀背", "engine": "1.5L 直列三缸 渦輪增壓", "hp": 156, "fuel": "汽油", "drive": "FF"},
    {"brand": "BMW", "brand_zh": "寶馬", "series": "2 Series Gran Coupe", "name": "BMW 220i M Sport", "price_low": 199.0, "price_high": 199.0,
     "body_type": "轎車", "engine": "2.0L 直列四缸 渦輪增壓", "hp": 170, "fuel": "汽油", "drive": "FF"},
    {"brand": "BMW", "brand_zh": "寶馬", "series": "3 Series", "name": "BMW 330i M Sport", "price_low": 289.0, "price_high": 289.0,
     "body_type": "轎車", "engine": "2.0L 直列四缸 渦輪增壓+48V", "hp": 245, "fuel": "油電混合", "drive": "RWD"},
    {"brand": "BMW", "brand_zh": "寶馬", "series": "5 Series", "name": "BMW 520i M Sport", "price_low": 299.0, "price_high": 299.0,
     "body_type": "轎車", "engine": "2.0L 直列四缸 渦輪增壓+48V", "hp": 190, "fuel": "油電混合", "drive": "RWD"},
    {"brand": "BMW", "brand_zh": "寶馬", "series": "X1", "name": "BMW X1 sDrive20i", "price_low": 199.0, "price_high": 199.0,
     "body_type": "SUV", "engine": "2.0L 直列四缸 渦輪增壓", "hp": 170, "fuel": "汽油", "drive": "FF"},
    {"brand": "BMW", "brand_zh": "寶馬", "series": "X3", "name": "BMW X3 xDrive20i", "price_low": 268.0, "price_high": 268.0,
     "body_type": "SUV", "engine": "2.0L 直列四缸 渦輪增壓+48V", "hp": 190, "fuel": "油電混合", "drive": "AWD"},
    {"brand": "BMW", "brand_zh": "寶馬", "series": "X5", "name": "BMW X5 xDrive30i", "price_low": 355.0, "price_high": 355.0,
     "body_type": "SUV", "engine": "2.0L 直列四缸 渦輪增壓+48V", "hp": 292, "fuel": "油電混合", "drive": "AWD"},
    {"brand": "BMW", "brand_zh": "寶馬", "series": "iX1", "name": "BMW iX1 xDrive30", "price_low": 239.0, "price_high": 239.0,
     "body_type": "SUV", "engine": "雙馬達電動", "hp": 313, "fuel": "純電動", "drive": "AWD"},
    {"brand": "BMW", "brand_zh": "寶馬", "series": "i4", "name": "BMW i4 eDrive40", "price_low": 279.0, "price_high": 279.0,
     "body_type": "轎車", "engine": "單馬達電動", "hp": 340, "fuel": "純電動", "drive": "RWD"},
    {"brand": "BMW", "brand_zh": "寶馬", "series": "i5", "name": "BMW i5 eDrive40", "price_low": 339.0, "price_high": 339.0,
     "body_type": "轎車", "engine": "單馬達電動", "hp": 340, "fuel": "純電動", "drive": "RWD"},

    # === Mercedes-Benz ===
    {"brand": "Mercedes-Benz", "brand_zh": "賓士", "series": "A-Class", "name": "M-Benz A 180", "price_low": 168.0, "price_high": 168.0,
     "body_type": "掀背", "engine": "1.3L 直列四缸 渦輪增壓", "hp": 136, "fuel": "汽油", "drive": "FF"},
    {"brand": "Mercedes-Benz", "brand_zh": "賓士", "series": "C-Class", "name": "M-Benz C 200", "price_low": 245.0, "price_high": 245.0,
     "body_type": "轎車", "engine": "1.5L 直列四缸 渦輪增壓+48V", "hp": 204, "fuel": "油電混合", "drive": "RWD"},
    {"brand": "Mercedes-Benz", "brand_zh": "賓士", "series": "C-Class", "name": "M-Benz C 300", "price_low": 285.0, "price_high": 285.0,
     "body_type": "轎車", "engine": "2.0L 直列四缸 渦輪增壓+48V", "hp": 258, "fuel": "油電混合", "drive": "RWD"},
    {"brand": "Mercedes-Benz", "brand_zh": "賓士", "series": "E-Class", "name": "M-Benz E 200", "price_low": 310.0, "price_high": 310.0,
     "body_type": "轎車", "engine": "2.0L 直列四缸 渦輪增壓+48V", "hp": 204, "fuel": "油電混合", "drive": "RWD"},
    {"brand": "Mercedes-Benz", "brand_zh": "賓士", "series": "GLA", "name": "M-Benz GLA 200", "price_low": 198.0, "price_high": 198.0,
     "body_type": "SUV", "engine": "1.3L 直列四缸 渦輪增壓", "hp": 163, "fuel": "汽油", "drive": "FF"},
    {"brand": "Mercedes-Benz", "brand_zh": "賓士", "series": "GLB", "name": "M-Benz GLB 200", "price_low": 218.0, "price_high": 218.0,
     "body_type": "SUV", "engine": "1.3L 直列四缸 渦輪增壓", "hp": 163, "fuel": "汽油", "drive": "FF"},
    {"brand": "Mercedes-Benz", "brand_zh": "賓士", "series": "GLC", "name": "M-Benz GLC 300 4MATIC", "price_low": 296.0, "price_high": 296.0,
     "body_type": "SUV", "engine": "2.0L 直列四缸 渦輪增壓+48V", "hp": 258, "fuel": "油電混合", "drive": "AWD"},
    {"brand": "Mercedes-Benz", "brand_zh": "賓士", "series": "GLE", "name": "M-Benz GLE 350 4MATIC", "price_low": 378.0, "price_high": 378.0,
     "body_type": "SUV", "engine": "2.0L 直列四缸 渦輪增壓+48V", "hp": 258, "fuel": "油電混合", "drive": "AWD"},
    {"brand": "Mercedes-Benz", "brand_zh": "賓士", "series": "EQA", "name": "M-Benz EQA 250+", "price_low": 229.0, "price_high": 229.0,
     "body_type": "SUV", "engine": "單馬達電動", "hp": 190, "fuel": "純電動", "drive": "FF"},
    {"brand": "Mercedes-Benz", "brand_zh": "賓士", "series": "EQB", "name": "M-Benz EQB 250+", "price_low": 249.0, "price_high": 249.0,
     "body_type": "SUV", "engine": "單馬達電動", "hp": 190, "fuel": "純電動", "drive": "FF"},

    # === Audi ===
    {"brand": "Audi", "brand_zh": "奧迪", "series": "A3", "name": "Audi A3 Sportback 35 TFSI", "price_low": 168.0, "price_high": 168.0,
     "body_type": "掀背", "engine": "1.5L 直列四缸 渦輪增壓+48V", "hp": 150, "fuel": "油電混合", "drive": "FF"},
    {"brand": "Audi", "brand_zh": "奧迪", "series": "A4", "name": "Audi A4 40 TFSI S line", "price_low": 239.0, "price_high": 239.0,
     "body_type": "轎車", "engine": "2.0L 直列四缸 渦輪增壓+48V", "hp": 204, "fuel": "油電混合", "drive": "FF"},
    {"brand": "Audi", "brand_zh": "奧迪", "series": "A6", "name": "Audi A6 40 TFSI S line", "price_low": 289.0, "price_high": 289.0,
     "body_type": "轎車", "engine": "2.0L 直列四缸 渦輪增壓+48V", "hp": 204, "fuel": "油電混合", "drive": "FF"},
    {"brand": "Audi", "brand_zh": "奧迪", "series": "Q2", "name": "Audi Q2 35 TFSI S line", "price_low": 165.0, "price_high": 165.0,
     "body_type": "SUV", "engine": "1.5L 直列四缸 渦輪增壓+48V", "hp": 150, "fuel": "油電混合", "drive": "FF"},
    {"brand": "Audi", "brand_zh": "奧迪", "series": "Q3", "name": "Audi Q3 35 TFSI S line", "price_low": 202.0, "price_high": 202.0,
     "body_type": "SUV", "engine": "1.5L 直列四缸 渦輪增壓+48V", "hp": 150, "fuel": "油電混合", "drive": "FF"},
    {"brand": "Audi", "brand_zh": "奧迪", "series": "Q5", "name": "Audi Q5 40 TFSI quattro", "price_low": 268.0, "price_high": 268.0,
     "body_type": "SUV", "engine": "2.0L 直列四缸 渦輪增壓+48V", "hp": 204, "fuel": "油電混合", "drive": "AWD"},
    {"brand": "Audi", "brand_zh": "奧迪", "series": "Q7", "name": "Audi Q7 45 TFSI quattro", "price_low": 358.0, "price_high": 358.0,
     "body_type": "SUV", "engine": "3.0L V6 渦輪增壓+48V", "hp": 340, "fuel": "油電混合", "drive": "AWD"},
    {"brand": "Audi", "brand_zh": "奧迪", "series": "e-tron GT", "name": "Audi e-tron GT", "price_low": 489.0, "price_high": 489.0,
     "body_type": "轎車", "engine": "雙馬達電動", "hp": 476, "fuel": "純電動", "drive": "AWD"},
    {"brand": "Audi", "brand_zh": "奧迪", "series": "Q4 e-tron", "name": "Audi Q4 e-tron 45", "price_low": 249.0, "price_high": 249.0,
     "body_type": "SUV", "engine": "單馬達電動", "hp": 286, "fuel": "純電動", "drive": "RWD"},

    # === Volvo ===
    {"brand": "Volvo", "brand_zh": "富豪", "series": "S60", "name": "Volvo S60 B4 Momentum", "price_low": 199.0, "price_high": 199.0,
     "body_type": "轎車", "engine": "2.0L 直列四缸 渦輪增壓+48V", "hp": 197, "fuel": "油電混合", "drive": "FF"},
    {"brand": "Volvo", "brand_zh": "富豪", "series": "S90", "name": "Volvo S90 B5 Momentum", "price_low": 265.0, "price_high": 265.0,
     "body_type": "轎車", "engine": "2.0L 直列四缸 渦輪增壓+48V", "hp": 250, "fuel": "油電混合", "drive": "FF"},
    {"brand": "Volvo", "brand_zh": "富豪", "series": "XC40", "name": "Volvo XC40 B4 Ultimate", "price_low": 199.0, "price_high": 199.0,
     "body_type": "SUV", "engine": "2.0L 直列四缸 渦輪增壓+48V", "hp": 197, "fuel": "油電混合", "drive": "FF"},
    {"brand": "Volvo", "brand_zh": "富豪", "series": "XC60", "name": "Volvo XC60 B5 Ultimate", "price_low": 253.0, "price_high": 253.0,
     "body_type": "SUV", "engine": "2.0L 直列四缸 渦輪增壓+48V", "hp": 250, "fuel": "油電混合", "drive": "AWD"},
    {"brand": "Volvo", "brand_zh": "富豪", "series": "XC90", "name": "Volvo XC90 B5 Momentum", "price_low": 289.0, "price_high": 289.0,
     "body_type": "SUV", "engine": "2.0L 直列四缸 渦輪增壓+48V", "hp": 250, "fuel": "油電混合", "drive": "AWD"},
    {"brand": "Volvo", "brand_zh": "富豪", "series": "EX30", "name": "Volvo EX30 Single Motor ER", "price_low": 149.9, "price_high": 149.9,
     "body_type": "SUV", "engine": "單馬達電動", "hp": 272, "fuel": "純電動", "drive": "RWD"},
    {"brand": "Volvo", "brand_zh": "富豪", "series": "EX40", "name": "Volvo EX40 Recharge", "price_low": 209.0, "price_high": 209.0,
     "body_type": "SUV", "engine": "單馬達電動", "hp": 238, "fuel": "純電動", "drive": "RWD"},
    {"brand": "Volvo", "brand_zh": "富豪", "series": "EC40", "name": "Volvo EC40 Recharge", "price_low": 219.0, "price_high": 219.0,
     "body_type": "轎跑SUV", "engine": "單馬達電動", "hp": 238, "fuel": "純電動", "drive": "RWD"},
]

def get_manual_catalog():
    """回傳手動維護的品牌資料"""
    print(f"\n📋 [手動目錄] BMW / M-Benz / Audi / Volvo")
    print(f"  ✅ 共 {len(MANUAL_CATALOG)} 款")
    return MANUAL_CATALOG

# ============ 統一入口 ============
def crawl_all():
    all_cars = []

    # 自動爬蟲
    for crawler_fn in [crawl_toyota, crawl_mazda, crawl_kia]:
        try:
            cars = crawler_fn()
            for c in cars:
                print(f"  📌 {c['name']:35s} {c['price_low']:>7.1f} ~ {c['price_high']:>7.1f} 萬")
            all_cars.extend(cars)
        except Exception as e:
            print(f"  ❌ 爬蟲錯誤: {e}")
        time.sleep(1)

    # 手動目錄
    manual = get_manual_catalog()
    all_cars.extend(manual)

    # 去重
    seen = set()
    unique = []
    for c in all_cars:
        key = f"{c['brand']}_{c.get('series', c['name'])}".upper()
        if key not in seen:
            seen.add(key)
            unique.append(c)

    return unique

def sync_to_db(cars, db_path="carcompare.db"):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    updated = 0
    added = 0

    for car in cars:
        brand = car["brand"]
        series = car.get("series", "")
        name = car["name"]
        price_low = int(car["price_low"] * 10000)

        # 先找是否已存在（用名稱或系列匹配）
        c.execute("""
            SELECT id, name, msrp FROM car_models
            WHERE brand = ? AND (name = ? OR name LIKE ? OR series = ?)
        """, (brand, name, f"%{series}%", series))
        rows = c.fetchall()

        if rows:
            for row in rows:
                db_id, db_name, db_msrp = row
                if db_msrp and abs(db_msrp - price_low) > 10000:
                    print(f"  💰 更新: {db_name} {db_msrp:,} → {price_low:,}")
                    c.execute("UPDATE car_models SET msrp = ? WHERE id = ?", (price_low, db_id))
                    updated += 1
        else:
            # 新增
            body = car.get("body_type", "待確認")
            engine = car.get("engine", "")
            hp = car.get("hp", None)
            fuel = car.get("fuel", "")
            drive = car.get("drive", "")
            brand_zh = car.get("brand_zh", "")

            c.execute("""
                INSERT INTO car_models
                (brand, brand_zh, series, name, year, body_type, msrp,
                 engine_type, horsepower, fuel_type, drivetrain, seats)
                VALUES (?, ?, ?, ?, 2026, ?, ?, ?, ?, ?, ?, 5)
            """, (brand, brand_zh, series, name, body, price_low,
                  engine, hp, fuel, drive))
            added += 1
            print(f"  🆕 新增: {name} {price_low:,} 元 ({body}/{fuel})")

    conn.commit()
    c.execute("SELECT COUNT(*) FROM car_models")
    total = c.fetchone()[0]
    conn.close()
    return {"updated": updated, "added": added, "total_in_db": total}

def update_latest_prices(db_path="carcompare.db"):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    latest = {
        "Corolla Cross 油電旗艦": 1059000, "RAV4 2.0 旗艦版": 1130000,
        "Camry 2.5 Hybrid旗艦": 1520000, "CR-V VTi-S": 1155000,
        "HR-V S": 899000, "Civic e:HEV": 1199000,
        "NX 200 豪華版": 1710000, "NX 350h 旗艦版": 2520000,
        "GLC 200 4MATIC": 2660000, "C 200 Avantgarde": 2450000,
        "X3 sDrive20i": 2550000, "320i M Sport": 2550000,
        "iX1 xDrive30": 2390000, "CX-5 旗艦進化型": 1290000,
        "CX-30 旗艦進化型": 1130000, "Mazda 3 5D旗艦進化型": 1029000,
        "MG ZS 1.5旗艦版": 699000, "MG HS 1.5T旗艦版": 899000,
        "MG4 XPower": 1099000, "Model Y Long Range": 1999900,
        "Model 3 Long Range": 1879900, "XC40 B4 Momentum": 1890000,
        "XC60 B5 Momentum": 2360000, "EX30 Single Motor ER": 1499000,
        "Q3 35 TFSI S line": 2020000, "Q5 40 TFSI quattro S line": 2680000,
        "Macan": 3030000, "Forester 2.0i-S EyeSight": 1290000,
        "Sportage 豪華版": 1249000, "Tucson L GLX-B": 1199000,
    }
    updated = 0
    for name, price in latest.items():
        c.execute("SELECT id, msrp FROM car_models WHERE name = ?", (name,))
        row = c.fetchone()
        if row and row[1] != price:
            c.execute("UPDATE car_models SET msrp = ? WHERE id = ?", (price, row[0]))
            updated += 1
    conn.commit()
    conn.close()
    return updated

if __name__ == "__main__":
    print("=" * 60)
    print("🚗 台灣汽車官網爬蟲 v2")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    cars = crawl_all()

    print(f"\n{'=' * 60}")
    print(f"📊 共抓取/載入 {len(cars)} 筆車款")

    if cars:
        print(f"\n📝 同步到資料庫...")
        result = sync_to_db(cars)
        print(f"\n📊 更新 {result['updated']} 筆 / 新增 {result['added']} 筆 / 資料庫共 {result['total_in_db']} 筆")

    update_latest_prices()

    print(f"\n{'=' * 60}")
    print("📋 資料庫完整清單:")
    print(f"{'=' * 60}")
    conn = sqlite3.connect("carcompare.db")
    cur = conn.cursor()
    cur.execute("SELECT brand, COUNT(*), MIN(msrp), MAX(msrp) FROM car_models GROUP BY brand ORDER BY brand")
    for row in cur.fetchall():
        lo = f"{row[2]/10000:.1f}" if row[2] else "N/A"
        hi = f"{row[3]/10000:.1f}" if row[3] else "N/A"
        print(f"  {row[0]:18s}: {row[1]:3d} 款  ({lo} ~ {hi} 萬)")
    cur.execute("SELECT COUNT(*) FROM car_models")
    total = cur.fetchone()[0]
    conn.close()
    print(f"\n  {'總計':18s}: {total} 款")
