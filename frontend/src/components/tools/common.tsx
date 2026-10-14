import { CheckCircle2, Download, Layers, Loader2, MousePointerClick } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { saveAndNotify } from "@/hooks/useRunTool";
import { cn, formatBytes } from "@/lib/utils";
import { targetPages, useStore } from "@/store";

export function Field({
  label,
  hint,
  children,
  className,
  htmlFor,
}: {
  label: React.ReactNode;
  hint?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
  htmlFor?: string;
}) {
  return (
    <div className={cn("grid gap-2", className)}>
      <div className="flex items-baseline justify-between gap-2">
        <Label htmlFor={htmlFor}>{label}</Label>
        {hint && <span className="text-xs text-muted-foreground tabular-nums">{hint}</span>}
      </div>
      {children}
    </div>
  );
}

/** 処理対象 (全ページ or 選択ページ) の表示 */
export function TargetInfo() {
  const total = useStore((s) => s.pages.length);
  const selectedCount = useStore((s) => s.selected.size);
  const clearSelection = useStore((s) => s.clearSelection);

  return (
    <div className="flex items-start gap-2.5 rounded-lg border border-dashed border-green-200 bg-accent/50 p-3 text-xs">
      {selectedCount > 0 ? (
        <>
          <MousePointerClick className="mt-0.5 size-4 shrink-0 text-primary" />
          <div className="flex-1 leading-relaxed">
            <span className="font-semibold text-accent-foreground">選択中の {selectedCount} ページ</span>
            を、並び順どおりに処理します。
            <button type="button" onClick={clearSelection} className="ml-1 cursor-pointer text-primary underline-offset-2 hover:underline">
              全ページを対象にする
            </button>
          </div>
        </>
      ) : (
        <>
          <Layers className="mt-0.5 size-4 shrink-0 text-primary" />
          <div className="flex-1 leading-relaxed">
            <span className="font-semibold text-accent-foreground">全 {total} ページ</span>
            を、表示中の並び順・回転のまま処理します。ページをクリックすると対象を絞り込めます。
          </div>
        </>
      )}
    </div>
  );
}

export function RunButton({
  label,
  onClick,
  disabled,
}: {
  label: string;
  onClick: () => void;
  disabled?: boolean;
}) {
  const busy = useStore((s) => !!s.task);
  const count = useStore((s) => targetPages(s).length);
  return (
    <Button size="lg" className="w-full" onClick={onClick} disabled={disabled || busy || count === 0}>
      {busy ? <Loader2 className="animate-spin" /> : <Download />}
      {busy ? "処理中..." : label}
    </Button>
  );
}

export function ResultCard() {
  const result = useStore((s) => s.result);
  if (!result) return null;
  const saved =
    result.size_before !== undefined && result.size_after !== undefined
      ? 1 - result.size_after / Math.max(result.size_before, 1)
      : null;

  return (
    <div className="animate-fade-in rounded-lg border border-green-200 bg-accent/60 p-3">
      <div className="flex items-start gap-2.5">
        <CheckCircle2 className="mt-0.5 size-4 shrink-0 text-primary" />
        <div className="min-w-0 flex-1 text-xs">
          <p className="font-semibold text-accent-foreground">処理が完了しました</p>
          <p className="mt-0.5 truncate text-muted-foreground" title={result.download_name}>
            {result.files.length > 1 ? `${result.files.length} ファイル` : result.download_name}（
            {formatBytes(result.total_size)}）
          </p>
          {saved !== null && (
            <p className="mt-1 text-muted-foreground">
              {formatBytes(result.size_before!)} → <span className="font-semibold text-foreground">{formatBytes(result.size_after!)}</span>
              <span className={cn("ml-1.5 font-semibold", saved > 0 ? "text-primary" : "text-muted-foreground")}>
                {saved > 0 ? `${Math.round(saved * 100)}% 削減` : "これ以上は小さくなりませんでした"}
              </span>
            </p>
          )}
        </div>
      </div>
      <Button variant="outline" size="sm" className="mt-2.5 w-full" onClick={() => void saveAndNotify(result)}>
        <Download /> もう一度保存
      </Button>
    </div>
  );
}
