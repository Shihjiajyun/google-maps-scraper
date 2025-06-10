#!/bin/bash

# Google Maps 高速版後台運行腳本
# 確保SSH斷線不會終止程序

echo "🚀 準備在後台運行 Google Maps 高速版爬蟲..."
echo "📅 開始時間: $(date)"
echo ""

# 檢查是否已有高速版在運行
if screen -list | grep -q "turbo_scraper"; then
    echo "⚠️  檢測到高速版已在運行中！"
    echo "📊 查看運行狀態請使用: screen -r turbo_scraper"
    echo "🛑 如需強制重啟，請先執行: screen -X -S turbo_scraper quit"
    exit 1
fi

# 確保在正確目錄
cd ~/google_maps_scraper_2000/ || {
    echo "❌ 無法進入工作目錄，請檢查路徑"
    exit 1
}

# 檢查Python文件是否存在
if [ ! -f "google_maps_scraper_turbo.py" ]; then
    echo "❌ 找不到 google_maps_scraper_turbo.py 文件"
    exit 1
fi

echo "✅ 環境檢查完成"
echo ""

# 創建高速版專用的screen會話
echo "🚀 創建高速版Screen會話: turbo_scraper"
screen -dmS turbo_scraper bash -c "
    echo '🚀 高速版爬蟲開始執行...'
    echo '📅 啟動時間: \$(date)'
    echo '📁 工作目錄: \$(pwd)'
    echo '🔧 Python版本: \$(python3 --version)'
    echo ''
    echo '⚡ 開始執行高速版爬蟲...'
    echo '=' * 50
    
    # 運行高速版爬蟲
    python3 google_maps_scraper_turbo.py
    
    echo ''
    echo '🏁 高速版爬蟲執行完成'
    echo '📅 結束時間: \$(date)'
    echo ''
    echo '💡 會話將保持開啟，按任意鍵關閉...'
    read
"

# 等待Screen會話創建
sleep 2

# 檢查Screen會話是否成功創建
if screen -list | grep -q "turbo_scraper"; then
    echo "✅ 高速版已成功在後台啟動！"
    echo ""
    echo "📊 監控命令："
    echo "   查看即時運行狀態: screen -r turbo_scraper"
    echo "   離開但保持運行: Ctrl+A, D"
    echo "   查看日誌: tail -f scraper_turbo.log"
    echo ""
    echo "🔍 快速檢查："
    echo "   screen -list                    # 查看所有會話"
    echo "   tail -f scraper_turbo.log      # 查看高速版日誌"
    echo "   grep '總計.*/' scraper_turbo.log | tail -5  # 查看進度"
    echo ""
    echo "⚠️  重要提醒："
    echo "   - SSH斷線不會影響程序運行"
    echo "   - 重新連接後使用 screen -r turbo_scraper 恢復查看"
    echo "   - 程序會自動在達到2000家店時停止"
else
    echo "❌ Screen會話創建失敗"
    exit 1
fi

echo ""
echo "🎯 高速版預計30-60分鐘完成2000家店收集"
echo "📈 預計速度提升10-15倍"
echo ""
echo "👀 立即查看運行狀態："
echo "screen -r turbo_scraper" 