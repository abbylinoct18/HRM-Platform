import uuid
import csv
import os
from io import StringIO
from typing import List, Dict, Optional
# 引入 Depends (依賴注入)、Session (資料庫會話)
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends 
from fastapi.middleware.cors import CORSMiddleware
# 引入 SQLModel 相關函式庫
from sqlmodel import SQLModel, Field, create_engine, Session, select 
from pydantic import BaseModel, field_validator
from sqlalchemy.exc import IntegrityError # 用於捕捉資料庫唯一性錯誤

# --- 1. 定義資料模型 (SQLModel) ---

# 員工資料的資料庫模型 (對應到資料庫表格 table=True)
class Employee(SQLModel, table=True):
    # ID：資料庫自動生成的主鍵，型別為 int
    id: Optional[int] = Field(default=None, primary_key=True) 
    
    # 員工編號 (資料庫層級唯一性約束)
    employee_code: str = Field(index=True, unique=True, nullable=False)
    
    name: str = Field(nullable=False) # 姓名
    position: str = Field(nullable=False) # 職位
    department: str = Field(nullable=False) # 部門
    salary: int = Field(gt=0, nullable=False) # 薪資 (確保大於 0)

# 用於 API 請求時的輸入模型 (不包含 id)
class EmployeeCreate(SQLModel):
    name: str 
    employee_code: str 
    position: str 
    department: str 
    salary: int

    # 驗證所有字串欄位不能為空 (針對輸入)
    @field_validator('name', 'employee_code', 'position', 'department', mode='before')
    @classmethod
    def check_non_empty_string(cls, value):
        if not value or (isinstance(value, str) and not value.strip()):
            raise ValueError('此欄位不能為空')
        return value

# --- 2. 應用程式初始化與配置 (資料庫連線) ---

app = FastAPI(
    title="HRM 平台 API",
    description="FastAPI 支援員工管理和批次上傳。",
    version="1.0.0"
)

# 啟用 CORS ... (保持不變)
origins = ["*"] 
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 【移除】舊的記憶體內儲存 db: Dict[str, Employee] = {}
# 【移除】舊的編號映射 code_to_id: Dict[str, str] = {}
# 【移除】預設範例資料 initial_employees

# 【新增】資料庫連線設定
# 從環境變數讀取連線字串 (來自 docker-compose.yml)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./test.db") 
engine = create_engine(DATABASE_URL, echo=False) # 建立連線引擎

def create_db_and_tables():
    """使用 SQLModel 創建資料庫中的所有表格。"""
    SQLModel.metadata.create_all(engine)

def get_session():
    """依賴注入函式：管理資料庫會話的生命週期。"""
    with Session(engine) as session:
        yield session

@app.on_event("startup")
def on_startup():
    """應用程式啟動時，自動建立資料庫表格 (如果不存在)。"""
    create_db_and_tables()

# --- 3. API 路由 (Routes) ---
# main.py - 調整 GET 路由

@app.get("/", summary="健康檢查", tags=["系統"])
def read_root():
    """系統健康檢查點。"""
    return {"message": "HRM API 運作中"}

@app.get("/employees", response_model=List[Employee], summary="獲取所有員工", tags=["員工管理"])
# 透過 Depends(get_session) 注入資料庫會話
def get_employees(session: Session = Depends(get_session)): 
    """返回所有員工清單。"""
    # 使用 select 查詢所有員工
    employees = session.exec(select(Employee)).all()
    return employees

@app.get("/employees/{employee_id}", response_model=Employee, summary="獲取單一員工", tags=["員工管理"])
# ID 型別改為 int
def get_employee(employee_id: int, session: Session = Depends(get_session)): 
    """根據 ID 獲取特定員工資料。"""
    # 使用 session.get 透過主鍵查詢
    employee = session.get(Employee, employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    return employee

# main.py - 調整 POST 路由

@app.post("/employees", response_model=Employee, status_code=201, summary="新增員工", tags=["員工管理"])
# 使用 EmployeeCreate 作為輸入模型
def create_employee(employee: EmployeeCreate, session: Session = Depends(get_session)): 
    """新增一名新員工，員工編號必須唯一。"""
    
    # 創建新的 Employee 物件
    new_employee = Employee.model_validate(employee)
    
    try:
        session.add(new_employee)
        session.commit() # 提交事務，寫入資料庫
        session.refresh(new_employee) # 重新整理物件以獲得資料庫生成的主鍵 ID
    except IntegrityError:
        # 捕捉資料庫唯一性錯誤
        session.rollback()
        raise HTTPException(status_code=400, detail=f"員工編號 {employee.employee_code} 已存在。")
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"內部資料儲存錯誤: {e}")
        
    return new_employee

# main.py - 調整 PUT 路由

@app.put("/employees/{employee_id}", response_model=Employee, summary="更新員工", tags=["員工管理"])
def update_employee(employee_id: int, employee_update: EmployeeCreate, session: Session = Depends(get_session)):
    """根據 ID 更新現有員工資料，員工編號若更改必須保持唯一。"""
    
    # 1. 檢查員工是否存在
    old_employee = session.get(Employee, employee_id)
    if not old_employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # 2. 將更新的資料複製到舊物件上
    updated_data = employee_update.model_dump()
    for key, value in updated_data.items():
        setattr(old_employee, key, value)
        
    try:
        session.add(old_employee) 
        session.commit()
        session.refresh(old_employee)
    except IntegrityError:
        # 捕捉資料庫唯一性錯誤 (員工編號與其他記錄重複)
        session.rollback()
        raise HTTPException(status_code=400, detail=f"新員工編號 {employee_update.employee_code} 已被其他員工使用。")
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"內部資料儲存錯誤: {e}")
    
    return old_employee

# main.py - 調整 DELETE 路由

@app.delete("/employees/{employee_id}", status_code=204, summary="刪除員工", tags=["員工管理"])
def delete_employee(employee_id: int, session: Session = Depends(get_session)):
    """根據 ID 刪除特定員工。"""
    
    # 檢查員工是否存在
    employee_to_delete = session.get(Employee, employee_id)
    
    if not employee_to_delete:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # 執行刪除
    session.delete(employee_to_delete)
    session.commit()
    
    # 返回 204 No Content
    return

# main.py - 調整 POST /upload 批次上傳路由

@app.post("/upload", summary="批次上傳 CSV 格式文件", tags=["批次處理"])
async def bulk_upload(file: UploadFile = File(...), session: Session = Depends(get_session)):
    """
    處理上傳的檔案。使用單一事務處理，若有任一筆員工編號衝突，則整批資料撤銷 (Rollback)。
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

    expected_columns = 5 
    if len(header) < expected_columns:
        raise HTTPException(status_code=400, detail="檔案標頭不完整，預期欄位：姓名 (Name), 員工編號 (Code), 職位 (Position), 部門 (Department), 薪資 (Salary)。")

    success_count = 0
    error_entries = []
    
    # 建立一個暫時集合來檢查當前批次中的重複編號
    current_batch_codes = set()

    for row_number, row in enumerate(csv_reader):
        row_num_display = row_number + 2 
        
        # 1. 檢查欄位數量
        if len(row) < expected_columns:
            error_entries.append({"row": row_num_display, "error": "資料欄位不足", "data": row})
            continue
        
        # 2. 欄位擷取與清理
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
            salary = int(float(salary_str)) 
            if salary < 0:
                raise ValueError("薪資必須為正值。")
        except ValueError:
            error_entries.append({"row": row_num_display, "error": f"薪資格式錯誤: '{salary_str}' 不是有效的正整數。", "data": row})
            continue
            
        # 5. 檢查員工編號的唯一性 (僅檢查當前批次內)
        if code in current_batch_codes:
            error_entries.append({"row": row_num_display, "error": f"員工編號 '{code}' 在本次上傳中重複。", "data": row})
            continue
        current_batch_codes.add(code)
            
        # 6. 成功新增資料 (暫時加入 session)
        try:
            employee_data = EmployeeCreate(
                name=name,
                employee_code=code,
                position=position,
                department=department,
                salary=salary
            )
            
            new_employee = Employee.model_validate(employee_data)
            
            session.add(new_employee)
            success_count += 1
            
        except Exception as e:
            error_entries.append({"row": row_num_display, "error": f"資料驗證錯誤: {e}", "data": row})
            if code in current_batch_codes:
                 current_batch_codes.remove(code)


    # 7. 嘗試提交所有成功的記錄
    try:
        session.commit()
    except IntegrityError:
        # 如果批次中有員工編號與既有資料庫記錄衝突，則整批資料撤銷
        session.rollback()
        # 為了簡化，直接將所有記錄視為失敗
        return {"message": "批次上傳失敗。批次中至少一筆記錄的員工編號與既有資料庫記錄衝突，所有記錄已撤銷。", 
                "successful_uploads": 0, 
                "errors": [{"row": "Batch Error", "error": "批次中有員工編號與既有資料庫記錄衝突，所有記錄已撤銷。", "data": "N/A"}] + error_entries}
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"批次資料庫儲存錯誤: {e}")


    message = f"批次上傳完成。成功新增 {success_count} 筆記錄。"
    return {"message": message, "successful_uploads": success_count, "errors": error_entries}