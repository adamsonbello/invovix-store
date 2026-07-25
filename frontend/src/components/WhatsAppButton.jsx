import React from "react";
import { useI18n } from "@/i18n";

export default function WhatsAppButton({ number }) {
  const { t } = useI18n();
  const clean = (number || "").replace(/[^0-9]/g, "");
  if (!clean) return null;
  return (
    <a
      href={`https://wa.me/${clean}`}
      target="_blank"
      rel="noopener noreferrer"
      className="fixed bottom-6 left-6 z-40 group flex items-center gap-3"
      data-testid="whatsapp-button"
      aria-label={t.whatsapp.label}
    >
      <span className="w-14 h-14 rounded-full bg-[#25D366] shadow-lg flex items-center justify-center hover:scale-105 transition-transform">
        <svg viewBox="0 0 32 32" className="w-7 h-7 fill-white">
          <path d="M16 3C9.4 3 4 8.4 4 15c0 2.1.6 4.2 1.6 6L4 29l8.2-1.6c1.7.9 3.7 1.4 5.8 1.4h.001C22.6 28.8 28 23.4 28 16.8 28 9.9 22.6 3 16 3zm0 23.2c-1.8 0-3.5-.5-5-1.4l-.4-.2-4.9.9.9-4.8-.2-.4c-1-1.6-1.5-3.4-1.5-5.3C4.9 10.3 9.9 5.3 16 5.3S27.1 10.3 27.1 16 22.1 26.2 16 26.2zm6.1-7.6c-.3-.2-1.9-1-2.2-1.1-.3-.1-.5-.2-.7.2s-.8 1-1 1.2c-.2.2-.4.2-.7.1-.3-.2-1.4-.5-2.6-1.6-1-.9-1.6-1.9-1.8-2.3-.2-.3 0-.5.1-.7.1-.1.3-.4.5-.6.1-.2.2-.3.3-.5.1-.2 0-.4 0-.6s-.7-1.6-.9-2.2c-.2-.6-.5-.5-.7-.5h-.6c-.2 0-.5.1-.8.4-.3.3-1 1-1 2.5s1.1 2.9 1.2 3.1c.2.2 2.1 3.3 5.2 4.6.7.3 1.3.5 1.7.6.7.2 1.4.2 1.9.1.6-.1 1.9-.8 2.1-1.5.3-.7.3-1.4.2-1.5-.1-.2-.3-.2-.6-.4z" />
        </svg>
      </span>
      <span className="hidden md:block bg-ink text-cream text-sm font-medium px-4 py-2 rounded-full opacity-0 -translate-x-2 group-hover:opacity-100 group-hover:translate-x-0 transition-all whitespace-nowrap">
        {t.whatsapp.label}
      </span>
    </a>
  );
}
