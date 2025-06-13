#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
高雄地區美甲美睫店家精準搜索程式 (Firefox版)
專門針對高雄地區進行地址驗證的店家資料收集
目標：收集2000家符合條件的店家（美甲、美睫、耳燭、採耳、熱蠟）
使用Firefox瀏覽器避免Chrome用戶數據目錄衝突問題
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
from selenium.webdriver.firefox.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from selenium.webdriver.common.action_chains import ActionChains
import logging
from datetime import datetime
import re
import urllib.parse

# 確保安裝了 openpyxl
try:
    import openpyxl
except ImportError:
    print("⚠️ 未安裝 openpyxl，將自動安裝...")
    import subprocess
    import sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "openpyxl"])
    import openpyxl

class KaohsiungPrecisionScraper:
    def __init__(self, debug_mode=True):
        self.debug_mode = debug_mode
        self.setup_logging()
        self.driver = None
        self.shops_data = []
        self.target_shops = 2000  # 目標店家數量
        self.search_radius_km = 2  # 搜尋半徑2公里
        
        # 🔑 加入成功版本的等待時間設定
        self.quick_wait = 0.1    # 極短等待時間
        self.medium_wait = 0.3   # 中等等待時間
        self.long_wait = 0.6     # 長等待時間
        
        self.kaohsiung_keywords = [
            '高雄', '鳳山', '左營', '楠梓', '三民', '苓雅', '新興', '前金', 
            '鼓山', '旗津', '前鎮', '小港', '仁武', '大社', '岡山', '路竹',
            '湖內', '茄萣', '永安', '彌陀', '梓官', '橋頭', '燕巢', '田寮',
            '阿蓮', '大樹', '大寮', '林園', '鳥松', '旗山', '美濃', '六龜'
        ]
        
    def setup_logging(self):
        """設定日誌記錄"""
        log_level = logging.DEBUG if self.debug_mode else logging.INFO
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('kaohsiung_scraper.log', encoding='utf-8'),
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
            "CLICK": "👆",
            "EXTRACT": "🔍",
            "WAIT": "⏳",
            "SAVE": "💾",
            "TARGET": "🎯"
        }
        symbol = symbols.get(level, "📋")
        print(f"[{timestamp}] {symbol} {message}")
        if self.debug_mode:
            self.logger.info(f"{level}: {message}")
    
    def setup_driver(self):
        """設定Firefox瀏覽器驅動器"""
        try:
            self.debug_print("正在設定Firefox高速瀏覽器...", "INFO")
            firefox_options = Options()
            
            # 🔑 關鍵：強制無頭模式（與成功版本一致）
            firefox_options.add_argument("--headless")  # 強制無頭模式更穩定
            firefox_options.add_argument("--no-sandbox")
            firefox_options.add_argument("--disable-dev-shm-usage")
            firefox_options.add_argument("--disable-gpu")
            firefox_options.add_argument("--disable-extensions")
            
            # 設定窗口大小
            firefox_options.add_argument("--width=1920")
            firefox_options.add_argument("--height=1080")
            
            # 🚀 完全複製成功版本的偏好設置
            prefs = {
                # 禁用圖片加載
                "permissions.default.image": 2,
                # 禁用通知
                "dom.webnotifications.enabled": False,
                "dom.push.enabled": False,
                # 禁用地理位置
                "geo.enabled": False,
                # 禁用自動更新
                "app.update.enabled": False,
                "app.update.auto": False,
                # 🚀 新增：禁用CSS動畫和過渡效果
                "browser.animation.enabled": False,
                "dom.animations-api.core.enabled": False,
                # 🚀 新增：禁用JavaScript計時器限制
                "dom.min_timeout_value": 1,
                # 🚀 新增：禁用媒體元素
                "media.autoplay.default": 5,
                "media.autoplay.enabled": False,
                # 🚀 新增：優化網路設定
                "network.http.max-connections": 100,
                "network.http.max-connections-per-server": 20,
                # 🚀 新增：禁用插件和擴展
                "plugins.scan.plid.all": False,
                "extensions.checkCompatibility": False,
                # 設置用戶代理
                "general.useragent.override": "Mozilla/5.0 (X11; Linux x86_64; rv:91.0) Gecko/20100101 Firefox/91.0"
            }
            
            for key, value in prefs.items():
                firefox_options.set_preference(key, value)
            
            # 設定日誌級別
            firefox_options.log.level = "fatal"
            
            self.debug_print("🦊 啟動Firefox (無頭模式)...", "INFO")
            self.driver = webdriver.Firefox(options=firefox_options)
            self.driver.set_window_size(1920, 1080)
            
            self.debug_print("Firefox高速瀏覽器設定完成", "SUCCESS")
            return True
            
        except Exception as e:
            self.debug_print(f"Firefox瀏覽器設定失敗: {e}", "ERROR")
            # 嘗試最簡配置
            try:
                self.debug_print("🦊 嘗試最簡Firefox配置...", "INFO")
                simple_options = Options()
                simple_options.add_argument("--headless")  # 強制headless
                self.driver = webdriver.Firefox(options=simple_options)
                self.debug_print("Firefox簡單配置成功", "SUCCESS")
                return True
            except Exception as e2:
                self.debug_print(f"Firefox簡單配置也失敗: {e2}", "ERROR")
                self.debug_print("請確保已安裝 Firefox 瀏覽器和 geckodriver", "INFO")
                return False
    
    def open_google_maps(self):
        """開啟 Google 地圖"""
        try:
            self.debug_print("正在開啟 Google 地圖...", "INFO")
            self.driver.get("https://www.google.com/maps")
            
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            time.sleep(self.quick_wait)  # 使用成功版本的等待時間
            self.handle_consent_popup()
            
            self.debug_print("🚀 Google 地圖載入完成", "SUCCESS")
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
            self.debug_print(f"正在定位到: {location_name}", "INFO")
            
            search_box = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "searchboxinput"))
            )
            
            search_box.clear()
            time.sleep(1)
            
            # 逐字輸入地點名稱
            for char in location_name:
                search_box.send_keys(char)
                time.sleep(random.uniform(0.05, 0.1))
            
            time.sleep(1)
            search_box.send_keys(Keys.ENTER)
            
            self.debug_print(f"等待定位到 {location_name}...", "WAIT")
            time.sleep(6)
            
            self.debug_print(f"成功定位到 {location_name}", "SUCCESS")
            return True
            
        except Exception as e:
            self.debug_print(f"定位失敗: {e}", "ERROR")
            return False
    
    def search_nearby_shops(self, shop_type, location):
        """搜尋附近的店家"""
        try:
            self.debug_print(f"在 {location} 搜尋: {shop_type}", "INFO")
            
            search_box = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "searchboxinput"))
            )
            
            search_box.clear()
            time.sleep(1)
            
            # 構建搜尋查詢，包含地點限制
            search_query = f"{shop_type} near {location} 高雄"
            
            for char in search_query:
                search_box.send_keys(char)
                time.sleep(random.uniform(0.03, 0.08))
            
            time.sleep(1)
            search_box.send_keys(Keys.ENTER)
            
            self.debug_print("等待搜尋結果載入...", "WAIT")
            time.sleep(8)
            
            return True
            
        except Exception as e:
            self.debug_print(f"搜尋失敗: {e}", "ERROR")
            return False
    
    def is_kaohsiung_address(self, address):
        """檢查地址是否在高雄市"""
        if not address or address in ['地址未提供', '地址獲取失敗']:
            return False
            
        address_lower = address.lower()
        
        # 檢查是否包含高雄相關關鍵字
        for keyword in self.kaohsiung_keywords:
            if keyword in address:
                return True
                
        # 檢查郵遞區號（高雄市郵遞區號範圍：800-852）
        postal_code_pattern = r'\b(8[0-4]\d|85[0-2])\b'
        if re.search(postal_code_pattern, address):
            return True
            
        return False
    
    def extract_shop_info(self, link_element):
        """擷取店家基本資訊並驗證地址"""
        try:
            # 獲取店家名稱
            name = None
            
            # 多種方式獲取名稱
            try:
                name = link_element.get_attribute('aria-label')
                if not name:
                    name = link_element.text
                if not name:
                    parent = link_element.find_element(By.XPATH, "..")
                    name = parent.get_attribute('aria-label') or parent.text
            except:
                pass
                
            if not name or len(name.strip()) < 2:
                return None
                
            name = name.strip()
            
            # 基本店家資訊
            shop_info = {
                'name': name,
                'google_maps_url': link_element.get_attribute('href'),
                'address': '地址未提供',
                'phone': '電話未提供'
            }
            
            # 獲取詳細資訊
            main_window = self.driver.current_window_handle
            
            try:
                # 在新分頁開啟店家詳細頁面
                self.driver.execute_script("arguments[0].setAttribute('target', '_blank');", link_element)
                link_element.click()
                time.sleep(3)
                
                # 切換到新分頁
                all_windows = self.driver.window_handles
                if len(all_windows) > 1:
                    self.driver.switch_to.window(all_windows[-1])
                    time.sleep(4)
                    
                    # 獲取地址
                    address = self.extract_address()
                    if address and address != '地址未提供':
                        shop_info['address'] = address
                    
                    # 獲取電話
                    phone = self.extract_phone()
                    if phone and phone != '電話未提供':
                        shop_info['phone'] = phone
                    
                    # 關閉詳細頁面
                    self.driver.close()
                    self.driver.switch_to.window(main_window)
                    time.sleep(2)
                else:
                    # 在當前頁面處理
                    time.sleep(4)
                    address = self.extract_address()
                    if address:
                        shop_info['address'] = address
                    phone = self.extract_phone()
                    if phone:
                        shop_info['phone'] = phone
                    self.driver.back()
                    time.sleep(3)
                    
            except Exception as e:
                # 確保回到主頁面
                if len(self.driver.window_handles) > 1:
                    self.driver.switch_to.window(main_window)
                
            # 驗證地址是否在高雄
            if not self.is_kaohsiung_address(shop_info['address']):
                self.debug_print(f"地址非高雄地區，跳過: {name} - {shop_info['address']}", "WARNING")
                return None
                
            self.debug_print(f"成功擷取高雄店家: {name}", "SUCCESS")
            return shop_info
            
        except Exception as e:
            self.debug_print(f"擷取店家資訊失敗: {e}", "ERROR")
            return None
    
    def extract_address(self):
        """從詳細頁面擷取地址"""
        try:
            address_selectors = [
                "[data-item-id='address'] .fontBodyMedium",
                "[aria-label*='地址']",
                ".rogA2c .fontBodyMedium",
                "div[data-value='Address'] .fontBodyMedium",
                ".Io6YTe .fontBodyMedium"
            ]
            
            for selector in address_selectors:
                try:
                    address_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if address_element and address_element.text.strip():
                        return address_element.text.strip()
                except:
                    continue
                    
            return '地址未提供'
            
        except Exception as e:
            return '地址獲取失敗'
    
    def extract_phone(self):
        """從詳細頁面擷取電話"""
        try:
            phone_selectors = [
                "[data-item-id='phone:tel:'] .fontBodyMedium",
                "[aria-label*='電話']",
                "button[data-value^='phone'] .fontBodyMedium",
                "div[data-value='Phone'] .fontBodyMedium"
            ]
            
            for selector in phone_selectors:
                try:
                    phone_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if phone_element and phone_element.text.strip():
                        return phone_element.text.strip()
                except:
                    continue
                    
            return '電話未提供'
            
        except Exception as e:
            return '電話獲取失敗'
    
    def scroll_and_extract(self):
        """滾動並擷取店家資訊"""
        try:
            self.debug_print("開始滾動擷取店家...", "INFO")
            
            container = self.find_scrollable_container()
            if not container:
                return False
            
            last_count = 0
            no_change_count = 0
            max_no_change = 3
            max_scrolls = 8
            scroll_count = 0
            
            while scroll_count < max_scrolls and no_change_count < max_no_change:
                scroll_count += 1
                
                # 擷取當前店家
                new_shops = self.extract_current_shops()
                current_count = len(self.shops_data)
                
                self.debug_print(f"第 {scroll_count} 次滾動：當前 {current_count} 家店", "INFO")
                
                if current_count == last_count:
                    no_change_count += 1
                else:
                    no_change_count = 0
                    last_count = current_count
                
                # 檢查是否達到目標
                if len(self.shops_data) >= self.target_shops:
                    self.debug_print(f"🎯 達到目標！收集了 {len(self.shops_data)} 家店", "TARGET")
                    return True
                
                if no_change_count >= max_no_change:
                    break
                
                # 執行滾動
                if scroll_count < max_scrolls:
                    scroll_amount = 500 + (scroll_count * 100)
                    self.driver.execute_script(f"arguments[0].scrollTop += {scroll_amount}", container)
                    time.sleep(2)
                    
                    self.driver.execute_script(f"window.scrollBy(0, {scroll_amount//2});")
                    time.sleep(1)
                
                # 等待載入
                time.sleep(3)
            
            return len(self.shops_data) < self.target_shops
            
        except Exception as e:
            self.debug_print(f"滾動擷取失敗: {e}", "ERROR")
            return False
    
    def extract_current_shops(self):
        """擷取當前可見的店家"""
        try:
            shop_selectors = [
                "a[href*='/maps/place/']",
                "a[data-value='Directions']",
                "div[role='article'] a",
                "div[jsaction*='click'] a[href*='place']"
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
            
            new_shops = []
            max_process = min(5, len(unique_links))
            
            for i, link in enumerate(unique_links[:max_process]):
                try:
                    # 滾動到元素位置
                    self.driver.execute_script("arguments[0].scrollIntoView(false);", link)
                    time.sleep(0.5)
                    
                    shop_info = self.extract_shop_info(link)
                    if shop_info and self.is_new_shop(shop_info):
                        self.shops_data.append(shop_info)
                        new_shops.append(shop_info)
                        self.debug_print(f"✅ 新增店家: {shop_info['name']}", "SUCCESS")
                        self.debug_print(f"   📍 地址: {shop_info['address'][:50]}...", "INFO")
                        self.debug_print(f"   📞 電話: {shop_info['phone']}", "INFO")
                        self.debug_print(f"📊 進度: {len(self.shops_data)}/{self.target_shops}", "INFO")
                        
                        # 檢查是否達到目標
                        if len(self.shops_data) >= self.target_shops:
                            self.debug_print(f"🎯 達到{self.target_shops}家目標！", "TARGET")
                            break
                            
                except Exception as e:
                    self.debug_print(f"處理店家 {i+1} 時出錯: {e}", "ERROR")
                    continue
            
            return new_shops
            
        except Exception as e:
            self.debug_print(f"擷取店家錯誤: {e}", "ERROR")
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
            self.debug_print(f"找不到滾動容器: {e}", "ERROR")
            return None
    
    def is_new_shop(self, shop_info):
        """檢查是否為新店家"""
        if not shop_info or not shop_info.get('name'):
            return False
            
        shop_name = shop_info['name'].strip().lower()
        shop_url = shop_info.get('google_maps_url', '').strip()
        
        for existing_shop in self.shops_data:
            existing_name = existing_shop.get('name', '').strip().lower()
            existing_url = existing_shop.get('google_maps_url', '').strip()
            
            # 名稱匹配
            if existing_name == shop_name:
                return False
            
            # URL匹配
            if shop_url and existing_url and shop_url == existing_url:
                return False
        
        return True
    
    def save_to_excel(self, filename=None):
        """儲存資料到Excel檔案"""
        try:
            if not self.shops_data:
                self.debug_print("沒有資料可以儲存", "ERROR")
                return False
            
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"高雄美甲美睫店家_{len(self.shops_data)}家_{timestamp}"
            
            # 去除重複
            unique_shops = []
            seen = set()
            
            for shop in self.shops_data:
                key = (shop['name'], shop.get('google_maps_url', ''))
                if key not in seen:
                    seen.add(key)
                    unique_shops.append(shop)
            
            # 儲存Excel
            excel_filename = f"{filename}.xlsx"
            df = pd.DataFrame(unique_shops)
            df.to_excel(excel_filename, index=False, engine='openpyxl')
            
            # 儲存CSV備份
            csv_filename = f"{filename}.csv"
            df.to_csv(csv_filename, index=False, encoding='utf-8-sig')
            
            self.debug_print(f"✅ 成功儲存 {len(unique_shops)} 筆資料", "SAVE")
            self.debug_print(f"📁 Excel檔案: {excel_filename}", "SAVE")
            self.debug_print(f"📁 CSV檔案: {csv_filename}", "SAVE")
            
            # 統計資料
            successful_addresses = sum(1 for shop in unique_shops if shop.get('address', '地址未提供') not in ['地址未提供', '地址獲取失敗'])
            successful_phones = sum(1 for shop in unique_shops if shop.get('phone', '電話未提供') not in ['電話未提供', '電話獲取失敗'])
            
            self.debug_print(f"📊 統計資料:", "INFO")
            self.debug_print(f"   - 總店家數: {len(unique_shops)}", "INFO")
            self.debug_print(f"   - 成功獲取地址: {successful_addresses}", "INFO")
            self.debug_print(f"   - 成功獲取電話: {successful_phones}", "INFO")
            
            return True
            
        except Exception as e:
            self.debug_print(f"儲存失敗: {e}", "ERROR")
            return False
    
    def get_kaohsiung_landmarks(self):
        """獲取高雄重要地標列表"""
        landmarks = [
            # 主要行政區中心
            "高雄火車站", "高雄市政府", "鳳山火車站", "鳳山區公所",
            "左營高鐵站", "左營區公所", "楠梓火車站", "楠梓區公所",
            "三民區公所", "苓雅區公所", "新興區公所", "前金區公所",
            "鼓山區公所", "前鎮區公所", "小港機場", "小港區公所",
            
            # 重要商圈
            "新崛江商圈", "五福商圈", "巨蛋商圈", "夢時代購物中心",
            "大立百貨", "漢神百貨", "新光三越左營店", "統一夢時代",
            "草衙道購物中心", "義享天地", "大遠百高雄店", "太平洋SOGO",
            
            # 夜市
            "六合夜市", "瑞豐夜市", "光華夜市", "凱旋夜市",
            "興中夜市", "南華路夜市", "青年夜市",
            
            # 醫院
            "高雄榮總", "高雄醫學大學附設醫院", "長庚紀念醫院高雄院區",
            "義大醫院", "阮綜合醫院", "高雄市立聯合醫院",
            
            # 學校
            "高雄大學", "中山大學", "高雄醫學大學", "高雄師範大學",
            "文藻外語大學", "正修科技大學", "高雄科技大學",
            
            # 觀光景點
            "西子灣", "旗津海岸公園", "愛河", "蓮池潭", "佛光山",
            "義大世界", "壽山動物園", "澄清湖", "打狗英國領事館",
            
            # 重要交通節點
            "美麗島站", "中央公園站", "三多商圈站", "巨蛋站",
            "左營站", "生態園區站", "鳳山西站", "大東站",
            
            # 各區重要地點
            "仁武區公所", "大社區公所", "岡山火車站", "路竹火車站",
            "湖內區公所", "茄萣區公所", "永安區公所", "彌陀區公所",
            "梓官區公所", "橋頭火車站", "橋頭糖廠", "燕巢區公所",
            "田寮區公所", "阿蓮區公所", "大樹區公所", "大寮區公所",
            "林園區公所", "鳥松區公所", "旗山火車站", "美濃區公所",
            "六龜區公所", "甲仙區公所", "杉林區公所", "內門區公所",
            
            # 工業區
            "林園工業區", "大社工業區", "仁武工業區", "臨海工業區",
            "路竹科學園區", "橋頭科學園區", "高雄軟體科技園區",
            
            # 其他重要地點
            "高雄港", "85大樓", "高雄展覽館", "高雄流行音樂中心",
            "高雄圖書館總館", "駁二藝術特區", "亞洲新灣區"
        ]
        
        return landmarks
    
    def run_precision_scraping(self):
        """執行精準搜索"""
        start_time = time.time()
        
        try:
            self.debug_print("🚀 開始高雄地區美甲美睫店家精準搜索", "INFO")
            self.debug_print(f"🎯 目標：收集 {self.target_shops} 家店家", "TARGET")
            self.debug_print("🔍 關鍵字：美甲、美睫、耳燭、採耳、熱蠟", "INFO")
            self.debug_print("📍 範圍：高雄市（地址驗證）", "INFO")
            print("=" * 70)
            
            if not self.setup_driver():
                return False
            
            if not self.open_google_maps():
                return False
            
            # 搜索關鍵字
            shop_types = ["美甲", "美睫", "耳燭", "採耳", "熱蠟"]
            landmarks = self.get_kaohsiung_landmarks()
            
            self.debug_print(f"📍 搜索地標: {len(landmarks)} 個", "INFO")
            self.debug_print(f"🏪 店家類型: {len(shop_types)} 種", "INFO")
            self.debug_print(f"🔍 預估搜索次數: {len(landmarks) * len(shop_types)}", "INFO")
            print("-" * 50)
            
            total_searches = len(landmarks) * len(shop_types)
            current_search = 0
            
            # 對每個地標進行搜索
            for i, landmark in enumerate(landmarks, 1):
                self.debug_print(f"[{i}/{len(landmarks)}] 地標: {landmark}", "INFO")
                
                if not self.set_location(landmark):
                    continue
                
                # 對每種店家類型進行搜索
                for j, shop_type in enumerate(shop_types, 1):
                    current_search += 1
                    progress = (current_search / total_searches) * 100
                    
                    self.debug_print(f"[{j}/{len(shop_types)}] 搜索 {shop_type} (進度: {progress:.1f}%)", "INFO")
                    
                    # 檢查是否達到目標
                    if len(self.shops_data) >= self.target_shops:
                        self.debug_print(f"🎯 達到{self.target_shops}家目標！", "TARGET")
                        break
                    
                    if not self.search_nearby_shops(shop_type, landmark):
                        continue
                    
                    should_continue = self.scroll_and_extract()
                    if not should_continue:
                        self.debug_print(f"🎯 達到目標，停止搜索", "TARGET")
                        break
                    
                    self.debug_print(f"完成 {landmark} - {shop_type}，目前 {len(self.shops_data)} 家", "INFO")
                    
                    # 搜索間隔
                    if current_search < total_searches and len(self.shops_data) < self.target_shops:
                        time.sleep(random.uniform(2, 4))
                
                # 檢查是否達到目標
                if len(self.shops_data) >= self.target_shops:
                    break
                
                # 每完成5個地標暫存一次
                if i % 5 == 0 and self.shops_data:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    temp_filename = f"高雄美甲美睫_暫存_{len(self.shops_data)}家_{timestamp}"
                    self.save_to_excel(temp_filename)
                
                # 地標間隔
                if i < len(landmarks) and len(self.shops_data) < self.target_shops:
                    time.sleep(random.uniform(3, 6))
            
            print("\n" + "=" * 70)
            
            # 儲存最終結果
            if self.shops_data:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                if len(self.shops_data) >= self.target_shops:
                    final_filename = f"高雄美甲美睫店家_完成_{self.target_shops}家_{timestamp}"
                else:
                    final_filename = f"高雄美甲美睫店家_完整_{len(self.shops_data)}家_{timestamp}"
                
                self.save_to_excel(final_filename)
                
                elapsed_time = time.time() - start_time
                hours = elapsed_time // 3600
                minutes = (elapsed_time % 3600) // 60
                
                if hours > 0:
                    time_str = f"{int(hours)}小時{int(minutes)}分"
                else:
                    time_str = f"{int(minutes)}分"
                
                self.debug_print(f"✅ 搜索完成！執行時間: {time_str}", "SUCCESS")
                self.debug_print(f"📊 最終收集: {len(self.shops_data)} 家店家", "SUCCESS")
                
                if len(self.shops_data) >= self.target_shops:
                    self.debug_print(f"🎯 成功達到 {self.target_shops} 家目標！", "TARGET")
                
            else:
                self.debug_print("未找到任何店家", "ERROR")
            
            return True
            
        except Exception as e:
            self.debug_print(f"搜索失敗: {e}", "ERROR")
            return False
        
        finally:
            if self.driver:
                self.debug_print("關閉瀏覽器...", "INFO")
                time.sleep(2)
                self.driver.quit()

def main():
    """主程式"""
    print("🚀 高雄地區美甲美睫店家精準搜索程式 (Firefox版)")
    print()
    print("🎯 搜索目標：")
    print("   - 收集2000家店家資料")
    print("   - 店家名稱、地圖連結、地址、電話")
    print("   - 確保地址在高雄市")
    print()
    print("🔍 搜索關鍵字：")
    print("   - 美甲、美睫、耳燭、採耳、熱蠟")
    print()
    print("📍 搜索範圍：")
    print("   - 高雄市所有區域重要地標")
    print("   - 地址驗證確保在高雄市")
    print()
    print("🦊 瀏覽器：Firefox (避免Chrome衝突)")
    print("⏰ 預估時間：約30分鐘 (2000家店)")
    print("💾 自動儲存Excel和CSV檔案")
    print()
    print("📋 系統需求：")
    print("   - 已安裝 Firefox 瀏覽器")
    print("   - 已安裝 geckodriver")
    print("-" * 50)
    
    user_input = input("確定要開始搜索嗎？(y/n): ").strip().lower()
    if user_input != 'y':
        print("程式已取消")
        return
    
    scraper = KaohsiungPrecisionScraper(debug_mode=True)
    scraper.run_precision_scraping()

if __name__ == "__main__":
    main() 