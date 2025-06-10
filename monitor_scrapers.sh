#!/bin/bash

# Google Maps 爬蟲雙版本監控腳本
# 同時監控詳細版和高速版的運行狀況

echo "📊 Google Maps 爬蟲雙版本監控面板"
echo "🕒 檢查時間: $(date)"
echo "=" * 60

# 進入工作目錄
cd ~/google_maps_scraper_2000/ 2>/dev/null || {
    echo "❌ 無法進入工作目錄 ~/google_maps_scraper_2000/"
    exit 1
}

echo "📁 當前目錄: $(pwd)"
echo ""

# 檢查Screen會話狀態
echo "🖥️  Screen 會話狀態："
echo "-" * 30
if command -v screen >/dev/null 2>&1; then
    screen_output=$(screen -list 2>/dev/null)
    if echo "$screen_output" | grep -q "\."; then
        echo "$screen_output"
        echo ""
        
        # 檢查詳細版會話
        if echo "$screen_output" | grep -q "detailed_scraper\|scraper"; then
            echo "✅ 詳細版 Screen 會話運行中"
        else
            echo "❌ 詳細版 Screen 會話未運行"
        fi
        
        # 檢查高速版會話
        if echo "$screen_output" | grep -q "turbo_scraper"; then
            echo "✅ 高速版 Screen 會話運行中"
        else
            echo "❌ 高速版 Screen 會話未運行"
        fi
    else
        echo "❌ 沒有運行中的 Screen 會話"
    fi
else
    echo "❌ Screen 未安裝"
fi

echo ""
echo "=" * 60

# 監控詳細版
echo "🔍 詳細版爬蟲狀態 (google_maps_scraper_detailed.py)："
echo "-" * 50

if [ -f "scraper_detailed.log" ]; then
    echo "📅 詳細版日誌更新時間:"
    ls -la scraper_detailed.log | awk '{print $6, $7, $8}'
    echo ""
    
    echo "📊 詳細版最新進度:"
    grep "總店家數進度\|達到目標" scraper_detailed.log | tail -3
    echo ""
    
    echo "✅ 詳細版最新收集的店家:"
    grep "新增店家" scraper_detailed.log | tail -3 | sed 's/.*新增店家: /  - /'
    echo ""
    
    echo "🏪 詳細版地點完成情況:"
    grep "地點.*完成" scraper_detailed.log | tail -3
    echo ""
else
    echo "❌ 詳細版日誌文件不存在 (scraper_detailed.log)"
fi

echo "=" * 60

# 監控高速版
echo "🚀 高速版爬蟲狀態 (google_maps_scraper_turbo.py)："
echo "-" * 50

if [ -f "scraper_turbo.log" ]; then
    echo "📅 高速版日誌更新時間:"
    ls -la scraper_turbo.log | awk '{print $6, $7, $8}'
    echo ""
    
    echo "📊 高速版最新進度:"
    grep "總計.*/" scraper_turbo.log | tail -3
    echo ""
    
    echo "🚀 高速版搜尋進度:"
    grep "搜尋進度.*店家進度" scraper_turbo.log | tail -3
    echo ""
    
    echo "✅ 高速版新增店家:"
    grep "本次新增.*家店家" scraper_turbo.log | tail -3
    echo ""
    
    echo "🏪 高速版核心區域完成:"
    grep "核心區域.*完成" scraper_turbo.log | tail -3
    echo ""
else
    echo "❌ 高速版日誌文件不存在 (scraper_turbo.log)"
fi

echo "=" * 60

# 檢查生成的Excel文件
echo "📁 已生成的Excel文件："
echo "-" * 30
ls -la *.xlsx 2>/dev/null | head -10 || echo "❌ 暫無Excel文件"

echo ""
echo "📁 已生成的CSV文件："
echo "-" * 30
ls -la *.csv 2>/dev/null | head -10 || echo "❌ 暫無CSV文件"

echo ""
echo "=" * 60

# 提供快速操作指令
echo "🛠️  快速操作指令："
echo "-" * 30
echo "📊 查看詳細版即時日誌:   tail -f scraper_detailed.log"
echo "🚀 查看高速版即時日誌:   tail -f scraper_turbo.log"
echo "🖥️  進入詳細版Screen:     screen -r (會話名稱)"
echo "🖥️  進入高速版Screen:     screen -r turbo_scraper"
echo "📈 詳細版進度查詢:       grep '總店家數進度' scraper_detailed.log | tail -10"
echo "📈 高速版進度查詢:       grep '總計.*/' scraper_turbo.log | tail -10"
echo "🔄 重新運行此監控:       ./monitor_scrapers.sh"
echo ""

# 系統資源使用情況
echo "💻 系統資源使用情況："
echo "-" * 30
echo "🧠 記憶體使用:"
free -h | head -2

echo ""
echo "💿 磁碟使用:"
df -h . | tail -1

echo ""
echo "🔥 Python進程:"
ps aux | grep python | grep -E "(scraper|chrome)" | grep -v grep | wc -l | xargs echo "Python爬蟲進程數:"

echo ""
echo "=" * 60
echo "✨ 監控完成！使用上述指令查看詳細資訊"