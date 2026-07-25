# Invovix — E-commerce Dropshipping (Smart Home & Remote Work)

## Original Problem Statement
Site e-commerce professionnel de dropshipping, compatible CJDropshipping. Domaine: invovix.store.
Niche: domotique (maison connectée) + tech télétravail. Cible: Europe zone euro. Bilingue FR/EN.
Paiements: Stripe + PayPal. Espace admin avec connexion. Comptes clients. Design premium (carte blanche).

## Architecture
- Frontend: React 19 + Tailwind + framer-motion + Lenis (smooth scroll) + react-fast-marquee. shadcn/ui.
- Backend: FastAPI (modules: server, database, security, cj, payments). MongoDB (motor).
- Auth: JWT Bearer (localStorage), bcrypt. Roles: admin / customer. Admin seeded on startup.
- i18n: contexte FR/EN maison, switch dans le header.
- Design: Swiss/high-contrast, Cabinet Grotesk + Satoshi, accent #FF3300, hero kinétique masqué, manifeste numéroté, marquee.

## Personas
- Client européen achetant de la domotique / matériel télétravail (paiement EUR).
- Admin gérant produits, commandes, et import CJDropshipping.

## Implemented (2026-06)
- Auth complète (register/login/me), JWT, admin seed idempotent.
- Catalogue produits (filtres + recherche), page produit, 8 produits seed + visuels générés (servis en /public).
- Panier, commandes, calcul livraison (offerte >=50€).
- **Stripe** (Flow B, EUR) sur le **compte du client** (clé sk_test fournie) — VÉRIFIÉ (session + redirection).
- **PayPal** REST (Orders v2, create+capture) + **boutons PayPal JS SDK** dans le checkout — clés Sandbox du client configurées. Backend VÉRIFIÉ (OAuth + création d'ordre → vrai PayPal order id). Test visuel e2e à faire par le client (limite de l'outil de screenshot sur les pages authentifiées).
- **CJDropshipping** connecté : recherche + import. Images CJ téléchargées côté serveur vers /public (contournement hotlink), descriptions HTML nettoyées. VÉRIFIÉ.
- **Avis & ratings** : note produit + note transport/livraison, achat vérifié requis, moyenne agrégée + JSON-LD. VÉRIFIÉ.
- **SEO** : meta dynamiques + OpenGraph + JSON-LD (Organization/Product), **sitemap.xml dynamique** (/api/sitemap.xml), robots.txt. VÉRIFIÉ.
- **Marketing** : capture newsletter (persistée en base). VÉRIFIÉ.
- **Email post-livraison via Brevo** (REST API v3, xkeysib) : envoyé automatiquement quand une commande passe en "delivered" (invitation à laisser un avis produit+transport, bilingue). VÉRIFIÉ (HTTP 201 + log "email sent"). Restriction IP Brevo désactivée par le client.

## Pending / Requires user action
- PayPal **Live** : nécessite un compte Business (les clés actuelles sont Sandbox/test).
- Brevo : vérifier l'expéditeur contact@invovix.store + authentifier le domaine (DKIM/DMARC) pour la délivrabilité.
- Test e2e navigateur du bouton PayPal avec un compte acheteur Sandbox.

## Backlog
- P1: Webhook signature PayPal, emails de confirmation (Resend), suivi de livraison.
- P1: Pagination catalogue, gestion stock réelle via CJ, variantes produit.
- P2: Wishlist, avis clients, codes promo, filtres prix.

## Credentials
Voir /app/memory/test_credentials.md (admin@invovix.store / Invovix2026!).
