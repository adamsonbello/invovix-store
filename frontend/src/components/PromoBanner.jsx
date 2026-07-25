import React from "react";
import { X } from "lucide-react";

export default function PromoBanner({ text, onClose }) {
  return (
    <div
      className="fixed top-0 inset-x-0 z-[60] bg-brand text-white h-9 flex items-center justify-center px-10 grain"
      data-testid="promo-banner"
    >
      <p className="text-xs md:text-sm tracking-wide font-medium text-center truncate relative z-10">{text}</p>
      <button
        onClick={onClose}
        className="absolute right-4 top-1/2 -translate-y-1/2 opacity-70 hover:opacity-100 transition-opacity z-10"
        aria-label="close banner"
        data-testid="promo-banner-close"
      >
        <X className="w-4 h-4" />
      </button>
    </div>
  );
}
