import React, { createContext, useContext, useEffect, useState } from "react";

const CartContext = createContext(null);

export function CartProvider({ children }) {
  const [items, setItems] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem("invovix_cart")) || [];
    } catch {
      return [];
    }
  });

  useEffect(() => {
    localStorage.setItem("invovix_cart", JSON.stringify(items));
  }, [items]);

  const add = (product, quantity = 1) => {
    setItems((prev) => {
      const existing = prev.find((i) => i.product_id === product.id);
      if (existing) {
        return prev.map((i) =>
          i.product_id === product.id ? { ...i, quantity: i.quantity + quantity } : i
        );
      }
      return [
        ...prev,
        {
          product_id: product.id,
          title: product.title,
          title_en: product.title_en,
          price: product.price,
          image: (product.images || [])[0],
          quantity,
        },
      ];
    });
  };

  const updateQty = (productId, quantity) => {
    if (quantity < 1) return remove(productId);
    setItems((prev) => prev.map((i) => (i.product_id === productId ? { ...i, quantity } : i)));
  };

  const remove = (productId) => setItems((prev) => prev.filter((i) => i.product_id !== productId));
  const clear = () => setItems([]);

  const count = items.reduce((s, i) => s + i.quantity, 0);
  const subtotal = items.reduce((s, i) => s + i.price * i.quantity, 0);

  return (
    <CartContext.Provider value={{ items, add, updateQty, remove, clear, count, subtotal }}>
      {children}
    </CartContext.Provider>
  );
}

export function useCart() {
  return useContext(CartContext);
}
