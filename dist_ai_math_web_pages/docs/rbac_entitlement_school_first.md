# RBAC & Entitlement — School-First Edition

> **Version**: 1.0  
> **Target**: AI Math Web — Taiwan G5–G6 數學教育平台  
> **Scope**: 學校授權模式 (School-first)，定義角色、資源、操作、權限規則  
> **Depends on**: `server.py` (FastAPI auth), `subscription.js`, `student_auth.js`, `auth_parent.js`, `adaptive_mastery.py`

---

## A. Role Matrix（角色矩陣）

### A.1 角色定義

| Role ID | 中文名 | 描述 | 建立方式 | 認證方式 |
|---------|--------|------|----------|----------|
| `student` | 學生 | G5–G6 練習者，產生作答紀錄 | 由 teacher 或 parent 建立 | name + PIN（沿用 `student_auth.js`）|
| `parent` | 家長 | 查看孩子報告、管理訂閱 | 自行註冊或由 school_admin 邀請 | Email/Password（沿用 `auth_parent.js`）或 OAuth |
| `teacher` | 教師 | 指派練習、查看班級報告、標記弱項 | 由 school_admin 建立 | Email/Password + school_code |
| `school_admin` | 學校管理員 | 管理教師帳號、班級、授權額度 | 由 platform_admin 建立 | Email/Password + org_id |
| `platform_admin` | 平台管理員 | 全域管理、開通學校、監控 SLO | 內部人員，手動建立 | X-Admin-Token（沿用現有 header-token）|

### A.2 角色層級關係

```
platform_admin
  └─ school_admin        (1 school : N school_admins)
       └─ teacher         (1 school : N teachers)
            └─ student    (1 teacher : N students，可跨班)
       └─ parent          (1 parent : N students，跨班/跨校)
```

**規則**：
- 每個 `student` 必須隸屬於至少一個 `teacher`（班級）
- 一個 `parent` 可關聯多個 `student`（跨校亦可）
- `teacher` 只能看到自己班級的學生（除非 school_admin 授權跨班）
- `school_admin` 可看到該校所有班級與學生

---

## B. Resource List（資源清單）

| Resource ID | 中文名 | 說明 | 現有檔案 |
|-------------|--------|------|----------|
| `question` | 題目 | mathgen 產出的練習題 | `engine.py`, `docs/*/index.html` |
| `attempt` | 作答紀錄 | 學生的每次答題結果 | `answers.db`, `server.py /v1/diagnose` |
| `hint` | 提示 | 4 層提示引擎輸出 | `docs/shared/hint_engine.js` |
| `parent_report` | 家長報告 | 學習摘要與補救方案 | `learning/parent_report.py` |
| `class_report` | 班級報告 | **NEW** 教師查看的班級統計 | 待建 |
| `school_report` | 學校報告 | **NEW** 校級彙總 | 待建 |
| `student_profile` | 學生檔案 | 姓名、年級、概念狀態 | `students` table |
| `concept_state` | 概念掌握狀態 | mastery stage + error_stats | `student_concepts` table |
| `subscription` | 訂閱狀態 | 方案、座位數、到期日 | `subscriptions` table |
| `assignment` | 指派練習 | **NEW** 教師指派的題組 | 待建 |
| `school_license` | 學校授權 | **NEW** 校級授權與席位 | 待建 |
| `teacher_account` | 教師帳號 | **NEW** 教師個人資料 | 待建 |

---

## C. Action List（操作清單）

| Action | 說明 | HTTP Verb | 端點範例 |
|--------|------|-----------|----------|
| `create` | 建立資源 | POST | `POST /v1/students` |
| `read` | 讀取資源 | GET | `GET /v1/reports/parent/{student_id}` |
| `update` | 修改資源 | PUT/PATCH | `PATCH /v1/students/{id}` |
| `delete` | 刪除資源 | DELETE | `DELETE /v1/students/{id}` |
| `list` | 列舉資源 | GET | `GET /v1/class/{class_id}/students` |
| `assign` | 指派練習 | POST | `POST /v1/assignments` |
| `submit` | 提交作答 | POST | `POST /v1/diagnose` |
| `export` | 匯出報告 | GET | `GET /v1/reports/class/{id}/export` |
| `invite` | 邀請成員 | POST | `POST /v1/school/{id}/invite` |
| `revoke` | 撤銷權限 | DELETE | `DELETE /v1/school/{id}/members/{uid}` |
| `provision` | 開通帳號 | POST | `POST /v1/app/auth/provision`（現有）|
| `flag_teacher` | 教師標記弱項 | PATCH | `PATCH /v1/concepts/{id}/flag` |

---

## D. Entitlement Rules（權限規則矩陣）

### D.1 Student

| Resource | create | read | update | delete | list | submit | assign | export |
|----------|--------|------|--------|--------|------|--------|--------|--------|
| question | — | ✓ own | — | — | ✓ assigned | — | — | — |
| attempt | — | ✓ own | — | — | ✓ own | ✓ | — | — |
| hint | — | ✓ own | — | — | — | — | — | — |
| parent_report | — | — | — | — | — | — | — | — |
| student_profile | — | ✓ own | ✓ own (display_name) | — | — | — | — | — |
| concept_state | — | ✓ own | — | — | — | — | — | — |
| assignment | — | ✓ assigned | — | — | ✓ assigned | ✓ | — | — |

### D.2 Parent

| Resource | create | read | update | delete | list | submit | export |
|----------|--------|------|--------|--------|------|--------|--------|
| attempt | — | ✓ child | — | — | ✓ child | — | — |
| parent_report | — | ✓ child¹ | — | — | ✓ children | — | ✓ child¹ |
| student_profile | — | ✓ child | — | — | ✓ children | — | — |
| concept_state | — | ✓ child | — | — | — | — | — |
| subscription | — | ✓ own | ✓ own | — | — | — | — |

> ¹ Full report 需 `subscription.status ∈ {trial, paid_active}`，否則降級為 basic report（沿用現有 `canAccessFullReport()` 邏輯）

### D.3 Teacher

| Resource | create | read | update | delete | list | assign | export | flag |
|----------|--------|------|--------|--------|------|--------|--------|------|
| question | — | ✓ all | — | — | ✓ all | — | — | — |
| attempt | — | ✓ class | — | — | ✓ class | — | — | — |
| hint | — | ✓ class | — | — | — | — | — | — |
| class_report | — | ✓ own_class | — | — | ✓ own_classes | — | ✓ own_class | — |
| student_profile | ✓ class | ✓ class | ✓ class | — | ✓ class | — | — | — |
| concept_state | — | ✓ class | ✓ flag | — | ✓ class | — | — | ✓ class |
| assignment | ✓ class | ✓ own | ✓ own | ✓ own | ✓ own | ✓ class | — | — |
| parent_report | — | ✓ class | — | — | ✓ class | — | ✓ class | — |

> Teacher 可查看班級學生的 parent_report（for 親師溝通），但不能修改訂閱狀態

### D.4 School Admin

| Resource | create | read | update | delete | list | invite | revoke | export |
|----------|--------|------|--------|--------|------|--------|--------|--------|
| teacher_account | ✓ | ✓ school | ✓ school | ✓ school | ✓ school | ✓ | ✓ | — |
| class_report | — | ✓ school | — | — | ✓ school | — | — | ✓ school |
| school_report | — | ✓ own | — | — | — | — | — | ✓ own |
| student_profile | ✓ | ✓ school | ✓ school | ✓ school | ✓ school | — | — | ✓ school |
| school_license | — | ✓ own | — | — | — | — | — | — |
| subscription | — | ✓ school | ✓ school² | — | ✓ school | — | — | — |
| assignment | — | ✓ school | — | — | ✓ school | — | — | — |

> ² school_admin 可調整該校席位與方案，但不能更改其他學校

### D.5 Platform Admin

| Resource | create | read | update | delete | list | provision |
|----------|--------|------|--------|--------|------|-----------|
| *all* | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

> Platform Admin 沿用現有 `X-Admin-Token` header 驗證（`server.py /v1/app/auth/provision`）

### D.6 Scope 規則速查

| Scope 標記 | 意義 |
|-----------|------|
| `own` | 只能操作自己的資源 |
| `child` / `children` | 只能操作已關聯的孩子資源 |
| `class` / `own_class` | 只能操作自己班級的資源 |
| `school` | 只能操作自己學校的資源 |
| `assigned` | 只能操作被指派的資源 |
| `all` | 無範圍限制（僅 platform_admin 或公開資源）|

---

## E. Risk Points（風險點與對策）

### E.1 已知風險（來自歷史教訓）

| # | 風險 | 來源 | 對策 |
|---|------|------|------|
| R1 | **Secret 洩漏到 git** | `SECURITY_MANUAL_ACTIONS.md`: OpenAI key 曾被 commit | 所有 token/key 存 `.env`；`check_no_secrets.py` pre-commit hook 必須啟用 |
| R2 | **Client-side subscription 可被竄改** | `MVP_GAP_LIST.md` P0-3 | 所有 RBAC 檢查必須 **server-side**；`subscription.js` localStorage 僅作 UI cache |
| R3 | **docs/dist 不同步** | `debug_note.txt` | 新增 RBAC middleware 後必須跑 `verify_all.py` 確認 hash 一致 |
| R4 | **Parent report 可被未授權存取** | `debug_note.txt`: registry out of sync | PIN 驗證 + server-side ownership check（`student.account_id == request.account_id`）|

### E.2 新增風險（School-first 特有）

| # | 風險 | 嚴重度 | 對策 |
|---|------|--------|------|
| R5 | **Teacher 越權查看他校學生** | HIGH | 每筆查詢加入 `WHERE school_id = ?` scope filter；禁止前端傳 school_id |
| R6 | **School Admin 竄改其他學校授權** | HIGH | `school_license` 的 CRUD 全部加 `school_id` ownership check |
| R7 | **邀請連結被重用或盜用** | MED | 邀請 token 設 24h TTL + single-use + school_id binding |
| R8 | **大量席位開通 DoS** | MED | school_license 設 `max_seats` 上限；provision 端點加 rate limit（沿用現有 rate_limit_events）|
| R9 | **學生資料跨校洩漏** | HIGH | `student_profile` 的 read/list 必須經過 school_id + class_id 雙重 scope 過濾 |
| R10 | **Teacher flag_teacher 被濫用** | LOW | flag 只能標記自己班級；flag 歷史紀錄可稽核 |
| R11 | **Role escalation（角色提權）** | CRITICAL | role 欄位 server-side only；禁止 client 傳遞 role 參數；role 變更需 platform_admin 或 school_admin 操作 |

### E.3 安全不可妥協規則

1. **永不信任 client-side role 聲明** — role 從 DB 讀取，不從 request body 或 header 取
2. **所有 scope filter 在 SQL query 層實施** — 不在應用邏輯過濾（避免 IDOR）
3. **rate limiting 沿用現有機制** — 延伸到新端點（invite, provision, flag）
4. **bootstrap token 模式沿用現有實作** — 不另造輪子（`bootstrap_tokens` table, SHA256 hash, 5min TTL, single-use）
5. **密碼儲存沿用 SHA256 + per-user salt** — 不改變現有 app_users 結構

---

## F. MVP Implementation Plan（最小可行實作）

### F.1 資料庫變更

```sql
-- 新增 schools 表
CREATE TABLE schools (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    school_code TEXT NOT NULL UNIQUE,  -- 學校代碼，用於 teacher 註冊
    max_seats   INTEGER DEFAULT 200,
    created_at  TEXT DEFAULT (datetime('now')),
    active      INTEGER DEFAULT 1
);

-- 新增 roles 表
CREATE TABLE roles (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id  INTEGER NOT NULL REFERENCES accounts(id),
    role        TEXT NOT NULL CHECK(role IN ('student','parent','teacher','school_admin','platform_admin')),
    school_id   INTEGER REFERENCES schools(id),  -- NULL for parent/platform_admin
    created_at  TEXT DEFAULT (datetime('now')),
    UNIQUE(account_id, role, school_id)
);

-- 新增 classes 表
CREATE TABLE classes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    school_id   INTEGER NOT NULL REFERENCES schools(id),
    teacher_id  INTEGER NOT NULL REFERENCES accounts(id),
    name        TEXT NOT NULL,
    grade       INTEGER CHECK(grade IN (5, 6)),
    created_at  TEXT DEFAULT (datetime('now'))
);

-- 新增 class_students 關聯表
CREATE TABLE class_students (
    class_id    INTEGER NOT NULL REFERENCES classes(id),
    student_id  INTEGER NOT NULL REFERENCES students(id),
    enrolled_at TEXT DEFAULT (datetime('now')),
    PRIMARY KEY (class_id, student_id)
);

-- 新增 parent_students 關聯表（取代現有 localStorage 模式）
CREATE TABLE parent_students (
    parent_account_id  INTEGER NOT NULL REFERENCES accounts(id),
    student_id         INTEGER NOT NULL REFERENCES students(id),
    verified_at        TEXT DEFAULT (datetime('now')),
    PRIMARY KEY (parent_account_id, student_id)
);

-- 新增 assignments 表
CREATE TABLE assignments (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    teacher_id  INTEGER NOT NULL REFERENCES accounts(id),
    class_id    INTEGER NOT NULL REFERENCES classes(id),
    title       TEXT NOT NULL,
    topic_codes TEXT NOT NULL,       -- JSON array of topic codes
    due_date    TEXT,
    created_at  TEXT DEFAULT (datetime('now'))
);

-- 新增 invitations 表
CREATE TABLE invitations (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    token_hash  TEXT NOT NULL UNIQUE,
    school_id   INTEGER NOT NULL REFERENCES schools(id),
    role        TEXT NOT NULL CHECK(role IN ('teacher','school_admin','parent')),
    email       TEXT,
    expires_at  TEXT NOT NULL,
    consumed_at TEXT,
    created_by  INTEGER NOT NULL REFERENCES accounts(id)
);

-- 擴展現有 subscriptions 表
ALTER TABLE subscriptions ADD COLUMN school_id INTEGER REFERENCES schools(id);
```

### F.2 Backend RBAC Middleware

```python
# rbac.py — 新檔案，置於 server.py 同層

from enum import Enum
from functools import wraps
from fastapi import HTTPException, Request

class Role(str, Enum):
    STUDENT = "student"
    PARENT = "parent"
    TEACHER = "teacher"
    SCHOOL_ADMIN = "school_admin"
    PLATFORM_ADMIN = "platform_admin"

# Role hierarchy for implicit permission inheritance
ROLE_HIERARCHY = {
    Role.PLATFORM_ADMIN: {Role.PLATFORM_ADMIN, Role.SCHOOL_ADMIN, Role.TEACHER, Role.PARENT, Role.STUDENT},
    Role.SCHOOL_ADMIN: {Role.SCHOOL_ADMIN, Role.TEACHER},
    Role.TEACHER: {Role.TEACHER},
    Role.PARENT: {Role.PARENT},
    Role.STUDENT: {Role.STUDENT},
}

def require_role(*allowed_roles: Role):
    """Decorator: reject request if user lacks any of the allowed roles."""
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            # Role is loaded from DB by auth middleware, never from client
            user_role = getattr(request.state, "role", None)
            if user_role is None:
                raise HTTPException(status_code=401, detail="authentication required")
            effective_roles = ROLE_HIERARCHY.get(Role(user_role), set())
            if not effective_roles & set(allowed_roles):
                raise HTTPException(status_code=403, detail="insufficient permissions")
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator

def require_scope(resource_owner_field: str, scope_field: str):
    """Decorator: ensure the resource belongs to the requesting user's scope.
       e.g. require_scope('school_id', 'school_id') ensures teacher can only
       access resources within their own school."""
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            user_scope = getattr(request.state, scope_field, None)
            resource_scope = kwargs.get(resource_owner_field) or request.path_params.get(resource_owner_field)
            if user_scope is None or resource_scope is None:
                raise HTTPException(status_code=403, detail="scope check failed")
            if str(user_scope) != str(resource_scope):
                # Platform admin bypasses scope checks
                if getattr(request.state, "role", None) != Role.PLATFORM_ADMIN:
                    raise HTTPException(status_code=403, detail="cross-scope access denied")
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator
```

### F.3 實作優先順序

| Phase | 項目 | 涉及檔案 | 前置條件 |
|-------|------|----------|----------|
| **MVP-1** | DB migration + `roles` table | `server.py` | 無 |
| **MVP-2** | `rbac.py` middleware + `require_role` | 新檔 `rbac.py` | MVP-1 |
| **MVP-3** | Teacher 註冊 + 班級建立 | `server.py` 新端點 | MVP-1, MVP-2 |
| **MVP-4** | `class_report` 端點 | `learning/class_report.py`（新）| MVP-3 |
| **MVP-5** | School Admin dashboard + invite | `server.py` 新端點 | MVP-2 |
| **MVP-6** | `assignment` CRUD + 學生端顯示 | `server.py` + `docs/shared/assignment.js`（新）| MVP-3 |
| **MVP-7** | Parent-Student 關聯遷移 | `server.py` + `auth_parent.js` 更新 | MVP-1 |
| **MVP-8** | `school_report` 彙總 | `learning/school_report.py`（新）| MVP-4 |

### F.4 與現有系統的相容策略

| 現有元件 | 相容方式 |
|----------|----------|
| `student_auth.js` (name+PIN) | 保留作為學生端快速登入；server-side 增加 `student.class_id` scope 過濾 |
| `auth_parent.js` (Firebase optional) | 保留 Firebase 路徑；增加 `parent_students` table 實現 server-side 關聯 |
| `subscription.js` (localStorage) | 保留作為 UI cache；所有權限判斷改為 server-side（修復 P0-3）|
| `X-API-Key` auth | 保留現有 API key 路徑；新增 role 欄位到 auth middleware |
| `X-Admin-Token` provision | 保留，映射為 `platform_admin` role |
| `hint_engine.js` (4-level) | 不變；teacher 可查看學生使用的 hint level |
| `adaptive_mastery.py` | 不變；`flag_teacher` 寫入 `student_concepts.flag_teacher` |
| `quality_gate.md` (4-gate) | 不變；RBAC 不影響題目品質管道 |
| `verify_all.py` | 新增端點後需加入 health check 清單 |

### F.5 Smoke Test 檢查項

```
□ platform_admin 可建立 school
□ school_admin 可建立 teacher（需 school_code）
□ teacher 可建立 class + 加入 student
□ teacher 只能看到自己班級的 student（scope filter 生效）
□ teacher 無法查看其他學校的資料（cross-scope denied）
□ parent 只能看到自己孩子的 report
□ parent 的 full report 需 active subscription（402 if not）
□ student 只能看到被指派的題目
□ invitation token 24h 過期 + single-use
□ client 傳遞 role 參數時被忽略（server 從 DB 讀取）
□ rate limit 在新端點生效
□ verify_all.py 通過（docs/dist hash 一致）
```

---

## Appendix: 資料流圖

```
┌──────────────┐     school_code      ┌──────────────────┐
│ School Admin │ ──── invite ────────▶│ Teacher 註冊     │
│ (school_admin)│                     │ (teacher role)   │
└──────┬───────┘                     └────────┬─────────┘
       │ manage license                       │ create class
       │ view school_report                   │ add students
       │                                      │ create assignment
       ▼                                      ▼
┌──────────────┐                     ┌──────────────────┐
│ Platform     │                     │ Class            │
│ Admin        │                     │ ├─ student_1     │
│ (provision)  │                     │ ├─ student_2     │
└──────────────┘                     │ └─ student_N     │
                                     └────────┬─────────┘
                                              │ attempt + concept_state
                                              ▼
                                     ┌──────────────────┐
                                     │ Reports          │
                                     │ ├─ parent_report │──▶ Parent (PIN + subscription gate)
                                     │ ├─ class_report  │──▶ Teacher (scope: own class)
                                     │ └─ school_report │──▶ School Admin (scope: own school)
                                     └──────────────────┘
```

---

## Change Log

| Date | Version | Author | Description |
|------|---------|--------|-------------|
| 2026-03-21 | 1.0 | AI Agent | Initial RBAC spec for School-first edition |
