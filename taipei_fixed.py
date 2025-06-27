import requests
import time
import csv
import os
import re
import logging
from datetime import datetime
from dotenv import load_dotenv

# ✅ 1. 從環境變數讀取 API 金鑰
try:
    load_dotenv()
    API_KEY = os.getenv('API_KEY')
except Exception as e:
    print(f"❌ 載入 .env 檔案時發生錯誤：{e}")
    exit(1)

if not API_KEY:
    print("❌ 未找到 API_KEY")
    print("💡 請建立 .env 檔案並填入 API_KEY")
    exit(1)

# ✅ 2. 設定 Log 記錄
def setup_logging():
    if not os.path.exists('logs'):
        os.makedirs('logs')
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"logs/taipei_scraper_{timestamp}.log"
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_filename, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logging()

# ✅ 3. 台北市行政區座標
area_keywords = [
    ("中正區", "25.0330,121.5183", "台北市"),
    ("大同區", "25.0633,121.5130", "台北市"),
    ("中山區", "25.0636,121.5264", "台北市"),
    ("松山區", "25.0576,121.5776", "台北市"),
    ("大安區", "25.0267,121.5436", "台北市"),
    ("萬華區", "25.0374,121.4991", "台北市"),
    ("信義區", "25.0330,121.5654", "台北市"),
    ("士林區", "25.0877,121.5258", "台北市"),
    ("北投區", "25.1315,121.5017", "台北市"),
    ("內湖區", "25.0692,121.5897", "台北市"),
    ("南港區", "25.0478,121.6073", "台北市"),
    ("文山區", "24.9876,121.5707", "台北市"),
]

# ✅ 4. 搜尋關鍵字
search_keywords = [
    # 美甲類
    "美甲", "光療指甲", "凝膠美甲", "日式美甲", "nail", "美甲美睫",
    # 美睫類  
    "美睫", "嫁接睫毛", "種睫毛", "睫毛延伸", "eyelash",
    # 耳燭類
    "耳燭", "耳燭療程", "耳燭SPA", "ear candling",
    # 採耳類
    "採耳", "掏耳", "耳部清潔", "耳SPA", "ear cleaning",
    # 熱蠟類
    "熱蠟", "熱蠟除毛", "蜜蠟除毛", "比基尼熱蠟", "私密處除毛", "waxing"
]

# ✅ 5. 搜尋函數
def search_places(keyword, location, radius=3000):
    """整合搜尋函數，結合文字搜尋和附近搜尋"""
    all_results = []
    seen_ids = set()
    
    # 文字搜尋
    text_url = 'https://maps.googleapis.com/maps/api/place/textsearch/json'
    text_params = {
        'key': API_KEY,
        'query': f"{keyword} near {location}",
        'location': location,
        'radius': radius,
        'language': 'zh-TW',
        'type': 'beauty_salon|spa|hair_care'
    }
    
    try:
        text_res = requests.get(text_url, params=text_params).json()
        if text_res.get('status') == 'OK':
            for place in text_res.get('results', []):
                if place['place_id'] not in seen_ids:
                    seen_ids.add(place['place_id'])
                    all_results.append(place)
    except Exception as e:
        logger.error(f"文字搜尋失敗: {e}")
    
    # 附近搜尋
    nearby_url = 'https://maps.googleapis.com/maps/api/place/nearbysearch/json'
    nearby_params = {
        'key': API_KEY,
        'location': location,
        'radius': radius,
        'keyword': keyword,
        'language': 'zh-TW',
        'type': 'beauty_salon|spa|hair_care'
    }
    
    try:
        nearby_res = requests.get(nearby_url, params=nearby_params).json()
        if nearby_res.get('status') == 'OK':
            for place in nearby_res.get('results', []):
                if place['place_id'] not in seen_ids:
                    seen_ids.add(place['place_id'])
                    all_results.append(place)
    except Exception as e:
        logger.error(f"附近搜尋失敗: {e}")
    
    return all_results

# ✅ 6. 地理過濾
def filter_by_location(places, target_city):
    """過濾符合目標城市的地點"""
    city_variants = [
        target_city,
        target_city.replace("台", "臺"),
        target_city.replace("臺", "台"),
        target_city.replace("市", ""),
        "Taipei"
    ]
    
    filtered = []
    for place in places:
        address = place.get('formatted_address', place.get('vicinity', '')).lower()
        name = place.get('name', '').lower()
        
        if any(variant.lower() in address.lower() or variant.lower() in name.lower() 
               for variant in city_variants):
            filtered.append(place)
    
    return filtered

# ✅ 7. 業務相關性過濾
def filter_by_relevance(places):
    """過濾相關的美容業務"""
    relevant_keywords = [
        '美甲', '光療', '凝膠', 'nail', '美睫', '睫毛', 'lash',
        '耳燭', '採耳', '掏耳', '除毛', 'wax', '熱蠟', '蜜蠟'
    ]
    
    exclude_keywords = [
        '醫院', '診所', '藥局', '銀行', '超商', '便利商店',
        '加油站', '餐廳', '小吃', '飲料', '火鍋'
    ]
    
    filtered = []
    for place in places:
        name = place.get('name', '').lower()
        
        # 如果包含相關關鍵字，直接加入
        if any(keyword in name for keyword in relevant_keywords):
            filtered.append(place)
            continue
        
        # 如果包含排除關鍵字，跳過
        if any(keyword in name for keyword in exclude_keywords):
            continue
        
        # 檢查 place types
        types = place.get('types', [])
        if 'beauty_salon' in types or 'spa' in types or 'hair_care' in types:
            filtered.append(place)
    
    return filtered

# ✅ 8. 獲取詳細資訊
def get_place_details(place_id):
    """獲取地點的詳細資訊"""
    url = 'https://maps.googleapis.com/maps/api/place/details/json'
    params = {
        'key': API_KEY,
        'place_id': place_id,
        'language': 'zh-TW',
        'fields': 'name,formatted_address,formatted_phone_number,website,reviews'
    }
    
    try:
        res = requests.get(url, params=params).json()
        if res.get('status') == 'OK':
            return res.get('result', {})
    except Exception as e:
        logger.error(f"獲取詳細資訊失敗: {e}")
    
    return {}

# ✅ 9. 主要搜尋流程
def search_area(area_name, location, city):
    """搜尋特定區域的店家"""
    logger.info(f"開始搜尋: {city} {area_name}")
    all_results = []
    seen_ids = set()
    
    for keyword in search_keywords:
        logger.info(f"搜尋關鍵字: {keyword}")
        
        # 搜尋店家
        places = search_places(keyword, location)
        if not places:
            continue
        
        # 過濾結果
        places = filter_by_location(places, city)
        places = filter_by_relevance(places)
        
        # 去重並添加到結果
        for place in places:
            if place['place_id'] not in seen_ids:
                seen_ids.add(place['place_id'])
                
                # 獲取詳細資訊
                details = get_place_details(place['place_id'])
                if details:
                    place.update(details)
                
                all_results.append(place)
                logger.info(f"找到店家: {place.get('name')}")
        
        time.sleep(1)  # 避免超過 API 限制
    
    return all_results

# ✅ 10. 保存結果
def save_results(results, filename="taipei_beauty_shops.csv"):
    """保存結果到 CSV 文件"""
    with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=[
            '縣市', '區域', '店名', '地址', '電話', '網站', '地圖連結'
        ])
        writer.writeheader()
        
        for place in results:
            writer.writerow({
                '縣市': place.get('city', '台北市'),
                '區域': place.get('area', ''),
                '店名': place.get('name', ''),
                '地址': place.get('formatted_address', place.get('vicinity', '')),
                '電話': place.get('formatted_phone_number', 'N/A'),
                '網站': place.get('website', 'N/A'),
                '地圖連結': f"https://www.google.com/maps/place/?q=place_id:{place['place_id']}"
            })

# ✅ 11. 主程序
def main():
    logger.info("開始搜尋台北市美容相關店家")
    all_results = []
    
    for area_name, location, city in area_keywords:
        try:
            results = search_area(area_name, location, city)
            for result in results:
                result['city'] = city
                result['area'] = area_name
            all_results.extend(results)
            
            logger.info(f"{city} {area_name} 找到 {len(results)} 家店")
            time.sleep(2)  # 避免超過 API 限制
            
        except Exception as e:
            logger.error(f"搜尋 {city} {area_name} 時發生錯誤: {e}")
    
    logger.info(f"總共找到 {len(all_results)} 家店")
    save_results(all_results)
    logger.info("搜尋完成，結果已保存")

if __name__ == '__main__':
    main() 