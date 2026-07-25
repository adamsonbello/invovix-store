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

## Implemented (2026-06 — session Blog/Contact)
- **Page Contact** (/contact) liée dans la navbar (FR "Contact"), formulaire → POST /api/contact (persisté en base + notification Brevo à l'admin en BackgroundTask). VÉRIFIÉ.
- **Système Blog** : page liste /blog + page article /blog/:slug (SEO + JSON-LD BlogPosting). 3 articles de démo seedés (domotique / télétravail / sécurité). VÉRIFIÉ.
- **Éditeur Blog admin** (onglet "Blog" dans /admin) : éditeur riche react-quill-new avec upload d'images (POST /api/admin/upload → stockage same-origin /public/blog/), CRUD complet (create/edit/delete). VÉRIFIÉ (backend 14/14 pytest + UI screenshot).
- **Onglet Messages admin** : liste des messages du formulaire de contact (GET /api/admin/contacts). VÉRIFIÉ.
- **Bouton Connexion navbar** : bouton pill visible pointant vers /login (qui contient le lien inscription) quand déconnecté. VÉRIFIÉ.

## Implemented (2026-06 — session Conversion/Rétention & Sécurité)
- **Bandeau promo** en haut du site (configurable admin, dismissable) + **bouton WhatsApp** flottant (configurable admin) + **onglet Réglages** admin (GET /api/settings, PUT /api/admin/settings). VÉRIFIÉ.
- **Bloc "Le Journal"** (3 derniers articles) + **bloc Avis clients** (GET /api/reviews/featured) sur la page d'accueil. VÉRIFIÉ.
- **Recherche instantanée** (modal navbar, debounce sur GET /api/products?q=). VÉRIFIÉ.
- **Wishlist / Favoris** (WishlistContext, cœur sur ProductCard + ProductDetail, page /wishlist, compteur navbar ; endpoints GET/POST /api/wishlist auth). VÉRIFIÉ.
- **"Vous aimerez aussi"** sur la page produit (GET /api/products/:id/related). VÉRIFIÉ.
- **Codes promo** : validation panier + checkout (POST /api/promo/validate), discount appliqué à la commande (_build_order), CRUD admin (/api/admin/promos). Code **WELCOME10** (-10%) seedé. VÉRIFIÉ (math : subtotal - 10% + shipping).
- **Pop-up newsletter -10%** (après 12s, 1x/localStorage) affichant le code WELCOME10. VÉRIFIÉ.
- **Page FAQ** /faq (accordion + livraison/retours + JSON-LD FAQPage). VÉRIFIÉ.
- **Sécurité formulaires** : honeypot (champ 'website') + rate-limiting IP + **Google reCAPTCHA v3** (soft-fail : la clé est restreinte au domaine invovix.store ; sur preview le token est vide → honeypot+rate-limit assurent la protection ; en production le score reCAPTCHA est appliqué). VÉRIFIÉ (28 tests pytest verts).
- **Google Tag Manager** (GTM-KZBXP887) intégré dans index.html (head + noscript). 
- **Sitemap** enrichi : URLs des articles de blog + /faq + /contact. VÉRIFIÉ.

## Pending / Requires user action

## Implemented (2026-06 — session Catalogue CJ + Fulfillment + Légal + Emails)
- **Seed catalogue CJ réel** : script `/app/scripts/seed_cj.py` (recherche + import en masse via API admin, pacing anti‑429, marge 55%). **23 produits réels** importés sur les 3 catégories. VÉRIFIÉ. NB : la recherche CJ étant floue, quelques produits sont hors‑niche → à épurer via l'admin.
- **Fulfillment CJ automatique** : à chaque commande **payée** (Stripe/PayPal/webhook), création auto de la commande fournisseur CJ (`createOrderV2`, payType=3 par défaut) + email de confirmation. Endpoints admin `POST /admin/orders/{id}/fulfill` (relance) et `POST /admin/orders/{id}/sync-cj` (récupère statut/numéro de suivi et déclenche l'email d'expédition). UI admin : boutons Fulfill/Sync + affichage suivi. VÉRIFIÉ de bout en bout (commande CJ réelle SD… créée, sync=CREATED).
  - Config (env, défauts fonctionnels) : `CJ_AUTO_FULFILL=true`, `CJ_PAY_TYPE=3`, `CJ_FROM_COUNTRY=CN`, `CJ_DEFAULT_LOGISTIC="CJPacket Ordinary"`.
- **Emails transactionnels complets** (Brevo) : **confirmation de commande** (au paiement, idempotent), **expédition + suivi** (au passage "shipped" ou via sync CJ), + review post‑livraison (existant). Suivi colis affiché aussi dans l'espace client (/account). VÉRIFIÉ (Brevo 201).
- **Pages légales RGPD/CGV** : `/legal/mentions`, `/legal/cgv`, `/legal/confidentialite` (contenu FR/EN, placeholders [À COMPLÉTER] pour infos société) + **bandeau consentement cookies** (accept/refuse, push dataLayer GTM). Liens footer + sitemap. VÉRIFIÉ.

## Requires user action (mise à jour)
- **reCAPTCHA v3** : ajouter le domaine de production `invovix.store` **ET** le domaine de preview aux domaines autorisés dans la console Google reCAPTCHA pour activer le scoring anti-bot complet (actuellement soft-fail hors invovix.store).
- **WhatsApp** : renseigner le numéro international dans /admin > Réglages et activer le bouton.
- PayPal **Live** : nécessite un compte Business (les clés actuelles sont Sandbox/test).
- Brevo : vérifier l'expéditeur contact@invovix.store + authentifier le domaine (DKIM/DMARC) pour la délivrabilité.
- Test e2e navigateur du bouton PayPal avec un compte acheteur Sandbox.

## Backlog
- P1: Webhook signature PayPal, emails de confirmation (Resend), suivi de livraison.
- P1: Pagination catalogue, gestion stock réelle via CJ, variantes produit.
- P2: Wishlist, avis clients, codes promo, filtres prix.

## Credentials
Voir /app/memory/test_credentials.md (admin@invovix.store / Invovix2026!).
