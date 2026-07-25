import React, { useEffect, useState } from "react";
import { Outlet, useLocation } from "react-router-dom";
import Lenis from "lenis";
import Header from "@/components/Header";
import Footer from "@/components/Footer";
import PromoBanner from "@/components/PromoBanner";
import WhatsAppButton from "@/components/WhatsAppButton";
import NewsletterPopup from "@/components/NewsletterPopup";
import CookieConsent from "@/components/CookieConsent";
import api from "@/lib/api";
import { useI18n } from "@/i18n";
import { loadRecaptcha } from "@/lib/recaptcha";

export default function Layout() {
  const location = useLocation();
  const { lang } = useI18n();
  const [settings, setSettings] = useState(null);
  const [bannerClosed, setBannerClosed] = useState(
    () => sessionStorage.getItem("invovix_banner_closed") === "1"
  );

  useEffect(() => {
    api.get("/settings").then((r) => setSettings(r.data)).catch(() => {});
    loadRecaptcha();
  }, []);

  useEffect(() => {
    const lenis = new Lenis({ duration: 1.1, smoothWheel: true });
    let raf;
    function loop(time) {
      lenis.raf(time);
      raf = requestAnimationFrame(loop);
    }
    raf = requestAnimationFrame(loop);
    return () => {
      cancelAnimationFrame(raf);
      lenis.destroy();
    };
  }, []);

  useEffect(() => {
    window.scrollTo(0, 0);
  }, [location.pathname]);

  const bannerText = settings
    ? lang === "en"
      ? settings.banner_text_en || settings.banner_text
      : settings.banner_text
    : "";
  const showBanner = Boolean(settings?.banner_enabled && bannerText && !bannerClosed);

  const closeBanner = () => {
    setBannerClosed(true);
    sessionStorage.setItem("invovix_banner_closed", "1");
  };

  return (
    <div className="min-h-screen bg-cream text-ink flex flex-col">
      {showBanner && <PromoBanner text={bannerText} onClose={closeBanner} />}
      <Header hasBanner={showBanner} />
      <main className="flex-1">
        <Outlet />
      </main>
      <Footer />
      {settings?.whatsapp_enabled && settings?.whatsapp_number && (
        <WhatsAppButton number={settings.whatsapp_number} />
      )}
      <NewsletterPopup />
      <CookieConsent />
    </div>
  );
}
