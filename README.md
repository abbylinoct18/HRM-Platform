# 員工資源管理平台 (HRM Platform)

本專案是一個輕量級的員工管理系統，採用 Python FastAPI 作為後端 API，搭配原生 JavaScript 和 Tailwind CSS 實現前端介面，並使用 **Docker Compose 進行容器化部署與資料儲存**。

---

## 📊 核心功能

- **介面操作**： 對員工資料進行完整的增、查、改、刪 (CRUD)。
- **篩選功能**： 前端提供即時、多欄位的資料篩選功能。
- **持久化儲存**： 資料不再儲存在記憶體中，應用程式重啟後資料不會遺失。
- **批次上傳與清晰錯誤報告**：
	- 支援 CSV 檔案格式上傳大量員工資料。
	- API 詳盡記錄批次處理中的每一行錯誤（如編號重複、資料格式錯誤）。
	- 前端以專屬的錯誤模態框 (Modal) 清晰展示錯誤清單，提升使用者體驗，無需查看 Console。

## 🛠 使用技術

- **後端**： Python 3.11, FastAPI, **SQLModel (ORM)**, **PostgreSQL (資料庫)**
- **前端**： HTML5, 原生 JavaScript, Tailwind CSS
- **部署**： Docker Compose
- **管理工具**： **pgAdmin 4** (用於圖形化管理資料庫)

## 📂 專案結構
```
hrm_platform/
├── Dockerfile.backend      # Python/FastAPI 容器建構檔
├── Dockerfile.frontend     # Nginx/Frontend 容器建構檔
├── docker-compose.yml      # 🐳 服務定義 (backend, frontend, db, pgadmin)
├── index.html              # 🌐 前端 UI 介面
├── main.py                 # 🏠 FastAPI 後端服務
├── requirements.txt        # 📦 後端 Python 依賴清單
├── hrm_employee_sample.csv # 📄 批次上傳 CSV 範例檔案
├── .gitignore              # 🚫 Git 忽略清單 (忽略環境文件和快取)
└── README.md               # 專案說明文件 (此檔案)
```

## 👉 執行步驟 (使用 Docker Compose)
前提條件
- 確保您的系統已安裝 Docker 和 Docker Compose。

步驟 1: 建構與啟動服務
- 在專案的根目錄下執行以下命令：
```
	docker compose up --build
```
- 說明： 此命令會啟動四個服務：backend (FastAPI), frontend (網頁介面), db (PostgreSQL 資料庫), 和 pgadmin (資料庫管理介面)。
- 預期結果：
	- 您會看到 hrm_postgres_db、hrm_backend、hrm_frontend 和 hrm_pgadmin 依序創建並啟動。
	- 若要查看服務日誌，請執行 docker compose logs -f。
	- 在 hrm_backend 的日誌中，您應該會看到 FastAPI 成功連線資料庫並初始化表格的訊息。

步驟 2: 訪問與驗證應用程式
- 務啟動後，請透過瀏覽器訪問以下網址進行功能驗證：
	- HRM 平台: [http://localhost:3000](http://localhost:3000) 主應用程式，驗證 CRUD 操作和持久化功能。
	- API 文件: [http://localhost:8000/docs](http://localhost:8000/docs) FastAPI 互動式 API 文件 (Swagger UI)。
	- pgAdmin 4 (管理): [http://localhost:5050](http://localhost:5050) 資料庫圖形化管理工具。
- 重要功能測試： 
	- 資料新增： 在 [http://localhost:3000](http://localhost:3000) 頁面上新增一筆員工或使用批次上傳功能匯入員工資料。
	- 持久化測試： 執行 docker compose restart，然後刷新頁面，確認該筆資料依然存在。

步驟 3: pgAdmin 資料庫連線配置
- 若要使用 pgAdmin 直接查看資料表結構或內容：
	- 訪問 [http://localhost:5050](http://localhost:5050) 並使用設定的 Email (admin@hrm.com) 和密碼 (supersecret) 登入。
	- 點擊左側導航欄中的 "Add New Server"，連線設定如下：
		- 主機名稱/地址： db
		- 埠號： 5432
		- 資料庫： db_name
		- 使用者名稱/密碼： user / password

步驟 4: 停止與清理
```
docker compose stop
```
- 停止容器，但保留它們的狀態。
```
docker compose down
```
- 停止並移除所有容器、網路和服務，但保留持久化資料 (postgres_data volume)。
```
docker volume rm hrm_platform_postgres_data
```
- 永久刪除所有員工資料，僅在需要重置資料庫時使用。