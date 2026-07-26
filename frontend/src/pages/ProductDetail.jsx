import React, { useEffect, useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowLeft, Minus, Plus, Check, Truck, ShieldCheck, Heart } from "lucide-react";
import { useI18n } from "@/i18n";
import api from "@/lib/api";
import { useCart } from "@/context/CartContext";
import { useAuth } from "@/context/AuthContext";
import { useWishlist } from "@/context/WishlistContext";
import { toast } from "sonner";
import SEO from "@/components/SEO";
import ProductReviews from "@/components/ProductReviews";
import RelatedProducts from "@/components/RelatedProducts";
import { Stars } from "@/components/StarRating";

export default function ProductDetail() {
  const { id } = useParams();
  const { t, lang } = useI18n();
  const { add } = useCart();
  const { user } = useAuth();
  const { has, toggle } = useWishlist();
  const navigate = useNavigate();
  const [product, setProduct] = useState(null);
  const [qty, setQty] = useState(1);
  const [selVid, setSelVid] = useState("");

  useEffect(() => {
    api.get(`/products/${id}`).then((r) => setProduct(r.data)).catch(() => navigate("/shop"));
  }, [id, navigate]);

  if (!product) return <div className="pt-40 text-center text-stone min-h-screen">{t.common.loading}</div>;

  const title = lang === "en" ? product.title_en || product.title : product.title;
  const desc = lang === "en" ? product.description_en || product.description : product.description;
  const hasCompare = product.compare_at_price > product.price;
  const wished = has(product.id);

  const variants = product.variants || [];
  const activeVar = variants.find((v) => v.vid === selVid) || variants[0] || null;
  const showVariants = variants.length > 1;
  const displayPrice = activeVar ? activeVar.price : product.price;
  const displayImage = (activeVar && activeVar.image) || product.images?.[0];
  const knownStock = activeVar && typeof activeVar.stock === "number"
    ? activeVar.stock
    : product.stock_total;
  const outOfStock = typeof knownStock === "number" && knownStock <= 0;
  const lowStock = typeof knownStock === "number" && knownStock > 0 && knownStock <= 5;

  const onWish = async () => {
    if (!user) {
      toast.error(t.wishlist.loginFirst);
      navigate("/login");
      return;
    }
    const added = await toggle(product.id);
    toast.success(added ? t.wishlist.added : t.wishlist.removed);
  };

  const buyNow = () => {
    add(product, qty, activeVar);
    navigate("/cart");
  };

  return (
    <div className="pt-24 md:pt-28" data-testid="product-detail-page">
      <SEO
        title={title}
        description={desc?.slice(0, 160)}
        path={`/product/${product.id}`}
        image={product.images?.[0]}
        type="product"
        jsonLd={{
          "@context": "https://schema.org",
          "@type": "Product",
          name: title,
          description: desc,
          image: product.images,
          brand: { "@type": "Brand", name: "Invovix" },
          offers: {
            "@type": "Offer",
            price: product.price,
            priceCurrency: "EUR",
            availability: "https://schema.org/InStock",
          },
          ...(product.rating_count
            ? { aggregateRating: { "@type": "AggregateRating", ratingValue: product.rating_avg, reviewCount: product.rating_count } }
            : {}),
        }}
      />
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
            <img src={displayImage} alt={title} className="absolute inset-0 w-full h-full object-cover" />
            {hasCompare && !outOfStock && (
              <span className="absolute top-5 left-5 bg-brand text-white text-xs font-bold px-3 py-1.5 uppercase tracking-wide">
                {t.product.save} {(product.compare_at_price - product.price).toFixed(2)}€
              </span>
            )}
            {outOfStock && (
              <span className="absolute top-5 left-5 bg-ink text-cream text-xs font-bold px-3 py-1.5 uppercase tracking-wide" data-testid="pd-oos-badge">
                {t.product.outOfStock}
              </span>
            )}
          </motion.div>

          <div className="lg:py-8">
            <p className="text-xs tracking-[0.2em] uppercase font-bold text-brand mb-4">{product.category}</p>
            <h1 className="font-display font-black uppercase tracking-tighter leading-[0.92] text-4xl md:text-6xl">
              {title}
            </h1>

            <div className="flex items-baseline gap-4 mt-6">
              <span className="font-display font-bold text-4xl" data-testid="pd-price">{displayPrice.toFixed(2)}€</span>
              {hasCompare && <span className="text-stone line-through text-2xl">{product.compare_at_price.toFixed(2)}€</span>}
            </div>

            {product.rating_count > 0 && (
              <div className="flex items-center gap-2 mt-3" data-testid="pd-rating">
                <Stars value={product.rating_avg} size={18} />
                <span className="text-sm text-stone">{product.rating_avg?.toFixed(1)} · {product.rating_count} {t.reviews.based}</span>
              </div>
            )}

            {showVariants && (
              <div className="mt-6" data-testid="pd-variants">
                <p className="text-xs tracking-[0.15em] uppercase font-bold text-stone mb-3">{t.product.variant}</p>
                <div className="flex flex-wrap gap-2">
                  {variants.map((v) => {
                    const vOos = typeof v.stock === "number" && v.stock <= 0;
                    return (
                      <button
                        key={v.vid}
                        onClick={() => !vOos && setSelVid(v.vid)}
                        disabled={vOos}
                        className={`px-4 py-2 border text-sm transition-colors ${
                          activeVar?.vid === v.vid ? "border-ink bg-ink text-cream" : "border-ink/20 hover:border-ink"
                        } ${vOos ? "opacity-40 line-through cursor-not-allowed" : ""}`}
                        data-testid={`pd-variant-${v.vid}`}
                      >
                        {v.name}
                      </button>
                    );
                  })}
                </div>
              </div>
            )}

            <div className="flex items-center gap-2 mt-4 text-sm font-medium" data-testid="pd-stock">
              {outOfStock ? (
                <span className="text-red-500">● {t.product.outOfStock}</span>
              ) : lowStock ? (
                <span className="text-amber-600">● {t.product.lowStock.replace("{n}", knownStock)}</span>
              ) : (
                <span className="flex items-center gap-2 text-emerald-600"><Check className="w-4 h-4" /> {t.product.inStock}</span>
              )}
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
                onClick={() => { add(product, qty, activeVar); toast.success(t.product.added); }}
                disabled={outOfStock}
                className="flex-1 border border-ink px-6 py-4 rounded-full font-medium hover:bg-ink hover:text-cream transition-colors disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:bg-transparent disabled:hover:text-ink"
                data-testid="add-to-cart-btn"
              >
                {outOfStock ? t.product.outOfStock : t.product.add}
              </button>
              <button
                onClick={onWish}
                className={`w-14 h-14 shrink-0 rounded-full border flex items-center justify-center transition-colors ${
                  wished ? "bg-brand text-white border-brand" : "border-ink/20 hover:border-ink"
                }`}
                data-testid="pd-wishlist-toggle"
                aria-label="toggle wishlist"
              >
                <Heart className="w-5 h-5" fill={wished ? "currentColor" : "none"} />
              </button>
            </div>
            <button
              onClick={buyNow}
              disabled={outOfStock}
              className="w-full mt-3 bg-brand text-white px-6 py-4 rounded-full font-medium hover:bg-ink transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
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

        <ProductReviews productId={product.id} />
        <RelatedProducts productId={product.id} />
      </div>
    </div>
  );
}
