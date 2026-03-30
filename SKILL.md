---
name: tronclass-control
description: 自動化操作 TronClass 學習平臺。查課程、查作業、下載教材、查成績。當使用者需要查詢學校功課或課程資料時使用。
---

# TronClass MCP Skill

透過 mcporter 呼叫 TronClass MCP Server，自動化操作 TronClass 學習平臺。

## ⚙️ 設定

### 1. 安裝依賴

```bash
pip install anyio mcp requests
```

### 2. 啟動 MCP Server

```bash
# 在專案目錄下執行（需要 Python 環境）
python tronclass_mcp.py
```

Server 會在背景執行，預設 port 8001。

### 3. 設定 mcporter

在 `mcporter.json` 加入：

```json
{
  "mcpServers": {
    "tronclass": {
      "command": "/path/to/python",
      "args": ["/path/to/tronclass_mcp.py"],
      "cwd": "/path/to/tronclass_control"
    }
  }
}
```

---

## 📌 重要：mcporter 參數格式

**TronClass MCP 工具需要使用 `--args` 標誌傳遞 JSON 參數！**

❌ 錯誤：
```bash
npx -y mcporter call tronclass.get_announcements '{"course_id": "382866", "limit": 10}'
```

✅ 正確：
```bash
npx -y mcporter call tronclass.get_announcements --args '{"course_id": "382866", "limit": 10}'
```

---

## 🛠️ MCP Server 工具列表

### 🔐 登入工具

| 工具 | 功能 |
|------|------|
| `login(username, password, org_keyword)` | 登入 TronClass（**不需要驗證碼**）|
| `get_profile` | 取得個人資料 |
| `check_connection` | 測試 API 連線 |
| `logout` | 登出並清除 Session |

### 🎓 課程工具

| 工具 | 功能 |
|------|------|
| `get_courses` | 取得課程列表（含 ID）|
| `get_course_details(course_id)` | 取得課程詳細資訊 |
| `get_announcements(course_id, limit?)` | 取得課程公告 |
| `get_bulletin_list(course_id)` | 取得公告列表 |
| `get_bulletin_content(course_id, bulletin_id)` | 取得公告內容 |
| `get_org_bulletins` | 取得學校公告 |

### 📝 作業工具

| 工具 | 功能 |
|------|------|
| `get_homework(course_id)` | 取得作業列表（含截止時間、繳交狀態）|
| `get_homework_with_grades(course_id)` | 取得作業列表（含個別作業成績）|
| `get_activity_detail(course_id, activity_id)` | 取得學習活動詳細（含附件下載資訊）|
| `get_submission_status(course_id, activity_id)` | 查詢作業繳交狀態 |

### 📊 成績工具

| 工具 | 功能 |
|------|------|
| `get_score(course_id)` | 取得成績摘要 |

### 📚 教材工具

| 工具 | 功能 |
|------|------|
| `get_courseware_list(course_id)` | 取得教材列表 |

### 📥 下載工具

| 工具 | 功能 |
|------|------|
| `get_reference_url(reference_id)` | 取得參考資料下載 URL |
| `download_reference(reference_id, save_dir, filename)` | 下載參考資料 |
| `get_upload_url(upload_id)` | 取得檔案下載 URL |
| `download_attachment(upload_id, save_dir)` | 下載附件 |

### 📱 其他工具

| 工具 | 功能 |
|------|------|
| `get_dashboard` | 取得首頁動態（通知、待辦、學校公告）|
| `get_all_course_summary` | 取得所有課程摘要 |
| `search_public_courses(keyword)` | 搜尋公開課程 |
| `get_server_info` | 取得伺服器資訊 |

---

## 📖 常用工作流程

### 測試連線

```bash
# 檢查是否已登入
npx -y mcporter call tronclass.check_connection --config /path/to/mcporter.json
```

### 登入（首次使用）

```bash
npx -y mcporter call tronclass.login \
  --args '{"username": "YOUR_USERNAME", "password": "YOUR_PASSWORD", "org_keyword": "輔仁大學"}' \
  --config /path/to/mcporter.json
```

> 💡 登入成功後 Session 會自動儲存，之後不需要再登入

### 取得課程列表

```bash
npx -y mcporter call tronclass.get_courses --config /path/to/mcporter.json
```

### 查看公告

```bash
# 使用 --args 傳遞參數
npx -y mcporter call tronclass.get_announcements \
  --args '{"course_id": "382866", "limit": 10}' \
  --config /path/to/mcporter.json
```

### 查詢作業

```bash
# 取得作業列表（不含成績）
npx -y mcporter call tronclass.get_homework \
  --args '{"course_id": "382866"}' \
  --config /path/to/mcporter.json

# 取得作業列表（含成績）
npx -y mcporter call tronclass.get_homework_with_grades \
  --args '{"course_id": "382866"}' \
  --config /path/to/mcporter.json
```

### 取得首頁動態

```bash
# 一次取得通知、待辦、學校公告
npx -y mcporter call tronclass.get_dashboard --config /path/to/mcporter.json
```

### 下載附件

```bash
# Step 1: 取得活動詳細（包含下載 ID）
npx -y mcporter call tronclass.get_activity_detail \
  --args '{"course_id": "382866", "activity_id": "2948328"}' \
  --config /path/to/mcporter.json

# Step 2: 下載參考資料（使用輸出的下載ID）
npx -y mcporter call tronclass.download_reference \
  --args '{"reference_id": "29855250", "filename": "exercise.docx"}' \
  --config /path/to/mcporter.json
```

---

## 📁 檔案結構

```
tronclass_control/
├── tronclass_mcp.py      # MCP Server 主程式
├── tronclass_api.py      # TronClass API 包裝
└── SKILL.md             # 本說明文件
```

## 🔧 常見問題

### Q: 工具呼叫出現 "Field required" 錯誤？

A: 確認使用 `--args` 標誌傳遞參數：
```bash
# 錯誤
npx -y mcporter call tronclass.get_announcements '{"course_id": "xxx"}'

# 正確
npx -y mcporter call tronclass.get_announcements --args '{"course_id": "xxx"}'
```

### Q: Session 過期需要重新登入？

A: 使用 `logout` 清除 Session，然後重新 `login`：
```bash
npx -y mcporter call tronclass.logout --config /path/to/mcporter.json
```

### Q: MCP Server 無法啟動？

A: 確認已安裝依賴：
```bash
pip install anyio mcp requests
```
