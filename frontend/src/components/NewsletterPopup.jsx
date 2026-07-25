import React, { useEffect, useState } from "react";
import { X, Gift } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { useI18n } from "@/i18n";
import api, { formatApiError } from "@/lib/api";
import { executeRecaptcha } from "@/lib/recaptcha";
import { toast } from "sonner";

export default function NewsletterPopup() {
  const { t } = useI18n();
  const [open, setOpen] = useState(false);
  const [email, setEmail] = useState("");
  const [website, setWebsite] = useState(""); // honeypot
  const [done, setDone] = useState(false);
  const [sending, setSending] = useState(false);
  const p = t.popup;

  useEffect(() => {
    if (localStorage.getItem("invovix_popup_seen")) return;
    const timer = setTimeout(() => setOpen(true), 12000);
    return () => clearTimeout(timer);
  }, []);

  const close = () => {
    setOpen(false);
    localStorage.setItem("invovix_popup_seen", "1");
  };

  const submit = async (e) => {
    e.preventDefault();
    if (!email) return;
    setSending(true);
    try {
      const token = await executeRecaptcha("newsletter");
      await api.post("/newsletter", { email, website, recaptcha_token: token });
      setDone(true);
      localStorage.setItem("invovix_popup_seen", "1");
    } catch (err) {
      toast.error(formatApiError(err.response?.data?.detail));
    } finally {
      setSending(false);
    }
  };

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-[80] bg-ink/60 backdrop-blur-sm flex items-center justify-center p-5"
          onClick={close}
          data-testid="newsletter-popup"
        >
          <motion.div
            initial={{ scale: 0.9, y: 20 }}
            animate={{ scale: 1, y: 0 }}
            exit={{ scale: 0.95, opacity: 0 }}
            transition={{ type: "spring", damping: 22, stiffness: 260 }}
            className="relative bg-cream max-w-md w-full p-9 md:p-11 overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >
            <button onClick={close} className="absolute right-4 top-4 text-ink/40 hover:text-ink transition-colors" data-testid="popup-close">
              <X className="w-5 h-5" />
            </button>
            <div className="w-14 h-14 rounded-full bg-brand/10 flex items-center justify-center mb-6">
              <Gift className="w-7 h-7 text-brand" strokeWidth={1.5} />
            </div>

            {done ? (
              <div data-testid="popup-success">
                <h3 className="font-display font-black text-3xl tracking-tighter leading-tight">{p.thanksT}</h3>
                <p className="text-ink/60 mt-3">{p.success}</p>
                <div className="mt-5 border-2 border-dashed border-brand rounded-lg py-4 text-center">
                  <p className="text-xs tracking-[0.2em] uppercase text-stone mb-1">{p.code}</p>
                  <p className="font-display font-black text-3xl text-brand tracking-widest" data-testid="popup-code">WELCOME10</p>
                </div>
                <button onClick={close} className="w-full mt-6 bg-ink text-cream py-3.5 rounded-full font-medium hover:bg-brand transition-colors">
                  {p.shopNow}
                </button>
              </div>
            ) : (
              <form onSubmit={submit}>
                <h3 className="font-display font-black text-3xl md:text-4xl tracking-tighter leading-[0.95]">{p.title}</h3>
                <p className="text-ink/60 mt-3">{p.sub}</p>
                <input
                  type="text"
                  value={website}
                  onChange={(e) => setWebsite(e.target.value)}
                  className="hidden"
                  tabIndex={-1}
                  autoComplete="off"
                  aria-hidden="true"
                />
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder={p.placeholder}
                  className="w-full mt-6 px-4 py-3.5 border border-ink/20 bg-transparent outline-none focus:border-ink transition-colors"
                  data-testid="popup-email"
                />
                <button
                  type="submit"
                  disabled={sending}
                  className="w-full mt-3 bg-brand text-white py-3.5 rounded-full font-medium hover:bg-ink transition-colors disabled:opacity-50"
                  data-testid="popup-submit"
                >
                  {sending ? "…" : p.cta}
                </button>
                <button type="button" onClick={close} className="w-full mt-3 text-stone text-sm hover:text-ink transition-colors">
                  {p.later}
                </button>
              </form>
            )}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
