import React, { createContext, useContext, useEffect, useState } from "react";
import { toast } from "sonner";

const CompareContext = createContext();
const MAX = 4;
const KEY = "invovix_compare";

export function CompareProvider({ children }) {
  const [ids, setIds] = useState(() => {
    try { return JSON.parse(localStorage.getItem(KEY)) || []; } catch { return []; }
  });

  useEffect(() => { localStorage.setItem(KEY, JSON.stringify(ids)); }, [ids]);

  const has = (id) => ids.includes(id);
  const toggle = (id) => {
    setIds((prev) => {
      if (prev.includes(id)) return prev.filter((x) => x !== id);
      if (prev.length >= MAX) { toast.error(`Comparez ${MAX} produits maximum`); return prev; }
      return [...prev, id];
    });
  };
  const remove = (id) => setIds((prev) => prev.filter((x) => x !== id));
  const clear = () => setIds([]);

  return (
    <CompareContext.Provider value={{ ids, has, toggle, remove, clear, count: ids.length, max: MAX }}>
      {children}
    </CompareContext.Provider>
  );
}

export function useCompare() {
  return useContext(CompareContext);
}
