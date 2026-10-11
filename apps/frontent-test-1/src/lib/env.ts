/** 运行期配置：全部来自环境变量（本地配置源 apps/.env），缺失即报错。 */

function requireEnv(name: keyof ImportMetaEnv): string {
  const value = import.meta.env[name];
  if (!value) {
    throw new Error(`缺少环境变量 ${name}（本地配置源：apps/.env）`);
  }
  return value;
}

export const env = {
  apiBaseUrl: requireEnv("VITE_API_BASE_URL"),
  lgBaseUrl: requireEnv("VITE_LG_BASE_URL"),
  lgAssistantId: requireEnv("VITE_LG_ASSISTANT_ID"),
} as const;
