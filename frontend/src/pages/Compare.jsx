import React, { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { X, Check, Minus, ShoppingBag, GitCompare } from "lucide-react";
import api from "@/lib/api";
import { useI18n } from "@/i18n";
import { useCompare } from "@/context/CompareContext";
import { useCart } from "@/context/CartContext";
import SEO from "@/components/SEO";
import { Stars } from "@/components/StarRating";
import { toast } from "sonner";

export default function Compare() {
  const { lang } = useI18n();
  const { ids, remove, clear } = useCompare();
  const { add } = useCart();
  const navigate = useNavigate();
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    setLoading(true);
    Promise.all(ids.map((id) => api.get(`/products/${id}`).then((r) => r.data).catch(() => null)))
      .then((res) => { if (alive) setProducts(res.filter(Boolean)); })
      .finally(() => alive && setLoading(false));
    return () => { alive = false; };
  }, [ids]);

  const title = (p) => (lang === "en" ? p.title_en || p.title : p.title);

  const specKeys = Array.from(
    products.reduce((set, p) => {
      Object.keys(p.specs || {}).forEach((k) => set.add(k));
      return set;
    }, new Set())
  );

  const rows = [
    { label: "Prix", render: (p) => <span className="font-display font-bold text-lg">{p.price?.toFixed(2)}€</span> },
    { label: "Prix barré", render: (p) => (p.compare_at_price > p.price ? <span className="text-stone line-through">{p.compare_at_price.toFixed(2)}€</span> : <Minus className="w-4 h-4 text-stone/40" />) },
    { label: "Catégorie", render: (p) => <span className="capitalize">{p.category}</span> },
    { label: "Marque", render: (p) => p.brand || <Minus className="w-4 h-4 text-stone/40" /> },
    { label: "Note", render: (p) => (p.rating_count > 0 ? <span className="inline-flex items-center gap-1"><Stars value={p.rating_avg} size={14} /> <span className="text-sm text-stone">({p.rating_count})</span></span> : <span className="text-sm text-stone">Aucun avis</span>) },
    { label: "Disponibilité", render: (p) => (p.in_stock === false ? <span className="text-brand font-medium">Épuisé</span> : <span className="text-emerald-700 inline-flex items-center gap-1"><Check className="w-4 h-4" /> En stock</span>) },
    { label: "Livraison", render: (p) => (p.price >= 50 ? "Offerte" : "4,90€") },
  ];

  return (
    <div className="pt-28 md:pt-32 pb-32 max-w-[1400px] mx-auto px-5 md:px-10" data-testid="compare-page">
      <SEO title="Comparateur de produits" path="/compare" />
      <div className="flex items-center justify-between mb-10">
        <h1 className="font-display font-black uppercase tracking-tighter text-4xl md:text-6xl flex items-center gap-3">
          <GitCompare className="w-8 h-8 md:w-10 md:h-10 text-brand" /> Comparateur
        </h1>
        {products.length > 0 && <button onClick={clear} className="text-sm text-stone hover:text-brand transition-colors" data-testid="compare-clear-all">Tout retirer</button>}
      </div>

      {loading ? (
        <p className="text-stone py-20 text-center">Chargement…</p>
      ) : products.length === 0 ? (
        <div className="py-20 text-center" data-testid="compare-empty">
          <p className="text-stone mb-6">Aucun produit à comparer. Ajoutez-en 2 à 4 depuis la boutique (icône comparateur).</p>
          <Link to="/shop" className="inline-flex items-center gap-2 bg-ink text-cream px-6 py-3 rounded-full font-medium hover:bg-brand transition-colors">Aller à la boutique</Link>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full border-collapse table-fixed min-w-[640px]">
            <thead>
              <tr>
                <th className="w-28 md:w-40" />
                {products.map((p) => (
                  <th key={p.id} className="p-3 align-top text-left" data-testid={`compare-col-${p.id}`}>
                    <div className="relative">
                      <button onClick={() => remove(p.id)} className="absolute -top-1 -right-1 z-10 bg-cream border border-ink/15 rounded-full p-1 hover:text-brand" data-testid={`compare-remove-${p.id}`}><X className="w-3.5 h-3.5" /></button>
                      <Link to={`/product/${p.id}`}>
                        <div className="aspect-square bg-[#f0efed] overflow-hidden mb-3">
                          <img src={p.images?.[0]} alt={title(p)} className="w-full h-full object-cover" />
                        </div>
                        <p className="font-display font-bold leading-tight text-sm md:text-base hover:text-brand transition-colors">{title(p)}</p>
                      </Link>
                    </div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.label} className="border-t border-ink/10">
                  <td className="py-4 pr-3 text-xs uppercase tracking-wide font-bold text-stone align-middle">{row.label}</td>
                  {products.map((p) => (
                    <td key={p.id} className="py-4 px-3 align-middle">{row.render(p)}</td>
                  ))}
                </tr>
              ))}
              {specKeys.length > 0 && (
                <tr className="border-t-2 border-ink/20" data-testid="compare-specs-section">
                  <td className="py-3 pr-3 text-xs uppercase tracking-widest font-black text-ink" colSpan={products.length + 1}>Caractéristiques techniques</td>
                </tr>
              )}
              {specKeys.map((key) => (
                <tr key={`spec-${key}`} className="border-t border-ink/10">
                  <td className="py-4 pr-3 text-xs uppercase tracking-wide font-bold text-stone align-middle">{key}</td>
                  {products.map((p) => (
                    <td key={p.id} className="py-4 px-3 align-middle text-sm" data-testid={`spec-${key}-${p.id}`}>
                      {(p.specs && p.specs[key]) || <Minus className="w-4 h-4 text-stone/40" />}
                    </td>
                  ))}
                </tr>
              ))}
              <tr className="border-t border-ink/10">
                <td />
                {products.map((p) => (
                  <td key={p.id} className="py-4 px-3">
                    <button
                      onClick={() => { if (p.in_stock === false) return; add(p, 1); toast.success("Ajouté au panier"); }}
                      disabled={p.in_stock === false}
                      className="inline-flex items-center gap-2 bg-ink text-cream text-sm px-4 py-2.5 rounded-full hover:bg-brand transition-colors disabled:opacity-40"
                      data-testid={`compare-add-${p.id}`}
                    >
                      <ShoppingBag className="w-4 h-4" /> Ajouter
                    </button>
                  </td>
                ))}
              </tr>
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
