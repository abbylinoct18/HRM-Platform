# 員工資源管理平台 (HRM Platform)

本專案是一個輕量級的員工管理系統，採用 Python FastAPI 作為後端 API，搭配原生 JavaScript 和 Tailwind CSS 實現前端介面，並使用 Docker Compose 進行容器化部署。

---

## 📊 核心功能
- **介面操作**： 對員工資料進行完整的增、查、改、刪。
- **篩選功能**： 前端提供即時、多欄位的資料篩選功能。
- **批次上傳與清晰錯誤報告**：
	- 支援 CSV 檔案格式上傳大量員工資料。
	- API 詳盡記錄批次處理中的每一行錯誤（如編號重複、資料格式錯誤）。
	- 前端以專屬的錯誤模態框 (Modal) 清晰展示錯誤清單，提升使用者體驗，無需查看 Console。

## 🛠 使用技術
- **後端**： Python 3.11 + FastAPI
- **前端**： HTML5, 原生 JavaScript, Tailwind CSS
- **部署**： Docker Compose

## 📂 專案結構
```
hrm_platform/
├── Dockerfile.backend      # Python/FastAPI 容器建構檔
├── Dockerfile.frontend     # Nginx/Frontend 容器建構檔
├── docker-compose.yml      # 🐳 服務定義 (backend, frontend)
├── index.html              # 🌐 前端 UI 介面
├── main.py                 # 🏠 FastAPI 後端服務
├── requirements.txt        # 📦 後端 Python 依賴清單 (FastAPI, Uvicorn)
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
- `--build`：確保重新建構所有映像檔。

步驟 2: 存取應用程式與 API 驗證
- 服務啟動後：
	- 前端介面 (HRM Web App): 瀏覽器開啟 [http://localhost:8000](http://localhost:8000) (依據 docker-compose.yml 設定)。
	- 後端 API 文件 (Swagger UI) 驗證：
		- 瀏覽器開啟 [http://localhost:8000/docs](http://localhost:8000/docs) 。
		- FastAPI 會自動生成互動式的 Swagger UI 介面，您可以在此查看所有 API 端點（如 `/employees`, `/upload`）。
		- 如何驗證：
			- 點擊任一端點（例如 `GET /employees`）。
			- 點擊右上角的「Try it out」。
			- 點擊「Execute」。
			- 如果 API 運作正常，您將看到 Response body 中返回預設的員工資料，且 Response code 為 200。

		- 您也可以使用 `POST /employees` 端點來手動新增測試員工，以驗證員工編號的唯一性檢查是否生效。

步驟 3: 停止與清理
- 要停止並移除所有容器和網路：
```
docker compose down
```
