import { useState } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { ArrowRight, ShieldCheck } from "lucide-react";
import { useAuth } from "../auth/AuthContext";

export function LoginPage() {
  const { user, admin, authLoading, adminLoading, signIn, authError, adminError } = useAuth();
  const [submitting, setSubmitting] = useState(false);
  const location = useLocation();
  if (authLoading || (user && adminLoading)) return <div className="auth-loading">Restoring secure session…</div>;
  if (user && admin?.active) return <Navigate to={location.state?.from?.pathname || "/admin/dashboard"} replace />;
  if (user && adminError?.status === 403) return <Navigate to="/admin/unauthorized" replace />;

  const submit = async () => {
    setSubmitting(true);
    try { await signIn(); } catch { /* AuthContext exposes a user-safe message. */ }
    finally { setSubmitting(false); }
  };

  return <main className="login-screen">
    <div className="login-side-art"><div className="login-orbit orbit-one" /><div className="login-orbit orbit-two" /><div className="login-art-copy"><div className="login-brand"><span className="brand-mark">E</span><span><b>ERRNO</b><small>OPERATIONS</small></span></div><div className="art-label"><i /> SECURE ADMIN WORKSPACE</div><h1>Workforce operations,<br /><em>under control.</em></h1><p>Manage users, shops and jobs with permissions verified by the ERRNO API.</p><div className="art-foot"><ShieldCheck size={16} /> Access is granted by an operator, never by self-registration.</div></div></div>
    <section className="login-panel">
      <div className="login-panel-inner"><div className="login-kicker">ADMINISTRATOR SIGN IN</div><h2>Welcome back</h2><p className="login-instruction">Continue with your authorized Google account.</p>
        <button className="google-signin" onClick={submit} disabled={submitting}><GoogleMark />{submitting ? "Opening Google sign-in…" : "Continue with Google"}<ArrowRight className="signin-arrow" size={17} /></button>
        {(authError || (adminError && adminError.status !== 403)) && <p className="auth-error" role="alert">{authError || adminError.message}</p>}
        <div className="login-security"><ShieldCheck size={17} /><span>Your Firebase identity is checked by the shared ERRNO API before access is granted.</span></div>
        <small className="login-legal">This portal does not support public administrator registration.</small>
      </div>
    </section>
  </main>;
}

function GoogleMark() {
  return <svg aria-hidden="true" width="18" height="18" viewBox="0 0 48 48"><path fill="#4285F4" d="M43.6 24.5c0-1.4-.1-2.8-.4-4.1H24v7.8h11a9.4 9.4 0 0 1-4.1 6.2v5h6.7c3.9-3.6 6-8.8 6-14.9Z"/><path fill="#34A853" d="M24 44c5.5 0 10.1-1.8 13.5-4.8l-6.7-5c-1.8 1.2-4 2-6.8 2-5.2 0-9.6-3.5-11.2-8.2H5.9v5.2A20 20 0 0 0 24 44Z"/><path fill="#FBBC05" d="M12.8 28a12 12 0 0 1 0-7.7v-5.2H5.9a20 20 0 0 0 0 18.1l6.9-5.2Z"/><path fill="#EA4335" d="M24 12.1c3 0 5.7 1 7.8 3l5.9-5.9C34.1 5.9 29.5 4 24 4A20 20 0 0 0 5.9 15.1l6.9 5.2c1.6-4.7 6-8.2 11.2-8.2Z"/></svg>;
}
