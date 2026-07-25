import React from "react";
import { Link } from "react-router-dom";
import { ArrowUpRight } from "lucide-react";
import { useI18n } from "@/i18n";

export default function Footer() {
  const { t } = useI18n();
  return (
    <footer className="relative bg-ink text-cream grain overflow-hidden" data-testid="site-footer">
      <div className="relative z-10 max-w-[1600px] mx-auto px-5 md:px-10 pt-20 md:pt-32 pb-10">
        <div className="grid grid-cols-1 md:grid-cols-12 gap-12 pb-16 border-b border-white/10">
          <div className="md:col-span-5">
            <h2 className="font-display text-5xl md:text-7xl font-black tracking-tighter uppercase leading-[0.9]">
              Invovix
            </h2>
            <p className="mt-6 text-white/60 max-w-sm text-lg">{t.footer.tagline}</p>
          </div>

          <div className="md:col-span-3 md:col-start-7">
            <p className="text-xs tracking-[0.2em] uppercase text-brand font-bold mb-6">{t.footer.shop}</p>
            <ul className="space-y-3 text-white/70">
              <li><Link to="/shop?category=smart-home" className="hover:text-white transition-colors">{t.nav.smartHome}</Link></li>
              <li><Link to="/shop?category=workspace" className="hover:text-white transition-colors">{t.nav.workspace}</Link></li>
              <li><Link to="/shop?category=security" className="hover:text-white transition-colors">{t.nav.security}</Link></li>
            </ul>
          </div>

          <div className="md:col-span-3">
            <p className="text-xs tracking-[0.2em] uppercase text-brand font-bold mb-6">{t.footer.newsletter}</p>
            <p className="text-white/60 mb-4">{t.footer.newsletterD}</p>
            <form className="flex border-b border-white/30 pb-2" onSubmit={(e) => e.preventDefault()}>
              <input
                type="email"
                placeholder="email@invovix.store"
                className="bg-transparent flex-1 outline-none text-white placeholder:text-white/40"
                data-testid="newsletter-input"
              />
              <button type="submit" data-testid="newsletter-submit" className="text-brand hover:translate-x-1 transition-transform">
                <ArrowUpRight className="w-5 h-5" />
              </button>
            </form>
          </div>
        </div>

        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 pt-8 text-sm text-white/40">
          <p>© {new Date().getFullYear()} Invovix · invovix.store · {t.footer.rights}</p>
          <div className="flex gap-6">
            <span className="hover:text-white transition-colors cursor-pointer">{t.footer.legal}</span>
            <span className="hover:text-white transition-colors cursor-pointer">{t.footer.contact}</span>
          </div>
        </div>
      </div>
    </footer>
  );
}
