import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Cookie } from "lucide-react";
import { useI18n } from "@/i18n";

export default function CookieConsent() {
  const { t } = useI18n();
  const [show, setShow] = useState(false);

  useEffect(() => {
    if (window.location.pathname.startsWith("/admin")) return;
    if (!localStorage.getItem("invovix_cookie_consent")) {
      const id = setTimeout(() => setShow(true), 1500);
      return () => clearTimeout(id);
    }
  }, []);

  const choose = (value) => {
    localStorage.setItem("invovix_cookie_consent", value);
    window.dataLayer = window.dataLayer || [];
    window.dataLayer.push({ event: "cookie_consent", consent: value });
    setShow(false);
  };

  if (!show) return null;

  return (
    <div className="fixed bottom-0 inset-x-0 z-[75] bg-ink text-cream p-4 md:p-5" data-testid="cookie-consent">
      <div className="max-w-[1600px] mx-auto flex flex-col md:flex-row items-start md:items-center gap-4">
        <Cookie className="w-6 h-6 text-brand shrink-0 hidden md:block" strokeWidth={1.5} />
        <p className="text-sm text-white/80 flex-1">
          {t.cookie.text}{" "}
          <Link to="/legal/confidentialite" className="underline hover:text-white">{t.cookie.link}</Link>
        </p>
        <div className="flex gap-3 shrink-0">
          <button onClick={() => choose("refused")} className="px-5 py-2.5 border border-white/30 rounded-full text-sm font-medium hover:border-white transition-colors" data-testid="cookie-refuse">
            {t.cookie.refuse}
          </button>
          <button onClick={() => choose("accepted")} className="px-5 py-2.5 bg-brand text-white rounded-full text-sm font-medium hover:bg-white hover:text-ink transition-colors" data-testid="cookie-accept">
            {t.cookie.accept}
          </button>
        </div>
      </div>
    </div>
  );
}
