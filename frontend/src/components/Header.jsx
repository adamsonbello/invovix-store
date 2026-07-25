import React, { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { ShoppingBag, Menu, X, User, LayoutDashboard } from "lucide-react";
import { useI18n } from "@/i18n";
import { useAuth } from "@/context/AuthContext";
import { useCart } from "@/context/CartContext";

export default function Header() {
  const { t, lang, toggle } = useI18n();
  const { user, logout } = useAuth();
  const { count } = useCart();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener("scroll", onScroll);
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  const links = [
    { to: "/shop", label: t.nav.shop },
    { to: "/shop?category=smart-home", label: t.nav.smartHome },
    { to: "/shop?category=workspace", label: t.nav.workspace },
    { to: "/shop?category=security", label: t.nav.security },
    { to: "/blog", label: t.nav.blog },
    { to: "/contact", label: t.nav.contact },
  ];

  return (
    <header
      className={`fixed top-0 left-0 right-0 z-50 transition-[background,box-shadow] duration-500 ${
        scrolled ? "glass" : "bg-transparent"
      }`}
      data-testid="site-header"
    >
      <div className="max-w-[1600px] mx-auto px-5 md:px-10 h-16 md:h-20 flex items-center justify-between">
        <Link to="/" className="flex items-center gap-2 group" data-testid="logo-link">
          <span className="font-display font-black text-2xl md:text-3xl tracking-tighter uppercase">
            Invovix
          </span>
          <span className="w-2 h-2 bg-brand rounded-full mt-2 group-hover:scale-150 transition-transform" />
        </Link>

        <nav className="hidden lg:flex items-center gap-9">
          {links.map((l) => (
            <Link
              key={l.label}
              to={l.to}
              className="text-sm font-medium tracking-tight text-ink/80 hover:text-brand transition-colors"
              data-testid={`nav-${l.label}`}
            >
              {l.label}
            </Link>
          ))}
        </nav>

        <div className="flex items-center gap-4 md:gap-5">
          <button
            onClick={toggle}
            className="text-xs font-bold tracking-[0.15em] uppercase border border-ink/20 rounded-full px-3 py-1.5 hover:bg-ink hover:text-cream transition-colors"
            data-testid="lang-toggle"
          >
            {lang === "fr" ? "FR" : "EN"}
          </button>

          {user ? (
            <div className="hidden md:flex items-center gap-4">
              {user.role === "admin" && (
                <Link to="/admin" title={t.nav.admin} data-testid="nav-admin">
                  <LayoutDashboard className="w-5 h-5 hover:text-brand transition-colors" />
                </Link>
              )}
              <Link to="/account" title={t.nav.account} data-testid="nav-account">
                <User className="w-5 h-5 hover:text-brand transition-colors" />
              </Link>
              <button
                onClick={() => { logout(); navigate("/"); }}
                className="text-sm font-medium text-stone hover:text-brand transition-colors"
                data-testid="logout-btn"
              >
                {t.nav.logout}
              </button>
            </div>
          ) : (
            <Link
              to="/login"
              className="hidden md:inline-flex items-center bg-ink text-cream text-sm font-medium px-5 py-2 rounded-full hover:bg-brand transition-colors"
              data-testid="nav-login"
            >
              {t.nav.login}
            </Link>
          )}

          <Link to="/cart" className="relative" data-testid="cart-link">
            <ShoppingBag className="w-5 h-5 md:w-6 md:h-6" />
            {count > 0 && (
              <span
                className="absolute -top-2 -right-2 bg-brand text-white text-[10px] font-bold w-4.5 h-4.5 min-w-[18px] h-[18px] rounded-full flex items-center justify-center px-1"
                data-testid="cart-count"
              >
                {count}
              </span>
            )}
          </Link>

          <button
            className="lg:hidden"
            onClick={() => setOpen(true)}
            data-testid="mobile-menu-open"
          >
            <Menu className="w-6 h-6" />
          </button>
        </div>
      </div>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ x: "100%" }}
            animate={{ x: 0 }}
            exit={{ x: "100%" }}
            transition={{ type: "tween", ease: [0.22, 1, 0.36, 1], duration: 0.4 }}
            className="fixed inset-0 z-50 bg-cream p-6 lg:hidden"
            data-testid="mobile-menu"
          >
            <div className="flex justify-between items-center mb-12">
              <span className="font-display font-black text-2xl uppercase">Invovix</span>
              <button onClick={() => setOpen(false)} data-testid="mobile-menu-close">
                <X className="w-7 h-7" />
              </button>
            </div>
            <div className="flex flex-col gap-6">
              {links.map((l) => (
                <Link
                  key={l.label}
                  to={l.to}
                  onClick={() => setOpen(false)}
                  className="font-display text-3xl font-bold tracking-tight"
                >
                  {l.label}
                </Link>
              ))}
              <div className="h-px bg-ink/10 my-4" />
              {user ? (
                <>
                  {user.role === "admin" && (
                    <Link to="/admin" onClick={() => setOpen(false)} className="text-xl font-medium">{t.nav.admin}</Link>
                  )}
                  <Link to="/account" onClick={() => setOpen(false)} className="text-xl font-medium">{t.nav.account}</Link>
                  <button onClick={() => { logout(); setOpen(false); navigate("/"); }} className="text-xl font-medium text-left text-brand">{t.nav.logout}</button>
                </>
              ) : (
                <Link to="/login" onClick={() => setOpen(false)} className="text-xl font-medium">{t.nav.login}</Link>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </header>
  );
}
