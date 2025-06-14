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
    def __init__(self, debug_mode=True, show_browser=True):
        self.debug_mode = debug_mode
        self.show_browser = show_browser  # 新增：控制是否顯示瀏覽器視窗
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
            if self.show_browser:
                self.debug_print("正在設定Firefox瀏覽器 (視窗模式)...", "INFO")
            else:
                self.debug_print("正在設定Firefox瀏覽器 (無頭模式)...", "INFO")
                
            firefox_options = Options()
            
            # 根據show_browser參數決定是否使用無頭模式
            if not self.show_browser:
                firefox_options.add_argument("--headless")  # 只在不顯示視窗時使用無頭模式
                
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
            
            if self.show_browser:
                self.debug_print("🦊 啟動Firefox (視窗模式)...", "INFO")
            else:
                self.debug_print("🦊 啟動Firefox (無頭模式)...", "INFO")
                
            self.driver = webdriver.Firefox(options=firefox_options)
            self.driver.set_window_size(1920, 1080)
            
            if self.show_browser:
                self.debug_print("Firefox瀏覽器設定完成 (可見視窗)", "SUCCESS")
            else:
                self.debug_print("Firefox瀏覽器設定完成 (無頭模式)", "SUCCESS")
            return True
            
        except Exception as e:
            self.debug_print(f"Firefox瀏覽器設定失敗: {e}", "ERROR")
            # 嘗試最簡配置
            try:
                self.debug_print("🦊 嘗試最簡Firefox配置...", "INFO")
                simple_options = Options()
                if not self.show_browser:
                    simple_options.add_argument("--headless")
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
        """搜尋附近的店家 - 改良版"""
        try:
            self.debug_print(f"在 {location} 搜尋: {shop_type}", "INFO")
            
            search_box = WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.ID, "searchboxinput"))
            )
            
            search_box.clear()
            time.sleep(1.5)
            
            # 構建更精確的搜尋查詢
            search_queries = [
                f"{shop_type} {location} 高雄",
                f"{shop_type} near {location}",
                f"高雄 {location} {shop_type}",
                f"{shop_type} 高雄市"
            ]
            
            # 使用第一個查詢
            search_query = search_queries[0]
            self.debug_print(f"搜尋查詢: {search_query}", "INFO")
            
            # 逐字輸入搜尋查詢
            for char in search_query:
                search_box.send_keys(char)
                time.sleep(random.uniform(0.02, 0.06))
            
            time.sleep(2)
            search_box.send_keys(Keys.ENTER)
            
            self.debug_print("等待搜尋結果載入...", "WAIT")
            time.sleep(10)  # 增加等待時間
            
            # 檢查是否有搜尋結果
            try:
                # 等待搜尋結果出現
                WebDriverWait(self.driver, 15).until(
                    lambda driver: len(driver.find_elements(By.CSS_SELECTOR, "a[href*='/maps/place/']")) > 0
                )
                results_count = len(self.driver.find_elements(By.CSS_SELECTOR, "a[href*='/maps/place/']"))
                self.debug_print(f"找到 {results_count} 個初始搜尋結果", "SUCCESS")
                
                if results_count == 0:
                    self.debug_print("沒有找到搜尋結果，嘗試其他查詢", "WARNING")
                    # 嘗試其他搜尋查詢
                    for backup_query in search_queries[1:]:
                        self.debug_print(f"嘗試備用查詢: {backup_query}", "INFO")
                        search_box.clear()
                        time.sleep(1)
                        
                        for char in backup_query:
                            search_box.send_keys(char)
                            time.sleep(random.uniform(0.02, 0.06))
                        
                        search_box.send_keys(Keys.ENTER)
                        time.sleep(8)
                        
                        results_count = len(self.driver.find_elements(By.CSS_SELECTOR, "a[href*='/maps/place/']"))
                        if results_count > 0:
                            self.debug_print(f"備用查詢成功，找到 {results_count} 個結果", "SUCCESS")
                            break
                
            except TimeoutException:
                self.debug_print("搜尋結果載入超時", "WARNING")
                # 但仍然繼續，可能有結果但載入較慢
            
            return True
            
        except Exception as e:
            self.debug_print(f"搜尋失敗: {e}", "ERROR")
            return False
    
    def is_kaohsiung_address(self, address):
        """檢查地址是否在高雄市 - 簡化版：只要包含高雄就可以"""
        if not address or address in ['地址未提供', '地址獲取失敗']:
            # 如果沒有地址，但在高雄搜尋，可能還是高雄的店家
            self.debug_print(f"地址為空，但在高雄搜尋範圍內，保留", "WARNING")
            return True
        
        # 簡化邏輯：只要包含"高雄"就通過
        if "高雄" in address:
            self.debug_print(f"✅ 地址包含高雄，通過驗證: {address[:50]}...", "SUCCESS")
            return True
        
        # 如果沒有高雄但地址很短，也可能是高雄的店家
        if len(address) < 15 and not any(city in address for city in ['台北', '台中', '台南', '新北', '桃園', '嘉義', '屏東']):
            self.debug_print(f"⚠️ 地址簡短無其他城市，可能是高雄店家，保留: {address}", "WARNING")
            return True
        
        self.debug_print(f"❌ 地址不包含高雄，過濾: {address}", "WARNING")
        return False
    
    def extract_shop_info(self, link_element):
        """擷取店家基本資訊並驗證地址 - 改良版，確保點開後滑動抓取"""
        try:
            # 獲取店家名稱
            name = None
            
            # 多種方式獲取名稱
            try:
                name = link_element.get_attribute('aria-label')
                if not name or len(name.strip()) < 2:
                    name = link_element.text.strip()
                if not name or len(name.strip()) < 2:
                    parent = link_element.find_element(By.XPATH, "..")
                    name = parent.get_attribute('aria-label') or parent.text.strip()
                if not name or len(name.strip()) < 2:
                    # 從連結中提取店家名稱
                    href = link_element.get_attribute('href')
                    if href and '/maps/place/' in href:
                        place_name = href.split('/maps/place/')[1].split('/')[0]
                        name = urllib.parse.unquote(place_name).replace('+', ' ')
            except Exception as e:
                self.debug_print(f"提取店家名稱時出錯: {e}", "WARNING")
                
            if not name or len(name.strip()) < 2:
                self.debug_print("無法獲取店家名稱，跳過", "WARNING")
                return None
                
            name = name.strip()
            
            # 先檢查店家名稱是否相關
            beauty_keywords = ['美甲', '美睫', '耳燭', '採耳', '熱蠟', '美容', '美體', '指甲', '睫毛', '美膚', '美髮', '護膚', '美顏']
            is_beauty_related = any(keyword in name for keyword in beauty_keywords)
            
            if not is_beauty_related:
                self.debug_print(f"店家名稱不相關，跳過: {name}", "WARNING")
                return None
            
            # 基本店家資訊
            shop_info = {
                'name': name,
                'google_maps_url': link_element.get_attribute('href') or '',
                'address': '地址未提供',
                'phone': '電話未提供',
                'line_contact': 'LINE未提供'
            }
            
            # 記錄主視窗
            main_window = self.driver.current_window_handle
            
            try:
                self.debug_print(f"🔍 開始提取店家詳細資訊: {name}", "INFO")
                
                # 點開店家詳細頁面
                self.driver.execute_script("arguments[0].click();", link_element)
                self.debug_print("👆 點擊店家連結", "INFO")
                time.sleep(4)  # 增加等待時間
                
                # 等待詳細頁面載入
                self.debug_print("⏳ 等待店家詳細頁面載入...", "WAIT")
                try:
                    WebDriverWait(self.driver, 15).until(
                        lambda driver: len(driver.find_elements(By.CSS_SELECTOR, "[data-item-id]")) > 0 or
                                       len(driver.find_elements(By.CSS_SELECTOR, ".fontBodyMedium")) > 0 or
                                       "高雄" in driver.page_source
                    )
                    self.debug_print("✅ 詳細頁面載入完成", "SUCCESS")
                except TimeoutException:
                    self.debug_print("⚠️ 頁面載入超時，但繼續嘗試", "WARNING")
                
                # 🔑 關鍵：往下滑動250px來載入地址和電話資訊
                self.debug_print("📱 開始滑動載入完整資訊...", "INFO")
                self.scroll_to_load_shop_details()
                
                # 提取地址 - 增加重試機制
                address = None
                for attempt in range(3):  # 最多重試3次
                    self.debug_print(f"🔍 第 {attempt + 1} 次嘗試提取地址...", "INFO")
                    address = self.extract_address_detailed()
                    if address and address not in ['地址未提供', '地址獲取失敗']:
                        break
                    if attempt < 2:  # 不是最後一次嘗試
                        self.debug_print("⏳ 等待更長時間後重試...", "WAIT")
                        time.sleep(2)
                        # 再次滑動
                        self.driver.execute_script("window.scrollBy(0, 100);")
                        time.sleep(1)
                
                if address and address not in ['地址未提供', '地址獲取失敗']:
                    shop_info['address'] = address
                    self.debug_print(f"✅ 成功提取地址: {address[:50]}...", "SUCCESS")
                else:
                    self.debug_print("⚠️ 未能提取到地址", "WARNING")
                
                # 提取電話 - 增加重試機制
                phone = None
                for attempt in range(3):  # 最多重試3次
                    self.debug_print(f"📞 第 {attempt + 1} 次嘗試提取電話...", "INFO")
                    phone = self.extract_phone_detailed()
                    if phone and phone not in ['電話未提供', '電話獲取失敗']:
                        break
                    if attempt < 2:  # 不是最後一次嘗試
                        self.debug_print("⏳ 等待更長時間後重試...", "WAIT")
                        time.sleep(2)
                        # 再次滑動
                        self.driver.execute_script("window.scrollBy(0, 100);")
                        time.sleep(1)
                
                if phone and phone not in ['電話未提供', '電話獲取失敗']:
                    shop_info['phone'] = phone
                    self.debug_print(f"✅ 成功提取電話: {phone}", "SUCCESS")
                else:
                    self.debug_print("⚠️ 未能提取到電話", "WARNING")
                
                # 提取LINE聯絡方式 - 增加重試機制
                line_contact = None
                for attempt in range(3):  # 最多重試3次
                    self.debug_print(f"📱 第 {attempt + 1} 次嘗試提取LINE聯絡方式...", "INFO")
                    line_contact = self.extract_line_contact_detailed()
                    if line_contact and line_contact not in ['LINE未提供', 'LINE獲取失敗']:
                        break
                    if attempt < 2:  # 不是最後一次嘗試
                        self.debug_print("⏳ 等待更長時間後重試...", "WAIT")
                        time.sleep(2)
                        # 再次滑動
                        self.driver.execute_script("window.scrollBy(0, 100);")
                        time.sleep(1)
                
                if line_contact and line_contact not in ['LINE未提供', 'LINE獲取失敗']:
                    shop_info['line_contact'] = line_contact
                    self.debug_print(f"✅ 成功提取LINE: {line_contact}", "SUCCESS")
                else:
                    self.debug_print("⚠️ 未能提取到LINE聯絡方式", "WARNING")
                
                # 返回上一頁
                self.debug_print("🔙 返回搜索列表...", "INFO")
                self.driver.back()
                time.sleep(4)  # 增加等待時間確保返回
                
            except Exception as e:
                self.debug_print(f"❌ 提取詳細資訊時出錯: {e}", "ERROR")
                # 確保回到搜索頁面
                try:
                    self.driver.back()
                    time.sleep(3)
                except:
                    pass
            
            # 驗證地址是否在高雄（使用簡化標準）
            if not self.is_kaohsiung_address(shop_info['address']):
                return None
            
            self.debug_print(f"🎉 成功擷取完整店家資訊: {name}", "SUCCESS")
            self.debug_print(f"   📍 地址: {shop_info['address']}", "INFO")
            self.debug_print(f"   📞 電話: {shop_info['phone']}", "INFO")
            self.debug_print(f"   📱 LINE: {shop_info['line_contact']}", "INFO")
            return shop_info
            
        except Exception as e:
            self.debug_print(f"❌ 擷取店家資訊失敗: {e}", "ERROR")
            return None
    
    def scroll_to_load_shop_details(self):
        """在店家詳細頁面智能滑動載入完整資訊 - 調試版本"""
        try:
            self.debug_print("📱 開始檢查店家詳細頁面...", "INFO")
            
            # 🔑 關鍵修正：先滑動到頁面頂部，確保每個店家都從頂部開始
            self.debug_print("⬆️ 先滑動到頁面頂部...", "INFO")
            self.driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(1)
            
            # 也嘗試滑動容器到頂部
            try:
                # 尋找主要容器並滑動到頂部
                main_containers = [
                    "[role='main']",
                    "div[data-value='ovrvw']", 
                    ".section-layout",
                    ".section-scrollbox"
                ]
                
                for selector in main_containers:
                    try:
                        container = self.driver.find_element(By.CSS_SELECTOR, selector)
                        if container:
                            self.driver.execute_script("arguments[0].scrollTop = 0", container)
                            self.debug_print(f"✅ 容器 ({selector}) 已滑動到頂部", "SUCCESS")
                            break
                    except:
                        continue
            except Exception as e:
                self.debug_print(f"⚠️ 容器滑動到頂部失敗: {e}", "WARNING")
            
            # 等待2秒讓頁面穩定
            time.sleep(2)
            self.debug_print("✅ 頁面已重置到頂部，開始檢查內容...", "SUCCESS")
            
            # 先檢查是否已經有"提出修改建議"按鈕
            suggest_edit_selectors = [
                "button[data-value='suggest_edits']",
                "button[aria-label*='提出修改建議']",
                "button[aria-label*='Suggest an edit']",
                "[data-value='suggest_edits']",
                "button:contains('提出修改建議')",
                "button:contains('Suggest')",
                "[jsaction*='suggest']",
                # 新增更多可能的選擇器
                "button[data-item-id*='suggest']",
                "div[data-value='suggest_edits']",
                "[role='button'][aria-label*='修改']"
            ]
            
            # 調試：列出頁面上所有的按鈕
            try:
                all_buttons = self.driver.find_elements(By.TAG_NAME, "button")
                self.debug_print(f"🔍 頁面上共有 {len(all_buttons)} 個按鈕", "INFO")
                
                # 檢查前10個按鈕的文字和屬性
                for i, btn in enumerate(all_buttons[:10]):
                    try:
                        btn_text = btn.text.strip()
                        btn_aria = btn.get_attribute('aria-label') or ''
                        btn_data = btn.get_attribute('data-value') or ''
                        if btn_text or btn_aria or btn_data:
                            self.debug_print(f"   按鈕 {i+1}: 文字='{btn_text}' aria-label='{btn_aria}' data-value='{btn_data}'", "INFO")
                    except:
                        continue
            except Exception as e:
                self.debug_print(f"調試按鈕列表失敗: {e}", "WARNING")
            
            # 檢查是否已經有提出修改建議按鈕
            has_suggest_button = False
            found_selector = ""
            
            for i, selector in enumerate(suggest_edit_selectors):
                try:
                    if ':contains(' in selector:
                        # 使用XPath處理contains
                        xpath = "//button[contains(text(), '提出修改建議') or contains(text(), 'Suggest')]"
                        elements = self.driver.find_elements(By.XPATH, xpath)
                    else:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    
                    if elements:
                        self.debug_print(f"🔍 選擇器 {i+1} 找到 {len(elements)} 個元素", "INFO")
                        for j, elem in enumerate(elements):
                            try:
                                if elem.is_displayed():
                                    has_suggest_button = True
                                    found_selector = selector
                                    self.debug_print(f"✅ 選擇器 {i+1} 找到可見的'提出修改建議'按鈕", "SUCCESS")
                                    break
                            except:
                                continue
                        if has_suggest_button:
                            break
                except Exception as e:
                    self.debug_print(f"選擇器 {i+1} 檢查失敗: {e}", "WARNING")
                    continue
            
            # 根據是否找到按鈕決定是否滑動
            if has_suggest_button:
                self.debug_print(f"✅ 發現'提出修改建議'按鈕 (選擇器: {found_selector})，頁面已完全載入，無需滑動", "SUCCESS")
            else:
                self.debug_print("⚠️ 未找到'提出修改建議'按鈕，開始滑動載入完整內容...", "WARNING")
                
                # 強制執行滑動操作來測試
                self.debug_print("⬇️ 開始執行滑動操作...", "INFO")
                
                # 1. 頁面滑動
                self.debug_print("📱 執行頁面滑動 250px...", "INFO")
                self.driver.execute_script("window.scrollBy(0, 250);")
                time.sleep(2)
                
                # 2. 再滑動一點
                self.debug_print("📱 執行額外滑動 100px...", "INFO")
                self.driver.execute_script("window.scrollBy(0, 100);")
                time.sleep(1)
                
                # 3. 尋找容器並滑動
                detail_containers = [
                    "[role='main']",
                    "div[data-value='ovrvw']", 
                    ".section-layout",
                    ".section-scrollbox",
                    "div[jsaction*='scroll']"
                ]
                
                container_found = False
                for i, selector in enumerate(detail_containers):
                    try:
                        container = self.driver.find_element(By.CSS_SELECTOR, selector)
                        if container:
                            self.debug_print(f"🎯 找到容器 {i+1} ({selector})，進行滑動...", "INFO")
                            self.driver.execute_script("arguments[0].scrollTop += 250", container)
                            time.sleep(1)
                            container_found = True
                            break
                    except Exception as e:
                        self.debug_print(f"容器 {i+1} 滑動失敗: {e}", "WARNING")
                        continue
                
                if not container_found:
                    self.debug_print("⚠️ 未找到可滑動容器", "WARNING")
                
                # 4. 鍵盤滑動
                try:
                    body = self.driver.find_element(By.TAG_NAME, "body")
                    body.send_keys(Keys.PAGE_DOWN)
                    time.sleep(1)
                    self.debug_print("⌨️ 執行鍵盤滑動", "INFO")
                except Exception as e:
                    self.debug_print(f"鍵盤滑動失敗: {e}", "WARNING")
                
                # 5. 最終滑動
                self.debug_print("📱 執行最終滑動 150px...", "INFO")
                self.driver.execute_script("window.scrollBy(0, 150);")
                time.sleep(2)
                
                self.debug_print("✅ 滑動操作完成", "SUCCESS")
            
        except Exception as e:
            self.debug_print(f"❌ 滑動詳細頁面失敗: {e}", "ERROR")
            import traceback
            self.debug_print(f"錯誤詳情: {traceback.format_exc()}", "ERROR")
    
    def extract_address_detailed(self):
        """從店家詳細頁面擷取地址 - 增強版"""
        try:
            self.debug_print("🔍 開始提取地址...", "INFO")
            
            # 更全面的地址選擇器
            address_selectors = [
                # 主要選擇器
                "[data-item-id='address'] .fontBodyMedium",
                "[data-item-id='address'] span",
                "button[data-item-id='address'] .fontBodyMedium",
                
                # 通用選擇器
                "[aria-label*='地址'] .fontBodyMedium",
                "[aria-label*='Address' i] .fontBodyMedium",
                ".rogA2c .fontBodyMedium",
                "div[data-value='Address'] .fontBodyMedium",
                ".Io6YTe .fontBodyMedium",
                
                # 備用選擇器
                "span[jstcache='84']",
                ".QSFF4-text",
                ".fontBodyMedium:contains('高雄')",
                
                # 新版選擇器
                "[jsaction*='address'] span",
                ".section-info-line .fontBodyMedium"
            ]
            
            for i, selector in enumerate(address_selectors):
                try:
                    if ':contains(' in selector:
                        # 對於包含特定文字的選擇器，使用XPath
                        xpath = f"//span[contains(@class, 'fontBodyMedium') and contains(text(), '高雄')]"
                        elements = self.driver.find_elements(By.XPATH, xpath)
                    else:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    
                    for element in elements:
                        if element and element.text.strip():
                            address_text = element.text.strip()
                            if len(address_text) > 5 and any(char.isdigit() for char in address_text):
                                self.debug_print(f"✅ 選擇器 {i+1} 找到地址: {address_text}", "SUCCESS")
                                return address_text
                                
                except Exception as e:
                    self.debug_print(f"選擇器 {i+1} 失敗: {e}", "WARNING")
                    continue
            
            # 最後嘗試從頁面文字中提取地址
            try:
                page_text = self.driver.find_element(By.TAG_NAME, "body").text
                import re
                # 尋找包含高雄的地址模式
                address_patterns = [
                    r'高雄市[^,\n\r]{10,50}',
                    r'\d{3}高雄[^,\n\r]{5,40}',
                    r'高雄[^,\n\r]{8,40}號',
                    r'高雄[^,\n\r]{8,40}樓'
                ]
                
                for pattern in address_patterns:
                    matches = re.findall(pattern, page_text)
                    if matches:
                        address = matches[0].strip()
                        self.debug_print(f"✅ 正則表達式找到地址: {address}", "SUCCESS")
                        return address
                        
            except Exception as e:
                self.debug_print(f"正則表達式提取失敗: {e}", "WARNING")
            
            self.debug_print("❌ 未能找到地址", "WARNING")
            return '地址未提供'
            
        except Exception as e:
            self.debug_print(f"地址提取失敗: {e}", "ERROR")
            return '地址獲取失敗'
    
    def extract_phone_detailed(self):
        """從店家詳細頁面擷取電話 - 增強版，添加調試信息"""
        try:
            self.debug_print("📞 開始提取電話...", "INFO")
            
            # 更全面的電話選擇器，根據截圖添加更多可能的選擇器
            phone_selectors = [
                # 主要選擇器
                "[data-item-id='phone:tel:'] .fontBodyMedium",
                "button[data-item-id*='phone'] .fontBodyMedium",
                "[data-item-id*='phone'] span",
                
                # 通用選擇器
                "[aria-label*='電話'] .fontBodyMedium",
                "[aria-label*='Phone' i] .fontBodyMedium",
                "[aria-label*='電話號碼'] .fontBodyMedium",
                "button[data-value^='phone'] .fontBodyMedium",
                "div[data-value='Phone'] .fontBodyMedium",
                
                # 備用選擇器
                "a[href^='tel:'] .fontBodyMedium",
                "a[href^='tel:']",
                ".section-info-line a[href^='tel:']",
                
                # 新版選擇器
                "[jsaction*='phone'] span",
                ".section-info-text .fontBodyMedium",
                
                # 根據截圖添加的選擇器
                "span.fontBodyMedium",  # 通用的 fontBodyMedium
                ".fontBodyMedium",      # 所有 fontBodyMedium 類別
                "div[role='button'] span", # 按鈕內的span
                "[role='button'] .fontBodyMedium", # 按鈕內的文字
                "button span",          # 按鈕內的span
                "a span"                # 連結內的span
            ]
            
            # 先嘗試用選擇器找電話
            for i, selector in enumerate(phone_selectors):
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    self.debug_print(f"🔍 選擇器 {i+1} ({selector}) 找到 {len(elements)} 個元素", "INFO")
                    
                    for j, element in enumerate(elements):
                        if element and element.text.strip():
                            phone_text = element.text.strip()
                            self.debug_print(f"   元素 {j+1}: '{phone_text}'", "INFO")
                            
                            # 檢查是否包含數字且長度合理
                            if len(phone_text) >= 8 and any(char.isdigit() for char in phone_text):
                                # 先用寬鬆的驗證
                                if self.is_phone_like(phone_text):
                                    self.debug_print(f"✅ 選擇器 {i+1} 找到疑似電話: {phone_text}", "SUCCESS")
                                    # 再用嚴格驗證
                                    if self.is_valid_phone(phone_text):
                                        self.debug_print(f"✅ 電話格式驗證通過: {phone_text}", "SUCCESS")
                                        return phone_text
                                    else:
                                        self.debug_print(f"⚠️ 電話格式驗證失敗，但保留: {phone_text}", "WARNING")
                                        # 即使格式驗證失敗，如果看起來像電話就保留
                                        return phone_text
                                        
                except Exception as e:
                    self.debug_print(f"選擇器 {i+1} 失敗: {e}", "WARNING")
                    continue
            
            # 從href屬性中提取電話
            try:
                tel_links = self.driver.find_elements(By.CSS_SELECTOR, "a[href^='tel:']")
                self.debug_print(f"🔍 找到 {len(tel_links)} 個電話連結", "INFO")
                
                for i, link in enumerate(tel_links):
                    href = link.get_attribute('href')
                    if href:
                        phone = href.replace('tel:', '').strip()
                        self.debug_print(f"   連結 {i+1}: {phone}", "INFO")
                        if self.is_phone_like(phone):
                            self.debug_print(f"✅ 從連結找到電話: {phone}", "SUCCESS")
                            return phone
            except Exception as e:
                self.debug_print(f"從連結提取電話失敗: {e}", "WARNING")
            
            # 最後嘗試從頁面文字中提取電話
            try:
                page_text = self.driver.find_element(By.TAG_NAME, "body").text
                import re
                
                # 更寬鬆的台灣電話格式，包括手機號碼
                phone_patterns = [
                    r'09\d{2}\s\d{3}\s\d{3}',  # 0903 533 568 格式
                    r'09\d{8}',                # 0903533568 格式
                    r'0\d{1,2}-\d{6,8}',       # 市話格式
                    r'0\d{9,10}',              # 連續數字格式
                    r'\d{2,4}-\d{6,8}',        # 一般格式
                    r'\(\d{2,3}\)\d{6,8}',     # 括號格式
                    r'0\d{1,2}\s\d{6,8}',      # 空格格式
                    r'09\d{2}-\d{3}-\d{3}'     # 09xx-xxx-xxx 格式
                ]
                
                self.debug_print("🔍 使用正則表達式搜尋電話...", "INFO")
                for i, pattern in enumerate(phone_patterns):
                    matches = re.findall(pattern, page_text)
                    if matches:
                        phone = matches[0].strip()
                        self.debug_print(f"✅ 正則表達式 {i+1} 找到電話: {phone}", "SUCCESS")
                        return phone
                        
            except Exception as e:
                self.debug_print(f"正則表達式提取電話失敗: {e}", "WARNING")
            
            self.debug_print("❌ 未能找到電話", "WARNING")
            return '電話未提供'
            
        except Exception as e:
            self.debug_print(f"電話提取失敗: {e}", "ERROR")
            return '電話獲取失敗'
    
    def is_phone_like(self, phone_text):
        """寬鬆的電話號碼檢查 - 只要看起來像電話就通過"""
        if not phone_text or len(phone_text) < 8:
            return False
        
        # 移除所有空格和特殊字符，只保留數字
        digits_only = ''.join(filter(str.isdigit, phone_text))
        
        # 檢查數字長度是否合理 (台灣電話號碼通常8-10位數)
        if len(digits_only) < 8 or len(digits_only) > 11:
            return False
        
        # 檢查是否以0開頭 (台灣電話號碼特徵)
        if digits_only.startswith('0'):
            return True
        
        # 或者包含常見的電話格式字符
        phone_chars = set('0123456789-() ')
        if all(char in phone_chars for char in phone_text):
            return True
        
        return False
    
    def is_valid_phone(self, phone_text):
        """嚴格的電話號碼格式驗證"""
        if not phone_text or len(phone_text) < 8:
            return False
        
        import re
        # 更寬鬆的台灣電話格式驗證，包括手機號碼
        phone_patterns = [
            r'^09\d{2}\s\d{3}\s\d{3}$',  # 0903 533 568 格式
            r'^09\d{8}$',                # 0903533568 格式
            r'^0\d{1,2}-\d{6,8}$',       # 市話格式
            r'^0\d{9,10}$',              # 連續數字格式
            r'^\d{2,4}-\d{6,8}$',        # 一般格式
            r'^\(\d{2,3}\)\d{6,8}$',     # 括號格式
            r'^0\d{1,2}\s\d{6,8}$',      # 空格格式
            r'^09\d{2}-\d{3}-\d{3}$'     # 09xx-xxx-xxx 格式
        ]
        
        for pattern in phone_patterns:
            if re.match(pattern, phone_text.strip()):
                return True
        
        return False
    
    def scroll_and_extract(self):
        """滾動並擷取店家資訊 - 改良版，詳細監控"""
        try:
            self.debug_print("🔄 開始滾動擷取店家...", "INFO")
            
            # 多次嘗試找到滾動容器
            container = None
            container_attempts = 0
            max_container_attempts = 5
            
            while not container and container_attempts < max_container_attempts:
                container_attempts += 1
                container = self.find_scrollable_container()
                if not container:
                    self.debug_print(f"🔍 第{container_attempts}次找不到滾動容器，等待後重試...", "WARNING")
                    time.sleep(3)
            
            if not container:
                self.debug_print("⚠️ 無法找到滾動容器，嘗試直接滾動頁面", "WARNING")
                container = self.driver.find_element(By.TAG_NAME, "body")
            
            # 檢查初始頁面狀態
            initial_height = self.driver.execute_script("return document.body.scrollHeight")
            self.debug_print(f"📏 初始頁面高度: {initial_height}px", "INFO")
            
            last_count = 0
            no_change_count = 0
            max_no_change = 15      # 增加容忍度
            max_scrolls = 300       # 增加滾動次數
            scroll_count = 0
            total_new_shops = 0
            
            # 記錄滾動效果
            scroll_effectiveness = []
            
            # 先擷取一次當前頁面的店家
            initial_shops = self.extract_current_shops()
            self.debug_print(f"📊 初始擷取到 {len(initial_shops)} 家新店", "SUCCESS")
            
            while scroll_count < max_scrolls and no_change_count < max_no_change:
                scroll_count += 1
                self.debug_print(f"🔄 開始第 {scroll_count} 次滾動...", "INFO")
                
                # 記錄滾動前的狀態
                before_scroll_height = self.driver.execute_script("return document.body.scrollHeight")
                before_scroll_y = self.driver.execute_script("return window.pageYOffset")
                before_shop_count = len(self.shops_data)
                
                # 多種滾動策略
                scroll_strategies = [
                    ("智能滾動", lambda: self.smart_scroll_down(container, scroll_count)),
                    ("側邊欄滾動", lambda: self.scroll_sidebar_list()),
                    ("頁面滾動", lambda: self.page_scroll_down(scroll_count))
                ]
                
                # 輪流使用不同的滾動策略
                strategy_index = scroll_count % len(scroll_strategies)
                strategy_name, strategy_func = scroll_strategies[strategy_index]
                
                self.debug_print(f"🎯 使用策略: {strategy_name}", "INFO")
                strategy_func()
                
                # 檢查滾動後的狀態
                after_scroll_height = self.driver.execute_script("return document.body.scrollHeight")
                after_scroll_y = self.driver.execute_script("return window.pageYOffset")
                
                height_change = after_scroll_height - before_scroll_height
                position_change = after_scroll_y - before_scroll_y
                
                self.debug_print(f"📏 滾動效果: 高度變化={height_change}px, 位置變化={position_change}px", "INFO")
                
                # 等待更長時間讓內容加載
                self.debug_print("⏳ 等待內容載入...", "WAIT")
                time.sleep(4 + random.uniform(1, 2))
                
                # 擷取當前店家
                self.debug_print("🔍 開始擷取店家...", "INFO")
                new_shops = self.extract_current_shops()
                current_count = len(self.shops_data)
                shops_found_this_round = current_count - before_shop_count
                total_new_shops += shops_found_this_round
                
                # 記錄滾動效果
                scroll_effectiveness.append({
                    'round': scroll_count,
                    'strategy': strategy_name,
                    'shops_found': shops_found_this_round,
                    'height_change': height_change,
                    'position_change': position_change
                })
                
                self.debug_print(f"📊 第 {scroll_count} 次滾動結果:", "SUCCESS")
                self.debug_print(f"   🏪 本輪新店家: {shops_found_this_round} 家", "INFO")
                self.debug_print(f"   📈 總店家數: {current_count} 家", "INFO")
                self.debug_print(f"   🎯 目標進度: {current_count}/{self.target_shops} ({current_count/self.target_shops*100:.1f}%)", "INFO")
                
                if current_count == last_count:
                    no_change_count += 1
                    self.debug_print(f"⚠️ 連續 {no_change_count} 次無新店家", "WARNING")
                    
                    # 如果連續多次沒有新店家，嘗試更激進的滾動
                    if no_change_count >= 5:
                        self.debug_print("🚀 啟動激進滾動模式...", "INFO")
                        self.aggressive_scroll(container)
                        time.sleep(3)
                        
                else:
                    no_change_count = 0
                    last_count = current_count
                    self.debug_print("✅ 找到新店家，重置計數器", "SUCCESS")
                
                # 檢查是否達到目標
                if len(self.shops_data) >= self.target_shops:
                    self.debug_print(f"🎯 達到目標！收集了 {len(self.shops_data)} 家店", "TARGET")
                    break
                
                if no_change_count >= max_no_change:
                    self.debug_print(f"⚠️ 連續{max_no_change}次沒找到新店家，結束此地點搜索", "WARNING")
                    break
                    
                # 每20次滾動重新刷新一下頁面
                if scroll_count % 20 == 0:
                    self.debug_print("🔄 重新刷新頁面以加載更多內容...", "INFO")
                    current_url = self.driver.current_url
                    self.driver.refresh()
                    time.sleep(8)
                    self.debug_print("✅ 頁面刷新完成", "SUCCESS")
                
                # 每10次滾動顯示效果統計
                if scroll_count % 10 == 0:
                    self.show_scroll_statistics(scroll_effectiveness)
            
            # 最終統計
            self.debug_print("📊 滾動階段完成統計:", "SUCCESS")
            self.debug_print(f"   🔄 總滾動次數: {scroll_count}", "INFO")
            self.debug_print(f"   🏪 本地點新增店家: {total_new_shops} 家", "INFO")
            self.debug_print(f"   📈 平均每次滾動新增: {total_new_shops/scroll_count:.2f} 家" if scroll_count > 0 else "   📈 平均效果: 無", "INFO")
            
            return len(self.shops_data) < self.target_shops
            
        except Exception as e:
            self.debug_print(f"❌ 滾動擷取失敗: {e}", "ERROR")
            return False
    
    def aggressive_scroll(self, container):
        """激進滾動策略 - 當普通滾動無效時使用"""
        try:
            self.debug_print("🚀 執行激進滾動策略...", "INFO")
            
            # 滾動到頁面底部
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            
            # 連續向下滾動
            for i in range(5):
                self.driver.execute_script(f"window.scrollBy(0, {1000 + i*200});")
                time.sleep(1)
            
            # 使用鍵盤滾動
            body = self.driver.find_element(By.TAG_NAME, "body")
            for i in range(10):
                body.send_keys(Keys.PAGE_DOWN)
                time.sleep(0.3)
            
            # 如果有容器，也滾動容器
            if container:
                self.driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", container)
                time.sleep(1)
            
            self.debug_print("✅ 激進滾動完成", "SUCCESS")
            
        except Exception as e:
            self.debug_print(f"⚠️ 激進滾動失敗: {e}", "WARNING")
    
    def show_scroll_statistics(self, scroll_effectiveness):
        """顯示滾動效果統計"""
        if not scroll_effectiveness:
            return
        
        self.debug_print("📈 滾動效果統計 (最近10次):", "INFO")
        recent_10 = scroll_effectiveness[-10:]
        
        for effect in recent_10:
            status = "✅" if effect['shops_found'] > 0 else "⚠️"
            self.debug_print(f"   {status} 第{effect['round']}次 [{effect['strategy']}]: {effect['shops_found']}家店", "INFO")
        
        total_shops = sum(e['shops_found'] for e in recent_10)
        self.debug_print(f"📊 最近10次總計: {total_shops} 家店", "SUCCESS")
    
    def smart_scroll_down(self, container, scroll_count):
        """智能滾動策略"""
        try:
            # 動態調整滾動距離
            base_scroll = 600
            progressive_scroll = scroll_count * 50
            total_scroll = min(base_scroll + progressive_scroll, 1500)
            
            # 滾動容器
            self.driver.execute_script(f"arguments[0].scrollTop += {total_scroll}", container)
            time.sleep(1)
            
            # 同時滾動頁面
            self.driver.execute_script(f"window.scrollBy(0, {total_scroll // 2});")
            
        except Exception as e:
            self.debug_print(f"智能滾動失敗: {e}", "WARNING")
    
    def scroll_sidebar_list(self):
        """滾動側邊欄列表"""
        try:
            # 嘗試找到側邊欄的滾動區域
            sidebar_selectors = [
                "div[role='main'] div[role='region']",
                "div[data-value='search_results']",
                "div[jsaction*='scroll']",
                "[aria-label*='結果'] div"
            ]
            
            for selector in sidebar_selectors:
                try:
                    sidebar = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if sidebar and sidebar.is_displayed():
                        self.driver.execute_script("arguments[0].scrollTop += 800", sidebar)
                        return
                except:
                    continue
                    
        except Exception as e:
            self.debug_print(f"側邊欄滾動失敗: {e}", "WARNING")
    
    def page_scroll_down(self, scroll_count):
        """頁面整體滾動"""
        try:
            scroll_amount = 400 + (scroll_count * 30)
            self.driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
            
            # 使用鍵盤滾動
            body = self.driver.find_element(By.TAG_NAME, "body")
            for _ in range(3):
                body.send_keys(Keys.PAGE_DOWN)
                time.sleep(0.5)
                
        except Exception as e:
            self.debug_print(f"頁面滾動失敗: {e}", "WARNING")

    def extract_current_shops(self):
        """擷取當前可見的店家 - 改良版"""
        try:
            # 更全面的店家選擇器
            shop_selectors = [
                # 主要的店家連結
                "a[href*='/maps/place/']",
                "a[data-value='directions' i]",
                "a[href*='place_id']",
                
                # 各種可能的店家容器
                "div[role='article'] a",
                "div[jsaction*='click'] a[href*='place']", 
                "div[data-result-index] a",
                "[data-result-ad-index] a",
                
                # 新版Google Maps選擇器
                "div[role='feed'] a",
                "div[role='region'] a[href*='place']",
                "[jsaction*='mouseover'] a[href*='maps']",
                
                # 備用選擇器
                "a[aria-label][href*='place']",
                "a[data-cid] ",
                "div[data-header] a"
            ]
            
            all_shop_links = []
            total_found = 0
            
            for i, selector in enumerate(shop_selectors):
                try:
                    links = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    valid_links = []
                    
                    for link in links:
                        href = link.get_attribute('href')
                        if href and ('/maps/place/' in href or 'place_id=' in href):
                            valid_links.append(link)
                    
                    all_shop_links.extend(valid_links)
                    total_found += len(valid_links)
                    
                    if len(valid_links) > 0:
                        self.debug_print(f"選擇器 {i+1} 找到 {len(valid_links)} 個店家連結", "INFO")
                        
                except Exception as e:
                    self.debug_print(f"選擇器 {i+1} 失敗: {e}", "WARNING")
                    continue
            
            self.debug_print(f"總共找到 {total_found} 個店家連結", "INFO")
            
            # 去除重複連結
            unique_links = []
            seen_hrefs = set()
            
            for link in all_shop_links:
                try:
                    href = link.get_attribute('href')
                    if href and href not in seen_hrefs:
                        # 提取place_id或地點名稱作為唯一標識
                        place_id = self.extract_place_identifier(href)
                        if place_id and place_id not in seen_hrefs:
                            unique_links.append(link)
                            seen_hrefs.add(href)
                            seen_hrefs.add(place_id)
                except:
                    continue
            
            self.debug_print(f"去重後剩餘 {len(unique_links)} 個獨特店家", "INFO")
            
            new_shops = []
            processed_count = 0
            max_process_per_round = min(50, len(unique_links))  # 每輪最多處理50家
            
            for i, link in enumerate(unique_links[:max_process_per_round]):
                try:
                    processed_count += 1
                    
                    # 滾動到元素位置
                    try:
                        self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", link)
                        time.sleep(0.8)
                    except:
                        pass
                    
                    shop_info = self.extract_shop_info(link)
                    if shop_info and self.is_new_shop(shop_info):
                        self.shops_data.append(shop_info)
                        new_shops.append(shop_info)
                        self.debug_print(f"✅ 新增店家: {shop_info['name']}", "SUCCESS")
                        self.debug_print(f"   📍 地址: {shop_info['address'][:60]}...", "INFO")
                        self.debug_print(f"   📞 電話: {shop_info['phone']}", "INFO")
                        self.debug_print(f"📊 進度: {len(self.shops_data)}/{self.target_shops} ({processed_count}/{max_process_per_round})", "INFO")
                        
                        # 檢查是否達到目標
                        if len(self.shops_data) >= self.target_shops:
                            self.debug_print(f"🎯 達到{self.target_shops}家目標！", "TARGET")
                            break
                    else:
                        if shop_info:
                            self.debug_print(f"⚠️ 重複或無效店家: {shop_info.get('name', '未知')}", "WARNING")
                        
                except Exception as e:
                    self.debug_print(f"處理店家 {i+1} 時出錯: {e}", "ERROR")
                    continue
            
            self.debug_print(f"本輪成功新增 {len(new_shops)} 家店", "SUCCESS")
            return new_shops
            
        except Exception as e:
            self.debug_print(f"擷取店家錯誤: {e}", "ERROR")
            return []
    
    def extract_place_identifier(self, href):
        """從URL中提取地點標識符"""
        try:
            if 'place_id=' in href:
                # 提取place_id
                import re
                match = re.search(r'place_id=([^&]+)', href)
                if match:
                    return f"place_id_{match.group(1)}"
            
            if '/maps/place/' in href:
                # 提取地點名稱
                parts = href.split('/maps/place/')
                if len(parts) > 1:
                    place_part = parts[1].split('/')[0]
                    return urllib.parse.unquote(place_part)
            
            return href
            
        except Exception as e:
            return href

    def find_scrollable_container(self):
        """找到可滾動的容器 - 改良版"""
        try:
            # 更全面的滾動容器選擇器
            result_selectors = [
                # Google Maps的主要容器
                "div[role='main']",
                "div[role='region'][aria-label*='結果']",
                "div[role='region'][aria-label*='results' i]",
                "div[data-value='search_results']",
                
                # 側邊欄容器
                "div[jsaction*='scroll']",
                "[role='main'] > div > div",
                "div[role='feed']",
                
                # 搜尋結果列表
                "[aria-label*='結果'] div",
                "[aria-label*='results' i] div",
                "div[data-result-index]",
                
                # 備用選擇器
                "#pane",
                "body"
            ]
            
            for i, selector in enumerate(result_selectors):
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        if element and element.is_displayed():
                            # 檢查元素是否可滾動
                            scroll_height = self.driver.execute_script("return arguments[0].scrollHeight", element)
                            client_height = self.driver.execute_script("return arguments[0].clientHeight", element)
                            
                            if scroll_height > client_height:
                                self.debug_print(f"找到可滾動容器：選擇器 {i+1} - {selector}", "SUCCESS")
                                return element
                except Exception as e:
                    self.debug_print(f"選擇器 {i+1} 檢查失敗: {e}", "WARNING")
                    continue
            
            # 如果都找不到，返回body
            self.debug_print("使用body作為滾動容器", "WARNING")
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
            successful_lines = sum(1 for shop in unique_shops if shop.get('line_contact', 'LINE未提供') not in ['LINE未提供', 'LINE獲取失敗'])
            
            self.debug_print(f"📊 統計資料:", "INFO")
            self.debug_print(f"   - 總店家數: {len(unique_shops)}", "INFO")
            self.debug_print(f"   - 成功獲取地址: {successful_addresses}", "INFO")
            self.debug_print(f"   - 成功獲取電話: {successful_phones}", "INFO")
            self.debug_print(f"   - 成功獲取LINE: {successful_lines}", "INFO")
            self.debug_print(f"   - 聯絡方式覆蓋率: {((successful_phones + successful_lines) / len(unique_shops) * 100):.1f}%", "INFO")
            
            return True
            
        except Exception as e:
            self.debug_print(f"儲存失敗: {e}", "ERROR")
            return False
    
    def get_kaohsiung_landmarks(self):
        """獲取高雄重要地標列表 - 完整覆蓋版"""
        landmarks = [
            # === 主要行政區中心和火車站 ===
            "高雄火車站", "高雄市政府", "鳳山火車站", "鳳山區公所",
            "左營高鐵站", "左營火車站", "左營區公所", "楠梓火車站", "楠梓區公所",
            "三民區公所", "苓雅區公所", "新興區公所", "前金區公所",
            "鼓山區公所", "前鎮區公所", "小港機場", "小港區公所",
            "仁武區公所", "大社區公所", "岡山火車站", "岡山區公所",
            "路竹火車站", "路竹區公所", "湖內區公所", "茄萣區公所",
            "永安區公所", "彌陀區公所", "梓官區公所", "橋頭火車站", "橋頭區公所",
            "燕巢區公所", "田寮區公所", "阿蓮區公所", "大樹區公所",
            "大寮區公所", "林園區公所", "鳥松區公所", "旗山火車站", "旗山區公所",
            "美濃區公所", "六龜區公所", "甲仙區公所", "杉林區公所", "內門區公所",
            "茂林區公所", "桃源區公所", "那瑪夏區公所",

            # === 重要商圈和購物中心 ===
            "新崛江商圈", "五福商圈", "巨蛋商圈", "夢時代購物中心",
            "大立百貨", "漢神百貨", "漢神巨蛋", "新光三越左營店", "統一夢時代",
            "草衙道購物中心", "義享天地", "大遠百高雄店", "太平洋SOGO高雄店",
            "環球購物中心左營店", "家樂福鳳山店", "好市多高雄店", "IKEA高雄店",
            "三多商圈", "文化中心商圈", "美麗島商圈", "建國商圈",

            # === 夜市和傳統市場 ===
            "六合夜市", "瑞豐夜市", "光華夜市", "凱旋夜市",
            "興中夜市", "南華路夜市", "青年夜市", "自強夜市",
            "鳳山中華街夜市", "左營果貿市場", "三鳳中街", "新興市場",

            # === 醫院 ===
            "高雄榮總", "高雄醫學大學附設醫院", "長庚紀念醫院高雄院區",
            "義大醫院", "阮綜合醫院", "高雄市立聯合醫院", "高雄市立大同醫院",
            "高雄市立民生醫院", "高雄市立小港醫院", "國軍高雄總醫院",
            "聖功醫院", "安泰醫院", "建佑醫院", "仁愛醫院",

            # === 大學和學校 ===
            "高雄大學", "中山大學", "高雄醫學大學", "高雄師範大學",
            "文藻外語大學", "正修科技大學", "高雄科技大學", "實踐大學高雄校區",
            "樹德科技大學", "輔英科技大學", "高雄餐旅大學", "和春技術學院",
            "義守大學", "高雄第一科技大學", "高雄海洋科技大學",

            # === 觀光景點 ===
            "西子灣", "旗津海岸公園", "愛河", "蓮池潭", "佛光山",
            "義大世界", "壽山動物園", "澄清湖", "打狗英國領事館",
            "駁二藝術特區", "高雄流行音樂中心", "亞洲新灣區", "旗津風車公園",
            "旗津燈塔", "鳳山熱帶園藝試驗所", "美濃民俗村", "茂林國家風景區",

            # === 捷運站 (重要站點) ===
            "美麗島站", "中央公園站", "三多商圈站", "巨蛋站",
            "左營站", "生態園區站", "鳳山西站", "大東站",
            "衛武營站", "技擊館站", "凹子底站", "後驛站",
            "高雄車站", "鹽埕埔站", "市議會站", "油廠國小站",

            # === 工業區和科學園區 ===
            "林園工業區", "大社工業區", "仁武工業區", "臨海工業區",
            "路竹科學園區", "橋頭科學園區", "高雄軟體科技園區", "楠梓加工出口區",
            "高雄港", "中鋼集團", "中油高雄煉油廠",

            # === 各區重要地標 ===
            # 鳳山區
            "鳳山體育館", "鳳山國父紀念館", "大東文化藝術中心", "鳳儀書院",
            
            # 左營區
            "左營蓮池潭", "左營舊城", "春秋閣", "龍虎塔", "孔廟",
            
            # 三民區
            "三民家商", "高雄市立圖書館總館", "河堤社區", "覺民路",
            
            # 苓雅區
            "文化中心", "五福路", "和平路", "青年路",
            
            # 前鎮區
            "前鎮區圖書館", "獅甲國小", "勞工公園", "復興路",
            
            # 小港區
            "小港國際機場", "小港醫院", "山明路", "沿海路",
            
            # 鼓山區
            "西子灣隧道", "鼓山輪渡站", "美術館", "內惟",
            
            # 楠梓區
            "楠梓火車站", "楠梓高中", "後勁", "加昌路",
            
            # 仁武區
            "仁武澄觀路", "仁武八德路", "仁心路", "鳳仁路",
            
            # 大寮區
            "大寮鳳林路", "大寮捷運站", "永芳路", "鳳林公園",
            
            # 林園區
            "林園中芸", "林園港埔", "林園工業區管理處", "東汕路",
            
            # 鳥松區
            "鳥松澄清湖", "鳥松神農路", "本館路", "大埤路",
            
            # 岡山區
            "岡山火車站", "岡山區公所", "中山路", "維仁路",
            
            # 橋頭區
            "橋頭糖廠", "橋頭火車站", "成功路", "隆豐路",
            
            # 梓官區
            "梓官區公所", "進學路", "中正路", "梓官漁港",
            
            # 旗山區
            "旗山老街", "旗山車站", "中山路", "延平路",
            
            # 美濃區
            "美濃客家文物館", "美濃中正路", "泰安路", "光明路",

            # === 其他重要地點 ===
            "85大樓", "高雄展覽館", "高雄圖書館新總館", "衛武營國家藝術文化中心",
            "世運主場館", "高雄巨蛋", "鳳山體育館", "澄清湖棒球場",
            "蓮潭國際會館", "高雄港埠旅運中心", "棧貳庫", "哈瑪星台灣鐵道館",
            
            # === 重要道路交匯點 ===
            "中正路與五福路口", "建國路與七賢路口", "青年路與中山路口",
            "民族路與自由路口", "河堤路與文藻外語大學", "博愛路與九如路口"
        ]
        
        self.debug_print(f"📍 完整地標清單載入完成，共 {len(landmarks)} 個地標", "SUCCESS")
        self.debug_print("🗺️ 涵蓋範圍：高雄市38個行政區 + 重要商圈 + 交通樞紐", "INFO")
        
        return landmarks
    
    def run_precision_scraping(self):
        """執行精準搜索 - 改良版"""
        start_time = time.time()
        
        try:
            self.debug_print("🚀 開始高雄地區美甲美睫店家精準搜索 (完整覆蓋版)", "INFO")
            self.debug_print(f"🎯 目標：收集 {self.target_shops} 家店家", "TARGET")
            self.debug_print("🔍 關鍵字：美甲、美睫、耳燭、採耳、熱蠟", "INFO")
            self.debug_print("📍 範圍：高雄市全區域（地址只需包含高雄）", "INFO")
            self.debug_print("🛠️ 改良項目：", "INFO")
            self.debug_print("   - 完整覆蓋高雄市所有區域", "INFO")
            self.debug_print("   - 詳細滾動監控和統計", "INFO")
            self.debug_print("   - 簡化地址驗證（只要有高雄）", "INFO")
            self.debug_print("   - 無頭模式詳細進度報告", "INFO")
            print("=" * 70)
            
            if not self.setup_driver():
                return False
            
            if not self.open_google_maps():
                return False
            
            # 搜索關鍵字
            shop_types = ["美甲", "美睫", "耳燭", "採耳", "熱蠟"]
            landmarks = self.get_kaohsiung_landmarks()
            
            # 使用完整的地標清單，不限制數量
            selected_landmarks = landmarks  # 使用全部地標
            
            self.debug_print(f"📍 搜索地標: {len(selected_landmarks)} 個 (完整版)", "INFO")
            self.debug_print(f"🏪 店家類型: {len(shop_types)} 種", "INFO")
            self.debug_print(f"🔍 預估搜索次數: {len(selected_landmarks) * len(shop_types)} 次", "INFO")
            self.debug_print(f"⏱️ 預估時間: {len(selected_landmarks) * len(shop_types) * 2} 分鐘", "INFO")
            print("-" * 50)
            
            total_searches = len(selected_landmarks) * len(shop_types)
            current_search = 0
            successful_searches = 0
            skipped_searches = 0
            
            # 對每個地標進行搜索
            for i, landmark in enumerate(selected_landmarks, 1):
                self.debug_print(f"[{i}/{len(selected_landmarks)}] 🗺️ 地標: {landmark}", "INFO")
                
                if not self.set_location(landmark):
                    self.debug_print(f"❌ 無法定位到 {landmark}，跳過", "WARNING")
                    skipped_searches += len(shop_types)
                    continue
                
                # 對每種店家類型進行搜索
                for j, shop_type in enumerate(shop_types, 1):
                    current_search += 1
                    progress = (current_search / total_searches) * 100
                    
                    self.debug_print(f"[{j}/{len(shop_types)}] 🔍 搜索 {shop_type} (總進度: {progress:.1f}%)", "INFO")
                    
                    # 檢查是否達到目標
                    if len(self.shops_data) >= self.target_shops:
                        self.debug_print(f"🎯 達到{self.target_shops}家目標！提前結束", "TARGET")
                        break
                    
                    if not self.search_nearby_shops(shop_type, landmark):
                        self.debug_print(f"❌ 搜索 {shop_type} 失敗", "WARNING")
                        continue
                    
                    # 開始滾動擷取，使用詳細監控
                    initial_count = len(self.shops_data)
                    self.debug_print(f"📊 滾動前店家數: {initial_count}", "INFO")
                    
                    should_continue = self.scroll_and_extract()
                    
                    final_count = len(self.shops_data)
                    found_in_this_search = final_count - initial_count
                    
                    if found_in_this_search > 0:
                        successful_searches += 1
                        self.debug_print(f"✅ 成功搜索：{shop_type} @ {landmark}，新增 {found_in_this_search} 家", "SUCCESS")
                        self.debug_print(f"   📈 成功率: {found_in_this_search} 家/搜索", "SUCCESS")
                    else:
                        self.debug_print(f"⚠️ 此次搜索無新店家：{shop_type} @ {landmark}", "WARNING")
                    
                    # 階段性統計
                    self.debug_print(f"📊 階段總結:", "INFO")
                    self.debug_print(f"   🏪 目前總數: {len(self.shops_data)} 家", "INFO")
                    self.debug_print(f"   ✅ 成功搜索: {successful_searches}/{current_search}", "INFO")
                    self.debug_print(f"   📈 成功率: {successful_searches/current_search*100:.1f}%" if current_search > 0 else "   📈 成功率: 0%", "INFO")
                    self.debug_print(f"   🎯 目標進度: {len(self.shops_data)}/{self.target_shops} ({len(self.shops_data)/self.target_shops*100:.1f}%)", "INFO")
                    
                    if not should_continue:
                        self.debug_print(f"🎯 達到目標，停止搜索", "TARGET")
                        break
                    
                    # 搜索間隔
                    if current_search < total_searches and len(self.shops_data) < self.target_shops:
                        wait_time = random.uniform(3, 6)
                        self.debug_print(f"⏳ 搜索間隔等待 {wait_time:.1f} 秒...", "WAIT")
                        time.sleep(wait_time)
                
                # 檢查是否達到目標
                if len(self.shops_data) >= self.target_shops:
                    break
                
                # 每完成5個地標暫存一次
                if i % 5 == 0 and self.shops_data:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    temp_filename = f"高雄美甲美睫_暫存_{len(self.shops_data)}家_{timestamp}"
                    self.save_to_excel(temp_filename)
                    self.debug_print(f"💾 已暫存 {len(self.shops_data)} 家店家資料", "SAVE")
                
                # 地標間隔
                if i < len(selected_landmarks) and len(self.shops_data) < self.target_shops:
                    time.sleep(random.uniform(4, 8))
            
            print("\n" + "=" * 70)
            
            # 儲存最終結果
            if self.shops_data:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                if len(self.shops_data) >= self.target_shops:
                    final_filename = f"高雄美甲美睫店家_完成_{self.target_shops}家_{timestamp}"
                    status = "完成目標"
                else:
                    final_filename = f"高雄美甲美睫店家_完整_{len(self.shops_data)}家_{timestamp}"
                    status = "完整搜索"
                
                self.save_to_excel(final_filename)
                
                elapsed_time = time.time() - start_time
                hours = elapsed_time // 3600
                minutes = (elapsed_time % 3600) // 60
                
                if hours > 0:
                    time_str = f"{int(hours)}小時{int(minutes)}分"
                else:
                    time_str = f"{int(minutes)}分"
                
                self.debug_print(f"✅ 搜索完成！狀態: {status}", "SUCCESS")
                self.debug_print(f"📊 最終收集: {len(self.shops_data)} 家店家", "SUCCESS")
                self.debug_print(f"⏱️ 執行時間: {time_str}", "SUCCESS")
                self.debug_print(f"📈 成功搜索率: {successful_searches}/{current_search} ({successful_searches/current_search*100:.1f}%)" if current_search > 0 else "📈 搜索統計: 無", "SUCCESS")
                
                if len(self.shops_data) >= self.target_shops:
                    self.debug_print(f"🎯 恭喜！成功達到 {self.target_shops} 家目標！", "TARGET")
                else:
                    self.debug_print(f"⚠️ 未達目標，但已盡力搜索。建議：", "WARNING")
                    self.debug_print(f"   1. 檢查網路連線", "INFO")
                    self.debug_print(f"   2. 嘗試在不同時間執行", "INFO")
                    self.debug_print(f"   3. 調整搜索關鍵字", "INFO")
                
            else:
                self.debug_print("❌ 未找到任何店家，請檢查：", "ERROR")
                self.debug_print("   1. 網路連線是否正常", "INFO")
                self.debug_print("   2. Firefox 和 geckodriver 是否正確安裝", "INFO")
                self.debug_print("   3. Google Maps 是否可以正常訪問", "INFO")
            
            return True
            
        except Exception as e:
            self.debug_print(f"❌ 搜索失敗: {e}", "ERROR")
            # 如果有部分資料，還是要儲存
            if self.shops_data:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                emergency_filename = f"高雄美甲美睫_緊急備份_{len(self.shops_data)}家_{timestamp}"
                self.save_to_excel(emergency_filename)
                self.debug_print(f"💾 已緊急備份 {len(self.shops_data)} 家店家資料", "SAVE")
            return False
        
        finally:
            if self.driver:
                self.debug_print("🔄 關閉瀏覽器...", "INFO")
                time.sleep(3)
                try:
                    self.driver.quit()
                    self.debug_print("✅ 瀏覽器已關閉", "SUCCESS")
                except:
                    self.debug_print("⚠️ 瀏覽器關閉時出現警告（可忽略）", "WARNING")

    def extract_line_contact_detailed(self):
        """從店家詳細頁面擷取LINE聯絡方式 - 增強版"""
        try:
            self.debug_print("📱 開始提取LINE聯絡方式...", "INFO")
            
            # LINE聯絡方式的選擇器
            line_selectors = [
                # 直接的LINE連結
                "a[href*='line.me']",
                "a[href*='lin.ee']",
                "a[href*='line://']",
                
                # 包含LINE文字的元素
                "[aria-label*='LINE']",
                "[aria-label*='line']",
                "button[aria-label*='LINE']",
                
                # 通用選擇器中可能包含LINE的
                ".fontBodyMedium",
                "span.fontBodyMedium",
                "div[role='button'] span",
                "[role='button'] .fontBodyMedium",
                "button span",
                "a span",
                
                # 網站連結中可能包含LINE的
                "[data-item-id*='website'] a",
                "[data-item-id*='website'] span",
                "a[href*='instagram.com']",  # 有時候會放在社群媒體區域
                
                # 其他可能的選擇器
                "[jsaction*='website'] a",
                ".section-info-line a",
                ".section-info-text a"
            ]
            
            # 先嘗試用選擇器找LINE
            for i, selector in enumerate(line_selectors):
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    self.debug_print(f"🔍 LINE選擇器 {i+1} ({selector}) 找到 {len(elements)} 個元素", "INFO")
                    
                    for j, element in enumerate(elements):
                        if element:
                            # 檢查href屬性
                            href = element.get_attribute('href') or ''
                            text = element.text.strip()
                            
                            self.debug_print(f"   元素 {j+1}: href='{href}' text='{text}'", "INFO")
                            
                            # 檢查是否為LINE連結
                            if self.is_line_contact(href) or self.is_line_contact(text):
                                line_contact = href if href else text
                                self.debug_print(f"✅ LINE選擇器 {i+1} 找到LINE聯絡方式: {line_contact}", "SUCCESS")
                                return line_contact
                                        
                except Exception as e:
                    self.debug_print(f"LINE選擇器 {i+1} 失敗: {e}", "WARNING")
                    continue
            
            # 從頁面文字中搜尋LINE相關資訊
            try:
                page_text = self.driver.find_element(By.TAG_NAME, "body").text
                import re
                
                # LINE相關的正則表達式模式
                line_patterns = [
                    r'line\.me/[A-Za-z0-9_-]+',      # line.me/xxxxx
                    r'lin\.ee/[A-Za-z0-9_-]+',       # lin.ee/xxxxx
                    r'@[A-Za-z0-9_-]{3,20}',         # @line_id
                    r'LINE\s*ID\s*[:：]\s*[@]?[A-Za-z0-9_-]+',  # LINE ID: xxxxx
                    r'LINE\s*[:：]\s*[@]?[A-Za-z0-9_-]+',       # LINE: xxxxx
                    r'加LINE\s*[:：]\s*[@]?[A-Za-z0-9_-]+',     # 加LINE: xxxxx
                ]
                
                self.debug_print("🔍 使用正則表達式搜尋LINE...", "INFO")
                for i, pattern in enumerate(line_patterns):
                    matches = re.findall(pattern, page_text, re.IGNORECASE)
                    if matches:
                        line_contact = matches[0].strip()
                        self.debug_print(f"✅ 正則表達式 {i+1} 找到LINE: {line_contact}", "SUCCESS")
                        return line_contact
                        
            except Exception as e:
                self.debug_print(f"正則表達式提取LINE失敗: {e}", "WARNING")
            
            self.debug_print("❌ 未能找到LINE聯絡方式", "WARNING")
            return 'LINE未提供'
            
        except Exception as e:
            self.debug_print(f"LINE聯絡方式提取失敗: {e}", "ERROR")
            return 'LINE獲取失敗'
    
    def is_line_contact(self, text):
        """檢查文字是否為LINE聯絡方式"""
        if not text:
            return False
        
        text = text.lower().strip()
        
        # 檢查是否包含LINE相關關鍵字和格式
        line_indicators = [
            'line.me/',
            'lin.ee/',
            'line://',
            text.startswith('@') and len(text) > 3,  # @開頭的ID
            'line id' in text,
            '加line' in text,
            text.startswith('line:')
        ]
        
        return any(line_indicators)

def main():
    """主程式"""
    print("🚀 高雄地區美甲美睫店家精準搜索程式 (Firefox版)")
    print()
    print("🎯 搜索目標：")
    print("   - 收集2000家店家資料")
    print("   - 店家名稱、地圖連結、地址、電話")
    print("   - 確保地址包含高雄")
    print()
    print("🔍 搜索關鍵字：")
    print("   - 美甲、美睫、耳燭、採耳、熱蠟")
    print()
    print("📍 搜索範圍：")
    print("   - 高雄市所有區域重要地標 (180+個)")
    print("   - 地址驗證：只要包含'高雄'即可")
    print()
    print("🦊 瀏覽器：Firefox")
    print("⏰ 預估時間：約1-2小時")
    print("💾 自動儲存Excel和CSV檔案")
    print()
    print("📋 系統需求：")
    print("   - 已安裝 Firefox 瀏覽器")
    print("   - 已安裝 geckodriver")
    print("-" * 50)
    
    # 詢問是否顯示瀏覽器視窗
    print("🖥️ 瀏覽器顯示設定：")
    print("   1. 顯示視窗 (推薦本地端使用，可觀察進度)")
    print("   2. 無頭模式 (推薦伺服器使用，較穩定)")
    print()
    
    while True:
        browser_choice = input("請選擇瀏覽器模式 (1/2): ").strip()
        if browser_choice == "1":
            show_browser = True
            print("✅ 選擇：顯示瀏覽器視窗")
            break
        elif browser_choice == "2":
            show_browser = False
            print("✅ 選擇：無頭模式")
            break
        else:
            print("❌ 請輸入 1 或 2")
    
    print("-" * 50)
    user_input = input("確定要開始搜索嗎？(y/n): ").strip().lower()
    if user_input != 'y':
        print("程式已取消")
        return
    
    scraper = KaohsiungPrecisionScraper(debug_mode=True, show_browser=show_browser)
    scraper.run_precision_scraping()

if __name__ == "__main__":
    main() 