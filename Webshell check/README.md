# Webshell Checker

一個高效的 Webshell 掃描工具，使用 **目錄列表 + 檔名字典** 組合方式進行暴力檢查。

## 功能特點

- 多執行緒加速掃描
- HEAD + GET 雙重檢查機制
- 內容長度過濾（減少誤報）
- 完整 Logging 系統
- 支援 Proxy、Delay 等進階設定

## 安裝方式

```bash
git clone https://github.com/你的帳號/webshell-checker.git
cd webshell-checker
pip install -r requirements.txt
使用方法
Bashpython check_webshell.py \
  --directories web_directories.txt \
  --dictionary webshell_dict.txt \
  --output found_webshells.txt \
  --threads 50
參數說明

參數簡寫必填說明預設值--directories-d是目錄列表檔案（Script 1 輸出的目錄清單）---dictionary-w是Webshell 檔名字典檔案---output-o否發現的 Webshell 結果輸出檔案found_webshells.txt--threads-t否並行執行緒數量20--timeout-否單一 HTTP 請求超時時間（秒）10--user-agent-否自訂 User-AgentChrome 預設--proxy-否使用 HTTP Proxy（例：http://127.0.0.1:8080）---delay-否每個請求之間的延遲（秒，避免被封鎖）0--allow-redirect-否是否允許 HTTP 重導向False
使用範例
Bash# 基本使用
python check_webshell.py -d directories.txt -w webshell_dict.txt

# 高併發 + Proxy
python check_webshell.py -d dirs.txt -w dict.txt -t 100 --proxy http://127.0.0.1:7890 --delay 0.5
範例檔案
請參考 example/ 資料夾內的範例檔案。