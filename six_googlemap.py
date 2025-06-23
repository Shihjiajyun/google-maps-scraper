import requests
import time
import csv
import os
import re
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

# ✅ 2. 台灣六都 + 屏東所有行政區中心座標
area_keywords = [
    # 台北市 (12區)
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

    # 新北市 (29區)
    ("板橋區", "25.0118,121.4625", "新北市"),
    ("三重區", "25.0622,121.4848", "新北市"),
    ("中和區", "24.9998,121.4991", "新北市"),
    ("永和區", "25.0068,121.5161", "新北市"),
    ("新莊區", "25.0372,121.4325", "新北市"),
    ("新店區", "24.9669,121.5414", "新北市"),
    ("樹林區", "24.9937,121.4200", "新北市"),
    ("鶯歌區", "24.9542,121.3548", "新北市"),
    ("三峽區", "24.9342,121.3688", "新北市"),
    ("淡水區", "25.1645,121.4404", "新北市"),
    ("汐止區", "25.0672,121.6422", "新北市"),
    ("瑞芳區", "25.1090,121.8070", "新北市"),
    ("土城區", "24.9729,121.4419", "新北市"),
    ("蘆洲區", "25.0840,121.4741", "新北市"),
    ("五股區", "25.0830,121.4439", "新北市"),
    ("泰山區", "25.0594,121.4218", "新北市"),
    ("林口區", "25.0769,121.3895", "新北市"),
    ("深坑區", "24.9988,121.6161", "新北市"),
    ("石碇區", "24.9895,121.6635", "新北市"),
    ("坪林區", "24.9361,121.7098", "新北市"),
    ("三芝區", "25.2519,121.4990", "新北市"),
    ("石門區", "25.2915,121.5675", "新北市"),
    ("八里區", "25.1496,121.3996", "新北市"),
    ("平溪區", "25.0255,121.7417", "新北市"),
    ("雙溪區", "25.0336,121.8264", "新北市"),
    ("貢寮區", "25.0196,121.9085", "新北市"),
    ("金山區", "25.2225,121.6341", "新北市"),
    ("萬里區", "25.1797,121.6897", "新北市"),
    ("烏來區", "24.8658,121.5497", "新北市"),

    # 桃園市 (13區)
    ("桃園區", "24.9936,121.3010", "桃園市"),
    ("中壢區", "24.9537,121.2257", "桃園市"),
    ("大溪區", "24.8838,121.2677", "桃園市"),
    ("楊梅區", "24.9175,121.1459", "桃園市"),
    ("蘆竹區", "25.0441,121.2914", "桃園市"),
    ("大園區", "25.0569,121.2014", "桃園市"),
    ("龜山區", "25.0002,121.3539", "桃園市"),
    ("八德區", "24.9444,121.2999", "桃園市"),
    ("龍潭區", "24.8632,121.2167", "桃園市"),
    ("平鎮區", "24.9234,121.2043", "桃園市"),
    ("新屋區", "24.9706,121.1061", "桃園市"),
    ("觀音區", "25.0357,121.1220", "桃園市"),
    ("復興區", "24.8176,121.3496", "桃園市"),

    # 台中市 (29區)
    ("中區", "24.1443,120.6794", "台中市"),
    ("東區", "24.1369,120.6973", "台中市"),
    ("南區", "24.1201,120.6642", "台中市"),
    ("西區", "24.1393,120.6736", "台中市"),
    ("北區", "24.1548,120.6848", "台中市"),
    ("西屯區", "24.1618,120.6176", "台中市"),
    ("南屯區", "24.1285,120.6185", "台中市"),
    ("北屯區", "24.1810,120.7131", "台中市"),
    ("豐原區", "24.2567,120.7236", "台中市"),
    ("東勢區", "24.2610,120.8239", "台中市"),
    ("大甲區", "24.3480,120.6242", "台中市"),
    ("清水區", "24.2638,120.5685", "台中市"),
    ("沙鹿區", "24.2260,120.5687", "台中市"),
    ("梧棲區", "24.2552,120.5216", "台中市"),
    ("后里區", "24.3047,120.7063", "台中市"),
    ("神岡區", "24.2544,120.6647", "台中市"),
    ("潭子區", "24.2067,120.7057", "台中市"),
    ("大雅區", "24.2286,120.6520", "台中市"),
    ("新社區", "24.2265,120.8069", "台中市"),
    ("石岡區", "24.2725,120.7827", "台中市"),
    ("外埔區", "24.3395,120.6519", "台中市"),
    ("大安區", "24.3452,120.5992", "台中市"),
    ("烏日區", "24.1062,120.6238", "台中市"),
    ("大肚區", "24.1566,120.5416", "台中市"),
    ("龍井區", "24.1926,120.5435", "台中市"),
    ("霧峰區", "24.0669,120.6998", "台中市"),
    ("太平區", "24.1241,120.7339", "台中市"),
    ("大里區", "24.0992,120.6773", "台中市"),
    ("和平區", "24.2395,121.0114", "台中市"),

    # 台南市 (37區)
    ("中西區", "22.9912,120.2020", "台南市"),
    ("東區", "22.9837,120.2265", "台南市"),
    ("南區", "22.9735,120.1873", "台南市"),
    ("北區", "23.0063,120.2121", "台南市"),
    ("安平區", "23.0011,120.1662", "台南市"),
    ("安南區", "23.0465,120.1864", "台南市"),
    ("永康區", "23.0262,120.2571", "台南市"),
    ("歸仁區", "22.9661,120.2896", "台南市"),
    ("新化區", "23.0379,120.3117", "台南市"),
    ("左鎮區", "23.0537,120.4070", "台南市"),
    ("玉井區", "23.1244,120.4601", "台南市"),
    ("楠西區", "23.1708,120.4856", "台南市"),
    ("南化區", "23.0421,120.4769", "台南市"),
    ("仁德區", "22.9619,120.2477", "台南市"),
    ("關廟區", "22.9704,120.3304", "台南市"),
    ("龍崎區", "22.9682,120.3567", "台南市"),
    ("官田區", "23.1939,120.3860", "台南市"),
    ("麻豆區", "23.1804,120.2473", "台南市"),
    ("佳里區", "23.1646,120.1751", "台南市"),
    ("西港區", "23.1252,120.2038", "台南市"),
    ("七股區", "23.1415,120.0881", "台南市"),
    ("將軍區", "23.2005,120.1695", "台南市"),
    ("學甲區", "23.2308,120.1761", "台南市"),
    ("北門區", "23.2678,120.1248", "台南市"),
    ("新營區", "23.3058,120.3169", "台南市"),
    ("後壁區", "23.3665,120.3611", "台南市"),
    ("白河區", "23.3516,120.4090", "台南市"),
    ("東山區", "23.3279,120.3979", "台南市"),
    ("六甲區", "23.2315,120.3477", "台南市"),
    ("下營區", "23.2360,120.2639", "台南市"),
    ("柳營區", "23.2776,120.3061", "台南市"),
    ("鹽水區", "23.3196,120.2662", "台南市"),
    ("善化區", "23.1322,120.2969", "台南市"),
    ("大內區", "23.1178,120.3520", "台南市"),
    ("山上區", "23.1049,120.3738", "台南市"),
    ("新市區", "23.0784,120.2951", "台南市"),
    ("安定區", "23.1215,120.2270", "台南市"),

    # 高雄市 (38區)
    ("鼓山區", "22.6515,120.2844", "高雄市"),
    ("左營區", "22.6873,120.3066", "高雄市"),
    ("三民區", "22.6466,120.3265", "高雄市"),
    ("鳳山區", "22.6287,120.3583", "高雄市"),
    ("苓雅區", "22.6239,120.3090", "高雄市"),
    ("新興區", "22.6317,120.3021", "高雄市"),
    ("前金區", "22.6263,120.2956", "高雄市"),
    ("前鎮區", "22.5918,120.3083", "高雄市"),
    ("鹽埕區", "22.6242,120.2842", "高雄市"),
    ("旗津區", "22.5884,120.2672", "高雄市"),
    ("小港區", "22.5653,120.3452", "高雄市"),
    ("楠梓區", "22.7283,120.3182", "高雄市"),
    ("仁武區", "22.7012,120.3603", "高雄市"),
    ("大社區", "22.7325,120.3506", "高雄市"),
    ("鳥松區", "22.6484,120.3629", "高雄市"),
    ("大寮區", "22.6057,120.3958", "高雄市"),
    ("林園區", "22.5006,120.3975", "高雄市"),
    ("大樹區", "22.6671,120.4344", "高雄市"),
    ("阿蓮區", "22.8844,120.3224", "高雄市"),
    ("路竹區", "22.8562,120.2603", "高雄市"),
    ("湖內區", "22.8993,120.2457", "高雄市"),
    ("茄萣區", "22.8971,120.1804", "高雄市"),
    ("永安區", "22.8337,120.2172", "高雄市"),
    ("岡山區", "22.7924,120.2982", "高雄市"),
    ("彌陀區", "22.7896,120.2456", "高雄市"),
    ("梓官區", "22.7511,120.2605", "高雄市"),
    ("燕巢區", "22.7931,120.3622", "高雄市"),
    ("田寮區", "22.8773,120.3869", "高雄市"),
    ("旗山區", "22.8882,120.4812", "高雄市"),
    ("美濃區", "22.9028,120.5598", "高雄市"),
    ("杉林區", "22.9956,120.5481", "高雄市"),
    ("內門區", "22.9537,120.4706", "高雄市"),
    ("六龜區", "23.0182,120.6866", "高雄市"),
    ("甲仙區", "23.0832,120.5914", "高雄市"),
    ("桃源區", "23.2348,120.7437", "高雄市"),
    ("那瑪夏區", "23.2396,120.6825", "高雄市"),
    ("茂林區", "22.8937,120.6592", "高雄市"),
    ("橋頭區", "22.7568,120.3068", "高雄市"),

    # 屏東縣 (33鄉鎮市)
    ("屏東市", "22.6690,120.4883", "屏東縣"),
    ("潮州鎮", "22.5508,120.5446", "屏東縣"),
    ("東港鎮", "22.4658,120.4476", "屏東縣"),
    ("恆春鎮", "22.0018,120.7395", "屏東縣"),
    ("萬丹鄉", "22.5892,120.4827", "屏東縣"),
    ("長治鄉", "22.6779,120.5337", "屏東縣"),
    ("麟洛鄉", "22.6515,120.5244", "屏東縣"),
    ("九如鄉", "22.7395,120.4823", "屏東縣"),
    ("里港鄉", "22.7758,120.4999", "屏東縣"),
    ("鹽埔鄉", "22.7542,120.5527", "屏東縣"),
    ("高樹鄉", "22.8058,120.6081", "屏東縣"),
    ("萬巒鄉", "22.5715,120.5907", "屏東縣"),
    ("內埔鄉", "22.6110,120.5655", "屏東縣"),
    ("竹田鄉", "22.5839,120.5426", "屏東縣"),
    ("新埤鄉", "22.4687,120.5566", "屏東縣"),
    ("枋寮鄉", "22.3618,120.5908", "屏東縣"),
    ("新園鄉", "22.4542,120.4582", "屏東縣"),
    ("崁頂鄉", "22.5066,120.5034", "屏東縣"),
    ("林邊鄉", "22.4287,120.5116", "屏東縣"),
    ("南州鄉", "22.4900,120.5143", "屏東縣"),
    ("佳冬鄉", "22.4272,120.5553", "屏東縣"),
    ("琉球鄉", "22.3444,120.3714", "屏東縣"),
    ("車城鄉", "22.0742,120.7090", "屏東縣"),
    ("滿州鄉", "22.0288,120.7842", "屏東縣"),
    ("枋山鄉", "22.2630,120.6552", "屏東縣"),
    ("三地門鄉", "22.7179,120.6548", "屏東縣"),
    ("霧台鄉", "22.7542,120.7394", "屏東縣"),
    ("瑪家鄉", "22.6818,120.6737", "屏東縣"),
    ("泰武鄉", "22.6081,120.6515", "屏東縣"),
    ("來義鄉", "22.5284,120.6648", "屏東縣"),
    ("春日鄉", "22.3966,120.6182", "屏東縣"),
    ("獅子鄉", "22.2284,120.7208", "屏東縣"),
    ("牡丹鄉", "22.1351,120.7834", "屏東縣")
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

# ✅ 4.1. 文字搜尋（更廣泛的搜尋）
def search_places_text(keyword, location, radius):
    url = 'https://maps.googleapis.com/maps/api/place/textsearch/json'
    params = {
        'key': API_KEY,
        'query': f"{keyword} {location}",
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

# ✅ 4.2. 多關鍵字搜尋策略
def search_places_comprehensive(keywords, location, radius):
    """綜合搜尋策略：使用多個關鍵字和搜尋方法"""
    all_results = []
    
    for keyword in keywords:
        print(f"   🔎 搜尋關鍵字：{keyword}")
        
        # 方法1: NearbySearch
        nearby_results = search_places_nearby(keyword, location, radius)
        all_results.extend(nearby_results)
        time.sleep(1)
        
        # 方法2: TextSearch (更廣泛)
        text_results = search_places_text(keyword, location, radius)
        all_results.extend(text_results)
        time.sleep(1)
        
        # 方法3: 加上類別搜尋
        category_results = search_places_nearby(f"{keyword} 美容", location, radius)
        all_results.extend(category_results)
        time.sleep(1)
    
    return all_results

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

# ✅ 7. 主程式：遍歷所有區域並輸出店家資訊
def run_search_all_areas(keywords=None, radius=8000):
    if keywords is None:
        # 擴充關鍵字列表，包含相關變形詞
        keywords = [
            "美甲", "指甲彩繪", "凝膠指甲", "光療美甲",
            "美睫", "睫毛嫁接", "接睫毛", "睫毛美容",
            "耳燭", "耳燭療法", "耳朵SPA",
            "採耳", "清耳垢", "耳朵清潔", "掏耳朵",
            "熱蠟", "熱蠟除毛", "蜜蠟除毛"
        ]
    all_results = []
    total_areas = len(area_keywords)
    
    print(f"🎯 搜尋關鍵字：{', '.join(keywords)}")
    print(f"📏 搜尋半徑：{radius} 公尺")
    
    for index, (area_name, center, city) in enumerate(area_keywords, 1):
        print(f"🔍 搜尋區域：{city} {area_name} ({index}/{total_areas})")
        
        # 使用綜合搜尋策略
        places = search_places_comprehensive(keywords, center, radius)
        
        # 去除重複
        unique_places = deduplicate_places(places)
        print(f"找到 {len(places)} 間店家，去重後 {len(unique_places)} 間")

        for place in unique_places:
            try:
                name = place.get('name')
                address = place.get('vicinity')
                place_id = place.get('place_id')
                
                # 取得詳細資訊
                details = get_place_details(place_id)
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
                    for review in details.get('reviews', [])[:5]:  # 只檢查前5個評論
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

                print(f"✅ {name}")
                print(f"地址：{address}")
                print(f"電話：{phone}")
                print(f"LINE：{line_contact}")
                print(f"網站：{website if website else 'N/A'}")
                print(f"地圖：{maps_url}")
                print("---")
                
                time.sleep(1)
            except Exception as e:
                print(f"❌ 發生錯誤：{e}")
                continue

    # 最終全域去重
    print("\n🔄 進行最終去重處理...")
    final_results = []
    seen_places = set()
    
    for result in all_results:
        # 使用店名+地址作為識別
        identifier = f"{result['店名']}_{result['地址']}"
        if identifier not in seen_places:
            seen_places.add(identifier)
            final_results.append(result)
    
    removed_count = len(all_results) - len(final_results)
    print(f"✅ 去除 {removed_count} 筆重複資料")
    print(f"🎉 最終完成，共 {len(final_results)} 筆店家資料")
    
    return final_results

# ✅ 8. 將結果寫入 CSV 檔案
def save_to_csv(data, filename="taiwan_six_cities_beauty_shops.csv"):
    with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=['縣市', '區域', '店名', '地址', '電話', 'LINE聯絡方式', '網站', '地圖連結'])
        writer.writeheader()
        writer.writerows(data)
    print(f"\n📁 成功輸出至 CSV 檔案：{filename}")

# ✅ 9. 執行主流程
if __name__ == '__main__':
    print("🚀 開始搜尋台灣六都 + 屏東的美容店家資料...")
    print("💅 搜尋類型：美甲、美睫、耳燭、採耳、熱蠟")
    print("📍 涵蓋區域：台北市、新北市、桃園市、台中市、台南市、高雄市、屏東縣")
    print(f"📊 總共 {len(area_keywords)} 個行政區")
    print("🔍 搜尋策略：多關鍵字 + 多方法 + 擴大半徑")
    print("=" * 60)
    
    data = run_search_all_areas()
    save_to_csv(data)
    
    # 統計結果
    if data:
        city_stats = {}
        for item in data:
            city = item['縣市']
            city_stats[city] = city_stats.get(city, 0) + 1
        
        print("\n📈 各縣市店家統計：")
        for city, count in city_stats.items():
            print(f"   {city}：{count} 間店家")
