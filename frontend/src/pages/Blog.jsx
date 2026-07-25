import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowUpRight } from "lucide-react";
import { useI18n } from "@/i18n";
import api from "@/lib/api";
import SEO from "@/components/SEO";

export default function Blog() {
  const { t, lang } = useI18n();
  const [posts, setPosts] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get("/blog").then((r) => setPosts(r.data.items)).finally(() => setLoading(false));
  }, []);

  return (
    <div className="pt-28 md:pt-36 pb-32" data-testid="blog-page">
      <SEO title={t.blog.title} description={t.blog.sub} path="/blog" />
      <div className="max-w-[1400px] mx-auto px-5 md:px-10">
        <h1 className="font-display font-black uppercase tracking-tighter text-6xl md:text-8xl">{t.blog.title}</h1>
        <p className="text-ink/60 text-lg mt-4 max-w-lg">{t.blog.sub}</p>

        {loading ? (
          <p className="text-stone py-20">{t.common.loading}</p>
        ) : posts.length === 0 ? (
          <p className="text-stone py-20" data-testid="blog-empty">{t.blog.empty}</p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-x-8 gap-y-12 mt-16">
            {posts.map((p, i) => (
              <motion.article
                key={p.id}
                initial={{ opacity: 0, y: 30 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, delay: (i % 3) * 0.08 }}
                data-testid={`blog-card-${p.slug}`}
              >
                <Link to={`/blog/${p.slug}`} className="group block">
                  <div className="relative aspect-[16/11] overflow-hidden bg-[#f0efed]">
                    {p.cover_image && (
                      <img src={p.cover_image} alt={p.title} className="absolute inset-0 w-full h-full object-cover hover-lift group-hover:scale-105" />
                    )}
                  </div>
                  <div className="pt-5">
                    {p.tags?.[0] && <span className="text-xs tracking-[0.2em] uppercase font-bold text-brand">{p.tags[0]}</span>}
                    <h2 className="font-display font-bold text-2xl leading-tight tracking-tight mt-2 group-hover:text-brand transition-colors">{p.title}</h2>
                    <p className="text-ink/60 mt-2 line-clamp-2">{p.excerpt}</p>
                    <div className="flex items-center gap-2 mt-4 text-sm font-medium">
                      {t.blog.read} <ArrowUpRight className="w-4 h-4 group-hover:rotate-45 transition-transform" />
                    </div>
                  </div>
                </Link>
              </motion.article>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
