"""玩法图工具：读写平台库里的玩法图（不落工作区、不参与发布）。"""

import json
from typing import Any
from urllib.parse import quote

from langchain_core.tools import BaseTool
from langchain_core.tools import tool as make_tool

from agent.core.constants import GAME_MAPS_PATH, INTERNAL_TIMEOUT_SECONDS
from agent.tools.internal_api import InternalApiError, call_internal, call_internal_list


def make_list_game_maps_tool(*, thread_id: str) -> BaseTool:
    """构造 list_game_maps 工具：列出当前游戏已有的玩法图 id。"""

    @make_tool
    def list_game_maps() -> str:
        """列出当前游戏已有的玩法图 id（只返回 id，不含内容）。

        生成或新增图前必须先调用，避免重复创建已有的 map_id；
        没有图时返回「当前游戏还没有玩法图。」
        """
        try:
            ids = call_internal_list(
                f"{GAME_MAPS_PATH}?thread_id={thread_id}",
                timeout=INTERNAL_TIMEOUT_SECONDS,
            )
        except InternalApiError as e:
            return f"列出玩法图失败：{e}"
        if not ids:
            return "当前游戏还没有玩法图。"
        return "当前游戏已有玩法图：" + "、".join(ids)

    return list_game_maps


def make_get_game_map_tool(*, thread_id: str) -> BaseTool:
    """构造 get_game_map 工具：读取一张玩法图的完整 JSON。"""

    @make_tool
    def get_game_map(map_id: str) -> str:
        """读取一张玩法图的完整内容（JSON：title / revision / nodes / edges）。

        map_id 必须是 list_game_maps 返回的 id；更新单张图前必须先调用本工具，
        在现有内容上修改，不要凭空重写无关部分。
        """
        try:
            data = call_internal(
                f"{GAME_MAPS_PATH}/{quote(map_id, safe='')}?thread_id={thread_id}",
                timeout=INTERNAL_TIMEOUT_SECONDS,
                method="GET",
            )
        except InternalApiError as e:
            if e.status_code == 404:
                return f"玩法图不存在：{map_id}"
            return f"读取玩法图失败：{e}"
        return json.dumps(data, ensure_ascii=False)

    return get_game_map


def make_save_game_map_tool(*, thread_id: str) -> BaseTool:
    """构造 save_game_map 工具：整张覆盖保存一张玩法图。"""

    @make_tool
    def save_game_map(
        map_id: str,
        title: str,
        nodes: list[dict[str, Any]],
        edges: list[dict[str, Any]],
    ) -> str:
        """保存一张玩法图（整张覆盖；新建 revision=1，更新 revision+1）。

        只有用户明确要求生成/更新玩法图、追加图，或从玩法图引用发起修改时才调用。
        map_id 沿用已有图时是更新；新图必须用 list_game_maps 里不存在的 id。
        map_id 只能用小写字母、数字、中划线：1–32 位，字母开头、字母或数字结尾
        （例如 core-loop、rules、levels-2），不能使用中文、下划线或大写字母。
        title 为 1–20 个字的玩家可读标题。

        nodes 每项：
          id（图内唯一的英文短标识，字母/数字/中划线/下划线）、
          title（1–30 字）、
          detail（可省略，≤200 字）、
          attributes（可省略，字符串数组，最多 8 项）、
          kind（可省略：start/action/decision/reward/penalty/end/note/value/level，默认 action）。
        edges 每项：
          from、to（必须是 nodes 里的 id）、
          title（可省略）、detail（可省略）、attributes（可省略）、
          kind（可省略：normal/success/failure/loop，默认 normal）。
        一张图 1–40 个节点、最多 80 条连线；内容必须是中文玩家可读文本。
        """
        try:
            data = call_internal(
                f"{GAME_MAPS_PATH}/{quote(map_id, safe='')}",
                {
                    "thread_id": thread_id,
                    "title": title,
                    "nodes": nodes,
                    "edges": edges,
                },
                timeout=INTERNAL_TIMEOUT_SECONDS,
                method="PUT",
            )
        except InternalApiError as e:
            return f"保存玩法图失败：{e}"
        return (
            f"已保存玩法图 {data['title']}（{data['map_id']}），"
            f"revision {data['revision']}。"
        )

    return save_game_map
