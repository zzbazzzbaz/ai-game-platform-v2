/** 资源上传：api 预签名 → 浏览器直传 COS → api 确认。 */

import { apiFetch } from "./client";

export interface PresignAssetResponse {
  asset_id: string;
  filename: string;
  key: string;
  upload_url: string;
  method: "PUT";
  headers: Record<string, string>;
  expires_at: string;
  sandbox_path: string;
}

export interface AssetResponse {
  asset_id: string;
  filename: string;
  key: string;
  size: number;
  content_type: string;
  sandbox_path: string;
}

export interface AssetListItem {
  asset_id: string;
  filename: string;
  key: string;
  size: number;
  last_modified: string | null;
  sandbox_path: string;
}

function presignAsset(gameId: string, file: File): Promise<PresignAssetResponse> {
  return apiFetch<PresignAssetResponse>(`/games/${gameId}/assets/presign`, {
    method: "POST",
    body: {
      filename: file.name,
      content_type: file.type || "application/octet-stream",
      size: file.size,
    },
  });
}

async function uploadToCos(presign: PresignAssetResponse, file: File): Promise<void> {
  let response: Response;
  try {
    // 预签名 URL 自带鉴权；直传 COS 不能带平台的 Authorization。
    response = await fetch(presign.upload_url, {
      method: presign.method,
      headers: presign.headers,
      body: file,
    });
  } catch {
    throw new Error("直传 COS 失败，请检查网络或对象存储 CORS 配置");
  }
  if (!response.ok) {
    throw new Error(`上传失败（HTTP ${response.status}）`);
  }
}

function completeAsset(
  gameId: string,
  assetId: string,
  filename: string,
): Promise<AssetResponse> {
  return apiFetch<AssetResponse>(`/games/${gameId}/assets/${assetId}/complete`, {
    method: "POST",
    body: { filename },
  });
}

/** 完整上传一个文件：预签名 → PUT → 确认。 */
export async function uploadAsset(gameId: string, file: File): Promise<AssetResponse> {
  const presign = await presignAsset(gameId, file);
  await uploadToCos(presign, file);
  return completeAsset(gameId, presign.asset_id, presign.filename);
}

export function listAssets(gameId: string): Promise<AssetListItem[]> {
  return apiFetch<AssetListItem[]>(`/games/${gameId}/assets`);
}

export function deleteAsset(gameId: string, assetId: string): Promise<void> {
  return apiFetch<void>(`/games/${gameId}/assets/${assetId}`, { method: "DELETE" });
}
