// 前端只跟后端说话（/api 由 Vite 代理到 FastAPI）。
// 这里把 4 个 REST 端点各封装成一个函数，方便对照学习。

const BASE = '/api'

async function request(method, path, body) {
  const res = await fetch(BASE + path, {
    method,
    headers: body ? { 'Content-Type': 'application/json' } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  })

  if (res.status === 204) return null // 删除成功没有响应体

  const data = await res.json().catch(() => null)
  if (!res.ok) {
    throw new Error((data && data.detail) || res.statusText)
  }
  return data
}

export const listTodos = () => request('GET', '/todos')
export const createTodo = (title) => request('POST', '/todos', { title })
export const updateTodo = (id, patch) => request('PATCH', `/todos/${id}`, patch)
export const deleteTodo = (id) => request('DELETE', `/todos/${id}`)
