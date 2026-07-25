import React, { useEffect, useState } from "react";
import { useI18n } from "@/i18n";
import api from "@/lib/api";
import ProductCard from "@/components/ProductCard";

export default function RelatedProducts({ productId }) {
  const { t } = useI18n();
  const [items, setItems] = useState([]);

  useEffect(() => {
    if (!productId) return;
    api.get(`/products/${productId}/related`).then((r) => setItems(r.data.items)).catch(() => {});
  }, [productId]);

  if (items.length === 0) return null;

  return (
    <section className="mt-24 md:mt-32 border-t border-ink/10 pt-14" data-testid="related-products">
      <h2 className="font-display font-black uppercase tracking-tighter text-3xl md:text-5xl mb-10">{t.related.title}</h2>
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-x-6 gap-y-2">
        {items.map((p, i) => (
          <ProductCard key={p.id} product={p} index={i} />
        ))}
      </div>
    </section>
  );
}
