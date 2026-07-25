import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useI18n } from "@/i18n";
import { useAuth } from "@/context/AuthContext";
import { formatApiError } from "@/lib/api";

export default function Register() {
  const { t } = useI18n();
  const { register } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ name: "", email: "", password: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await register(form.email, form.password, form.name);
      navigate("/account");
    } catch (err) {
      setError(formatApiError(err.response?.data?.detail) || err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="pt-32 pb-32 min-h-screen flex items-center" data-testid="register-page">
      <div className="max-w-md w-full mx-auto px-5">
        <h1 className="font-display font-black uppercase tracking-tighter text-5xl mb-2">{t.auth.registerT}</h1>
        <div className="w-12 h-1 bg-brand mb-10" />
        <form onSubmit={submit} className="space-y-5">
          <div>
            <label className="text-xs tracking-[0.15em] uppercase font-bold text-stone mb-2 block">{t.auth.name}</label>
            <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required className="w-full px-4 py-3 border border-ink/20 bg-transparent outline-none focus:border-ink transition-colors" data-testid="register-name" />
          </div>
          <div>
            <label className="text-xs tracking-[0.15em] uppercase font-bold text-stone mb-2 block">{t.auth.email}</label>
            <input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} required className="w-full px-4 py-3 border border-ink/20 bg-transparent outline-none focus:border-ink transition-colors" data-testid="register-email" />
          </div>
          <div>
            <label className="text-xs tracking-[0.15em] uppercase font-bold text-stone mb-2 block">{t.auth.password}</label>
            <input type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} required minLength={6} className="w-full px-4 py-3 border border-ink/20 bg-transparent outline-none focus:border-ink transition-colors" data-testid="register-password" />
          </div>
          {error && <p className="text-brand text-sm" data-testid="register-error">{error}</p>}
          <button type="submit" disabled={loading} className="w-full bg-ink text-cream py-4 rounded-full font-medium hover:bg-brand transition-colors disabled:opacity-50" data-testid="register-submit">
            {loading ? t.common.loading : t.auth.registerBtn}
          </button>
        </form>
        <p className="text-stone mt-6 text-sm">
          {t.auth.hasAccount} <Link to="/login" className="text-ink font-medium underline hover:text-brand">{t.auth.signin}</Link>
        </p>
      </div>
    </div>
  );
}
