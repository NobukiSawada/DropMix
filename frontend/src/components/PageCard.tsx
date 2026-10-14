import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { Check, Maximize2, RotateCcw, RotateCw, Trash2 } from "lucide-react";
import { memo } from "react";

import type { PageItem } from "@/lib/types";
import { cn } from "@/lib/utils";
import type { StoredFile } from "@/store";

import { PageThumb } from "./PageThumb";

interface Props {
  page: PageItem;
  position: number;
  file: StoredFile;
  size: number;
  selected: boolean;
  onSelect: (uid: string, e: React.MouseEvent) => void;
  onRotate: (uid: string, delta: number) => void;
  onDelete: (uid: string) => void;
  onPreview: (uid: string) => void;
}

export function PageCardView({
  page,
  position,
  file,
  size,
  selected = false,
  overlay = false,
  actions,
}: {
  page: PageItem;
  position: number;
  file: StoredFile;
  size: number;
  selected?: boolean;
  overlay?: boolean;
  actions?: React.ReactNode;
}) {
  return (
    <div
      className={cn(
        "group relative flex flex-col rounded-xl border bg-white p-2 transition-[box-shadow,border-color,background-color]",
        selected ? "border-primary bg-accent ring-2 ring-primary/30" : "border-border hover:border-green-300 hover:shadow-md",
        overlay && "cursor-grabbing border-primary shadow-2xl ring-2 ring-primary/40",
      )}
      style={{ width: size + 18 }}
    >
      <div
        className="relative overflow-hidden rounded-lg bg-muted"
        style={{ width: size, height: size }}
      >
        <PageThumb fileId={page.fileId} index={page.index} rotation={page.rotation} size={size} className="h-full w-full p-1.5" />
        <span className="absolute top-1.5 left-1.5 rounded-md bg-white/90 px-1.5 py-0.5 text-[11px] font-semibold text-foreground shadow-sm">
          {position}
        </span>
        {selected && (
          <span className="absolute top-1.5 right-1.5 flex size-5 items-center justify-center rounded-full bg-primary text-white shadow">
            <Check className="size-3.5" strokeWidth={3} />
          </span>
        )}
        {actions}
      </div>
      <div className="mt-1.5 flex min-w-0 items-center gap-1.5 px-0.5">
        <span className="size-2 shrink-0 rounded-full" style={{ backgroundColor: file.color }} />
        <span className="truncate text-[11px] text-muted-foreground" title={file.name}>
          {file.name}
        </span>
        {file.page_count > 1 && (
          <span className="ml-auto shrink-0 text-[11px] font-medium text-muted-foreground">p.{page.index + 1}</span>
        )}
      </div>
    </div>
  );
}

function ActionButton({
  label,
  onClick,
  children,
  danger,
}: {
  label: string;
  onClick: () => void;
  children: React.ReactNode;
  danger?: boolean;
}) {
  return (
    <button
      type="button"
      title={label}
      aria-label={label}
      onPointerDown={(e) => e.stopPropagation()}
      onClick={(e) => {
        e.stopPropagation();
        onClick();
      }}
      className={cn(
        "flex size-7 cursor-pointer items-center justify-center rounded-md bg-white/95 text-slate-600 shadow-sm transition-colors",
        danger ? "hover:bg-red-50 hover:text-destructive" : "hover:bg-accent hover:text-accent-foreground",
      )}
    >
      {children}
    </button>
  );
}

export const PageCard = memo(function PageCard({
  page,
  position,
  file,
  size,
  selected,
  onSelect,
  onRotate,
  onDelete,
  onPreview,
}: Props) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: page.uid });

  return (
    <div
      ref={setNodeRef}
      style={{ transform: CSS.Translate.toString(transform), transition }}
      className={cn("touch-none outline-none", isDragging && "opacity-30")}
      onClick={(e) => onSelect(page.uid, e)}
      onDoubleClick={() => onPreview(page.uid)}
      {...attributes}
      {...listeners}
    >
      <PageCardView
        page={page}
        position={position}
        file={file}
        size={size}
        selected={selected}
        actions={
          <div className="absolute inset-x-0 bottom-0 flex justify-center gap-1 bg-gradient-to-t from-slate-900/25 to-transparent p-1.5 pt-6 opacity-0 transition-opacity group-hover:opacity-100">
            <ActionButton label="左に回転" onClick={() => onRotate(page.uid, -90)}>
              <RotateCcw className="size-3.5" />
            </ActionButton>
            <ActionButton label="右に回転" onClick={() => onRotate(page.uid, 90)}>
              <RotateCw className="size-3.5" />
            </ActionButton>
            <ActionButton label="拡大表示" onClick={() => onPreview(page.uid)}>
              <Maximize2 className="size-3.5" />
            </ActionButton>
            <ActionButton label="削除" onClick={() => onDelete(page.uid)} danger>
              <Trash2 className="size-3.5" />
            </ActionButton>
          </div>
        }
      />
    </div>
  );
});
