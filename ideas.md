# Ideas v2

- Création de ligue custom : possibilité de créer ses propres match, propres équipes, propres résultats. En fait on devrait même pouvoir créer une compétition custom, et autant de ligue branchées sur ces compétitions->Angle collaboratif, chacun peut créer une compétition custom, et n'importe qui créer sa ligue sur cette compétition-> ouverture à tout type de pari
- Visualisation des résultats sous forme de tableau, avec uniquement son score. Ligne accordéon, si on clique, on accède à tout
- Visualisation des paris sous forme de tableau : on peut parier sur chaque match, ou sur tous les matchs d'un coup
- Tous les paris sont listés les uns après les autres en fonction de la date de démarrage du match. On peut filtrer par ligue/compétition

### Catégories accessibles depuis la page d'accueil
- Paris
- Résultats: détails de tous les matchs passés 
- Classement: classement sur les différentes ligues. Ça peut aussi être sous la forme d'un tableau/accordéon. De base t'as ta liste de ligues avec ton classement sur chacune des ligues (3/5)


Chacune des vues ci-dessus pour reprendre exactement la même formule:
- quelques filtres 
- un tableau/accordéon 


Depuis le menu User
- Gérer mes ligues : pour se desinscrire/supprimer des ligues/s'inscrire à de nouvelles Ligue/récupérer un lien de connexion à partager 
- Gérer mes compétitions : créer une nouvelle compétition, modifier les matchs, ajouter des matchs, indiquer les scores. Date/heure sont obligatoires pour chaque match. On doit aussi pouvoir créer des équipes 
- Gérer mes équipes : impossible de supprimer une équipe engagée dans une compétition 

### Création de ligue 

#### Choix de competition
- possibilité de choisir une compétition "officielle" 
- possibilité de choisir parmi les compétitions créées par des utilisateurs : affichage du nom, de l'activité, du nombre de ligues lancées sur cette compétition
- possibilité de créer une compétition custom 

#### Choix des règles
- activer les bonus "enjeu" : poule->pas de multiplicateur, huitième de finales -> multiplication des points par 1+1/8=1.125... 
- activer les bonus "parfait" : 0/20/50/100
- score avant/après prolongation 

#### Définition du nom

#### Récupération lien de connexion 
- récupération du lien de connexion (besoin d'obfusquer le lien) + code user

Je pense que le lien doit contenir une clé générée automatiquement à la création de la ligue 

### Création de competition custom 

#### Définition du nom et de l'activité 
- le choix de l'activité permettra de filtrer les équipes accessibles, et de faciliter le process de création de ligue en permettant d'identifier compétitions en fonction de leur type
- les pays et les équipes custom seront toujours accessibles pour toutes les compétitions
- on peut créer une compétion de type "mixed" : dans ce cas, toutes les équipes sont accessibles 

#### Sélection des équipes 
- possibilité de choisir des équipes qui existent déjà 
- possibilité de créer des équipes ultra facilement dans le même écran

Trop compliqué techniquement de passer la liste des équipes dans le contexte... Passer par un  Modal de création d'équipe depuis la page de définition des match. 
Une fois le modal validé, dans la création de match, on a accès aux équipes "officielles" + équipes "custom". 

Quand on crée une équipe custom, l'activité associée est l'activité pour la compétition choisie. Si on est sur une activité "Mixed", alors l'utilisateur doit choisir à la main l'activité de l'équipe. 

#### Définition des matchs
- Création de match avec choix d'équipes parmi les équipes officielles + custom : select2js, possibilité de classer les équipes par catégories : pays, sport foot, tennis... , custom
- Type de match : poule, 1/64...
- Date et heure du match : obligatoire car sinon pas de pari possible. Indiquer la raison et préciser que si la date n'est pas encore connue, il faut mettre une date dans le futur qu'il faudra modifier ensuite 

### Modification des `Models`
- competition
 - c'est la compétition qui pointe vers les différents matchs. Chaque match pointe vers des équipes. 

- activity: propriété d'une équipe et d'une compétition : foot, tennis... Lorsqu'on crée une compétition et qu'on doit choisir les équipes, on a la liste des équipes nationales + celles de l'activité de la compétition. Il faut modifier le model `team` pour ajouter des paramètres `type`=country, official, custom et `activity`=le type d'activité, nulle si type==country. Pour le model `competition` on a aussi un champ type=official, custom. Ainsi qu'un champ activity forcément renseigné (qui peut être mixed et/ou autre) et aussi un champ owner si c'est custom. Faudrait trouver une nomenclature des types d'activités : typiquement sur XYYY, X le macro type sport=1, e-sport=2, YYY le micro type, foot = 001, fifa = 001...

- game : type de match (poule, 1/2...) pour application des bonus 

### Business/Community
- tout le monde peut ajouter et partager ses équipes gratuitement avec une limite de : maximum 15 joueurs par ligue, maximum 2 ligues par équipe 
- une entité peut payer pour ajouter son tournoi dans la liste des tournois "officiels" 
- une équipe peut payer pour ajouter son équipe dans la liste des équipes "officielles" 

### RGPD!!! 

### Oubli mot de passe 