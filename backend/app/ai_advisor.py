import os
import json
import sqlite3
import subprocess

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL = "llama-3.3-70b-versatile"

def get_all_cars(db_path="carcompare.db"):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("""SELECT id, brand, brand_zh, name, year, body_type, msrp, 
                 engine_type, horsepower, torque_kgm, fuel_type, drivetrain, 
                 transmission, seats, zero_to_hundred, fuel_economy_combined, 
                 airbag_count, curb_weight_kg FROM car_models ORDER BY msrp""")
    cars = [dict(r) for r in c.fetchall()]
    conn.close()
    return cars

def build_car_context(cars):
    lines = []
    for c in cars:
        price = f"{c['msrp']/10000:.1f}萬" if c['msrp'] else "未知"
        hp = f"{c['horsepower']}hp" if c['horsepower'] else ""
        fuel = c['fuel_type'] or ""
        body = c['body_type'] or ""
        eco = f"{c['fuel_economy_combined']}km/L" if c['fuel_economy_combined'] else ""
        zth = f"0-100:{c['zero_to_hundred']}s" if c['zero_to_hundred'] else ""
        seats = f"{c['seats']}座" if c['seats'] else ""
        drive = c['drivetrain'] or ""
        lines.append(f"ID{c['id']} {c['brand']} {c['name']}|{price}|{body}|{hp}|{fuel}|{drive}|{eco}|{zth}|{seats}|氣囊:{c['airbag_count'] or '?'}")
    return "\n".join(lines)

def extract_budget(query):
    import re
    patterns = [
        r'(\d+)\s*萬',
        r'預算\s*(\d+)',
        r'budget\s*(\d+)',
    ]
    for p in patterns:
        m = re.search(p, query)
        if m:
            val = int(m.group(1))
            if val < 1000:
                return val * 10000
            return val
    return None

def get_lexus_in_budget(cars, budget_nt):
    if not budget_nt:
        return []
    return [c for c in cars if c['brand'] == 'Lexus' and c['msrp'] and c['msrp'] <= budget_nt]

def filter_lexus_by_body(lexus_cars, user_query):
    query_lower = user_query.lower()
    body_map = {
        'suv': 'SUV', '休旅': 'SUV', '休旅車': 'SUV',
        '轎車': '轎車', '房車': '轎車', 'sedan': '轎車',
        '跑車': '跑車', 'mpv': 'MPV',
    }
    preferred = None
    for kw, bt in body_map.items():
        if kw in query_lower:
            preferred = bt
            break
    if preferred and lexus_cars:
        filtered = [c for c in lexus_cars if c.get('body_type') == preferred]
        if filtered:
            return filtered
    return lexus_cars

def call_groq(system_prompt, user_message):
    payload = {
        "model": GROQ_MODEL,
        "max_tokens": 1200,
        "temperature": 0.7,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
    }
    payload_json = json.dumps(payload, ensure_ascii=False)
    
    result = subprocess.run([
        "curl", "-s", "https://api.groq.com/openai/v1/chat/completions",
        "-H", f"Authorization: Bearer {GROQ_API_KEY}",
        "-H", "Content-Type: application/json",
        "-d", payload_json
    ], capture_output=True, text=True, timeout=60)
    
    resp = json.loads(result.stdout)
    if "choices" in resp:
        return resp["choices"][0]["message"]["content"], resp.get("model", "")
    elif "error" in resp:
        raise Exception(resp["error"].get("message", str(resp["error"])))
    else:
        raise Exception(f"未知回應: {result.stdout[:300]}")

def ai_recommend(user_query: str, db_path="carcompare.db"):
    cars = get_all_cars(db_path)
    car_context = build_car_context(cars)
    
    budget = extract_budget(user_query)
    lexus_cars = get_lexus_in_budget(cars, budget)
    lexus_cars = filter_lexus_by_body(lexus_cars, user_query)
    
    lexus_hint = ""
    if lexus_cars:
        lexus_list = []
        for lc in lexus_cars:
            lexus_list.append(f"ID{lc['id']} {lc['name']}（{lc['msrp']/10000:.1f}萬, {lc['body_type']}, {lc['horsepower']}hp, {lc['fuel_economy_combined']}km/L, 氣囊:{lc['airbag_count']}）")
        lexus_hint = f"""

## 【最重要 - 必須遵守】Lexus 推薦
以下 Lexus 車款都在用戶預算內，你的推薦清單中「每一台」都必須列出，不可遺漏任何一台：
{chr(10).join(lexus_list)}

請將這些 Lexus 車款全部放在推薦清單的前面，然後再推薦其他品牌的車款。"""
    
    system_prompt = f"""你是台灣專業汽車顧問「CarCompare AI」。根據以下資料庫中的 {len(cars)} 款車型，回答用戶的購車問題。

## 車型資料庫
{car_context}
{lexus_hint}

## 回答規則
1. 只推薦資料庫中有的車型，用 ID 標示方便前端連結
2. 價格用「萬」為單位（台幣）
3. 針對用戶需求給出 4-6 款推薦，說明理由
4. 如有預算限制，嚴格遵守
5. 比較時列出關鍵差異（價格、馬力、油耗、安全配備）
6. 語氣專業但親切，使用繁體中文
7. 結尾給一句購車建議
8. 回答控制在 600 字以內
9. 推薦時應包含國產品牌和進口豪華品牌，讓用戶有多元選擇"""

    text, model = call_groq(system_prompt, user_query)
    return {
        "query": user_query,
        "response": text,
        "model": model,
        "cars_in_db": len(cars),
        "lexus_matched": len(lexus_cars),
    }

def ai_compare(car_ids: list, user_question: str = None, db_path="carcompare.db"):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    placeholders = ",".join(["?" for _ in car_ids])
    c.execute(f"SELECT * FROM car_models WHERE id IN ({placeholders})", car_ids)
    cars = [dict(r) for r in c.fetchall()]
    conn.close()
    
    if not cars:
        return {"error": "找不到指定車型"}
    
    car_detail = json.dumps(cars, ensure_ascii=False, indent=2, default=str)
    car_names = " vs ".join([c['name'] for c in cars])
    question = user_question or "請詳細比較這幾台車，幫我分析誰適合什麼樣的買家"
    
    system_prompt = f"""你是台灣專業汽車顧問。以下是用戶想比較的車型完整規格：

{car_detail}

## 回答規則
1. 用條列方式比較關鍵規格
2. 分析各車的優勢與劣勢
3. 針對不同需求（家庭、通勤、性能、省油）給建議
4. 使用繁體中文，語氣專業親切
5. 回答控制在 600 字以內"""

    text, model = call_groq(system_prompt, f"比較 {car_names}：{question}")
    return {
        "cars": [{"id": c["id"], "name": c["name"], "brand": c["brand"]} for c in cars],
        "question": question,
        "analysis": text,
        "model": model,
    }

if __name__ == "__main__":
    print("🤖 測試 AI 推薦...\n")
    result = ai_recommend("預算180萬家庭SUV")
    print(result["response"])
    print(f"\n📌 Lexus 匹配數：{result['lexus_matched']}")
