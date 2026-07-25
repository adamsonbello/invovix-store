import React, { createContext, useContext, useEffect, useState, useCallback } from "react";
import api from "@/lib/api";
import { useAuth } from "@/context/AuthContext";

const WishlistContext = createContext(null);

export function WishlistProvider({ children }) {
  const { user } = useAuth();
  const [ids, setIds] = useState([]);

  const refresh = useCallback(() => {
    if (!user) {
      setIds([]);
      return;
    }
    api.get("/wishlist").then((r) => setIds(r.data.product_ids || [])).catch(() => {});
  }, [user]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const toggle = async (productId) => {
    const r = await api.post(`/wishlist/${productId}`);
    setIds(r.data.product_ids || []);
    return r.data.added;
  };

  const has = (id) => ids.includes(id);

  return (
    <WishlistContext.Provider value={{ ids, toggle, has, refresh, count: ids.length }}>
      {children}
    </WishlistContext.Provider>
  );
}

export function useWishlist() {
  return useContext(WishlistContext);
}
