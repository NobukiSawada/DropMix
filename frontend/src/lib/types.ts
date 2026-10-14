export interface FileInfo {
  id: string;
  name: string;
  kind: "pdf" | "image";
  size: number;
  locked: boolean;
  page_count: number;
  pages: { width: number; height: number }[];
}

/** グリッド上の1ページ。並び順・回転はフロントエンドで管理する */
export interface PageItem {
  uid: string;
  fileId: string;
  index: number;
  rotation: number; // 追加の回転 (0/90/180/270)
}

export interface OutputResult {
  id: string;
  files: string[];
  download_name: string;
  total_size: number;
  size_before?: number;
  size_after?: number;
}

export type ToolId = "merge" | "split" | "images" | "compress" | "watermark" | "pagenum" | "protect";

export interface PageSpec {
  file_id: string;
  index: number;
  rotation: number;
}
