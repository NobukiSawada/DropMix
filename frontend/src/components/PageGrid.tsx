import {
  closestCenter,
  DndContext,
  type DragEndEvent,
  DragOverlay,
  type DragStartEvent,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
} from "@dnd-kit/core";
import { rectSortingStrategy, SortableContext, sortableKeyboardCoordinates } from "@dnd-kit/sortable";
import { useCallback, useMemo, useState } from "react";

import { useStore } from "@/store";

import { PageCard, PageCardView } from "./PageCard";
import { PreviewDialog } from "./PreviewDialog";

export function PageGrid() {
  const pages = useStore((s) => s.pages);
  const files = useStore((s) => s.files);
  const selected = useStore((s) => s.selected);
  const size = useStore((s) => s.thumbSize);
  const movePage = useStore((s) => s.movePage);
  const rotatePages = useStore((s) => s.rotatePages);
  const deletePages = useStore((s) => s.deletePages);
  const select = useStore((s) => s.select);

  const [activeUid, setActiveUid] = useState<string | null>(null);
  const [previewUid, setPreviewUid] = useState<string | null>(null);

  const sensors = useSensors(
    // 少し動かしてからドラッグ開始 (クリックでの選択と両立させる)
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  );

  const ids = useMemo(() => pages.map((p) => p.uid), [pages]);

  const onDragStart = useCallback((e: DragStartEvent) => setActiveUid(String(e.active.id)), []);
  const onDragEnd = useCallback(
    (e: DragEndEvent) => {
      setActiveUid(null);
      if (e.over && e.active.id !== e.over.id) movePage(String(e.active.id), String(e.over.id));
    },
    [movePage],
  );

  const onSelect = useCallback(
    (uid: string, e: React.MouseEvent) => select(uid, e.shiftKey ? "range" : "toggle"),
    [select],
  );
  const onRotate = useCallback((uid: string, delta: number) => rotatePages([uid], delta), [rotatePages]);
  const onDelete = useCallback((uid: string) => deletePages([uid]), [deletePages]);

  const activeIndex = activeUid ? pages.findIndex((p) => p.uid === activeUid) : -1;
  const activePage = activeIndex >= 0 ? pages[activeIndex] : null;

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCenter}
      onDragStart={onDragStart}
      onDragEnd={onDragEnd}
      onDragCancel={() => setActiveUid(null)}
    >
      <SortableContext items={ids} strategy={rectSortingStrategy}>
        <div
          className="grid justify-start gap-3 p-5"
          style={{ gridTemplateColumns: `repeat(auto-fill, ${size + 18}px)` }}
        >
          {pages.map((page, i) => (
            <PageCard
              key={page.uid}
              page={page}
              position={i + 1}
              file={files[page.fileId]}
              size={size}
              selected={selected.has(page.uid)}
              onSelect={onSelect}
              onRotate={onRotate}
              onDelete={onDelete}
              onPreview={setPreviewUid}
            />
          ))}
        </div>
      </SortableContext>
      <DragOverlay dropAnimation={{ duration: 200, easing: "cubic-bezier(0.2, 0, 0, 1)" }}>
        {activePage && (
          <PageCardView
            page={activePage}
            position={activeIndex + 1}
            file={files[activePage.fileId]}
            size={size}
            selected={selected.has(activePage.uid)}
            overlay
          />
        )}
      </DragOverlay>
      <PreviewDialog uid={previewUid} onUidChange={setPreviewUid} />
    </DndContext>
  );
}
