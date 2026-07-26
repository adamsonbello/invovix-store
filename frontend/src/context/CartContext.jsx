import React, { createContext, useContext, useEffect, useState } from "react";

const CartContext = createContext(null);

export function CartProvider({ children }) {
  const [items, setItems] = useState(() => {
    try {
      const raw = JSON.parse(localStorage.getItem("invovix_cart")) || [];
      return raw.map((i) => ({ ...i, key: i.key || `${i.product_id}::${i.variant_id || ""}` }));
    } catch {
      return [];
    }
  });

  useEffect(() => {
    localStorage.setItem("invovix_cart", JSON.stringify(items));
  }, [items]);

  const [promo, setPromo] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem("invovix_promo")) || null;
    } catch {
      return null;
    }
  });

  useEffect(() => {
    localStorage.setItem("invovix_promo", JSON.stringify(promo));
  }, [promo]);

  const applyPromo = (p) => setPromo(p);
  const removePromo = () => setPromo(null);

  const add = (product, quantity = 1, variant = null) => {
    const vid = variant?.vid || "";
    const unitPrice = variant?.price ?? product.price;
    const image = variant?.image || (product.images || [])[0];
    const key = `${product.id}::${vid}`;
    setItems((prev) => {
      const existing = prev.find((i) => i.key === key);
      if (existing) {
        return prev.map((i) => (i.key === key ? { ...i, quantity: i.quantity + quantity } : i));
      }
      return [
        ...prev,
        {
          key,
          product_id: product.id,
          variant_id: vid,
          variant_name: variant && variant.name ? variant.name : "",
          title: product.title,
          title_en: product.title_en,
          price: unitPrice,
          image,
          quantity,
        },
      ];
    });
  };

  const updateQty = (key, quantity) => {
    if (quantity < 1) return remove(key);
    setItems((prev) => prev.map((i) => (i.key === key ? { ...i, quantity } : i)));
  };

  const remove = (key) => setItems((prev) => prev.filter((i) => i.key !== key));
  const clear = () => { setItems([]); setPromo(null); };

  const count = items.reduce((s, i) => s + i.quantity, 0);
  const subtotal = items.reduce((s, i) => s + i.price * i.quantity, 0);

  let discount = 0;
  if (promo && subtotal >= (promo.min_subtotal || 0)) {
    discount = promo.type === "percent"
      ? Number((subtotal * promo.value / 100).toFixed(2))
      : Math.min(Number(promo.value), subtotal);
  }
  const validPromo = discount > 0 ? promo : null;

  return (
    <CartContext.Provider value={{ items, add, updateQty, remove, clear, count, subtotal, promo: validPromo, applyPromo, removePromo, discount }}>
      {children}
    </CartContext.Provider>
  );
}

export function useCart() {
  return useContext(CartContext);
}
