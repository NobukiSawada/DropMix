import { useState } from "react";

import { Input } from "@/components/ui/input";
import { RadioCard, RadioGroup } from "@/components/ui/radio-group";
import { useRunTool } from "@/hooks/useRunTool";
import { targetPages, useStore } from "@/store";

import { Field, RunButton } from "./common";

type Mode = "each" | "ranges" | "extract";

const RANGE_RE = /^\s*(\d+\s*(-\s*\d*)?|-\s*\d+)\s*$/;

function validateRanges(spec: string, total: number): string | null {
  // バックエンド (pdf_ops.parse_ranges) と同じ正規化
  const parts = spec
    .replace(/\s*[-～〜−ー]\s*/g, "-")
    .split(/[,、，\s]+/)
    .filter(Boolean);
  if (!parts.length) return "ページ範囲を入力してください";
  for (const part of parts) {
    if (!RANGE_RE.test(part)) return `書式が正しくありません: ${part}`;
    const [a, b] = part.split("-").map((s) => s.trim());
    const start = a ? Number(a) : 1;
    const end = part.includes("-") ? (b ? Number(b) : total) : start;
    if (start < 1 || end > total || start > end) return `範囲が不正です: ${part}（1〜${total}）`;
  }
  return null;
}

export function SplitTool() {
  const run = useRunTool();
  const total = useStore((s) => targetPages(s).length);
  const [mode, setMode] = useState<Mode>("each");
  const [ranges, setRanges] = useState("");

  const error = mode === "each" ? null : validateRanges(ranges, total);
  const showError = mode !== "each" && ranges.trim() !== "" && error;

  return (
    <>
      <RadioGroup value={mode} onValueChange={(v) => setMode(v as Mode)}>
        <RadioCard value="each" title="1ページずつ分割" description={`${total} 個のPDFに分けます`} />
        <RadioCard value="ranges" title="範囲ごとに分割" description="「1-3, 5」→ 1〜3ページと5ページの2ファイル" />
        <RadioCard value="extract" title="指定ページを抽出" description="指定したページだけを1つのPDFにまとめます" />
      </RadioGroup>

      {mode !== "each" && (
        <Field label="ページ範囲" hint={`1〜${total}`} htmlFor="split-ranges">
          <Input
            id="split-ranges"
            value={ranges}
            onChange={(e) => setRanges(e.target.value)}
            placeholder="例: 1-3, 5, 8-"
            aria-invalid={!!showError}
          />
          <p className={showError ? "text-xs text-destructive" : "text-xs text-muted-foreground"}>
            {showError || "番号は現在の並び順（対象ページ内）です。「8-」は8ページ目から最後まで。"}
          </p>
        </Field>
      )}

      <RunButton
        label={mode === "extract" ? "抽出して保存" : "分割して保存"}
        disabled={!!error}
        onClick={() => run("split", "PDFを分割中...", { mode, ranges: mode === "each" ? null : ranges })}
      />
    </>
  );
}
