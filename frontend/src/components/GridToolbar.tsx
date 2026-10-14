import {
  ArrowDownUp,
  CheckSquare,
  FileImage,
  FileText,
  Lock,
  RotateCcw,
  RotateCw,
  Square,
  Trash2,
  X,
  ZoomIn,
  ZoomOut,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Slider } from "@/components/ui/slider";
import { Tooltip } from "@/components/ui/tooltip";
import { formatBytes } from "@/lib/utils";
import { useStore } from "@/store";

export function FileChips({ onUnlock, onRemove }: { onUnlock: (id: string) => void; onRemove: (id: string) => void }) {
  const files = useStore((s) => s.files);
  const fileOrder = useStore((s) => s.fileOrder);
  const pages = useStore((s) => s.pages);
  const busy = useStore((s) => !!s.task);

  const counts = new Map<string, number>();
  for (const p of pages) counts.set(p.fileId, (counts.get(p.fileId) ?? 0) + 1);

  return (
    <div className="flex flex-wrap gap-2">
      {fileOrder.map((id) => {
        const f = files[id];
        const Icon = f.kind === "pdf" ? FileText : FileImage;
        return (
          <div
            key={id}
            className="flex h-8 max-w-64 items-center gap-2 rounded-full border bg-white pr-1 pl-2.5 text-xs shadow-xs"
            title={`${f.name}（${formatBytes(f.size)}）`}
          >
            <span className="size-2 shrink-0 rounded-full" style={{ backgroundColor: f.color }} />
            <Icon className="size-3.5 shrink-0 text-muted-foreground" />
            <span className="truncate font-medium">{f.name}</span>
            {f.locked ? (
              <button
                type="button"
                onClick={() => onUnlock(id)}
                className="flex shrink-0 cursor-pointer items-center gap-1 rounded-full bg-amber-50 px-2 py-0.5 font-medium text-amber-700 hover:bg-amber-100"
              >
                <Lock className="size-3" /> 解除
              </button>
            ) : (
              <span className="shrink-0 text-muted-foreground tabular-nums">
                {counts.get(id) ?? 0}/{f.page_count}p
              </span>
            )}
            <button
              type="button"
              aria-label={`${f.name} を閉じる`}
              disabled={busy}
              onClick={() => onRemove(id)}
              className="flex size-6 shrink-0 cursor-pointer items-center justify-center rounded-full text-muted-foreground hover:bg-red-50 hover:text-destructive disabled:pointer-events-none disabled:opacity-40"
            >
              <X className="size-3.5" />
            </button>
          </div>
        );
      })}
    </div>
  );
}

export function GridToolbar() {
  const pageCount = useStore((s) => s.pages.length);
  const selected = useStore((s) => s.selected);
  const thumbSize = useStore((s) => s.thumbSize);
  const setThumbSize = useStore((s) => s.setThumbSize);
  const selectAll = useStore((s) => s.selectAll);
  const clearSelection = useStore((s) => s.clearSelection);
  const rotatePages = useStore((s) => s.rotatePages);
  const deletePages = useStore((s) => s.deletePages);
  const sortByFile = useStore((s) => s.sortByFile);
  const reversePages = useStore((s) => s.reversePages);
  const pages = useStore((s) => s.pages);

  const hasSelection = selected.size > 0;
  // 選択がなければ全ページが対象
  const targetUids = hasSelection ? [...selected] : pages.map((p) => p.uid);

  return (
    <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
      <div className="text-sm">
        <span className="font-semibold tabular-nums">{pageCount}</span>
        <span className="text-muted-foreground"> ページ</span>
        {hasSelection && (
          <span className="ml-2 rounded-full bg-accent px-2 py-0.5 text-xs font-semibold text-accent-foreground">
            {selected.size} 件選択中
          </span>
        )}
      </div>

      <div className="flex items-center gap-0.5">
        {hasSelection ? (
          <Button variant="ghost" size="sm" onClick={clearSelection}>
            <Square /> 選択解除
          </Button>
        ) : (
          <Button variant="ghost" size="sm" onClick={selectAll} disabled={!pageCount}>
            <CheckSquare /> すべて選択
          </Button>
        )}
        <Tooltip content={hasSelection ? "選択ページを左に回転" : "全ページを左に回転"}>
          <Button variant="ghost" size="icon-sm" onClick={() => rotatePages(targetUids, -90)} disabled={!pageCount} aria-label="左に回転">
            <RotateCcw />
          </Button>
        </Tooltip>
        <Tooltip content={hasSelection ? "選択ページを右に回転" : "全ページを右に回転"}>
          <Button variant="ghost" size="icon-sm" onClick={() => rotatePages(targetUids, 90)} disabled={!pageCount} aria-label="右に回転">
            <RotateCw />
          </Button>
        </Tooltip>
        <Tooltip content="選択ページを削除 (Delete)">
          <Button
            variant="ghost"
            size="icon-sm"
            onClick={() => deletePages([...selected])}
            disabled={!hasSelection}
            aria-label="選択ページを削除"
            className="hover:bg-red-50 hover:text-destructive"
          >
            <Trash2 />
          </Button>
        </Tooltip>
        <Tooltip content="ファイル順・ページ順に並べ直す">
          <Button variant="ghost" size="sm" onClick={sortByFile} disabled={pageCount < 2}>
            <ArrowDownUp /> 元の順
          </Button>
        </Tooltip>
        <Button variant="ghost" size="sm" onClick={reversePages} disabled={pageCount < 2}>
          逆順
        </Button>
      </div>

      <div className="ml-auto flex w-40 items-center gap-2 text-muted-foreground">
        <ZoomOut className="size-3.5 shrink-0" />
        <Slider
          value={[thumbSize]}
          min={110}
          max={300}
          step={2}
          onValueChange={([v]) => setThumbSize(v)}
          aria-label="サムネイルの大きさ"
        />
        <ZoomIn className="size-3.5 shrink-0" />
      </div>
    </div>
  );
}
