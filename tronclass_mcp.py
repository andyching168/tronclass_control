#!/usr/bin/env python3
"""
TronClass MCP Server
使用純 API 方式（tronclass_api）取代 Playwright 瀏覽器自動化

基於 server.py 的接口，使用 tronclass_api.py 的實現方式
"""

import json
import subprocess
import warnings

warnings.filterwarnings("ignore", message="Unverified HTTPS request")
warnings.filterwarnings(
    "ignore", message=r"urllib3 .* doesn't match a supported version!"
)

import anyio


class _GenericCreateMemoryStream:
    """Allow anyio.create_memory_object_stream[T](...) style used by newer MCP."""

    def __init__(self, fn):
        self._fn = fn

    def __call__(self, *args, **kwargs):
        return self._fn(*args, **kwargs)

    def __getitem__(self, item_type):
        def _factory(max_buffer_size=0):
            return self._fn(max_buffer_size, item_type=item_type)

        return _factory


if not hasattr(anyio.create_memory_object_stream, "__getitem__"):
    anyio.create_memory_object_stream = _GenericCreateMemoryStream(
        anyio.create_memory_object_stream
    )

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("TronClassAPI")

from tronclass_api import TronClassAPI
import os
import requests

_api_instance = None
SESSION_FILE = os.path.expanduser("~/.tronclass_session.json")


def _save_session(api: TronClassAPI):
    """Save session state to file"""
    try:
        session_data = {
            "cookies": dict(api.session.cookies),
            "org_info": api.org_info,
            "org_id": api.org_id,
            "user_id": api.user_id,
            "session_token": api.session_token,
            "jwt_token": api.jwt_token,
            "base_url": api.base_url,
        }
        with open(SESSION_FILE, "w") as f:
            json.dump(session_data, f)
    except Exception as e:
        print(f"Warning: Failed to save session: {e}")


def _load_session() -> dict:
    """Load session state from file, returns None if invalid"""
    if not os.path.exists(SESSION_FILE):
        return None
    try:
        with open(SESSION_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return None


def _restore_api(session_data: dict) -> TronClassAPI:
    """Restore API instance from saved session"""
    api = TronClassAPI()
    api.org_info = session_data.get("org_info")
    api.org_id = session_data.get("org_id")
    api.user_id = session_data.get("user_id")
    api.session_token = session_data.get("session_token")
    api.jwt_token = session_data.get("jwt_token")
    api.base_url = session_data.get("base_url")

    # Restore cookies
    cookies = session_data.get("cookies", {})
    for name, value in cookies.items():
        api.session.cookies.set(name, value)

    # IMPORTANT: Restore X-SESSION-ID header (this was missing and causing API calls to fail!)
    if api.session_token:
        api.session.headers.update({"X-SESSION-ID": api.session_token})

    return api


def get_api():
    global _api_instance
    if _api_instance is None:
        # Try to restore from saved session
        session_data = _load_session()
        if session_data and session_data.get("user_id"):
            _api_instance = _restore_api(session_data)
        else:
            _api_instance = TronClassAPI()
    return _api_instance


# ───────── 登入工具 ─────────


@mcp.tool()
def check_connection() -> str:
    """測試 API 連線是否正常，並顯示目前登入狀態"""
    try:
        api = get_api()
        if api.user_id:
            return f"✅ 已登入 | User ID: {api.user_id} | 學校: {api.org_info.get('orgName') if api.org_info else 'N/A'}"
        else:
            return "⚠️ 未登入，請先呼叫 login()"
    except Exception as e:
        return f"❌ 連線錯誤：{e}"


@mcp.tool()
def logout() -> str:
    """登出並清除已儲存的 Session"""
    global _api_instance
    try:
        if os.path.exists(SESSION_FILE):
            os.remove(SESSION_FILE)
        _api_instance = TronClassAPI()
        return "✅ 已登出，Session 已清除"
    except Exception as e:
        return f"❌ 登出失敗：{e}"


@mcp.tool()
def login(username: str, password: str, org_keyword: str = "天主教輔仁大學") -> str:
    """
    登入 TronClass

    Args:
        username: 學號或帳號
        password: 密碼
        org_keyword: 學校關鍵字（預設：天主教輔仁大學）
    """
    try:
        api = get_api()
        api.search_org(org_keyword)
        api.login(username, password)

        # Save session to file for persistence across calls
        _save_session(api)

        return (
            f"✅ 登入成功！\n"
            f"使用者：{username}\n"
            f"學校：{api.org_info.get('orgName') if api.org_info else 'Unknown'}\n"
            f"User ID：{api.user_id}\n"
            f"Session：{api.session_token[:30]}..."
        )
    except Exception as e:
        return f"❌ 登入失敗：{e}"


@mcp.tool()
def get_profile() -> str:
    """取得個人資料"""
    try:
        api = get_api()
        if not api.user_id:
            return "❌ 尚未登入，請先呼叫 login()"

        data = api.get_profile()
        if not data:
            return "❌ 無法取得個人資料"

        name = data.get("name", "N/A")
        email = data.get("email", "N/A")
        user_no = data.get("user_no", "N/A")
        dept = data.get("department", {})
        dept_name = dept.get("name", "N/A") if isinstance(dept, dict) else "N/A"

        return (
            f"✅ 個人資料\n"
            f"姓名：{name}\n"
            f"學號：{user_no}\n"
            f"Email：{email}\n"
            f"系所：{dept_name}"
        )
    except Exception as e:
        return f"❌ 取得個人資料失敗：{e}"


# ───────── 課程工具 ─────────


@mcp.tool()
def get_courses() -> str:
    """取得所有課程名稱與 ID"""
    try:
        api = get_api()
        if not api.user_id:
            return "❌ 尚未登入"

        data = api.get_my_courses()
        if not data or not isinstance(data, dict):
            return "❌ 無法取得課程資料"

        courses = data.get("courses", [])
        if not courses:
            return "❌ 找不到任何課程"

        lines = []
        for c in courses:
            cid = c.get("id")
            name = c.get("name", "Unknown")
            lines.append(f"{name} → course_id={cid}")

        return "✅ 課程列表（附 ID）：\n\n" + "\n".join(lines)
    except Exception as e:
        return f"❌ 取得課程失敗：{e}"


@mcp.tool()
def get_course_details(course_id: str) -> str:
    """
    取得課程詳細資訊

    Args:
        course_id: 課程 ID（例如 '382866'）
    """
    try:
        api = get_api()
        if not api.user_id:
            return "❌ 尚未登入"

        data = api.get_course_details(course_id)
        if not data:
            return f"❌ 無法取得課程 {course_id} 的詳細資訊"

        name = data.get("name", "N/A")
        code = data.get("course_code", "N/A")
        mode = data.get("teaching_mode", "N/A")
        instructors = data.get("instructors", [])
        instructor_names = (
            ", ".join([i.get("name", "") for i in instructors])
            if instructors
            else "N/A"
        )

        return (
            f"✅ 課程詳細：{name}\n"
            f"課程代碼：{code}\n"
            f"授課方式：{mode}\n"
            f"授課教師：{instructor_names}"
        )
    except Exception as e:
        return f"❌ 取得課程詳細失敗：{e}"


# ───────── 公告工具 ─────────


@mcp.tool()
def get_announcements(course_id: str, limit: int = 10) -> str:
    """
    取得指定課程的公告列表

    Args:
        course_id: 課程 ID（用 get_courses 取得，例如 '382863'）
        limit: 最多顯示幾則公告（預設 10）
    """
    try:
        api = get_api()
        if not api.user_id:
            return "❌ 尚未登入"

        data = api.get_announcements(course_id, limit)
        if not data:
            return f"❌ 無法取得課程 {course_id} 的公告"

        bulletins = data.get("bulletins", data.get("list", []))
        if not bulletins:
            return f"課程 {course_id} 目前沒有公告"

        lines = []
        for b in bulletins[:limit]:
            title = b.get("title", "Untitled")
            created = b.get("created_at", "")[:10]
            lines.append(f"[{created}] {title}")

        return "✅ 公告列表：\n\n" + "\n".join(lines)
    except Exception as e:
        return f"❌ 取得公告失敗：{e}"


@mcp.tool()
def get_bulletin_list(course_id: str) -> str:
    """
    取得指定課程的公告列表及各公告的附件下載連結

    Args:
        course_id: 課程 ID（用 get_courses 取得）
    """
    try:
        api = get_api()
        if not api.user_id:
            return "❌ 尚未登入"

        data = api.get_announcements(course_id, limit=20)
        if not data:
            return f"❌ 無法取得公告列表"

        bulletins = data.get("bulletins", data.get("list", []))
        if not bulletins:
            return f"課程 {course_id} 目前沒有公告"

        lines = []
        for b in bulletins:
            title = b.get("title", "Untitled")
            bid = b.get("id", "")
            lines.append(f"[{bid}] {title}")

        result = "✅ 公告列表：\n\n" + "\n".join(lines)
        result += f"\n\n（如需查看特定公告內容，請使用 get_bulletin_content）"
        return result
    except Exception as e:
        return f"❌ 取得公告失敗：{e}"


@mcp.tool()
def get_bulletin_content(course_id: str, bulletin_id: str) -> str:
    """
    取得特定公告的完整內容

    Args:
        course_id: 課程 ID
        bulletin_id: 公告 ID
    """
    try:
        api = get_api()
        if not api.user_id:
            return "❌ 尚未登入"

        data = api.get_bulletin_content(course_id, bulletin_id)
        if not data:
            return f"❌ 無法取得公告 {bulletin_id} 的內容"

        title = data.get("title", "N/A")
        content = data.get("content", "N/A")

        import re

        content = re.sub(r"<[^>]+>", "", content)
        content = content.strip()

        return f"✅ 公告內容：{title}\n\n{content[:2000]}"
    except Exception as e:
        return f"❌ 取得公告內容失敗：{e}"


@mcp.tool()
def get_org_bulletins() -> str:
    """取得學校/組織公告"""
    try:
        api = get_api()
        if not api.user_id:
            return "❌ 尚未登入"

        data = api.get_org_bulletins()
        if not data:
            return "❌ 無法取得學校公告"

        bulletins = data.get("bulletins", [])
        if not bulletins:
            return "目前沒有學校公告"

        lines = []
        for b in bulletins[:10]:
            title = b.get("title", "Untitled")
            lines.append(f"• {title}")

        return "✅ 學校公告：\n\n" + "\n".join(lines)
    except Exception as e:
        return f"❌ 取得學校公告失敗：{e}"


# ───────── 作業工具 ─────────


@mcp.tool()
def get_homework(course_id: str) -> str:
    """
    取得指定課程的作業列表（含成績）

    Args:
        course_id: 課程 ID（用 get_courses 取得，例如 '382863'）
    """
    try:
        api = get_api()
        if not api.user_id:
            return "❌ 尚未登入"

        data = api.get_homework_with_score(course_id)
        if not data:
            return f"❌ 無法取得課程 {course_id} 的作業"

        activities = data.get("homework_activities", data.get("list", []))
        if not activities:
            return f"課程 {course_id} 目前沒有作業"

        lines = []
        for hw in activities:
            title = hw.get("title", hw.get("name", "Untitled"))
            end_time = hw.get("end_time", "")
            if end_time:
                end_time = end_time[:16].replace("T", " ")
            else:
                end_time = "無期限"

            hw_id = hw.get("id")
            submission = api.get_student_submission(course_id, hw_id)
            status = "已繳" if submission and submission.get("created_at") else "未繳"

            # 優先讀取作業本身的 score 欄位
            score = hw.get("score")
            score_published = hw.get("score_published", False)
            
            if score is None and submission:
                # 作業本身沒分數，從繳交記錄讀取 final_score
                score = submission.get("final_score")

            if score is not None:
                if score_published:
                    lines.append(
                        f"• {title}\n  截止：{end_time} | 狀態：{status} | 成績：{score}"
                    )
                else:
                    lines.append(
                        f"• {title}\n  截止：{end_time} | 狀態：{status} | 成績：{score} (尚未公布)"
                    )
            else:
                lines.append(
                    f"• {title}\n  截止：{end_time} | 狀態：{status} | 成績：尚未評分"
                )

        return "✅ 作業列表：\n\n" + "\n".join(lines)
    except Exception as e:
        return f"❌ 取得作業失敗：{e}"


@mcp.tool()
def get_activity_detail(course_id: str, activity_id: str) -> str:
    """
    取得指定學習活動（作業/教材）的詳細內容及附件下載連結

    Args:
        course_id: 課程 ID（例如 '382866'）
        activity_id: 學習活動 ID（例如 '2948328'）
    """
    try:
        api = get_api()
        if not api.user_id:
            return "❌ 尚未登入"

        data = api.get_activity_detail(activity_id)
        if not data:
            return f"❌ 無法取得活動 {activity_id} 的詳細資訊"

        title = data.get("title", "N/A")
        desc = data.get("description", "")

        import re

        desc = re.sub(r"<[^>]+>", "", desc).strip()

        uploads = data.get("uploads", [])
        attachments = []
        if uploads:
            for u in uploads:
                fname = u.get("name", "Unknown")
                ref_id = u.get("reference_id", "")
                upload_id = u.get("id", "")
                size = u.get("size", 0)
                if size:
                    size_str = f"{size / 1024:.1f}KB"
                else:
                    size_str = "N/A"
                attachments.append(f"• {fname} ({size_str})")
                if ref_id:
                    attachments.append(
                        f"  下載ID: {ref_id} (可用 download_reference 下載)"
                    )

        result = f"✅ 活動詳細：{title}\n\n"
        result += f"說明：{desc[:500] if desc else '無'}\n\n"

        if attachments:
            result += "📎 附件：\n" + "\n".join(attachments)
        else:
            result += "📎 此活動無附件"

        return result
    except Exception as e:
        return f"❌ 取得活動詳細失敗：{e}"


@mcp.tool()
def get_submission_status(course_id: str, activity_id: str) -> str:
    """
    查詢作業繳交狀態

    Args:
        course_id: 課程 ID
        activity_id: 作業活動 ID
    """
    try:
        api = get_api()
        if not api.user_id:
            return "❌ 尚未登入"

        data = api.get_student_submission(course_id, activity_id)
        if not data:
            return f"❌ 無法取得繳交狀態"

        submitted = data.get("created_at") is not None
        status = "✅ 已繳交" if submitted else "❌ 未繳交"
        created = data.get("created_at", "N/A")[:19] if submitted else "N/A"

        return f"作業 {activity_id} 繳交狀態：{status}\n繳交時間：{created}"
    except Exception as e:
        return f"❌ 查詢繳交狀態失敗：{e}"


# ───────── 成績工具 ─────────


@mcp.tool()
def get_score(course_id: str) -> str:
    """
    取得指定課程的成績摘要

    Args:
        course_id: 課程 ID
    """
    try:
        api = get_api()
        if not api.user_id:
            return "❌ 尚未登入"

        activities = api.get_course_activities(course_id)
        if not activities:
            return f"❌ 無法取得課程 {course_id} 的成績資料"

        course_data = api.get_course_details(course_id)
        course_name = course_data.get("name", "Unknown") if course_data else "Unknown"

        result = f"✅ {course_name} 成績資訊\n\n"
        result += "（如需詳細成績，請使用網頁版查看完整成績頁面）\n"
        result += f"\nAPI 目前不提供詳細成績欄位，僅有活動完成狀態"

        return result
    except Exception as e:
        return f"❌ 取得成績失敗：{e}"


# ───────── 教材工具 ─────────


@mcp.tool()
def get_courseware_list(course_id: str) -> str:
    """
    取得指定課程的教材列表

    Args:
        course_id: 課程 ID
    """
    try:
        api = get_api()
        if not api.user_id:
            return "❌ 尚未登入"

        activities = api.get_course_activities(course_id)
        if not activities:
            return f"❌ 無法取得課程 {course_id} 的教材"

        course_data = api.get_course_details(course_id)
        course_name = course_data.get("name", "Unknown") if course_data else "Unknown"

        result = f"✅ {course_name} 教材列表\n\n"
        result += "（如需完整教材列表，建議使用網頁版查看）\n"
        result += f"\n共 {len(activities)} 個學習活動"

        return result
    except Exception as e:
        return f"❌ 取得教材失敗：{e}"


# ───────── 首頁動態工具 ─────────


@mcp.tool()
def get_dashboard() -> str:
    """
    取得 TronClass 首頁動態，包含：最新動態（成績/公告/作業）、待辦事項、最新公告列表。
    """
    try:
        api = get_api()
        if not api.user_id:
            return "❌ 尚未登入"

        result = "✅ TronClass 首頁動態\n\n"

        notifications = api.get_all_notifications(limit=10)
        if notifications and isinstance(notifications, dict):
            items = notifications.get("notifications", [])
            if items:
                result += "📡 最新通知：\n"
                for n in items[:5]:
                    ntype = n.get("type", "unknown")
                    payload = n.get("payload", {})
                    title = payload.get("activity_title") or payload.get(
                        "bulletin_title", "N/A"
                    )
                    course = payload.get("course_name", "")
                    result += f"  • [{ntype}] {title} ({course})\n"

        todos = api.get_todos()
        if todos and isinstance(todos, dict):
            todo_list = todos.get("todo_list", [])
            if todo_list:
                result += "\n📋 待辦事項：\n"
                for t in todo_list[:5]:
                    result += f"  • {t.get('title', 'N/A')}\n"
            else:
                result += "\n📋 待辦事項：無\n"

        org_bulletins = api.get_org_bulletins()
        if org_bulletins:
            result += "\n📢 最新學校公告：\n"
            if isinstance(org_bulletins, dict):
                bulletins = org_bulletins.get("bulletins", [])
                for b in bulletins[:3]:
                    result += f"  • {b.get('title', 'N/A')}\n"

        return result
    except Exception as e:
        return f"❌ 取得首頁動態失敗：{e}"


@mcp.tool()
def get_all_course_summary() -> str:
    """
    一次把所有課程的公告、作業狀態整合成一份摘要，方便快速掌握所有課程狀況。
    """
    try:
        api = get_api()
        if not api.user_id:
            return "❌ 尚未登入"

        api.get_all_course_summary()
        return "✅ 課程摘要已產生（見上方輸出）"
    except Exception as e:
        return f"❌ 取得課程摘要失敗：{e}"


# ───────── 工具函式 ─────────


@mcp.tool()
def search_public_courses(keyword: str = "") -> str:
    """
    搜尋公開課程

    Args:
        keyword: 搜尋關鍵字
    """
    try:
        api = get_api()
        if not api.user_id:
            return "❌ 尚未登入"

        data = api.get_public_courses(keyword=keyword)
        if not data:
            return "❌ 無法搜尋課程"

        courses = data.get("courses", data.get("list", []))
        if not courses:
            return f"找不到符合「{keyword}」的課程"

        lines = []
        for c in courses[:10]:
            name = c.get("name", "Unknown")
            cid = c.get("id", "")
            instructor = c.get("instructors", [])
            instructors = (
                ", ".join([i.get("name", "") for i in instructor])
                if instructor
                else "N/A"
            )
            lines.append(f"• {name}\n  ID: {cid} | 教師: {instructors}")

        return f"✅ 搜尋結果：\n\n" + "\n\n".join(lines)
    except Exception as e:
        return f"❌ 搜尋失敗：{e}"


@mcp.tool()
def get_server_info() -> str:
    """取得伺服器資訊"""
    try:
        api = get_api()
        version = api.get_version()
        server_time = api.get_server_time()

        if version:
            import datetime

            try:
                st = int(server_time) / 1000
                dt = datetime.datetime.fromtimestamp(st)
                server_time_str = dt.strftime("%Y-%m-%d %H:%M:%S")
            except:
                server_time_str = server_time

        return f"✅ 伺服器資訊\n版本：{version}\n伺服器時間：{server_time_str}"
    except Exception as e:
        return f"❌ 取得伺服器資訊失敗：{e}"


# ───────── 下載工具 ─────────


@mcp.tool()
def get_upload_url(upload_id: str) -> str:
    """
    取得檔案下載 URL

    Args:
        upload_id: 上傳檔案 ID（從活動或公告中取得）
    """
    try:
        api = get_api()
        if not api.user_id:
            return "❌ 尚未登入"

        path = f"/api/uploads/{upload_id}/url"
        resp = api._get_json("GET", path)
        if not resp:
            return f"❌ 無法取得檔案 {upload_id} 的下載 URL"

        url = resp.get("url") if isinstance(resp, dict) else resp
        return f"✅ 檔案下載 URL：\n\n{url}"
    except Exception as e:
        return f"❌ 取得下載 URL 失敗：{e}"


@mcp.tool()
def download_attachment(
    upload_id: str, save_dir: str = "/tmp/tronclass_downloads"
) -> str:
    """
    下載 TronClass 的附件到本地

    Args:
        upload_id: 上傳檔案 ID（從 get_activity_detail 或 get_bulletin_content 取得）
        save_dir: 儲存目錄（預設 /tmp/tronclass_downloads/）
    """
    try:
        import os

        api = get_api()
        if not api.user_id:
            return "❌ 尚未登入"

        os.makedirs(save_dir, exist_ok=True)

        path = f"/api/uploads/{upload_id}/url"
        resp = api._get_json("GET", path)
        if not resp:
            return f"❌ 無法取得檔案 {upload_id} 的下載 URL"

        url = resp.get("url") if isinstance(resp, dict) else None
        if not url:
            return f"❌ 無法取得下載 URL"

        filename = resp.get("filename") if isinstance(resp, dict) else None
        if not filename:
            filename = f"download_{upload_id}"

        download_url = f"{api.base_url}{url}" if url.startswith("/") else url

        download_resp = api.session.get(download_url, verify=False, stream=True)
        if download_resp.status_code != 200:
            return f"❌ 下載失敗，HTTP {download_resp.status_code}"

        final_path = os.path.join(save_dir, filename)
        with open(final_path, "wb") as f:
            for chunk in download_resp.iter_content(chunk_size=8192):
                f.write(chunk)

        size = os.path.getsize(final_path)
        return f"✅ 下載完成！\n儲存至：{final_path}\n檔案大小：{size} bytes"
    except Exception as e:
        return f"❌ 下載失敗：{e}"


@mcp.tool()
def get_reference_url(reference_id: str) -> str:
    """
    取得參考資料的下載 URL

    Args:
        reference_id: 參考資料 ID
    """
    try:
        api = get_api()
        if not api.user_id:
            return "❌ 尚未登入"

        url = f"{api.base_url}/api/uploads/reference/{reference_id}/blob"
        return f"✅ 參考資料下載 URL：\n\n{url}"
    except Exception as e:
        return f"❌ 取得參考 URL 失敗：{e}"


@mcp.tool()
def download_reference(
    reference_id: str, save_dir: str = "/tmp/tronclass_downloads", filename: str = None
) -> str:
    """
    下載參考資料

    Args:
        reference_id: 參考資料 ID
        save_dir: 儲存目錄（預設 /tmp/tronclass_downloads/）
        filename: 自訂檔案名稱（可選）
    """
    try:
        import os

        api = get_api()
        if not api.user_id:
            return "❌ 尚未登入"

        os.makedirs(save_dir, exist_ok=True)

        download_url = f"{api.base_url}/api/uploads/reference/{reference_id}/blob"

        if not filename:
            filename = f"reference_{reference_id}"

        final_path = os.path.join(save_dir, filename)

        download_resp = api.session.get(download_url, verify=False, stream=True)
        if download_resp.status_code != 200:
            return f"❌ 下載失敗，HTTP {download_resp.status_code}"

        with open(final_path, "wb") as f:
            for chunk in download_resp.iter_content(chunk_size=8192):
                f.write(chunk)

        size = os.path.getsize(final_path)
        return f"✅ 下載完成！\n儲存至：{final_path}\n檔案大小：{size} bytes"
    except Exception as e:
        return f"❌ 下載失敗：{e}"


if __name__ == "__main__":
    mcp.run(transport="stdio")
