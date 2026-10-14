import { useCallback } from "react";
import { toast } from "sonner";

import { uploadFile } from "@/lib/api";
import { useStore } from "@/store";

const ACCEPTED = /\.(pdf|jpe?g|png|webp|bmp|gif|tiff?)$/i;

export function useUploader() {
  const addFile = useStore((s) => s.addFile);
  const setTask = useStore((s) => s.setTask);

  return useCallback(
    async (files: File[]) => {
      const valid = files.filter((f) => ACCEPTED.test(f.name));
      const skipped = files.length - valid.length;
      if (skipped > 0) toast.warning(`${skipped} 件のファイルは未対応の形式のためスキップしました`);
      if (!valid.length) return;
      if (useStore.getState().task) {
        toast.warning("処理中です。完了してからもう一度お試しください");
        return;
      }

      const total = valid.reduce((sum, f) => sum + f.size, 0) || 1;
      let done = 0;
      let added = 0;
      let locked = 0;
      // ドロップした順序を保つため 1 ファイルずつ送る
      for (const [i, file] of valid.entries()) {
        const label = valid.length > 1 ? `読み込み中 (${i + 1}/${valid.length}) ${file.name}` : `読み込み中 ${file.name}`;
        setTask({ label, progress: done / total });
        try {
          const info = await uploadFile(file, (loaded) => setTask({ label, progress: (done + loaded) / total }));
          addFile(info);
          added++;
          if (info.locked) locked++;
        } catch (e) {
          toast.error(e instanceof Error ? e.message : String(e));
        }
        done += file.size;
      }
      setTask(null);
      if (added) {
        toast.success(`${added} 件のファイルを追加しました`);
      }
      if (locked) {
        toast.info(`${locked} 件のPDFはパスワードで保護されています。鍵アイコンからロックを解除してください`);
      }
    },
    [addFile, setTask],
  );
}
