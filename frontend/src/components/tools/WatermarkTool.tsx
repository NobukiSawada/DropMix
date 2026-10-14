import { useState } from "react";

import { Input } from "@/components/ui/input";
import { Segmented } from "@/components/ui/radio-group";
import { Slider } from "@/components/ui/slider";
import { useRunTool } from "@/hooks/useRunTool";
import { cn } from "@/lib/utils";

import { Field, RunButton } from "./common";

const COLORS = ["#16a34a", "#64748b", "#dc2626", "#2563eb", "#111827"];

export function ColorPicker({ value, onChange }: { value: string; onChange: (c: string) => void }) {
  return (
    <div className="flex gap-2">
      {COLORS.map((c) => (
        <button
          key={c}
          type="button"
          aria-label={c}
          onClick={() => onChange(c)}
          className={cn(
            "size-7 cursor-pointer rounded-full ring-offset-2 transition-shadow",
            value === c ? "ring-2 ring-primary" : "hover:ring-2 hover:ring-slate-200",
          )}
          style={{ backgroundColor: c }}
        />
      ))}
    </div>
  );
}

export function WatermarkTool() {
  const run = useRunTool();
  const [text, setText] = useState("社外秘");
  const [fontsize, setFontsize] = useState(60);
  const [opacity, setOpacity] = useState(25);
  const [angle, setAngle] = useState("45");
  const [color, setColor] = useState(COLORS[0]);

  return (
    <>
      <Field label="透かしのテキスト" htmlFor="wm-text">
        <Input id="wm-text" value={text} maxLength={200} onChange={(e) => setText(e.target.value)} placeholder="例: 社外秘 / DRAFT" />
      </Field>
      {/* 簡易プレビュー */}
      <div className="relative flex h-28 items-center justify-center overflow-hidden rounded-lg border bg-white">
        <div className="absolute inset-3 space-y-1.5 opacity-60">
          {Array.from({ length: 6 }, (_, i) => (
            <div key={i} className="h-1.5 rounded bg-slate-100" style={{ width: `${90 - (i % 3) * 15}%` }} />
          ))}
        </div>
        <span
          className="relative max-w-[90%] truncate font-bold whitespace-nowrap"
          style={{
            color,
            opacity: opacity / 100,
            transform: `rotate(${-Number(angle)}deg)`,
            fontSize: Math.max(10, fontsize / 3),
          }}
        >
          {text || "テキスト"}
        </span>
      </div>
      <Field label="角度">
        <Segmented
          value={angle}
          onValueChange={setAngle}
          options={[
            { value: "0", label: "水平" },
            { value: "45", label: "斜め 45°" },
            { value: "90", label: "縦 90°" },
          ]}
        />
      </Field>
      <Field label="文字サイズ" hint={`${fontsize} pt`}>
        <Slider value={[fontsize]} min={12} max={150} step={2} onValueChange={([v]) => setFontsize(v)} />
      </Field>
      <Field label="不透明度" hint={`${opacity}%`}>
        <Slider value={[opacity]} min={5} max={100} step={5} onValueChange={([v]) => setOpacity(v)} />
      </Field>
      <Field label="色">
        <ColorPicker value={color} onChange={setColor} />
      </Field>
      <RunButton
        label="透かしを入れて保存"
        disabled={!text.trim()}
        onClick={() =>
          run("watermark", "透かしを追加中...", {
            text,
            fontsize,
            opacity: opacity / 100,
            angle: Number(angle),
            color,
          })
        }
      />
    </>
  );
}
