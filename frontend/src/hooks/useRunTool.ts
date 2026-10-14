import { useCallback } from "react";
import { toast } from "sonner";

import { api, desktopApi, saveOutput } from "@/lib/api";
import type { OutputResult } from "@/lib/types";
import { targetPages, toPageSpecs, useStore } from "@/store";

/** 保存して結果をトーストで知らせる */
export async function saveAndNotify(output: OutputResult) {
  try {
    const res = await saveOutput(output);
    if (!res.saved) return; // ダイアログでキャンセル
    const desktop = desktopApi();
    const path = res.path;
    toast.success("保存しました", {
      description: path ?? output.download_name,
      action:
        desktop && path
          ? {
              label: "フォルダを開く",
              onClick: () => void desktop.open_path(path),
            }
          : undefined,
    });
  } catch (e) {
    toast.error(e instanceof Error ? e.message : String(e));
  }
}

export function useRunTool() {
  const setTask = useStore((s) => s.setTask);
  const setResult = useStore((s) => s.setResult);

  return useCallback(
    async (endpoint: string, label: string, options: Record<string, unknown> = {}) => {
      const state = useStore.getState();
      if (state.task) return;
      const pages = targetPages(state);
      if (!pages.length) {
        toast.warning("ページがありません。ファイルを追加してください");
        return;
      }
      setTask({ label, progress: null });
      setResult(null);
      try {
        const result = await api.runTool(endpoint, { pages: toPageSpecs(pages), ...options });
        setResult(result);
        setTask(null);
        await saveAndNotify(result);
      } catch (e) {
        toast.error(e instanceof Error ? e.message : String(e));
      } finally {
        setTask(null);
      }
    },
    [setTask, setResult],
  );
}
