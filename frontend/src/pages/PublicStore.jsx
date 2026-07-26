import React, { useEffect, useMemo, useState } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import { Helmet } from "react-helmet-async";
import { motion } from "framer-motion";
import { ShoppingBag, Plus, ArrowRight, ExternalLink } from "lucide-react";
import api from "@/lib/api";
import { useI18n } from "@/i18n";
import { useCart } from "@/context/CartContext";
import { toast } from "sonner";

const CAT_LABELS = {
  "smart-home": "Maison connectée",
  security: "Sécurité",
  workspace: "Télétravail",
};

function ThemedCard({ product, accent, lang }) {
  const { add } = useCart();
  const title = lang === "en" ? product.title_en || product.title : product.title;
  const hasCompare = product.compare_at_price > product.price;
  const outOfStock = product.in_stock === false;
  return (
    <div className="group relative" data-testid={`store-product-${product.id}`}>
      <Link to={`/product/${product.id}`} className="block">
        <div className="relative aspect-[4/5] overflow-hidden bg-[#f0efed]">
          <img src={product.images?.[0]} alt={title} className="absolute inset-0 w-full h-full object-cover transition-transform duration-700 group-hover:scale-105" />
          {hasCompare && !outOfStock && (
            <span className="absolute top-4 left-4 text-white text-[11px] font-bold tracking-wide px-2.5 py-1 uppercase" style={{ backgroundColor: accent }}>
              -{Math.round(((product.compare_at_price - product.price) / product.compare_at_price) * 100)}%
            </span>
          )}
          {outOfStock && (
            <div className="absolute inset-0 bg-cream/60 flex items-center justify-center">
              <span className="bg-ink text-cream text-xs font-bold tracking-wide px-3 py-1.5 uppercase">Épuisé</span>
            </div>
          )}
          {!outOfStock && (
            <button
              onClick={(e) => { e.preventDefault(); add(product, 1); toast.success("Ajouté au panier"); }}
              className="absolute bottom-4 right-4 w-11 h-11 text-white rounded-full flex items-center justify-center opacity-0 translate-y-2 group-hover:opacity-100 group-hover:translate-y-0 transition-all duration-300"
              style={{ backgroundColor: accent }}
              data-testid={`store-add-${product.id}`}
              aria-label="ajouter au panier"
            >
              <Plus className="w-5 h-5" />
            </button>
          )}
        </div>
        <div className="py-5">
          <div className="flex items-start justify-between gap-3">
            <h3 className="font-display font-bold text-lg leading-tight tracking-tight transition-colors">
              {title}
            </h3>
            <div className="text-right shrink-0">
              <p className="font-display font-bold text-lg">{product.price.toFixed(2)}€</p>
              {hasCompare && <p className="text-sm text-stone line-through">{product.compare_at_price.toFixed(2)}€</p>}
            </div>
          </div>
        </div>
      </Link>
    </div>
  );
}

export default function PublicStore({ slug: slugProp }) {
  const params = useParams();
  const slug = slugProp || params.slug;
  const { lang } = useI18n();
  const navigate = useNavigate();
  const { count } = useCart();
  const [data, setData] = useState(null);
  const [notFound, setNotFound] = useState(false);
  const [cat, setCat] = useState("all");

  useEffect(() => {
    setData(null); setNotFound(false);
    api.get(`/public/stores/${slug}`)
      .then((r) => setData(r.data))
      .catch(() => setNotFound(true));
  }, [slug]);

  const accent = data?.store?.accent_color || "#FF3300";
  const cats = useMemo(() => {
    if (!data) return [];
    return [...new Set(data.products.map((p) => p.category))];
  }, [data]);
  const products = useMemo(() => {
    if (!data) return [];
    return cat === "all" ? data.products : data.products.filter((p) => p.category === cat);
  }, [data, cat]);

  if (notFound) {
    return (
      <div className="min-h-screen bg-cream flex flex-col items-center justify-center text-center px-6" data-testid="store-not-found">
        <p className="font-display font-black text-4xl mb-3">Boutique introuvable</p>
        <p className="text-stone mb-6">Cette vitrine n'existe pas ou a été désactivée.</p>
        <Link to="/" className="inline-flex items-center gap-2 bg-ink text-cream px-6 py-3 rounded-full font-medium hover:bg-brand transition-colors">Aller sur Invovix <ArrowRight className="w-4 h-4" /></Link>
      </div>
    );
  }

  if (!data) {
    return <div className="min-h-screen bg-cream flex items-center justify-center" data-testid="store-loading"><div className="w-10 h-10 border-2 border-ink/20 border-t-ink rounded-full animate-spin" /></div>;
  }

  const store = data.store;
  const name = store.name;

  return (
    <div className="min-h-screen bg-cream text-ink" data-testid="public-store-page">
      <Helmet>
        <html lang={lang} />
        <title>{`${name} — ${store.tagline || "Boutique"}`}</title>
        <meta name="description" content={store.tagline || `${name}, boutique en ligne.`} />
        <meta property="og:title" content={name} />
        <meta property="og:description" content={store.tagline || ""} />
        <meta property="og:type" content="website" />
        {data.products?.[0]?.images?.[0] && <meta property="og:image" content={data.products[0].images[0]} />}
      </Helmet>

      {/* Bandeau */}
      <div className="text-center text-[13px] py-2 font-medium tracking-wide" style={{ backgroundColor: accent, color: "#fff" }} data-testid="store-announcement">
        Livraison offerte dès 50€ · Paiement 100% sécurisé
      </div>

      {/* Header */}
      <header className="sticky top-0 z-40 bg-cream/90 backdrop-blur border-b border-ink/10">
        <div className="max-w-[1400px] mx-auto px-5 md:px-10 h-16 flex items-center justify-between">
          <Link to={`/b/${slug}`} className="flex items-center gap-2" data-testid="store-logo">
            <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: accent }} />
            <span className="font-display font-black text-xl uppercase tracking-tight">{name}</span>
          </Link>
          <nav className="flex items-center gap-5 text-sm">
            <a href="#produits" className="hidden sm:inline hover:opacity-70 transition-opacity">Produits</a>
            {cats.map((c) => (
              <button key={c} onClick={() => { setCat(c); document.getElementById("produits")?.scrollIntoView({ behavior: "smooth" }); }} className="hidden md:inline text-stone hover:text-ink transition-colors">
                {CAT_LABELS[c] || c}
              </button>
            ))}
            <button onClick={() => navigate("/cart")} className="relative p-2" data-testid="store-cart-btn" aria-label="panier">
              <ShoppingBag className="w-5 h-5" />
              {count > 0 && <span className="absolute -top-0.5 -right-0.5 text-white text-[10px] font-bold w-4 h-4 rounded-full flex items-center justify-center" style={{ backgroundColor: accent }}>{count}</span>}
            </button>
          </nav>
        </div>
      </header>

      {/* Hero */}
      <section className="relative overflow-hidden border-b border-ink/10">
        <div className="max-w-[1400px] mx-auto px-5 md:px-10 py-20 md:py-28">
          <motion.p initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}
            className="text-xs md:text-sm font-bold uppercase tracking-[0.25em] mb-5" style={{ color: accent }}>
            {store.tagline || "Sélection premium"}
          </motion.p>
          <motion.h1 initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6, delay: 0.05 }}
            className="font-display font-black uppercase tracking-tighter leading-[0.9] text-5xl sm:text-6xl lg:text-8xl max-w-4xl">
            {name}
          </motion.h1>
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.6, delay: 0.15 }} className="mt-8 flex flex-wrap items-center gap-4">
            <a href="#produits" className="inline-flex items-center gap-2 text-cream px-7 py-3.5 rounded-full font-medium transition-transform hover:-translate-y-0.5" style={{ backgroundColor: accent }} data-testid="store-hero-cta">
              Découvrir la sélection <ArrowRight className="w-4 h-4" />
            </a>
            <span className="text-stone text-sm">{data.count} produit{data.count > 1 ? "s" : ""} disponibles</span>
          </motion.div>
        </div>
        <div className="absolute -right-24 -bottom-24 w-72 h-72 rounded-full opacity-10 blur-2xl pointer-events-none" style={{ backgroundColor: accent }} />
      </section>

      {/* Catégories */}
      {cats.length > 1 && (
        <div className="max-w-[1400px] mx-auto px-5 md:px-10 pt-10 flex flex-wrap gap-2" data-testid="store-cats">
          <button onClick={() => setCat("all")} className={`px-4 py-2 rounded-full text-sm border transition-colors ${cat === "all" ? "text-cream border-transparent" : "border-ink/20 text-stone hover:border-ink"}`} style={cat === "all" ? { backgroundColor: accent } : {}} data-testid="store-cat-all">
            Tout
          </button>
          {cats.map((c) => (
            <button key={c} onClick={() => setCat(c)} className={`px-4 py-2 rounded-full text-sm border transition-colors ${cat === c ? "text-cream border-transparent" : "border-ink/20 text-stone hover:border-ink"}`} style={cat === c ? { backgroundColor: accent } : {}} data-testid={`store-cat-${c}`}>
              {CAT_LABELS[c] || c}
            </button>
          ))}
        </div>
      )}

      {/* Grille produits */}
      <section id="produits" className="max-w-[1400px] mx-auto px-5 md:px-10 py-14">
        {products.length === 0 ? (
          <p className="text-stone py-20 text-center" data-testid="store-empty">Aucun produit dans cette sélection pour le moment.</p>
        ) : (
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-x-6 gap-y-4">
            {products.map((p) => <ThemedCard key={p.id} product={p} accent={accent} lang={lang} />)}
          </div>
        )}
      </section>

      {/* Footer */}
      <footer className="border-t border-ink/10 py-10">
        <div className="max-w-[1400px] mx-auto px-5 md:px-10 flex flex-col sm:flex-row items-center justify-between gap-4 text-sm text-stone">
          <p className="font-display font-bold text-ink uppercase tracking-tight">{name}</p>
          <a href="https://invovix.store" target="_blank" rel="noreferrer" className="inline-flex items-center gap-1.5 hover:text-ink transition-colors" data-testid="store-powered-by">
            Propulsé par Invovix <ExternalLink className="w-3.5 h-3.5" />
          </a>
        </div>
      </footer>
    </div>
  );
}
