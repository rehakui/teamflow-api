from fastapi import FastAPI
from .database import engine
from .models import Base
from fastapi import Depends
from sqlalchemy.orm import Session
from .database import SessionLocal
from .models import User, Project, Task
import bcrypt
from fastapi import HTTPException
from jose import jwt
from datetime import datetime, timedelta
import bcrypt
from sqlalchemy import select
from fastapi import Header
from jose import JWTError
from sqlalchemy import select
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
import os
from dotenv import load_dotenv
from pydantic import BaseModel
from typing import Optional
from fastapi import HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select


load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

app = FastAPI()

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:63342",  # 今のPyCharmのURL
        "http://127.0.0.1:63342",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],  # Authorizationを通すため必須
)

Base.metadata.create_all(bind=engine)



@app.get("/")
def root():
    return {"message": "TeamFlow is running"}

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/register")
def register(name: str, email: str, password: str, db: Session = Depends(get_db)):
    hashed_password = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())

    user = User(
        name=name,
        email=email,
        hashed_password=hashed_password.decode("utf-8")
    )

    db.add(user)
    db.commit()

    return {"message": "User created"}

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

@app.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.execute(select(User).where(User.email == form_data.username)).scalar_one_or_none()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Invalid email or password")

    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return {"access_token": access_token, "token_type": "bearer"}

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.execute(select(User).where(User.id == int(user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user

@app.get("/projects")
def list_projects(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    projects = db.execute(
        select(Project).where(Project.owner_id == current_user.id)
    ).scalars().all()

    return [{"id": p.id, "name": p.name} for p in projects]

@app.delete("/projects/{project_id}")
def delete_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    project = db.execute(
        select(Project).where(Project.id == project_id, Project.owner_id == current_user.id)
    ).scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    db.delete(project)
    db.commit()
    return {"message": "Deleted"}

@app.post("/projects")
def create_project(
    name: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    project = Project(name=name, owner_id=current_user.id)
    db.add(project)
    db.commit()
    db.refresh(project)
    return {"id": project.id, "name": project.name}

class TaskCreate(BaseModel):
    title: str
    description: str = ""
    due_date: Optional[str] = None

@app.post("/projects/{project_id}/tasks")
def create_task(
    project_id: int,
    payload: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    title = payload.title
    description = payload.description
    due_date = payload.due_date

    # プロジェクト存在チェック（オーナーのみ操作可）
    project = db.execute(
        select(Project).where(Project.id == project_id, Project.owner_id == current_user.id)
    ).scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    task = Task(
        title=title,
        description=description,
        due_date=due_date,
        project_id=project_id,
        status="todo",
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return {"id": task.id, "title": task.title, "status": task.status}

@app.get("/projects/{project_id}/tasks")
def list_tasks(
    project_id: int,
    status: str | None = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    project = db.execute(
        select(Project).where(Project.id == project_id, Project.owner_id == current_user.id)
    ).scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    query = select(Task).where(Task.project_id == project_id)
    if status:
        query = query.where(Task.status == status)

    tasks = db.execute(query).scalars().all()
    return [
        {
            "id": t.id,
            "title": t.title,
            "description": t.description,
            "status": t.status,
            "due_date": t.due_date,
            "assignee_id": t.assignee_id,
        }
        for t in tasks
    ]

@app.patch("/tasks/{task_id}/status")
def update_task_status(
    task_id: int,
    status: str,  # todo / doing / done
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    if status not in {"todo", "doing", "done"}:
        raise HTTPException(status_code=400, detail="Invalid status")

    task = db.execute(select(Task).where(Task.id == task_id)).scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # オーナーのプロジェクト配下かチェック
    project = db.execute(
        select(Project).where(Project.id == task.project_id, Project.owner_id == current_user.id)
    ).scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=403, detail="Not allowed")

    task.status = status
    db.commit()
    db.refresh(task)
    return {"id": task.id, "status": task.status}

# 既に get_db, get_current_user, Task を使ってる前提
@app.delete("/tasks/{task_id}")
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = db.execute(select(Task).where(Task.id == task_id)).scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # もし「自分のプロジェクト配下だけ削除可」にしたいならここでチェック
    project = db.execute(select(Project).where(Project.id == task.project_id)).scalar_one_or_none()
    if not project or project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not allowed")

    db.delete(task)
    db.commit()
    return {"message": "deleted", "id": task_id}