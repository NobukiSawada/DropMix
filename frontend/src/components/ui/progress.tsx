import { cn } from "@/lib/utils";

/** value: 0〜1。null の場合は処理中アニメーション (不確定) */
export function Progress({ value, className }: { value: number | null; className?: string }) {
  return (
    <div className={cn("relative h-1.5 w-full overflow-hidden rounded-full bg-green-100", className)}>
      {value === null ? (
        <div className="absolute inset-y-0 w-2/5 animate-progress rounded-full bg-primary" />
      ) : (
        <div
          className="h-full rounded-full bg-primary transition-[width] duration-200"
          style={{ width: `${Math.round(Math.min(1, Math.max(0, value)) * 100)}%` }}
        />
      )}
    </div>
  );
}
