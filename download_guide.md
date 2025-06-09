# 📥 下載結果檔案完整指南

## 🎯 結果檔案位置

爬蟲完成後，結果檔案會保存在 GCP 虛擬機器的以下位置：
```
~/google_maps_scraper_2000/
├── 高雄美甲美睫店家_詳細版_2000家達標_YYYYMMDD_HHMMSS.xlsx
├── 高雄美甲美睫店家_詳細版_2000家達標_YYYYMMDD_HHMMSS.csv
├── scraper_detailed.log
└── scraper_checkpoint.json
```

## 🚀 方法一：使用 gcloud CLI（推薦）

### 安裝 gcloud CLI
```bash
# Windows: 下載並安裝 https://cloud.google.com/sdk/docs/install
# macOS: brew install --cask google-cloud-sdk
# Linux: curl https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-cli-linux-x86_64.tar.gz | tar xz
```

### 下載檔案
```bash
# 下載所有結果檔案
gcloud compute scp google-maps-scraper:~/google_maps_scraper_2000/*.xlsx ./ --zone=asia-east1-a
gcloud compute scp google-maps-scraper:~/google_maps_scraper_2000/*.csv ./ --zone=asia-east1-a

# 下載整個目錄
gcloud compute scp --recurse google-maps-scraper:~/google_maps_scraper_2000/ ./results/ --zone=asia-east1-a
```

## 📦 方法二：使用 Cloud Storage

### 在虛擬機器中上傳
```bash
# SSH 到虛擬機器
gcloud compute ssh google-maps-scraper --zone=asia-east1-a

# 創建 bucket 並上傳
gsutil mb gs://your-scraper-results-bucket
cd ~/google_maps_scraper_2000
gsutil cp *.xlsx *.csv gs://your-scraper-results-bucket/
```

### 從 Cloud Storage 下載
```bash
# 下載到本地
gsutil -m cp gs://your-scraper-results-bucket/* ./local_results/

# 或通過瀏覽器：https://console.cloud.google.com/storage/
```

## 🗜️ 方法三：壓縮後下載

```bash
# 在虛擬機器中壓縮
gcloud compute ssh google-maps-scraper --zone=asia-east1-a
cd ~/google_maps_scraper_2000
tar -czf results_$(date +%Y%m%d).tar.gz *.xlsx *.csv *.log

# 下載壓縮檔案
gcloud compute scp google-maps-scraper:~/google_maps_scraper_2000/*.tar.gz ./ --zone=asia-east1-a
```

## 📊 檢查檔案內容

```bash
# 查看檔案資訊
ls -lah *.xlsx *.csv

# 用 Python 檢查內容
python3 -c "
import pandas as pd
df = pd.read_excel('檔案名.xlsx')
print(f'店家數量: {len(df)}')
print(f'欄位: {list(df.columns)}')
print(df.head())
"
```

## 🔄 自動下載腳本

```bash
# 創建自動下載腳本
cat > download_results.sh << 'EOF'
#!/bin/bash
echo "🚀 開始下載結果..."
mkdir -p ./results
gcloud compute scp google-maps-scraper:~/google_maps_scraper_2000/*.xlsx ./results/ --zone=asia-east1-a
gcloud compute scp google-maps-scraper:~/google_maps_scraper_2000/*.csv ./results/ --zone=asia-east1-a
echo "✅ 下載完成！"
ls -la ./results/
EOF

chmod +x download_results.sh
./download_results.sh
```

## 💰 清理資源

```bash
# 下載完成後停止虛擬機器節省費用
gcloud compute instances stop google-maps-scraper --zone=asia-east1-a

# 或刪除虛擬機器
gcloud compute instances delete google-maps-scraper --zone=asia-east1-a
```

## 🎯 注意事項

- Excel 檔案通常包含完整的店家資訊
- CSV 檔案可用於進一步的資料分析
- 確保檔案完整性，店家數量應接近 2000 家
- 建議備份重要的結果檔案 