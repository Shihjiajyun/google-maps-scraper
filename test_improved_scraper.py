#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
測試改進後的高雄美甲美睫店家爬蟲
主要測試：
1. 避免重複抓取
2. 避免跳過店家
3. 精確的滾動位置控制
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from google_maps_scraper_kaohsiung_precision import KaohsiungPrecisionScraper

def test_improved_scraper():
    """測試改進後的爬蟲"""
    print("🧪 測試改進後的高雄美甲美睫店家爬蟲")
    print("=" * 60)
    print("🎯 測試目標：")
    print("   1. 避免重複抓取同一家店")
    print("   2. 避免跳過店家")
    print("   3. 精確的滾動位置控制")
    print("   4. 左側搜尋結果位置穩定")
    print()
    
    # 詢問測試模式
    print("🔧 測試模式選擇：")
    print("   1. 快速測試 (3個地標，每個地標最多10家店)")
    print("   2. 中等測試 (10個地標，每個地標最多20家店)")
    print("   3. 完整測試 (所有地標，目標2000家店)")
    print()
    
    while True:
        choice = input("請選擇測試模式 (1/2/3): ").strip()
        if choice in ['1', '2', '3']:
            break
        print("❌ 請輸入 1、2 或 3")
    
    # 詢問瀏覽器模式
    print()
    print("🖥️ 瀏覽器模式：")
    print("   1. 顯示視窗 (推薦，可觀察改進效果)")
    print("   2. 無頭模式")
    print()
    
    while True:
        browser_choice = input("請選擇瀏覽器模式 (1/2): ").strip()
        if browser_choice in ['1', '2']:
            break
        print("❌ 請輸入 1 或 2")
    
    show_browser = browser_choice == '1'
    
    # 設定測試參數
    if choice == '1':
        test_landmarks = ["高雄火車站", "夢時代購物中心", "六合夜市"]
        target_shops = 30
        test_name = "快速測試"
    elif choice == '2':
        test_landmarks = [
            "高雄火車站", "夢時代購物中心", "六合夜市", "新崛江商圈", "文化中心",
            "左營高鐵站", "鳳山火車站", "三多商圈", "美麗島站", "巨蛋商圈"
        ]
        target_shops = 100
        test_name = "中等測試"
    else:
        test_landmarks = None  # 使用所有地標
        target_shops = 2000
        test_name = "完整測試"
    
    print()
    print(f"🚀 開始 {test_name}")
    print(f"🎯 目標店家數: {target_shops}")
    if test_landmarks:
        print(f"📍 測試地標: {len(test_landmarks)} 個")
    else:
        print(f"📍 測試地標: 全部地標")
    print("=" * 60)
    
    # 創建爬蟲實例
    scraper = KaohsiungPrecisionScraper(debug_mode=True, show_browser=show_browser)
    
    # 如果是測試模式，修改目標和地標
    if test_landmarks:
        scraper.target_shops = target_shops
        # 暫時修改地標列表
        original_get_landmarks = scraper.get_kaohsiung_landmarks
        scraper.get_kaohsiung_landmarks = lambda: test_landmarks
    
    try:
        # 執行測試
        success = scraper.run_precision_scraping()
        
        print()
        print("=" * 60)
        print(f"🧪 {test_name} 完成")
        
        if success and scraper.shops_data:
            print(f"✅ 測試成功！")
            print(f"📊 收集店家數: {len(scraper.shops_data)}")
            print(f"🎯 目標達成率: {len(scraper.shops_data)/target_shops*100:.1f}%")
            
            # 檢查重複
            unique_names = set()
            unique_urls = set()
            duplicates = 0
            
            for shop in scraper.shops_data:
                name = shop['name'].lower().strip()
                url = shop.get('google_maps_url', '').strip()
                
                if name in unique_names or url in unique_urls:
                    duplicates += 1
                else:
                    unique_names.add(name)
                    unique_urls.add(url)
            
            print(f"🔍 重複檢查: {duplicates} 個重複項目")
            if duplicates == 0:
                print("✅ 無重複，去重功能正常！")
            else:
                print(f"⚠️ 發現 {duplicates} 個重複項目，需要進一步優化")
            
            # 統計聯絡資訊
            has_address = sum(1 for shop in scraper.shops_data if shop.get('address', '地址未提供') not in ['地址未提供', '地址獲取失敗'])
            has_phone = sum(1 for shop in scraper.shops_data if shop.get('phone', '電話未提供') not in ['電話未提供', '電話獲取失敗'])
            has_line = sum(1 for shop in scraper.shops_data if shop.get('line_contact', 'LINE未提供') not in ['LINE未提供', 'LINE獲取失敗'])
            
            print(f"📞 聯絡資訊統計:")
            print(f"   📍 地址: {has_address}/{len(scraper.shops_data)} ({has_address/len(scraper.shops_data)*100:.1f}%)")
            print(f"   📞 電話: {has_phone}/{len(scraper.shops_data)} ({has_phone/len(scraper.shops_data)*100:.1f}%)")
            print(f"   📱 LINE: {has_line}/{len(scraper.shops_data)} ({has_line/len(scraper.shops_data)*100:.1f}%)")
            
        else:
            print("❌ 測試失敗或未收集到資料")
            
    except Exception as e:
        print(f"❌ 測試過程中出錯: {e}")
        return False
    
    return True

if __name__ == "__main__":
    test_improved_scraper() 