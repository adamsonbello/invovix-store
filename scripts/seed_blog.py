import os, requests, json

API = os.environ.get("SEED_API", "http://localhost:8001/api")
EMAIL = "admin@invovix.store"
PASSWORD = "Invovix2026!"

def main():
    r = requests.post(f"{API}/auth/login", json={"email": EMAIL, "password": PASSWORD})
    r.raise_for_status()
    token = r.json()["token"]
    h = {"Authorization": f"Bearer {token}"}

    posts = [
        {
            "title": "5 gadgets domotiques indispensables pour 2026",
            "excerpt": "De l'éclairage intelligent aux prises connectées, découvrez les 5 objets qui transforment vraiment le quotidien d'une maison connectée.",
            "cover_image": "/blog/blog-smarthome.jpg",
            "tags": ["Domotique", "Maison connectée"],
            "published": True,
            "content": """
<h2>La maison connectée n'est plus un luxe</h2>
<p>En 2026, équiper son intérieur d'objets connectés est devenu à la fois abordable et incroyablement pratique. Voici notre sélection des 5 essentiels pour démarrer.</p>
<h3>1. L'éclairage intelligent</h3>
<p>Contrôlez l'ambiance de chaque pièce depuis votre smartphone ou à la voix. Programmez des scénarios pour le réveil, le cinéma ou le coucher.</p>
<h3>2. Les prises connectées</h3>
<p>Transformez n'importe quel appareil en objet pilotable à distance. Idéal pour éteindre la machine à café oubliée ou suivre sa consommation d'énergie.</p>
<h3>3. Le thermostat intelligent</h3>
<p>Réduisez votre facture de chauffage jusqu'à 20% grâce à un apprentissage automatique de vos habitudes.</p>
<h3>4. Le capteur d'ouverture</h3>
<p>Recevez une alerte dès qu'une porte ou une fenêtre s'ouvre. Simple, discret et rassurant.</p>
<h3>5. L'assistant vocal</h3>
<p>Le chef d'orchestre de votre maison : il relie tous vos appareils et répond à vos commandes en un instant.</p>
<blockquote>Commencez petit, puis étendez votre écosystème pièce par pièce.</blockquote>
"""
        },
        {
            "title": "Aménager un bureau de télétravail ergonomique",
            "excerpt": "Un espace de travail bien pensé booste la productivité et préserve votre santé. Nos conseils pour un home office parfait.",
            "cover_image": "/blog/blog-remote.jpg",
            "tags": ["Télétravail", "Ergonomie"],
            "published": True,
            "content": """
<h2>Le télétravail mérite un vrai espace</h2>
<p>Travailler depuis chez soi est confortable, à condition d'avoir un poste adapté. Voici comment créer un environnement à la fois sain et inspirant.</p>
<h3>La posture avant tout</h3>
<p>Écran à hauteur des yeux, coudes à 90°, pieds à plat : ces réflexes évitent les douleurs cervicales et lombaires sur le long terme.</p>
<h3>Une lumière maîtrisée</h3>
<p>Privilégiez la lumière naturelle et complétez avec un éclairage LED réglable en température pour réduire la fatigue oculaire.</p>
<h3>Le bon matériel connecté</h3>
<p>Support d'écran ajustable, station de charge sans fil et éclairage d'ambiance transforment un simple coin en véritable bureau professionnel.</p>
<blockquote>Un espace ordonné, c'est un esprit plus clair.</blockquote>
"""
        },
        {
            "title": "Sécuriser sa maison connectée : le guide complet",
            "excerpt": "Caméras, capteurs et bonnes pratiques : tout ce qu'il faut savoir pour protéger votre foyer et vos données.",
            "cover_image": "/blog/blog-security.jpg",
            "tags": ["Sécurité", "Maison connectée"],
            "published": True,
            "content": """
<h2>Protéger son domicile intelligemment</h2>
<p>La sécurité connectée offre une tranquillité d'esprit inédite. Encore faut-il choisir les bons équipements et adopter les bons réflexes.</p>
<h3>Les caméras intelligentes</h3>
<p>Détection de mouvement, vision nocturne et alertes en temps réel : gardez un œil sur votre maison où que vous soyez.</p>
<h3>Les capteurs de sécurité</h3>
<p>Ouverture de porte, fumée, fuite d'eau : ces petits capteurs préviennent les incidents avant qu'ils ne s'aggravent.</p>
<h3>Protéger vos données</h3>
<p>Activez l'authentification à deux facteurs, mettez à jour vos appareils et privilégiez les marques transparentes sur le chiffrement.</p>
<blockquote>La meilleure sécurité combine technologie et bon sens.</blockquote>
"""
        },
    ]

    for p in posts:
        resp = requests.post(f"{API}/admin/blog", headers=h, json=p)
        print(resp.status_code, resp.json().get("slug") if resp.ok else resp.text)

if __name__ == "__main__":
    main()
