import React from "react";
import { Link } from "react-router-dom";
import { Truck, RotateCcw, MessageCircle } from "lucide-react";
import { useI18n } from "@/i18n";
import SEO from "@/components/SEO";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";

export default function FAQ() {
  const { t } = useI18n();
  const f = t.faq;

  return (
    <div className="pt-28 md:pt-36 pb-32" data-testid="faq-page">
      <SEO
        title={f.title}
        description={f.sub}
        path="/faq"
        jsonLd={{
          "@context": "https://schema.org",
          "@type": "FAQPage",
          mainEntity: f.items.map((it) => ({
            "@type": "Question",
            name: it.q,
            acceptedAnswer: { "@type": "Answer", text: it.a },
          })),
        }}
      />
      <div className="max-w-[1000px] mx-auto px-5 md:px-10">
        <h1 className="font-display font-black uppercase tracking-tighter text-6xl md:text-8xl">{f.title}</h1>
        <p className="text-ink/60 text-lg mt-4 max-w-lg">{f.sub}</p>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-14">
          <div className="bg-surface p-6">
            <Truck className="w-6 h-6 text-brand mb-3" strokeWidth={1.5} />
            <h3 className="font-display font-bold text-lg">{f.shippingT}</h3>
            <p className="text-ink/60 text-sm mt-2">{f.shippingD}</p>
          </div>
          <div className="bg-surface p-6">
            <RotateCcw className="w-6 h-6 text-brand mb-3" strokeWidth={1.5} />
            <h3 className="font-display font-bold text-lg">{f.returnsT}</h3>
            <p className="text-ink/60 text-sm mt-2">{f.returnsD}</p>
          </div>
          <Link to="/contact" className="bg-ink text-cream p-6 grain group">
            <MessageCircle className="w-6 h-6 text-brand mb-3" strokeWidth={1.5} />
            <h3 className="font-display font-bold text-lg">{f.contactT}</h3>
            <p className="text-white/60 text-sm mt-2 group-hover:text-white transition-colors">{f.contactD}</p>
          </Link>
        </div>

        <div className="mt-16">
          <Accordion type="single" collapsible className="w-full" data-testid="faq-accordion">
            {f.items.map((it, i) => (
              <AccordionItem key={i} value={`item-${i}`} data-testid={`faq-item-${i}`}>
                <AccordionTrigger className="text-left font-display font-bold text-lg md:text-xl hover:text-brand hover:no-underline">
                  {it.q}
                </AccordionTrigger>
                <AccordionContent className="text-ink/70 text-base leading-relaxed">{it.a}</AccordionContent>
              </AccordionItem>
            ))}
          </Accordion>
        </div>
      </div>
    </div>
  );
}
