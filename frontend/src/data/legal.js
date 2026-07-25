// Contenu légal bilingue. ⚠️ Les champs [À COMPLÉTER] doivent être renseignés
// avec les informations réelles de l'entreprise (raison sociale, SIRET, adresse…).
export const LEGAL_DOCS = {
  mentions: {
    fr: {
      title: "Mentions légales",
      updated: "Dernière mise à jour : 2026",
      sections: [
        { h: "Éditeur du site", p: "Le site invovix.store est édité par Invovix — [RAISON SOCIALE À COMPLÉTER], [FORME JURIDIQUE], au capital de [MONTANT] €, immatriculée sous le SIREN [À COMPLÉTER], dont le siège social est situé [ADRESSE À COMPLÉTER]. TVA intracommunautaire : [À COMPLÉTER]." },
        { h: "Contact", p: "Email : contact@invovix.store. Directeur de la publication : [NOM À COMPLÉTER]." },
        { h: "Hébergement", p: "Le site est hébergé par [HÉBERGEUR À COMPLÉTER], [ADRESSE HÉBERGEUR]." },
        { h: "Propriété intellectuelle", p: "L'ensemble des contenus du site (textes, visuels, logo, charte graphique) est protégé par le droit d'auteur. Toute reproduction sans autorisation est interdite." },
        { h: "Responsabilité", p: "Invovix s'efforce d'assurer l'exactitude des informations diffusées mais ne saurait être tenue responsable des erreurs ou d'une indisponibilité du service." },
      ],
    },
    en: {
      title: "Legal notice",
      updated: "Last updated: 2026",
      sections: [
        { h: "Publisher", p: "invovix.store is operated by Invovix — [COMPANY NAME TBD], registered under [COMPANY ID TBD], head office at [ADDRESS TBD]. VAT: [TBD]." },
        { h: "Contact", p: "Email: contact@invovix.store. Publication director: [NAME TBD]." },
        { h: "Hosting", p: "The website is hosted by [HOST TBD], [HOST ADDRESS]." },
        { h: "Intellectual property", p: "All site content (texts, visuals, logo) is protected by copyright. Reproduction without permission is prohibited." },
        { h: "Liability", p: "Invovix strives for accuracy but cannot be held liable for errors or service unavailability." },
      ],
    },
  },
  cgv: {
    fr: {
      title: "Conditions Générales de Vente",
      updated: "Dernière mise à jour : 2026",
      sections: [
        { h: "1. Objet", p: "Les présentes CGV régissent les ventes de produits réalisées sur invovix.store entre Invovix et ses clients (consommateurs au sens du Code de la consommation), dans la zone euro." },
        { h: "2. Prix", p: "Les prix sont indiqués en euros toutes taxes comprises (TTC). Invovix se réserve le droit de modifier ses prix à tout moment, le prix applicable étant celui en vigueur au moment de la commande." },
        { h: "3. Commande & paiement", p: "Le paiement s'effectue par carte bancaire (Stripe) ou PayPal, de manière sécurisée (chiffrement SSL). La commande est validée après confirmation du paiement." },
        { h: "4. Livraison", p: "Les produits sont livrés dans toute la zone euro. Livraison offerte dès 50€ d'achat, sinon une participation de 4,90€ s'applique. Les délais indicatifs sont de 5 à 12 jours ouvrés selon le produit. Un numéro de suivi est communiqué à l'expédition." },
        { h: "5. Droit de rétractation", p: "Conformément aux articles L221-18 et suivants du Code de la consommation, vous disposez d'un délai de 14 jours à compter de la réception pour exercer votre droit de rétractation, sans avoir à justifier de motifs. Invovix accorde en outre une garantie satisfait ou remboursé de 30 jours." },
        { h: "6. Retours & remboursements", p: "Pour tout retour, contactez contact@invovix.store. Le remboursement intervient dans un délai maximum de 14 jours après réception du produit retourné, par le même moyen de paiement." },
        { h: "7. Garanties légales", p: "Tous les produits bénéficient de la garantie légale de conformité (art. L217-4 et s.) et de la garantie des vices cachés (art. 1641 et s. du Code civil)." },
        { h: "8. Litiges & médiation", p: "En cas de litige, une solution amiable sera recherchée en priorité. Le consommateur peut recourir gratuitement à un médiateur de la consommation ou à la plateforme européenne de règlement en ligne des litiges (ec.europa.eu/consumers/odr). Droit applicable : droit français." },
      ],
    },
    en: {
      title: "Terms & Conditions of Sale",
      updated: "Last updated: 2026",
      sections: [
        { h: "1. Purpose", p: "These terms govern sales made on invovix.store between Invovix and its customers (consumers) within the eurozone." },
        { h: "2. Prices", p: "Prices are shown in euros, all taxes included. Invovix may change prices at any time; the applicable price is the one in force at the time of the order." },
        { h: "3. Order & payment", p: "Payment is made securely by card (Stripe) or PayPal (SSL encryption). The order is confirmed once payment is validated." },
        { h: "4. Shipping", p: "Products are delivered throughout the eurozone. Free shipping from €50, otherwise a €4.90 fee applies. Indicative times are 5–12 business days. A tracking number is provided at shipment." },
        { h: "5. Right of withdrawal", p: "In accordance with EU consumer law, you have 14 days from receipt to withdraw without justification. Invovix also offers a 30-day satisfied-or-refunded guarantee." },
        { h: "6. Returns & refunds", p: "For any return, contact contact@invovix.store. Refunds are issued within 14 days of receiving the returned product, via the original payment method." },
        { h: "7. Legal warranties", p: "All products benefit from the legal warranty of conformity and the warranty against hidden defects." },
        { h: "8. Disputes & mediation", p: "In case of dispute, an amicable solution is sought first. Consumers may use the EU online dispute resolution platform (ec.europa.eu/consumers/odr). Governing law: French law." },
      ],
    },
  },
  confidentialite: {
    fr: {
      title: "Politique de confidentialité & cookies",
      updated: "Dernière mise à jour : 2026 · Conforme RGPD",
      sections: [
        { h: "Responsable du traitement", p: "Invovix ([À COMPLÉTER]) est responsable du traitement des données collectées sur invovix.store. Contact DPO : contact@invovix.store." },
        { h: "Données collectées", p: "Nous collectons : identité et coordonnées (nom, email, adresse de livraison), données de commande, et données de navigation (via cookies). Aucune donnée bancaire n'est stockée par Invovix : les paiements sont traités par Stripe et PayPal." },
        { h: "Finalités & base légale", p: "Traitement de vos commandes (exécution du contrat), envoi d'emails transactionnels, newsletter (consentement), amélioration du site et mesure d'audience (intérêt légitime / consentement pour les cookies)." },
        { h: "Durée de conservation", p: "Les données de commande sont conservées pendant la durée légale (facturation : 10 ans). Les données de prospection sont conservées 3 ans après le dernier contact." },
        { h: "Vos droits", p: "Vous disposez d'un droit d'accès, de rectification, d'effacement, de portabilité, de limitation et d'opposition. Exercez-les à contact@invovix.store. Vous pouvez introduire une réclamation auprès de la CNIL (cnil.fr)." },
        { h: "Cookies", p: "Le site utilise des cookies de mesure d'audience (Google Tag Manager / Google Analytics) déposés uniquement après votre consentement, ainsi que des cookies techniques nécessaires au fonctionnement (panier, session). Vous pouvez gérer votre choix via le bandeau cookies et à tout moment via les paramètres de votre navigateur." },
        { h: "Sous-traitants", p: "Nous partageons des données strictement nécessaires avec : Stripe & PayPal (paiement), CJDropshipping (expédition), Brevo (emails), Google (mesure d'audience). Certains transferts hors UE sont encadrés par des garanties appropriées." },
      ],
    },
    en: {
      title: "Privacy & cookie policy",
      updated: "Last updated: 2026 · GDPR compliant",
      sections: [
        { h: "Data controller", p: "Invovix ([TBD]) is the controller for data collected on invovix.store. DPO contact: contact@invovix.store." },
        { h: "Data collected", p: "We collect: identity and contact details (name, email, shipping address), order data, and browsing data (via cookies). No payment card data is stored by Invovix: payments are handled by Stripe and PayPal." },
        { h: "Purposes & legal basis", p: "Processing your orders (contract), transactional emails, newsletter (consent), site improvement and analytics (legitimate interest / cookie consent)." },
        { h: "Retention", p: "Order data is kept for the legal period (invoicing: 10 years). Marketing data is kept for 3 years after last contact." },
        { h: "Your rights", p: "You have rights of access, rectification, erasure, portability, restriction and objection. Exercise them at contact@invovix.store. You may lodge a complaint with your data protection authority." },
        { h: "Cookies", p: "The site uses analytics cookies (Google Tag Manager / Analytics) set only after your consent, plus technical cookies needed for operation (cart, session). Manage your choice via the cookie banner or your browser settings." },
        { h: "Processors", p: "We share strictly necessary data with: Stripe & PayPal (payment), CJDropshipping (shipping), Brevo (emails), Google (analytics). Some transfers outside the EU are covered by appropriate safeguards." },
      ],
    },
  },
};
