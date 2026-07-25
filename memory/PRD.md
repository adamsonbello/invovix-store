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
- Catalogue produits (filtres catégorie + recherche), page produit, 8 produits seed avec visuels générés (servis en local /public/products).
- Panier (localStorage), création de commande, calcul livraison (offerte >=50€).
- Paiement Stripe (Flow B, montant dynamique EUR) — VÉRIFIÉ end-to-end (session créée, redirection checkout).
- PayPal REST (Orders v2, create+capture) — code prêt, ACTIVÉ dès que clés fournies (désactivé UI si non configuré).
- CJDropshipping: client API (token/refresh), recherche + import produits dans l'admin — code prêt, s'active dès que CJ_API_KEY fournie.
- Admin dashboard: stats, CRUD produits, gestion statut commandes, onglet import CJ.
- Bilingue FR/EN, responsive, animations premium.

## Pending / Requires user keys
- CJ_API_KEY (backend/.env) → active recherche + import CJ.
- PAYPAL_CLIENT_ID / PAYPAL_SECRET (backend/.env) → active PayPal (bouton actuellement désactivé).
- PayPal: brancher le SDK JS PayPal Buttons dans Checkout pour l'approbation complète (actuellement create order côté serveur uniquement).

## Backlog
- P1: Webhook signature PayPal, emails de confirmation (Resend), suivi de livraison.
- P1: Pagination catalogue, gestion stock réelle via CJ, variantes produit.
- P2: Wishlist, avis clients, codes promo, filtres prix.

## Credentials
Voir /app/memory/test_credentials.md (admin@invovix.store / Invovix2026!).
