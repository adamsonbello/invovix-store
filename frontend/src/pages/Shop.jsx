import React, { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Search } from "lucide-react";
import { useI18n } from "@/i18n";
import api from "@/lib/api";
import ProductCard from "@/components/ProductCard";

export default function Shop() {
  const { t } = useI18n();
  const [searchParams, setSearchParams] = useSearchParams();
  const category = searchParams.get("category") || "";
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [q, setQ] = useState("");

  const cats = [
    { key: "", label: t.shop.filterAll },
    { key: "smart-home", label: t.nav.smartHome },
    { key: "workspace", label: t.nav.workspace },
    { key: "security", label: t.nav.security },
  ];

  useEffect(() => {
    setLoading(true);
    const params = new URLSearchParams();
    if (category) params.set("category", category);
    if (q) params.set("q", q);
    api
      .get(`/products?${params.toString()}`)
      .then((r) => setProducts(r.data.items))
      .finally(() => setLoading(false));
  }, [category, q]);

  const setCategory = (key) => {
    if (key) setSearchParams({ category: key });
    else setSearchParams({});
  };

  return (
    <div className="pt-28 md:pt-36" data-testid="shop-page">
      <div className="max-w-[1600px] mx-auto px-5 md:px-10">
        <div className="border-b border-ink/10 pb-10 mb-10">
          <h1 className="font-display font-black uppercase tracking-tighter leading-[0.9] text-6xl md:text-8xl">
            {t.shop.title}
          </h1>
          <p className="text-ink/60 text-lg mt-4 max-w-lg">{t.shop.sub}</p>
        </div>

        <div className="flex flex-col md:flex-row justify-between gap-6 mb-12">
          <div className="flex flex-wrap gap-2">
            {cats.map((c) => (
              <button
                key={c.key || "all"}
                onClick={() => setCategory(c.key)}
                className={`px-5 py-2.5 rounded-full text-sm font-medium border transition-colors ${
                  category === c.key
                    ? "bg-ink text-cream border-ink"
                    : "border-ink/20 hover:border-ink"
                }`}
                data-testid={`filter-${c.key || "all"}`}
              >
                {c.label}
              </button>
            ))}
          </div>
          <div className="relative md:w-72">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-stone" />
            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder={t.shop.search}
              className="w-full pl-11 pr-4 py-2.5 rounded-full border border-ink/20 bg-transparent outline-none focus:border-ink transition-colors"
              data-testid="shop-search"
            />
          </div>
        </div>

        {loading ? (
          <div className="py-32 text-center text-stone">{t.common.loading}</div>
        ) : products.length === 0 ? (
          <div className="py-32 text-center text-stone" data-testid="shop-empty">{t.shop.empty}</div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-x-6 gap-y-2 pb-32">
            {products.map((p, i) => (
              <ProductCard key={p.id} product={p} index={i} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
