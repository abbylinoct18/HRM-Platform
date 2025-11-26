import uuid
import csv
from io import StringIO
from typing import List, Dict, Optional
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator

# --- 1. 定義資料模型 (Pydantic) ---

# 員工資料的基底模型
class EmployeeBase(BaseModel):
    name: str # 姓名
    employee_code: str # 員工編號 (新增欄位，必須唯一)
    position: str # 職位
    department: str # 部門
    salary: int # 薪資 (已從 float 改為 int)

    # 驗證所有字串欄位不能為空 (針對 Pydantic 模型的輸入)
    @field_validator('name', 'employee_code', 'position', 'department', mode='before')
    @classmethod
    def check_non_empty_string(cls, value):
        if not value or (isinstance(value, str) and not value.strip()):
            raise ValueError('此欄位不能為空')
        return value

# 員工資料，包含內部 ID
class Employee(EmployeeBase):
    id: str # 內部 UUID，作為字典 key

# --- 2. 應用程式初始化與配置 ---

app = FastAPI(
    title="HRM 平台 API",
    description="FastAPI 支援員工管理和批次上傳。",
    version="1.0.0"
)

# 啟用 CORS 以允許前端訪問 API (在 Docker 環境中尤其重要)
origins = ["*"] 

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 記憶體內儲存（替代資料庫，應用重啟資料會重置）
# db: 內部 ID (str: UUID) -> Employee 物件
db: Dict[str, Employee] = {}
# code_to_id: 員工編號 (str) -> 內部 ID (str: UUID)，用於快速檢查編號唯一性
code_to_id: Dict[str, str] = {}

# 預設範例資料 (新增 employee_code)
initial_employees = [
    {"employee_code": "E001", "name": "王小明", "position": "軟體工程師", "department": "研發部", "salary": 80000}, # TWD 整數
    {"employee_code": "E002", "name": "林美玲", "position": "人力資源經理", "department": "人資部", "salary": 95000}, # TWD 整數
]
for data in initial_employees:
    employee_id = str(uuid.uuid4())
    code = data["employee_code"]
    db[employee_id] = Employee(id=employee_id, **data)
    code_to_id[code] = employee_id

# --- 3. API 路由 (Routes) ---

@app.get("/", summary="健康檢查", tags=["系統"])
def read_root():
    """系統健康檢查點。"""
    return {"message": "HRM API 運作中"}

@app.get("/employees", response_model=List[Employee], summary="獲取所有員工", tags=["員工管理"])
def get_employees():
    """返回所有員工清單。"""
    return list(db.values())

@app.get("/employees/{employee_id}", response_model=Employee, summary="獲取單一員工", tags=["員工管理"])
def get_employee(employee_id: str):
    """根據 ID 獲取特定員工資料。"""
    if employee_id not in db:
        raise HTTPException(status_code=404, detail="Employee not found")
    return db[employee_id]

@app.post("/employees", response_model=Employee, status_code=201, summary="新增員工", tags=["員工管理"])
def create_employee(employee: EmployeeBase):
    """新增一名新員工，員工編號必須唯一。"""
    # 檢查員工編號是否重複
    if employee.employee_code in code_to_id:
        raise HTTPException(status_code=400, detail=f"員工編號 {employee.employee_code} 已存在。")

    employee_id = str(uuid.uuid4())
    new_employee = Employee(id=employee_id, **employee.model_dump())
    
    # 更新資料庫和編號映射
    db[employee_id] = new_employee
    code_to_id[new_employee.employee_code] = employee_id
    
    return new_employee

@app.put("/employees/{employee_id}", response_model=Employee, summary="更新員工", tags=["員工管理"])
def update_employee(employee_id: str, employee_update: EmployeeBase):
    """根據 ID 更新現有員工資料，員工編號若更改必須保持唯一。"""
    if employee_id not in db:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    old_employee = db[employee_id]
    
    # 檢查員工編號是否被更改且與其他員工重複
    new_code = employee_update.employee_code
    if new_code != old_employee.employee_code:
        if new_code in code_to_id:
            raise HTTPException(status_code=400, detail=f"新員工編號 {new_code} 已被其他員工使用。")
        
        # 如果編號更改，先從舊編號映射中移除
        del code_to_id[old_employee.employee_code]
        # 更新 code_to_id
        code_to_id[new_code] = employee_id

    # 執行更新
    updated_employee = Employee(id=employee_id, **employee_update.model_dump())
    db[employee_id] = updated_employee
    
    return db[employee_id]

@app.delete("/employees/{employee_id}", status_code=204, summary="刪除員工", tags=["員工管理"])
def delete_employee(employee_id: str):
    """根據 ID 刪除特定員工。"""
    if employee_id not in db:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # 刪除前從 code_to_id 中移除
    code_to_remove = db[employee_id].employee_code
    if code_to_remove in code_to_id:
        del code_to_id[code_to_remove]
        
    del db[employee_id]
    return {"ok": True}

@app.post("/upload", summary="批次上傳 CSV 格式文件", tags=["批次處理"])
async def bulk_upload(file: UploadFile = File(...)):
    """
    處理上傳的檔案。支援副檔名為 .csv 或 .txt 的檔案，但內容必須是 CSV 格式。
    不支援 .xlsx 檔案。
    """
    contents = await file.read()
    
    try:
        decoded_content = contents.decode('utf-8')
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="檔案編碼錯誤，請確保使用 UTF-8 編碼。")

    csv_reader = csv.reader(StringIO(decoded_content))
    
    try:
        header = next(csv_reader) # 假設第一行是標頭
    except StopIteration:
        raise HTTPException(status_code=400, detail="檔案內容為空。")

    # 預期的欄位數為 5: 姓名, 員工編號, 職位, 部門, 薪資
    expected_columns = 5 
    if len(header) < expected_columns:
        raise HTTPException(status_code=400, detail="檔案標頭不完整，預期欄位：姓名 (Name), 員工編號 (Code), 職位 (Position), 部門 (Department), 薪資 (Salary)。")

    success_count = 0
    error_entries = []
    
    # 建立一個暫時集合來檢查當前批次中的重複編號
    current_batch_codes = set()

    for row_number, row in enumerate(csv_reader):
        row_num_display = row_number + 2 # 顯示行號 (從 2 開始，因為 1 是標頭)
        
        # 1. 檢查欄位數量
        if len(row) < expected_columns:
            error_entries.append({"row": row_num_display, "error": "資料欄位不足", "data": row})
            continue
        
        # 2. 欄位擷取與清理
        # 預期順序: Name, Employee_Code, Position, Department, Salary
        try:
            name, code, position, department, salary_str = [field.strip() for field in row[:expected_columns]]
        except Exception as e:
            error_entries.append({"row": row_num_display, "error": f"資料擷取或格式化錯誤: {e}", "data": row})
            continue

        # 3. 檢查欄位是否為空 (強制驗證)
        if not name or not code or not position or not department or not salary_str:
            error_entries.append({"row": row_num_display, "error": "所有欄位 (姓名, 編號, 職位, 部門, 薪資) 均為必填，不能為空。", "data": row})
            continue

        # 4. 檢查薪資格式
        try:
            # 轉換為 int(float()) 以確保薪資被儲存為整數
            salary = int(float(salary_str)) 
            if salary < 0:
                raise ValueError("薪資必須為正值。")
        except ValueError:
            error_entries.append({"row": row_num_display, "error": f"薪資格式錯誤: '{salary_str}' 不是有效的正整數。", "data": row})
            continue
            
        # 5. 檢查員工編號的唯一性 (當前批次 + 既有資料庫)
        if code in code_to_id:
            error_entries.append({"row": row_num_display, "error": f"員工編號 '{code}' 已存在於系統中。", "data": row})
            continue
        if code in current_batch_codes:
            error_entries.append({"row": row_num_display, "error": f"員工編號 '{code}' 在本次上傳中重複。", "data": row})
            continue
        current_batch_codes.add(code)
            
        # 6. 成功新增資料
        try:
            employee_data = EmployeeBase(
                name=name,
                employee_code=code,
                position=position,
                department=department,
                salary=salary
            )
            
            employee_id = str(uuid.uuid4())
            new_employee = Employee(id=employee_id, **employee_data.model_dump())
            
            # 更新資料庫和編號映射
            db[employee_id] = new_employee
            code_to_id[code] = employee_id
            success_count += 1
            
        except Exception as e:
            error_entries.append({"row": row_num_display, "error": f"內部資料儲存錯誤: {e}", "data": row})
            # 如果儲存失敗，且編號已被暫存，理論上不應該發生，但作為防禦性編程，可以處理
            if code in current_batch_codes:
                 current_batch_codes.remove(code)


    message = f"批次上傳完成。成功新增 {success_count} 筆記錄。"
    return {"message": message, "successful_uploads": success_count, "errors": error_entries}