import { ImageOff, Loader2 } from "lucide-react";
import { useState } from "react";

import { thumbnailUrl } from "@/lib/api";
import { cn } from "@/lib/utils";

/** サムネイル幅を 160px 単位に丸めてキャッシュを効かせる */
export function thumbWidth(cssSize: number): number {
  const px = cssSize * (window.devicePixelRatio || 1);
  return Math.min(1600, Math.max(160, Math.ceil(px / 160) * 160));
}

export function PageThumb({
  fileId,
  index,
  rotation,
  size,
  className,
}: {
  fileId: string;
  index: number;
  rotation: number;
  size: number;
  className?: string;
}) {
  const [state, setState] = useState<"loading" | "ok" | "error">("loading");
  return (
    <div className={cn("relative flex items-center justify-center", className)}>
      {state === "loading" && <Loader2 className="absolute size-5 animate-spin text-green-300" />}
      {state === "error" && <ImageOff className="absolute size-6 text-slate-300" />}
      <img
        src={thumbnailUrl(fileId, index, thumbWidth(size))}
        alt=""
        draggable={false}
        loading="lazy"
        onLoad={() => setState("ok")}
        onError={() => setState("error")}
        className={cn(
          "h-full w-full object-contain transition-transform duration-300 ease-out",
          state !== "ok" && "opacity-0",
        )}
        style={{ transform: `rotate(${rotation}deg)` }}
      />
    </div>
  );
}
