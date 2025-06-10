#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Google 地圖店家資訊擷取程式 (高速版 - Firefox)
專為快速收集2000家店家設計，使用Firefox避免與Chrome版衝突
- 優化搜索半徑到8公里，減少搜索次數
- 聚焦主要商業區，避免過度細分
- 每輪處理20+家店家，大幅提升效率
- 簡化詳細信息獲取，先保存基本信息
- 大幅減少等待時間
"""

import time
import random
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from selenium.webdriver.common.action_chains import ActionChains
import logging
from datetime import datetime
import re
import urllib.parse

try:
    import openpyxl
except ImportError:
    print("⚠️ 未安裝 openpyxl，將安裝該套件以支援 Excel 輸出...")
    import subprocess
    import sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "openpyxl"])
    import openpyxl

class GoogleMapsTurboFirefoxScraper:
    def __init__(self, debug_mode=True):
        self.debug_mode = debug_mode
        self.setup_logging()
        self.driver = None
        self.shops_data = []
        self.current_location_shops = []
        self.current_location = None
        self.search_radius_km = 8  # 增加搜尋半徑到8公里
        self.target_shops = 2000
        self.max_shops_per_search = 25  # 每次搜索最多處理25家店
        
    def setup_logging(self):
        """設定日誌記錄"""
        log_level = logging.DEBUG if self.debug_mode else logging.INFO
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('scraper_turbo_firefox.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def debug_print(self, message, level="INFO"):
        """詳細的debug輸出"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        symbols = {
            "INFO": "ℹ️",
            "SUCCESS": "✅", 
            "ERROR": "❌",
            "WARNING": "⚠️",
            "TURBO": "🚀",
            "FIREFOX": "🦊",
            "EXTRACT": "🔍",
            "WAIT": "⏳",
            "SAVE": "💾"
        }
        symbol = symbols.get(level, "📋")
        print(f"[{timestamp}] {symbol} {message}")
        if self.debug_mode:
            self.logger.info(f"{level}: {message}")
    
    def setup_driver(self):
        """設定Firefox瀏覽器驅動器"""
        try:
            self.debug_print("正在設定Firefox高速瀏覽器...", "FIREFOX")
            firefox_options = Options()
            
            # Firefox高速模式設定
            firefox_options.add_argument("--no-sandbox")
            firefox_options.add_argument("--disable-dev-shm-usage")
            firefox_options.add_argument("--width=1920")
            firefox_options.add_argument("--height=1080")
            
            # 禁用圖片和廣告以提高速度
            firefox_options.set_preference("permissions.default.image", 2)
            firefox_options.set_preference("dom.ipc.plugins.enabled.libflashplayer.so", False)
            firefox_options.set_preference("media.volume_scale", "0.0")
            
            # 禁用不必要的功能
            firefox_options.set_preference("geo.enabled", False)
            firefox_options.set_preference("geo.provider.use_corelocation", False)
            firefox_options.set_preference("geo.prompt.testing", False)
            firefox_options.set_preference("geo.prompt.testing.allow", False)
            
            # 設定用戶代理
            firefox_options.set_preference("general.useragent.override", 
                "Mozilla/5.0 (X11; Linux x86_64; rv:91.0) Gecko/20100101 Firefox/91.0")
            
            if not self.debug_mode:
                firefox_options.add_argument("--headless")
            
            self.driver = webdriver.Firefox(options=firefox_options)
            self.driver.set_window_size(1920, 1080)
            
            self.debug_print("Firefox高速瀏覽器設定完成", "SUCCESS")
            return True
            
        except Exception as e:
            self.debug_print(f"Firefox瀏覽器設定失敗: {e}", "ERROR")
            return False
    
    def open_google_maps(self):
        """開啟 Google 地圖"""
        try:
            self.debug_print("正在開啟 Google 地圖...", "FIREFOX")
            self.driver.get("https://www.google.com/maps")
            
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            time.sleep(2)  # 減少等待時間
            self.handle_consent_popup()
            
            self.debug_print("Google 地圖載入完成", "SUCCESS")
            return True
            
        except Exception as e:
            self.debug_print(f"開啟 Google 地圖失敗: {e}", "ERROR")
            return False
    
    def handle_consent_popup(self):
        """處理同意視窗"""
        try:
            consent_xpaths = [
                "//button[contains(text(), '接受全部') or contains(text(), 'Accept all')]",
                "//button[contains(text(), '接受') or contains(text(), 'Accept')]", 
                "//button[contains(text(), '同意') or contains(text(), 'Agree')]"
            ]
            
            for xpath in consent_xpaths:
                try:
                    consent_button = WebDriverWait(self.driver, 1).until(
                        EC.element_to_be_clickable((By.XPATH, xpath))
                    )
                    consent_button.click()
                    self.debug_print("已點擊同意按鈕", "SUCCESS")
                    time.sleep(1)
                    return True
                except:
                    continue
                    
            return True
            
        except Exception as e:
            return True
    
    def set_location(self, location_name):
        """設定定位到指定地點"""
        try:
            self.debug_print(f"🦊 Firefox高速定位到: {location_name}", "FIREFOX")
            
            if self.current_location != location_name:
                self.current_location_shops = []
            
            search_box = WebDriverWait(self.driver, 8).until(
                EC.presence_of_element_located((By.ID, "searchboxinput"))
            )
            
            search_box.clear()
            time.sleep(0.5)
            
            # 快速輸入
            search_box.send_keys(location_name)
            time.sleep(0.8)
            search_box.send_keys(Keys.ENTER)
            
            time.sleep(3)  # 減少等待時間
            self.current_location = location_name
            return True
            
        except Exception as e:
            self.debug_print(f"定位失敗: {e}", "ERROR")
            return False
    
    def search_nearby_shops_turbo(self, shop_type):
        """高速搜尋附近店家"""
        try:
            self.debug_print(f"🦊 Firefox高速搜尋: {shop_type} (半徑 {self.search_radius_km}km)", "FIREFOX")
            
            search_box = WebDriverWait(self.driver, 8).until(
                EC.presence_of_element_located((By.ID, "searchboxinput"))
            )
            
            search_box.clear()
            time.sleep(0.3)
            
            # 構建高效搜尋查詢
            search_query = f"{shop_type} near {self.current_location}"
            
            # 快速輸入
            search_box.send_keys(search_query)
            time.sleep(0.8)
            search_box.send_keys(Keys.ENTER)
            
            time.sleep(4)  # 減少等待時間
            return True
            
        except Exception as e:
            self.debug_print(f"搜尋失敗: {e}", "ERROR")
            return False
    
    def extract_shop_info_basic(self, link_element):
        """基本版店家資訊擷取 - 只獲取關鍵信息，不點進詳細頁面"""
        try:
            shop_info = {}
            
            # 獲取店家名稱
            name = None
            
            # 方式1: aria-label
            try:
                name = link_element.get_attribute('aria-label')
                if name and name.strip():
                    name = name.strip()
            except:
                pass
            
            # 方式2: 元素文字
            if not name:
                try:
                    name = link_element.text
                    if name and name.strip():
                        name = name.strip()
                except:
                    pass
            
            # 方式3: 從父元素獲取
            if not name:
                try:
                    parent = link_element.find_element(By.XPATH, "..")
                    name = parent.get_attribute('aria-label') or parent.text
                    if name and name.strip():
                        name = name.strip()
                except:
                    pass
            
            if not name or len(name.strip()) < 2:
                return None
            
            # 清理店家名稱
            name = name.strip()
            prefixes_to_remove = ['搜尋', '前往', '路線', '導航', '評論']
            for prefix in prefixes_to_remove:
                if name.startswith(prefix):
                    name = name[len(prefix):].strip()
            
            if len(name) < 2:
                return None
            
            invalid_keywords = ['undefined', 'null', '載入中', 'loading', '...']
            if any(keyword in name.lower() for keyword in invalid_keywords):
                return None
            
            shop_info['name'] = name
            shop_info['search_location'] = self.current_location
            shop_info['google_maps_url'] = link_element.get_attribute('href')
            shop_info['browser'] = 'Firefox'
            
            # 嘗試從周圍元素快速獲取基本信息
            try:
                # 尋找附近的評分信息
                parent_container = link_element.find_element(By.XPATH, "../../..")
                rating_elements = parent_container.find_elements(By.CSS_SELECTOR, "[aria-label*='星']")
                if rating_elements:
                    rating_text = rating_elements[0].get_attribute('aria-label')
                    shop_info['rating'] = rating_text if rating_text else '評分未提供'
                else:
                    shop_info['rating'] = '評分未提供'
                
                # 尋找地址信息
                address_elements = parent_container.find_elements(By.CSS_SELECTOR, ".fontBodyMedium")
                address_found = False
                for addr_elem in address_elements[:3]:  # 只檢查前3個
                    addr_text = addr_elem.text.strip()
                    if addr_text and ('路' in addr_text or '街' in addr_text or '區' in addr_text):
                        shop_info['address'] = addr_text
                        address_found = True
                        break
                
                if not address_found:
                    shop_info['address'] = '地址未提供'
                    
                # 設定預設值
                shop_info['phone'] = '電話未提供'
                shop_info['hours'] = '營業時間未提供'
                
            except:
                shop_info['address'] = '地址未提供'
                shop_info['phone'] = '電話未提供'
                shop_info['hours'] = '營業時間未提供'
                shop_info['rating'] = '評分未提供'
            
            return shop_info
            
        except Exception as e:
            return None
    
    def scroll_and_extract_turbo(self):
        """高速滾動並擷取店家資訊"""
        try:
            self.debug_print(f"🦊 開始Firefox高速擷取 {self.current_location} 的店家...", "FIREFOX")
            
            container = self.find_scrollable_container()
            if not container:
                return False
            
            last_count = 0
            no_change_count = 0
            max_no_change = 2  # 高速模式：2次無變化停止
            max_scrolls = 5    # 高速模式：最多5次滾動
            scroll_count = 0
            
            while scroll_count < max_scrolls and no_change_count < max_no_change:
                scroll_count += 1
                
                self.debug_print(f"🦊 第 {scroll_count} 次Firefox高速滾動", "FIREFOX")
                
                # 高速擷取當前店家
                current_shops = self.extract_current_shops_turbo()
                current_count = len(self.current_location_shops)
                
                if current_count == last_count:
                    no_change_count += 1
                else:
                    no_change_count = 0
                    last_count = current_count
                    self.debug_print(f"🦊 本輪新增了 {len(current_shops)} 家店家", "SUCCESS")
                
                # 檢查是否達到目標
                if len(self.shops_data) >= self.target_shops:
                    self.debug_print(f"🎯 達到{self.target_shops}家目標，停止滾動", "SUCCESS")
                    break
                
                # 檢查是否已獲取足夠店家
                if len(current_shops) >= self.max_shops_per_search:
                    self.debug_print(f"🦊 已獲取 {len(current_shops)} 家店家，停止本次搜索", "FIREFOX")
                    break
                
                if scroll_count < max_scrolls:
                    # 高速滾動
                    scroll_amount = 800
                    self.driver.execute_script(f"arguments[0].scrollTop += {scroll_amount}", container)
                    time.sleep(0.8)  # 減少等待時間
                    
                    self.driver.execute_script(f"window.scrollBy(0, {scroll_amount//2});")
                    time.sleep(0.5)
                
                # 檢查是否達到目標
                if len(self.shops_data) >= self.target_shops:
                    break
            
            final_count = len(self.current_location_shops)
            self.debug_print(f"🦊 {self.current_location} Firefox高速搜尋完成！新增 {final_count} 家店", "SUCCESS")
            
            return len(self.shops_data) < self.target_shops
            
        except Exception as e:
            self.debug_print(f"Firefox高速滾動擷取失敗: {e}", "ERROR")
            return False
    
    def extract_current_shops_turbo(self):
        """高速擷取當前可見的店家"""
        try:
            # 使用高效的選擇器
            shop_selectors = [
                "a[href*='/maps/place/']"
            ]
            
            all_shop_links = []
            for selector in shop_selectors:
                try:
                    links = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for link in links:
                        href = link.get_attribute('href')
                        if href and '/maps/place/' in href:
                            all_shop_links.append(link)
                except:
                    continue
            
            # 去除重複連結
            unique_links = []
            seen_hrefs = set()
            for link in all_shop_links:
                href = link.get_attribute('href')
                if href and href not in seen_hrefs:
                    unique_links.append(link)
                    seen_hrefs.add(href)
            
            shop_links = unique_links
            self.debug_print(f"🦊 Firefox找到 {len(shop_links)} 個店家連結", "FIREFOX")
            
            new_shops = []
            processed_count = 0
            
            # 高速模式：處理更多店家
            max_process = min(self.max_shops_per_search, len(shop_links))
            
            for i, link in enumerate(shop_links[:max_process]):
                try:
                    # 快速檢查重複
                    try:
                        pre_name = link.get_attribute('aria-label') or link.text
                        if pre_name and pre_name.strip():
                            temp_shop = {
                                'name': pre_name.strip(), 
                                'google_maps_url': link.get_attribute('href'), 
                                'search_location': self.current_location
                            }
                            if not self.is_new_shop_fast(temp_shop):
                                continue
                    except:
                        pass
                    
                    shop_info = self.extract_shop_info_basic(link)
                    if not shop_info:
                        continue
                    
                    if self.is_new_shop_fast(shop_info):
                        self.shops_data.append(shop_info)
                        self.current_location_shops.append(shop_info)
                        new_shops.append(shop_info)
                        
                        processed_count += 1
                        
                        if processed_count % 5 == 0:
                            self.debug_print(f"🦊 Firefox已處理 {processed_count} 家店家", "FIREFOX")
                        
                        # 檢查是否達到目標
                        if len(self.shops_data) >= self.target_shops:
                            self.debug_print(f"🎯 達到{self.target_shops}家目標！", "SUCCESS")
                            break
                        
                        # 檢查是否達到單次搜索上限
                        if processed_count >= self.max_shops_per_search:
                            break
                    
                except Exception as e:
                    continue
            
            if new_shops:
                self.debug_print(f"🦊 Firefox本次新增 {len(new_shops)} 家店家，總計 {len(self.shops_data)}/{self.target_shops}", "SUCCESS")
            
            return new_shops
            
        except Exception as e:
            self.debug_print(f"Firefox高速擷取店家錯誤: {e}", "ERROR")
            return []
    
    def find_scrollable_container(self):
        """找到可滾動的容器"""
        try:
            result_selectors = [
                "div[role='main']",
                "div[aria-label*='結果']",
                "[role='main'] > div",
                "body"
            ]
            
            for selector in result_selectors:
                try:
                    element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if element and element.is_displayed():
                        return element
                except:
                    continue
            
            return self.driver.find_element(By.TAG_NAME, "body")
            
        except Exception as e:
            return None
    
    def is_new_shop_fast(self, shop_info):
        """快速檢查是否為新店家"""
        if not shop_info or not shop_info.get('name'):
            return False
            
        shop_name = shop_info['name'].strip().lower()
        shop_url = shop_info.get('google_maps_url', '').strip()
        
        # 快速檢查：只檢查名稱和URL的完全匹配
        for existing_shop in self.shops_data:
            existing_name = existing_shop.get('name', '').strip().lower()
            existing_url = existing_shop.get('google_maps_url', '').strip()
            
            if existing_name == shop_name or (shop_url and existing_url and shop_url == existing_url):
                return False
        
        return True
    
    def save_to_excel(self, filename=None, save_csv=True):
        """儲存資料到 Excel 和 CSV 檔案"""
        try:
            if not self.shops_data:
                self.debug_print("沒有資料可以儲存", "ERROR")
                return False
            
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"高雄美甲美睫店家_Firefox高速版_{timestamp}"
            
            self.debug_print("🦊 開始Firefox高速儲存資料...", "SAVE")
            
            # 快速去重
            unique_shops = []
            seen = set()
            
            for shop in self.shops_data:
                key = (shop['name'], shop.get('google_maps_url', ''))
                if key not in seen:
                    seen.add(key)
                    unique_shops.append(shop)
            
            # 儲存到 Excel
            excel_filename = f"{filename}.xlsx"
            df = pd.DataFrame(unique_shops)
            df.to_excel(excel_filename, index=False, engine='openpyxl')
            self.debug_print(f"✅ 成功儲存Excel: {excel_filename}", "SUCCESS")
            
            # 同時儲存 CSV
            if save_csv:
                csv_filename = f"{filename}.csv"
                df.to_csv(csv_filename, index=False, encoding='utf-8-sig')
                self.debug_print(f"✅ 同時儲存CSV: {csv_filename}", "SUCCESS")
            
            self.debug_print(f"🦊 Firefox高速儲存完成！共 {len(unique_shops)} 筆店家資料", "SUCCESS")
            
            # 統計資料
            self.debug_print("📊 儲存統計:", "INFO")
            self.debug_print(f"   - 總店家數: {len(unique_shops)}", "INFO")
            
            # 按搜尋地點分組
            location_stats = {}
            for shop in unique_shops:
                location = shop.get('search_location', '未知地點')
                location_stats[location] = location_stats.get(location, 0) + 1
            
            self.debug_print("各地點店家數量:", "INFO")
            for location, count in sorted(location_stats.items(), key=lambda x: x[1], reverse=True)[:10]:
                self.debug_print(f"   - {location}: {count} 家", "INFO")
            
            return True
            
        except Exception as e:
            self.debug_print(f"儲存失敗: {e}", "ERROR")
            return False
    
    def get_key_search_locations(self):
        """獲取關鍵搜索地點列表 - 聚焦主要商業區"""
        
        # 主要商業核心區域（高密度區域）
        core_locations = [
            # 高雄市中心核心
            "高雄火車站",
            "五福商圈",
            "新崛江商圈", 
            "大立百貨",
            "漢來大飯店",
            "統一夢時代購物中心",
            "中山大學",
            "高雄醫學大學",
            "文化中心",
            "六合夜市",
            "瑞豐夜市",
            
            # 鳳山區重點
            "鳳山火車站",
            "鳳山區公所",
            "大東文化藝術中心",
            "正修科技大學",
            "澄清湖",
            
            # 左營楠梓區重點
            "高雄左營站",
            "新光三越左營店",
            "漢神巨蛋",
            "楠梓火車站",
            "高雄大學",
            "右昌",
            
            # 三民區重點
            "建工路商圈",
            "民族路商圈",
            "九如路",
            "十全路",
            
            # 苓雅區重點
            "苓雅區公所",
            "成功路",
            "光華路",
            "青年路",
            
            # 前鎮小港區重點
            "草衙道",
            "小港機場",
            "前鎮區公所",
            "獅甲",
            
            # 鼓山區重點
            "西子灣",
            "駁二藝術特區",
            "美術館",
            "內惟",
            
            # 岡山區重點
            "岡山火車站",
            "岡山區公所",
            
            # 其他重要區域
            "路竹火車站",
            "橋頭火車站",
            "大寮區公所",
            "林園區公所",
            "旗山火車站",
            "美濃區公所",
            
            # 重要購物中心
            "大遠百",
            "太平洋SOGO",
            "環球購物中心",
            "義大世界",
            "好市多高雄店",
            "IKEA高雄店",
            
            # 重要醫院
            "高雄榮總",
            "高雄醫學大學附設醫院",
            "長庚紀念醫院",
            "義大醫院",
            
            # 重要夜市
            "光華夜市",
            "南華路夜市",
            "興中夜市",
            "凱旋夜市",
            "青年夜市"
        ]
        
        self.debug_print(f"🦊 Firefox高速模式：聚焦 {len(core_locations)} 個核心商業區", "FIREFOX")
        self.debug_print(f"   🎯 搜索半徑: {self.search_radius_km}km (高效覆蓋)", "INFO")
        self.debug_print(f"   🦊 每次搜索處理: {self.max_shops_per_search} 家店", "INFO")
        
        return core_locations

    def run_turbo_scraping(self):
        """執行Firefox高速版店家資訊擷取"""
        start_time = time.time()
        
        try:
            self.debug_print("🦊 開始執行Firefox高速擷取程式", "FIREFOX")
            self.debug_print("⚡ 專為快速收集2000家店家設計", "TURBO")
            self.debug_print(f"🎯 搜尋半徑: {self.search_radius_km} 公里 (高效模式)", "INFO")
            self.debug_print(f"🦊 每次處理: {self.max_shops_per_search} 家店家", "INFO")
            self.debug_print("🔧 優化特色：Firefox瀏覽器、大半徑搜索、快速基本信息", "INFO")
            print("=" * 80)
            
            if not self.setup_driver():
                return False
            
            if not self.open_google_maps():
                return False
            
            # 高速模式：聚焦核心地點
            locations = self.get_key_search_locations()
            
            # 高速模式：美甲美睫相關店家類型
            shop_types = ["美甲", "美睫", "指甲彩繪", "手足保養"]
            
            self.debug_print("【Firefox高速搜索模式】設定：", "FIREFOX")
            self.debug_print(f"📍 核心地點: {len(locations)} 個商業區", "INFO")
            self.debug_print(f"🏪 店家類型: {len(shop_types)} 種類型", "INFO")
            self.debug_print(f"🎯 搜索半徑: {self.search_radius_km}km", "INFO")
            self.debug_print(f"🦊 每輪處理: {self.max_shops_per_search}家店家", "INFO")
            self.debug_print(f"🔍 預估搜尋次數: {len(locations) * len(shop_types)} 次", "INFO")
            self.debug_print("⏰ 預估完成時間: 30-60分鐘", "TURBO")
            print("-" * 70)
            
            total_searches = len(locations) * len(shop_types)
            current_search = 0
            
            # 對每個核心地點進行搜尋
            for i, location in enumerate(locations, 1):
                self.debug_print(f"🦊 [{i}/{len(locations)}] Firefox核心區域: {location}", "FIREFOX")
                
                if not self.set_location(location):
                    self.debug_print(f"定位到 '{location}' 失敗，跳過", "ERROR")
                    continue
                
                # 對每種店家類型進行搜尋
                for j, shop_type in enumerate(shop_types, 1):
                    current_search += 1
                    self.debug_print(f"🦊 [{j}/{len(shop_types)}] Firefox搜尋: {shop_type}", "FIREFOX")
                    
                    # 檢查是否達到目標
                    if len(self.shops_data) >= self.target_shops:
                        self.debug_print(f"🎯 達到目標！已收集 {len(self.shops_data)} 家店家", "SUCCESS")
                        break
                    
                    if not self.search_nearby_shops_turbo(shop_type):
                        continue
                    
                    should_continue = self.scroll_and_extract_turbo()
                    if not should_continue:
                        self.debug_print(f"🎯 達到{self.target_shops}家目標，停止搜尋", "SUCCESS")
                        break
                    
                    # 顯示進度
                    progress = (current_search / total_searches) * 100
                    shops_progress = (len(self.shops_data) / self.target_shops) * 100
                    self.debug_print(f"📊 Firefox搜尋進度: {progress:.1f}% | 店家進度: {shops_progress:.1f}% ({len(self.shops_data)}/{self.target_shops})", "FIREFOX")
                    
                    # 高速模式：減少等待時間
                    if current_search < total_searches:
                        time.sleep(random.uniform(0.5, 1.5))
                
                # 檢查是否達到目標
                if len(self.shops_data) >= self.target_shops:
                    self.debug_print("🎯 已達到目標店家數量，停止所有搜尋", "SUCCESS")
                    break
                
                location_shops = len(self.current_location_shops)
                self.debug_print(f"🦊 Firefox '{location}' 完成，新增 {location_shops} 家店，累計 {len(self.shops_data)} 家", "SUCCESS")
                
                # 每完成5個地點，暫存一次結果
                if i % 5 == 0 and self.shops_data:
                    timestamp = datetime.now().strftime("%H%M%S")
                    temp_filename = f"高雄美甲美睫店家_Firefox高速版_暫存_{timestamp}"
                    self.save_to_excel(temp_filename)
                
                # 高速模式：短暫等待
                if i < len(locations):
                    time.sleep(random.uniform(1, 2))
            
            print("\n" + "=" * 80)
            
            # 儲存最終結果
            if self.shops_data:
                self.debug_print("🦊 正在儲存Firefox最終結果...", "SAVE")
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                
                if len(self.shops_data) >= self.target_shops:
                    final_filename = f"高雄美甲美睫店家_Firefox高速版_{self.target_shops}家達標_{timestamp}"
                    self.debug_print(f"🎯 成功達到{self.target_shops}家目標！總共收集 {len(self.shops_data)} 家店家", "SUCCESS")
                else:
                    final_filename = f"高雄美甲美睫店家_Firefox高速版_完整_{timestamp}"
                    
                self.save_to_excel(final_filename)
            else:
                self.debug_print("沒有找到任何店家資料", "ERROR")
            
            elapsed_time = time.time() - start_time
            minutes = elapsed_time // 60
            seconds = elapsed_time % 60
            
            time_str = f"{int(minutes)} 分 {seconds:.1f} 秒"
                
            self.debug_print(f"🦊 Firefox高速執行完成！總時間: {time_str}", "SUCCESS")
            self.debug_print(f"⚡ 完成 {current_search} 次搜尋", "SUCCESS")
            self.debug_print(f"📊 總共發現 {len(self.shops_data)} 家店家", "SUCCESS")
            
            if len(self.shops_data) >= self.target_shops:
                self.debug_print(f"🎯【{self.target_shops}家目標達成！】", "SUCCESS")
            else:
                self.debug_print("【Firefox高速搜索完成】", "SUCCESS")
            
            return True
            
        except Exception as e:
            self.debug_print(f"程式執行失敗: {e}", "ERROR")
            return False
        
        finally:
            if self.driver:
                self.debug_print("正在關閉Firefox瀏覽器...", "INFO")
                time.sleep(1)
                self.driver.quit()
                self.debug_print("Firefox高速程式執行完成", "SUCCESS")

def main():
    """主程式 - Firefox高速版"""
    print("🦊 Google 地圖店家Firefox高速擷取程式")
    print("⚡ 專為快速收集2000家店家設計")
    print("🔧 使用Firefox避免與Chrome版本衝突")
    print()
    print("🎯 Firefox高速優化特色：")
    print("   - 🦊 使用Firefox瀏覽器，避免Chrome衝突")
    print("   - 🚀 搜索半徑增加到8公里，減少搜索次數")
    print("   - 📍 聚焦60個核心商業區，避免過度細分")
    print("   - ⚡ 每輪處理25家店家，大幅提升效率")
    print("   - 🔧 簡化詳細信息獲取，優先收集基本信息")
    print("   - ⏰ 大幅減少等待時間")
    print("   - 🎯 智能停止：達到2000家自動停止")
    print()
    print("📊 效率提升：")
    print("   - 📈 預計速度提升10-15倍")
    print("   - ⏰ 預估完成時間：30-60分鐘")
    print("   - 🎯 每小時可收集400-800家店家")
    print()
    print("📍 覆蓋範圍：")
    print("   - 高雄市中心核心商圈")
    print("   - 各區主要商業區和交通樞紐")
    print("   - 重要購物中心和醫院周邊")
    print("   - 大學城和夜市商圈")
    print()
    print("📋 收集資訊：")
    print("   - 店家名稱、Google Maps連結")
    print("   - 基本地址信息（如可獲取）")
    print("   - 評分信息（如可獲取）")
    print("   - 搜索位置記錄")
    print()
    print("💡 與Chrome版本並行：")
    print("   - 可與詳細版Chrome同時運行")
    print("   - 獨立的日誌文件 scraper_turbo_firefox.log")
    print("   - 不會干擾現有的Chrome進程")
    print("-" * 70)
    
    user_input = input("確定要開始Firefox高速2000家店搜索嗎？(y/n): ").strip().lower()
    if user_input != 'y':
        print("程式已取消")
        return
    
    scraper = GoogleMapsTurboFirefoxScraper(debug_mode=True)
    scraper.run_turbo_scraping()

if __name__ == "__main__":
    main()