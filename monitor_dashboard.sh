#!/bin/bash
# 🚀 Google Maps 爬蟲實時監控面板

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 清屏函數
clear_screen() {
    clear
    echo -e "${CYAN}============================================================================${NC}"
    echo -e "${CYAN}           🚀 Google Maps 爬蟲實時監控面板 (2000家店版)                    ${NC}"
    echo -e "${CYAN}============================================================================${NC}"
    echo ""
}

# 檢查程式狀態
check_scraper_status() {
    echo -e "${BLUE}📊 程式執行狀態${NC}"
    echo "------------------------------------------------------------------------"
    
    if pgrep -f "python3.*scraper" > /dev/null; then
        PID=$(pgrep -f "python3.*scraper")
        echo -e "   狀態: ${GREEN}✅ 爬蟲程式正在運行${NC}"
        echo -e "   進程ID: ${GREEN}$PID${NC}"
        START_TIME=$(ps -o lstart= -p $PID 2>/dev/null | head -1)
        if [ ! -z "$START_TIME" ]; then
            echo -e "   開始時間: ${YELLOW}$START_TIME${NC}"
        fi
    else
        echo -e "   狀態: ${RED}❌ 爬蟲程式未運行${NC}"
        if screen -ls | grep -q "scraper"; then
            echo -e "   Screen: ${YELLOW}⚠️ 發現 Screen 會話${NC}"
        fi
    fi
    echo ""
}

# 檢查系統資源
check_system_resources() {
    echo -e "${BLUE}💻 系統資源使用情況${NC}"
    echo "------------------------------------------------------------------------"
    
    # CPU 使用率
    CPU_USAGE=$(top -bn1 | grep "Cpu(s)" | sed "s/.*, *\([0-9.]*\)%* id.*/\1/" | awk '{print 100 - $1}')
    echo -e "   CPU 使用率: ${GREEN}${CPU_USAGE}%${NC}"
    
    # 記憶體使用
    MEM_INFO=$(free -h | awk '/^Mem:/ {print $3 "/" $2 " (" int($3/$2 * 100) "%)"}')
    echo -e "   記憶體使用: ${GREEN}$MEM_INFO${NC}"
    
    # 磁碟使用
    DISK_INFO=$(df -h / | awk '/\// {print $3 "/" $2 " (" $5 ")"}')
    echo -e "   磁碟使用: ${GREEN}$DISK_INFO${NC}"
    
    # 交換記憶體
    SWAP_INFO=$(free -h | awk '/^Swap:/ {if($2 != "0B") print $3 "/" $2; else print "未使用"}')
    echo -e "   Swap 使用: ${GREEN}$SWAP_INFO${NC}"
    
    echo ""
}

# 檢查網路狀況
check_network() {
    echo -e "${BLUE}🌐 網路連接狀況${NC}"
    echo "------------------------------------------------------------------------------------------------"
    
    # 檢查網路連接
    if ping -c 1 google.com &> /dev/null; then
        echo -e "   網路連接: ${GREEN}✅ 正常${NC}"
    else
        echo -e "   網路連接: ${RED}❌ 異常${NC}"
    fi
    
    # 檢查 Google Maps 連接
    if curl -s --max-time 5 https://maps.google.com > /dev/null; then
        echo -e "   Google Maps: ${GREEN}✅ 可訪問${NC}"
    else
        echo -e "   Google Maps: ${RED}❌ 無法訪問${NC}"
    fi
    
    echo ""
}

# 檢查檔案狀況
check_files() {
    echo -e "${BLUE}📁 檔案和進度狀況${NC}"
    echo "------------------------------------------------------------------------"
    
    # 檢查結果檔案
    EXCEL_COUNT=$(ls -1 *.xlsx 2>/dev/null | wc -l)
    CSV_COUNT=$(ls -1 *.csv 2>/dev/null | wc -l)
    
    echo -e "   Excel 檔案數量: ${GREEN}$EXCEL_COUNT${NC}"
    echo -e "   CSV 檔案數量: ${GREEN}$CSV_COUNT${NC}"
    
    # 檢查最新檔案
    if [ $EXCEL_COUNT -gt 0 ]; then
        LATEST_EXCEL=$(ls -t *.xlsx 2>/dev/null | head -1)
        EXCEL_SIZE=$(du -h "$LATEST_EXCEL" 2>/dev/null | cut -f1)
        echo -e "   最新 Excel: ${YELLOW}$LATEST_EXCEL${NC} (${GREEN}$EXCEL_SIZE${NC})"
        
        # 嘗試讀取店家數量
        if command -v python3 &> /dev/null; then
            SHOP_COUNT=$(python3 -c "
import pandas as pd
try:
    df = pd.read_excel('$LATEST_EXCEL')
    print(len(df))
except:
    print('0')
" 2>/dev/null)
            if [ "$SHOP_COUNT" != "0" ]; then
                PROGRESS=$(echo "scale=1; $SHOP_COUNT * 100 / 2000" | bc 2>/dev/null)
                echo -e "   店家數量: ${GREEN}$SHOP_COUNT${NC}/2000 (${YELLOW}${PROGRESS}%${NC})"
            fi
        fi
    fi
    
    # 檢查日誌檔案
    if [ -f "scraper_detailed.log" ]; then
        LOG_SIZE=$(du -h scraper_detailed.log | cut -f1)
        echo -e "   日誌檔案: ${GREEN}存在${NC} (${YELLOW}$LOG_SIZE${NC})"
        LAST_LOG=$(tail -1 scraper_detailed.log 2>/dev/null | cut -c1-60)
        if [ ! -z "$LAST_LOG" ]; then
            echo -e "   最後活動: ${CYAN}$LAST_LOG...${NC}"
        fi
    fi
    
    # 檢查檢查點檔案
    if [ -f "scraper_checkpoint.json" ]; then
        CHECKPOINT_SIZE=$(du -h scraper_checkpoint.json | cut -f1)
        echo -e "   檢查點檔案: ${GREEN}存在${NC} (${YELLOW}$CHECKPOINT_SIZE${NC})"
    else
        echo -e "   檢查點檔案: ${YELLOW}不存在${NC}"
    fi
    
    echo ""
}

# 檢查日誌中的錯誤
check_errors() {
    echo -e "${BLUE}🚨 錯誤和警告檢查${NC}"
    echo "------------------------------------------------------------------------"
    
    if [ -f "scraper_detailed.log" ]; then
        ERROR_COUNT=$(grep -c "ERROR" scraper_detailed.log 2>/dev/null || echo "0")
        SUCCESS_COUNT=$(grep -c "SUCCESS" scraper_detailed.log 2>/dev/null || echo "0")
        
        echo -e "   錯誤數量: ${RED}$ERROR_COUNT${NC}"
        echo -e "   成功數量: ${GREEN}$SUCCESS_COUNT${NC}"
        
        if [ $ERROR_COUNT -gt 0 ]; then
            echo -e "   ${RED}最近錯誤:${NC}"
            tail -50 scraper_detailed.log | grep "ERROR" | tail -2 | while read line; do
                echo -e "   ${RED}↳${NC} $(echo "$line" | cut -c1-60)..."
            done
        fi
    fi
    echo ""
}

# 顯示 Screen 會話
check_screen_sessions() {
    echo -e "${BLUE}🖥️ Screen 會話狀態${NC}"
    echo "------------------------------------------------------------------------------------------------"
    
    SCREEN_OUTPUT=$(screen -ls 2>/dev/null)
    if echo "$SCREEN_OUTPUT" | grep -q "scraper"; then
        echo -e "   ${GREEN}✅ 發現爬蟲相關的 Screen 會話:${NC}"
        echo "$SCREEN_OUTPUT" | grep -E "(scraper|Attached|Detached)" | sed 's/^/   /'
    else
        echo -e "   ${YELLOW}⚠️ 未發現爬蟲相關的 Screen 會話${NC}"
    fi
    
    echo ""
}

# 顯示統計資訊
show_statistics() {
    echo -e "${BLUE}📊 執行統計${NC}"
    echo "------------------------------------------------------------------------------------------------"
    
    if [ -f "scraper_detailed.log" ]; then
        # 計算各種統計
        TOTAL_SEARCHES=$(grep -c "搜尋" scraper_detailed.log 2>/dev/null || echo "0")
        SHOPS_FOUND=$(grep -c "新增店家" scraper_detailed.log 2>/dev/null || echo "0")
        LOCATIONS_PROCESSED=$(grep -c "地點.*完成" scraper_detailed.log 2>/dev/null || echo "0")
        
        echo -e "   總搜尋次數: ${CYAN}$TOTAL_SEARCHES${NC}"
        echo -e "   發現店家: ${GREEN}$SHOPS_FOUND${NC}"
        echo -e "   處理地點: ${YELLOW}$LOCATIONS_PROCESSED${NC}"
        
        # 計算平均效率
        if [ $TOTAL_SEARCHES -gt 0 ] && [ $SHOPS_FOUND -gt 0 ]; then
            EFFICIENCY=$(echo "scale=2; $SHOPS_FOUND * 100 / $TOTAL_SEARCHES" | bc 2>/dev/null)
            echo -e "   成功率: ${GREEN}${EFFICIENCY}%${NC}"
        fi
    fi
    
    echo ""
}

# 顯示操作選項
show_options() {
    echo -e "${CYAN}🔧 快速操作: [r]重新整理 [l]查看日誌 [s]連接Screen [k]停止程式 [q]退出${NC}"
    echo ""
}

# 主監控函數
monitor_dashboard() {
    while true; do
        clear_screen
        check_scraper_status
        check_system_resources
        check_network
        check_files
        check_errors
        check_screen_sessions
        show_statistics
        show_options
        
        echo -n "選擇操作或等待30秒自動重新整理: "
        read -t 30 -n 1 choice
        echo ""
        
        case $choice in
            r|R) continue ;;
            l|L) 
                echo "開啟即時日誌... (按 Ctrl+C 返回)"
                sleep 2
                tail -f scraper_detailed.log
                ;;
            s|S)
                if screen -ls | grep -q "scraper"; then
                    screen -r scraper
                else
                    echo "未發現 scraper Screen 會話"
                    sleep 2
                fi
                ;;
            k|K)
                echo "確定停止程式? (y/N): "
                read -n 1 confirm
                if [[ $confirm =~ ^[Yy]$ ]]; then
                    pkill -f "python3.*scraper"
                    echo "已停止程式"
                    sleep 2
                fi
                ;;
            q|Q) exit 0 ;;
        esac
    done
}

# 檢查是否在正確的目錄
if [ ! -f "google_maps_scraper_detailed.py" ] && [ ! -f "test_scraper.py" ]; then
    echo -e "${RED}❌ 錯誤：請在包含爬蟲程式的目錄中執行此腳本${NC}"
    echo "建議目錄：~/google_maps_scraper_2000/"
    exit 1
fi

# 啟動監控面板
monitor_dashboard 