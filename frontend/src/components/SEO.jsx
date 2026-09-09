import React from "react";
import { Helmet } from "react-helmet-async";
import { useI18n } from "@/i18n";

const SITE = "https://invovix.store";
const DEFAULT_IMG = `${SITE}/og-image.jpg`;

export default function SEO({ title, description, path = "", image, type = "website", jsonLd }) {
  const { lang } = useI18n();
  const fullTitle = title ? `${title} — Invovix` : "Invovix — Smart Home & Remote Work Tech";
  const desc =
    description ||
    (lang === "fr"
      ? "Invovix — domotique premium et matériel de télétravail, livrés dans toute la zone euro. Maison connectée, sécurité, bureau augmenté."
      : "Invovix — premium smart home & remote work tech, delivered across the eurozone. Connected home, security, augmented workspace.");
  const url = `${SITE}${path}`;
  const img = image || DEFAULT_IMG;

  return (
    <Helmet>
      <html lang={lang} />
      <title>{fullTitle}</title>
      <meta name="description" content={desc} />
      <link rel="canonical" href={url} />
      <meta property="og:type" content={type} />
      <meta property="og:site_name" content="Invovix" />
      <meta property="og:title" content={fullTitle} />
      <meta property="og:description" content={desc} />
      <meta property="og:url" content={url} />
      <meta property="og:image" content={img} />
      <meta property="og:locale" content={lang === "fr" ? "fr_FR" : "en_US"} />
      <meta name="twitter:card" content="summary_large_image" />
      <meta name="twitter:title" content={fullTitle} />
      <meta name="twitter:description" content={desc} />
      <meta name="twitter:image" content={img} />
      {jsonLd && <script type="application/ld+json">{JSON.stringify(jsonLd)}</script>}
    </Helmet>
  );
}
