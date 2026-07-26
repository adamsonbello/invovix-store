import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useI18n } from "@/i18n";
import { useAuth } from "@/context/AuthContext";
import { formatApiError } from "@/lib/api";

export default function Login() {
  const { t } = useI18n();
  const { login, verify2fa } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [tempToken, setTempToken] = useState("");
  const [code, setCode] = useState("");

  const STAFF = ["admin", "manager", "marketing", "support", "accounting"];
  const go = (user) => navigate(STAFF.includes(user.role) ? "/admin" : "/account");

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const res = await login(email, password);
      if (res && res.twofa_required) { setTempToken(res.temp_token); }
      else { go(res); }
    } catch (err) {
      setError(formatApiError(err.response?.data?.detail) || err.message);
    } finally {
      setLoading(false);
    }
  };

  const submit2fa = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const user = await verify2fa(tempToken, code);
      go(user);
    } catch (err) {
      setError(formatApiError(err.response?.data?.detail) || err.message);
    } finally {
      setLoading(false);
    }
  };

  if (tempToken) {
    return (
      <div className="pt-32 pb-32 min-h-screen flex items-center" data-testid="login-2fa-page">
        <div className="max-w-md w-full mx-auto px-5">
          <h1 className="font-display font-black uppercase tracking-tighter text-4xl mb-2">Vérification 2FA</h1>
          <div className="w-12 h-1 bg-brand mb-6" />
          <p className="text-stone mb-8 text-sm">Saisissez le code à 6 chiffres généré par votre application d'authentification.</p>
          <form onSubmit={submit2fa} className="space-y-5">
            <input inputMode="numeric" maxLength={6} value={code} onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))} placeholder="123456" required className="w-full px-4 py-4 border border-ink/20 bg-transparent outline-none focus:border-ink text-center text-2xl tracking-[0.5em] font-display" data-testid="login-2fa-code" autoFocus />
            {error && <p className="text-brand text-sm" data-testid="login-2fa-error">{error}</p>}
            <button type="submit" disabled={loading} className="w-full bg-ink text-cream py-4 rounded-full font-medium hover:bg-brand transition-colors disabled:opacity-50" data-testid="login-2fa-submit">
              {loading ? t.common.loading : "Vérifier"}
            </button>
            <button type="button" onClick={() => { setTempToken(""); setCode(""); setError(""); }} className="w-full text-stone text-sm hover:text-ink">← Retour</button>
          </form>
        </div>
      </div>
    );
  }

  return (
    <div className="pt-32 pb-32 min-h-screen flex items-center" data-testid="login-page">
      <div className="max-w-md w-full mx-auto px-5">
        <h1 className="font-display font-black uppercase tracking-tighter text-5xl mb-2">{t.auth.loginT}</h1>
        <div className="w-12 h-1 bg-brand mb-10" />
        <form onSubmit={submit} className="space-y-5">
          <div>
            <label className="text-xs tracking-[0.15em] uppercase font-bold text-stone mb-2 block">{t.auth.email}</label>
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required className="w-full px-4 py-3 border border-ink/20 bg-transparent outline-none focus:border-ink transition-colors" data-testid="login-email" />
          </div>
          <div>
            <label className="text-xs tracking-[0.15em] uppercase font-bold text-stone mb-2 block">{t.auth.password}</label>
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required className="w-full px-4 py-3 border border-ink/20 bg-transparent outline-none focus:border-ink transition-colors" data-testid="login-password" />
          </div>
          {error && <p className="text-brand text-sm" data-testid="login-error">{error}</p>}
          <button type="submit" disabled={loading} className="w-full bg-ink text-cream py-4 rounded-full font-medium hover:bg-brand transition-colors disabled:opacity-50" data-testid="login-submit">
            {loading ? t.common.loading : t.auth.loginBtn}
          </button>
        </form>
        <p className="text-stone mt-6 text-sm">
          {t.auth.noAccount} <Link to="/register" className="text-ink font-medium underline hover:text-brand">{t.auth.signup}</Link>
        </p>
      </div>
    </div>
  );
}
