import React from "react";
import { Link } from "react-router-dom";
import { XCircle } from "lucide-react";
import { useI18n } from "@/i18n";

export default function PaymentCancel() {
  const { t } = useI18n();
  return (
    <div className="pt-40 pb-40 min-h-screen max-w-xl mx-auto px-5 text-center" data-testid="payment-cancel-page">
      <XCircle className="w-16 h-16 mx-auto text-stone" strokeWidth={1.4} />
      <h1 className="font-display font-black uppercase tracking-tighter text-5xl mt-6">{t.payment.cancelT}</h1>
      <p className="text-stone mt-4 text-lg">{t.payment.cancelD}</p>
      <Link to="/cart" className="inline-block mt-10 bg-ink text-cream px-7 py-3.5 rounded-full font-medium hover:bg-brand transition-colors">
        {t.cart.title}
      </Link>
    </div>
  );
}
