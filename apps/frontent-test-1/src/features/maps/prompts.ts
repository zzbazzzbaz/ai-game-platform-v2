/** 玩法图任务的固定提示词与引用模板。 */

import type { GameMapDetail, GameMapEdge, GameMapNode } from "@/api/maps";

export const GENERATE_MAPS_PROMPT = `【玩法图任务】请根据用户本次要求为当前游戏生成玩法图。先调用 list_game_maps 查看现有图；图的数量、主题、map_id、标题由你根据用户要求和当前游戏代码决定，不固定为四张。读取当前游戏代码后，逐张调用 save_game_map 保存。只更新玩法图，不要修改游戏代码。`;

export const UPDATE_MAPS_PROMPT = `【玩法图任务】请根据当前游戏代码更新已有玩法图。先调用 list_game_maps 获取所有图 id，再逐张调用 get_game_map 读取；只更新已有图，不新增、不删除，除非用户明确要求。逐张调用 save_game_map 保存。只更新玩法图，不要修改游戏代码。`;

export function nodeReferencePrompt(map: GameMapDetail, node: GameMapNode): string {
  return `【玩法图引用】地图：${map.title}（${map.map_id}）；节点：${node.id}（${node.title}）
我的修改：
`;
}

export function edgeReferencePrompt(map: GameMapDetail, edge: GameMapEdge): string {
  const title = edge.title || "未命名连线";
  return `【玩法图引用】地图：${map.title}（${map.map_id}）；连线：${edge.from} -> ${edge.to}（${title}）
我的修改：
`;
}
