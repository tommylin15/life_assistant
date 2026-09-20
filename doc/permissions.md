# 生活助理 App v0.1 — Permissions & OAuth

## 1. 原則

- 最小權限
- 延遲請求
- 使用到功能時才要求
- 拒絕後 App 核心仍可用

## 2. Google OAuth

分功能請求：

### 基本登入
- user identity

### Calendar
- read/write calendar scope

### Gmail
- read metadata / messages 所需最小 scope

### Drive
- Bridge / 指定資料夾所需 scope

若可使用 app-specific / file-specific scope，優先於整個 Drive 權限。

## 3. Device Permissions

可能包含：

- Notifications
- Biometrics
- Microphone / Speech Recognition
- Camera
- Photos / File picker
- Selected folder access

## 4. Permission UI

設定頁顯示：

```text
Google Account   Connected
Gmail            Connected
Calendar         Connected
Drive            Connected
Notifications    Allowed
Microphone       Allowed
Camera           Allowed
```

## 5. Revocation

權限被撤銷後：

- 不刪本機資料
- 顯示功能不可用
- 提供重新授權
