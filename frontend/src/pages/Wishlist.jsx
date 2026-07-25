import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Heart } from "lucide-react";
import { useI18n } from "@/i18n";
import { useAuth } from "@/context/AuthContext";
import { useWishlist } from "@/context/WishlistContext";
import api from "@/lib/api";
import ProductCard from "@/components/ProductCard";
import SEO from "@/components/SEO";

export default function Wishlist() {
  const { t } = useI18n();
  const { user } = useAuth();
  const { ids } = useWishlist();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!user) {
      setLoading(false);
      return;
    }
    api.get("/wishlist").then((r) => setItems(r.data.items)).finally(() => setLoading(false));
  }, [user, ids.length]);

  return (
    <div className="pt-28 md:pt-36 pb-32" data-testid="wishlist-page">
      <SEO title={t.wishlist.title} path="/wishlist" />
      <div className="max-w-[1600px] mx-auto px-5 md:px-10">
        <h1 className="font-display font-black uppercase tracking-tighter text-5xl md:text-7xl mb-12">{t.wishlist.title}</h1>

        {loading ? (
          <p className="text-stone">{t.common.loading}</p>
        ) : items.length === 0 ? (
          <div className="border border-ink/10 p-12 text-center" data-testid="wishlist-empty">
            <Heart className="w-10 h-10 mx-auto text-ink/30" strokeWidth={1.2} />
            <p className="text-stone mt-4">{t.wishlist.empty}</p>
            <Link to="/shop" className="inline-block mt-6 bg-ink text-cream px-6 py-3 rounded-full font-medium hover:bg-brand transition-colors">
              {t.wishlist.browse}
            </Link>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-x-6 gap-y-2">
            {items.map((p, i) => (
              <ProductCard key={p.id} product={p} index={i} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
