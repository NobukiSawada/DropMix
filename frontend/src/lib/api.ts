import type { FileInfo, OutputResult } from "./types";

/**
 * デスクトップ版はランダムなトークン付き URL (`?token=...`) で起動される。
 * API へのリクエストには必ずこのトークンを付与する。
 */
const TOKEN = new URLSearchParams(window.location.search).get("token") ?? "";

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

function headers(extra?: Record<string, string>): Record<string, string> {
  return { ...(TOKEN ? { "X-DropMix-Token": TOKEN } : {}), ...extra };
}

function withToken(url: string): string {
  if (!TOKEN) return url;
  return `${url}${url.includes("?") ? "&" : "?"}token=${encodeURIComponent(TOKEN)}`;
}

function errorMessage(body: unknown, status: number): string {
  if (body && typeof body === "object" && "detail" in body) {
    const detail = (body as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      return detail.map((d) => (d && typeof d === "object" && "msg" in d ? String(d.msg) : String(d))).join("\n");
    }
  }
  if (status === 0) return "サーバーに接続できませんでした";
  return `エラーが発生しました (HTTP ${status})`;
}

async function request<T>(method: string, url: string, body?: unknown): Promise<T> {
  let res: Response;
  try {
    res = await fetch(url, {
      method,
      headers: headers(body !== undefined ? { "Content-Type": "application/json" } : undefined),
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new ApiError("サーバーに接続できませんでした", 0);
  }
  const data = await res.json().catch(() => null);
  if (!res.ok) throw new ApiError(errorMessage(data, res.status), res.status);
  return data as T;
}

/** 1ファイルをアップロードする (進捗コールバック付き) */
export function uploadFile(file: File, onProgress?: (loaded: number) => void): Promise<FileInfo> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", "/api/files");
    for (const [k, v] of Object.entries(headers())) xhr.setRequestHeader(k, v);
    xhr.responseType = "json";
    xhr.upload.onprogress = (e) => onProgress?.(e.loaded);
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) resolve(xhr.response as FileInfo);
      else reject(new ApiError(errorMessage(xhr.response, xhr.status), xhr.status));
    };
    xhr.onerror = () => reject(new ApiError("サーバーに接続できませんでした", 0));
    const form = new FormData();
    form.append("file", file, file.name);
    xhr.send(form);
  });
}

export const api = {
  unlock: (fileId: string, password: string) =>
    request<FileInfo>("POST", `/api/files/${fileId}/unlock`, { password }),
  deleteFile: (fileId: string) => request<{ ok: boolean }>("DELETE", `/api/files/${fileId}`),
  clearFiles: () => request<{ ok: boolean }>("DELETE", "/api/files"),
  runTool: (endpoint: string, body: unknown) => request<OutputResult>("POST", `/api/${endpoint}`, body),
};

export function thumbnailUrl(fileId: string, index: number, width: number): string {
  return withToken(`/api/files/${fileId}/pages/${index}/thumbnail?w=${width}`);
}

export function downloadUrl(outputId: string): string {
  return withToken(`/api/outputs/${outputId}/download`);
}

// ---------------------------------------------------------------------------
// 保存処理: デスクトップ版 (PyWebView) はネイティブの保存ダイアログ、
// ブラウザ (開発時) は通常のダウンロードを使う。
// ---------------------------------------------------------------------------

interface DesktopApi {
  save_output(outputId: string): Promise<{ saved: boolean; path?: string; error?: string }>;
  open_path(path: string): Promise<boolean>;
}

declare global {
  interface Window {
    pywebview?: { api: DesktopApi };
  }
}

export function desktopApi(): DesktopApi | null {
  return window.pywebview?.api?.save_output ? window.pywebview.api : null;
}

export type SaveResult = { saved: boolean; path?: string };

export async function saveOutput(output: OutputResult): Promise<SaveResult> {
  const desktop = desktopApi();
  if (desktop) {
    const res = await desktop.save_output(output.id);
    if (res.error) throw new ApiError(res.error, 500);
    return res;
  }
  const a = document.createElement("a");
  a.href = downloadUrl(output.id);
  a.download = output.download_name;
  document.body.appendChild(a);
  a.click();
  a.remove();
  return { saved: true };
}
