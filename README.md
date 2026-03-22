# TronClass Skill

透過 mcporter 呼叫 TronClass MCP Server，自動化操作輔仁大學（及其他大學的） TronClass 平臺。

---

## 🛠️ MCP Server 工具列表

### 🔐 登入工具

| 工具 | 功能 |
|------|------|
| `login(username, password, org_keyword)` | 登入 TronClass |
| `get_profile` | 取得個人資料 |
| `check_connection` | 測試 API 連線 |

### 🎓 TronClass 專業工具

| 工具 | 功能 |
|------|------|
| `get_courses` | 取得課程列表（含 ID）|
| `get_course_details(course_id)` | 取得課程詳細資訊 |
| `get_announcements(course_id, limit)` | 取得課程公告 |
| `get_bulletin_list(course_id)` | 取得公告列表 |
| `get_bulletin_content(course_id, bulletin_id)` | 取得公告內容 |
| `get_org_bulletins` | 取得學校公告 |
| `get_homework(course_id)` | 取得作業列表（含截止時間、繳交狀態）|
| `get_activity_detail(course_id, activity_id)` | 取得學習活動詳細（含附件下載資訊）|
| `get_submission_status(course_id, activity_id)` | 查詢作業繳交狀態 |
| `get_score(course_id)` | 取得成績摘要 |
| `get_courseware_list(course_id)` | 取得教材列表 |
| `get_dashboard` | 取得首頁動態 |
| `get_all_course_summary` | 取得所有課程摘要 |
| `search_public_courses(keyword)` | 搜尋公開課程 |
| `get_server_info` | 取得伺服器資訊 |

### 📥 下載工具

| 工具 | 功能 |
|------|------|
| `get_reference_url(reference_id)` | 取得參考資料下載 URL |
| `download_reference(reference_id, save_dir, filename)` | 下載參考資料 |
| `get_upload_url(upload_id)` | 取得檔案下載 URL |
| `download_attachment(upload_id, save_dir)` | 下載附件 |

---

## 📖 常用示例

### 啟動 MCP Server

```bash
# 在專案目錄下執行
python tronclass_mcp.py
```

### 檢查 MCP 伺服器狀態

```bash
npx -y mcporter list
```

### 自動登入 + 取得課程列表

```bash
# Step 1: 登入
npx -y mcporter call tronclass.login --args '{"username": "YOUR_USERNAME", "password": "YOUR_PASSWORD", "org_keyword": "輔仁大學"}'

# Step 2: 取得課程列表
npx -y mcporter call tronclass.get_courses
```

### 查詢作業

```bash
# 取得課程列表（含 ID）
npx -y mcporter call tronclass.get_courses

# 查詢特定課程的作業
npx -y mcporter call tronclass.get_homework '{"course_id": "382866"}'
```

### 查看公告

```bash
# 取得公告列表
npx -y mcporter call tronclass.get_announcements '{"course_id": "382866", "limit": 10}'
```

### 取得首頁動態

```bash
# 一次取得通知、待辦、學校公告
npx -y mcporter call tronclass.get_dashboard
```

### 下載附件

```bash
# Step 1: 取得活動詳細（包含下載 ID）
npx -y mcporter call tronclass.get_activity_detail '{"course_id": "382866", "activity_id": "2948328"}'

# Step 2: 下載參考資料（使用輸出的下載ID）
npx -y mcporter call tronclass.download_reference --args '{"reference_id": "29855250", "filename": "org03h練習.docx"}'
```

---

## 📦 需求與安裝

### 系統需求

- Python 3.11+
- Node.js（用於 `npx -y mcporter`）

### 方案 A：使用 venv + pip

```bash
# 1) 建立虛擬環境
python -m venv venv

# 2) 啟用虛擬環境
source venv/bin/activate

# 3) 安裝依賴
pip install -r requirements.txt
```

### 方案 B：使用 conda

```bash
# 1) 建立 conda 環境（建議 Python 3.11 或以上）
conda create -n tronclass-control python=3.11 -y

# 2) 啟用環境
conda activate tronclass-control

# 3) 安裝依賴
pip install -r requirements.txt
```

---

## 📁 檔案位置

- MCP Server: `tronclass_mcp.py`（專案目錄下）
- 預設下載目錄: `/tmp/tronclass_downloads/`

---

## ⚠️ 免責聲明

本專案僅供學術研究、個人學習與合法授權之自動化測試用途。

使用本工具前，請先確認並遵守：

- 你所屬學校或機構的資訊安全政策
- TronClass 平臺使用條款與相關法規
- 你對帳號、密碼、Session、JWT 與下載資料的保護責任

本專案作者不保證任何功能的可用性、正確性或持續相容性，亦不對以下情況負責：

- 因不當使用導致之帳號停權、資料遺失、服務中斷或其他損害
- 因平臺 API 變更、封鎖或政策調整造成之功能失效
- 因憑證外洩、環境設定錯誤或第三方操作造成的任何風險

若你不同意上述條件，請勿使用本專案。
