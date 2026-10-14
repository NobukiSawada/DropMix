import { useState } from "react";

import { Input } from "@/components/ui/input";
import { useRunTool } from "@/hooks/useRunTool";

import { Field, RunButton } from "./common";

export function MergeTool() {
  const run = useRunTool();
  const [name, setName] = useState("");

  return (
    <>
      <p className="text-xs leading-relaxed text-muted-foreground">
        PDFと画像を、表示中の順番で1つのPDFにまとめます。並び替え・回転・削除はすべて反映されます。画像は自動でPDFページに変換されます。
      </p>
      <Field label="ファイル名（省略可）" htmlFor="merge-name">
        <Input id="merge-name" value={name} onChange={(e) => setName(e.target.value)} placeholder="例: 提出書類まとめ" />
      </Field>
      <RunButton label="PDFを作成して保存" onClick={() => run("merge", "PDFを作成中...", { output_name: name || null })} />
    </>
  );
}
