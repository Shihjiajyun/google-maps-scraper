import requests
import time
import csv
import os
from dotenv import load_dotenv

# ✅ 1. 從環境變數讀取 API 金鑰
load_dotenv()
API_KEY = os.getenv('API_KEY')

if not API_KEY:
    raise ValueError("請在 .env 檔案中設定 API_KEY")

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


# ✅ 3. 搜尋附近店家（最多 60 筆）
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

# ✅ 4. 取得店家詳細資訊（含電話）
def get_place_details(place_id):
    url = 'https://maps.googleapis.com/maps/api/place/details/json'
    params = {
        'key': API_KEY,
        'place_id': place_id,
        'language': 'zh-TW',
        'fields': 'name,formatted_address,formatted_phone_number'
    }
    res = requests.get(url, params=params).json()
    return res.get('result', {})

# ✅ 5. 主程式：遍歷所有區域並輸出店家資訊
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
                details = get_place_details(place_id)
                phone = details.get('formatted_phone_number', 'N/A')
                maps_url = f"https://www.google.com/maps/place/?q=place_id={place_id}"

                result = {
                    '區域': area_name,
                    '店名': name,
                    '地址': address,
                    '電話': phone,
                    '地圖連結': maps_url
                }
                all_results.append(result)

                print(f"✅ {name}\n地址：{address}\n電話：{phone}\n地圖：{maps_url}\n---")
                time.sleep(1)
            except Exception as e:
                print(f"❌ 發生錯誤：{e}")
                continue

    print(f"\n✅ 全部完成，共 {len(all_results)} 筆店家資料")
    return all_results

# ✅ 6. 將結果寫入 CSV 檔案
def save_to_csv(data, filename="kaohsiung_nail_shops.csv"):
    with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=['區域', '店名', '地址', '電話', '地圖連結'])
        writer.writeheader()
        writer.writerows(data)
    print(f"\n📁 成功輸出至 CSV 檔案：{filename}")

# ✅ 7. 執行主流程
if __name__ == '__main__':
    data = run_search_all_areas()
    save_to_csv(data)
