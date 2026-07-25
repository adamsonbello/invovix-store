# Invovix — Structure du projet (à jour, 2026-06)

## Stack
React (CRA) + Tailwind + Framer Motion + Lenis · FastAPI + Motor (MongoDB) · Intégrations : CJDropshipping, Stripe, PayPal, Brevo, Google reCAPTCHA v3, Google Tag Manager.

```
/app
├── backend/
│   ├── server.py        # App FastAPI + routes /api (auth, produits, commandes, avis,
│   │                    #   blog, upload, contact, newsletter, sitemap/robots,
│   │                    #   anti-spam reCAPTCHA/rate-limit, webhook Stripe, admin CJ & orders)
│   ├── database.py      # Connexion Motor (MONGO_URL, DB_NAME)
│   ├── security.py      # JWT, hash mots de passe, get_current_user / require_admin
│   ├── cj.py            # Intégration CJDropshipping : token, search, import produit,
│   │                    #   create_cj_order (createOrderV2), get_cj_order (suivi)
│   ├── payments.py      # Stripe Checkout + PayPal (create/capture) → déclenche fulfillment
│   ├── fulfillment.py   # handle_paid_order (email confirmation + création commande CJ)
│   │                    #   + sync_cj_order (récup. suivi + email expédition)
│   ├── brevo.py         # Emails : confirmation, expédition/suivi, avis, contact
│   ├── extras.py        # settings (bannière/WhatsApp), related, avis vedettes,
│   │                    #   wishlist, codes promo
│   ├── requirements.txt
│   └── .env             # MONGO_URL, DB_NAME, CJ_API_KEY, STRIPE/PAYPAL, BREVO,
│                        #   RECAPTCHA_SECRET_KEY, FRONTEND_URL, (CJ_* fulfillment opts)
│
├── scripts/
│   ├── seed_blog.py     # Seed 3 articles de blog de démo
│   └── seed_cj.py       # Seed catalogue depuis CJ (recherche + import en masse)
│
├── frontend/
│   ├── public/
│   │   ├── index.html   # + Google Tag Manager (GTM-KZBXP887)
│   │   ├── products/    # Images produits téléchargées en local (anti-hotlinking)
│   │   └── blog/        # Images blog / cover uploadées
│   └── src/
│       ├── App.js       # Routes + Providers (Auth, Cart, Wishlist)
│       ├── i18n.js      # Traductions FR/EN (source unique)
│       ├── index.js
│       ├── context/     # AuthContext, CartContext (+ promo/discount), WishlistContext
│       ├── lib/         # api.js (axios), recaptcha.js, utils.js
│       ├── data/        # legal.js (contenu CGV / mentions / confidentialité FR-EN)
│       ├── components/
│       │   ├── Layout, Header, Footer, PromoBanner, WhatsAppButton,
│       │   │   NewsletterPopup, CookieConsent, SearchModal
│       │   ├── ProductCard, RelatedProducts, ProductReviews, StarRating
│       │   ├── BlogEditor (react-quill-new), SEO, ProtectedRoute
│       │   └── ui/       # 46 composants shadcn/ui
│       └── pages/
│           ├── Home, Shop, ProductDetail, Cart, Checkout,
│           │   PaymentSuccess, PaymentCancel
│           ├── Login, Register, Account (+ suivi commande), Wishlist
│           ├── Blog, BlogPost, Contact, FAQ, Legal
│           └── Admin (onglets : Produits, Commandes+Fulfillment,
│                       Import CJ, Blog, Messages, Codes promo, Réglages)
│
└── memory/              # PRD.md, CHANGELOG/ROADMAP, STRUCTURE.md, test_credentials.md
```

## Endpoints backend clés (préfixe /api)
- Auth : /auth/register, /auth/login
- Catalogue : /products, /products/{id}, /products/{id}/related
- Commandes : /orders, /admin/orders, /admin/orders/{id}/status,
  /admin/orders/{id}/fulfill, /admin/orders/{id}/sync-cj
- Paiement : /payments/stripe/*, /payments/paypal/*, /webhook/stripe
- Contenu : /blog, /admin/blog, /admin/upload, /reviews, /reviews/featured
- Marketing : /promo/validate, /admin/promos, /settings, /admin/settings, /newsletter, /contact
- CJ admin : /admin/cj/status, /admin/cj/search, /admin/cj/import-bulk
- SEO : /sitemap.xml, /robots.txt
