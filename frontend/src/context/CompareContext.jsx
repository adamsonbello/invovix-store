import React, { createContext, useContext, useEffect, useState } from "react";
import { toast } from "sonner";

const CompareContext = createContext();
const MAX = 4;
const KEY = "invovix_compare_v2";

export function CompareProvider({ children }) {
  const [items, setItems] = useState(() => {
    try {
      const raw = JSON.parse(localStorage.getItem(KEY));
      return Array.isArray(raw) ? raw.filter((x) => x && x.id) : [];
    } catch {
      return [];
    }
  });

  useEffect(() => {
    localStorage.setItem(KEY, JSON.stringify(items));
  }, [items]);

  const ids = items.map((x) => x.id);
  const has = (id) => ids.includes(id);

  const toggle = (product) => {
    const id = typeof product === "string" ? product : product.id;
    const category = typeof product === "string" ? null : product.category;
    setItems((prev) => {
      if (prev.some((x) => x.id === id)) return prev.filter((x) => x.id !== id);
      if (prev.length >= MAX) {
        toast.error(`Comparez ${MAX} produits maximum`);
        return prev;
      }
      if (prev.length > 0 && category && prev[0].category && prev[0].category !== category) {
        toast.error("Comparez uniquement des produits de la même catégorie");
        return prev;
      }
      return [...prev, { id, category: category || null }];
    });
  };

  const remove = (id) => setItems((prev) => prev.filter((x) => x.id !== id));
  const clear = () => setItems([]);

  return (
    <CompareContext.Provider value={{ ids, items, has, toggle, remove, clear, count: items.length, max: MAX }}>
      {children}
    </CompareContext.Provider>
  );
}

export function useCompare() {
  return useContext(CompareContext);
}
