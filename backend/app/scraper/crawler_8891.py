"""
8891 新車爬蟲 - 從品牌頁面抓取車款清單和價格
"""
import re
import json
import sqlite3
import urllib.request
import time

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# 台灣市場主要品牌 (品牌URL名, 中文名)
BRANDS = [
    ("toyota", "豐田"), ("honda", "本田"), ("nissan", "日產"),
    ("mazda", "馬自達"), ("mitsubishi", "三菱"), ("suzuki", "鈴木"),
    ("ford", "福特"), ("hyundai", "現代"), ("kia", "起亞"),
    ("volkswagen", "福斯"), ("skoda", "Skoda"), ("subaru", "速霸陸"),
    ("lexus", "凌志"), ("mercedes-benz", "賓士"), ("bmw", "寶馬"),
    ("audi", "奧迪"), ("volvo", "富豪"), ("porsche", "保時捷"),
    ("mini", "Mini"), ("tesla", "特斯拉"), ("mg", "MG"),
    ("peugeot", "寶獅"),
]

def fetch_page(url):
    """抓取網頁內容"""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read().decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"  ❌ 抓取失敗: {e}")
        return None

def parse_brand_page(html, brand_url, brand_zh):
    """
    從 8891 品牌頁面的 HTML 解析車款資訊
    頁面結構: 車款名 + 價格範圍 (XX.X-XX.X萬)
    """
    cars = []

    # 取得品牌英文名（首字大寫）
    brand_en = brand_url.replace("-", " ").title().replace(" ", "-")
    # 特殊品牌名修正
    name_map = {
        "Mercedes-Benz": "Mercedes-Benz",
        "Bmw": "BMW",
        "Mg": "MG",
        "Kia": "Kia",
        "Mini": "Mini",
        "Tesla": "Tesla",
    }
    brand_en = name_map.get(brand_en, brand_en)

    # 方法1: 從 HTML 文字中找車款名和價格
    # 8891 品牌頁格式: "Toyota RAV4" 接著 "104.0-139.0萬"
    # 嘗試找 "品牌 車名\n\n價格範圍萬" 的模式
    pattern = rf'({re.escape(brand_en)}\s+[\w\s\-\.]+?)(?:\n|\r).*?(\d+\.?\d*)\s*(?:-\s*(\d+\.?\d*))?\s*萬'
    matches = re.findall(pattern, html, re.DOTALL)

    if not matches:
        # 方法2: 更寬鬆的模式 - 找所有 "XX.X-XX.X萬" 或 "XX.X萬"
        # 先找所有看起來像車名的文字
        lines = html.split('\n')
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            # 找包含品牌名的行
            if brand_en.lower() in line.lower() and len(line) < 80:
                car_name = line.strip()
                # 往下找價格
                for j in range(i+1, min(i+5, len(lines))):
                    price_match = re.search(r'(\d+\.?\d*)\s*(?:-\s*(\d+\.?\d*))?\s*萬', lines[j])
                    if price_match:
                        low = float(price_match.group(1))
                        high = float(price_match.group(2)) if price_match.group(2) else low
                        cars.append({
                            "brand": brand_en,
                            "brand_zh": brand_zh,
                            "name": car_name,
                            "price_low_wan": low,
                            "price_high_wan": high,
                        })
                        break
            i += 1

    if not cars and matches:
        for m in matches:
            name = m[0].strip()
            low = float(m[1])
            high = float(m[2]) if m[2] else low
            cars.append({
                "brand": brand_en,
                "brand_zh": brand_zh,
                "name": name,
                "price_low_wan": low,
                "price_high_wan": high,
            })

    return cars

def crawl_all_brands():
    """爬取所有品牌的車款清單"""
    all_cars = []

    for brand_url, brand_zh in BRANDS:
        url = f"https://c.8891.com.tw/Models/{brand_url}"
        print(f"\n🔍 抓取 {brand_zh} ({brand_url})...")
        html = fetch_page(url)
        if not html:
            continue

        cars = parse_brand_page(html, brand_url, brand_zh)
        if cars:
            for c in cars:
                print(f"  ✅ {c['name']} - {c['price_low_wan']:.1f}~{c['price_high_wan']:.1f} 萬")
            all_cars.extend(cars)
        else:
            print(f"  ⚠️ 未找到車款資料 (頁面可能是動態載入)")

        time.sleep(1)  # 禮貌性延遲

    return all_cars

def update_prices_in_db(cars, db_path="carcompare.db"):
    """更新資料庫中已存在車款的價格"""
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    updated = 0
    for car in cars:
        # 用品牌名 + 車系模糊比對
        brand = car["brand"]
        name = car["name"]
        # 取出車系名 (例如 "Toyota RAV4" -> "RAV4")
        series = name.replace(brand, "").strip()

        # 找資料庫中匹配的車款
        c.execute("""
            SELECT id, name, msrp FROM car_models
            WHERE brand = ? AND (series LIKE ? OR name LIKE ?)
        """, (brand, f"%{series}%", f"%{series}%"))

        rows = c.fetchall()
        if rows:
            # 用最低價更新（如果價格有變化）
            new_price = int(car["price_low_wan"] * 10000)
            for row in rows:
                db_id, db_name, db_msrp = row
                if db_msrp != new_price:
                    print(f"  💰 價格更新: {db_name} {db_msrp:,} → {new_price:,}")
                    c.execute("UPDATE car_models SET msrp = ? WHERE id = ?", (new_price, db_id))
                    updated += 1
                else:
                    print(f"  ✔️ 價格不變: {db_name} {db_msrp:,}")

    conn.commit()
    conn.close()
    return updated

if __name__ == "__main__":
    print("=" * 60)
    print("🚗 8891 新車爬蟲啟動")
    print("=" * 60)

    cars = crawl_all_brands()

    print(f"\n{'=' * 60}")
    print(f"📊 共抓取 {len(cars)} 筆車款資料")
    print(f"{'=' * 60}")

    if cars:
        print(f"\n📝 更新資料庫價格...")
        updated = update_prices_in_db(cars)
        print(f"\n✅ 完成！更新了 {updated} 筆價格")

    # 顯示抓到的所有車款
    print(f"\n{'=' * 60}")
    print("📋 完整車款清單:")
    print(f"{'=' * 60}")
    for i, car in enumerate(cars, 1):
        print(f"{i:3d}. {car['brand']:15s} {car['name']:30s} {car['price_low_wan']:>7.1f} ~ {car['price_high_wan']:>7.1f} 萬")
