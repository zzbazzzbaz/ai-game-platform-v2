<script setup>
import { ref, onMounted } from 'vue'
import { listTodos, createTodo, updateTodo, deleteTodo } from './api'

const todos = ref([])      // 列表数据
const title = ref('')      // 输入框
const error = ref('')
const loading = ref(false)

// 从后端拉取列表（GET /api/todos）
async function refresh() {
  loading.value = true
  try {
    todos.value = await listTodos()
    error.value = ''
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

// 新增（POST /api/todos）
async function add() {
  const t = title.value.trim()
  if (!t) return
  try {
    await createTodo(t)
    title.value = ''
    await refresh()
  } catch (e) {
    error.value = e.message
  }
}

// 切换完成状态（PATCH /api/todos/{id}）
async function toggle(todo) {
  try {
    await updateTodo(todo.id, { done: !todo.done })
    await refresh()
  } catch (e) {
    error.value = e.message
  }
}

// 删除（DELETE /api/todos/{id}）
async function remove(todo) {
  try {
    await deleteTodo(todo.id)
    await refresh()
  } catch (e) {
    error.value = e.message
  }
}

onMounted(refresh)
</script>

<template>
  <main>
    <h1>待办清单 · CRUD Demo</h1>
    <p class="hint">Vue（这个页面） → FastAPI（8000） → PostgreSQL（5432）</p>

    <form class="row" @submit.prevent="add">
      <input v-model="title" placeholder="要做什么？回车或点添加" maxlength="200" />
      <button type="submit">添加</button>
    </form>

    <p v-if="error" class="error">出错了：{{ error }}</p>
    <p v-if="loading" class="hint">加载中…</p>

    <ul v-if="todos.length">
      <li v-for="t in todos" :key="t.id" :class="{ done: t.done }">
        <label>
          <input type="checkbox" :checked="t.done" @change="toggle(t)" />
          <span>{{ t.title }}</span>
        </label>
        <button class="del" @click="remove(t)">删除</button>
      </li>
    </ul>
    <p v-else-if="!loading" class="hint">还没有待办，加一条试试。</p>
  </main>
</template>

<style>
:root {
  color-scheme: light dark;
}
body {
  margin: 0;
  font-family: -apple-system, "PingFang SC", "Microsoft YaHei", sans-serif;
  background: #f6f7f9;
}
main {
  max-width: 560px;
  margin: 48px auto;
  padding: 24px 28px;
  background: #fff;
  border-radius: 14px;
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.06);
}
h1 {
  font-size: 20px;
  margin: 0 0 4px;
}
.hint {
  color: #8a8f98;
  font-size: 13px;
  margin: 4px 0 16px;
}
.error {
  color: #d92d20;
  font-size: 13px;
}
.row {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
}
.row input {
  flex: 1;
  padding: 10px 12px;
  border: 1px solid #d0d5dd;
  border-radius: 8px;
  font-size: 14px;
}
.row button {
  padding: 10px 16px;
  border: 0;
  border-radius: 8px;
  background: #2563eb;
  color: #fff;
  font-size: 14px;
  cursor: pointer;
}
ul {
  list-style: none;
  padding: 0;
  margin: 0;
}
li {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 4px;
  border-bottom: 1px solid #eef0f3;
}
li label {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
}
li.done span {
  text-decoration: line-through;
  color: #98a2b3;
}
.del {
  border: 0;
  background: transparent;
  color: #d92d20;
  cursor: pointer;
  font-size: 13px;
}
</style>
