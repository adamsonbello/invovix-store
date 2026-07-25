import React from "react";
import { useParams, Navigate } from "react-router-dom";
import { useI18n } from "@/i18n";
import SEO from "@/components/SEO";
import { LEGAL_DOCS } from "@/data/legal";

export default function Legal() {
  const { doc } = useParams();
  const { lang } = useI18n();
  const entry = LEGAL_DOCS[doc];
  if (!entry) return <Navigate to="/" replace />;
  const content = entry[lang] || entry.fr;

  return (
    <div className="pt-28 md:pt-36 pb-32" data-testid="legal-page">
      <SEO title={content.title} description={content.title} path={`/legal/${doc}`} />
      <div className="max-w-3xl mx-auto px-5 md:px-10">
        <h1 className="font-display font-black uppercase tracking-tighter text-4xl md:text-6xl">{content.title}</h1>
        <p className="text-stone text-sm mt-3">{content.updated}</p>
        <div className="mt-12 space-y-10">
          {content.sections.map((s, i) => (
            <section key={i} data-testid={`legal-section-${i}`}>
              <h2 className="font-display font-bold text-xl md:text-2xl mb-3">{s.h}</h2>
              <p className="text-ink/70 leading-relaxed">{s.p}</p>
            </section>
          ))}
        </div>
      </div>
    </div>
  );
}
