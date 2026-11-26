# 数据结构

`src/data` 里每个图一个 JSON：

| 文件 | 图 |
|---|---|
| `loop.json` | 怎么玩 |
| `states.json` | 游戏流程 |
| `hook.json` | 抓取规则 |
| `levels.json` | 关卡与奖励 |

JSON 只放图的内容，不放样式、坐标、类型。

## node

只保留四个字段：

```json
{
  "id": "launch",
  "title": "按一下",
  "detail": "空格或点屏幕，钩子飞出去",
  "attributes": ["左右各约 60°"]
}
```

| 字段 | 说明 |
|---|---|
| `id` | 唯一标识，连线用 |
| `title` | 卡片标题 |
| `detail` | 点开后的说明 |
| `attributes` | 这个节点的值，字符串数组，可选；没有 key |

`attributes` 只放值，例如：

```json
["目标 320 分", "限时 110 秒", "1 颗钻石"]
["60 分"]
["左右各约 60°"]
```

展示约定：

- 普通卡片：只显示 `title`。
- 数值卡：显示 `title` + `attributes[0]`。
- 关卡卡：显示 `title` + `attributes[0]`（目标）+ `attributes[1]`（限时）。
- 点开后：`title`、`detail`、所有 `attributes` 值。

节点类型/颜色不在 JSON 里，在 `src/layout.js` 的 `types`：

```js
types: {
  start: "start",
  swing: "action",
  hit: "decision",
  pass: "end",
  "v-gold": "gold"
}
```

## edge

只保留这些字段：

```json
{ "from": "launch", "to": "hit" }
```

```json
{
  "from": "hit",
  "to": "grab",
  "title": "碰到了"
}
```

| 字段 | 说明 |
|---|---|
| `from` | 起点 id |
| `to` | 终点 id |
| `title` | 分叉/回环的说明，可选 |
| `detail` | 点开后的说明，可选；不写就显示「从 A 走到 B」 |
| `attributes` | 字符串数组，可选 |

线的样式（普通 / 分叉 / 回环 / 过关 / 虚线）由前端根据节点类型和 `src/layout.js` 的 routes 自动判断，不在 JSON 里写。

## view

```json
{
  "id": "loop",
  "tab": "怎么玩",
  "nodes": [],
  "edges": []
}
```

`title` / `subtitle` 已删除，页面不显示。
