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
        self.max_shops_per_search = 25  # 增強模式：增加每次處理數量
        self.max_scrolls = 10    # 增強模式：增加滾動次數
        
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
            
            # 基本穩定配置
            firefox_options.add_argument("--headless")  # 強制無頭模式更穩定
            firefox_options.add_argument("--no-sandbox")
            firefox_options.add_argument("--disable-dev-shm-usage")
            firefox_options.add_argument("--disable-gpu")
            firefox_options.add_argument("--disable-extensions")
            
            # 設定窗口大小
            firefox_options.add_argument("--width=1920")
            firefox_options.add_argument("--height=1080")
            
            # 簡化的偏好設置
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
                # 設置用戶代理
                "general.useragent.override": "Mozilla/5.0 (X11; Linux x86_64; rv:91.0) Gecko/20100101 Firefox/91.0"
            }
            
            for key, value in prefs.items():
                firefox_options.set_preference(key, value)
            
            # 設定日誌級別
            firefox_options.log.level = "fatal"
            
            self.debug_print("🦊 啟動Firefox (無頭模式)...", "FIREFOX")
            self.driver = webdriver.Firefox(options=firefox_options)
            self.driver.set_window_size(1920, 1080)
            
            self.debug_print("Firefox高速瀏覽器設定完成", "SUCCESS")
            return True
            
        except Exception as e:
            self.debug_print(f"Firefox瀏覽器設定失敗: {e}", "ERROR")
            # 嘗試最簡配置
            try:
                self.debug_print("🦊 嘗試最簡Firefox配置...", "FIREFOX")
                simple_options = Options()
                simple_options.add_argument("--headless")
                self.driver = webdriver.Firefox(options=simple_options)
                self.debug_print("Firefox簡單配置成功", "SUCCESS")
                return True
            except Exception as e2:
                self.debug_print(f"Firefox簡單配置也失敗: {e2}", "ERROR")
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
    
    def extract_shop_info_detailed(self, link_element):
        """詳細版店家資訊擷取 - 點擊進入詳細頁面獲取完整信息包括電話和地址"""
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
            
            # 點擊進入詳細頁面獲取完整信息
            try:
                self.debug_print(f"🔍 點擊進入 {name} 詳細頁面", "EXTRACT")
                
                # 使用JavaScript點擊，避免元素遮擋問題
                self.driver.execute_script("arguments[0].click();", link_element)
                time.sleep(2)  # 等待頁面載入
                
                # 獲取詳細信息
                detailed_info = self.extract_detailed_info_from_page()
                
                # 合併詳細信息
                shop_info.update(detailed_info)
                
                # 返回列表頁面
                self.driver.back()
                time.sleep(1.5)  # 等待返回
                
            except Exception as e:
                self.debug_print(f"獲取詳細信息失敗 {name}: {e}", "ERROR")
                # 如果詳細頁面失敗，使用基本信息
                shop_info.update({
                    'address': '地址獲取失敗',
                    'phone': '電話獲取失敗', 
                    'hours': '營業時間獲取失敗',
                    'rating': '評分獲取失敗'
                })
                
                # 嘗試返回列表頁面
                try:
                    self.driver.back()
                    time.sleep(1)
                except:
                    pass
            
            return shop_info
            
        except Exception as e:
            return None
    
    def extract_detailed_info_from_page(self):
        """從店家詳細頁面擷取完整信息"""
        detailed_info = {
            'address': '地址未提供',
            'phone': '電話未提供',
            'hours': '營業時間未提供',
            'rating': '評分未提供'
        }
        
        try:
            # 等待頁面載入完成
            WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # 獲取地址信息
            address_selectors = [
                "[data-item-id='address'] .fontBodyMedium",
                "[data-item-id='address'] .DkEaL",
                "button[data-item-id='address'] .fontBodyMedium",
                ".Io6YTe.fontBodyMedium[data-item-id='address']",
                "[aria-label*='地址'] .fontBodyMedium",
                ".fontBodyMedium:contains('台灣')",
                ".fontBodyMedium:contains('高雄')",
            ]
            
            for selector in address_selectors:
                try:
                    if ':contains(' in selector:
                        # 使用XPath處理contains
                        xpath = f"//div[contains(@class, 'fontBodyMedium') and (contains(text(), '台灣') or contains(text(), '高雄'))]"
                        address_elem = self.driver.find_element(By.XPATH, xpath)
                    else:
                        address_elem = self.driver.find_element(By.CSS_SELECTOR, selector)
                    
                    address_text = address_elem.text.strip()
                    if address_text and len(address_text) > 5:
                        detailed_info['address'] = address_text
                        self.debug_print(f"✅ 找到地址: {address_text[:30]}...", "SUCCESS")
                        break
                except:
                    continue
            
            # 獲取電話信息
            phone_selectors = [
                "[data-item-id='phone:tel:'] .fontBodyMedium",
                "button[data-item-id*='phone'] .fontBodyMedium", 
                "[aria-label*='電話'] .fontBodyMedium",
                "a[href^='tel:']",
                ".fontBodyMedium[jslog*='phone']",
                "[data-value*='phone'] .fontBodyMedium"
            ]
            
            for selector in phone_selectors:
                try:
                    phone_elem = self.driver.find_element(By.CSS_SELECTOR, selector)
                    phone_text = phone_elem.text.strip()
                    
                    # 驗證電話格式
                    if phone_text and (phone_text.startswith('0') or '+' in phone_text or '-' in phone_text):
                        detailed_info['phone'] = phone_text
                        self.debug_print(f"✅ 找到電話: {phone_text}", "SUCCESS")
                        break
                        
                    # 也檢查href屬性
                    href = phone_elem.get_attribute('href')
                    if href and href.startswith('tel:'):
                        phone_number = href.replace('tel:', '').strip()
                        if phone_number:
                            detailed_info['phone'] = phone_number
                            self.debug_print(f"✅ 找到電話(href): {phone_number}", "SUCCESS")
                            break
                except:
                    continue
            
            # 獲取營業時間
            hours_selectors = [
                "[data-item-id='oh'] .fontBodyMedium",
                "[aria-label*='營業時間'] .fontBodyMedium",
                ".fontBodyMedium[jslog*='hours']",
                "[data-value*='hours'] .fontBodyMedium",
                ".t39EBf.GUrTXd .fontBodyMedium"  # 營業時間的常見CSS
            ]
            
            for selector in hours_selectors:
                try:
                    hours_elem = self.driver.find_element(By.CSS_SELECTOR, selector)
                    hours_text = hours_elem.text.strip()
                    if hours_text and ('時' in hours_text or ':' in hours_text or '營業' in hours_text):
                        detailed_info['hours'] = hours_text
                        self.debug_print(f"✅ 找到營業時間: {hours_text[:30]}...", "SUCCESS")
                        break
                except:
                    continue
            
            # 獲取評分信息
            rating_selectors = [
                ".F7nice span[aria-hidden='true']",
                "[aria-label*='星'] span",
                ".fontDisplayLarge[aria-hidden='true']",
                ".F7nice .fontDisplayLarge"
            ]
            
            for selector in rating_selectors:
                try:
                    rating_elem = self.driver.find_element(By.CSS_SELECTOR, selector)
                    rating_text = rating_elem.text.strip()
                    if rating_text and ('.' in rating_text or rating_text.replace('.', '').isdigit()):
                        detailed_info['rating'] = f"{rating_text} 星"
                        self.debug_print(f"✅ 找到評分: {rating_text} 星", "SUCCESS")
                        break
                except:
                    continue
            
            return detailed_info
            
        except Exception as e:
            self.debug_print(f"詳細信息擷取錯誤: {e}", "ERROR")
            return detailed_info
    
    def scroll_and_extract_turbo(self):
        """高速滾動並擷取店家資訊"""
        try:
            self.debug_print(f"🦊 開始Firefox高速擷取 {self.current_location} 的店家...", "FIREFOX")
            
            container = self.find_scrollable_container()
            if not container:
                return False
            
            last_count = 0
            no_change_count = 0
            max_no_change = 3  # 增強模式：3次無變化停止
            max_scrolls = self.max_scrolls    # 使用類變數設定的滾動次數
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
                    
                    shop_info = self.extract_shop_info_detailed(link)
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
        """獲取關鍵搜索地點列表 - 擴大覆蓋範圍達到2000家目標"""
        
        # 大幅擴大搜尋範圍 - 包含高雄周邊縣市
        core_locations = [
            # 高雄市中心核心
            "高雄火車站", "五福商圈", "新崛江商圈", "大立百貨", "漢來大飯店",
            "統一夢時代購物中心", "中山大學", "高雄醫學大學", "文化中心", 
            "六合夜市", "瑞豐夜市", "三多商圈", "中央公園",
            
            # 鳳山區
            "鳳山火車站", "鳳山區公所", "大東文化藝術中心", "正修科技大學", 
            "澄清湖", "鳳山中山路", "鳳山青年路", "衛武營",
            
            # 左營楠梓區
            "高雄左營站", "新光三越左營店", "漢神巨蛋", "楠梓火車站",
            "高雄大學", "右昌", "左營蓮池潭", "半屏山",
            
            # 三民區
            "建工路商圈", "民族路商圈", "九如路", "十全路", "大豐路",
            "覺民路", "三民家商", "高雄車站",
            
            # 苓雅區
            "苓雅區公所", "成功路", "光華路", "青年路", "四維路",
            "中正路", "民權路", "林德官",
            
            # 前鎮小港區
            "草衙道", "小港機場", "前鎮區公所", "獅甲", "小港醫院",
            "前鎮高中", "小港區公所", "中鋼",
            
            # 鼓山區
            "西子灣", "駁二藝術特區", "美術館", "內惟", "鼓山區公所",
            "明誠路", "美術東路", "博愛路",
            
            # 新興區
            "新興區公所", "中山路", "七賢路", "林森路", "新興高中",
            
            # 前金區
            "前金區公所", "中正路", "成功路", "市議會", "勞工公園",
            
            # 鹽埕區
            "鹽埕區公所", "大勇路", "七賢路", "駁二", "愛河",
            
            # 岡山區
            "岡山火車站", "岡山區公所", "岡山高中", "岡山夜市",
            
            # 路竹區
            "路竹火車站", "路竹區公所", "路竹高中",
            
            # 橋頭區
            "橋頭火車站", "橋頭區公所", "橋頭糖廠",
            
            # 大寮區
            "大寮區公所", "大寮車站", "義守大學",
            
            # 林園區
            "林園區公所", "林園高中",
            
            # 旗山區
            "旗山車站", "旗山區公所", "旗山老街",
            
            # 美濃區
            "美濃區公所", "美濃車站",
            
            # 購物中心
            "大遠百", "太平洋SOGO", "環球購物中心", "義大世界",
            "好市多高雄店", "IKEA高雄店", "家樂福", "大潤發",
            
            # 醫院
            "高雄榮總", "高雄醫學大學附設醫院", "長庚紀念醫院", 
            "義大醫院", "阮綜合醫院", "國軍高雄總醫院",
            
            # 夜市和商圈
            "光華夜市", "南華路夜市", "興中夜市", "凱旋夜市", 
            "青年夜市", "自強夜市", "忠孝夜市", "鳳山第一公有零售市場",
            
            # 大學和學校
            "中山大學", "高雄大學", "高雄師範大學", "高雄應用科技大學",
            "樹德科技大學", "文藻外語大學", "東方設計大學",
            
            # 重要道路和地標
            "博愛路", "民生路", "中華路", "中山路", "青年路",
            "建國路", "自由路", "同盟路", "澄清路", "鳥松區公所",
            
            # 擴大搜尋範圍 - 高雄週邊城市
            "台南市中西區", "台南火車站", "台南中山路", "台南成功大學",
            "屏東市中正路", "屏東火車站", "屏東大學", "屏東夜市",
            "嘉義市中山路", "嘉義火車站", "嘉義大學", "嘉義文化路",
            
            # 高雄市38個行政區完整覆蓋
            # 市區核心區（已在上面）：鹽埕區、鼓山區、左營區、楠梓區、三民區、新興區、前金區、苓雅區、前鎮區、小港區
            
            # 鳳山區（已在上面有部分）
            "鳳山區公所", "鳳山火車站", "鳳山中山路", "鳳山青年路", "鳳山市場",
            
            # 旗津區
            "旗津區公所", "旗津輪渡站", "旗津海岸公園", "旗津老街",
            
            # 林園區  
            "林園區公所", "林園高中", "林園工業區", "林園市場",
            
            # 大寮區
            "大寮區公所", "大寮車站", "義守大學", "大寮市場",
            
            # 大樹區
            "大樹區公所", "佛光山", "大樹火車站", "大樹市場",
            
            # 大社區
            "大社區公所", "大社工業區", "大社市場",
            
            # 仁武區
            "仁武區公所", "仁武火車站", "仁武市場", "仁武澄觀路",
            
            # 鳥松區
            "鳥松區公所", "鳥松澄清湖", "鳥松市場", "鳥松長庚路",
            
            # 岡山區（已在上面有部分）
            "岡山區公所", "岡山火車站", "岡山高中", "岡山夜市", "岡山市場",
            
            # 橋頭區（已在上面有部分）
            "橋頭區公所", "橋頭火車站", "橋頭糖廠", "橋頭市場",
            
            # 燕巢區
            "燕巢區公所", "高雄師範大學燕巢校區", "燕巢市場", "燕巢泥火山",
            
            # 田寮區
            "田寮區公所", "田寮月世界", "田寮市場",
            
            # 阿蓮區
            "阿蓮區公所", "阿蓮火車站", "阿蓮市場",
            
            # 路竹區（已在上面有部分）
            "路竹區公所", "路竹火車站", "路竹高中", "路竹市場",
            
            # 湖內區
            "湖內區公所", "湖內火車站", "湖內市場",
            
            # 茄萣區
            "茄萣區公所", "茄萣火車站", "茄萣市場", "茄萣濱海公園",
            
            # 永安區
            "永安區公所", "永安火車站", "永安市場", "永安漁港",
            
            # 彌陀區
            "彌陀區公所", "彌陀火車站", "彌陀市場", "彌陀漁港",
            
            # 梓官區
            "梓官區公所", "梓官火車站", "梓官市場", "梓官漁港",
            
            # 旗山區（已在上面有部分）
            "旗山區公所", "旗山車站", "旗山老街", "旗山市場", "旗山醫院",
            
            # 美濃區（已在上面有部分）
            "美濃區公所", "美濃車站", "美濃市場", "美濃客家文物館",
            
            # 六龜區
            "六龜區公所", "六龜市場", "六龜荖濃溪", "六龜溫泉",
            
            # 甲仙區
            "甲仙區公所", "甲仙市場", "甲仙芋頭冰", "甲仙老街",
            
            # 杉林區
            "杉林區公所", "杉林市場", "杉林大愛園區",
            
            # 內門區
            "內門區公所", "內門市場", "內門宋江陣",
            
            # 茂林區
            "茂林區公所", "茂林國家風景區", "茂林紫蝶幽谷",
            
            # 桃源區
            "桃源區公所", "桃源市場", "桃源溫泉",
            
            # 那瑪夏區
            "那瑪夏區公所", "那瑪夏民生醫院",
            
            # 更多商業區
            "漢神百貨", "大統百貨", "新光三越三多店", "愛買",
            "特力屋", "B&Q", "燦坤", "全國電子", "順發3C",
            "屈臣氏", "康是美", "寶雅", "小三美日",
            
            # 捷運站點
            "美麗島站", "中央公園站", "三多商圈站", "獅甲站",
            "凱旋站", "前鎮高中站", "草衙站", "世運站",
            "左營站", "巨蛋站", "生態園區站", "橋頭糖廠站",
            "橋頭火車站", "青埔站", "都會公園站", "後勁站",
            
            # 更多住宅區和生活圈
            "鼓山一路", "鼓山二路", "鼓山三路", "美術東二路",
            "美術東三路", "美術東四路", "美術東五路",
            "河西路", "河東路", "大中路", "大順路", "民族路",
            "建國路", "九如路", "十全路", "覺民路",
            "明誠路", "自由路", "中華路", "中山路",
            "成功路", "五福路", "四維路", "三多路",
            
            # 學校周邊
            "高雄女中", "高雄中學", "三民高中", "前鎮高中",
            "左營高中", "楠梓高中", "鳳山高中", "岡山高中",
            "小港高中", "海青工商", "中正高工", "高雄高工",
            
            # 傳統市場
            "鳳山市場", "三民市場", "苓雅市場", "前金市場",
            "新興市場", "鹽埕市場", "鼓山市場", "左營市場",
            "楠梓市場", "仁武市場", "大社市場", "橋頭市場"
        ]
        
        self.debug_print(f"🦊 Firefox擴大搜尋模式：覆蓋 {len(core_locations)} 個搜尋點", "FIREFOX")
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
            self.debug_print("🔧 優化特色：Firefox瀏覽器、大半徑搜索、詳細信息擷取", "INFO")
            print("=" * 80)
            
            if not self.setup_driver():
                return False
            
            if not self.open_google_maps():
                return False
            
            # 高速模式：聚焦核心地點
            locations = self.get_key_search_locations()
            
            # 大幅擴大店家類型搜索 - 增加更多相關關鍵字
            shop_types = [
                # 基本美甲美睫
                "美甲店", "美睫店", "指甲彩繪", "手足保養", "美甲美睫",
                "nail salon", "eyelash extension", "美容美甲",
                "指甲店", "睫毛店", "美甲工作室", "美睫工作室",
                "nail art", "美甲沙龍", "美睫沙龍",
                
                # 更多美甲相關
                "凝膠指甲", "光療指甲", "水晶指甲", "法式美甲",
                "指甲彩繪店", "指甲護理", "指甲修護", "指甲造型",
                "手部保養", "足部保養", "手足護理", "指甲油",
                
                # 更多美睫相關  
                "睫毛嫁接", "植睫毛", "種睫毛", "接睫毛",
                "假睫毛", "睫毛燙", "睫毛夾", "睫毛增長",
                "眉毛設計", "眉毛修護", "眉毛造型", "繡眉",
                
                # 耳燭相關
                "耳燭", "耳燭療法", "耳燭護理", "耳部護理",
                "ear candling", "耳燭工作室", "耳燭店", "耳燭館",
                "耳部保養", "耳朵護理", "耳燭美容",
                
                # 英文關鍵字
                "beauty salon", "nail spa", "lash bar", "nail studio",
                "manicure", "pedicure", "gel nails", "nail design",
                "lash extensions", "eyebrow design", "beauty studio",
                
                # 複合式美容
                "美甲美睫美容", "美甲美睫工作室", "美容美甲店",
                "指甲睫毛專門店", "美甲美睫沙龍"
            ]
            
            self.debug_print("【Firefox高速搜索模式】設定：", "FIREFOX")
            self.debug_print(f"📍 核心地點: {len(locations)} 個商業區", "INFO")
            self.debug_print(f"🏪 店家類型: {len(shop_types)} 種類型", "INFO")
            self.debug_print(f"🎯 搜索半徑: {self.search_radius_km}km", "INFO")
            self.debug_print(f"🦊 每輪處理: {self.max_shops_per_search}家店家", "INFO")
            self.debug_print(f"🔍 預估搜尋次數: {len(locations) * len(shop_types)} 次", "INFO")
            self.debug_print("⏰ 預估完成時間: 60-120分鐘 (詳細模式)", "TURBO")
            print("-" * 70)
            
            total_searches = len(locations) * len(shop_types)
            current_search = 0
            search_round = 1
            
            # 持續搜尋直到達到目標
            while len(self.shops_data) < self.target_shops:
                self.debug_print(f"🦊 Firefox 第 {search_round} 輪搜尋開始", "FIREFOX")
                
                # 對每個核心地點進行搜尋
                for i, location in enumerate(locations, 1):
                    if len(self.shops_data) >= self.target_shops:
                        self.debug_print("🎯 已達到目標店家數量，停止所有搜尋", "SUCCESS")
                        break
                        
                    self.debug_print(f"🦊 [{i}/{len(locations)}] Firefox核心區域: {location}", "FIREFOX")
                    
                    if not self.set_location(location):
                        self.debug_print(f"定位到 '{location}' 失敗，跳過", "ERROR")
                        continue
                    
                    # 對每種店家類型進行搜尋
                    for j, shop_type in enumerate(shop_types, 1):
                        if len(self.shops_data) >= self.target_shops:
                            self.debug_print(f"🎯 達到目標！已收集 {len(self.shops_data)} 家店家", "SUCCESS")
                            break
                            
                        current_search += 1
                        self.debug_print(f"🦊 [{j}/{len(shop_types)}] Firefox搜尋: {shop_type}", "FIREFOX")
                        
                        if not self.search_nearby_shops_turbo(shop_type):
                            continue
                        
                        should_continue = self.scroll_and_extract_turbo()
                        if not should_continue:
                            self.debug_print(f"🎯 達到{self.target_shops}家目標，停止搜尋", "SUCCESS")
                            break
                        
                        # 顯示進度
                        shops_progress = (len(self.shops_data) / self.target_shops) * 100
                        self.debug_print(f"📊 Firefox搜尋進度: 第{search_round}輪 | 店家進度: {shops_progress:.1f}% ({len(self.shops_data)}/{self.target_shops})", "FIREFOX")
                        
                        # 高速模式：減少等待時間
                        time.sleep(random.uniform(0.3, 1.0))
                
                    location_shops = len(self.current_location_shops)
                    self.debug_print(f"🦊 Firefox '{location}' 完成，新增 {location_shops} 家店，累計 {len(self.shops_data)} 家", "SUCCESS")
                    
                    # 每完成10個地點，暫存一次結果
                    if i % 10 == 0 and self.shops_data:
                        timestamp = datetime.now().strftime("%H%M%S")
                        temp_filename = f"高雄美甲美睫店家_Firefox高速版_暫存_{timestamp}"
                        self.save_to_excel(temp_filename)
                    
                    # 高速模式：短暫等待
                    if i < len(locations):
                        time.sleep(random.uniform(0.5, 1.5))
                
                # 檢查是否達到目標或需要進行下一輪
                if len(self.shops_data) >= self.target_shops:
                    self.debug_print("🎯 已達到目標店家數量，停止所有搜尋", "SUCCESS")
                    break
                elif search_round >= 3:  # 最多搜尋3輪
                    self.debug_print(f"已完成 {search_round} 輪搜尋，停止並儲存結果", "INFO")
                    break
                else:
                    search_round += 1
                    self.debug_print(f"🔄 第 {search_round-1} 輪完成，收集到 {len(self.shops_data)} 家店，開始第 {search_round} 輪", "INFO")
            
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
    print("🦊 Google 地圖店家Firefox高速擷取程式 (增強版)")
    print("⚡ 專為快速收集2000家店家設計 - 大幅擴展搜尋範圍")
    print("🔧 使用Firefox避免與Chrome版本衝突")
    print()
    print("🎯 Firefox增強版優化特色：")
    print("   - 🦊 使用Firefox瀏覽器，避免Chrome衝突") 
    print("   - 🚀 搜索半徑8公里，減少搜索次數")
    print("   - 📍 擴大到200+個搜尋點（含周邊縣市）")
    print("   - 🔍 50+種搜尋關鍵字，涵蓋所有相關業態")
    print("   - ⚡ 每輪處理20家店家，確保信息完整性")
    print("   - 🔧 詳細信息獲取，包含電話、地址、營業時間")
    print("   - 🔄 多輪搜尋模式：確保達到2000家目標")
    print("   - 🎯 智能停止：達到2000家或搜尋3輪後停止")
    print()
    print("📊 大幅提升覆蓋率：")
    print("   - 📈 搜尋點數量增加3倍以上")
    print("   - 🔍 搜尋關鍵字增加4倍以上")
    print("   - ⏰ 預估完成時間：2-4小時")
    print("   - 🎯 目標：確保達到2000家店家")
    print()
    print("📍 大幅擴展覆蓋範圍：")
    print("   - 高雄市所有區域（38個行政區）")
    print("   - 台南、屏東、嘉義周邊城市")
    print("   - 所有捷運站點和交通樞紐")
    print("   - 購物中心、醫院、學校、市場周邊")
    print()
    print("📋 收集資訊：")
    print("   - 店家名稱、Google Maps連結")
    print("   - 📍 詳細地址信息（點擊獲取）")
    print("   - 📞 電話號碼（點擊獲取）")
    print("   - ⭐ 評分信息（點擊獲取）")
    print("   - 🕐 營業時間（點擊獲取）")
    print("   - 搜索位置記錄")
    print()
    print("💡 與Chrome版本並行：")
    print("   - 可與詳細版Chrome同時運行")
    print("   - 獨立的日誌文件 scraper_turbo_firefox.log")
    print("   - 不會干擾現有的Chrome進程")
    print("-" * 70)
    
    user_input = input("確定要開始Firefox增強版2000家店搜索嗎？(此版本會進行更徹底的搜索) (y/n): ").strip().lower()
    if user_input != 'y':
        print("程式已取消")
        return
    
    scraper = GoogleMapsTurboFirefoxScraper(debug_mode=True)
    scraper.run_turbo_scraping()

if __name__ == "__main__":
    main()