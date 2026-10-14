import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatBytes(bytes: number): string {
  if (!Number.isFinite(bytes) || bytes < 0) return "-";
  if (bytes < 1024) return `${bytes} B`;
  const units = ["KB", "MB", "GB"];
  let value = bytes / 1024;
  let i = 0;
  while (value >= 1024 && i < units.length - 1) {
    value /= 1024;
    i++;
  }
  return `${value.toFixed(value >= 100 ? 0 : 1)} ${units[i]}`;
}

/** ファイルごとに割り当てる見分け用の色 */
const FILE_COLORS = ["#16a34a", "#0891b2", "#7c3aed", "#db2777", "#ea580c", "#ca8a04", "#2563eb", "#0d9488"];

export function fileColor(n: number): string {
  return FILE_COLORS[n % FILE_COLORS.length];
}
