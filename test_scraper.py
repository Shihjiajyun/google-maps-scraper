#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Google 地圖爬蟲 - 快速測試版
用於驗證 GCP 環境是否正常工作
目標：測試 5-10 家店，執行時間 5-10 分鐘
"""

import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from datetime import datetime

class TestGoogleMapsScraper:
    def __init__(self):
        self.driver = None
        self.shops_data = []
        
    def debug_print(self, message, level="INFO"):
        """輸出訊息"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        symbols = {"INFO": "ℹ️", "SUCCESS": "✅", "ERROR": "❌", "TEST": "🧪"}
        symbol = symbols.get(level, "📋")
        print(f"[{timestamp}] {symbol} {message}")
    
    def setup_driver(self):
        """設定瀏覽器"""
        try:
            self.debug_print("🧪 測試：設定 GCP 環境瀏覽器...", "TEST")
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            
            self.driver = webdriver.Chrome(options=chrome_options)
            self.debug_print("✅ 測試：瀏覽器設定成功", "SUCCESS")
            return True
        except Exception as e:
            self.debug_print(f"❌ 測試：瀏覽器設定失敗: {e}", "ERROR")
            return False
    
    def test_google_maps_access(self):
        """測試訪問 Google Maps"""
        try:
            self.debug_print("🧪 測試：訪問 Google Maps...", "TEST")
            self.driver.get("https://www.google.com/maps")
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            time.sleep(3)
            self.debug_print("✅ 測試：Google Maps 訪問成功", "SUCCESS")
            return True
        except Exception as e:
            self.debug_print(f"❌ 測試：Google Maps 訪問失敗: {e}", "ERROR")
            return False
    
    def test_shop_search(self):
        """測試店家搜尋"""
        try:
            self.debug_print("🧪 測試：店家搜尋", "TEST")
            search_box = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "searchboxinput"))
            )
            search_box.clear()
            search_box.send_keys("美甲 near 高雄火車站")
            search_box.send_keys(Keys.ENTER)
            time.sleep(8)
            
            # 找店家連結
            shop_links = self.driver.find_elements(By.CSS_SELECTOR, "a[href*='/maps/place/']")
            self.debug_print(f"✅ 測試：找到 {len(shop_links)} 個店家連結", "SUCCESS")
            
            # 擷取前5家店
            for i, link in enumerate(shop_links[:5]):
                try:
                    name = link.get_attribute('aria-label') or link.text
                    url = link.get_attribute('href')
                    if name and url:
                        shop_info = {
                            'name': name.strip(),
                            'google_maps_url': url,
                            'test_location': '高雄火車站',
                            'extracted_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }
                        self.shops_data.append(shop_info)
                        self.debug_print(f"✅ 擷取店家 {i+1}: {name[:30]}...", "SUCCESS")
                except:
                    continue
            
            return len(self.shops_data) > 0
        except Exception as e:
            self.debug_print(f"❌ 測試：店家搜尋失敗: {e}", "ERROR")
            return False
    
    def test_save_results(self):
        """測試儲存功能"""
        try:
            self.debug_print("🧪 測試：儲存功能", "TEST")
            if not self.shops_data:
                return False
                
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            df = pd.DataFrame(self.shops_data)
            
            # 儲存檔案
            csv_filename = f"test_results_{timestamp}.csv"
            excel_filename = f"test_results_{timestamp}.xlsx"
            
            df.to_csv(csv_filename, index=False, encoding='utf-8-sig')
            df.to_excel(excel_filename, index=False)
            
            self.debug_print(f"✅ 測試：檔案儲存成功", "SUCCESS")
            self.debug_print(f"   📁 CSV: {csv_filename}", "INFO")
            self.debug_print(f"   📁 Excel: {excel_filename}", "INFO")
            self.debug_print(f"   📊 資料筆數: {len(self.shops_data)}", "INFO")
            return True
        except Exception as e:
            self.debug_print(f"❌ 測試：儲存失敗: {e}", "ERROR")
            return False
    
    def run_test(self):
        """執行測試"""
        self.debug_print("🧪 開始 Google Maps 爬蟲 GCP 環境測試", "TEST")
        print("=" * 60)
        
        tests = [
            ("瀏覽器設定", self.setup_driver),
            ("Google Maps 訪問", self.test_google_maps_access),
            ("店家搜尋和擷取", self.test_shop_search),
            ("儲存功能", self.test_save_results)
        ]
        
        results = []
        for test_name, test_func in tests:
            self.debug_print(f"🔧 測試：{test_name}", "INFO")
            result = test_func()
            results.append(result)
            if not result and test_name != "儲存功能":
                break
        
        # 顯示結果
        print("\n" + "=" * 60)
        self.debug_print("🧪 測試結果總結", "INFO")
        print("-" * 60)
        
        test_names = ["瀏覽器設定", "Google Maps 訪問", "店家搜尋和擷取", "儲存功能"]
        all_passed = True
        for i, (name, result) in enumerate(zip(test_names, results)):
            if i < len(results):
                status = "✅ 通過" if result else "❌ 失敗"
                self.debug_print(f"   {name}: {status}", "INFO")
                if not result:
                    all_passed = False
        
        print("-" * 60)
        if all_passed:
            self.debug_print("🎉 所有測試通過！GCP 環境正常", "SUCCESS")
            self.debug_print("✅ 可以開始執行完整版爬蟲程式", "SUCCESS")
        else:
            self.debug_print("❌ 部分測試失敗，請檢查環境設定", "ERROR")
        
        if self.driver:
            self.driver.quit()
        
        return all_passed

def main():
    print("🧪 Google Maps 爬蟲 - GCP 環境測試")
    print("=" * 50)
    print("🎯 測試目標：")
    print("   - 驗證 Chrome 和 ChromeDriver 安裝")
    print("   - 測試 Google Maps 訪問和搜尋")
    print("   - 驗證店家擷取和儲存功能")
    print("   - 預計執行時間：5-10 分鐘")
    print("   - 預計擷取：5-10 家店家")
    print()
    
    input("按 Enter 開始測試...")
    
    tester = TestGoogleMapsScraper()
    success = tester.run_test()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 測試完成！環境正常，可以執行完整程式")
        print("💡 接下來執行：python3 google_maps_scraper_detailed.py")
    else:
        print("❌ 測試失敗，請檢查錯誤訊息並修復環境")

if __name__ == "__main__":
    main() 