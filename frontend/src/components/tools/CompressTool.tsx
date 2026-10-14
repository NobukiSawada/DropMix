import { useState } from "react";

import { RadioCard, RadioGroup } from "@/components/ui/radio-group";
import { useRunTool } from "@/hooks/useRunTool";

import { RunButton } from "./common";

type Level = "standard" | "strong" | "max";

export function CompressTool() {
  const run = useRunTool();
  const [level, setLevel] = useState<Level>("standard");

  return (
    <>
      <RadioGroup value={level} onValueChange={(v) => setLevel(v as Level)}>
        <RadioCard value="standard" title="標準（画質そのまま）" description="不要データの削除と再圧縮のみ。見た目は一切変わりません" />
        <RadioCard value="strong" title="高圧縮（推奨）" description="画像を150dpi程度に最適化。画面表示・通常の印刷に十分な画質です" />
        <RadioCard value="max" title="最大圧縮" description="画像を96dpiまで縮小し、フォントも最適化。メール添付向け" />
      </RadioGroup>
      <RunButton label="圧縮して保存" onClick={() => run("compress", "PDFを圧縮中...", { level })} />
    </>
  );
}
