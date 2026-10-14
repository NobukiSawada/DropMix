import { KeyRound, Loader2 } from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { api } from "@/lib/api";
import { useStore } from "@/store";

export function UnlockDialog({ fileId, onClose }: { fileId: string | null; onClose: () => void }) {
  const file = useStore((s) => (fileId ? s.files[fileId] : undefined));
  const unlockFile = useStore((s) => s.unlockFile);
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    setPassword("");
    setError(null);
  }, [fileId]);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!fileId || !password) return;
    setBusy(true);
    setError(null);
    try {
      const info = await api.unlock(fileId, password);
      unlockFile(info);
      toast.success(`「${info.name}」のロックを解除しました`);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Dialog open={!!file} onOpenChange={(open) => !open && onClose()}>
      <DialogContent>
        <form onSubmit={submit} className="grid gap-4">
          <DialogHeader>
            <div className="mb-1 flex size-10 items-center justify-center rounded-full bg-accent text-primary">
              <KeyRound className="size-5" />
            </div>
            <DialogTitle>パスワードを入力</DialogTitle>
            <DialogDescription className="break-all">
              「{file?.name}」はパスワードで保護されています。解除すると編集・結合できるようになり、出力されるPDFは保護なしになります。
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-1.5">
            <Input
              type="password"
              autoFocus
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="PDFのパスワード"
              aria-invalid={!!error}
            />
            {error && <p className="text-xs text-destructive">{error}</p>}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={onClose}>
              キャンセル
            </Button>
            <Button type="submit" disabled={!password || busy}>
              {busy && <Loader2 className="animate-spin" />}
              ロックを解除
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
