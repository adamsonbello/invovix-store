import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { motion, useScroll, useTransform } from "framer-motion";
import Marquee from "react-fast-marquee";
import { ArrowUpRight, ArrowRight, ShieldCheck, Truck, Headphones, RefreshCw } from "lucide-react";
import { useI18n } from "@/i18n";
import api from "@/lib/api";
import ProductCard from "@/components/ProductCard";
import SEO from "@/components/SEO";

const ease = [0.22, 1, 0.36, 1];

function MaskLine({ children, delay = 0 }) {
  return (
    <span className="line-mask">
      <motion.span
        className="block"
        initial={{ y: "110%" }}
        animate={{ y: 0 }}
        transition={{ duration: 0.9, delay, ease }}
      >
        {children}
      </motion.span>
    </span>
  );
}

function Hero() {
  const { t } = useI18n();
  const { scrollY } = useScroll();
  const y = useTransform(scrollY, [0, 600], [0, 140]);
  const scale = useTransform(scrollY, [0, 600], [1, 1.12]);

  return (
    <section className="relative min-h-screen flex flex-col justify-end overflow-hidden" data-testid="hero">
      <motion.div style={{ y, scale }} className="absolute inset-0 z-0">
        <img
          src="https://images.unsplash.com/photo-1499951360447-b19be8fe80f5?crop=entropy&cs=srgb&fm=jpg&q=85&w=2000"
          alt="Invovix smart workspace"
          className="w-full h-[115%] object-cover"
        />
        <div className="absolute inset-0 bg-gradient-to-t from-cream via-cream/20 to-black/20" />
      </motion.div>

      <div className="relative z-10 max-w-[1600px] w-full mx-auto px-5 md:px-10 pb-16 md:pb-24 pt-32">
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.2, duration: 0.8 }}
          className="text-xs md:text-sm tracking-[0.25em] uppercase font-bold text-brand mb-6"
        >
          {t.hero.overline}
        </motion.p>

        <h1 className="font-display font-black uppercase tracking-tighter leading-[0.85] text-[15vw] md:text-[10vw] lg:text-[8.5vw]">
          <MaskLine delay={0.15}>{t.hero.l1}</MaskLine>
          <MaskLine delay={0.28}>{t.hero.l2}</MaskLine>
          <MaskLine delay={0.41}>
            <span className="text-brand">{t.hero.l3}</span>
          </MaskLine>
        </h1>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.8, duration: 0.7 }}
          className="mt-8 flex flex-col md:flex-row md:items-end justify-between gap-8"
        >
          <p className="max-w-md text-base md:text-lg text-ink/70 leading-relaxed">{t.hero.sub}</p>
          <div className="flex items-center gap-4">
            <Link
              to="/shop"
              className="group inline-flex items-center gap-2 bg-ink text-cream px-7 py-4 rounded-full font-medium hover:bg-brand transition-colors"
              data-testid="hero-shop-cta"
            >
              {t.hero.cta}
              <ArrowUpRight className="w-5 h-5 group-hover:rotate-45 transition-transform" />
            </Link>
            <a href="#manifesto" className="hidden md:inline-flex items-center gap-2 font-medium hover:text-brand transition-colors">
              {t.hero.cta2}
              <ArrowRight className="w-4 h-4" />
            </a>
          </div>
        </motion.div>
      </div>
    </section>
  );
}

function MarqueeBar() {
  const { t } = useI18n();
  return (
    <div className="bg-brand text-white py-4 border-y border-brand overflow-hidden" data-testid="marquee">
      <Marquee speed={45} gradient={false}>
        {t.marquee.concat(t.marquee).map((m, i) => (
          <span key={i} className="font-display font-bold uppercase tracking-tight text-2xl md:text-4xl mx-8 flex items-center gap-8">
            {m} <span className="w-2 h-2 bg-white rounded-full" />
          </span>
        ))}
      </Marquee>
    </div>
  );
}

function Featured() {
  const { t } = useI18n();
  const [products, setProducts] = useState([]);
  useEffect(() => {
    api.get("/products?featured=true").then((r) => setProducts(r.data.items)).catch(() => {});
  }, []);

  return (
    <section className="max-w-[1600px] mx-auto px-5 md:px-10 py-24 md:py-36" data-testid="featured">
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 mb-14">
        <div>
          <p className="text-xs tracking-[0.25em] uppercase font-bold text-brand mb-4">{t.featured.overline}</p>
          <h2 className="font-display font-black uppercase tracking-tighter leading-[0.9] text-5xl md:text-7xl max-w-2xl">
            {t.featured.title}
          </h2>
        </div>
        <p className="text-ink/60 max-w-xs md:text-right">{t.featured.sub}</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-x-6 gap-y-2">
        {products.map((p, i) => (
          <ProductCard key={p.id} product={p} index={i} />
        ))}
      </div>

      <div className="mt-14 flex justify-center">
        <Link
          to="/shop"
          className="group inline-flex items-center gap-3 border border-ink/20 rounded-full px-8 py-4 font-medium hover:bg-ink hover:text-cream transition-colors"
          data-testid="featured-all"
        >
          {t.featured.all}
          <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
        </Link>
      </div>
    </section>
  );
}

function Categories() {
  const { t } = useI18n();
  const cats = [
    { key: "smart-home", label: t.categories.smartHome, desc: t.categories.smartHomeD, img: "/products/switch.jpg", span: "md:col-span-7" },
    { key: "workspace", label: t.categories.workspace, desc: t.categories.workspaceD, img: "/products/workstation.jpg", span: "md:col-span-5" },
    { key: "security", label: t.categories.security, desc: t.categories.securityD, img: "/products/camera360.jpg", span: "md:col-span-12" },
  ];
  return (
    <section className="max-w-[1600px] mx-auto px-5 md:px-10 pb-24 md:pb-36" data-testid="categories">
      <div className="mb-14">
        <p className="text-xs tracking-[0.25em] uppercase font-bold text-brand mb-4">{t.categories.overline}</p>
        <h2 className="font-display font-black uppercase tracking-tighter leading-[0.9] text-5xl md:text-7xl">
          {t.categories.title}
        </h2>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-12 gap-6">
        {cats.map((c, i) => (
          <motion.div
            key={c.key}
            initial={{ opacity: 0, y: 40 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.7, delay: i * 0.1, ease }}
            className={c.span}
          >
            <Link
              to={`/shop?category=${c.key}`}
              className="group relative block overflow-hidden aspect-[16/10] md:aspect-auto md:h-[380px]"
              data-testid={`category-${c.key}`}
            >
              <img src={c.img} alt={c.label} className="absolute inset-0 w-full h-full object-cover hover-lift group-hover:scale-105" />
              <div className="absolute inset-0 bg-gradient-to-t from-ink/80 via-ink/10 to-transparent" />
              <div className="absolute bottom-0 left-0 p-8 text-cream">
                <div className="flex items-center gap-3">
                  <h3 className="font-display font-black uppercase tracking-tight text-3xl md:text-4xl">{c.label}</h3>
                  <ArrowUpRight className="w-7 h-7 group-hover:rotate-45 transition-transform" />
                </div>
                <p className="text-white/70 mt-2">{c.desc}</p>
              </div>
            </Link>
          </motion.div>
        ))}
      </div>
    </section>
  );
}

function Manifesto() {
  const { t } = useI18n();
  const chapters = [
    { n: "01", title: t.manifesto.c1t, desc: t.manifesto.c1d },
    { n: "02", title: t.manifesto.c2t, desc: t.manifesto.c2d },
    { n: "03", title: t.manifesto.c3t, desc: t.manifesto.c3d },
  ];
  return (
    <section id="manifesto" className="relative bg-ink text-cream grain overflow-hidden" data-testid="manifesto">
      <div className="relative z-10 max-w-[1600px] mx-auto px-5 md:px-10 py-24 md:py-40">
        <p className="text-xs tracking-[0.25em] uppercase font-bold text-brand mb-16">{t.manifesto.overline}</p>
        <div className="space-y-2">
          {chapters.map((c, i) => (
            <motion.div
              key={c.n}
              initial={{ opacity: 0, y: 60 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-80px" }}
              transition={{ duration: 0.8, ease }}
              className="grid grid-cols-1 md:grid-cols-12 gap-6 py-10 md:py-14 border-t border-white/15"
            >
              <div className="md:col-span-2">
                <span className="font-display font-black text-5xl md:text-6xl text-brand">{c.n}</span>
              </div>
              <h3 className="md:col-span-5 font-display font-black uppercase tracking-tighter leading-[0.92] text-4xl md:text-6xl">
                {c.title}
              </h3>
              <p className="md:col-span-4 md:col-start-9 text-white/60 text-lg leading-relaxed self-end">{c.desc}</p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}

function Trust() {
  const { t } = useI18n();
  const items = [
    { icon: Truck, title: t.trust.free, desc: t.trust.freeD },
    { icon: ShieldCheck, title: t.trust.secure, desc: t.trust.secureD },
    { icon: Headphones, title: t.trust.support, desc: t.trust.supportD },
    { icon: RefreshCw, title: t.trust.returns, desc: t.trust.returnsD },
  ];
  return (
    <section className="max-w-[1600px] mx-auto px-5 md:px-10 py-20" data-testid="trust">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-px bg-ink/10 border border-ink/10">
        {items.map((it) => (
          <div key={it.title} className="bg-cream p-8">
            <it.icon className="w-7 h-7 text-brand mb-4" strokeWidth={1.5} />
            <h4 className="font-display font-bold text-lg tracking-tight">{it.title}</h4>
            <p className="text-stone text-sm mt-1">{it.desc}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

function CtaBand() {
  const { t } = useI18n();
  return (
    <section className="max-w-[1600px] mx-auto px-5 md:px-10 pb-24 md:pb-32" data-testid="cta-band">
      <div className="relative overflow-hidden bg-brand text-white rounded-none px-8 md:px-20 py-20 md:py-28 text-center">
        <h2 className="font-display font-black uppercase tracking-tighter leading-[0.9] text-4xl md:text-7xl max-w-4xl mx-auto">
          {t.cta.title}
        </h2>
        <p className="mt-6 text-white/80 text-lg max-w-xl mx-auto">{t.cta.sub}</p>
        <Link
          to="/shop"
          className="mt-10 inline-flex items-center gap-2 bg-white text-ink px-8 py-4 rounded-full font-medium hover:bg-ink hover:text-white transition-colors"
          data-testid="cta-band-btn"
        >
          {t.cta.btn}
          <ArrowUpRight className="w-5 h-5" />
        </Link>
      </div>
    </section>
  );
}

export default function Home() {
  return (
    <div data-testid="home-page">
      <SEO
        path="/"
        jsonLd={{
          "@context": "https://schema.org",
          "@type": "Organization",
          name: "Invovix",
          url: "https://invovix.store",
          description: "Domotique premium et matériel de télétravail, livrés dans toute la zone euro.",
        }}
      />
      <Hero />
      <MarqueeBar />
      <Featured />
      <Categories />
      <Manifesto />
      <Trust />
      <CtaBand />
    </div>
  );
}
