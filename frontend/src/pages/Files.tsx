import { useCallback, useEffect, useRef, useState } from "react";
import { apiDelete, apiGet, apiUpload, API_BASE } from "@/lib/api";
import { supabase } from "@/lib/supabase";
import { Button, Card } from "@/components/ui";

type FileRow = {
  id: string;
  filename: string | null;
  bytes: number | null;
  openai_file_id: string;
  status: string;
  created_at: string;
};

export default function Files() {
  const [rows, setRows] = useState<FileRow[]>([]);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const refresh = useCallback(async () => {
    const r = await apiGet<FileRow[]>("/api/files");
    setRows(r);
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  // Poll status of any in-progress files.
  useEffect(() => {
    const pending = rows.filter((r) => r.status !== "completed" && r.status !== "failed");
    if (pending.length === 0) return;
    const t = setInterval(async () => {
      const session = (await supabase.auth.getSession()).data.session;
      if (!session) return;
      const updates = await Promise.all(
        pending.map((r) =>
          fetch(`${API_BASE}/api/files/${r.id}/status`, {
            headers: { Authorization: `Bearer ${session.access_token}` },
          }).then((res) => res.json()).catch(() => null),
        ),
      );
      setRows((cur) =>
        cur.map((r) => {
          const u = updates.find((x) => x?.id === r.id);
          return u ? { ...r, status: u.status } : r;
        }),
      );
    }, 3000);
    return () => clearInterval(t);
  }, [rows]);

  async function onUpload(files: FileList | null) {
    if (!files || files.length === 0) return;
    setErr(null);
    setBusy(true);
    try {
      for (const f of Array.from(files)) {
        await apiUpload<FileRow>("/api/files", f);
      }
      await refresh();
    } catch (e: any) {
      setErr(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function onDelete(id: string) {
    await apiDelete(`/api/files/${id}`);
    await refresh();
  }

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-4">
      <h1 className="text-xl font-semibold">Files</h1>
      <Card
        className="p-8 border-dashed text-center cursor-pointer"
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => {
          e.preventDefault();
          onUpload(e.dataTransfer.files);
        }}
      >
        <p className="text-sm text-zinc-600">
          {busy ? "Uploading…" : "Drop files here or click to choose"}
        </p>
        <input
          ref={inputRef}
          type="file"
          multiple
          className="hidden"
          onChange={(e) => onUpload(e.target.files)}
        />
      </Card>
      {err && <p className="text-sm text-red-600">{err}</p>}
      <Card className="divide-y">
        {rows.length === 0 && <p className="p-4 text-sm text-zinc-500">No files uploaded yet.</p>}
        {rows.map((r) => (
          <div key={r.id} className="flex items-center gap-3 p-3">
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium truncate">{r.filename}</p>
              <p className="text-xs text-zinc-500">
                {r.bytes ? `${(r.bytes / 1024).toFixed(1)} KB` : ""} · {r.status}
              </p>
            </div>
            <Button variant="danger" onClick={() => onDelete(r.id)}>Delete</Button>
          </div>
        ))}
      </Card>
    </div>
  );
}
