import { Navigate, Route, Routes, Link, useLocation } from "react-router-dom";
import { AuthProvider, useAuth } from "@/auth/AuthContext";
import SignIn from "@/pages/SignIn";
import SignUp from "@/pages/SignUp";
import Chat from "@/pages/Chat";
import Files from "@/pages/Files";
import { supabase } from "@/lib/supabase";
import { Button } from "@/components/ui";

function Protected({ children }: { children: React.ReactNode }) {
  const { session, loading } = useAuth();
  if (loading) return <div className="p-6 text-sm text-zinc-500">Loading…</div>;
  if (!session) return <Navigate to="/signin" replace />;
  return <>{children}</>;
}

function Nav() {
  const { session } = useAuth();
  const loc = useLocation();
  if (!session) return null;
  const tab = (to: string, label: string) => (
    <Link
      to={to}
      className={`px-3 py-1.5 rounded-md text-sm ${
        loc.pathname.startsWith(to) ? "bg-zinc-200" : "hover:bg-zinc-100"
      }`}
    >
      {label}
    </Link>
  );
  return (
    <header className="border-b border-zinc-200 bg-white px-4 h-12 flex items-center gap-2">
      <span className="font-semibold mr-4">Agentic RAG</span>
      {tab("/chat", "Chat")}
      {tab("/files", "Files")}
      <div className="ml-auto flex items-center gap-3">
        <span className="text-xs text-zinc-500">{session.user.email}</span>
        <Button variant="ghost" onClick={() => supabase.auth.signOut()}>
          Sign out
        </Button>
      </div>
    </header>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <div className="h-full flex flex-col bg-zinc-50">
        <Nav />
        <main className="flex-1 min-h-0">
          <Routes>
            <Route path="/signin" element={<SignIn />} />
            <Route path="/signup" element={<SignUp />} />
            <Route
              path="/chat"
              element={
                <Protected>
                  <Chat />
                </Protected>
              }
            />
            <Route
              path="/files"
              element={
                <Protected>
                  <Files />
                </Protected>
              }
            />
            <Route path="*" element={<Navigate to="/chat" replace />} />
          </Routes>
        </main>
      </div>
    </AuthProvider>
  );
}
