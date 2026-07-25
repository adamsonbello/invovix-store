import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Minus, Plus, X, ArrowRight, ShoppingBag, Tag } from "lucide-react";
import { useI18n } from "@/i18n";
import { useCart } from "@/context/CartContext";
import api, { formatApiError } from "@/lib/api";
import { toast } from "sonner";

export default function Cart() {
  const { t, lang } = useI18n();
  const { items, updateQty, remove, subtotal, promo, applyPromo, removePromo, discount } = useCart();
  const navigate = useNavigate();
  const [code, setCode] = useState("");
  const [checking, setChecking] = useState(false);
  const shipping = subtotal >= 50 || subtotal === 0 ? 0 : 4.9;
  const total = Math.max(0, subtotal + shipping - discount);

  const applyCode = async (e) => {
    e.preventDefault();
    if (!code.trim()) return;
    setChecking(true);
    try {
      const r = await api.post("/promo/validate", { code, subtotal });
      applyPromo(r.data);
      toast.success(t.promo.applied);
      setCode("");
    } catch (err) {
      toast.error(formatApiError(err.response?.data?.detail) || t.promo.invalid);
    } finally {
      setChecking(false);
    }
  };

  if (items.length === 0) {
    return (
      <div className="pt-40 pb-32 min-h-screen max-w-3xl mx-auto px-5 text-center" data-testid="cart-empty">
        <ShoppingBag className="w-12 h-12 mx-auto text-ink/30" strokeWidth={1.2} />
        <h1 className="font-display font-black uppercase tracking-tighter text-4xl mt-6">{t.cart.title}</h1>
        <p className="text-stone mt-3">{t.cart.empty}</p>
        <Link to="/shop" className="inline-flex items-center gap-2 mt-8 bg-ink text-cream px-7 py-4 rounded-full font-medium hover:bg-brand transition-colors">
          {t.cart.continue} <ArrowRight className="w-4 h-4" />
        </Link>
      </div>
    );
  }

  return (
    <div className="pt-28 md:pt-36 pb-32" data-testid="cart-page">
      <div className="max-w-[1600px] mx-auto px-5 md:px-10">
        <h1 className="font-display font-black uppercase tracking-tighter text-5xl md:text-7xl mb-12">{t.cart.title}</h1>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-12">
          <div className="lg:col-span-2">
            {items.map((it) => {
              const title = lang === "en" ? it.title_en || it.title : it.title;
              return (
                <div key={it.product_id} className="flex gap-5 py-6 border-t border-ink/10" data-testid={`cart-item-${it.product_id}`}>
                  <img src={it.image} alt={title} className="w-24 h-28 object-cover bg-[#f0efed]" />
                  <div className="flex-1 flex flex-col justify-between">
                    <div className="flex justify-between gap-4">
                      <div>
                        <h3 className="font-display font-bold text-lg tracking-tight">{title}</h3>
                        <p className="text-stone text-sm">{it.price.toFixed(2)}€ {t.cart.each}</p>
                      </div>
                      <button onClick={() => remove(it.product_id)} className="text-stone hover:text-brand" data-testid={`remove-${it.product_id}`}>
                        <X className="w-5 h-5" />
                      </button>
                    </div>
                    <div className="flex justify-between items-center">
                      <div className="flex items-center border border-ink/20 rounded-full">
                        <button onClick={() => updateQty(it.product_id, it.quantity - 1)} className="p-2.5 hover:text-brand" data-testid={`dec-${it.product_id}`}>
                          <Minus className="w-3.5 h-3.5" />
                        </button>
                        <span className="w-8 text-center text-sm font-medium">{it.quantity}</span>
                        <button onClick={() => updateQty(it.product_id, it.quantity + 1)} className="p-2.5 hover:text-brand" data-testid={`inc-${it.product_id}`}>
                          <Plus className="w-3.5 h-3.5" />
                        </button>
                      </div>
                      <span className="font-display font-bold text-lg">{(it.price * it.quantity).toFixed(2)}€</span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          <div className="lg:col-span-1">
            <div className="bg-surface p-8 sticky top-28">
              <h2 className="font-display font-bold text-xl mb-6">{t.checkout.summary}</h2>

              <div className="mb-6">
                {promo ? (
                  <div className="flex items-center justify-between bg-brand/10 text-brand px-4 py-3 rounded-lg" data-testid="promo-applied">
                    <span className="flex items-center gap-2 font-medium text-sm"><Tag className="w-4 h-4" /> {promo.code}</span>
                    <button onClick={removePromo} className="text-brand hover:text-ink transition-colors" data-testid="promo-remove"><X className="w-4 h-4" /></button>
                  </div>
                ) : (
                  <form onSubmit={applyCode} className="flex gap-2">
                    <input
                      value={code}
                      onChange={(e) => setCode(e.target.value)}
                      placeholder={t.promo.placeholder}
                      className="flex-1 px-4 py-2.5 border border-ink/20 bg-transparent outline-none focus:border-ink transition-colors text-sm"
                      data-testid="promo-input"
                    />
                    <button type="submit" disabled={checking} className="px-4 py-2.5 border border-ink font-medium text-sm hover:bg-ink hover:text-cream transition-colors disabled:opacity-50" data-testid="promo-apply">
                      {t.promo.apply}
                    </button>
                  </form>
                )}
              </div>

              <div className="space-y-3 text-sm border-b border-ink/10 pb-6">
                <div className="flex justify-between"><span className="text-stone">{t.cart.subtotal}</span><span>{subtotal.toFixed(2)}€</span></div>
                {discount > 0 && (
                  <div className="flex justify-between text-brand font-medium" data-testid="cart-discount"><span>{t.promo.discount}</span><span>−{discount.toFixed(2)}€</span></div>
                )}
                <div className="flex justify-between"><span className="text-stone">{t.cart.shipping}</span><span>{shipping === 0 ? t.cart.free : `${shipping.toFixed(2)}€`}</span></div>
              </div>
              <div className="flex justify-between items-baseline py-6">
                <span className="font-display font-bold text-lg">{t.cart.total}</span>
                <span className="font-display font-black text-2xl">{total.toFixed(2)}€</span>
              </div>
              <button
                onClick={() => navigate("/checkout")}
                className="w-full bg-brand text-white px-6 py-4 rounded-full font-medium hover:bg-ink transition-colors flex items-center justify-center gap-2"
                data-testid="checkout-btn"
              >
                {t.cart.checkout} <ArrowRight className="w-4 h-4" />
              </button>
              <Link to="/shop" className="block text-center text-stone hover:text-brand text-sm mt-4 transition-colors">
                {t.cart.continue}
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
