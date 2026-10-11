/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** 平台后端基地址（默认 /api/v1，经 Vite/Nginx 代理） */
  readonly VITE_API_BASE_URL: string;
  /** LangGraph Server 基地址（默认 /lg，经 Vite/Nginx 代理） */
  readonly VITE_LG_BASE_URL: string;
  /** LangGraph 图 ID */
  readonly VITE_LG_ASSISTANT_ID: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
