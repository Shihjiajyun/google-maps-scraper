#!/bin/bash
# GCP Ubuntu 環境設置腳本 - Google Maps 爬蟲專用

echo "🚀 開始設置 GCP 環境用於 Google Maps 爬蟲..."

# 更新系統
sudo apt update && sudo apt upgrade -y

# 安裝 Python 和 pip
sudo apt install python3 python3-pip python3-venv -y

# 安裝 Chrome 瀏覽器
wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" | sudo tee /etc/apt/sources.list.d/google-chrome.list
sudo apt update
sudo apt install google-chrome-stable -y

# 安裝 ChromeDriver
CHROMEDRIVER_VERSION=$(curl -sS chromedriver.storage.googleapis.com/LATEST_RELEASE)
wget -O /tmp/chromedriver.zip https://chromedriver.storage.googleapis.com/$CHROMEDRIVER_VERSION/chromedriver_linux64.zip
sudo unzip /tmp/chromedriver.zip chromedriver -d /usr/local/bin/
sudo chmod +x /usr/local/bin/chromedriver

# 安裝中文字體支援
sudo apt install fonts-wqy-zenhei fonts-wqy-microhei -y

# 安裝其他必要套件
sudo apt install xvfb unzip curl wget screen htop -y

# 建立虛擬環境
python3 -m venv gcp_scraper_env
source gcp_scraper_env/bin/activate

# 安裝 Python 套件
pip install --upgrade pip
pip install selenium pandas openpyxl requests beautifulsoup4 lxml

# 建立專案目錄
mkdir -p ~/google_maps_scraper
cd ~/google_maps_scraper

echo "✅ GCP 環境設置完成！"
echo ""
echo "🔧 使用方法："
echo "1. 上傳 Python 程式到 ~/google_maps_scraper/"
echo "2. 啟動虛擬環境：source ~/gcp_scraper_env/bin/activate"
echo "3. 使用 Screen 運行：screen -S scraper"
echo "4. 在 Screen 中執行：python3 your_script.py"
echo "5. 離開但保持運行：Ctrl+A, D"
echo "6. 重新連接：screen -r scraper"
echo ""
echo "📊 監控命令："
echo "- 查看執行狀態：screen -ls"
echo "- 查看系統資源：htop"
echo "- 查看磁碟空間：df -h" 