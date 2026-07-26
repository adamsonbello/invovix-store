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

## Implemented (2026-06 — session Back-office solide : stock, variantes, analytics, factures, retours)
- **Synchro stock CJ** : stock temps réel par variante via `/product/stock/queryByVid`. Endpoints `POST /admin/products/{id}/sync-stock` et `POST /admin/products/sync-stock-all` (paced). Storefront : badges En stock / Stock faible / Épuisé, blocage ajout panier + checkout si rupture (back+front). VÉRIFIÉ (stock réel 7).
- **Variantes produit** : le produit expose `variants` (nom/prix/image/stock/vid), `has_variants`, `stock_total`, `in_stock` (raw `cj_variants` masqué). Sélecteur sur la fiche produit, prix/image/stock dynamiques, panier & commande portent `variant_id` (→ bon vid au fulfillment CJ). VÉRIFIÉ.
- **Synchro auto du suivi** : tâche planifiée (`CJ_SYNC_INTERVAL_MIN`, défaut 60 min) qui sync les commandes ouvertes + email d'expédition auto ; + **webhook CJ** `POST /api/webhook/cj`. VÉRIFIÉ.
- **Tableau de bord Analytics** (onglet admin, recharts) : CA, commandes payées, panier moyen, taux de conversion, visites 30j, clients, courbe CA 30j, top produits, répartition par statut. Tracking visites `POST /api/track/pageview`. VÉRIFIÉ.
- **Factures PDF** (reportlab) : `GET /api/orders/{id}/invoice` (propriétaire/admin, commande payée). Bouton de téléchargement dans /account. VÉRIFIÉ (PDF 2.3 Ko).
- **Retours & remboursements** : demande client (`POST /returns`), gestion admin (onglet Retours : approuver→remboursement Stripe auto avec fallback manuel / refuser). Statuts affichés côté client. VÉRIFIÉ (52/52 pytest).

## Implemented (2026-06 — session Conformité e-facturation FR + synchro stock planifiée)
- **Synchro stock CJ planifiée (cron)** : tâche de fond `_stock_sync_loop` (server.py) lancée au démarrage, intervalle `STOCK_SYNC_INTERVAL_HOURS` (défaut 24h), gated par `STOCK_AUTO_SYNC` (défaut true). Aucun clic requis. Endpoints manuels conservés (`/admin/products/sync-stock-all`, `/admin/products/{id}/sync-stock`). VÉRIFIÉ (iteration 4, sync-all 15 produits OK).
- **Synchro suivi CJ planifiée** : `_tracking_sync_loop`, intervalle `CJ_SYNC_INTERVAL_MIN` (défaut 60), gated par `CJ_AUTO_SYNC`. VÉRIFIÉ.
- **Conformité e-facturation B2C (mandat FR)** :
  - **E-reporting** `GET /api/admin/ereporting` (JSON + CSV) : agrégation des ventes payées par jour × taux de TVA (régime franchise → TVA 0 ; assujetti → HT=TTC/1.2, TVA=TTC-HT). Export CSV depuis Admin > Réglages (bouton `ereporting-export-btn`). VÉRIFIÉ.
  - **Factures PDF numérotées** : numérotation séquentielle continue par année (`INV-YYYY-NNNNN`, compteur `counters`), idempotente par commande, mentions légales vendeur (forme juridique, SIREN/SIRET, TVA intracom) via Réglages. `GET /api/orders/{id}/invoice` (payé uniquement, owner/admin). VÉRIFIÉ.
  - **Identité légale** dans Admin > Réglages : forme juridique, SIREN, SIRET, régime TVA, taux — laissés en placeholders (choix utilisateur), configurables. Persistance VÉRIFIÉE.
- Validation : **68/68 pytest** (dont test_ereporting_invoice.py) + UI e2e (iteration 4). Aucun bug.

## Implemented (2026-06 — Phase 1 : Cerveau IA / AI Brain)
Objectif utilisateur : transformer la boutique en ERP dropshipping (30 modules). Phase 1 = intelligence IA.
- **Module IA backend** `/app/backend/ai.py` (`ai_router`), clé universelle Emergent (`EMERGENT_LLM_KEY`), texte = `gpt-5.4` (configurable `AI_TEXT_MODEL`), image = `gemini-3.1-flash-image-preview` (Nano Banana).
- **Réécriture de fiche** `POST /api/admin/ai/rewrite-product` → JSON (title, title_en, description FR/EN HTML, bullet_points, seo_title, seo_description, keywords, faq). VÉRIFIÉ.
- **Générateur d'images IA** `POST /api/admin/ai/generate-image` (styles: lifestyle/white/infographic/thumbnail, édition depuis image produit de référence). Sauvegarde en `/public/products/ai_*.png` (same-origin, anti-hotlink), ajout auto à la galerie produit. VÉRIFIÉ (fichier servi 200).
- **Scoring produit gagnant** `POST /api/admin/ai/product-score` → opportunity_score, demand/margin/competition, verdict, reasons, recommended_price, margin_pct. VÉRIFIÉ.
- **Assistant d'analyse décisionnelle** `POST /api/admin/ai/analyze` : Q&A langage naturel FR sur données réelles (CA, top produits, ruptures, à expédier…). VÉRIFIÉ.
- **UI Admin > Studio IA** (`Admin.jsx` : `AiTab` + 4 panneaux) avec application directe du contenu réécrit sur la fiche produit.
- Validation : **8/8 pytest** (`tests/test_ai.py`) + smoke frontend (iteration 5). Pop-up newsletter masqué sur /admin.

## Implemented (2026-06 — Amélioration IA "1 clic" + Phase 2 Back-office ERP)
### Amélioration : Studio IA branché partout
- **Optimisation 1-clic** `POST /api/admin/ai/optimize-product/{id}` (rewrite + score + image optionnelle), réutilisable. Stocke seo_title/seo_description/keywords/faq/bullet_points/ai_score/ai_optimized sur le produit.
- **Formulaire produit** : boutons « Optimiser avec l'IA » (réécrit titre/desc FR-EN) + « Générer une image IA ».
- **Liste produits admin** : bouton IA 1-clic par produit + badge score (IA xx/100 · ✨ optimisé).
- **Import CJ** : case « Optimiser à l'import (IA) » → réécriture + score auto à chaque import (rewrite+score, texte, rapide). VÉRIFIÉ (iteration 6).
### Phase 2 — Back-office ERP (module `erp.py`)
- **Fournisseurs + comparateur** (mod 6/23) : CRUD `/api/admin/suppliers`, score global (qualité − délai − port), `/compare` trié, comptage produits. UI onglet « Fournisseurs ». VÉRIFIÉ.
- **Catalogue enrichi** (mod 2) : produits + buy_price, marge (calculée UI), brand, sku, ean, weight, dimensions, subcategory, supplier_id, supplier_url, video_url. Form admin étendu. VÉRIFIÉ.
- **Dashboard enrichi** (mod 1) : bénéfice brut, CA 30j, bénéfice net, ROAS, ROI, dépenses pub (réglages), ruptures, stock faible, à expédier, alertes actives + graphe CA mensuel 12 mois. VÉRIFIÉ.
- **Moteur de règles no-code** (mod 21) : `/api/admin/rules` (SI rupture/stock≤seuil/marge<seuil → ALORS alerte/masquer/ajuster prix), exécution `/rules/run` + intégré à la synchro stock planifiée. Alertes `/api/admin/alerts` (résoudre/clear). UI onglet « Règles & Alertes ». VÉRIFIÉ.
- **Dépenses pub** dans Réglages (`ad_spend_30d`) pour ROAS/ROI/bénéfice net.
- Validation : **26/26 pytest** (`tests/test_erp_phase2.py`) + smoke UI (iteration 6). Bannières newsletter & cookies masquées sur /admin.

## Roadmap ERP (phases restantes)
- **Phase 2 (reste)** : import CSV/Excel/URL (mod 3) — non fait.
- **Phase 3 — CRM & Marketing** : CRM + fidélité (mod 10), email marketing/panier abandonné (mod 11), notifications multi-canal SMS/WhatsApp/Discord/Slack (mod 12), bundles + ventes flash (mod 16).
- **Phase 4 — Plateforme & sécurité** : rôles & permissions (mod 20), 2FA/journal/sauvegardes (mod 27), PWA (mod 26), multi-boutiques (mod 19), documents + API publique (mod 24/25).
- Note réalité : imports Amazon/AliExpress/Temu/Alibaba/eBay/Walmart/Etsy sans API officielle → CSV/Excel + import par URL (CJ = pipeline principal).

## Requires user action (mise à jour)
- **Identité légale société** : renseigner forme juridique, SIREN/SIRET, TVA intracom (et régime/taux TVA) dans Admin > Réglages avant émission de factures officielles (actuellement placeholders vides).
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
