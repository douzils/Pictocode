# Pictocode

Pictocode est une application permettant de composer visuellement des formes pour ensuite générer du code. Son interface rappelle les logiciels de dessin comme Illustrator.

Ce dépôt contient **l'intégralité du code source** de l'application. Les modules Python se trouvent dans le package `pictocode` et implémentent l'ensemble des fonctionnalités décrites ci-dessous.

## Fonctionnalités principales

### Écran d'accueil
- Interface modernisée avec en‑tête coloré.
- Bouton **Nouveau projet** pour créer un canvas vierge.
- Liste des projets sauvegardés dans le dossier `Projects` avec icônes.
- Liste de modèles et formats disponibles (double-cliquez pour préremplir la création de projet).
- Recherche instantanée pour retrouver rapidement un projet existant.

### Création d'un projet
- Fenêtre de création avec choix du nom, des dimensions et de l'unité.
- Orientation portrait ou paysage.
- Mode couleur (RGB, CMJN ou niveaux de gris).
- Résolution en DPI.

### Barre de menu
- **Fichier** : nouveau projet, ouvrir, enregistrer, enregistrer sous, retour à l'accueil et quitter l'application.
- **Projet** : paramètres du projet en cours.
- **Préférences** : réglages généraux et apparence (thème clair ou sombre).

### Fenêtre de paramètres
- **Général** : choix de la langue.
- **Apparence** : personnalisation fine de l'interface. Chaque zone (menu, barre d'outils, inspecteur) peut
  avoir sa propre couleur d'accent et sa taille de police.

### Dans un projet
- Canvas avec grille optionnelle et magnétisme. La grille s'adapte à
  l'échelle de zoom pour conserver un espacement lisible.
- Outils : rectangle, ellipse, ligne, polygone, tracé libre, texte, sélection et gomme.
- Choix de la couleur des formes.
- Clic droit sur une forme pour modifier couleur, remplissage ou bordure.
- Zoom à la molette et déplacement (pan). Un clic molette permet de
  déplacer temporairement la vue.
- Inspecteur pour modifier position, taille et couleur de l'objet sélectionné.
- Sauvegarde du projet au format JSON et génération de code Python.

### Fonctionnalités avancées inspirées de Canvas et Illustrator

#### Dessin et création de formes
- Tracer des lignes droites
- Tracer des polygones (manuellement ou avec outils)
- Tracer des rectangles, carrés
- Tracer des cercles, ellipses, arcs
- Créer des courbes de Bézier (quadratiques, cubiques)
- Tracer des spirales, étoiles, polygones à n côtés
- Définir des chemins personnalisés (suite de lignes et courbes)
- Combiner des formes (ajout, soustraction, intersection, exclusion)
- Découper des formes avec des outils (couteau, ciseaux)
- Tracer librement à la main (plume, crayon, pinceau)
- Créer des grilles de dégradé
- Déformer des formes (gonfler, torsion, enveloppe, maillage, filet de dégradé)

#### Couleurs, styles et remplissage
- Remplir avec une couleur unie
- Remplir avec un dégradé linéaire
- Remplir avec un dégradé radial ou circulaire
- Remplir avec un motif image
- Remplir avec des motifs vectoriels personnalisés
- Modifier l'épaisseur des traits
- Modifier la forme des extrémités des lignes (rond, carré, pointu)
- Modifier la jonction des lignes (biseau, arrondi, pointu)
- Appliquer des ombres et lueurs
- Appliquer des modes de fusion (superposition, multiplication, écran, etc.)
- Gérer l'opacité globale
- Appliquer plusieurs apparences sur un même objet
- Peinture dynamique pour remplir automatiquement les zones fermées

#### Texte
- Ajouter du texte libre
- Ajouter du texte dans une forme
- Ajouter du texte suivant un chemin
- Changer la police, la taille et la couleur
- Aligner le texte (gauche, centre, droite)
- Appliquer des styles de texte (paragraphe, caractère)
- Utiliser les glyphes et fonctions OpenType
- Déformer du texte (arc, drapeau, poisson, etc.)

#### Transformations et déplacements
- Déplacer des objets
- Tourner des objets
- Redimensionner ou mettre à l'échelle
- Incliner ou déformer
- Répéter des objets (grille, radiale, miroir)
- Travailler en perspective
- Appliquer des transformations combinées

#### Gestion d'images et pixels
- Afficher une image
- Lire et modifier les pixels d'une image
- Importer des images bitmap dans le dessin
- Incorporer ou lier des images

#### Effets et filtres
- Ombres portées
- Lueurs internes et externes
- Flou (directionnel, gaussien)
- Déformations (zigzag, ondulation, drapé)
- Effets 3D (extrusion, révolution)
- Trame, mosaïque
- Combinaisons d'effets multiples

#### Précision et aides
- Grilles visibles
- Repères magnétiques et guides
- Outils d'alignement et de distribution
- Outil de mesure (distances, angles)
- Outil largeur pour varier l'épaisseur d'un trait

#### Animation et dynamisme
- Créer des animations via `requestAnimationFrame`
- Préparer des fichiers pour animation (plans de travail, séquences)

#### Symboles et réutilisabilité
- Créer des symboles réutilisables
- Réutiliser des chemins pré-enregistrés
- Utiliser des bibliothèques partagées

#### Export et import
- Exporter au format image (PNG, JPEG)
- Exporter en SVG, PDF, EPS, PNG, JPG
- Exporter pour le web, l'impression ou la vidéo
- Gérer plusieurs plans de travail
- Effectuer une exportation en lot

#### Automatisation et scripts
- Automatiser des tâches avec des scripts
- Créer des actions enregistrées
- Étendre l'application avec des plugins

#### Autres fonctionnalités diverses
- Masquer des zones avec des masques de découpe
- Combiner des formes via des modes de fusion
- Générer le code pour Pillow avec les variables choisies

#### Sélection et manipulation
- Sélection directe pour manipuler des points ou segments
- Sélection classique pour déplacer des objets entiers
- Lasso pour sélectionner librement
- Cadre de transformation autour de l'objet sélectionné
- Poignées pour redimensionner ou déformer
- Guides de transformation indiquant l'orientation
- Magnétisme à la grille, aux repères ou aux autres objets

#### Transformations interactives
- Déplacement par glisser-déposer
- Redimensionnement via les poignées
- Rotation avec une poignée dédiée
- Inclinaison avec l'outil de transformation manuelle
- Miroir ou symétrie via un outil dédié
- Déformation par enveloppe interactive

#### Aides visuelles et interactives
- Grilles visibles avec magnétisme
- Repères personnalisés pour aligner les objets
- Grilles de perspective pour dessiner en profondeur
- Contours et surlignage des objets sélectionnés
- Poignées de courbe de Bézier visibles
- Points d'ancrage visibles et sélectionnables
- Alignement et distribution automatiques via des panneaux
- Aperçu des formes pendant la transformation

#### Autres outils d'interaction
- Outil largeur pour ajuster l'épaisseur d'un trait
- Outil concepteur de forme pour fusionner ou séparer des zones
- Outil filet de dégradé pour ajouter des points de dégradé
- Outil ciseaux pour couper un chemin
- Outil couteau pour découper un objet

## Installation des dépendances

Pictocode nécessite **Python 3.8 ou plus récent** ainsi que **PyQt5** :

```bash
pip install -r requirements.txt
```

## Lancement de l'application

Deux méthodes sont possibles :

1. Via le module installé :
   ```bash
   python -m pictocode
   ```
2. Ou en exécutant directement `main.py` :
   ```bash
   python main.py
   ```

Ces commandes ouvrent la fenêtre principale de l'éditeur.

### Exporter une image

Depuis un projet ouvert, utilisez le menu **Fichier > Exporter en image…**
pour enregistrer le contenu du canvas au format PNG ou JPEG.

### Exporter en SVG

Le menu **Fichier > Exporter en SVG…** permet d'enregistrer un fichier `.svg`
contenant toutes les formes vectorielles du canvas.

### Exporter le code Python

Utilisez **Fichier > Exporter en code Python…** pour générer un script
`PyQt5` reproduisant les formes de votre projet.

### Personnaliser l'apparence

Dans le menu **Préférences**, vous pouvez choisir le thème (clair ou sombre),
définir une couleur et une taille de police spécifique pour la barre de menu,
la barre d'outils et l'inspecteur. Les menus disposent d'une animation
d'ouverture pour un rendu plus élégant.
