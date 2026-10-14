import { arrayMove } from "@dnd-kit/sortable";
import { create } from "zustand";

import { fileColor } from "@/lib/utils";
import type { FileInfo, OutputResult, PageItem, PageSpec, ToolId } from "@/lib/types";

export interface StoredFile extends FileInfo {
  color: string;
}

export interface Task {
  label: string;
  /** 0〜1。null は進捗不明 (処理中) */
  progress: number | null;
}

const HISTORY_LIMIT = 100;

interface State {
  files: Record<string, StoredFile>;
  fileOrder: string[];
  pages: PageItem[];
  selected: Set<string>;
  anchor: string | null;
  past: PageItem[][];
  future: PageItem[][];
  tool: ToolId;
  task: Task | null;
  result: OutputResult | null;
  thumbSize: number;

  addFile: (info: FileInfo) => void;
  unlockFile: (info: FileInfo) => void;
  removeFile: (fileId: string) => void;
  clearAll: () => void;

  movePage: (activeUid: string, overUid: string) => void;
  rotatePages: (uids: string[], delta: number) => void;
  deletePages: (uids: string[]) => void;
  sortByFile: () => void;
  reversePages: () => void;
  undo: () => void;
  redo: () => void;

  select: (uid: string, mode: "toggle" | "range" | "single") => void;
  selectAll: () => void;
  clearSelection: () => void;

  setTool: (tool: ToolId) => void;
  setTask: (task: Task | null) => void;
  setResult: (result: OutputResult | null) => void;
  setThumbSize: (size: number) => void;
}

let uidCounter = 0;
const newUid = () => `p${++uidCounter}`;

function pagesFor(info: FileInfo): PageItem[] {
  return Array.from({ length: info.page_count }, (_, index) => ({
    uid: newUid(),
    fileId: info.id,
    index,
    rotation: 0,
  }));
}

export const useStore = create<State>((set, get) => {
  /** ページ配列を更新し、元に戻す履歴に積む */
  const commit = (pages: PageItem[], extra: Partial<State> = {}) => {
    const { pages: prev, past, selected } = get();
    const alive = new Set(pages.map((p) => p.uid));
    set({
      pages,
      past: [...past, prev].slice(-HISTORY_LIMIT),
      future: [],
      selected: new Set([...selected].filter((uid) => alive.has(uid))),
      result: null,
      ...extra,
    });
  };

  return {
    files: {},
    fileOrder: [],
    pages: [],
    selected: new Set(),
    anchor: null,
    past: [],
    future: [],
    tool: "merge",
    task: null,
    result: null,
    thumbSize: 168,

    addFile: (info) => {
      const { files, fileOrder, pages } = get();
      const stored: StoredFile = { ...info, color: fileColor(fileOrder.length) };
      set({ files: { ...files, [info.id]: stored }, fileOrder: [...fileOrder, info.id] });
      if (!info.locked) commit([...pages, ...pagesFor(info)]);
    },

    unlockFile: (info) => {
      const { files, pages } = get();
      const prev = files[info.id];
      if (!prev) return;
      set({ files: { ...files, [info.id]: { ...info, color: prev.color } } });
      commit([...pages, ...pagesFor(info)]);
    },

    removeFile: (fileId) => {
      const { files, fileOrder, pages, past, future, selected } = get();
      const rest = { ...files };
      delete rest[fileId];
      const keep = (list: PageItem[]) => list.filter((p) => p.fileId !== fileId);
      const nextPages = keep(pages);
      const alive = new Set(nextPages.map((p) => p.uid));
      // 削除したファイルのページは履歴からも取り除く (元に戻しても復元できないため)
      set({
        files: rest,
        fileOrder: fileOrder.filter((id) => id !== fileId),
        pages: nextPages,
        past: past.map(keep),
        future: future.map(keep),
        selected: new Set([...selected].filter((uid) => alive.has(uid))),
        result: null,
      });
    },

    clearAll: () =>
      set({
        files: {},
        fileOrder: [],
        pages: [],
        selected: new Set(),
        anchor: null,
        past: [],
        future: [],
        result: null,
      }),

    movePage: (activeUid, overUid) => {
      const { pages } = get();
      const from = pages.findIndex((p) => p.uid === activeUid);
      const to = pages.findIndex((p) => p.uid === overUid);
      if (from < 0 || to < 0 || from === to) return;
      commit(arrayMove(pages, from, to));
    },

    rotatePages: (uids, delta) => {
      const target = new Set(uids);
      if (!target.size) return;
      commit(
        get().pages.map((p) => (target.has(p.uid) ? { ...p, rotation: (((p.rotation + delta) % 360) + 360) % 360 } : p)),
      );
    },

    deletePages: (uids) => {
      const target = new Set(uids);
      if (!target.size) return;
      commit(get().pages.filter((p) => !target.has(p.uid)));
    },

    sortByFile: () => {
      const { pages, fileOrder } = get();
      const order = new Map(fileOrder.map((id, i) => [id, i]));
      commit([...pages].sort((a, b) => order.get(a.fileId)! - order.get(b.fileId)! || a.index - b.index));
    },

    reversePages: () => commit([...get().pages].reverse()),

    undo: () => {
      const { past, future, pages } = get();
      if (!past.length) return;
      set({ pages: past[past.length - 1], past: past.slice(0, -1), future: [pages, ...future], result: null });
    },

    redo: () => {
      const { past, future, pages } = get();
      if (!future.length) return;
      set({ pages: future[0], future: future.slice(1), past: [...past, pages], result: null });
    },

    select: (uid, mode) => {
      const { selected, anchor, pages } = get();
      if (mode === "single") {
        set({ selected: new Set([uid]), anchor: uid });
      } else if (mode === "range" && anchor) {
        const a = pages.findIndex((p) => p.uid === anchor);
        const b = pages.findIndex((p) => p.uid === uid);
        if (a < 0 || b < 0) {
          set({ selected: new Set([uid]), anchor: uid });
          return;
        }
        const [lo, hi] = a < b ? [a, b] : [b, a];
        const next = new Set(selected);
        for (let i = lo; i <= hi; i++) next.add(pages[i].uid);
        set({ selected: next });
      } else {
        const next = new Set(selected);
        if (next.has(uid)) next.delete(uid);
        else next.add(uid);
        set({ selected: next, anchor: uid });
      }
    },

    selectAll: () => set({ selected: new Set(get().pages.map((p) => p.uid)) }),
    clearSelection: () => set({ selected: new Set(), anchor: null }),

    setTool: (tool) => set({ tool, result: null }),
    setTask: (task) => set({ task }),
    setResult: (result) => set({ result }),
    setThumbSize: (thumbSize) => set({ thumbSize }),
  };
});

/** 処理対象のページ: 選択があれば選択ページ (並び順どおり)、なければ全ページ */
export function targetPages(state: Pick<State, "pages" | "selected">): PageItem[] {
  if (state.selected.size === 0) return state.pages;
  return state.pages.filter((p) => state.selected.has(p.uid));
}

export function toPageSpecs(pages: PageItem[]): PageSpec[] {
  return pages.map((p) => ({ file_id: p.fileId, index: p.index, rotation: p.rotation }));
}
