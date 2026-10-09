"""
学习用 CRUD demo 的后端（FastAPI + PostgreSQL）。

数据流：Vue 前端 --HTTP JSON--> 这里（FastAPI）--SQL--> PostgreSQL
每个 REST 端点对应一条 SQL，方便你把「HTTP 请求」和「SQL」对上。
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .db import pool


@asynccontextmanager
async def lifespan(app: FastAPI):
    pool.open()      # 启动时打开连接池
    yield
    pool.close()     # 关闭时释放


app = FastAPI(title="CRUD Demo API", version="0.1.0", lifespan=lifespan)

# 学习用：允许任意来源的跨域（正式环境要收敛到具体域名）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- 请求体模型（FastAPI 会自动校验并生成文档） ----------
class TodoCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)


class TodoUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    done: bool | None = None


# ---------- 健康检查 ----------
@app.get("/api/health")
def health():
    return {"ok": True}


# ---------- 查（列表） ----------
@app.get("/api/todos")
def list_todos():
    with pool.connection() as conn, conn.cursor() as cur:
        cur.execute(
            "select id, title, done, created_at "
            "from public.todos order by id desc"
        )
        return cur.fetchall()


# ---------- 增 ----------
@app.post("/api/todos", status_code=201)
def create_todo(body: TodoCreate):
    with pool.connection() as conn, conn.cursor() as cur:
        cur.execute(
            "insert into public.todos (title) values (%s) "
            "returning id, title, done, created_at",
            (body.title,),
        )
        return cur.fetchone()


# ---------- 改（部分更新） ----------
@app.patch("/api/todos/{todo_id}")
def update_todo(todo_id: int, body: TodoUpdate):
    sets, values = [], []
    if body.title is not None:
        sets.append("title = %s")
        values.append(body.title)
    if body.done is not None:
        sets.append("done = %s")
        values.append(body.done)
    if not sets:
        raise HTTPException(status_code=400, detail="没有需要更新的字段")

    values.append(todo_id)
    with pool.connection() as conn, conn.cursor() as cur:
        cur.execute(
            f"update public.todos set {', '.join(sets)} "
            "where id = %s returning id, title, done, created_at",
            values,
        )
        row = cur.fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="todo 不存在")
        return row


# ---------- 删 ----------
@app.delete("/api/todos/{todo_id}", status_code=204)
def delete_todo(todo_id: int):
    with pool.connection() as conn, conn.cursor() as cur:
        cur.execute("delete from public.todos where id = %s", (todo_id,))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="todo 不存在")
    return None
