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
except UnicodeDecodeError:
    print("❌ .env 檔案編碼錯誤，請確保檔案使用 UTF-8 編碼")
    print("💡 解決方案：")
    print("   1. 刪除現有的 .env 檔案")
    print("   2. 建立新的 .env 檔案，內容如下：")
    print("   API_KEY=您的Google_Places_API_Key")
    print("   3. 確保檔案保存為 UTF-8 編碼")
    exit(1)
except Exception as e:
    print(f"❌ 載入 .env 檔案時發生錯誤：{e}")
    exit(1)

if not API_KEY:
    print("❌ 未找到 API_KEY")
    print("💡 請建立 .env 檔案，內容如下：")
    print("API_KEY=您的Google_Places_API_Key")
    
    # 嘗試建立 .env 檔案模板
    try:
        with open('.env', 'w', encoding='utf-8') as f:
            f.write('# Google Places API 金鑰\n')
            f.write('# 請將下面的 YOUR_API_KEY_HERE 替換為您的實際 API 金鑰\n')
            f.write('API_KEY=YOUR_API_KEY_HERE\n')
        print("✅ 已建立 .env 檔案模板，請編輯並填入您的 API 金鑰")
    except Exception as e:
        print(f"❌ 無法建立 .env 檔案：{e}")
    
    exit(1)

print(f"✅ API 金鑰載入成功：{API_KEY[:10]}...")

# ✅ 1.5. 設定 Log 記錄
def setup_logging():
    """設定 log 檔案和格式"""
    # 建立 logs 目錄
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    # 建立時間戳記的檔案名稱
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"logs/beauty_scraper_{timestamp}.log"
    
    # 設定 logging 格式
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_filename, encoding='utf-8'),
            logging.StreamHandler()  # 同時輸出到控制台
        ]
    )
    
    logger = logging.getLogger(__name__)
    logger.info("=" * 60)
    logger.info("🚀 開始執行美容店家搜尋程式")
    logger.info(f"📁 Log 檔案：{log_filename}")
    logger.info("=" * 60)
    
    return logger

# 初始化 logger
logger = setup_logging()

# ✅ 2. 台灣六都 + 屏東所有行政區中心座標 (擴大版)
area_keywords = [
    # 雲林縣
    ("斗六市", "23.7092,120.5430", "雲林縣"),
    ("斗南鎮", "23.6754,120.4804", "雲林縣"),
    ("虎尾鎮", "23.7071,120.4325", "雲林縣"),
    ("西螺鎮", "23.8005,120.4649", "雲林縣"),
    ("土庫鎮", "23.6789,120.3790", "雲林縣"),
    ("北港鎮", "23.5689,120.3036", "雲林縣"),
    ("古坑鄉", "23.6533,120.5894", "雲林縣"),
    ("大埤鄉", "23.6624,120.4476", "雲林縣"),
    ("莿桐鄉", "23.7567,120.5185", "雲林縣"),
    ("林內鄉", "23.7540,120.6172", "雲林縣"),
    ("二崙鄉", "23.7597,120.3967", "雲林縣"),
    ("崙背鄉", "23.7623,120.3485", "雲林縣"),
    ("麥寮鄉", "23.7801,120.2455", "雲林縣"),
    ("東勢鄉", "23.6980,120.2486", "雲林縣"),
    ("褒忠鄉", "23.7116,120.3125", "雲林縣"),
    ("臺西鄉", "23.6975,120.2024", "雲林縣"),
    ("元長鄉", "23.6465,120.3087", "雲林縣"),
    ("四湖鄉", "23.6287,120.2161", "雲林縣"),
    ("口湖鄉", "23.5878,120.1847", "雲林縣"),
    ("水林鄉", "23.5642,120.2316", "雲林縣"),
]




# ✅ 3. 提取LINE聯絡方式的函數
def extract_line_contact(text):
    """從文字中提取LINE聯絡方式"""
    if not text:
        return 'N/A'
    
    # 常見的LINE ID格式
    line_patterns = [
        r'line[：:]\s*@?([a-zA-Z0-9_.-]+)',
        r'line\s*id[：:]\s*@?([a-zA-Z0-9_.-]+)',
        r'@([a-zA-Z0-9_.-]+)',
        r'line[：:]\s*([a-zA-Z0-9_.-]+)',
        r'加line[：:]\s*@?([a-zA-Z0-9_.-]+)',
        r'加入line[：:]\s*@?([a-zA-Z0-9_.-]+)'
    ]
    
    text_lower = text.lower()
    for pattern in line_patterns:
        match = re.search(pattern, text_lower, re.IGNORECASE)
        if match:
            line_id = match.group(1)
            return f"@{line_id}" if not line_id.startswith('@') else line_id
    
    return 'N/A'

# ✅ 4. 搜尋附近店家（最多 60 筆） - NearbySearch
def search_places_nearby(keyword, location, radius):
    url = 'https://maps.googleapis.com/maps/api/place/nearbysearch/json'
    params = {
        'key': API_KEY,
        'location': location,
        'radius': radius,
        'keyword': keyword,
        'language': 'zh-TW'
    }

    results = []
    while True:
        res = requests.get(url, params=params).json()
        results.extend(res.get('results', []))

        next_page_token = res.get('next_page_token')
        if next_page_token:
            time.sleep(2)
            params['pagetoken'] = next_page_token
        else:
            break
    return results

# ✅ 4.1. 文字搜尋（正確設定地理範圍限制）
def search_places_text(keyword, location, radius):
    url = 'https://maps.googleapis.com/maps/api/place/textsearch/json'
    params = {
        'key': API_KEY,
        'query': keyword,  # ✅ 只使用關鍵字，不混入座標
        'location': location,  # ✅ 正確使用 location 參數
        'radius': radius,
        'language': 'zh-TW'
    }

    results = []
    while True:
        res = requests.get(url, params=params).json()
        results.extend(res.get('results', []))

        next_page_token = res.get('next_page_token')
        if next_page_token:
            time.sleep(2)
            params['pagetoken'] = next_page_token
        else:
            break
    return results

# ✅ 4.2. 擴大搜尋策略 - 增加店家數量
def search_places_comprehensive_expanded(keywords, location, radius, area_name, city):
    """擴大的搜尋策略：更多關鍵字、更寬鬆的地理限制"""
    all_results = []
    seen_place_ids = set()  # 早期去重，避免重複處理相同店家
    
    # 解析中心座標
    center_lat, center_lng = map(float, location.split(','))
    
    logger.info(f"   🔎 擴大搜尋策略啟用")
    logger.info(f"   📍 搜尋中心：{area_name}, {city} ({location})")
    print(f"   🔎 擴大搜尋策略 - 目標：更多店家")
    
    # 方法1: 廣泛的美容相關搜尋
    broad_keywords = [
        # 美甲類
        "美甲", "光療指甲", "凝膠美甲", "日式美甲", "手足保養", "手足護理", "手部保養",
        # 美睫類  
        "美睫", "嫁接睫毛", "種睫毛", "睫毛延伸", "睫毛嫁接", "日式睫毛",
        # 耳燭類
        "耳燭", "耳燭療程", "耳燭SPA", "印度耳燭",
        # 採耳類
        "採耳", "掏耳", "耳部清潔", "耳SPA", "耳部護理",
        # 熱蠟類
        "熱蠟", "熱蠟除毛", "蜜蠟除毛", "比基尼熱蠟", "私密處除毛", "巴西除毛",
        # 美容相關
        "美容工作室", "美容SPA", "美容美體", "美容護膚", "臉部保養",
        # 台南在地用詞
        "美容美甲", "美甲美睫", "美容美睫", "美容工作室", "美甲工作室", "美睫工作室"
    ]
    
    for keyword in broad_keywords:
        try:
            # Text Search - 更廣範圍
            text_results = search_places_text(keyword, location, radius)
            geo_filtered = filter_by_location_relaxed(text_results, center_lat, center_lng, radius * 2, city)  # 地理過濾
            relevant_filtered = filter_by_business_relevance(geo_filtered)  # 業務相關性過濾
            
            for place in relevant_filtered:
                place_id = place.get('place_id')
                if place_id and place_id not in seen_place_ids:
                    seen_place_ids.add(place_id)
                    all_results.append(place)
            
            logger.info(f"      關鍵字 '{keyword}' (Text): 原始 {len(text_results)} → 地理過濾 {len(geo_filtered)} → 相關性過濾 {len(relevant_filtered)} 筆")
            time.sleep(0.5)
            
            # Nearby Search - 精確搜尋
            nearby_results = search_places_nearby(keyword, location, radius)
            geo_filtered = filter_by_location_relaxed(nearby_results, center_lat, center_lng, radius * 2, city)
            relevant_filtered = filter_by_business_relevance(geo_filtered)  # 業務相關性過濾
            
            for place in relevant_filtered:
                place_id = place.get('place_id')
                if place_id and place_id not in seen_place_ids:
                    seen_place_ids.add(place_id)
                    all_results.append(place)
            
            logger.info(f"      關鍵字 '{keyword}' (Nearby): 原始 {len(nearby_results)} → 地理過濾 {len(geo_filtered)} → 相關性過濾 {len(relevant_filtered)} 筆")
            time.sleep(0.5)
            
        except Exception as e:
            logger.error(f"      關鍵字 '{keyword}' 搜尋失敗：{e}")
    
    # 方法2: 使用 Place Types 搜尋
    try:
        beauty_types_results = search_by_place_types(location, radius)
        geo_filtered = filter_by_location_relaxed(beauty_types_results, center_lat, center_lng, radius * 2, city)
        relevant_filtered = filter_by_business_relevance(geo_filtered)  # 業務相關性過濾
        
        for place in relevant_filtered:
            place_id = place.get('place_id')
            if place_id and place_id not in seen_place_ids:
                seen_place_ids.add(place_id)
                all_results.append(place)
        
        logger.info(f"      類型搜尋: 原始 {len(beauty_types_results)} → 地理過濾 {len(geo_filtered)} → 相關性過濾 {len(relevant_filtered)} 筆")
    except Exception as e:
        logger.error(f"      類型搜尋失敗：{e}")
    
    logger.info(f"   🎯 {area_name} 總計找到 {len(all_results)} 間不重複店家")
    
    return all_results

# ✅ 4.2.1. 精確的 Place Types 搜尋
def search_by_place_types(location, radius):
    """使用 Google Places 的 type 參數搜尋美容相關店家"""
    url = 'https://maps.googleapis.com/maps/api/place/nearbysearch/json'
    
    # 只使用精確的美容相關 place types
    beauty_types = [
        'beauty_salon',  # 美容院
        'hair_care',     # 美髮護理  
        'spa'            # SPA
        # 移除 'establishment' - 太廣泛了
    ]
    
    all_results = []
    
    for place_type in beauty_types:
        params = {
            'key': API_KEY,
            'location': location,
            'radius': radius,
            'type': place_type,
            'language': 'zh-TW'
        }
        
        try:
            results = []
            while True:
                res = requests.get(url, params=params).json()
                results.extend(res.get('results', []))

                next_page_token = res.get('next_page_token')
                if next_page_token:
                    time.sleep(2)
                    params['pagetoken'] = next_page_token
                else:
                    break
            
            all_results.extend(results)
            time.sleep(1)
            
        except Exception as e:
            logger.error(f"類型 '{place_type}' 搜尋失敗：{e}")
    
    return all_results

# ✅ 4.2.2. 放寬的地理範圍過濾函數
def filter_by_location_relaxed(places, center_lat, center_lng, radius, target_city):
    """更寬鬆的地理範圍過濾"""
    import math
    
    def calculate_distance(lat1, lng1, lat2, lng2):
        """計算兩點間距離（公尺）"""
        R = 6371000  # 地球半徑（公尺）
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lng = math.radians(lng2 - lng1)
        
        a = (math.sin(delta_lat / 2) ** 2 + 
             math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lng / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        distance = R * c
        return distance
    
    filtered_places = []
    
    # 定義更寬鬆的城市名稱變體
    city_variants = [target_city]
    if "市" in target_city:
        city_variants.append(target_city.replace("市", ""))
    if "縣" in target_city:
        city_variants.append(target_city.replace("縣", ""))
    
    for place in places:
        # 更寬鬆的地址檢查
        address = place.get('formatted_address', place.get('vicinity', ''))
        
        # 檢查是否包含任何城市變體
        address_match = any(variant in address for variant in city_variants)
        
        if address_match:
            # 距離檢查（如果有座標）
            geometry = place.get('geometry', {})
            if geometry:
                location_data = geometry.get('location', {})
                place_lat = location_data.get('lat')
                place_lng = location_data.get('lng')
                
                if place_lat and place_lng:
                    distance = calculate_distance(center_lat, center_lng, place_lat, place_lng)
                    if distance <= radius * 2.5:  # 擴大到 2.5 倍範圍
                        filtered_places.append(place)
                else:
                    # 沒有座標但地址正確，也加入
                    filtered_places.append(place)
            else:
                # 沒有地理資訊但地址正確，也加入
                filtered_places.append(place)
        else:
            # 即使地址不完全匹配，如果距離很近也加入
            geometry = place.get('geometry', {})
            if geometry:
                location_data = geometry.get('location', {})
                place_lat = location_data.get('lat')
                place_lng = location_data.get('lng')
                
                if place_lat and place_lng:
                    distance = calculate_distance(center_lat, center_lng, place_lat, place_lng)
                    if distance <= radius:  # 在原始範圍內就加入
                        filtered_places.append(place)
    
    return filtered_places

# ✅ 4.2.3. 業務類型相關性過濾
def filter_by_business_relevance(places):
    """過濾掉不相關的業務類型"""
    
    # 美容相關關鍵字（店名中應該包含的）
    beauty_keywords = [
        '美甲', '光療指甲', '凝膠美甲', '日式美甲', '指甲', '手足保養', '手足護理',
        '美睫', '嫁接睫毛', '種睫毛', '睫毛延伸', '睫毛', '睫毛嫁接',
        '耳燭', '耳燭療程', '耳燭SPA', '印度耳燭',
        '採耳', '掏耳', '耳部清潔', '耳SPA', '耳部護理',
        '熱蠟', '熱蠟除毛', '蜜蠟除毛', '比基尼熱蠟', '私密處除毛', '除毛', '巴西除毛',
        '美容', '美體', '護膚', '保養', 'SPA', '工作室', '沙龍'
    ]
    
    # 排除的關鍵字（明顯不相關的業務）
    exclude_keywords = [
        '幼稚園', '學校', '醫院', '診所', '藥局', '銀行', '郵局',
        '超商', '便利商店', '7-11', '全家', '萊爾富', '加油站',
        '中油', '台塑', '修車', '汽車', '機車', '通訊', '手機',
        '電信', '網路', '餐廳', '小吃', '雞排', '飲料', '咖啡',
        '便當', '麵店', '火鍋', '燒烤', '公司', '企業', '工廠',
        '建設', '不動產', '房仲', '保險', '律師', '會計', '顧問'
    ]
    
    relevant_places = []
    
    for place in places:
        name = place.get('name', '').lower()
        address = place.get('formatted_address', place.get('vicinity', '')).lower()
        
        # 先檢查是否包含美容相關關鍵字
        is_beauty_related = any(beauty_keyword in name or beauty_keyword in address 
                               for beauty_keyword in beauty_keywords)
        
        # 檢查 Google Places 的 types（只保留精確的美容類型）
        place_types = place.get('types', [])
        has_beauty_type = any(ptype in ['beauty_salon', 'hair_care', 'spa'] 
                             for ptype in place_types)
        
        # 如果包含美容關鍵字或有美容類型，直接加入（優先級最高）
        if is_beauty_related or has_beauty_type:
            relevant_places.append(place)
            logger.info(f"      ✅ 美容相關店家：{place.get('name', '未知')}")
            continue
        
        # 如果不是美容相關，才檢查是否需要排除
        is_excluded = any(exclude_keyword in name or exclude_keyword in address 
                         for exclude_keyword in exclude_keywords)
        
        if is_excluded:
            logger.info(f"      ❌ 排除不相關店家：{place.get('name', '未知')}")
            continue
        else:
            # 既不是美容相關，也不需要排除的，也加入（可能是其他相關的店家）
            relevant_places.append(place)
    
    return relevant_places

# ✅ 4.3. 全局緩存機制
global_place_cache = {}  # place_id -> place_details 的緩存
global_seen_places = set()  # 全局已處理的 place_id

def get_place_details_cached(place_id):
    """帶緩存的店家詳細資訊獲取"""
    if place_id in global_place_cache:
        logger.info(f"      使用緩存資料：{place_id[:20]}...")
        return global_place_cache[place_id]
    
    # 如果沒有緩存，才發送API請求
    details = get_place_details(place_id)
    global_place_cache[place_id] = details
    return details

# ✅ 5. 取得店家詳細資訊（含電話、網站、評論等）
def get_place_details(place_id):
    url = 'https://maps.googleapis.com/maps/api/place/details/json'
    params = {
        'key': API_KEY,
        'place_id': place_id,
        'language': 'zh-TW',
        'fields': 'name,formatted_address,formatted_phone_number,website,reviews,editorial_summary'
    }
    res = requests.get(url, params=params).json()
    return res.get('result', {})

# ✅ 6. 去重複功能
def deduplicate_places(places):
    """根據 place_id 去除重複店家"""
    seen_ids = set()
    unique_places = []
    
    for place in places:
        place_id = place.get('place_id')
        if place_id and place_id not in seen_ids:
            seen_ids.add(place_id)
            unique_places.append(place)
    
    return unique_places

# ✅ 7. 擴大版主程式：更多店家
def run_search_all_areas(keywords=None, radius=15000):  # 預設擴大半徑到 15km
    all_results = []
    total_areas = len(area_keywords)
    api_request_count = 0  # 追踪API請求次數
    
    logger.info(f"🎯 擴大搜尋策略啟用")
    logger.info(f"📏 搜尋半徑：{radius} 公尺")
    logger.info(f"📊 總共需要搜尋 {total_areas} 個行政區")
    logger.info(f"⚡ 預估API請求次數：{total_areas * 20} 次 (為了更多店家)")
    
    print(f"🎯 擴大搜尋策略啟用 - 目標：更多店家數量")
    print(f"📏 搜尋半徑：{radius} 公尺")
    print(f"🔍 使用多樣化搜尋方法")
    
    for index, (area_name, center, city) in enumerate(area_keywords, 1):
        region_info = f"{city} {area_name} ({index}/{total_areas})"
        logger.info(f"🔍 開始搜尋區域：{region_info}")
        print(f"🔍 搜尋區域：{region_info}")
        
        # 使用擴大的搜尋策略
        start_time = time.time()
        places = search_places_comprehensive_expanded(keywords, center, radius, area_name, city)
        search_time = time.time() - start_time
        api_request_count += 20  # 估計每個區域約20次請求
        
        result_info = f"找到 {len(places)} 間店家，耗時 {search_time:.1f} 秒"
        logger.info(f"✅ {region_info} - {result_info}")
        print(result_info)

        for place in places:
            place_id = place.get('place_id')
            
            # 全局去重檢查
            if place_id in global_seen_places:
                continue
            global_seen_places.add(place_id)
            
            try:
                name = place.get('name')
                address = place.get('vicinity', place.get('formatted_address', ''))
                
                # 使用緩存的詳細資訊獲取
                details = get_place_details_cached(place_id)
                phone = details.get('formatted_phone_number', 'N/A')
                website = details.get('website', '')
                
                # 修正Google Maps連結格式
                maps_url = f"https://www.google.com/maps/place/?q=place_id:{place_id}"
                
                # 搜尋LINE聯絡方式
                line_contact = 'N/A'
                
                # 從網站連結查找LINE
                if website and 'line' in website.lower():
                    line_contact = extract_line_contact(website)
                
                # 從評論中搜尋LINE資訊
                if line_contact == 'N/A' and details.get('reviews'):
                    for review in details.get('reviews', [])[:3]:  # 減少到3個評論
                        review_text = review.get('text', '')
                        extracted_line = extract_line_contact(review_text)
                        if extracted_line != 'N/A':
                            line_contact = extracted_line
                            break
                
                # 從編輯摘要搜尋LINE資訊
                if line_contact == 'N/A' and details.get('editorial_summary'):
                    summary_text = details.get('editorial_summary', {}).get('overview', '')
                    line_contact = extract_line_contact(summary_text)

                result = {
                    '縣市': city,
                    '區域': area_name,
                    '店名': name,
                    '地址': address,
                    '電話': phone,
                    'LINE聯絡方式': line_contact,
                    '網站': website if website else 'N/A',
                    '地圖連結': maps_url
                }
                all_results.append(result)

                # 記錄店家資訊到 log
                logger.info(f"   📍 {name} | {address} | {phone} | LINE: {line_contact}")
                
                print(f"✅ {name}")
                print(f"地址：{address}")
                print(f"電話：{phone}")
                print(f"LINE：{line_contact}")
                print(f"網站：{website if website else 'N/A'}")
                print("---")
                
                time.sleep(0.3)  # 減少延遲時間
            except Exception as e:
                error_msg = f"處理店家時發生錯誤：{e}"
                logger.error(f"❌ {error_msg}")
                print(f"❌ {error_msg}")
                continue

    logger.info(f"\n📊 API請求統計：實際使用約 {api_request_count + len(all_results)} 次")
    logger.info(f"✅ 全域去重：共找到 {len(all_results)} 筆不重複店家")
    logger.info("🎉 搜尋程序完成！")
    
    print(f"\n📊 擴大搜尋完成")
    print(f"✅ 共找到 {len(all_results)} 筆不重複店家")
    print(f"🎉 最終完成！")
    
    return all_results

# ✅ 8. 將結果寫入 CSV 檔案
def save_to_csv(data, filename="yunlin_0711.csv"):
    try:
        with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=['縣市', '區域', '店名', '地址', '電話', 'LINE聯絡方式', '網站', '地圖連結'])
            writer.writeheader()
            writer.writerows(data)
        
        logger.info(f"📁 CSV 檔案保存成功：{filename}")
        logger.info(f"📊 總計匯出 {len(data)} 筆店家資料")
        print(f"\n📁 成功輸出至 CSV 檔案：{filename}")
        
    except Exception as e:
        logger.error(f"❌ CSV 檔案保存失敗：{e}")
        print(f"❌ CSV 檔案保存失敗：{e}")

# ✅ 9. 執行主流程
if __name__ == '__main__':
    print("🚀 開始搜尋台灣六都 + 屏東的美容店家資料... (優化版)")
    print("💅 搜尋類型：美容、美甲、美睫、指甲、睫毛、採耳、耳燭、熱蠟、除毛、護膚等")
    print("📍 涵蓋區域：台南市、高雄市、屏東縣")
    print(f"📊 總共 {len(area_keywords)} 個行政區")
    print("⚡ 搜尋策略：精準版本 - 準確關鍵字 + 業務相關性過濾")
    print("🔍 搜尋方法：關鍵字搜尋 + 類型搜尋 + 地理範圍優化 + 業務過濾")
    print("📏 搜尋半徑：15km + 雙重過濾機制")
    print("🚫 自動排除：學校、醫院、加油站、餐廳、通訊行等不相關業務")
    print("=" * 60)
    
    data = run_search_all_areas()
    save_to_csv(data)
    
    # 統計結果
    if data:
        city_stats = {}
        for item in data:
            city = item['縣市']
            city_stats[city] = city_stats.get(city, 0) + 1
        
        logger.info("\n📈 各縣市店家統計結果：")
        print("\n📈 各縣市店家統計：")
        
        for city, count in city_stats.items():
            stat_info = f"{city}：{count} 間店家"
            logger.info(f"   {stat_info}")
            print(f"   {stat_info}")
        
        logger.info("=" * 60)
        logger.info("🏁 程式執行完畢！")
        logger.info("=" * 60)
