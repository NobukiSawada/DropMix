import { FilePlus2, Redo2, Trash2, Undo2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Tooltip } from "@/components/ui/tooltip";
import { useStore } from "@/store";

export function Logo() {
  return (
    <div className="flex items-center gap-2.5">
      <img src="/favicon.svg" alt="" className="size-8" draggable={false} />
      <div className="leading-tight">
        <div className="text-[17px] font-bold tracking-tight">
          Drop<span className="text-primary">Mix</span>
        </div>
        <div className="text-[10px] text-muted-foreground">ローカルで完結するPDF・画像ツール</div>
      </div>
    </div>
  );
}

export function Header({ onAddFiles, onClearAll }: { onAddFiles: () => void; onClearAll: () => void }) {
  const task = useStore((s) => s.task);
  const canUndo = useStore((s) => s.past.length > 0);
  const canRedo = useStore((s) => s.future.length > 0);
  const hasFiles = useStore((s) => s.fileOrder.length > 0);
  const undo = useStore((s) => s.undo);
  const redo = useStore((s) => s.redo);

  return (
    <header className="relative z-10 flex h-16 shrink-0 items-center gap-4 border-b bg-white px-5">
      <Logo />

      <div className="mx-auto flex min-w-0 flex-1 justify-center">
        {task && (
          <div className="flex w-full max-w-md animate-fade-in flex-col gap-1.5">
            <div className="flex items-center justify-between gap-3 text-xs">
              <span className="truncate font-medium text-accent-foreground">{task.label}</span>
              {task.progress !== null && (
                <span className="shrink-0 tabular-nums text-muted-foreground">{Math.round(task.progress * 100)}%</span>
              )}
            </div>
            <Progress value={task.progress} />
          </div>
        )}
      </div>

      <div className="flex items-center gap-1">
        <Tooltip content="元に戻す (Ctrl+Z)">
          <Button variant="ghost" size="icon" onClick={undo} disabled={!canUndo} aria-label="元に戻す">
            <Undo2 />
          </Button>
        </Tooltip>
        <Tooltip content="やり直す (Ctrl+Y)">
          <Button variant="ghost" size="icon" onClick={redo} disabled={!canRedo} aria-label="やり直す">
            <Redo2 />
          </Button>
        </Tooltip>
        <Tooltip content="すべてのファイルを閉じる">
          <Button
            variant="ghost"
            size="icon"
            onClick={onClearAll}
            disabled={!hasFiles || !!task}
            aria-label="すべてクリア"
            className="hover:bg-red-50 hover:text-destructive"
          >
            <Trash2 />
          </Button>
        </Tooltip>
        <Button onClick={onAddFiles} disabled={!!task} className="ml-2">
          <FilePlus2 /> ファイルを追加
        </Button>
      </div>
    </header>
  );
}
