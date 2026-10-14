import { FileImage, FileText, Lock, UploadCloud } from "lucide-react";

import { Button } from "@/components/ui/button";

export function EmptyState({ onBrowse }: { onBrowse: () => void }) {
  return (
    <div className="flex h-full items-center justify-center p-6">
      <button
        type="button"
        onClick={onBrowse}
        className="group flex h-full max-h-[620px] w-full max-w-4xl cursor-pointer flex-col items-center justify-center gap-6 rounded-3xl border-2 border-dashed border-green-200 bg-gradient-to-b from-white to-accent/60 p-10 text-center transition-colors outline-none hover:border-primary hover:bg-accent focus-visible:border-primary"
      >
        <div className="flex size-24 items-center justify-center rounded-3xl bg-white text-primary shadow-lg shadow-green-900/5 ring-1 ring-green-100 transition-transform duration-300 group-hover:-translate-y-1">
          <UploadCloud className="size-12" strokeWidth={1.6} />
        </div>
        <div className="space-y-2">
          <p className="text-2xl font-bold tracking-tight">ここにPDFや画像をドロップ</p>
          <p className="text-sm text-muted-foreground">
            結合・並び替え・分割・圧縮・画像変換などを、すべてこのPCの中だけで処理します
          </p>
        </div>
        <Button size="lg" asChild>
          <span>ファイルを選択</span>
        </Button>
        <div className="flex flex-wrap items-center justify-center gap-x-6 gap-y-2 text-xs text-muted-foreground">
          <span className="flex items-center gap-1.5">
            <FileText className="size-4 text-primary" /> PDF
          </span>
          <span className="flex items-center gap-1.5">
            <FileImage className="size-4 text-primary" /> JPG / PNG / WebP / BMP / GIF / TIFF
          </span>
          <span className="flex items-center gap-1.5">
            <Lock className="size-4 text-primary" /> ファイルは外部に送信されません
          </span>
        </div>
      </button>
    </div>
  );
}

export function DropOverlay() {
  return (
    <div className="pointer-events-none fixed inset-0 z-40 flex animate-fade-in items-center justify-center bg-green-50/85 p-6 backdrop-blur-sm">
      <div className="flex h-full w-full flex-col items-center justify-center gap-4 rounded-3xl border-[3px] border-dashed border-primary">
        <UploadCloud className="size-16 text-primary" strokeWidth={1.6} />
        <p className="text-2xl font-bold text-accent-foreground">ドロップして追加</p>
      </div>
    </div>
  );
}
