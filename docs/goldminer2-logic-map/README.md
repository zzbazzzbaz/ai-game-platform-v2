# 黄金矿工2 · 玩法地图（React Flow 原型）

面向没有代码基础的用户：只讲玩法，不出现源码、节点、连线、坐标等术语。

## 启动

```bash
npm install
npm run dev
```

打开 http://localhost:5188

## 四个图

| 文件 | 页面 |
|---|---|
| `src/data/loop.json` | 怎么玩 |
| `src/data/states.json` | 游戏流程 |
| `src/data/hook.json` | 抓取规则 |
| `src/data/levels.json` | 关卡与奖励 |

## node 只有四个字段

```json
{
  "id": "launch",
  "title": "按一下",
  "detail": "空格或点屏幕，钩子飞出去",
  "attributes": ["左右各约 60°"]
}
```

- `id`：连线用
- `title`：卡片标题
- `detail`：点开后的说明
- `attributes`：字符串数组，只放值，没有 key

卡片只显示标题；数值卡显示第一个属性，关卡卡显示目标和限时。点开后显示 `detail` + 所有属性值。

## edge 只有这些字段

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

- `from` / `to`：起点、终点
- `title`：分叉/回环说明，可选
- `detail`：点开后的说明，可选
- `attributes`：字符串数组，可选

节点和连线都可以点开。连线详情显示 `title`、`detail` 和属性值。

## 前端固定

| 位置 | 内容 |
|---|---|
| `src/layout.js` | 坐标、节点类型、回环走线、透明占位 |
| `src/ui.js` | 页面标题、按钮文案、图例、Tab 图标 |
| `src/styles.css` | 颜色、卡片、连线、详情面板 |
| `src/components/` | 渲染组件 |

节点类型/颜色只在 `src/layout.js` 的 `types` 里写，JSON 不关心样式。

## 样式

- 所有样式在 `src/styles.css`，不引外部主题、外部字体或 CDN。
- React Flow 的基础布局样式也在本地，不 import 它的默认样式表。
- 配色为靛蓝 / 天蓝 / 翠绿 / 紫 / 石板灰 / 棕铜，不使用黄色。
- 节点不显示图标；卡片只显示标题，详情只显示一句说明 + 值。
