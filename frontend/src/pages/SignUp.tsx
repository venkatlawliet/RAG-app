import { useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { supabase } from "@/lib/supabase";
import { useAuth } from "@/auth/AuthContext";
import { Button, Card, Input } from "@/components/ui";

export default function SignUp() {
  const { session } = useAuth();
  const nav = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (session) return <Navigate to="/chat" replace />;

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setErr(null);
    setMsg(null);
    const { data, error } = await supabase.auth.signUp({ email, password });
    setBusy(false);
    if (error) {
      setErr(error.message);
      return;
    }
    if (data.session) nav("/chat");
    else setMsg("Check your email to confirm your account, then sign in.");
  }

  return (
    <div className="h-full flex items-center justify-center p-6">
      <Card className="w-full max-w-sm p-6">
        <h1 className="text-lg font-semibold mb-4">Create account</h1>
        <form onSubmit={onSubmit} className="space-y-3">
          <Input type="email" placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} required />
          <Input type="password" placeholder="Password (min 6 chars)" minLength={6} value={password} onChange={(e) => setPassword(e.target.value)} required />
          {err && <p className="text-sm text-red-600">{err}</p>}
          {msg && <p className="text-sm text-emerald-600">{msg}</p>}
          <Button type="submit" disabled={busy} className="w-full">
            {busy ? "Creating…" : "Sign up"}
          </Button>
        </form>
        <p className="text-sm text-zinc-500 mt-4">
          Have an account? <Link className="underline" to="/signin">Sign in</Link>
        </p>
      </Card>
    </div>
  );
}
