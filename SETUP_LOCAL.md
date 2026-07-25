# 🖥️ Invovix — Installation locale (pas à pas)

Stack : **React** (frontend) · **FastAPI / Python** (backend) · **MongoDB** (base de données).

---

## 0. Prérequis à installer une fois
| Outil | Version | Lien |
|---|---|---|
| Node.js | 18+ | https://nodejs.org |
| Yarn | (via `npm i -g yarn`) | — |
| Python | 3.11+ | https://python.org |
| MongoDB | 6+ (ou compte Atlas gratuit) | https://mongodb.com |
| Git | — | https://git-scm.com |

---

## 1. Récupérer le code
Depuis Emergent : bouton **« Save to GitHub »** → pousse le projet sur votre dépôt GitHub.
Puis sur votre machine :
```bash
git clone https://github.com/<votre-compte>/<votre-repo>.git invovix
cd invovix
```

---

## 2. Base de données MongoDB

### Option A — MongoDB local
- **macOS** : `brew tap mongodb/brew && brew install mongodb-community && brew services start mongodb-community`
- **Ubuntu/Debian** : suivre https://www.mongodb.com/docs/manual/installation/ puis `sudo systemctl start mongod`
- **Windows** : installer « MongoDB Community Server » (le service démarre tout seul).
- URL de connexion : `mongodb://localhost:27017`

### Option B — MongoDB Atlas (cloud gratuit, recommandé)
1. Créez un cluster gratuit sur https://cloud.mongodb.com
2. Database Access → créez un utilisateur/mot de passe.
3. Network Access → autorisez votre IP (ou 0.0.0.0/0 pour test).
4. Récupérez l'URI : `mongodb+srv://user:pass@cluster.xxx.mongodb.net`

---

## 3. Backend (FastAPI)
```bash
cd backend
python -m venv venv
# macOS/Linux :
source venv/bin/activate
# Windows :
venv\Scripts\activate

pip install -r requirements.txt
# La lib Stripe interne d'Emergent nécessite un index supplémentaire :
pip install emergentintegrations --extra-index-url https://d33sy5i8bnduwe.cloudfront.net/simple/
```

Créez le fichier **`backend/.env`** :
```env
MONGO_URL="mongodb://localhost:27017"
DB_NAME="invovix"
CORS_ORIGINS="*"
JWT_SECRET="mettez-une-longue-chaine-aleatoire"
ADMIN_EMAIL="admin@invovix.store"
ADMIN_PASSWORD="Invovix2026!"
STRIPE_API_KEY="sk_test_xxx"
CJ_API_KEY="CJ...votre_cle"
CJ_BASE_URL="https://developers.cjdropshipping.com/api2.0/v1"
PAYPAL_CLIENT_ID="votre_client_id"
PAYPAL_SECRET="votre_secret"
PAYPAL_MODE="sandbox"
BREVO_API_KEY="xkeysib-..."
BREVO_SMTP_KEY=""
BREVO_SMTP_LOGIN=""
BREVO_SENDER_EMAIL="contact@invovix.store"
BREVO_SENDER_NAME="Invovix"
FRONTEND_URL="http://localhost:3000"
```

Lancez le backend :
```bash
uvicorn server:app --reload --host 0.0.0.0 --port 8001
```
> Au 1er démarrage : le compte **admin** et les **8 produits de démo** sont créés automatiquement.
> Les images produits sont dans `frontend/public/products/` (déjà dans le repo).

---

## 4. Frontend (React)
Dans un **2e terminal** :
```bash
cd frontend
yarn install
```

Créez le fichier **`frontend/.env`** :
```env
REACT_APP_BACKEND_URL=http://localhost:8001
WDS_SOCKET_PORT=0
```

Lancez le frontend :
```bash
yarn start
```
Ouvrez http://localhost:3000 🎉

---

## 5. Vérifications
- Boutique : http://localhost:3000
- Admin : http://localhost:3000/admin → `admin@invovix.store` / `Invovix2026!`
- API santé : http://localhost:8001/api/ (doit renvoyer `{"message":"Invovix API"...}`)

---

## 6. Points importants
- **Ports** : backend `8001`, frontend `3000`. Toutes les routes API commencent par `/api`.
- **Import CJ** : Admin → onglet « Import CJ » → recherche → réglez la marge (%) et la catégorie → « Importer » (à l'unité) ou « Tout importer ». Les images CJ sont téléchargées dans `frontend/public/products/`.
- **Emails Brevo** : envoyés quand une commande passe en « delivered » dans l'admin. Désactivez la restriction d'IP dans Brevo si vous changez de serveur.
- **Passage en production (vrais paiements)** : clés **Live** Stripe + compte **Business** PayPal (clés Live), et authentification du domaine `invovix.store` dans Brevo.
