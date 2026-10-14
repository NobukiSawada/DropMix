import { ChevronLeft, ChevronRight, RotateCcw, RotateCw, Trash2 } from "lucide-react";
import { useEffect } from "react";

import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "@/components/ui/dialog";
import { useStore } from "@/store";

import { PageThumb } from "./PageThumb";

const PREVIEW_SIZE = 900;

export function PreviewDialog({ uid, onUidChange }: { uid: string | null; onUidChange: (uid: string | null) => void }) {
  const pages = useStore((s) => s.pages);
  const files = useStore((s) => s.files);
  const rotatePages = useStore((s) => s.rotatePages);
  const deletePages = useStore((s) => s.deletePages);

  const index = uid ? pages.findIndex((p) => p.uid === uid) : -1;
  const page = index >= 0 ? pages[index] : null;
  const file = page ? files[page.fileId] : null;

  useEffect(() => {
    if (uid && index < 0) onUidChange(null);
  }, [uid, index, onUidChange]);

  const go = (delta: number) => {
    const next = pages[index + delta];
    if (next) onUidChange(next.uid);
  };

  return (
    <Dialog open={!!page} onOpenChange={(open) => !open && onUidChange(null)}>
      <DialogContent
        className="max-w-none gap-3 p-4 sm:w-auto"
        onKeyDown={(e) => {
          if (e.key === "ArrowLeft") go(-1);
          if (e.key === "ArrowRight") go(1);
        }}
      >
        {page && file && (
          <>
            <div className="flex items-center gap-3 pr-8">
              <span className="size-2.5 rounded-full" style={{ backgroundColor: file.color }} />
              <div className="min-w-0">
                <DialogTitle className="truncate text-sm">{file.name}</DialogTitle>
                <DialogDescription className="text-xs">
                  {index + 1} / {pages.length} ページ目（元ファイルの p.{page.index + 1}）
                </DialogDescription>
              </div>
            </div>
            <div
              className="flex items-center justify-center rounded-lg bg-muted"
              style={{ width: "min(76vh, 80vw)", height: "min(76vh, 80vw)" }}
            >
              <PageThumb
                key={page.uid}
                fileId={page.fileId}
                index={page.index}
                rotation={page.rotation}
                size={PREVIEW_SIZE}
                className="h-full w-full p-3"
              />
            </div>
            <div className="flex items-center justify-between gap-2">
              <Button variant="outline" size="sm" onClick={() => go(-1)} disabled={index <= 0}>
                <ChevronLeft /> 前へ
              </Button>
              <div className="flex gap-1.5">
                <Button variant="outline" size="sm" onClick={() => rotatePages([page.uid], -90)}>
                  <RotateCcw /> 左回転
                </Button>
                <Button variant="outline" size="sm" onClick={() => rotatePages([page.uid], 90)}>
                  <RotateCw /> 右回転
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  className="hover:border-red-200 hover:bg-red-50 hover:text-destructive"
                  onClick={() => {
                    const next = pages[index + 1] ?? pages[index - 1];
                    deletePages([page.uid]);
                    onUidChange(next ? next.uid : null);
                  }}
                >
                  <Trash2 /> 削除
                </Button>
              </div>
              <Button variant="outline" size="sm" onClick={() => go(1)} disabled={index >= pages.length - 1}>
                次へ <ChevronRight />
              </Button>
            </div>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}
