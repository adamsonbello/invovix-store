import React, { useEffect } from "react";
import { Outlet, useLocation } from "react-router-dom";
import Lenis from "lenis";
import Header from "@/components/Header";
import Footer from "@/components/Footer";

export default function Layout() {
  const location = useLocation();

  useEffect(() => {
    const lenis = new Lenis({ duration: 1.1, smoothWheel: true });
    let raf;
    function loop(time) {
      lenis.raf(time);
      raf = requestAnimationFrame(loop);
    }
    raf = requestAnimationFrame(loop);
    return () => {
      cancelAnimationFrame(raf);
      lenis.destroy();
    };
  }, []);

  useEffect(() => {
    window.scrollTo(0, 0);
  }, [location.pathname]);

  return (
    <div className="min-h-screen bg-cream text-ink flex flex-col">
      <Header />
      <main className="flex-1">
        <Outlet />
      </main>
      <Footer />
    </div>
  );
}
