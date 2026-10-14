import { Eye, EyeOff, Info } from "lucide-react";
import { useState } from "react";

import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { useRunTool } from "@/hooks/useRunTool";

import { Field, RunButton } from "./common";

function Toggle({ id, label, checked, onChange }: { id: string; label: string; checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <Label htmlFor={id} className="font-normal">
        {label}
      </Label>
      <Switch id={id} checked={checked} onCheckedChange={onChange} />
    </div>
  );
}

export function ProtectTool() {
  const run = useRunTool();
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [show, setShow] = useState(false);
  const [allowPrint, setAllowPrint] = useState(true);
  const [allowCopy, setAllowCopy] = useState(false);
  const [allowModify, setAllowModify] = useState(false);

  const mismatch = confirm !== "" && password !== confirm;

  return (
    <>
      <Field label="パスワード" htmlFor="pw">
        <div className="relative">
          <Input
            id="pw"
            type={show ? "text" : "password"}
            value={password}
            maxLength={128}
            onChange={(e) => setPassword(e.target.value)}
            className="pr-9"
            autoComplete="new-password"
          />
          <button
            type="button"
            onClick={() => setShow((v) => !v)}
            className="absolute top-1/2 right-2 -translate-y-1/2 cursor-pointer rounded p-1 text-muted-foreground hover:text-foreground"
            aria-label={show ? "パスワードを隠す" : "パスワードを表示"}
          >
            {show ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
          </button>
        </div>
      </Field>
      <Field label="パスワード（確認）" htmlFor="pw2">
        <Input
          id="pw2"
          type={show ? "text" : "password"}
          value={confirm}
          maxLength={128}
          onChange={(e) => setConfirm(e.target.value)}
          aria-invalid={mismatch}
          autoComplete="new-password"
        />
        {mismatch && <p className="text-xs text-destructive">パスワードが一致しません</p>}
      </Field>
      <div className="grid gap-3 rounded-lg border p-3">
        <Toggle id="perm-print" label="印刷を許可" checked={allowPrint} onChange={setAllowPrint} />
        <Toggle id="perm-copy" label="テキストのコピーを許可" checked={allowCopy} onChange={setAllowCopy} />
        <Toggle id="perm-modify" label="編集を許可" checked={allowModify} onChange={setAllowModify} />
      </div>
      <p className="flex gap-2 text-xs leading-relaxed text-muted-foreground">
        <Info className="mt-0.5 size-3.5 shrink-0 text-primary" />
        AES-256 で暗号化します。パスワード付きPDFを追加すると、ファイル一覧の「解除」からロックを外せます（解除後に保存したPDFは保護なしになります）。
      </p>
      <RunButton
        label="パスワードを設定して保存"
        disabled={!password || password !== confirm}
        onClick={() =>
          run("protect", "暗号化中...", {
            user_password: password,
            allow_print: allowPrint,
            allow_copy: allowCopy,
            allow_modify: allowModify,
          })
        }
      />
    </>
  );
}
