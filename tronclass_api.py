#!/usr/bin/env python3
"""
TronClass API Client
Based on HAR analysis of the TronClass Android app
"""

import requests
import warnings
import json
from urllib.parse import quote

warnings.filterwarnings("ignore", message="Unverified HTTPS request")


class TronClassAPI:
    BASE_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) TronClass/common",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-TW,zh-Hant;q=0.9",
        "X-LC-Id": "s0QbLDG5u6IrBSx9dC4yFiLr-gzGzoHsz",
        "X-LC-Key": "jEivEsoel0KxBdX4gDuO5Sak",
    }

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(self.BASE_HEADERS)
        self.org_info = None
        self.org_id = None
        self.user_id = None
        self.session_token = None
        self.jwt_token = None
        self.base_url = None

    def _request(self, method, path, base_url=None, **kwargs):
        """Make HTTP request with session headers"""
        url = f"{base_url or self.base_url}{path}"
        resp = self.session.request(method, url, verify=False, **kwargs)
        return resp

    def _get_json(self, method, path, base_url=None, **kwargs):
        """Make request and return JSON"""
        resp = self._request(method, path, base_url, **kwargs)
        if resp.status_code >= 400:
            print(f"    Error {resp.status_code}: {resp.text[:200]}")
            return None
        try:
            return resp.json()
        except:
            return resp.text

    def search_org(self, keyword="天主教輔仁大學"):
        """Search for organization"""
        print(f"[1] Searching org: {keyword}")
        url = f"https://api-org.tronclass.com.tw/orgs?keywords={quote(keyword)}"
        resp = self.session.get(url, verify=False)
        resp.raise_for_status()

        data = resp.json()
        if not data.get("results"):
            raise Exception("No org found")

        self.org_info = data["results"][0]
        self.org_id = self.org_info["id"]
        self.base_url = self.org_info["apiUrl"]

        print(f"    Found: {self.org_info['orgName']}")
        print(f"    Org ID: {self.org_id}")
        print(f"    API URL: {self.base_url}")
        return self.org_info

    def login(self, username, password):
        """CAS Login flow"""
        print(f"[2] CAS Login for user: {username}")

        # Step 1: Create TGT
        url = f"{self.base_url}/cas/v1/tickets"
        data = {"username": username, "password": password}
        resp = self.session.post(url, data=data, verify=False)

        if resp.status_code != 201:
            raise Exception(
                f"TGT creation failed: {resp.status_code} - {resp.text[:200]}"
            )

        import re

        match = re.search(r"TGT-[\w\.-]+", resp.text)
        if not match:
            raise Exception("Could not extract TGT from response")
        tgt = match.group(0)
        print(f"    TGT: {tgt[:40]}...")

        # Step 2: Get Service Ticket
        # Use the URL from Location header but convert http to https
        location = resp.headers.get("location", "")
        if location:
            tgt_url = location.replace("http://", "https://")
        else:
            # Fallback: construct URL with https
            tgt_url = f"{self.base_url}/cas/v1/tickets/{tgt}"

        service = f"{self.base_url}/api/cas-login"
        data = {"service": service}

        # Use https URL directly for TGT validation
        resp = self.session.post(tgt_url, data=data, verify=False)

        if resp.status_code != 200:
            raise Exception(
                f"Service ticket failed: {resp.status_code} - {resp.text[:200]}"
            )
        service_ticket = resp.text.strip()
        print(f"    Service Ticket: {service_ticket[:40]}...")

        # Step 3: CAS Login
        url = f"{self.base_url}/api/cas-login?ticket={service_ticket}"
        resp = self.session.get(url, verify=False)

        if resp.status_code != 200:
            raise Exception(f"CAS login failed: {resp.status_code}")

        result = resp.json()
        self.user_id = result.get("user_id")
        self.session_token = resp.cookies.get("session") or resp.headers.get(
            "X-SESSION-ID"
        )

        print(f"    User ID: {self.user_id}")
        print(
            f"    Session: {self.session_token[:40]}..."
            if self.session_token
            else "    Session: N/A"
        )

        # Update session headers
        self.session.headers.update(
            {
                "X-SESSION-ID": self.session_token,
                "X-Requested-With": "XMLHttpRequest",
                "Origin": "capacitor://localhost",
            }
        )

        return result

    def get_jwt(self):
        """Get JWT token"""
        print(f"[3] Getting JWT token")
        data = self._get_json("GET", "/api/jwt")
        if data and "jwt" in data:
            self.jwt_token = data["jwt"]
            print(f"    JWT: {self.jwt_token[:40]}...")
        return self.jwt_token

    def get_profile(self):
        """Get user profile"""
        print(f"[4] Getting user profile")
        data = self._get_json("GET", "/api/profile")
        if data and isinstance(data, dict):
            print(f"    Name: {data.get('name')}")
            print(f"    Email: {data.get('email')}")
            print(f"    User No: {data.get('user_no')}")
            dept = data.get("department", {})
            if isinstance(dept, dict):
                print(f"    Department: {dept.get('name')}")
        return data

    def get_my_courses(self, page=1, page_size=10, sort="all", keyword=""):
        """Get user's enrolled courses"""
        print(f"[5] Getting my courses (page={page}, sort={sort})")
        path = f"/api/users/{self.user_id}/courses?page={page}&page_size={page_size}&sort={sort}&keyword={quote(keyword)}&normal=%7B%22version%22%3A7%2C%22apiVersion%22%3A%221.1.0%22%7D&conditions=%7B%22role%22%3A%5B%5D%2C%22semester_id%22%3A%5B%5D%2C%22academic_year_id%22%3A%5B%5D%2C%22status%22%3A%5B%22ongoing%22%5D%2C%22course_type%22%3A%5B%5D%2C%22effectiveness%22%3A%5B%5D%2C%22published%22%3A%5B%5D%2C%22display_studio_list%22%3Afalse%7D&fields=id%2Corg_id%2Cname%2Csecond_name%2Cstart_date%2Cend_date%2Cdepartment%28id%2Cname%29%2Cinstructors%28id%2Cemail%2Cname%29%2Cgrade%28name%29%2Cklass%28name%29%2Cacademic_year_id%2Csemester_id%2Ccover%2Clearning_mode%2Ccourse_attributes%28teaching_class_name%2Cdata%2Cgraduate_method%29%2Cpublic_scope%2Ccourse_type%2Ccourse_code%2Ccompulsory%2Ccredit%2Csecond_name%2Cteam_teachings%28id%2Cname%2Cemail%29%2Carchived%2Cshow_archive_course_tips%2Cauto_archive_course_date"
        data = self._get_json("GET", path)
        if data and isinstance(data, dict):
            courses = data.get("courses", [])
            if isinstance(courses, list):
                print(f"    Found {len(courses)} courses")
                for c in courses[:5]:
                    if isinstance(c, dict):
                        print(f"    - {c.get('name', 'Unknown')} ({c.get('id')})")
                if len(courses) > 5:
                    print(f"    ... and {len(courses) - 5} more")
        return data

    def get_course_details(self, course_id):
        """Get course details"""
        print(f"[6] Getting course details: {course_id}")
        path = f"/api/courses/{course_id}"
        data = self._get_json("GET", path)
        if data and isinstance(data, dict):
            print(f"    Name: {data.get('name')}")
            print(f"    Code: {data.get('course_code')}")
            print(f"    Teaching Mode: {data.get('teaching_mode')}")
        return data

    def get_course_bulletins(self, course_id):
        """Get course bulletins/notices"""
        print(f"[7] Getting course bulletins: {course_id}")
        path = f"/api/courses/{course_id}/bulletins"
        data = self._get_json("GET", path)
        if data and isinstance(data, dict):
            bulletins = data.get("bulletins", data.get("list", []))
            if isinstance(bulletins, list):
                print(f"    Found {len(bulletins)} bulletins")
                for b in bulletins[:3]:
                    if isinstance(b, dict):
                        print(f"    - {b.get('title', 'Untitled')}")
        return data

    def get_course_activities(self, course_id, page=1, page_size=10):
        """Get course activities (homework, exams, etc.)"""
        print(f"[8] Getting course activities: {course_id}")
        path = f"/api/courses/{course_id}/homework-activities?page={page}&page_size={page_size}"
        data = self._get_json("GET", path)
        if data and isinstance(data, dict):
            activities = data.get("list", [])
            if isinstance(activities, list):
                print(f"    Found {len(activities)} activities")
        return data

    def get_notifications(self, types=None, limit=6, offset=0):
        """Get notifications

        types: list of notification types like:
          - bulletin_created, bulletin_updated
          - exam_opened, exam_submission_info, etc.
          - homework_ended, homework_expiring, etc.
          - course_opening, course_started, etc.
        """
        if types is None:
            types = ["bulletin_created", "bulletin_updated"]

        print(f"[9] Getting notifications")
        types_str = "&".join(f"types={t}" for t in types)
        path = f"/ntf/users/{self.user_id}/notifications?limit={limit}&offset={offset}&additionalFields=unread_count&{types_str}"
        data = self._get_json("GET", path)
        if data and isinstance(data, dict):
            items = data.get("list", [])
            if isinstance(items, list):
                print(f"    Found {len(items)} notifications")
                for n in items[:3]:
                    if isinstance(n, dict):
                        print(f"    - {n.get('title', 'Untitled')}")
        return data

    def get_notification_unread_count(self, types=None):
        """Get notification unread count"""
        if types is None:
            types = ["bulletin_created", "bulletin_updated"]

        print(f"[10] Getting notification unread count")
        types_str = "&".join(f"types={t}" for t in types)
        path = f"/ntf/users/{self.user_id}/notifications/unread-count?{types_str}"
        data = self._get_json("GET", path)
        if data and isinstance(data, dict):
            print(f"    Unread count: {data.get('unread_count', 0)}")
        return data

    def get_semesters(self):
        """Get user's academic years and semesters"""
        print(f"[11] Getting semesters")
        path = "/api/my-semesters?fields=id,name,sort,academic_year_id,is_active,code"
        data = self._get_json("GET", path)
        if data and isinstance(data, dict):
            semesters = data.get("list", [])
            if isinstance(semesters, list):
                print(f"    Found {len(semesters)} semesters")
                for s in semesters[:3]:
                    if isinstance(s, dict):
                        print(f"    - {s.get('name')} (active: {s.get('is_active')})")
        return data

    def get_academic_years(self):
        """Get academic years"""
        print(f"[12] Getting academic years")
        data = self._get_json("GET", "/api/my-academic-years")
        if data and isinstance(data, dict):
            years = data.get("list", [])
            if isinstance(years, list):
                print(f"    Found {len(years)} years")
        return data

    def get_course_classifications(self):
        """Get course classifications"""
        print(f"[13] Getting course classifications")
        data = self._get_json("GET", "/api/course-classifications")
        if data:
            print(f"    Data: {str(data)[:200]}")
        return data

    def get_public_courses(
        self,
        page=1,
        page_size=10,
        keyword="",
        classification_ids="",
        course_status="",
        course_type="all",
    ):
        """Search public courses"""
        print(f"[14] Searching public courses")
        path = f"/api/courses/public?page={page}&page_size={page_size}&classification_ids={classification_ids}&course_status={course_status}&course_type={course_type}&keyword={quote(keyword)}"
        data = self._get_json("GET", path)
        if data and isinstance(data, dict):
            courses = data.get("list", [])
            if isinstance(courses, list):
                print(f"    Found {len(courses)} courses")
        return data

    def get_feature_toggles(self):
        """Get feature toggles"""
        print(f"[15] Getting feature toggles")
        data = self._get_json("GET", "/api/feature-toggles")
        if data:
            print(f"    Features: {str(data)[:200]}")
        return data

    def get_org_settings(self):
        """Get organization settings"""
        print(f"[16] Getting org settings")
        path = f"/api/orgs/{self.org_id}/org-settings"
        data = self._get_json("GET", path)
        if data and isinstance(data, dict):
            org_name = data.get("name") or (
                self.org_info.get("orgName") if self.org_info else "Unknown"
            )
            print(f"    Org name: {org_name}")
        return data

    def get_todos(self):
        """Get todos"""
        print(f"[17] Getting todos")
        data = self._get_json("GET", "/api/todos")
        if data:
            print(f"    Data: {str(data)[:200]}")
        return data

    def get_recently_visited_courses(self):
        """Get recently visited courses"""
        print(f"[18] Getting recently visited courses")
        data = self._get_json("GET", "/api/user/recently-visited-courses")
        if data and isinstance(data, dict):
            courses = data.get("list", [])
            if isinstance(courses, list):
                print(f"    Found {len(courses)} recently visited courses")
        return data

    def get_user_tags(self):
        """Get user tags"""
        print(f"[19] Getting user tags")
        data = self._get_json("GET", "/api/user/tags")
        if data and isinstance(data, dict):
            tags = data.get("list", [])
            if isinstance(tags, list):
                print(f"    Found {len(tags)} tags")
        return data

    def get_server_time(self):
        """Get server time"""
        print(f"[20] Getting server time")
        data = self._get_json("GET", "/d/server-time")
        if data:
            print(f"    Server time: {data}")
        return data

    def get_version(self):
        """Get server version"""
        print(f"[21] Getting server version")
        data = self._get_json("GET", "/d/version")
        if data:
            print(f"    Version: {data}")
        return data

    # ───────── 課程內容相關功能 ─────────

    def get_announcements(self, course_id, limit=10):
        """取得課程公告列表（包含標題、發布時間）

        Args:
            course_id: 課程 ID
            limit: 最大顯示公告數量
        """
        print(f"[A1] Getting announcements for course: {course_id}")
        path = f"/api/courses/{course_id}/bulletins"
        data = self._get_json("GET", path)
        if data and isinstance(data, dict):
            bulletins = data.get("bulletins", data.get("list", []))
            if isinstance(bulletins, list):
                print(f"    Found {len(bulletins)} bulletins")
                for b in bulletins[:limit]:
                    if isinstance(b, dict):
                        title = b.get("title", "Untitled")
                        created = b.get("created_at", "")[:10]
                        print(f"    - [{created}] {title}")
        return data

    def get_bulletin_content(self, course_id, bulletin_id):
        """取得特定公告的完整內容

        Args:
            course_id: 課程 ID
            bulletin_id: 公告 ID
        """
        print(f"[A2] Getting bulletin {bulletin_id} content")
        path = f"/api/courses/{course_id}/bulletins/{bulletin_id}"
        data = self._get_json("GET", path)
        if data and isinstance(data, dict):
            print(f"    Title: {data.get('title', 'N/A')}")
            print(f"    Content: {str(data.get('content', ''))[:200]}...")
        return data

    def get_homework(self, course_id, page=1, page_size=20):
        """取得課程作業列表（包含截止時間、繳交狀態）

        Args:
            course_id: 課程 ID
            page: 頁碼
            page_size: 每頁數量
        """
        print(f"[H1] Getting homework for course: {course_id}")
        path = f"/api/courses/{course_id}/homework-activities?page={page}&page_size={page_size}"
        data = self._get_json("GET", path)
        if data and isinstance(data, dict):
            activities = data.get("homework_activities", data.get("list", []))
            if isinstance(activities, list):
                print(f"    Found {len(activities)} homework activities")
                for hw in activities[:10]:
                    if isinstance(hw, dict):
                        title = hw.get("title", hw.get("name", "Untitled"))
                        end_time = (
                            hw.get("end_time", "")[:16]
                            if hw.get("end_time")
                            else "No deadline"
                        )
                        print(f"    - {title}")
                        print(f"      Deadline: {end_time}")
        return data

    def get_homework_with_score(self, course_id, page=1, page_size=20):
        """取得課程作業列表（包含截止時間、繳交狀態與成績）

        Args:
            course_id: 課程 ID
            page: 頁碼
            page_size: 每頁數量
        """
        print(f"[H1] Getting homework with scores for course: {course_id}")
        path = f"/api/courses/{course_id}/homework-activities?page={page}&page_size={page_size}"
        data = self._get_json("GET", path)
        if data and isinstance(data, dict):
            activities = data.get("homework_activities", data.get("list", []))
            if isinstance(activities, list):
                print(f"    Found {len(activities)} homework activities")
                for hw in activities[:10]:
                    if isinstance(hw, dict):
                        title = hw.get("title", hw.get("name", "Untitled"))
                        end_time = (
                            hw.get("end_time", "")[:16]
                            if hw.get("end_time")
                            else "No deadline"
                        )
                        hw_id = hw.get("id")
                        score = hw.get("score")
                        score_published = hw.get("score_published", False)

                        print(f"    - {title}")
                        print(f"      Deadline: {end_time}")

                        if score is not None and score_published:
                            print(f"      Score: {score}")
                        elif score is not None:
                            print(f"      Score: {score} (未公布)")
                        else:
                            print(f"      Score: 尚未評分")

                        submission = self.get_student_submission(course_id, hw_id)
                        if submission and submission.get("created_at"):
                            sub_score = submission.get("score")
                            if sub_score is not None:
                                print(f"      成績: {sub_score}")
        return data

    def get_activity_detail(self, activity_id):
        """取得學習活動（作業/教材）的詳細內容

        Args:
            activity_id: 活動 ID
        """
        print(f"[H2] Getting activity detail: {activity_id}")
        path = f"/api/activities/{activity_id}"
        data = self._get_json("GET", path)
        if data and isinstance(data, dict):
            print(f"    Title: {data.get('title', 'N/A')}")
            desc = data.get("description", data.get("data", {}).get("description", ""))
            print(f"    Description: {str(desc)[:150]}...")

            # Check for file uploads/attachments
            uploads = data.get("uploads", [])
            if uploads:
                print(f"    Attachments: {len(uploads)} files")
        return data

    def get_student_submission(self, course_id, activity_id):
        """取得學生的作業繳交記錄

        Args:
            course_id: 課程 ID
            activity_id: 作業活動 ID
        """
        print(f"[H3] Getting student submission for activity: {activity_id}")
        path = (
            f"/api/course/activities/{activity_id}/students/{self.user_id}/submission"
        )
        data = self._get_json("GET", path)
        if data and isinstance(data, dict):
            print(f"    Activity ID: {data.get('activity_id')}")
            print(f"    Created at: {data.get('created_at', 'N/A')}")
            submitted = data.get("created_at") is not None
            print(f"    Status: {'已繳交' if submitted else '未繳交'}")
        return data

    def get_submission_list(self, activity_id):
        """取得作業的繳交列表

        Args:
            activity_id: 作業活動 ID
        """
        print(f"[H4] Getting submission list for activity: {activity_id}")
        path = f"/api/activities/{activity_id}/students/{self.user_id}/submission_list"
        data = self._get_json("GET", path)
        if data and isinstance(data, dict):
            submissions = data.get("list", [])
            if isinstance(submissions, list):
                print(f"    Found {len(submissions)} submissions")
                for sub in submissions[:5]:
                    if isinstance(sub, dict):
                        print(
                            f"    - Activity {sub.get('activity_id')}: {sub.get('created_at', 'N/A')}"
                        )
        return data

    def get_makeup_record(self, course_id, activity_id):
        """取得作業補交記錄

        Args:
            course_id: 課程 ID
            activity_id: 作業活動 ID
        """
        print(f"[H5] Getting make-up record for activity: {activity_id}")
        path = f"/api/homework/{activity_id}/students/{self.user_id}/make-up-record"
        data = self._get_json("GET", path)
        if data is not None:
            print(f"    Make-up record: {data}")
        return data

    def get_resubmit_record(self, course_id, activity_id):
        """取得作業重交記錄

        Args:
            course_id: 課程 ID
            activity_id: 作業活動 ID
        """
        print(f"[H6] Getting resubmit record for activity: {activity_id}")
        path = f"/api/homework/{activity_id}/students/{self.user_id}/resubmit-record"
        data = self._get_json("GET", path)
        if data is not None:
            print(f"    Resubmit record: {data}")
        return data

    def get_course_enrollment(self, course_id, fields="roles,aliases,group_id"):
        """取得課程的選課資訊

        Args:
            course_id: 課程 ID
            fields: 要取得的欄位
        """
        print(f"[C1] Getting enrollment for course: {course_id}")
        path = f"/api/course/{course_id}/enrollment?fields={fields}"
        data = self._get_json("GET", path)
        if data and isinstance(data, dict):
            roles = data.get("roles", [])
            if isinstance(roles, list):
                print(f"    Roles: {roles}")
        return data

    def get_course_students(self, course_id):
        """取得課程的學生列表

        Args:
            course_id: 課程 ID
        """
        print(f"[C2] Getting students for course: {course_id}")
        path = f"/api/course/{course_id}/students"
        data = self._get_json("GET", path)
        if data and isinstance(data, dict):
            students = data.get("list", [])
            if isinstance(students, list):
                print(f"    Found {len(students)} students")
        return data

    # ───────── 通知與首頁動態 ─────────

    def get_all_notifications(self, limit=20):
        """一次取得所有類型的通知

        Args:
            limit: 最大顯示數量
        """
        print(f"[N1] Getting all notifications")
        all_types = [
            "bulletin_created",
            "bulletin_updated",
            "exam_opened",
            "exam_submission_info",
            "exam_submit_started",
            "exam_score_updated",
            "exam_ended",
            "exam_make_up",
            "homework_ended",
            "homework_expiring",
            "homework_submitted",
            "homework_opening_for_submission",
            "homework_opened_for_submission",
            "course_opening",
            "course_started",
            "discussion_create",
            "topic_create",
            "topic_replies",
        ]
        types_str = "&".join(f"types={t}" for t in all_types)
        path = f"/ntf/users/{self.user_id}/notifications?limit={limit}&offset=0&additionalFields=unread_count&{types_str}"
        data = self._get_json("GET", path)
        if data and isinstance(data, dict):
            notifications = data.get("notifications", data.get("list", []))
            if isinstance(notifications, list):
                print(f"    Found {len(notifications)} notifications")
                for n in notifications[:10]:
                    if isinstance(n, dict):
                        ntype = n.get("type", "unknown")
                        payload = n.get("payload", {})
                        title = payload.get(
                            "title",
                            payload.get(
                                "activity_title", payload.get("bulletin_title", "N/A")
                            ),
                        )
                        course = payload.get("course_name", "")
                        print(f"    - [{ntype}] {title} ({course})")
        return data

    def get_org_bulletins(self, page=1, page_size=10):
        """取得學校/組織公告

        Args:
            page: 頁碼
            page_size: 每頁數量
        """
        print(f"[N2] Getting org bulletins")
        path = f"/api/org-bulletin/bulletins?page={page}&page_size={page_size}&conditions=%7B%7D"
        data = self._get_json("GET", path)
        if data and isinstance(data, dict):
            bulletins = data.get("bulletins", [])
            if isinstance(bulletins, list):
                print(f"    Found {len(bulletins)} org bulletins")
                for b in bulletins[:5]:
                    if isinstance(b, dict):
                        title = b.get("title", "Untitled")
                        print(f"    - {title}")
        return data

    def get_dashboard(self):
        """取得首頁動態資訊（通知 + 待辦）

        類似 server.py 的 get_dashboard() 功能
        """
        print(f"[D1] Getting dashboard")
        print(f"    --- Notifications (recent) ---")
        self.get_notifications(
            types=[
                "bulletin_created",
                "bulletin_updated",
                "homework_opened_for_submission",
            ],
            limit=5,
        )
        print(f"    --- Unread counts ---")
        self.get_notification_unread_count(
            types=[
                "bulletin_created",
                "bulletin_updated",
                "homework_opened_for_submission",
                "exam_opened",
            ]
        )
        print(f"    --- Todos ---")
        todos = self.get_todos()
        if todos and isinstance(todos, dict):
            todo_list = todos.get("todo_list", [])
            if isinstance(todo_list, list) and todo_list:
                print(f"    You have {len(todo_list)} todos")
        return True

    def get_all_course_summary(self):
        """一次取得所有課程的摘要（公告數、作業數）

        類似 server.py 的 get_all_course_summary() 功能
        """
        print(f"[D2] Getting course summary for all courses")
        courses_data = self.get_my_courses()
        if not courses_data or not isinstance(courses_data, dict):
            return None

        courses = courses_data.get("courses", [])
        if not isinstance(courses, list):
            return None

        print(f"\n    === Course Summary ===")
        for course in courses[:6]:
            if not isinstance(course, dict):
                continue
            cid = course.get("id")
            name = course.get("name", "Unknown")
            print(f"\n    Course: {name} (ID: {cid})")

            # Get bulletins count
            bulletins_data = self.get_course_bulletins(cid)
            if bulletins_data and isinstance(bulletins_data, dict):
                bulletins = bulletins_data.get(
                    "bulletins", bulletins_data.get("list", [])
                )
                if isinstance(bulletins, list):
                    print(f"      Bulletins: {len(bulletins)}")

            # Get homework count
            hw_data = self.get_homework(cid)
            if hw_data and isinstance(hw_data, dict):
                hw_list = hw_data.get("homework_activities", hw_data.get("list", []))
                if isinstance(hw_list, list):
                    print(f"      Homework activities: {len(hw_list)}")

        return True

    def demo_all_features(self):
        """Demo all available features"""
        print("\n" + "=" * 60)
        print("DEMO: Testing all API features")
        print("=" * 60)

        self.get_jwt()
        self.get_profile()
        self.get_my_courses()
        self.get_semesters()
        self.get_academic_years()
        self.get_feature_toggles()
        self.get_org_settings()
        self.get_course_classifications()
        self.get_todos()
        self.get_recently_visited_courses()
        self.get_user_tags()
        self.get_notification_unread_count()
        self.get_notifications()
        self.get_server_time()
        self.get_version()

        print("\n" + "=" * 60)
        print("Demo complete!")
        print("=" * 60)


def main():
    import sys

    if len(sys.argv) < 3:
        print("Usage: python tronclass_api.py <username> <password> [org_keyword]")
        print("Example: python tronclass_api.py 409261172 mypassword 輔仁大學")
        print()
        print("This will login and demo all available API features.")
        sys.exit(1)

    username = sys.argv[1]
    password = sys.argv[2]
    org_keyword = sys.argv[3] if len(sys.argv) > 3 else "天主教輔仁大學"

    api = TronClassAPI()

    # Login flow
    api.search_org(org_keyword)
    api.login(username, password)

    # Demo features
    api.demo_all_features()

    # Save session info
    print("\n" + "=" * 60)
    print("LOGIN SUCCESSFUL!")
    print("=" * 60)
    print(f"User ID: {api.user_id}")
    print(f"Session: {api.session_token}")
    print(f"JWT: {api.jwt_token[:50]}..." if api.jwt_token else "JWT: N/A")


if __name__ == "__main__":
    main()
