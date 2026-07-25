import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Package } from "lucide-react";
import { useI18n } from "@/i18n";
import { useAuth } from "@/context/AuthContext";
import api from "@/lib/api";

const statusColor = {
  pending: "bg-amber-100 text-amber-700",
  processing: "bg-blue-100 text-blue-700",
  shipped: "bg-indigo-100 text-indigo-700",
  delivered: "bg-emerald-100 text-emerald-700",
  cancelled: "bg-red-100 text-red-700",
};

export default function Account() {
  const { t, lang } = useI18n();
  const { user } = useAuth();
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get("/orders").then((r) => setOrders(r.data.items)).finally(() => setLoading(false));
  }, []);

  return (
    <div className="pt-28 md:pt-36 pb-32" data-testid="account-page">
      <div className="max-w-[1200px] mx-auto px-5 md:px-10">
        <p className="text-xs tracking-[0.2em] uppercase font-bold text-brand mb-3">{t.account.hello}, {user?.name}</p>
        <h1 className="font-display font-black uppercase tracking-tighter text-5xl md:text-7xl mb-12">{t.account.title}</h1>

        <h2 className="font-display font-bold text-2xl mb-6">{t.account.orders}</h2>
        {loading ? (
          <p className="text-stone">{t.common.loading}</p>
        ) : orders.length === 0 ? (
          <div className="border border-ink/10 p-12 text-center">
            <Package className="w-10 h-10 mx-auto text-ink/30" strokeWidth={1.2} />
            <p className="text-stone mt-4">{t.account.noOrders}</p>
            <Link to="/shop" className="inline-block mt-6 bg-ink text-cream px-6 py-3 rounded-full font-medium hover:bg-brand transition-colors">{t.payment.shop}</Link>
          </div>
        ) : (
          <div className="space-y-4">
            {orders.map((o) => (
              <div key={o.id} className="border border-ink/10 p-6" data-testid={`order-${o.id}`}>
                <div className="flex flex-wrap justify-between gap-4 items-start">
                  <div>
                    <p className="font-display font-bold">{t.account.order} #{o.id.slice(0, 8).toUpperCase()}</p>
                    <p className="text-stone text-sm mt-1">{new Date(o.created_at).toLocaleDateString(lang)} · {o.items.length} {t.account.items}</p>
                  </div>
                  <div className="text-right">
                    <span className={`text-xs font-bold uppercase tracking-wide px-3 py-1 rounded-full ${statusColor[o.status] || "bg-gray-100 text-gray-700"}`}>{o.status}</span>
                    <p className="font-display font-black text-xl mt-2">{o.total.toFixed(2)}€</p>
                  </div>
                </div>
                <div className="flex gap-2 mt-4 pt-4 border-t border-ink/10 overflow-auto">
                  {o.items.map((it) => (
                    <img key={it.product_id} src={it.image} alt={it.title} className="w-14 h-16 object-cover bg-[#f0efed]" title={it.title} />
                  ))}
                </div>
                {o.tracking_number && (
                  <a
                    href={o.tracking_url || `https://parcelsapp.com/en/tracking/${o.tracking_number}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-2 mt-4 text-brand font-medium text-sm hover:text-ink transition-colors"
                    data-testid={`account-tracking-${o.id}`}
                  >
                    📦 {t.account.track}: {o.logistic_name ? `${o.logistic_name} · ` : ""}{o.tracking_number}
                  </a>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
