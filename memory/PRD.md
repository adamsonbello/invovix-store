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

## Implemented (2026-06 — Phase 3 CRM & Marketing)
Modules 10/11/12/16 + fidélité. Livré en 3 lots testés (iteration 7 : 24/24 pytest + 100% front).
### 3A — CRM + Fidélité + Relance panier abandonné (`crm.py`)
- **CRM clients** `/api/admin/customers` (+ `/{id}`) : dépensé, commandes, panier moyen, retours, points, palier (Bronze/Argent/Or/Platine), statut (nouveau/actif/VIP), recherche + segments. UI onglet « Marketing & CRM » → sous-onglet Clients (modale fiche).
- **Fidélité** : 1 pt/€ à chaque commande payée (`accrue_loyalty`, idempotent), paliers par total dépensé. `GET /api/loyalty` + carte fidélité dans l'espace client.
- **Relance checkout abandonné** : `GET /api/admin/abandoned` (candidats, CA potentiel, relancés, récupérés), relance manuelle `/{id}/remind` + `/run`, boucle auto `_abandoned_cart_loop` (email Brevo `send_abandoned_cart` avec code promo). VÉRIFIÉ.
### 3B — Campagnes email + Bundles + Ventes flash (`marketing.py`)
- **Campagnes** `/api/admin/campaigns` (segments newsletter/customers/vip/all, envoi Brevo en background) + `/api/admin/segments/count`. UI sous-onglet Campagnes.
- **Bundles/Packs** : CRUD `/api/admin/bundles` + public `/api/bundles` (prix pack, économie %). Section « NOS PACKS » sur l'accueil. UI sous-onglet Bundles.
- **Ventes flash** : CRUD `/api/admin/flash-sales` (scope category/product/all, % + fin) + public `/api/flash-sales/active`. Remise appliquée côté serveur aux `/api/products` ET au checkout (`_build_order`). Bannière compte à rebours + badges flash sur les cartes produit. VÉRIFIÉ (34.90€→27.92€ à -20%).
### 3C — Notifications multi-canal (`notifications.py`)
- **Discord & Slack** (webhooks, sans clé) : notif à chaque commande payée (`notify_new_order`), test `/api/admin/notifications/test`. Réglages admin (webhooks + toggle). VÉRIFIÉ.
- **SMS & WhatsApp (Twilio)** : NON FAIT — nécessite les identifiants Twilio de l'utilisateur (Account SID, Auth Token, numéro).
- Réglages : `ad_spend_30d`, `discord_webhook_url`, `slack_webhook_url`, `notify_new_order`.

## Implemented (2026-06 — Phase 4 Plateforme & Sécurité)
Livré en 2 lots testés (iteration 8 : 24/24 backend + 100% front pour 4A ; 4B auto-vérifié curl+screenshot).
### 4A — RBAC + 2FA + Journal (`security.py`, `staff.py`, `twofa.py`)
- **RBAC** : rôles admin/manager/marketing/support/accounting/customer. Permissions par ZONE (`ROLE_PERMISSIONS`), dépendance `require_area(zone)` appliquée à TOUS les endpoints admin (server.py + ops/ai/erp/crm/marketing). `GET /api/auth/permissions`.
- **Gestion du personnel** (admin) : `/api/admin/staff` CRUD + rôle. UI onglet « Sécurité ».
- **2FA TOTP** (pyotp+qrcode) : `/api/auth/2fa/setup|enable|disable`, login 2 étapes (`temp_token` → `/api/auth/2fa/login`). UI panneau 2FA + écran code login.
- **Journal des connexions** : succès/échec + IP + UA, `GET /api/admin/login-journal`. UI panneau journal.
- Frontend : onglets admin filtrés par permissions ; `ProtectedRoute adminOnly` autorise le staff.
### 4B — PWA + API publique (`publicapi.py`)
- **PWA installable** : manifest + icônes 192/512/maskable, service-worker (network-first nav, jamais /api), enregistré. VÉRIFIÉ.
- **API publique read-only** `X-API-Key` : `GET /api/public/products|/{id}|/stats`. Clés API admin `/api/admin/api-keys` (CRUD+toggle). UI panneau « API publique ». VÉRIFIÉ (401/200).

## Implemented (2026-06 — Phase 5 : Multi-boutiques, Documents, Prévisions IA, Import CSV/URL)
Livré et testé (iteration 9 : 21/21 pytest backend + 100% frontend, aucun bug bloquant).
### Module 3 — Import produits CSV / Excel / URL (`imports.py`)
- **Import fichier** `POST /api/admin/import/file` (multipart : CSV ou XLSX via pandas/openpyxl). Mapping colonnes tolérant FR/EN (title, description, price, buy_price, category, brand, sku, ean, stock, image(s)). Prix calculé depuis buy_price×marge si prix absent. Images externes localisées en /public/products.
- **Import URL** `POST /api/admin/import/url` : scraping OpenGraph + JSON-LD (bs4/lxml) → titre, description, image, prix. 422 si aucune donnée produit détectée.
- UI Admin > onglet « Import produits » (2 panneaux : fichier + URL) avec récap des résultats. VÉRIFIÉ (marge 15€×1.6=24€).
### Module 24 — Gestion documentaire (`documents.py`)
- Stockage **privé** (`/app/backend/storage/documents`, jamais public), servi via endpoint protégé. CRUD `/api/admin/documents` (upload multipart + name/category/tags/notes/linked_order/linked_supplier), `GET /{id}/download` (StreamingResponse), DELETE. Catégories : contract/invoice/supplier/legal/shipping/other. Max 25 Mo. Zone RBAC : operations.
- UI Admin > onglet « Documents » : upload, filtres par catégorie, recherche, download/suppression. VÉRIFIÉ.
### Module Prévisions & Prix IA (`predict.py`)
- **Prévision CA** `GET /api/admin/predict/forecast` : régression linéaire (numpy) + moyenne mobile 7j sur 90j d'historique → prévision N jours, tendance, croissance 30j, demande par produit (30j vs 30j-1). Graphe recharts (historique + prévision pointillée).
- **Moteur de prix** `GET /api/admin/predict/pricing` : suggestions par produit pour aligner la marge cible (défaut 55%) sans dépasser le prix barré ; `POST /pricing/apply` applique ; `POST /ai-price/{id}` = avis IA (Emergent LLM, recommended_price + score). Zones : analytics (lecture), catalog (apply), ai (avis IA).
- UI Admin > onglet « Prévisions & Prix IA ». VÉRIFIÉ.
### Module 19 — Multi-boutiques (`stores.py`)
- Gestion centralisée : chaque boutique = catalogue central filtré par catégories (= synchronisation). CRUD `/api/admin/stores` (name, domain, tagline, currency, accent_color, categories, featured_only, active), `GET /{id}/catalog`. **Vitrine publique** `GET /api/public/stores/{slug}` (sans auth) renvoie config + produits (flash sales appliquées). Zone RBAC : operations.
- UI Admin > onglet « Multi-boutiques » : formulaire (chips catégories, couleur accent), liste avec compteur produits + slug d'API vitrine. VÉRIFIÉ.
- Dépendances ajoutées : openpyxl, beautifulsoup4, lxml.

### Lot fonctionnalités (zoom, avis CJ, comparateur, Audio, identité) — 2026-06
- **(1) Zoom/loupe** sur l'image en page produit (survol → agrandissement au curseur). `ProductDetail.jsx`. VÉRIFIÉ.
- **(2) Description CJ concise** : `_concise_description()` dans `cj.py` retire HTML/bruit logistique et garde l'essentiel (~600 car.).
- **(3) Compteur inventaire CJ** dans l'admin (onglet Produits) : produits catalogue / importés de CJ / stock total / clients. `/api/admin/stats` enrichi (`cj_products`, `total_stock`).
- **(6) Import des vrais avis CJ** : `POST /api/admin/products/{id}/import-cj-reviews` (bouton « Avis CJ » par produit). Récupère `/product/productComments`, traduit en FR (Emergent LLM), marque « achat vérifié », recalcule la note. Retry auto sur 429 (limite CJ 1 req/s). NB : n'importe que si le produit CJ a des avis (nos 15 produits CJ actuels en ont 0 avec ce compte). Pipeline traduction+stockage+note VÉRIFIÉ.
- **(8) Comparateur produits** (2 à 4) : `CompareContext` (localStorage), bouton sur ProductCard, barre flottante `CompareBar`, page `/compare` (tableau comparatif prix/marque/note/stock/livraison). VÉRIFIÉ (3 colonnes).
- **Catégorie Audio** : `seed_audio()` (4 produits démo) + label i18n + lien navbar. VÉRIFIÉ.
- **Identité numérique** : logo wordmark « INVOVIX. » (point rouge), favicon.ico + favicon-32 + icônes PWA (192/512/maskable/apple-touch) régénérés, image de partage `og-image.jpg` (SEO/OG mis à jour). Générés via Nano Banana.
- **Stockage objet Emergent** (`backend/storage.py`) : uploads documents + images blog migrés du disque pod (éphémère) vers Emergent Object Storage (persistant en déploiement). Documents → `/api/admin/documents/{id}/download` (protégé) ; blog → `/api/media/{path}`. Init au démarrage. VÉRIFIÉ (upload/download/list/delete).



### LOT 3B — Push web (VAPID) & API GraphQL — 2026-06
Auto-vérifié (curl + screenshots). Catalogue nettoyé : « Orchestral Music Stand » supprimé (1 hors-niche).
- **Web Push (VAPID)** (`push.py`) : clés VAPID générées (.env : VAPID_PUBLIC_KEY/PRIVATE_KEY/CLAIM_EMAIL). Endpoints : `GET /api/push/vapid-public-key`, `POST /api/push/subscribe|unsubscribe`, `GET /api/admin/push/stats`, `POST /api/admin/push/send` (require marketing). `send_push_to_all()` via pywebpush + purge des abonnements 404/410. SW (`service-worker.js`) : handlers `push` + `notificationclick`. Front : `PushOptIn.jsx` (bouton « Activer les notifications » dans le Footer) + onglet Admin Marketing « Notifications push » (compteur + formulaire d'envoi). **Auto-push** à la création d'une vente flash (marketing.py). NB : la livraison réelle exige la permission navigateur (non testable en preview headless) ; endpoints vérifiés par curl.
- **API GraphQL** (`graphql_api.py`, strawberry) montée sur `/api/graphql` (+ GraphiQL). Requêtes lecture catalogue : `products(category,q,page,size)`, `product(id)`, `categories`. Vérifié (query renvoie produits + catégories).
- Dépendances ajoutées : pywebpush, py-vapid, strawberry-graphql.


Auto-vérifié (curl + script + screenshot).
- **Pagination catalogue** (`Shop.jsx`) : 12 produits/page, contrôles Précédent/Suivant + numéros de page, reset à chaque changement de catégorie/recherche, scroll top. Catégorie **Audio** ajoutée aux filtres. Vérifié (27 produits → 3 pages).
- **Signature webhook PayPal** : `POST /api/payments/paypal/webhook` vérifie la signature via l'API PayPal `verify-webhook-signature` (env `PAYPAL_WEBHOOK_ID`). Rejette (400) toute requête non signée / non configurée ; sur `PAYMENT.CAPTURE.COMPLETED`/`CHECKOUT.ORDER.APPROVED` → commande payée + fulfillment (idempotent). Vérifié (unsigned → 400).
- **Webhooks sortants signés** (module 25 partiel) : `dispatch_event()` signe désormais en **HMAC-SHA256** (`X-Invovix-Signature`, `X-Invovix-Event`) ; secret auto-généré par webhook. Déclenché sur `order.paid` dans `fulfillment.handle_paid_order` (idempotent, flag `webhook_paid_sent`). Vérifié (dispatch réel → 200 + signature reçue).
- **RESTE (non fait, plus lourd)** : Push web (notifications navigateur — nécessite VAPID + gestion permission, difficile à vérifier en preview) ; API GraphQL complète (module 25).
### LOT 2 — Conversion & confiance — 2026-06
Auto-vérifié (curl audit + screenshots bannière/avis) ; démo reviews nettoyées.
- **Épuration catalogue CJ** : `GET /api/admin/products/audit` (détecte les produits hors-niche via allowlist de mots-clés FR/EN ; ignore seed/manual) + `POST /api/admin/products/bulk-delete {ids}`. UI onglet Produits : bouton « Auditer (hors-niche) » + panneau de sélection/suppression groupée. (Audit réel : 1 suspect sur 27 = « Orchestral Music Stand ».)
- **Fiche avis enrichie** (`ProductReviews.jsx`) : **répartition par note** (barres 5→1), **filtre par note** (Tous/5/4/3/2/1) + **filtre « Avec photos »**, **miniatures photos** cliquables par avis, **drapeau pays** (countryCode). Rendu vérifié.
- **Bannière vitrine Audio** sur l'accueil (`AudioBanner` dans Home.jsx, après Categories) : visuel sombre premium + CTA « Découvrir l'Audio » → /shop?category=audio. Vérifié.
### LOT 1 — Comparateur (catégorie + specs) & Espace client (coordonnées + messagerie) — 2026-06
Livré et testé (iteration 10 : 6/6 pytest backend + 100% frontend, aucun bug).
- **Comparateur** : contrainte **même catégorie** (CompareContext stocke {id,category}, toast si catégorie différente) + section **« Caractéristiques techniques »** (specs CJ). `cj.py extract_specs()` (nettoyage listes JSON, filtre valeurs non latines/junk) → Poids/Emballage/Catégorie/Matière/Unité. Endpoint admin `POST /api/admin/products/{id}/sync-specs` + bouton « Specs CJ » par produit. Specs stockées à l'import CJ + exposées dans `/api/products/{id}`.
- **Espace client** : `GET/PUT /api/account/profile` (nom, téléphone, adresse, ville, CP, pays ; email lecture seule) — formulaire « Mes coordonnées ». `POST /api/account/message` → contact `source=client` + notif Brevo — formulaire « Contacter la direction ».
- **Réponse admin** : `POST /api/admin/contacts/{id}/reply` (email Brevo + thread stocké). UI Messages : badge « Client », bouton Répondre. NB : Brevo peut renvoyer `sent=false` en preview → réponse quand même enregistrée.


- **Page vitrine standalone** `/app/frontend/src/pages/PublicStore.jsx`, route `/b/:slug` (hors Layout principal) : header/hero/grille/footer entièrement **thématisés** par la couleur d'accent de la boutique, nom + tagline, badges promo, panier partagé Invovix, SEO (title/description/OG) par boutique, filtres catégories. Feeling « boutique totalement différente » sur une seule base de code.
- **Détection par domaine** (`DomainGate` dans App.js) : en production, un visiteur sur `maison.invovix.store` voit automatiquement la vitrine dédiée (résolue via `GET /api/public/store-resolve?host=`). Les domaines primaires (invovix.store, preview, localhost) rendent le site principal. En preview : accès direct `/b/:slug`.
- Backend : endpoint `GET /api/public/store-resolve` ajouté à `stores.py`. Boutique démo « Invovix Maison » (slug `invovix-maison`, domaine `maison.invovix.store`, accent vert, catégorie smart-home) créée pour SEO par niche.
- VÉRIFIÉ : vitrine `/b/invovix-maison` (13 produits, thème vert) + site principal intact (screenshots).


- **Phase 4 (reste)** : GraphQL + webhooks sortants avancés (mod 25). ✅ multi-boutiques (mod 19) et gestion documentaire (mod 24) faits en Phase 5.
- **Phase 3 (reste)** : Notifications SMS/WhatsApp via Twilio (attente clés) ; push web.
- **Phase 2 (reste)** : import CSV/Excel/URL de produits (module 3).
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
