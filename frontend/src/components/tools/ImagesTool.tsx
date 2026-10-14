import { useState } from "react";

import { Segmented } from "@/components/ui/radio-group";
import { Slider } from "@/components/ui/slider";
import { useRunTool } from "@/hooks/useRunTool";

import { Field, RunButton } from "./common";

const DPI_OPTIONS = [
  { value: "96", label: "96" },
  { value: "150", label: "150" },
  { value: "200", label: "200" },
  { value: "300", label: "300" },
  { value: "400", label: "400" },
];

export function ImagesTool() {
  const run = useRunTool();
  const [format, setFormat] = useState<"jpg" | "png">("jpg");
  const [dpi, setDpi] = useState("200");
  const [quality, setQuality] = useState(90);

  return (
    <>
      <p className="text-xs leading-relaxed text-muted-foreground">
        各ページを画像として書き出します。複数ページの場合はフォルダ（ブラウザではZIP）にまとめて保存します。
      </p>
      <Field label="形式">
        <Segmented
          value={format}
          onValueChange={setFormat}
          options={[
            { value: "jpg", label: "JPG（軽量）" },
            { value: "png", label: "PNG（劣化なし）" },
          ]}
        />
      </Field>
      <Field label="解像度 (dpi)" hint={dpi === "300" || dpi === "400" ? "印刷向け" : dpi === "96" ? "画面表示向け" : "標準"}>
        <Segmented value={dpi} onValueChange={setDpi} options={DPI_OPTIONS} />
      </Field>
      {format === "jpg" && (
        <Field label="JPG 画質" hint={quality}>
          <Slider value={[quality]} min={50} max={100} step={1} onValueChange={([v]) => setQuality(v)} />
        </Field>
      )}
      <RunButton
        label="画像に変換して保存"
        onClick={() => run("to-images", "画像に変換中...", { format, dpi: Number(dpi), quality })}
      />
    </>
  );
}
