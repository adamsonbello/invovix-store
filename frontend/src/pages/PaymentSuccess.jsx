import React, { useEffect, useState, useRef } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { CheckCircle2, Loader2, XCircle } from "lucide-react";
import { motion } from "framer-motion";
import { useI18n } from "@/i18n";
import api from "@/lib/api";
import { useCart } from "@/context/CartContext";

export default function PaymentSuccess() {
  const { t } = useI18n();
  const [params] = useSearchParams();
  const { clear } = useCart();
  const [status, setStatus] = useState("checking");
  const attempts = useRef(0);
  const sessionId = params.get("session_id");

  useEffect(() => {
    if (params.get("paypal")) {
      setStatus("paid");
      clear();
      return;
    }
    if (!sessionId) {
      setStatus("error");
      return;
    }
    let timer;
    const poll = async () => {
      attempts.current += 1;
      if (attempts.current > 8) {
        setStatus("error");
        return;
      }
      try {
        const res = await api.get(`/payments/status/${sessionId}`);
        if (res.data.payment_status === "paid") {
          setStatus("paid");
          clear();
          return;
        }
        if (["expired", "failed"].includes(res.data.payment_status)) {
          setStatus("error");
          return;
        }
      } catch {
        setStatus("error");
        return;
      }
      timer = setTimeout(poll, 2000);
    };
    poll();
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId]);

  return (
    <div className="pt-40 pb-40 min-h-screen max-w-xl mx-auto px-5 text-center" data-testid="payment-success-page">
      {status === "checking" && (
        <div className="text-stone">
          <Loader2 className="w-10 h-10 mx-auto animate-spin text-brand" />
          <p className="mt-6 text-lg">{t.payment.verifying}</p>
        </div>
      )}
      {status === "paid" && (
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
          <CheckCircle2 className="w-16 h-16 mx-auto text-emerald-500" strokeWidth={1.4} />
          <h1 className="font-display font-black uppercase tracking-tighter text-5xl mt-6">{t.payment.successT}</h1>
          <p className="text-stone mt-4 text-lg">{t.payment.successD}</p>
          <div className="flex gap-3 justify-center mt-10">
            <Link to="/account" className="bg-ink text-cream px-7 py-3.5 rounded-full font-medium hover:bg-brand transition-colors">{t.payment.orders}</Link>
            <Link to="/shop" className="border border-ink/20 px-7 py-3.5 rounded-full font-medium hover:border-ink transition-colors">{t.payment.shop}</Link>
          </div>
        </motion.div>
      )}
      {status === "error" && (
        <div>
          <XCircle className="w-16 h-16 mx-auto text-brand" strokeWidth={1.4} />
          <h1 className="font-display font-black uppercase tracking-tighter text-4xl mt-6">{t.payment.failed}</h1>
          <Link to="/cart" className="inline-block mt-8 bg-ink text-cream px-7 py-3.5 rounded-full font-medium hover:bg-brand transition-colors">{t.cart.title}</Link>
        </div>
      )}
    </div>
  );
}
