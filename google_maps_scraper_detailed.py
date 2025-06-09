#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Google 地圖店家資訊擷取程式 (詳細版)
整合快速版的改進邏輯 + 詳細資訊擷取
- 使用更小的搜索半徑和更多的搜索點，確保覆蓋所有區域
- 改進的重複檢查機制，按位置分離避免誤判
- 多種CSS選擇器和重試機制，提高擷取成功率
- 獲取詳細資訊：店家名稱、地址、電話、營業時間、評分、Google Maps連結
"""

import time
import random
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from selenium.webdriver.common.action_chains import ActionChains
import logging
from datetime import datetime
import re
import urllib.parse

# 確保安裝了 openpyxl 用於 Excel 輸出
try:
    import openpyxl
except ImportError:
    print("⚠️ 未安裝 openpyxl，將安裝該套件以支援 Excel 輸出...")
    import subprocess
    import sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "openpyxl"])
    import openpyxl

class GoogleMapsDetailedScraper:
    def __init__(self, debug_mode=True):
        self.debug_mode = debug_mode
        self.setup_logging()
        self.driver = None
        self.shops_data = []
        self.current_location_shops = []  # 新增：當前位置的店家暫存
        self.current_location = None
        self.search_radius_km = 3  # 搜尋半徑縮小到3公里，超精確模式
        self.target_shops = 2000  # 目標店家數量提升至2000家
        self.coverage_multiplier = 1.8  # 180%覆蓋率
        
    def setup_logging(self):
        """設定日誌記錄"""
        log_level = logging.DEBUG if self.debug_mode else logging.INFO
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('scraper_detailed.log', encoding='utf-8'),
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
            "SAVE": "💾"
        }
        symbol = symbols.get(level, "📋")
        print(f"[{timestamp}] {symbol} {message}")
        if self.debug_mode:
            self.logger.info(f"{level}: {message}")
    
    def setup_driver(self):
        """設定瀏覽器驅動器"""
        try:
            self.debug_print("正在設定瀏覽器...", "INFO")
            chrome_options = Options()
            
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            chrome_options.add_argument("--start-maximized")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
            
            if not self.debug_mode:
                chrome_options.add_argument("--headless")
            
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            self.debug_print("瀏覽器設定完成", "SUCCESS")
            return True
            
        except Exception as e:
            self.debug_print(f"瀏覽器設定失敗: {e}", "ERROR")
            return False
    
    def open_google_maps(self):
        """開啟 Google 地圖"""
        try:
            self.debug_print("正在開啟 Google 地圖...", "INFO")
            self.driver.get("https://www.google.com/maps")
            
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            time.sleep(5)
            self.handle_consent_popup()
            
            self.debug_print("Google 地圖載入完成", "SUCCESS")
            return True
            
        except Exception as e:
            self.debug_print(f"開啟 Google 地圖失敗: {e}", "ERROR")
            return False
    
    def handle_consent_popup(self):
        """處理同意視窗"""
        try:
            self.debug_print("檢查是否有同意視窗...", "INFO")
            time.sleep(2)
            
            consent_xpaths = [
                "//button[contains(text(), '接受全部') or contains(text(), 'Accept all')]",
                "//button[contains(text(), '接受') or contains(text(), 'Accept')]", 
                "//button[contains(text(), '同意') or contains(text(), 'Agree')]"
            ]
            
            for xpath in consent_xpaths:
                try:
                    consent_button = WebDriverWait(self.driver, 2).until(
                        EC.element_to_be_clickable((By.XPATH, xpath))
                    )
                    self.debug_print(f"找到同意按鈕，準備點擊: {xpath}", "CLICK")
                    consent_button.click()
                    self.debug_print("已點擊同意按鈕", "SUCCESS")
                    time.sleep(2)
                    return True
                except:
                    continue
                    
            self.debug_print("未發現同意視窗", "INFO")
            return True
            
        except Exception as e:
            self.debug_print("同意視窗處理完成", "INFO")
            return True
    
    def set_location(self, location_name):
        """設定定位到指定地點"""
        try:
            self.debug_print(f"正在定位到: {location_name}", "INFO")
            
            # 切換位置時重置當前位置的店家列表
            if self.current_location != location_name:
                self.current_location_shops = []
                self.debug_print(f"切換到新位置，重置店家列表", "INFO")
            
            self.debug_print("尋找搜尋框元素...", "EXTRACT")
            search_box = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "searchboxinput"))
            )
            
            self.debug_print("點擊搜尋框並清空內容", "CLICK")
            search_box.clear()
            time.sleep(1)
            
            # 逐字輸入定位地點
            self.debug_print(f"開始逐字輸入地點名稱: {location_name}", "INFO")
            for i, char in enumerate(location_name):
                search_box.send_keys(char)
                if self.debug_mode and i % 2 == 0:  # 每兩個字元顯示一次進度
                    self.debug_print(f"輸入進度: {char} ({i+1}/{len(location_name)})", "INFO")
                time.sleep(random.uniform(0.08, 0.15))
            
            self.debug_print("輸入完成，按下 Enter 鍵", "CLICK")
            time.sleep(1)
            search_box.send_keys(Keys.ENTER)
            
            self.debug_print(f"等待定位到 {location_name}...", "WAIT")
            time.sleep(8)
            
            self.debug_print(f"成功定位到 {location_name}", "SUCCESS")
            self.current_location = location_name
            return True
            
        except Exception as e:
            self.debug_print(f"定位失敗: {e}", "ERROR")
            return False
    
    def search_nearby_shops_with_radius(self, shop_type):
        """在當前定位附近指定半徑內搜尋店家"""
        try:
            self.debug_print(f"在 {self.current_location} 周圍 {self.search_radius_km} 公里內搜尋: {shop_type}", "INFO")
            
            self.debug_print("尋找搜尋框元素...", "EXTRACT")
            search_box = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "searchboxinput"))
            )
            
            self.debug_print("清空搜尋框", "CLICK")
            search_box.clear()
            time.sleep(1)
            
            # 構建帶有距離限制的搜尋查詢
            search_query = f"{shop_type} near {self.current_location} within {self.search_radius_km}km"
            self.debug_print(f"搜尋查詢字串: {search_query}", "INFO")
            
            # 輸入搜尋查詢
            self.debug_print("開始輸入搜尋查詢...", "INFO")
            for i, char in enumerate(search_query):
                search_box.send_keys(char)
                if self.debug_mode and i % 5 == 0:  # 每五個字元顯示一次進度
                    progress = f"{i+1}/{len(search_query)}"
                    self.debug_print(f"搜尋輸入進度: {progress}", "INFO")
                time.sleep(random.uniform(0.05, 0.12))
            
            self.debug_print("搜尋輸入完成，按下 Enter", "CLICK")
            time.sleep(1)
            search_box.send_keys(Keys.ENTER)
            
            self.debug_print("等待搜尋結果載入...", "WAIT")
            time.sleep(10)
            
            return True
            
        except Exception as e:
            self.debug_print(f"搜尋附近店家失敗: {e}", "ERROR")
            return False
    
    def extract_shop_info_detailed(self, link_element):
        """詳細版店家資訊擷取 - 改進版，增加重試機制和多種名稱擷取方法"""
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                # 先獲取基本資訊
                shop_info = {}
                
                self.debug_print(f"開始擷取店家基本資訊... (嘗試 {attempt + 1}/{max_retries})", "EXTRACT")
                
                # 多種方式獲取店家名稱
                name = None
                
                # 方式1: aria-label
                try:
                    name = link_element.get_attribute('aria-label')
                    if name and name.strip():
                        self.debug_print(f"透過aria-label獲取名稱: {name[:30]}...", "EXTRACT")
                except:
                    pass
                
                # 方式2: 元素文字
                if not name:
                    try:
                        name = link_element.text
                        if name and name.strip():
                            self.debug_print(f"透過元素文字獲取名稱: {name[:30]}...", "EXTRACT")
                    except:
                        pass
                
                # 方式3: 從父元素獲取
                if not name:
                    try:
                        parent = link_element.find_element(By.XPATH, "..")
                        name = parent.get_attribute('aria-label') or parent.text
                        if name and name.strip():
                            self.debug_print(f"透過父元素獲取名稱: {name[:30]}...", "EXTRACT")
                    except:
                        pass
                
                # 方式4: 從兄弟元素獲取
                if not name:
                    try:
                        siblings = link_element.find_elements(By.XPATH, "..//span | ..//div")
                        for sibling in siblings[:3]:  # 只檢查前3個兄弟元素
                            sibling_text = sibling.text or sibling.get_attribute('aria-label')
                            if sibling_text and len(sibling_text.strip()) > 2:
                                name = sibling_text
                                self.debug_print(f"透過兄弟元素獲取名稱: {name[:30]}...", "EXTRACT")
                                break
                    except:
                        pass
                
                # 方式5: 從URL解析名稱
                if not name:
                    try:
                        href = link_element.get_attribute('href')
                        if href and '/maps/place/' in href:
                            # 從URL中提取店家名稱
                            url_parts = href.split('/maps/place/')
                            if len(url_parts) > 1:
                                place_info = url_parts[1].split('/')[0]
                                decoded_name = urllib.parse.unquote(place_info)
                                if decoded_name and len(decoded_name.strip()) > 2:
                                    name = decoded_name
                                    self.debug_print(f"透過URL解析獲取名稱: {name[:30]}...", "EXTRACT")
                    except:
                        pass
                
                if not name or len(name.strip()) == 0:
                    if attempt < max_retries - 1:
                        self.debug_print(f"第 {attempt + 1} 次嘗試失敗，重試中...", "WARNING")
                        time.sleep(0.5)
                        continue
                    else:
                        self.debug_print("所有嘗試都失敗，跳過此店家", "ERROR")
                        return None
                
                # 清理店家名稱
                name = name.strip()
                
                # 移除不必要的前綴和後綴
                prefixes_to_remove = ['搜尋', '前往', '路線', '導航', '評論']
                for prefix in prefixes_to_remove:
                    if name.startswith(prefix):
                        name = name[len(prefix):].strip()
                
                # 如果名稱太短或包含無意義內容，跳過
                if len(name) < 2:
                    if attempt < max_retries - 1:
                        continue
                    return None
                
                invalid_keywords = ['undefined', 'null', '載入中', 'loading', '...']
                if any(keyword in name.lower() for keyword in invalid_keywords):
                    if attempt < max_retries - 1:
                        continue
                    return None
                    
                shop_info['name'] = name
                shop_info['search_location'] = self.current_location
                shop_info['google_maps_url'] = link_element.get_attribute('href')
                
                self.debug_print(f"正在獲取店家詳細資訊: {shop_info['name']}", "INFO")
                
                # 記住當前頁面的handle
                main_window = self.driver.current_window_handle
                
                try:
                    # 點擊店家連結 (在新分頁開啟)
                    self.debug_print(f"準備點擊店家連結: {shop_info['name']}", "CLICK")
                    self.driver.execute_script("arguments[0].setAttribute('target', '_blank');", link_element)
                    link_element.click()
                    time.sleep(3)
                    
                    # 切換到新分頁
                    all_windows = self.driver.window_handles
                    if len(all_windows) > 1:
                        self.debug_print("切換到新分頁", "INFO")
                        self.driver.switch_to.window(all_windows[-1])
                        
                        # 等待詳細頁面載入
                        self.debug_print("等待詳細頁面載入...", "WAIT")
                        time.sleep(5)
                        
                        # 獲取詳細資訊
                        detailed_info = self.extract_details_from_page()
                        shop_info.update(detailed_info)
                        
                        # 關閉詳細頁面
                        self.debug_print("關閉詳細頁面", "INFO")
                        self.driver.close()
                        
                        # 切換回主頁面
                        self.debug_print("切換回搜尋結果頁面", "INFO")
                        self.driver.switch_to.window(main_window)
                        time.sleep(2)
                        
                    else:
                        # 如果沒有新分頁，在當前頁面處理
                        self.debug_print("在當前頁面處理詳細資訊", "INFO")
                        time.sleep(5)
                        detailed_info = self.extract_details_from_page()
                        shop_info.update(detailed_info)
                        
                        # 返回搜尋結果頁面
                        self.debug_print("返回搜尋結果頁面", "CLICK")
                        self.driver.back()
                        time.sleep(3)
                        
                except Exception as e:
                    self.debug_print(f"獲取詳細資訊時出錯: {e}", "ERROR")
                    
                    # 確保回到主頁面
                    if len(self.driver.window_handles) > 1:
                        self.driver.switch_to.window(main_window)
                    
                    # 設定預設值
                    shop_info.update({
                        'address': '地址獲取失敗',
                        'phone': '電話獲取失敗',
                        'hours': '營業時間獲取失敗',
                        'rating': '評分獲取失敗'
                    })
                
                self.debug_print(f"成功擷取店家: {name}", "SUCCESS")
                return shop_info
                
            except Exception as e:
                if attempt < max_retries - 1:
                    self.debug_print(f"第 {attempt + 1} 次擷取失敗: {e}，重試中...", "WARNING")
                    time.sleep(0.5)
                    continue
                else:
                    self.debug_print(f"店家資訊擷取完全失敗: {e}", "ERROR")
                    return None
        
        return None
    
    def extract_details_from_page(self):
        """從店家詳細頁面擷取資訊"""
        details = {
            'address': '地址未提供',
            'phone': '電話未提供', 
            'hours': '營業時間未提供',
            'rating': '評分未提供'
        }
        
        try:
            # 等待頁面載入
            self.debug_print("等待詳細頁面完全載入...", "WAIT")
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # 獲取地址
            self.debug_print("開始擷取地址資訊...", "EXTRACT")
            try:
                address_selectors = [
                    "[data-item-id='address'] .fontBodyMedium",
                    "[aria-label*='地址']",
                    ".rogA2c .fontBodyMedium",  # 常見的地址選擇器
                    "div[data-value='Address'] .fontBodyMedium"
                ]
                
                for i, selector in enumerate(address_selectors):
                    try:
                        self.debug_print(f"嘗試地址選擇器 {i+1}: {selector}", "EXTRACT")
                        address_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                        if address_element and address_element.text.strip():
                            details['address'] = address_element.text.strip()
                            self.debug_print(f"✅ 成功獲取地址: {details['address']}", "SUCCESS")
                            break
                    except:
                        continue
                        
                if details['address'] == '地址未提供':
                    self.debug_print("❌ 無法獲取地址", "WARNING")
            except:
                self.debug_print("地址擷取過程出錯", "ERROR")
            
            # 獲取電話
            self.debug_print("開始擷取電話資訊...", "EXTRACT")
            try:
                phone_selectors = [
                    "[data-item-id='phone:tel:'] .fontBodyMedium",
                    "[aria-label*='電話']",
                    "button[data-value^='phone'] .fontBodyMedium",
                    "div[data-value='Phone'] .fontBodyMedium"
                ]
                
                for i, selector in enumerate(phone_selectors):
                    try:
                        self.debug_print(f"嘗試電話選擇器 {i+1}: {selector}", "EXTRACT")
                        phone_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                        if phone_element and phone_element.text.strip():
                            details['phone'] = phone_element.text.strip()
                            self.debug_print(f"✅ 成功獲取電話: {details['phone']}", "SUCCESS")
                            break
                    except:
                        continue
                        
                if details['phone'] == '電話未提供':
                    self.debug_print("❌ 無法獲取電話", "WARNING")
            except:
                self.debug_print("電話擷取過程出錯", "ERROR")
            
            # 獲取營業時間（需要處理展開）
            self.debug_print("開始擷取營業時間資訊...", "EXTRACT")
            details['hours'] = self.extract_business_hours_detailed()
            
            # 獲取評分
            self.debug_print("開始擷取評分資訊...", "EXTRACT")
            try:
                rating_selectors = [
                    ".F7nice span[aria-hidden='true']",  # 評分數字
                    ".ceNzKf[aria-label*='顆星']",
                    "span.Aq14fc"
                ]
                
                for i, selector in enumerate(rating_selectors):
                    try:
                        self.debug_print(f"嘗試評分選擇器 {i+1}: {selector}", "EXTRACT")
                        rating_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                        if rating_element and rating_element.text.strip():
                            rating_text = rating_element.text.strip()
                            # 檢查是否是數字格式的評分
                            if re.match(r'\d+\.\d+', rating_text):
                                # 嘗試獲取評論數量
                                try:
                                    review_count_element = self.driver.find_element(By.CSS_SELECTOR, ".F7nice a[href*='reviews']")
                                    review_count = review_count_element.text.strip()
                                    details['rating'] = f"{rating_text}({review_count})"
                                except:
                                    details['rating'] = rating_text
                                
                                self.debug_print(f"✅ 成功獲取評分: {details['rating']}", "SUCCESS")
                                break
                    except:
                        continue
                        
                if details['rating'] == '評分未提供':
                    self.debug_print("❌ 無法獲取評分", "WARNING")
            except:
                self.debug_print("評分擷取過程出錯", "ERROR")
            
        except Exception as e:
            self.debug_print(f"詳細資訊擷取時出錯: {e}", "ERROR")
        
        return details
    
    def extract_business_hours_detailed(self):
        """詳細擷取營業時間，包括需要點開的部分 - 改進版"""
        try:
            self.debug_print("尋找營業時間區塊...", "EXTRACT")
            
            # 先等待頁面穩定
            time.sleep(2)
            
            # 嘗試多種營業時間的展開按鈕選擇器
            expand_buttons = [
                "button[data-value='Open hours']",
                ".t39EBf button",
                ".OqCZI button", 
                "[aria-label*='營業時間'] button",
                "[aria-label*='營業'] button",
                "button[aria-label*='hours']",
                ".fontBodyMedium[role='button']",
                "[role='button'][aria-expanded='false']"
            ]
            
            expanded = False
            for i, selector in enumerate(expand_buttons):
                try:
                    self.debug_print(f"嘗試營業時間展開按鈕 {i+1}: {selector}", "EXTRACT")
                    buttons = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    
                    for button in buttons:
                        try:
                            if button and button.is_displayed() and button.is_enabled():
                                button_text = button.text.strip()
                                if any(keyword in button_text for keyword in ['營業', '時間', 'hours', '10:', '9:', '8:']):
                                    self.debug_print(f"找到營業時間展開按鈕，文字: {button_text}", "CLICK")
                                    
                                    # 使用 ActionChains 來確保點擊成功
                                    actions = ActionChains(self.driver)
                                    actions.move_to_element(button).click().perform()
                                    
                                    self.debug_print("已點擊營業時間展開按鈕", "SUCCESS")
                                    time.sleep(3)  # 等待展開動畫完成
                                    expanded = True
                                    break
                        except Exception as e:
                            continue
                    
                    if expanded:
                        break
                        
                except Exception as e:
                    continue
            
            if expanded:
                self.debug_print("營業時間已展開，等待內容載入...", "WAIT")
                time.sleep(2)
            else:
                self.debug_print("未找到營業時間展開按鈕，嘗試直接抓取", "INFO")
            
            # 更新的營業時間選擇器 - 基於截圖中看到的結構
            hours_selectors = [
                # 主要的營業時間容器
                "[data-value='Open hours'] .fontBodyMedium",
                ".t39EBf .fontBodyMedium",
                ".OqCZI .fontBodyMedium",
                
                # 展開後的營業時間（從截圖看到的結構）
                ".eK4R0e .fontBodyMedium",
                ".rogA2c .fontBodyMedium", 
                
                # 通用的營業時間選擇器
                "div[data-item-id*='oh'] .fontBodyMedium",
                "[role='rowgroup'] .fontBodyMedium",
                
                # 更廣泛的搜尋
                ".fontBodyMedium:contains('10:')",
                ".fontBodyMedium:contains('9:')",
                ".fontBodyMedium:contains('星期')",
                ".fontBodyMedium:contains('週')",
                ".fontBodyMedium:contains('Monday')",
                ".fontBodyMedium:contains('休')",
                
                # 所有可能包含時間的元素
                "[class*='fontBody']:contains(':')",
                "div:contains('10:00'):not(:contains('電話')):not(:contains('地址'))"
            ]
            
            # 嘗試獲取營業時間內容
            for i, selector in enumerate(hours_selectors):
                try:
                    self.debug_print(f"嘗試營業時間選擇器 {i+1}: {selector}", "EXTRACT")
                    
                    # 對於包含 :contains 的選擇器，改用 XPath
                    if ':contains(' in selector:
                        xpath_selector = selector.replace(':contains(', '[contains(text(), ').replace(')', ')]')
                        hours_elements = self.driver.find_elements(By.XPATH, f"//*{xpath_selector}")
                    else:
                        hours_elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    
                    if hours_elements:
                        hours_text = []
                        self.debug_print(f"找到 {len(hours_elements)} 個營業時間元素", "INFO")
                        
                        for j, element in enumerate(hours_elements):
                            try:
                                text = element.text.strip()
                                if text and len(text) > 2:
                                    # 檢查是否包含時間相關的關鍵字
                                    time_keywords = ['10:', '9:', '8:', '11:', '12:', '13:', '14:', '15:', '16:', '17:', '18:', '19:', '20:', '21:', '星期', '週', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday', '休']
                                    
                                    if any(keyword in text for keyword in time_keywords) and '營業時間' not in text:
                                        hours_text.append(text)
                                        self.debug_print(f"  營業時間 {j+1}: {text}", "INFO")
                                        
                                        # 限制最多取前10個，避免抓到太多無關內容
                                        if len(hours_text) >= 10:
                                            break
                            except Exception as e:
                                continue
                        
                        if hours_text:
                            # 去除重複的時間資訊
                            unique_hours = []
                            seen_hours = set()
                            
                            for hour in hours_text:
                                hour_clean = hour.strip().lower()
                                if hour_clean not in seen_hours and len(hour_clean) > 2:
                                    unique_hours.append(hour)
                                    seen_hours.add(hour_clean)
                            
                            if unique_hours:
                                result = '; '.join(unique_hours)
                                self.debug_print(f"✅ 成功獲取營業時間: {result[:80]}...", "SUCCESS")
                                return result
                                
                except Exception as e:
                    self.debug_print(f"選擇器 {i+1} 執行錯誤: {e}", "WARNING")
                    continue
            
            # 最後嘗試：搜尋頁面中所有包含時間格式的文字
            try:
                self.debug_print("最後嘗試：搜尋所有時間格式文字", "EXTRACT")
                all_elements = self.driver.find_elements(By.XPATH, "//*[contains(text(), ':') and (contains(text(), '10') or contains(text(), '9') or contains(text(), '星期') or contains(text(), '週'))]")
                
                time_texts = []
                for element in all_elements[:15]:  # 限制數量
                    try:
                        text = element.text.strip()
                        if text and len(text) < 50:  # 避免抓到太長的文字
                            time_keywords = ['10:', '9:', '8:', '11:', '12:', '13:', '14:', '15:', '16:', '17:', '18:', '19:', '20:', '21:', '星期', '週']
                            if any(keyword in text for keyword in time_keywords):
                                time_texts.append(text)
                                self.debug_print(f"  發現時間文字: {text}", "INFO")
                    except:
                        continue
                
                if time_texts:
                    result = '; '.join(time_texts[:7])  # 取前7個（一週的時間）
                    self.debug_print(f"✅ 最終成功獲取營業時間: {result[:80]}...", "SUCCESS")
                    return result
                    
            except Exception as e:
                self.debug_print(f"最終嘗試失敗: {e}", "ERROR")
            
            self.debug_print("❌ 無法獲取營業時間", "WARNING")
            return '營業時間未提供'
            
        except Exception as e:
            self.debug_print(f"營業時間擷取過程出錯: {e}", "ERROR")
            return '營業時間獲取失敗'
    
    def scroll_and_extract_with_details(self):
        """滾動並擷取店家詳細資訊 - 改進版滾動策略"""
        try:
            self.debug_print(f"開始擷取 {self.current_location} 周圍 {self.search_radius_km}km 內的店家...", "INFO")
            
            container = self.find_scrollable_container()
            if not container:
                self.debug_print("找不到滾動容器", "ERROR")
                return False
            
            last_count = 0
            no_change_count = 0
            max_no_change = 3  # 詳細模式：3次無變化停止
            max_scrolls = 10   # 詳細模式：最多10次滾動
            scroll_count = 0
            
            initial_count = len(self.current_location_shops)
            
            # 先等待頁面完全載入
            self.debug_print("等待頁面完全載入...", "WAIT")
            time.sleep(3)
            
            while scroll_count < max_scrolls and no_change_count < max_no_change:
                scroll_count += 1
                
                self.debug_print(f"第 {scroll_count} 次滾動 - 擷取當前店家...", "INFO")
                
                # 在滾動前先擷取一次
                current_shops = self.extract_current_shops_with_details()
                current_count = len(self.current_location_shops)
                
                self.debug_print(f"滾動前：當前位置共 {current_count} 家店", "INFO")
                
                if current_count == last_count:
                    no_change_count += 1
                    self.debug_print(f"連續 {no_change_count} 次沒有新增店家", "WARNING")
                else:
                    no_change_count = 0
                    last_count = current_count
                    self.debug_print(f"本輪新增了 {len(current_shops)} 家店家", "SUCCESS")
                
                # 如果連續無新增店家就停止
                if no_change_count >= max_no_change:
                    self.debug_print("連續多次無新增店家，停止滾動", "INFO")
                    break
                
                # 詳細模式：如果新增店家數量很少，提早停止
                if len(current_shops) < 1 and scroll_count > 3:
                    self.debug_print("新增店家數量很少，提早停止滾動", "INFO")
                    break
                
                if scroll_count < max_scrolls:
                    self.debug_print("執行滾動策略...", "INFO")
                    try:
                        # 詳細模式：較大的滾動距離，減少滾動次數
                        scroll_amount = 600 + (scroll_count * 100)
                        self.debug_print(f"滾動距離: {scroll_amount}px", "INFO")
                        self.driver.execute_script(f"arguments[0].scrollTop += {scroll_amount}", container)
                        time.sleep(2)
                        
                        # 窗口滾動
                        self.driver.execute_script(f"window.scrollBy(0, {scroll_amount//2});")
                        time.sleep(1)
                        
                    except Exception as e:
                        self.debug_print(f"滾動執行錯誤: {e}", "ERROR")
                
                # 等待新內容載入
                wait_time = 3 + (scroll_count * 0.5)  # 詳細模式需要更多等待時間
                self.debug_print(f"等待 {wait_time:.1f} 秒讓內容載入...", "WAIT")
                time.sleep(wait_time)
                
                # 滾動後再次擷取
                post_scroll_shops = self.extract_current_shops_with_details()
                if post_scroll_shops:
                    self.debug_print(f"滾動後又發現 {len(post_scroll_shops)} 家新店家", "SUCCESS")
                
                # 🎯 滾動後檢查是否達到目標
                if len(self.shops_data) >= self.target_shops:
                    self.debug_print(f"🎯 達到{self.target_shops}家目標，停止滾動擷取", "SUCCESS")
                    break
            
            final_count = len(self.current_location_shops)
            added_this_location = final_count - initial_count
            self.debug_print(f"{self.current_location} 搜尋完成！新增 {added_this_location} 家店", "SUCCESS")
            self.debug_print(f"總滾動次數: {scroll_count}，最終無變化次數: {no_change_count}", "INFO")
            
            # 🎯 返回是否達到目標的狀態
            return len(self.shops_data) < self.target_shops
            
        except Exception as e:
            self.debug_print(f"滾動擷取失敗: {e}", "ERROR")
            return False
    
    def extract_current_shops_with_details(self):
        """擷取當前可見的店家並獲取詳細資訊 - 改進版"""
        try:
            self.debug_print("尋找當前頁面的店家連結...", "EXTRACT")
            
            # 使用多種CSS選擇器確保不遺漏店家
            shop_selectors = [
                "a[href*='/maps/place/']",
                "a[data-value='Directions']",
                "div[role='article'] a",
                "div[jsaction*='click'] a[href*='place']",
                "[data-feature-id] a",
                "div[aria-label*='結果'] a[href*='place']"
            ]
            
            all_shop_links = []
            for selector in shop_selectors:
                try:
                    links = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for link in links:
                        href = link.get_attribute('href')
                        if href and '/maps/place/' in href and link not in all_shop_links:
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
            self.debug_print(f"找到 {len(shop_links)} 個唯一店家連結", "INFO")
            
            new_shops = []
            processed_count = 0
            
            # 詳細模式：處理前6家店家，平衡品質和效率
            max_process = min(6, len(shop_links))
            self.debug_print(f"準備處理 {max_process} 家店家", "INFO")
            
            for i, link in enumerate(shop_links[:max_process]):
                try:
                    self.debug_print(f"處理店家 {i+1}/{max_process}", "INFO")
                    
                    # 改進可見性檢查
                    try:
                        # 滾動到元素位置確保可見
                        self.driver.execute_script("arguments[0].scrollIntoView(false);", link)
                        time.sleep(0.5)
                        
                        if not link.is_displayed():
                            self.debug_print(f"店家 {i+1} 不可見，但繼續處理", "WARNING")
                    except:
                        pass
                    
                    # 先快速檢查是否重複
                    try:
                        pre_name = link.get_attribute('aria-label')
                        if not pre_name:
                            pre_name = link.text
                        if not pre_name:
                            # 嘗試從父元素獲取名稱
                            try:
                                parent = link.find_element(By.XPATH, "..")
                                pre_name = parent.get_attribute('aria-label') or parent.text
                            except:
                                pass
                        
                        if pre_name and pre_name.strip():
                            temp_shop = {'name': pre_name.strip(), 'google_maps_url': link.get_attribute('href'), 'search_location': self.current_location}
                            if not self.is_new_shop(temp_shop):
                                self.debug_print(f"店家 {pre_name} 已存在，跳過處理", "WARNING")
                                continue
                    except Exception as e:
                        self.debug_print(f"預檢查店家名稱時出錯: {e}", "WARNING")
                        pass
                        
                    shop_info = self.extract_shop_info_detailed(link)
                    if not shop_info:
                        self.debug_print(f"店家 {i+1} 資訊擷取失敗", "WARNING")
                        continue
                    
                    if self.is_new_shop(shop_info):
                        # 同時加入兩個列表
                        self.shops_data.append(shop_info)
                        self.current_location_shops.append(shop_info)
                        new_shops.append(shop_info)
                        self.debug_print(f"✅ 新增店家: {shop_info['name']} (當前位置第 {len(self.current_location_shops)} 家)", "SUCCESS")
                        self.debug_print(f"    📞 電話: {shop_info.get('phone', '未獲取')}", "INFO")
                        self.debug_print(f"    📍 地址: {shop_info.get('address', '未獲取')[:30]}...", "INFO")
                        self.debug_print(f"    🕒 營業時間: {shop_info.get('hours', '未獲取')[:30]}...", "INFO")
                        self.debug_print(f"    ⭐ 評分: {shop_info.get('rating', '未獲取')}", "INFO")
                        self.debug_print(f"📊 總店家數進度: {len(self.shops_data)}/600", "INFO")
                        processed_count += 1
                        
                        # 🎯 每新增一家店家就檢查是否達到目標
                        if len(self.shops_data) >= self.target_shops:
                            self.debug_print(f"🎯 達到{self.target_shops}家目標！總共收集 {len(self.shops_data)} 家店家", "SUCCESS")
                            self.debug_print("🛑 立即停止擷取，準備輸出結果...", "INFO")
                            break
                    else:
                        self.debug_print(f"店家 {shop_info.get('name', '未知')} 重複，跳過", "WARNING")
                    
                    # 詳細模式：如果已經處理了4家新店家，就停止當前輪次
                    if processed_count >= 4:
                        self.debug_print("已處理足夠的新店家，停止當前輪次", "INFO")
                        break
                    
                    # 🎯 檢查是否達到目標（在處理店家後）
                    if len(self.shops_data) >= self.target_shops:
                        self.debug_print(f"🎯 達到{self.target_shops}家目標，停止處理更多店家", "SUCCESS")
                        break
                        
                except Exception as e:
                    self.debug_print(f"處理店家 {i+1} 時出錯: {e}", "ERROR")
                    continue
            
            if new_shops:
                self.debug_print(f"本次新增 {len(new_shops)} 家店家", "SUCCESS")
            else:
                self.debug_print("本次沒有新增店家", "WARNING")
            
            # 🎯 最終檢查是否達到目標
            if len(self.shops_data) >= self.target_shops:
                self.debug_print(f"🎯 已達到{self.target_shops}家目標，停止本次擷取", "SUCCESS")
                
            return new_shops
            
        except Exception as e:
            self.debug_print(f"擷取店家錯誤: {e}", "ERROR")
            return []
    
    def find_scrollable_container(self):
        """找到可滾動的容器"""
        try:
            self.debug_print("尋找可滾動的容器...", "EXTRACT")
            result_selectors = [
                "div[role='main']",
                "div[aria-label*='結果']",
                "[role='main'] > div",
                "body"
            ]
            
            for i, selector in enumerate(result_selectors):
                try:
                    self.debug_print(f"嘗試滾動容器選擇器 {i+1}: {selector}", "EXTRACT")
                    element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if element and element.is_displayed():
                        self.debug_print(f"✅ 找到滾動容器: {selector}", "SUCCESS")
                        return element
                except:
                    continue
            
            self.debug_print("使用 body 作為滾動容器", "WARNING")
            return self.driver.find_element(By.TAG_NAME, "body")
            
        except Exception as e:
            self.debug_print(f"找不到滾動容器: {e}", "ERROR")
            return None
    
    def is_new_shop(self, shop_info):
        """檢查是否為新店家 - 改進版重複檢查（優先檢查當前位置）"""
        if not shop_info or not shop_info.get('name'):
            return False
            
        shop_name = shop_info['name'].strip().lower()
        shop_url = shop_info.get('google_maps_url', '').strip()
        
        # 首先檢查當前位置的店家（避免同位置重複）
        for existing_shop in self.current_location_shops:
            existing_name = existing_shop.get('name', '').strip().lower()
            existing_url = existing_shop.get('google_maps_url', '').strip()
            
            # 精確名稱匹配
            if existing_name == shop_name:
                self.debug_print(f"發現重複店家(當前位置-名稱): {shop_info['name']}", "WARNING")
                return False
            
            # URL匹配（如果兩個都有URL）
            if shop_url and existing_url and shop_url == existing_url:
                self.debug_print(f"發現重複店家(當前位置-URL): {shop_info['name']}", "WARNING")
                return False
        
        # 然後檢查全域店家列表（允許不同位置的相同店家，但檢查URL重複）
        for existing_shop in self.shops_data:
            existing_name = existing_shop.get('name', '').strip().lower()
            existing_url = existing_shop.get('google_maps_url', '').strip()
            existing_location = existing_shop.get('search_location', '')
            
            # 如果是相同位置，跳過（已在上面檢查過）
            if existing_location == self.current_location:
                continue
            
            # 對於不同位置，只檢查完全相同的URL
            if shop_url and existing_url and shop_url == existing_url:
                self.debug_print(f"發現相同URL的店家: {shop_name} (位置: {self.current_location} vs {existing_location})", "WARNING")
                return False
                
            # 檢查名稱相似度（移除空格、特殊字符後比較）- 用於全域檢查
            clean_name = ''.join(c for c in shop_name if c.isalnum())
            clean_existing = ''.join(c for c in existing_name if c.isalnum())
            
            if clean_name and clean_existing and clean_name == clean_existing and len(clean_name) > 3:
                self.debug_print(f"發現相似店家: {shop_info['name']} vs {existing_shop['name']} (位置: {self.current_location} vs {existing_location})", "WARNING")
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
                filename = f"高雄美甲美睫店家_詳細版_{timestamp}"
            
            self.debug_print("開始處理資料並儲存...", "SAVE")
            
            # 去除重複
            unique_shops = []
            seen = set()
            
            self.debug_print("正在去除重複店家...", "INFO")
            for shop in self.shops_data:
                key = (shop['name'], shop.get('google_maps_url', ''))
                if key not in seen:
                    seen.add(key)
                    unique_shops.append(shop)
                else:
                    self.debug_print(f"移除重複店家: {shop['name']}", "WARNING")
            
            # 儲存到 Excel
            excel_filename = f"{filename}.xlsx"
            self.debug_print(f"正在儲存 {len(unique_shops)} 筆資料到 {excel_filename}...", "SAVE")
            df = pd.DataFrame(unique_shops)
            df.to_excel(excel_filename, index=False, engine='openpyxl')
            self.debug_print(f"✅ 成功儲存 Excel 檔案: {excel_filename}", "SUCCESS")
            
            # 同時儲存 CSV 備份
            if save_csv:
                csv_filename = f"{filename}.csv"
                df.to_csv(csv_filename, index=False, encoding='utf-8-sig')
                self.debug_print(f"✅ 同時儲存 CSV 備份: {csv_filename}", "SUCCESS")
            
            self.debug_print(f"成功儲存 {len(unique_shops)} 筆店家詳細資料", "SUCCESS")
            
            # 顯示統計資料
            self.debug_print("CSV儲存統計資料:", "INFO")
            self.debug_print(f"   - 總店家數: {len(unique_shops)}", "INFO")
            
            successful_addresses = sum(1 for shop in unique_shops if shop.get('address', '地址未提供') not in ['地址未提供', '地址獲取失敗'])
            self.debug_print(f"   - 成功獲取地址的店家: {successful_addresses}", "INFO")
            
            successful_phones = sum(1 for shop in unique_shops if shop.get('phone', '電話未提供') not in ['電話未提供', '電話獲取失敗'])
            self.debug_print(f"   - 成功獲取電話的店家: {successful_phones}", "INFO")
            
            successful_hours = sum(1 for shop in unique_shops if shop.get('hours', '營業時間未提供') not in ['營業時間未提供', '營業時間獲取失敗'])
            self.debug_print(f"   - 成功獲取營業時間的店家: {successful_hours}", "INFO")
            
            successful_ratings = sum(1 for shop in unique_shops if shop.get('rating', '評分未提供') not in ['評分未提供', '評分獲取失敗'])
            self.debug_print(f"   - 成功獲取評分的店家: {successful_ratings}", "INFO")
            
            # 按搜尋地點分組統計
            location_stats = {}
            for shop in unique_shops:
                location = shop.get('search_location', '未知地點')
                location_stats[location] = location_stats.get(location, 0) + 1
            
            self.debug_print("各地點店家數量:", "INFO")
            for location, count in location_stats.items():
                self.debug_print(f"   - {location}: {count} 家", "INFO")
            
            self.debug_print(f"檔案已準備完成", "SUCCESS")
            
            return True
            
        except Exception as e:
            self.debug_print(f"儲存失敗: {e}", "ERROR")
            return False
    
    def get_comprehensive_search_locations(self):
        """獲取超縝密的搜索地點列表 - 180%覆蓋率涵蓋高雄市所有區域"""
        
        # 行政區中心點（主要商業區和人口聚集地）
        admin_centers = [
            # 市中心核心區域
            "高雄火車站",
            "高雄捷運美麗島站", 
            "五福商圈",
            "大立百貨",
            "漢來大飯店",
            "高雄市政府",
            "統一夢時代購物中心",
            "中山大學",
            "高雄醫學大學",
            "高雄師範大學",
            "高雄第一科技大學",
            "文藻外語大學",
            
            # 鳳山區重點
            "鳳山火車站",
            "鳳山區公所",
            "鳳山西站",
            "大東文化藝術中心",
            "鳳山商圈",
            "五甲",
            "鳳西國中",
            "鳳山高中",
            "正修科技大學",
            "澄清湖",
            
            # 左營楠梓區重點
            "高雄左營站",
            "新光三越左營店",
            "漢神巨蛋",
            "蓮潭會館",
            "楠梓火車站",
            "楠梓區公所",
            "高雄大學",
            "海科大",
            "右昌",
            "後勁",
            "援中港",
            "德民路",
            
            # 三民區重點  
            "三民區公所",
            "建工路商圈",
            "民族路商圈",
            "覺民路商圈",
            "建國路商圈",
            "九如路",
            "十全路",
            "大昌路",
            "陽明路",
            "民族國小",
            
            # 苓雅區重點
            "苓雅區公所", 
            "文化中心",
            "六合夜市",
            "新興區公所",
            "五權國小",
            "復華中學",
            "成功路",
            "光華路",
            "青年路",
            
            # 前鎮小港區重點
            "前鎮區公所",
            "草衙道",
            "小港機場",
            "小港區公所",
            "小港醫院",
            "前鎮高中",
            "獅甲",
            "瑞豐",
            "勞工公園",
            "鎮中路",
            
            # 鼓山區重點
            "鼓山區公所",
            "西子灣",
            "駁二藝術特區",
            "鼓山輪渡站",
            "美術館",
            "內惟",
            "龍華國小",
            "明華國中",
            
            # 前金區重點
            "前金區公所",
            "中央公園站",
            "城市光廊",
            "前金國小",
            "建國三路",
            
            # 仁武大社區重點
            "仁武區公所",
            "仁武高中", 
            "大社區公所",
            "義大世界",
            "仁武國小",
            "八卦國小",
            
            # 岡山區重點
            "岡山火車站",
            "岡山區公所",
            "岡山高中",
            "岡山國小",
            "岡山農會",
            "中山公園",
            
            # 路竹區重點
            "路竹火車站",
            "路竹區公所",
            "路竹高中",
            "路竹國小",
            
            # 湖內區重點
            "湖內區公所",
            "湖內國小",
            "湖內高中",
            
            # 茄萣區重點
            "茄萣區公所",
            "茄萣國小",
            "興達港",
            
            # 永安區重點
            "永安區公所",
            "永安國小",
            
            # 彌陀區重點
            "彌陀區公所",
            "彌陀國小",
            
            # 梓官區重點
            "梓官區公所",
            "梓官國小",
            
            # 橋頭區重點
            "橋頭火車站",
            "橋頭區公所",
            "橋頭糖廠",
            "橋頭科學園區",
            "橋頭國小",
            
            # 燕巢區重點
            "燕巢區公所",
            "燕巢國小",
            "燕巢高中",
            
            # 田寮區重點
            "田寮區公所",
            "田寮國小",
            
            # 阿蓮區重點
            "阿蓮區公所",
            "阿蓮國小",
            
            # 大樹區重點
            "大樹區公所",
            "大樹國小",
            "佛光山",
            
            # 大寮區重點
            "大寮區公所",
            "大寮國小",
            "大寮高中",
            
            # 林園區重點
            "林園區公所",
            "林園國小",
            "林園高中",
            "林園工業區",
            
            # 鳥松區重點
            "鳥松區公所",
            "鳥松國小",
            "鳥松高中",
            "澄清湖",
            
            # 大社區重點
            "大社觀音山",
            "大社國小",
            "大社高中",
            
            # 旗山區重點
            "旗山火車站",
            "旗山區公所",
            "旗山國小",
            "旗山高中",
            "旗山老街",
            
            # 美濃區重點
            "美濃區公所",
            "美濃國小",
            "美濃高中",
            "美濃客家文物館",
            
            # 六龜區重點
            "六龜區公所",
            "六龜國小",
            "六龜高中",
            
            # 甲仙區重點
            "甲仙區公所",
            "甲仙國小",
            
            # 杉林區重點
            "杉林區公所",
            "杉林國小",
            
            # 內門區重點
            "內門區公所",
            "內門國小",
            
            # 茂林區重點
            "茂林區公所",
            "茂林國小",
            
            # 桃源區重點
            "桃源區公所",
            "桃源國小",
            
            # 那瑪夏區重點
            "那瑪夏區公所",
            "那瑪夏國小",
        ]
        
        # 重要商圈和生活機能區域
        commercial_areas = [
            # 夜市和傳統市場
            "瑞豐夜市",
            "光華夜市",
            "南華路夜市",
            "興中夜市",
            "鳳山中華街夜市",
            "青年夜市",
            "凱旋夜市",
            "旗津夜市",
            "旗山夜市",
            "美濃夜市",
            "岡山夜市",
            "路竹夜市",
            "鳳山第一公有市場",
            "三民街市場",
            "前鎮第一公有市場",
            "小港市場",
            "楠梓市場",
            "左營第一公有市場",
            "苓雅市場",
            "新興第一公有市場",
            
            # 購物中心周邊
            "大遠百",
            "太平洋SOGO",
            "新崛江商圈",
            "巨蛋商圈",
            "夢時代商圈",
            "大立精品",
            "漢神百貨",
            "新光三越三多店",
            "大統百貨",
            "環球購物中心",
            "家樂福鼎山店",
            "家樂福楠梓店",
            "愛河之心",
            "中友百貨",
            "IKEA高雄店",
            "好市多高雄店",
            "COSTCO高雄大順店",
            
            # 醫院周邊（人流密集）
            "高雄榮總",
            "高雄醫學大學附設醫院",
            "長庚紀念醫院",
            "義大醫院",
            "阮綜合醫院",
            "高雄市立聯合醫院",
            "高雄市立大同醫院",
            "高雄市立小港醫院",
            "聖功醫院",
            "國軍高雄總醫院",
            "天主教聖功醫院",
            "建佑醫院",
            "安泰醫院",
            "國軍左營總醫院",
            "義大大昌醫院",
            "七賢脊椎外科醫院",
            "恆春基督教醫院",
            
            # 學校周邊
            "高雄師範大學",
            "中山大學",
            "高雄科技大學",
            "文藻外語大學",
            "正修科技大學",
            "樹德科技大學",
            "和春技術學院",
            "輔英科技大學",
            "國立高雄餐旅大學",
            "實踐大學高雄校區",
            "高苑科技大學",
            "東方設計大學",
            "高雄應用科技大學",
            "高雄第一科技大學",
            "高雄海洋科技大學",
            
            # 觀光景點
            "西子灣風景區",
            "旗津海岸公園",
            "愛河",
            "蓮池潭",
            "佛光山",
            "義大遊樂世界",
            "壽山動物園",
            "金獅湖",
            "澄清湖風景區",
            "田寮月世界",
            "茂林國家風景區",
            "美濃客家文物館",
            "六龜溫泉",
            "打狗英國領事館",
            "高雄港",
            "85大樓",
            
            # 宗教場所
            "佛光山寺",
            "慈濟靜思堂",
            "天主教玫瑰堂",
            "高雄文武聖殿",
            "代天宮",
            "三鳳宮",
            "左營啟明堂",
            "鳳山龍山寺",
        ]
        
        # 重要路段和交通節點
        transport_roads = [
            # 主要幹道重要路段
            "中山路與七賢路口",
            "建國路與民族路口", 
            "博愛路與九如路口",
            "自由路與中正路口",
            "中華路與五福路口",
            "澄清路與鳳山火車站",
            "大中路與正義路口",
            "民族路與建工路口",
            "中正路與成功路口",
            "光華路與三多路口",
            "四維路與中山路口",
            "青年路與民生路口",
            "復興路與中華路口",
            "南京路與凱旋路口",
            "五甲路與鳳甲路口",
            "中庄路與建國路口",
            "德民路與後昌路口",
            "高楠公路與楠梓路口",
            "旗楠路與岡山路口",
            "中山路與美濃路口",
            "光復路與旗山路口",
            "沿海路與林園路口",
            
            # 捷運站周邊
            "高雄車站捷運站",
            "後驛站",
            "三多商圈站",
            "中央公園站",
            "巨蛋站",
            "生態園區站",
            "左營高鐵站",
            "鳳山西站",
            "大東站",
            "鳳山站",
            "美麗島站",
            "中央公園站",
            "橘線技擊館站",
            "紅線小港站",
            "橘線西子灣站",
            "紅線後驛站",
            "橘線市議會站",
            "紅線南岡山站",
            "橘線大寮站",
            "紅線草衙站",
            "橘線鳳山國中站",
            
            # 火車站周邊
            "高雄火車站前站",
            "高雄火車站後站",
            "鳳山火車站前站",
            "鳳山火車站後站",
            "左營火車站",
            "楠梓火車站",
            "岡山火車站",
            "路竹火車站",
            "湖內火車站",
            "茄萣火車站",
            "永安火車站",
            "橋頭火車站",
            "旗山車站",
            
            # 重要公車站
            "高雄客運總站",
            "鳳山轉運站",
            "左營轉運站",
            "小港轉運站",
            "建國轉運站",
            
            # 高速公路交流道
            "高雄交流道",
            "鼎金交流道",
            "左營交流道",
            "楠梓交流道",
            "岡山交流道",
            "路竹交流道",
            "湖內交流道",
            "茄萣交流道",
            "大寮交流道",
            "林園交流道",
        ]
        
        # 新興發展區域
        new_developments = [
            # 亞洲新灣區
            "高雄展覽館",
            "亞灣軟體園區",
            "高雄流行音樂中心",
            "高雄圖書館總館",
            "高雄港埠旅運中心",
            "輕軌凱旋中華站",
            "輕軌前鎮之星站",
            "輕軌凱旋瑞田站",
            "輕軌軟體園區站",
            "輕軌高雄展覽館站",
            
            # 橋頭新市鎮
            "橋頭火車站",
            "橋頭糖廠",
            "橋頭科學園區",
            "橋頭新市鎮特區",
            "橋科環球購物中心",
            
            # 路竹科學園區
            "路竹科學園區",
            "路竹高科技產業園區",
            "南科高雄園區",
            
            # 高雄軟體科技園區
            "高雄軟體科技園區",
            "中鋼集團總部大樓",
            "統一夢時代購物中心",
            
            # 其他工業園區
            "林園工業區",
            "大社工業區",
            "仁武工業區",
            "永安工業區",
            "臨海工業區",
            "大發工業區",
            "鳳山工業區",
            
            # 大學城區域
            "高雄大學特區",
            "義守大學城",
            "文藻外語大學城",
            "正修科大特區",
            
            # 重劃區
            "鳳山新城",
            "左營新城",
            "楠梓新市鎮",
            "小港森林公園特區",
            "前鎮河堤特區",
            "苓雅寶業里",
            "三民陽明商圈",
            
            # 新興商業區
            "高雄巨蛋商圈",
            "夢時代商圈",
            "義享天地",
            "草衙道購物中心",
            "IKEA高雄店商圈",
            "好市多高雄商圈",
            
            # 觀光發展區
            "旗津風車公园",
            "西子灣隧道商圈",
            "愛河之心商圈",
            "蓮池潭觀光區",
            "澄清湖特區",
            "佛光山觀光區",
            "美濃客家文化園區",
            "六龜溫泉區",
            "茂林紫蝶幽谷",
        ]
        
        # 合併所有搜索點
        all_locations = admin_centers + commercial_areas + transport_roads + new_developments
        
        # 180%覆蓋率：為每個位置添加擴展搜索
        extended_locations = []
        for location in all_locations:
            extended_locations.append(location)
            extended_locations.append(f"{location} 附近")
            extended_locations.append(f"{location} 周邊")
            extended_locations.append(f"{location} 500米內")
            if self.coverage_multiplier >= 1.8:
                extended_locations.append(f"{location} 1公里內")
                extended_locations.append(f"{location} 商圈")
        
        # 去重
        unique_extended = list(set(extended_locations))
        
        self.debug_print(f"🎯 180%超高覆蓋率模式：共準備 {len(unique_extended)} 個搜索點", "INFO")
        self.debug_print(f"   📍 行政區中心: {len(admin_centers)} 個", "INFO")
        self.debug_print(f"   🛒 商圈生活區: {len(commercial_areas)} 個", "INFO") 
        self.debug_print(f"   🚇 交通路段: {len(transport_roads)} 個", "INFO")
        self.debug_print(f"   🏗️ 新興發展區: {len(new_developments)} 個", "INFO")
        self.debug_print(f"   🔄 擴展覆蓋率: {self.coverage_multiplier}x", "INFO")
        self.debug_print(f"   🎯 最終搜索點: {len(unique_extended)} 個", "INFO")
        
        return unique_extended

    def run_detailed_scraping(self):
        """執行詳細版店家資訊擷取 - 改進版（整合快速版優化邏輯）"""
        start_time = time.time()
        
        try:
            self.debug_print("開始執行 Google 地圖店家詳細資訊擷取程式 【改進版】", "INFO")
            self.debug_print("✨ 整合快速版的優化邏輯 + 詳細資訊擷取", "INFO")
            self.debug_print(f"搜尋半徑: {self.search_radius_km} 公里 (精確模式)", "INFO")
            self.debug_print("將獲取：店家名稱、地址、電話、營業時間、評分、Google Maps連結", "INFO")
            self.debug_print("🔧 改進特色：位置分離重複檢查、多種CSS選擇器、重試機制", "INFO")
            print("=" * 80)
            
            if not self.setup_driver():
                return False
            
            if not self.open_google_maps():
                return False
            
            # 縝密模式：獲取所有搜索地點
            locations = self.get_comprehensive_search_locations()
            
            # 縝密模式：美甲美睫相關店家類型
            shop_types = ["美甲", "美睫", "指甲彩繪", "凝膠指甲", "光療指甲", "手足保養", "耳燭","熱蠟"]
            
            self.debug_print("【縝密搜索模式】設定：", "INFO")
            self.debug_print(f"📍 搜尋地點: {len(locations)} 個精確地點", "INFO")
            self.debug_print(f"🏪 店家類型: {len(shop_types)} 種類型", "INFO")
            self.debug_print(f"🎯 搜索半徑: {self.search_radius_km}km (更精確)", "INFO")
            self.debug_print(f"📜 每輪處理: 4家店家 (品質優先)", "INFO")
            self.debug_print(f"🔍 預估總搜尋次數: {len(locations) * len(shop_types)} 次", "INFO")
            print("-" * 70)
            
            total_searches = len(locations) * len(shop_types)
            current_search = 0
            
            # 對每個定位點進行搜尋
            for i, location in enumerate(locations, 1):
                self.debug_print(f"[{i}/{len(locations)}] 定位點: {location}", "INFO")
                print("=" * 50)
                
                if not self.set_location(location):
                    self.debug_print(f"定位到 '{location}' 失敗，跳過", "ERROR")
                    continue
                
                # 對每種店家類型進行搜尋
                for j, shop_type in enumerate(shop_types, 1):
                    current_search += 1
                    self.debug_print(f"[{j}/{len(shop_types)}] 在 {location} 周圍 {self.search_radius_km}km 內搜尋: {shop_type}", "INFO")
                    self.debug_print(f"進度: {current_search}/{total_searches} ({(current_search/total_searches)*100:.1f}%)", "INFO")
                    
                    # 🎯 檢查店家數量是否超過600家
                    if len(self.shops_data) >= 600:
                        self.debug_print(f"🎯 達到目標！已收集 {len(self.shops_data)} 家店家 (超過600家)", "SUCCESS")
                        self.debug_print("🛑 自動停止搜尋，準備輸出結果...", "INFO")
                        break
                    
                    if not self.search_nearby_shops_with_radius(shop_type):
                        self.debug_print(f"在 {location} 搜尋 '{shop_type}' 失敗，跳過", "ERROR")
                        continue
                    
                    should_continue = self.scroll_and_extract_with_details()
                    if not should_continue:
                        self.debug_print(f"🎯 達到600家目標，停止搜尋", "SUCCESS")
                        break
                    elif should_continue is False:
                        self.debug_print(f"擷取 {location} 的 '{shop_type}' 結果失敗，跳過", "ERROR")
                        continue
                    
                    self.debug_print(f"在 {location} 搜尋 '{shop_type}' 完成", "SUCCESS")
                    self.debug_print(f"📊 目前總店家數: {len(self.shops_data)}/600", "INFO")
                    
                    # 🎯 再次檢查店家數量
                    if len(self.shops_data) >= 600:
                        self.debug_print(f"🎯 達到目標！已收集 {len(self.shops_data)} 家店家 (超過600家)", "SUCCESS")
                        self.debug_print("🛑 自動停止搜尋，準備輸出結果...", "INFO")
                        break
                    
                    # 詳細模式：適當的等待時間
                    if current_search < total_searches:
                        wait_time = random.uniform(2, 4)
                        self.debug_print(f"等待 {wait_time:.1f} 秒後繼續...", "WAIT")
                        time.sleep(wait_time)
                
                # 🎯 如果達到目標店家數，跳出外層迴圈
                if len(self.shops_data) >= 600:
                    self.debug_print("🎯 已達到目標店家數量，停止所有搜尋", "SUCCESS")
                    break
                
                location_shops = len(self.current_location_shops)
                total_shops = len(self.shops_data)
                self.debug_print(f"地點 '{location}' 完成，新增 {location_shops} 家店，累計 {total_shops} 家", "SUCCESS")
                
                # 每完成一個地點，顯示進度統計
                progress = (i / len(locations)) * 100
                self.debug_print(f"整體進度: {progress:.1f}% ({i}/{len(locations)} 個地點完成)", "INFO")
                
                # 每完成10個地點，暫存一次結果
                if i % 10 == 0 and self.shops_data:
                    self.debug_print(f"已完成 {i} 個地點，暫存結果...", "SAVE")
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    temp_filename = f"高雄美甲美睫店家_縝密版_暫存_{timestamp}"
                    self.save_to_excel(temp_filename)
                
                if i < len(locations):
                    wait_time = random.uniform(5, 8)
                    self.debug_print(f"等待 {wait_time:.1f} 秒後切換到下一個地點...", "WAIT")
                    time.sleep(wait_time)
            
            print("\n" + "=" * 80)
            
            # 儲存最終結果
            if self.shops_data:
                self.debug_print("正在儲存最終結果...", "SAVE")
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                
                # 根據是否達到目標決定檔名
                if len(self.shops_data) >= self.target_shops:
                    final_filename = f"高雄美甲美睫店家_詳細版_{self.target_shops}家達標_{timestamp}"
                    self.debug_print(f"🎯 成功達到{self.target_shops}家目標！總共收集 {len(self.shops_data)} 家店家", "SUCCESS")
                else:
                    final_filename = f"高雄美甲美睫店家_詳細版_完整_{timestamp}"
                    
                self.save_to_excel(final_filename)
            else:
                self.debug_print("沒有找到任何店家資料", "ERROR")
            
            elapsed_time = time.time() - start_time
            hours = elapsed_time // 3600
            minutes = (elapsed_time % 3600) // 60
            seconds = elapsed_time % 60
            
            if hours > 0:
                time_str = f"{int(hours)} 小時 {int(minutes)} 分 {seconds:.1f} 秒"
            else:
                time_str = f"{int(minutes)} 分 {seconds:.1f} 秒"
                
            self.debug_print(f"總執行時間: {time_str}", "INFO")
            self.debug_print(f"成功完成 {current_search} 次搜尋", "SUCCESS")
            self.debug_print(f"總共發現 {len(self.shops_data)} 家店家", "SUCCESS")
            
            if len(self.shops_data) >= self.target_shops:
                self.debug_print(f"🎯【{self.target_shops}家目標達成！程式自動停止】", "SUCCESS")
            else:
                self.debug_print("【180%覆蓋率詳細搜索完成】", "SUCCESS")
            
            return True
            
        except Exception as e:
            self.debug_print(f"程式執行失敗: {e}", "ERROR")
            return False
        
        finally:
            if self.driver:
                self.debug_print("正在關閉瀏覽器...", "INFO")
                time.sleep(2)
                self.driver.quit()
                self.debug_print("程式執行完成", "SUCCESS")

def main():
    """主程式 - 詳細版（整合快速版改進邏輯 + 600家自動停止）"""
    print("🚀 Google 地圖店家詳細資訊擷取程式 【改進版 + 智能停止】")
    print("✨ 整合快速版的優化邏輯 + 詳細資訊擷取功能")
    print()
    print("🎯 主要改進：")
    print("   - ✅ 按位置分離的重複檢查機制，避免跨位置誤判")
    print("   - ✅ 多種CSS選擇器，確保不遺漏店家")
    print("   - ✅ 重試機制和多種名稱擷取方法")
    print("   - ✅ 改進的滾動策略和進度統計")
    print("   - ✅ 每個位置重置店家列表，確保完整抓取")
    print("   - 🆕 智能停止：達到600家店自動停止並輸出Excel")
    print()
    print("🎯 智能停止功能：")
    print("   - 🛑 程式會持續監控店家數量")
    print("   - 📊 當達到600家店時自動停止搜尋")
    print("   - 📁 自動輸出Excel格式檔案(.xlsx)")
    print("   - 💾 同時保存CSV備份檔案")
    print("   - ⏰ 大幅縮短執行時間（預估2-3小時）")
    print()
    print("📊 詳細功能：")
    print("   - 搜索半徑縮小為 5 公里，更精確")
    print("   - 涵蓋 200+ 個高雄重要地點和商圈")
    print("   - 包含行政區中心、商圈、交通節點、新興發展區")
    print("   - 7 種美甲美睫相關店家類型")
    print("   - 最多搜尋次數：約1400次（智能停止）")
    print()
    print("📍 搜尋地點涵蓋：")
    print("   - 行政區中心：火車站、區公所、主要商業區")
    print("   - 商圈生活區：夜市、購物中心、醫院、學校周邊")
    print("   - 交通節點：重要路口、捷運站周邊")
    print("   - 新興發展區：亞洲新灣區、橋頭新市鎮")
    print()
    print("🏪 店家類型：")
    print("   - 美甲、美睫、指甲彩繪、凝膠指甲、光療指甲、手足保養、耳燭")
    print()
    print("📋 獲取資訊：")
    print("   - 店家名稱、地址、電話、營業時間、評分、Google Maps連結")
    print()
    print("🔧 技術改進：")
    print("   - 🎯 位置分離重複檢查，解決同名店家問題")
    print("   - 📍 每位置處理6家店家，平衡品質和效率")
    print("   - 🔄 每10個地點自動暫存結果")
    print("   - 📊 詳細的進度追蹤和統計")
    print("   - 🔄 多重重試機制，提高資料品質")
    print("   - 🎯 智能停止機制，節省時間")
    print("-" * 70)
    print("⏰ 預估執行時間：約 2-3 小時（智能停止）")
    print("💾 結果會自動儲存為Excel(.xlsx)和CSV檔案")
    print("🔄 程式會自動處理重複店家，確保資料品質")
    print("🎯 目標：收集600家高品質美甲美睫店家資料")
    print()
    
    user_input = input("確定要開始智能版詳細搜索嗎？(y/n): ").strip().lower()
    if user_input != 'y':
        print("程式已取消")
        return
    
    scraper = GoogleMapsDetailedScraper(debug_mode=True)
    scraper.run_detailed_scraping()

if __name__ == "__main__":
    main() 