import "@/App.css";
import { useState, useEffect } from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { HelmetProvider } from "react-helmet-async";
import { LanguageProvider } from "@/i18n";
import { AuthProvider } from "@/context/AuthContext";
import { CartProvider } from "@/context/CartContext";
import { WishlistProvider } from "@/context/WishlistContext";
import { Toaster } from "@/components/ui/sonner";
import api from "@/lib/api";
import Layout from "@/components/Layout";
import ProtectedRoute from "@/components/ProtectedRoute";
import Home from "@/pages/Home";
import Shop from "@/pages/Shop";
import ProductDetail from "@/pages/ProductDetail";
import Cart from "@/pages/Cart";
import Checkout from "@/pages/Checkout";
import PaymentSuccess from "@/pages/PaymentSuccess";
import PaymentCancel from "@/pages/PaymentCancel";
import Login from "@/pages/Login";
import Register from "@/pages/Register";
import Account from "@/pages/Account";
import Admin from "@/pages/Admin";
import Contact from "@/pages/Contact";
import Blog from "@/pages/Blog";
import BlogPost from "@/pages/BlogPost";
import FAQ from "@/pages/FAQ";
import Wishlist from "@/pages/Wishlist";
import Legal from "@/pages/Legal";
import PublicStore from "@/pages/PublicStore";

function AppRoutes() {
  return (
    <Routes>
      <Route path="/b/:slug" element={<PublicStore />} />
      <Route element={<Layout />}>
        <Route path="/" element={<Home />} />
        <Route path="/shop" element={<Shop />} />
        <Route path="/product/:id" element={<ProductDetail />} />
        <Route path="/cart" element={<Cart />} />
        <Route path="/checkout" element={<Checkout />} />
        <Route path="/payment/success" element={<PaymentSuccess />} />
        <Route path="/payment/cancel" element={<PaymentCancel />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/contact" element={<Contact />} />
        <Route path="/blog" element={<Blog />} />
        <Route path="/blog/:slug" element={<BlogPost />} />
        <Route path="/faq" element={<FAQ />} />
        <Route path="/legal/:doc" element={<Legal />} />
        <Route path="/wishlist" element={<ProtectedRoute><Wishlist /></ProtectedRoute>} />
        <Route path="/account" element={<ProtectedRoute><Account /></ProtectedRoute>} />
        <Route path="/admin" element={<ProtectedRoute adminOnly><Admin /></ProtectedRoute>} />
      </Route>
    </Routes>
  );
}

// Rend une vitrine de boutique dédiée quand le domaine visité correspond à une boutique.
function DomainGate() {
  const [state, setState] = useState(() => {
    const host = window.location.hostname.toLowerCase();
    const primary =
      host === "invovix.store" || host === "www.invovix.store" ||
      host === "localhost" || host === "127.0.0.1" ||
      host.includes("emergent") || host.includes("preview");
    return { resolved: primary, slug: null };
  });

  useEffect(() => {
    if (state.resolved) return;
    const host = window.location.hostname.toLowerCase();
    api
      .get("/public/store-resolve", { params: { host } })
      .then((r) => setState({ resolved: true, slug: r.data.slug }))
      .catch(() => setState({ resolved: true, slug: null }));
  }, []); // eslint-disable-line

  if (!state.resolved) return null;
  if (state.slug && window.location.pathname === "/") return <PublicStore slug={state.slug} />;
  return <AppRoutes />;
}

function App() {
  return (
    <div className="App">
      <HelmetProvider>
        <LanguageProvider>
        <AuthProvider>
          <CartProvider>
            <WishlistProvider>
            <BrowserRouter>
              <DomainGate />
            </BrowserRouter>
            </WishlistProvider>
            <Toaster position="bottom-right" />
          </CartProvider>
        </AuthProvider>
      </LanguageProvider>
      </HelmetProvider>
    </div>
  );
}

export default App;
