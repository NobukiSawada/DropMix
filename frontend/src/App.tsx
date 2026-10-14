import { useCallback, useEffect, useState } from "react";
import { type FileRejection, useDropzone } from "react-dropzone";
import { toast, Toaster } from "sonner";

import { DropOverlay, EmptyState } from "@/components/EmptyState";
import { FileChips, GridToolbar } from "@/components/GridToolbar";
import { Header } from "@/components/Header";
import { PageGrid } from "@/components/PageGrid";
import { ToolPanel } from "@/components/ToolPanel";
import { TooltipProvider } from "@/components/ui/tooltip";
import { UnlockDialog } from "@/components/UnlockDialog";
import { useUploader } from "@/hooks/useUploader";
import { api } from "@/lib/api";
import { useStore } from "@/store";

const ACCEPT = {
  "application/pdf": [".pdf"],
  "image/jpeg": [".jpg", ".jpeg"],
  "image/png": [".png"],
  "image/webp": [".webp"],
  "image/bmp": [".bmp"],
  "image/gif": [".gif"],
  "image/tiff": [".tif", ".tiff"],
};

function isTextInput(target: EventTarget | null): boolean {
  return target instanceof HTMLElement && (target.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName));
}

export default function App() {
  const upload = useUploader();
  const hasFiles = useStore((s) => s.fileOrder.length > 0);
  const hasPages = useStore((s) => s.pages.length > 0);
  const removeFile = useStore((s) => s.removeFile);
  const clearAll = useStore((s) => s.clearAll);
  const [unlockId, setUnlockId] = useState<string | null>(null);

  const onDrop = useCallback(
    (accepted: File[], rejected: FileRejection[]) => {
      if (rejected.length) toast.warning(`${rejected.length} 件のファイルは未対応の形式のためスキップしました`);
      if (accepted.length) void upload(accepted);
    },
    [upload],
  );
  // ウィンドウ全体をドロップ領域にする (クリックでのファイル選択は個別ボタンから)
  const { getRootProps, getInputProps, isDragActive, open } = useDropzone({
    onDrop,
    accept: ACCEPT,
    noClick: true,
    noKeyboard: true,
    multiple: true,
  });

  // 最初にロック中のファイルが追加されたら自動でパスワード入力を開く
  const firstLocked = useStore((s) => s.fileOrder.find((id) => s.files[id]?.locked) ?? null);
  useEffect(() => {
    if (firstLocked && !useStore.getState().task) setUnlockId((cur) => cur ?? firstLocked);
  }, [firstLocked]);

  const handleRemove = useCallback(
    async (fileId: string) => {
      removeFile(fileId);
      try {
        await api.deleteFile(fileId);
      } catch {
        // 既に存在しない場合などは無視
      }
    },
    [removeFile],
  );

  const handleClearAll = useCallback(async () => {
    clearAll();
    try {
      await api.clearFiles();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : String(e));
    }
  }, [clearAll]);

  // キーボードショートカット
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (isTextInput(e.target) || document.querySelector("[role=dialog]")) return;
      const s = useStore.getState();
      const mod = e.ctrlKey || e.metaKey;
      if (mod && e.key.toLowerCase() === "z" && !e.shiftKey) {
        e.preventDefault();
        s.undo();
      } else if (mod && (e.key.toLowerCase() === "y" || (e.key.toLowerCase() === "z" && e.shiftKey))) {
        e.preventDefault();
        s.redo();
      } else if (mod && e.key.toLowerCase() === "a") {
        e.preventDefault();
        s.selectAll();
      } else if (mod && e.key.toLowerCase() === "o") {
        e.preventDefault();
        open();
      } else if ((e.key === "Delete" || e.key === "Backspace") && s.selected.size) {
        e.preventDefault();
        s.deletePages([...s.selected]);
      } else if (e.key === "Escape" && s.selected.size) {
        s.clearSelection();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  return (
    <TooltipProvider delayDuration={400}>
      <div {...getRootProps({ className: "flex h-full flex-col outline-none" })}>
        <input {...getInputProps()} />
        <Header onAddFiles={open} onClearAll={() => void handleClearAll()} />
        <div className="flex min-h-0 flex-1">
          <main className="flex min-w-0 flex-1 flex-col bg-muted/40">
            {hasFiles ? (
              <>
                <div className="grid gap-3 border-b bg-white/80 px-5 py-3">
                  <FileChips onUnlock={setUnlockId} onRemove={(id) => void handleRemove(id)} />
                  <GridToolbar />
                </div>
                <div
                  className="min-h-0 flex-1 overflow-y-auto"
                  onClick={(e) => {
                    // 余白クリックで選択解除
                    if (e.target === e.currentTarget) useStore.getState().clearSelection();
                  }}
                >
                  {hasPages ? (
                    <PageGrid />
                  ) : (
                    <p className="p-10 text-center text-sm text-muted-foreground">
                      表示できるページがありません。パスワード付きPDFはロックを解除するか、ファイルを追加してください。
                    </p>
                  )}
                </div>
              </>
            ) : (
              <EmptyState onBrowse={open} />
            )}
          </main>
          <ToolPanel />
        </div>
        {isDragActive && <DropOverlay />}
      </div>
      <UnlockDialog fileId={unlockId} onClose={() => setUnlockId(null)} />
      <Toaster
        position="bottom-left"
        closeButton
        toastOptions={{
          classNames: {
            toast: "!rounded-xl !border !shadow-lg !font-sans",
            success: "!border-green-200 !bg-green-50 !text-green-900 [&_[data-icon]]:!text-green-600",
            error: "!border-red-200 !bg-red-50 !text-red-900",
            warning: "!border-amber-200 !bg-amber-50 !text-amber-900",
            info: "!border-green-200 !bg-white !text-foreground [&_[data-icon]]:!text-green-600",
            actionButton: "!bg-primary !text-white",
            description: "!text-current !opacity-75 !break-all",
          },
        }}
      />
    </TooltipProvider>
  );
}
