import React, { useEffect, useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowLeft, Minus, Plus, Check, Truck, ShieldCheck } from "lucide-react";
import { useI18n } from "@/i18n";
import api from "@/lib/api";
import { useCart } from "@/context/CartContext";
import { toast } from "sonner";

export default function ProductDetail() {
  const { id } = useParams();
  const { t, lang } = useI18n();
  const { add } = useCart();
  const navigate = useNavigate();
  const [product, setProduct] = useState(null);
  const [qty, setQty] = useState(1);

  useEffect(() => {
    api.get(`/products/${id}`).then((r) => setProduct(r.data)).catch(() => navigate("/shop"));
  }, [id, navigate]);

  if (!product) return <div className="pt-40 text-center text-stone min-h-screen">{t.common.loading}</div>;

  const title = lang === "en" ? product.title_en || product.title : product.title;
  const desc = lang === "en" ? product.description_en || product.description : product.description;
  const hasCompare = product.compare_at_price > product.price;

  const buyNow = () => {
    add(product, qty);
    navigate("/cart");
  };

  return (
    <div className="pt-24 md:pt-28" data-testid="product-detail-page">
      <div className="max-w-[1600px] mx-auto px-5 md:px-10 py-8">
        <Link to="/shop" className="inline-flex items-center gap-2 text-stone hover:text-brand transition-colors mb-8" data-testid="back-to-shop">
          <ArrowLeft className="w-4 h-4" /> {t.product.back}
        </Link>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-10 lg:gap-20">
          <motion.div
            initial={{ opacity: 0, scale: 0.98 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
            className="relative aspect-square bg-[#f0efed] overflow-hidden"
          >
            <img src={product.images?.[0]} alt={title} className="absolute inset-0 w-full h-full object-cover" />
            {hasCompare && (
              <span className="absolute top-5 left-5 bg-brand text-white text-xs font-bold px-3 py-1.5 uppercase tracking-wide">
                {t.product.save} {(product.compare_at_price - product.price).toFixed(2)}€
              </span>
            )}
          </motion.div>

          <div className="lg:py-8">
            <p className="text-xs tracking-[0.2em] uppercase font-bold text-brand mb-4">{product.category}</p>
            <h1 className="font-display font-black uppercase tracking-tighter leading-[0.92] text-4xl md:text-6xl">
              {title}
            </h1>

            <div className="flex items-baseline gap-4 mt-6">
              <span className="font-display font-bold text-4xl">{product.price.toFixed(2)}€</span>
              {hasCompare && <span className="text-stone line-through text-2xl">{product.compare_at_price.toFixed(2)}€</span>}
            </div>

            <div className="flex items-center gap-2 mt-4 text-emerald-600 text-sm font-medium">
              <Check className="w-4 h-4" /> {t.product.inStock}
            </div>

            <p className="text-ink/70 text-lg leading-relaxed mt-8 border-t border-ink/10 pt-8">{desc}</p>

            <div className="flex items-center gap-4 mt-10">
              <div className="flex items-center border border-ink/20 rounded-full">
                <button onClick={() => setQty((q) => Math.max(1, q - 1))} className="p-3.5 hover:text-brand" data-testid="qty-minus">
                  <Minus className="w-4 h-4" />
                </button>
                <span className="w-10 text-center font-medium" data-testid="qty-value">{qty}</span>
                <button onClick={() => setQty((q) => q + 1)} className="p-3.5 hover:text-brand" data-testid="qty-plus">
                  <Plus className="w-4 h-4" />
                </button>
              </div>
              <button
                onClick={() => { add(product, qty); toast.success(t.product.added); }}
                className="flex-1 border border-ink px-6 py-4 rounded-full font-medium hover:bg-ink hover:text-cream transition-colors"
                data-testid="add-to-cart-btn"
              >
                {t.product.add}
              </button>
            </div>
            <button
              onClick={buyNow}
              className="w-full mt-3 bg-brand text-white px-6 py-4 rounded-full font-medium hover:bg-ink transition-colors"
              data-testid="buy-now-btn"
            >
              {t.product.buy}
            </button>

            <div className="grid grid-cols-2 gap-4 mt-10 text-sm">
              <div className="flex items-center gap-3 text-stone">
                <Truck className="w-5 h-5 text-ink" strokeWidth={1.5} /> {t.trust.free}
              </div>
              <div className="flex items-center gap-3 text-stone">
                <ShieldCheck className="w-5 h-5 text-ink" strokeWidth={1.5} /> {t.trust.secure}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
