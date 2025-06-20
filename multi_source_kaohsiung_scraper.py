#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
高雄美甲美睫店家多源整合爬蟲
整合多個平台：Google搜尋、Facebook、商業目錄、求職網站等
目標：快速收集大量高雄美甲美睫店家基本資料
作者：AI Assistant
日期：2024
"""

import time
import random
import pandas as pd
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import logging
from datetime import datetime
import re
import urllib.parse
import json
from threading import Lock
import concurrent.futures

# 確保安裝必要套件
try:
    import openpyxl
    from bs4 import BeautifulSoup
except ImportError:
    print("⚠️ 正在安裝必要套件...")
    import subprocess
    import sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "openpyxl", "beautifulsoup4", "lxml", "requests"])
    import openpyxl
    from bs4 import BeautifulSoup

class MultiSourceKaohsiungScraper:
    def __init__(self, debug_mode=True, show_browser=False):
        self.debug_mode = debug_mode
        self.show_browser = show_browser
        self.setup_logging()
        self.driver = None
        self.shops_data = []
        self.target_shops = 2000
        self.data_lock = Lock()
        
        # 搜尋關鍵字
        self.beauty_keywords = [
            "美甲", "美睫", "耳燭", "採耳", "熱蠟", "美容", "美體", 
            "指甲彩繪", "睫毛嫁接", "美甲工作室", "美睫工作室",
            "nail", "eyelash", "美甲店", "美睫店", "美容院"
        ]
        
        # 高雄地區
        self.kaohsiung_areas = [
            "高雄市", "高雄", "鳳山", "左營", "楠梓", "三民", "苓雅", 
            "新興", "前金", "鼓山", "前鎮", "小港", "仁武", "大社", 
            "岡山", "路竹", "橋頭", "燕巢", "大樹", "大寮", "林園", 
            "鳥松", "旗山", "美濃"
        ]
        
        # 用戶代理
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0"
        ]
        
    def setup_logging(self):
        """設定日誌"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('multi_source_scraper.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def debug_print(self, message, level="INFO"):
        """輸出訊息"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        symbols = {
            "INFO": "ℹ️", "SUCCESS": "✅", "ERROR": "❌", "WARNING": "⚠️",
            "EXTRACT": "🔍", "SAVE": "💾", "TARGET": "🎯", "PLATFORM": "🌐"
        }
        symbol = symbols.get(level, "📋")
        print(f"[{timestamp}] {symbol} {message}")
        if self.debug_mode:
            self.logger.info(f"{level}: {message}")
    
    def setup_driver(self):
        """設定瀏覽器"""
        try:
            self.debug_print("🦊 設定Firefox瀏覽器...", "INFO")
            
            options = Options()
            if not self.show_browser:
                options.add_argument("--headless")
            
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            options.add_argument("--disable-extensions")
            options.add_argument("--width=1920")
            options.add_argument("--height=1080")
            
            # 性能優化
            prefs = {
                "permissions.default.image": 2,
                "dom.webnotifications.enabled": False,
                "media.autoplay.enabled": False,
                "general.useragent.override": random.choice(self.user_agents)
            }
            
            for key, value in prefs.items():
                options.set_preference(key, value)
            
            options.log.level = "fatal"
            
            self.driver = webdriver.Firefox(options=options)
            self.driver.set_window_size(1920, 1080)
            
            self.debug_print("✅ Firefox設定完成", "SUCCESS")
            return True
            
        except Exception as e:
            self.debug_print(f"❌ Firefox設定失敗: {e}", "ERROR")
            return False
    
    def get_session(self):
        """獲取HTTP會話"""
        session = requests.Session()
        session.headers.update({
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-TW,zh;q=0.9,en;q=0.8',
            'Connection': 'keep-alive',
        })
        return session
    
    def add_shop_data(self, shop_info):
        """安全添加店家資料"""
        with self.data_lock:
            # 檢查重複
            for existing in self.shops_data:
                if (existing['name'].lower().strip() == shop_info['name'].lower().strip() or
                    (existing.get('phone', '') == shop_info.get('phone', '') and 
                     shop_info.get('phone', '') not in ['', '需進一步查詢'])):
                    return False
            
            self.shops_data.append(shop_info)
            self.debug_print(f"✅ 新增店家 ({len(self.shops_data)}): {shop_info['name']}", "SUCCESS")
            return True
    
    def scrape_google_search(self, keyword, area):
        """Google搜尋"""
        try:
            self.debug_print(f"🔍 Google搜尋: {keyword} {area}", "PLATFORM")
            
            if not self.driver:
                if not self.setup_driver():
                    return []
            
            search_query = f"{keyword} {area} 店家 電話 地址"
            search_url = f"https://www.google.com/search?q={urllib.parse.quote(search_query)}"
            
            self.driver.get(search_url)
            time.sleep(3)
            
            shops = []
            
            # 提取搜尋結果
            results = self.driver.find_elements(By.CSS_SELECTOR, "div.g")[:15]
            
            for result in results:
                try:
                    # 標題
                    title_elem = result.find_element(By.CSS_SELECTOR, "h3")
                    title = title_elem.text.strip() if title_elem else ""
                    
                    if not title or len(title) < 3:
                        continue
                    
                    # 檢查相關性
                    if not any(kw in title.lower() for kw in ['美甲', '美睫', '美容', '指甲', '睫毛']):
                        continue
                    
                    # 描述文字
                    desc_elem = result.find_element(By.CSS_SELECTOR, "span")
                    desc_text = desc_elem.text if desc_elem else ""
                    
                    # 提取電話
                    phone_match = re.search(r'0\d{1,2}[-\s]?\d{6,8}|09\d{8}', desc_text)
                    phone = phone_match.group() if phone_match else '需進一步查詢'
                    
                    # 提取地址
                    addr_match = re.search(r'高雄[^,\n]{5,40}', desc_text)
                    address = addr_match.group() if addr_match else f'{area}（詳細地址需進一步查詢）'
                    
                    shop_info = {
                        'name': title,
                        'address': address,
                        'phone': phone,
                        'line_contact': '需進一步查詢',
                        'source': 'Google搜尋',
                        'google_maps_url': ''
                    }
                    
                    shops.append(shop_info)
                    
                except Exception as e:
                    continue
            
            self.debug_print(f"📊 Google搜尋找到 {len(shops)} 家店", "SUCCESS")
            return shops
            
        except Exception as e:
            self.debug_print(f"❌ Google搜尋失敗: {e}", "ERROR")
            return []
    
    def scrape_business_websites(self, keyword, area):
        """搜尋商業網站"""
        try:
            self.debug_print(f"🏢 商業網站搜尋: {keyword} {area}", "PLATFORM")
            
            session = self.get_session()
            shops = []
            
            # 商業網站列表
            websites = [
                f"https://www.iyp.com.tw/search.html?q={urllib.parse.quote(keyword + ' ' + area)}",
                f"https://www.518.com.tw/job-search-1.html?i=1&am=1&kwop=7&kw={urllib.parse.quote(keyword)}",
                f"https://www.104.com.tw/jobs/search/?keyword={urllib.parse.quote(keyword + ' ' + area)}"
            ]
            
            for url in websites:
                try:
                    response = session.get(url, timeout=15)
                    if response.status_code != 200:
                        continue
                    
                    soup = BeautifulSoup(response.content, 'html.parser')
                    
                    # 通用商家資訊提取
                    business_elements = soup.find_all(['div', 'li', 'article'], 
                                                    class_=re.compile(r'(business|company|shop|store|job)', re.I))[:20]
                    
                    for elem in business_elements:
                        try:
                            text_content = elem.get_text()
                            
                            # 查找包含美甲美睫關鍵字的內容
                            if any(kw in text_content.lower() for kw in self.beauty_keywords):
                                
                                # 提取店名
                                name_elem = elem.find(['h1', 'h2', 'h3', 'h4', 'a', 'strong'])
                                name = name_elem.get_text().strip() if name_elem else ""
                                
                                if not name or len(name) < 3 or len(name) > 50:
                                    continue
                                
                                # 提取電話
                                phone_match = re.search(r'0\d{1,2}[-\s]?\d{6,8}|09\d{8}', text_content)
                                phone = phone_match.group() if phone_match else '需進一步查詢'
                                
                                # 提取地址
                                addr_match = re.search(r'高雄[市]?[^,\n]{5,40}', text_content)
                                address = addr_match.group() if addr_match else f'{area}（詳細地址需進一步查詢）'
                                
                                shop_info = {
                                    'name': name,
                                    'address': address,
                                    'phone': phone,
                                    'line_contact': '需進一步查詢',
                                    'source': '商業網站',
                                    'google_maps_url': ''
                                }
                                
                                shops.append(shop_info)
                                
                        except Exception as e:
                            continue
                            
                except Exception as e:
                    self.debug_print(f"⚠️ 網站 {url} 搜尋失敗: {e}", "WARNING")
                    continue
                
                # 避免過於頻繁的請求
                time.sleep(random.uniform(1, 3))
            
            self.debug_print(f"📊 商業網站找到 {len(shops)} 家店", "SUCCESS")
            return shops
            
        except Exception as e:
            self.debug_print(f"❌ 商業網站搜尋失敗: {e}", "ERROR")
            return []
    
    def scrape_social_media(self, keyword, area):
        """搜尋社群媒體"""
        try:
            self.debug_print(f"📱 社群媒體搜尋: {keyword} {area}", "PLATFORM")
            
            if not self.driver:
                if not self.setup_driver():
                    return []
            
            shops = []
            
            # Facebook搜尋
            try:
                search_query = f"{keyword} {area}"
                fb_url = f"https://www.facebook.com/search/pages/?q={urllib.parse.quote(search_query)}"
                
                self.driver.get(fb_url)
                time.sleep(5)
                
                # 提取Facebook頁面
                page_elements = self.driver.find_elements(By.CSS_SELECTOR, "[role='article']")[:10]
                
                for elem in page_elements:
                    try:
                        text_content = elem.text
                        
                        # 查找店名
                        name_lines = text_content.split('\n')
                        for line in name_lines:
                            if any(kw in line.lower() for kw in self.beauty_keywords) and len(line) < 50:
                                name = line.strip()
                                
                                # 提取聯絡資訊
                                phone_match = re.search(r'0\d{1,2}[-\s]?\d{6,8}|09\d{8}', text_content)
                                phone = phone_match.group() if phone_match else '需進一步查詢'
                                
                                addr_match = re.search(r'高雄[^,\n]{5,40}', text_content)
                                address = addr_match.group() if addr_match else f'{area}（詳細地址需進一步查詢）'
                                
                                shop_info = {
                                    'name': name,
                                    'address': address,
                                    'phone': phone,
                                    'line_contact': '可能有LINE，需進一步查詢',
                                    'source': 'Facebook',
                                    'google_maps_url': ''
                                }
                                
                                shops.append(shop_info)
                                break
                                
                    except Exception as e:
                        continue
                        
            except Exception as e:
                self.debug_print(f"⚠️ Facebook搜尋失敗: {e}", "WARNING")
            
            self.debug_print(f"📊 社群媒體找到 {len(shops)} 家店", "SUCCESS")
            return shops
            
        except Exception as e:
            self.debug_print(f"❌ 社群媒體搜尋失敗: {e}", "ERROR")
            return []
    
    def scrape_directory_sites(self, keyword, area):
        """搜尋目錄網站"""
        try:
            self.debug_print(f"📋 目錄網站搜尋: {keyword} {area}", "PLATFORM")
            
            session = self.get_session()
            shops = []
            
            # 目錄網站
            directory_sites = [
                f"https://www.lifego.tw/search?q={urllib.parse.quote(keyword + ' ' + area)}",
                f"https://www.walkerland.com.tw/search?q={urllib.parse.quote(keyword + ' ' + area)}",
                f"https://www.gomaji.com/search?keyword={urllib.parse.quote(keyword + ' ' + area)}"
            ]
            
            for site_url in directory_sites:
                try:
                    response = session.get(site_url, timeout=15)
                    if response.status_code != 200:
                        continue
                    
                    soup = BeautifulSoup(response.content, 'html.parser')
                    
                    # 提取商家卡片
                    cards = soup.find_all(['div', 'article', 'section'], 
                                        class_=re.compile(r'(card|item|business|shop|store)', re.I))[:15]
                    
                    for card in cards:
                        try:
                            card_text = card.get_text()
                            
                            # 檢查相關性
                            if not any(kw in card_text.lower() for kw in self.beauty_keywords):
                                continue
                            
                            # 提取店名
                            title_elem = card.find(['h1', 'h2', 'h3', 'h4', 'a'])
                            if title_elem:
                                name = title_elem.get_text().strip()
                                
                                if len(name) < 3 or len(name) > 50:
                                    continue
                                
                                # 提取聯絡資訊
                                phone_match = re.search(r'0\d{1,2}[-\s]?\d{6,8}|09\d{8}', card_text)
                                phone = phone_match.group() if phone_match else '需進一步查詢'
                                
                                addr_match = re.search(r'高雄[^,\n]{5,40}', card_text)
                                address = addr_match.group() if addr_match else f'{area}（詳細地址需進一步查詢）'
                                
                                shop_info = {
                                    'name': name,
                                    'address': address,
                                    'phone': phone,
                                    'line_contact': '需進一步查詢',
                                    'source': '目錄網站',
                                    'google_maps_url': ''
                                }
                                
                                shops.append(shop_info)
                                
                        except Exception as e:
                            continue
                            
                except Exception as e:
                    continue
                
                time.sleep(random.uniform(1, 2))
            
            self.debug_print(f"📊 目錄網站找到 {len(shops)} 家店", "SUCCESS")
            return shops
            
        except Exception as e:
            self.debug_print(f"❌ 目錄網站搜尋失敗: {e}", "ERROR")
            return []
    
    def run_multi_source_scraping(self):
        """執行多源搜尋"""
        start_time = time.time()
        
        try:
            self.debug_print("🚀 開始多源整合搜尋", "INFO")
            self.debug_print(f"🎯 目標：{self.target_shops} 家店家", "TARGET")
            self.debug_print("🌐 搜尋平台：Google搜尋、商業網站、社群媒體、目錄網站", "INFO")
            print("=" * 70)
            
            # 搜尋任務
            search_tasks = []
            for keyword in self.beauty_keywords[:6]:  # 前6個關鍵字
                for area in self.kaohsiung_areas[:8]:  # 前8個地區
                    search_tasks.append((keyword, area))
            
            self.debug_print(f"📋 準備 {len(search_tasks)} 個搜尋任務", "INFO")
            
            # 執行搜尋
            task_count = 0
            for keyword, area in search_tasks:
                task_count += 1
                progress = (task_count / len(search_tasks)) * 100
                
                self.debug_print(f"[{task_count}/{len(search_tasks)}] 搜尋: {keyword} @ {area} ({progress:.1f}%)", "INFO")
                
                # 各平台搜尋
                platforms = [
                    ("Google搜尋", self.scrape_google_search),
                    ("商業網站", self.scrape_business_websites),
                    ("社群媒體", self.scrape_social_media),
                    ("目錄網站", self.scrape_directory_sites)
                ]
                
                for platform_name, scrape_func in platforms:
                    try:
                        shops = scrape_func(keyword, area)
                        for shop in shops:
                            if len(self.shops_data) >= self.target_shops:
                                break
                            self.add_shop_data(shop)
                        
                        if len(self.shops_data) >= self.target_shops:
                            self.debug_print(f"🎯 達到目標！", "TARGET")
                            break
                            
                    except Exception as e:
                        self.debug_print(f"⚠️ {platform_name}搜尋失敗: {e}", "WARNING")
                        continue
                
                if len(self.shops_data) >= self.target_shops:
                    break
                
                # 進度報告
                if len(self.shops_data) % 100 == 0 and len(self.shops_data) > 0:
                    completion = (len(self.shops_data) / self.target_shops) * 100
                    self.debug_print(f"📊 進度: {len(self.shops_data)}/{self.target_shops} ({completion:.1f}%)", "INFO")
                
                # 搜尋間隔
                time.sleep(random.uniform(2, 4))
            
            # 儲存結果
            if self.shops_data:
                self.save_results()
                
                elapsed_time = time.time() - start_time
                minutes = int(elapsed_time // 60)
                seconds = int(elapsed_time % 60)
                
                self.debug_print(f"✅ 搜尋完成！", "SUCCESS")
                self.debug_print(f"📊 收集店家: {len(self.shops_data)} 家", "SUCCESS")
                self.debug_print(f"⏱️ 執行時間: {minutes}分{seconds}秒", "SUCCESS")
                
                # 平台統計
                platform_stats = {}
                for shop in self.shops_data:
                    platform = shop.get('source', '未知')
                    platform_stats[platform] = platform_stats.get(platform, 0) + 1
                
                self.debug_print("📈 各平台貢獻:", "INFO")
                for platform, count in platform_stats.items():
                    percentage = (count / len(self.shops_data)) * 100
                    self.debug_print(f"   {platform}: {count} 家 ({percentage:.1f}%)", "INFO")
                
            else:
                self.debug_print("❌ 未收集到店家資料", "ERROR")
            
            return True
            
        except Exception as e:
            self.debug_print(f"❌ 搜尋失敗: {e}", "ERROR")
            return False
        
        finally:
            if self.driver:
                try:
                    self.driver.quit()
                except:
                    pass
    
    def save_results(self):
        """儲存結果"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"高雄美甲美睫店家_多源整合_{len(self.shops_data)}家_{timestamp}"
            
            # Excel
            excel_file = f"{filename}.xlsx"
            df = pd.DataFrame(self.shops_data)
            df.to_excel(excel_file, index=False, engine='openpyxl')
            
            # CSV
            csv_file = f"{filename}.csv"
            df.to_csv(csv_file, index=False, encoding='utf-8-sig')
            
            self.debug_print(f"💾 Excel: {excel_file}", "SAVE")
            self.debug_print(f"💾 CSV: {csv_file}", "SAVE")
            
            # 統計完整性
            complete_phone = sum(1 for shop in self.shops_data 
                               if shop.get('phone', '') not in ['需進一步查詢', ''])
            complete_address = sum(1 for shop in self.shops_data 
                                 if '詳細地址需進一步查詢' not in shop.get('address', ''))
            
            self.debug_print(f"📊 電話完整性: {complete_phone}/{len(self.shops_data)} ({complete_phone/len(self.shops_data)*100:.1f}%)", "INFO")
            self.debug_print(f"📊 地址完整性: {complete_address}/{len(self.shops_data)} ({complete_address/len(self.shops_data)*100:.1f}%)", "INFO")
            
            return True
            
        except Exception as e:
            self.debug_print(f"❌ 儲存失敗: {e}", "ERROR")
            return False

def main():
    """主程式"""
    print("🚀 高雄美甲美睫店家多源整合爬蟲")
    print()
    print("🎯 搜尋目標：")
    print("   - 收集2000家店家資料")
    print("   - 店名、地址、電話、LINE")
    print("   - 多平台整合搜尋")
    print()
    print("🌐 搜尋平台：")
    print("   - Google搜尋結果")
    print("   - 商業網站（518、104等）")
    print("   - 社群媒體（Facebook）")
    print("   - 目錄網站（生活網站）")
    print()
    print("⚡ 優勢：")
    print("   - 多源整合，數量更多")
    print("   - 速度較快，效率更高")
    print("   - 自動去重，避免重複")
    print()
    
    # 瀏覽器設定
    print("🖥️ 瀏覽器設定：")
    print("   1. 無頭模式 (推薦，速度快)")
    print("   2. 顯示視窗 (可觀察進度)")
    
    while True:
        choice = input("請選擇 (1/2): ").strip()
        if choice == "1":
            show_browser = False
            print("✅ 選擇：無頭模式")
            break
        elif choice == "2":
            show_browser = True
            print("✅ 選擇：顯示視窗")
            break
        else:
            print("❌ 請輸入 1 或 2")
    
    print("-" * 50)
    confirm = input("確定開始搜尋？(y/n): ").strip().lower()
    if confirm != 'y':
        print("程式已取消")
        return
    
    scraper = MultiSourceKaohsiungScraper(debug_mode=True, show_browser=show_browser)
    scraper.run_multi_source_scraping()

if __name__ == "__main__":
    main() 