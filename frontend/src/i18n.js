import React, { createContext, useContext, useState, useCallback } from "react";

const translations = {
  fr: {
    nav: { shop: "Boutique", smartHome: "Maison connectée", workspace: "Télétravail", security: "Sécurité", story: "Manifeste", account: "Compte", admin: "Admin", login: "Connexion", logout: "Déconnexion", cart: "Panier" },
    hero: { overline: "Domotique premium · Livraison Europe", l1: "La maison", l2: "qui pense", l3: "à votre place.", sub: "Invovix conçoit un écosystème connecté pour la maison intelligente et le télétravail. Objets pensés, livrés dans toute la zone euro.", cta: "Découvrir la boutique", cta2: "Notre manifeste" },
    marquee: ["Maison connectée", "Télétravail", "Sécurité intelligente", "Livraison Europe", "Support FR / EN"],
    featured: { overline: "Sélection", title: "Les essentiels connectés", sub: "Une curation d'objets techniques pour transformer votre quotidien.", all: "Voir toute la boutique" },
    categories: { overline: "Univers", title: "Explorez par usage", smartHome: "Maison connectée", smartHomeD: "Éclairage, thermostats, hubs.", workspace: "Télétravail", workspaceD: "Bureaux augmentés, sans fil.", security: "Sécurité", securityD: "Caméras & capteurs intelligents." },
    manifesto: { overline: "Le manifeste Invovix", c1t: "La technologie disparaît", c1d: "Le meilleur objet connecté est celui qu'on oublie. Il agit, anticipe et s'efface. Nous concevons pour la simplicité radicale.", c2t: "Fabriqué pour durer", c2d: "Chaque produit est sélectionné pour sa fiabilité et son intégration native à votre écosystème existant.", c3t: "Livré en Europe", c3d: "Une logistique pensée pour la zone euro. Prix en euros, support bilingue, livraison suivie." },
    trust: { free: "Livraison offerte dès 50€", freeD: "Partout en zone euro", secure: "Paiement sécurisé", secureD: "Stripe & PayPal, cryptage SSL", support: "Support bilingue", supportD: "Assistance FR / EN 7j/7", returns: "Retours 30 jours", returnsD: "Satisfait ou remboursé" },
    cta: { title: "Prêt à connecter votre intérieur ?", sub: "Rejoignez les foyers qui ont choisi l'intelligence discrète.", btn: "Commencer" },
    shop: { title: "La boutique", sub: "Tous nos objets connectés, sélectionnés pour l'Europe.", filterAll: "Tout", empty: "Aucun produit trouvé.", search: "Rechercher…" },
    product: { add: "Ajouter au panier", added: "Ajouté au panier", buy: "Acheter maintenant", desc: "Description", back: "Retour", inStock: "En stock", qty: "Quantité", save: "Économisez" },
    cart: { title: "Votre panier", empty: "Votre panier est vide.", continue: "Continuer mes achats", subtotal: "Sous-total", shipping: "Livraison", free: "Offerte", total: "Total", checkout: "Passer commande", remove: "Retirer", each: "l'unité" },
    checkout: { title: "Paiement", contact: "Coordonnées de livraison", fullName: "Nom complet", email: "Email", address: "Adresse", city: "Ville", postal: "Code postal", country: "Pays", phone: "Téléphone", payment: "Mode de paiement", card: "Carte bancaire (Stripe)", paypal: "PayPal", paypalSoon: "Bientôt disponible", pay: "Payer", summary: "Récapitulatif", processing: "Traitement…", loginFirst: "Connectez-vous pour finaliser votre commande." },
    payment: { successT: "Paiement confirmé", successD: "Merci pour votre commande ! Un email de confirmation vous sera envoyé.", verifying: "Vérification du paiement…", cancelT: "Paiement annulé", cancelD: "Votre paiement a été annulé. Votre panier est conservé.", orders: "Voir mes commandes", shop: "Retour à la boutique", failed: "Le paiement n'a pas abouti." },
    auth: { loginT: "Connexion", registerT: "Créer un compte", email: "Email", password: "Mot de passe", name: "Nom complet", loginBtn: "Se connecter", registerBtn: "Créer mon compte", noAccount: "Pas encore de compte ?", hasAccount: "Déjà inscrit ?", signup: "Inscrivez-vous", signin: "Connectez-vous" },
    account: { title: "Mon compte", hello: "Bonjour", orders: "Mes commandes", noOrders: "Aucune commande pour le moment.", order: "Commande", status: "Statut", total: "Total", date: "Date", items: "articles" },
    admin: { title: "Tableau de bord", revenue: "Chiffre d'affaires", orders: "Commandes", paid: "Payées", products: "Produits", customers: "Clients", tabProducts: "Produits", tabOrders: "Commandes", tabCj: "Import CJ", addProduct: "Ajouter un produit", cjSearch: "Rechercher sur CJDropshipping", cjImport: "Importer", cjNotConfigured: "Clé API CJDropshipping non configurée. Ajoutez-la pour importer des produits.", newProduct: "Nouveau produit", ptitle: "Titre", pprice: "Prix (€)", pcompare: "Prix barré (€)", pcat: "Catégorie", pimg: "URL image", pdesc: "Description", save: "Enregistrer", delete: "Supprimer", edit: "Modifier", featured: "Vedette", customer: "Client", status: "Statut" },
    footer: { tagline: "La maison connectée, réinventée pour l'Europe.", shop: "Boutique", company: "Entreprise", about: "À propos", contact: "Contact", legal: "Mentions légales", rights: "Tous droits réservés.", newsletter: "Restez connecté", newsletterD: "Nouveautés et offres, sans spam.", subscribe: "S'inscrire" },
    reviews: { title: "Avis clients", based: "avis", product: "Produit", transport: "Transport / Livraison", write: "Laisser un avis", yourRating: "Note du produit", deliveryRating: "Note de la livraison / transport", comment: "Votre commentaire", placeholder: "Partagez votre expérience produit et livraison…", submit: "Publier mon avis", empty: "Aucun avis pour le moment. Soyez le premier à en laisser un.", verified: "Achat vérifié", mustBuy: "Seuls les acheteurs vérifiés peuvent laisser un avis.", thanks: "Merci pour votre avis !", already: "Vous avez déjà laissé un avis pour ce produit.", loginToReview: "Connectez-vous pour laisser un avis." },
    announce: "Livraison offerte dès 50€ en zone euro · Support bilingue FR / EN",
    newsletterOk: "Merci ! Vous êtes inscrit à la newsletter.",
    common: { loading: "Chargement…" },
  },
  en: {
    nav: { shop: "Shop", smartHome: "Smart Home", workspace: "Remote Work", security: "Security", story: "Manifesto", account: "Account", admin: "Admin", login: "Login", logout: "Logout", cart: "Cart" },
    hero: { overline: "Premium smart home · Europe delivery", l1: "The home", l2: "that thinks", l3: "for you.", sub: "Invovix designs a connected ecosystem for the smart home and remote work. Considered objects, delivered across the eurozone.", cta: "Explore the shop", cta2: "Our manifesto" },
    marquee: ["Smart Home", "Remote Work", "Intelligent Security", "Europe Delivery", "EN / FR Support"],
    featured: { overline: "Selection", title: "Connected essentials", sub: "A curation of technical objects to transform your everyday.", all: "Browse the full shop" },
    categories: { overline: "Worlds", title: "Explore by use", smartHome: "Smart Home", smartHomeD: "Lighting, thermostats, hubs.", workspace: "Remote Work", workspaceD: "Augmented, wireless desks.", security: "Security", securityD: "Smart cameras & sensors." },
    manifesto: { overline: "The Invovix manifesto", c1t: "Technology disappears", c1d: "The best connected object is the one you forget. It acts, anticipates and fades away. We design for radical simplicity.", c2t: "Built to last", c2d: "Every product is selected for its reliability and native integration into your existing ecosystem.", c3t: "Delivered in Europe", c3d: "Logistics built for the eurozone. Prices in euros, bilingual support, tracked delivery." },
    trust: { free: "Free shipping from €50", freeD: "Everywhere in the eurozone", secure: "Secure payment", secureD: "Stripe & PayPal, SSL encrypted", support: "Bilingual support", supportD: "EN / FR assistance 7/7", returns: "30-day returns", returnsD: "Satisfied or refunded" },
    cta: { title: "Ready to connect your space?", sub: "Join the homes that chose discreet intelligence.", btn: "Get started" },
    shop: { title: "The shop", sub: "All our connected objects, curated for Europe.", filterAll: "All", empty: "No products found.", search: "Search…" },
    product: { add: "Add to cart", added: "Added to cart", buy: "Buy now", desc: "Description", back: "Back", inStock: "In stock", qty: "Quantity", save: "Save" },
    cart: { title: "Your cart", empty: "Your cart is empty.", continue: "Continue shopping", subtotal: "Subtotal", shipping: "Shipping", free: "Free", total: "Total", checkout: "Checkout", remove: "Remove", each: "each" },
    checkout: { title: "Checkout", contact: "Shipping details", fullName: "Full name", email: "Email", address: "Address", city: "City", postal: "Postal code", country: "Country", phone: "Phone", payment: "Payment method", card: "Credit card (Stripe)", paypal: "PayPal", paypalSoon: "Coming soon", pay: "Pay", summary: "Summary", processing: "Processing…", loginFirst: "Log in to complete your order." },
    payment: { successT: "Payment confirmed", successD: "Thank you for your order! A confirmation email is on its way.", verifying: "Verifying payment…", cancelT: "Payment cancelled", cancelD: "Your payment was cancelled. Your cart is saved.", orders: "View my orders", shop: "Back to shop", failed: "Payment did not complete." },
    auth: { loginT: "Login", registerT: "Create account", email: "Email", password: "Password", name: "Full name", loginBtn: "Sign in", registerBtn: "Create account", noAccount: "No account yet?", hasAccount: "Already registered?", signup: "Sign up", signin: "Sign in" },
    account: { title: "My account", hello: "Hello", orders: "My orders", noOrders: "No orders yet.", order: "Order", status: "Status", total: "Total", date: "Date", items: "items" },
    admin: { title: "Dashboard", revenue: "Revenue", orders: "Orders", paid: "Paid", products: "Products", customers: "Customers", tabProducts: "Products", tabOrders: "Orders", tabCj: "CJ Import", addProduct: "Add product", cjSearch: "Search CJDropshipping", cjImport: "Import", cjNotConfigured: "CJDropshipping API key not configured. Add it to import products.", newProduct: "New product", ptitle: "Title", pprice: "Price (€)", pcompare: "Compare-at price (€)", pcat: "Category", pimg: "Image URL", pdesc: "Description", save: "Save", delete: "Delete", edit: "Edit", featured: "Featured", customer: "Customer", status: "Status" },
    footer: { tagline: "The connected home, reinvented for Europe.", shop: "Shop", company: "Company", about: "About", contact: "Contact", legal: "Legal", rights: "All rights reserved.", newsletter: "Stay connected", newsletterD: "News and offers, no spam.", subscribe: "Subscribe" },
    reviews: { title: "Customer reviews", based: "reviews", product: "Product", transport: "Shipping / Delivery", write: "Write a review", yourRating: "Product rating", deliveryRating: "Delivery / shipping rating", comment: "Your comment", placeholder: "Share your product and delivery experience…", submit: "Publish my review", empty: "No reviews yet. Be the first to leave one.", verified: "Verified purchase", mustBuy: "Only verified buyers can leave a review.", thanks: "Thanks for your review!", already: "You already reviewed this product.", loginToReview: "Log in to leave a review." },
    announce: "Free shipping from €50 in the eurozone · EN / FR bilingual support",
    newsletterOk: "Thanks! You're subscribed to the newsletter.",
    common: { loading: "Loading…" },
  },
};

const I18nContext = createContext(null);

export function LanguageProvider({ children }) {
  const [lang, setLang] = useState(localStorage.getItem("invovix_lang") || "fr");
  const toggle = useCallback(() => {
    setLang((l) => {
      const next = l === "fr" ? "en" : "fr";
      localStorage.setItem("invovix_lang", next);
      return next;
    });
  }, []);
  const t = translations[lang];
  return <I18nContext.Provider value={{ lang, t, toggle, setLang }}>{children}</I18nContext.Provider>;
}

export function useI18n() {
  return useContext(I18nContext);
}
