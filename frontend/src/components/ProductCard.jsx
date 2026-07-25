import React from "react";
import { Link, useNavigate } from "react-router-dom";
import { Plus, Heart } from "lucide-react";
import { useI18n } from "@/i18n";
import { useCart } from "@/context/CartContext";
import { useAuth } from "@/context/AuthContext";
import { useWishlist } from "@/context/WishlistContext";
import { toast } from "sonner";

export default function ProductCard({ product, index = 0 }) {
  const { lang, t } = useI18n();
  const { add } = useCart();
  const { user } = useAuth();
  const { has, toggle } = useWishlist();
  const navigate = useNavigate();
  const title = lang === "en" ? product.title_en || product.title : product.title;
  const hasCompare = product.compare_at_price > product.price;
  const wished = has(product.id);

  const onWish = async (e) => {
    e.preventDefault();
    if (!user) {
      toast.error(t.wishlist.loginFirst);
      navigate("/login");
      return;
    }
    const added = await toggle(product.id);
    toast.success(added ? t.wishlist.added : t.wishlist.removed);
  };

  return (
    <div
      className="group relative border-t border-ink/10"
      data-testid={`product-card-${product.id}`}
    >
      <Link to={`/product/${product.id}`} className="block">
        <div className="relative aspect-[4/5] overflow-hidden bg-[#f0efed]">
          <img
            src={product.images?.[0]}
            alt={title}
            className="absolute inset-0 w-full h-full object-cover hover-lift group-hover:scale-105"
          />
          {hasCompare && (
            <span className="absolute top-4 left-4 bg-brand text-white text-[11px] font-bold tracking-wide px-2.5 py-1 uppercase">
              -{Math.round(((product.compare_at_price - product.price) / product.compare_at_price) * 100)}%
            </span>
          )}
          <button
            onClick={onWish}
            className={`absolute top-3.5 right-3.5 w-9 h-9 rounded-full flex items-center justify-center transition-all ${
              wished ? "bg-brand text-white" : "bg-cream/80 backdrop-blur text-ink hover:bg-cream"
            }`}
            data-testid={`wishlist-toggle-${product.id}`}
            aria-label="toggle wishlist"
          >
            <Heart className="w-4 h-4" fill={wished ? "currentColor" : "none"} />
          </button>
          <button
            onClick={(e) => {
              e.preventDefault();
              add(product, 1);
              toast.success(t.product.added);
            }}
            className="absolute bottom-4 right-4 w-11 h-11 bg-ink text-cream rounded-full flex items-center justify-center opacity-0 translate-y-2 group-hover:opacity-100 group-hover:translate-y-0 transition-all duration-300 hover:bg-brand"
            data-testid={`quick-add-${product.id}`}
            aria-label="add to cart"
          >
            <Plus className="w-5 h-5" />
          </button>
        </div>
        <div className="py-5 px-1">
          <div className="flex items-start justify-between gap-3">
            <h3 className="font-display font-bold text-lg leading-tight tracking-tight group-hover:text-brand transition-colors">
              {title}
            </h3>
            <div className="text-right shrink-0">
              <p className="font-display font-bold text-lg">{product.price.toFixed(2)}€</p>
              {hasCompare && (
                <p className="text-sm text-stone line-through">{product.compare_at_price.toFixed(2)}€</p>
              )}
            </div>
          </div>
        </div>
      </Link>
    </div>
  );
}
