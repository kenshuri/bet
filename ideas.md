# Ideas v2

- Création de ligue custom : possibilité de créer ses propres match, propres équipes, propres résultats. En fait on devrait même pouvoir créer une compétition custom, et autant de ligue branchées sur ces compétitions->Angle collaboratif, chacun peut créer une compétition custom, et n'importe qui créer sa ligue sur cette compétition-> ouverture à tout type de pari
- Visualisation des résultats sous forme de tableau, avec uniquement son score. Ligne accordéon, si on clique, on accède à tout
- Visualisation des paris sous forme de tableau : on peut parier sur chaque match, ou sur tous les matchs d'un coup
- Tous les paris sont listés les uns après les autres en fonction de la date de démarrage du match. On peut filtrer par ligue/compétition

### Catégories accessibles depuis la page d'accueil
- Mes Paris
- Résultats: détails de tous les matchs passés 
- Classement: classement sur les différentes ligues. Ça peut aussi être sous la forme d'un tableau/accordéon. De base t'as ta liste de ligues avec ton classement sur chacune des ligues (3/5)

Depuis le menu User :
- Gérer mes ligues : pour se desinscrire/supprimer des ligues/s'inscrire à de nouvelles Ligue 
- Gérer mes compétitions : créer une nouvelle compétition, modifier les matchs, ajouter des matchs, indiquer les scores. Date/heure sont obligatoires pour chaque match. On doit aussi pouvoir créer des équipes 
- Gérer mes équipes 

### Création de ligue 

#### Choix du tournament 
- possibilité de choisir un tournament qui existe déjà 
- possibilité de créer un tournament custom 

#### Choix des règles
- activer les bonus "enjeu" : poule->pas de multiplicateur, huitième de finales -> multiplication des points par 1+1/8=1.125... 
- activer les bonus "parfait" : 0/20/50/100
- score avant/après prolongation 

#### Création de tournament custom 

##### Sélection des équipes 
- possibilité de choisir des équipes qui existent déjà 
- possibilité de créer des équipes ultra facilement dans le même écran 

##### Définition des matchs


### Modification des `Models`
- tournament
 - c'est le tournoi qui pointe vers les différents matchs. Chaque match pointe vers des équipes. 

- activity: propriété d'une équipe : équipe de foot, de tennis... L'activité d'un match est définie en fonction de l'activité des deux équipes 

### Business/Community
- tout le monde peut ajouter et partager ses équipes gratuitement avec une limite de : maximum 15 joueurs par ligue, maximum 2 ligues par équipe 
- une entité peut payer pour ajouter son tournoi dans la liste des tournois "officiels" 
- une équipe peut payer pour ajouter son équipe dans la liste des équipes "officielles" 

### RGPD!!! 