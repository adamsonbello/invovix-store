import React, { useEffect, useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import { useI18n } from "@/i18n";
import api from "@/lib/api";
import SEO from "@/components/SEO";

export default function BlogPost() {
  const { slug } = useParams();
  const { t, lang } = useI18n();
  const navigate = useNavigate();
  const [post, setPost] = useState(null);

  useEffect(() => {
    api.get(`/blog/${slug}`).then((r) => setPost(r.data)).catch(() => navigate("/blog"));
  }, [slug, navigate]);

  if (!post) return <div className="pt-40 text-center text-stone min-h-screen">{t.common.loading}</div>;

  return (
    <div className="pt-28 md:pt-32 pb-32" data-testid="blog-post-page">
      <SEO
        title={post.title}
        description={post.excerpt}
        path={`/blog/${post.slug}`}
        image={post.cover_image}
        type="article"
        jsonLd={{
          "@context": "https://schema.org",
          "@type": "BlogPosting",
          headline: post.title,
          description: post.excerpt,
          image: post.cover_image,
          author: { "@type": "Organization", name: "Invovix" },
          datePublished: post.created_at,
        }}
      />
      <article className="max-w-3xl mx-auto px-5">
        <Link to="/blog" className="inline-flex items-center gap-2 text-stone hover:text-brand transition-colors mb-8" data-testid="blog-back">
          <ArrowLeft className="w-4 h-4" /> {t.blog.back}
        </Link>
        {post.tags?.[0] && <span className="text-xs tracking-[0.2em] uppercase font-bold text-brand">{post.tags[0]}</span>}
        <h1 className="font-display font-black uppercase tracking-tighter leading-[0.95] text-4xl md:text-6xl mt-3">{post.title}</h1>
        <p className="text-stone mt-5 text-sm">
          {t.blog.by} {post.author} · {new Date(post.created_at).toLocaleDateString(lang)}
        </p>
        {post.cover_image && (
          <div className="relative aspect-[16/9] overflow-hidden bg-[#f0efed] my-10">
            <img src={post.cover_image} alt={post.title} className="absolute inset-0 w-full h-full object-cover" />
          </div>
        )}
        <div
          className="blog-content prose prose-lg max-w-none mt-8"
          data-testid="blog-content"
          dangerouslySetInnerHTML={{ __html: post.content }}
        />
      </article>
    </div>
  );
}
