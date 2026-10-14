import { Combine, FileImage, Hash, Lock, Minimize2, Scissors, Stamp, type LucideIcon } from "lucide-react";

import type { ToolId } from "@/lib/types";
import { cn } from "@/lib/utils";
import { useStore } from "@/store";

import { ResultCard, TargetInfo } from "./tools/common";
import { CompressTool } from "./tools/CompressTool";
import { ImagesTool } from "./tools/ImagesTool";
import { MergeTool } from "./tools/MergeTool";
import { PageNumberTool } from "./tools/PageNumberTool";
import { ProtectTool } from "./tools/ProtectTool";
import { SplitTool } from "./tools/SplitTool";
import { WatermarkTool } from "./tools/WatermarkTool";

const TOOLS: { id: ToolId; label: string; title: string; icon: LucideIcon; Component: React.ComponentType }[] = [
  { id: "merge", label: "結合", title: "結合・保存", icon: Combine, Component: MergeTool },
  { id: "split", label: "分割・抽出", title: "分割・抽出", icon: Scissors, Component: SplitTool },
  { id: "images", label: "画像変換", title: "PDF → 画像 (JPG/PNG)", icon: FileImage, Component: ImagesTool },
  { id: "compress", label: "圧縮", title: "PDFを圧縮", icon: Minimize2, Component: CompressTool },
  { id: "watermark", label: "透かし", title: "透かしを追加", icon: Stamp, Component: WatermarkTool },
  { id: "pagenum", label: "ページ番号", title: "ページ番号を追加", icon: Hash, Component: PageNumberTool },
  { id: "protect", label: "パスワード", title: "パスワードで保護", icon: Lock, Component: ProtectTool },
];

export function ToolPanel() {
  const tool = useStore((s) => s.tool);
  const setTool = useStore((s) => s.setTool);
  const current = TOOLS.find((t) => t.id === tool) ?? TOOLS[0];
  const { Component } = current;

  return (
    <aside className="flex w-[340px] shrink-0 flex-col border-l bg-white">
      <nav className="grid grid-cols-4 gap-1.5 border-b p-3" aria-label="ツール">
        {TOOLS.map((t) => {
          const active = t.id === tool;
          return (
            <button
              key={t.id}
              type="button"
              onClick={() => setTool(t.id)}
              aria-pressed={active}
              className={cn(
                "flex cursor-pointer flex-col items-center gap-1 rounded-lg px-1 py-2 text-[11px] font-medium transition-colors outline-none focus-visible:ring-2 focus-visible:ring-ring/40",
                active ? "bg-primary text-white shadow-sm" : "text-slate-600 hover:bg-accent hover:text-accent-foreground",
              )}
            >
              <t.icon className="size-[18px]" strokeWidth={active ? 2.2 : 1.8} />
              <span className="leading-none whitespace-nowrap">{t.label}</span>
            </button>
          );
        })}
      </nav>
      <div className="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto p-4">
        <h2 className="flex items-center gap-2 text-base font-bold">
          <current.icon className="size-5 text-primary" />
          {current.title}
        </h2>
        <TargetInfo />
        {/* key でツール切り替え時に入力状態をリセット */}
        <div key={current.id} className="grid gap-4">
          <Component />
        </div>
        <ResultCard />
      </div>
    </aside>
  );
}
