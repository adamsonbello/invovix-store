import React, { useState } from "react";
import { Mail, Send, Clock, MapPin } from "lucide-react";
import { useI18n } from "@/i18n";
import api, { formatApiError } from "@/lib/api";
import SEO from "@/components/SEO";
import { toast } from "sonner";

export default function Contact() {
  const { t } = useI18n();
  const [form, setForm] = useState({ name: "", email: "", subject: "", message: "" });
  const [sending, setSending] = useState(false);
  const c = t.contactPage;

  const submit = async (e) => {
    e.preventDefault();
    setSending(true);
    try {
      await api.post("/contact", form);
      toast.success(c.ok);
      setForm({ name: "", email: "", subject: "", message: "" });
    } catch (err) {
      toast.error(formatApiError(err.response?.data?.detail));
    } finally {
      setSending(false);
    }
  };

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  return (
    <div className="pt-28 md:pt-36 pb-32" data-testid="contact-page">
      <SEO title={c.title} description={c.sub} path="/contact" />
      <div className="max-w-[1400px] mx-auto px-5 md:px-10">
        <h1 className="font-display font-black uppercase tracking-tighter text-6xl md:text-8xl">{c.title}</h1>
        <p className="text-ink/60 text-lg mt-4 max-w-lg">{c.sub}</p>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-12 mt-16">
          <form onSubmit={submit} className="lg:col-span-2 grid grid-cols-1 md:grid-cols-2 gap-5">
            <Field label={c.name} value={form.name} onChange={set("name")} required testid="contact-name" />
            <Field label={c.email} type="email" value={form.email} onChange={set("email")} required testid="contact-email" />
            <Field label={c.subject} value={form.subject} onChange={set("subject")} span2 testid="contact-subject" />
            <div className="md:col-span-2">
              <label className="text-xs tracking-[0.15em] uppercase font-bold text-stone mb-2 block">{c.message}</label>
              <textarea value={form.message} onChange={set("message")} required rows={6} className="w-full px-4 py-3 border border-ink/20 bg-transparent outline-none focus:border-ink transition-colors" data-testid="contact-message" />
            </div>
            <button type="submit" disabled={sending} className="md:col-span-2 justify-self-start inline-flex items-center gap-2 bg-brand text-white px-8 py-4 rounded-full font-medium hover:bg-ink transition-colors disabled:opacity-50" data-testid="contact-submit">
              <Send className="w-4 h-4" /> {sending ? c.sending : c.send}
            </button>
          </form>

          <div className="bg-ink text-cream p-8 grain relative">
            <div className="relative z-10 space-y-8">
              <h2 className="font-display font-bold text-2xl">{c.info}</h2>
              <div className="flex items-start gap-4">
                <Mail className="w-5 h-5 text-brand mt-1" />
                <div><p className="font-medium">Email</p><p className="text-white/60">contact@invovix.store</p></div>
              </div>
              <div className="flex items-start gap-4">
                <Clock className="w-5 h-5 text-brand mt-1" />
                <div><p className="font-medium">Support</p><p className="text-white/60">{c.hours}</p></div>
              </div>
              <div className="flex items-start gap-4">
                <MapPin className="w-5 h-5 text-brand mt-1" />
                <div><p className="font-medium">Europe</p><p className="text-white/60">Zone euro · invovix.store</p></div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function Field({ label, value, onChange, type = "text", required, span2, testid }) {
  return (
    <div className={span2 ? "md:col-span-2" : ""}>
      <label className="text-xs tracking-[0.15em] uppercase font-bold text-stone mb-2 block">{label}</label>
      <input type={type} value={value} onChange={onChange} required={required} className="w-full px-4 py-3 border border-ink/20 bg-transparent outline-none focus:border-ink transition-colors" data-testid={testid} />
    </div>
  );
}
