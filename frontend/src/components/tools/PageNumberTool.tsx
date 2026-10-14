import { useState } from "react";

import { Input } from "@/components/ui/input";
import { Segmented } from "@/components/ui/radio-group";
import { Slider } from "@/components/ui/slider";
import { useRunTool } from "@/hooks/useRunTool";
import { cn } from "@/lib/utils";

import { Field, RunButton } from "./common";
import { ColorPicker } from "./WatermarkTool";

type Position = "top-left" | "top-center" | "top-right" | "bottom-left" | "bottom-center" | "bottom-right";
const POSITIONS: Position[] = ["top-left", "top-center", "top-right", "bottom-left", "bottom-center", "bottom-right"];

const PRESETS = [
  { value: "{n}", label: "1" },
  { value: "{n} / {total}", label: "1 / 10" },
  { value: "- {n} -", label: "- 1 -" },
  { value: "custom", label: "カスタム" },
];

export function PageNumberTool() {
  const run = useRunTool();
  const [position, setPosition] = useState<Position>("bottom-center");
  const [preset, setPreset] = useState("{n} / {total}");
  const [custom, setCustom] = useState("{n} ページ");
  const [start, setStart] = useState("1");
  const [fontsize, setFontsize] = useState(11);
  const [color, setColor] = useState("#111827");

  const format = preset === "custom" ? custom : preset;
  const startNum = Number(start);
  const formatError = !format.includes("{n}") ? "書式には {n} を含めてください" : null;
  const startError =
    start.trim() === "" || !Number.isInteger(startNum) || startNum < 0 ? "0以上の整数を入力してください" : null;

  return (
    <>
      <Field label="位置">
        <div className="grid w-40 grid-cols-3 gap-1.5 self-center justify-self-center rounded-lg border bg-white p-2">
          {POSITIONS.map((p, i) => (
            <button
              key={p}
              type="button"
              aria-label={p}
              onClick={() => setPosition(p)}
              className={cn(
                "flex h-9 cursor-pointer items-center justify-center rounded-md border transition-colors",
                i < 3 ? "items-start pt-1.5" : "items-end pb-1.5",
                position === p ? "border-primary bg-accent" : "border-dashed border-slate-200 hover:border-green-300",
              )}
            >
              <span className={cn("h-1 w-4 rounded-full", position === p ? "bg-primary" : "bg-slate-300")} />
            </button>
          ))}
        </div>
      </Field>
      <Field label="書式">
        <Segmented value={preset} onValueChange={setPreset} options={PRESETS} />
        {preset === "custom" && (
          <>
            <Input value={custom} onChange={(e) => setCustom(e.target.value)} maxLength={60} aria-invalid={!!formatError} />
            <p className={formatError ? "text-xs text-destructive" : "text-xs text-muted-foreground"}>
              {formatError ?? "{n} = ページ番号、{total} = 総ページ数"}
            </p>
          </>
        )}
      </Field>
      <div className="grid grid-cols-2 gap-3">
        <Field label="開始番号" htmlFor="pn-start">
          <Input
            id="pn-start"
            type="number"
            min={0}
            value={start}
            onChange={(e) => setStart(e.target.value)}
            aria-invalid={!!startError}
          />
        </Field>
        <Field label="文字サイズ" hint={`${fontsize} pt`}>
          <Slider value={[fontsize]} min={6} max={36} step={1} onValueChange={([v]) => setFontsize(v)} className="mt-2" />
        </Field>
      </div>
      <Field label="色">
        <ColorPicker value={color} onChange={setColor} />
      </Field>
      <RunButton
        label="ページ番号を入れて保存"
        disabled={!!formatError || !!startError}
        onClick={() =>
          run("page-numbers", "ページ番号を追加中...", { position, format, start: startNum, fontsize, color })
        }
      />
    </>
  );
}
