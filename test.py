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

# ✅ 2. 高雄行政區＋中心座標（可擴充）
area_keywords = [
    ("鼓山區", "22.6515,120.2844"),
    ("左營區", "22.6873,120.3066"),
    ("三民區", "22.6466,120.3265"),
    ("鳳山區", "22.6287,120.3583"),
    ("苓雅區", "22.6239,120.3090"),
    ("新興區", "22.6317,120.3021"),
    ("前金區", "22.6263,120.2956"),
    ("前鎮區", "22.5918,120.3083"),
    ("鹽埕區", "22.6242,120.2842"),
    ("旗津區", "22.5884,120.2672"),
    ("小港區", "22.5653,120.3452"),
    ("楠梓區", "22.7283,120.3182"),
    ("仁武區", "22.7012,120.3603"),
    ("大社區", "22.7325,120.3506"),
    ("鳥松區", "22.6484,120.3629"),
    ("大寮區", "22.6057,120.3958"),
    ("林園區", "22.5006,120.3975"),
    ("大樹區", "22.6671,120.4344"),
    ("阿蓮區", "22.8844,120.3224"),
    ("路竹區", "22.8562,120.2603"),
    ("湖內區", "22.8993,120.2457"),
    ("茄萣區", "22.8971,120.1804"),
    ("永安區", "22.8337,120.2172"),
    ("岡山區", "22.7924,120.2982"),
    ("彌陀區", "22.7896,120.2456"),
    ("梓官區", "22.7511,120.2605"),
    ("燕巢區", "22.7931,120.3622"),
    ("田寮區", "22.8773,120.3869"),
    ("旗山區", "22.8882,120.4812"),
    ("美濃區", "22.9028,120.5598"),
    ("杉林區", "22.9956,120.5481"),
    ("內門區", "22.9537,120.4706"),
    ("六龜區", "23.0182,120.6866"),
    ("甲仙區", "23.0832,120.5914"),
    ("桃源區", "23.2348,120.7437"),
    ("那瑪夏區", "23.2396,120.6825"),
    ("茂林區", "22.8937,120.6592")
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

# ✅ 4. 搜尋附近店家（最多 60 筆）
def search_places(keyword, location, radius):
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

# ✅ 6. 主程式：遍歷所有區域並輸出店家資訊
def run_search_all_areas(keyword="美甲", radius=5000):
    all_results = []

    for area_name, center in area_keywords:
        print(f"🔍 搜尋區域：{area_name}")
        places = search_places(keyword, center, radius)
        print(f"找到 {len(places)} 間店家")

        for place in places:
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

    print(f"\n✅ 全部完成，共 {len(all_results)} 筆店家資料")
    return all_results

# ✅ 7. 將結果寫入 CSV 檔案
def save_to_csv(data, filename="kaohsiung_nail_shops.csv"):
    with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=['區域', '店名', '地址', '電話', 'LINE聯絡方式', '網站', '地圖連結'])
        writer.writeheader()
        writer.writerows(data)
    print(f"\n📁 成功輸出至 CSV 檔案：{filename}")

# ✅ 8. 執行主流程
if __name__ == '__main__':
    data = run_search_all_areas()
    save_to_csv(data)
