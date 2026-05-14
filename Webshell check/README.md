# Webshell Checker

一個高效的 Webshell 掃描工具，使用 **目錄列表 + 檔名字典** 組合方式進行暴力檢查。

## 功能特點

- 多執行緒加速掃描
- HEAD + GET 雙重檢查機制
- 內容長度過濾（減少誤報）
- 完整 Logging 系統
- 支援 Proxy、Delay 等進階設定

## 主要升級點（14/5/2026）
- 風險評分系統（核心改進）
- Title + 關鍵字 + HTML 結構 多維度檢測
- HEAD → GET 正確流程
- URL 去重 + 標準化
- 大幅降低誤報
- 詳細 logging 和彩色輸出
