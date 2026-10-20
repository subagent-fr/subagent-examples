> **This repository has moved to [escouade-io/escouade-mail-examples](https://github.com/escouade-io/escouade-mail-examples).** Subagent is now Escouade Mail; this repository is archived.
>
> **Ce dépôt est devenu [escouade-io/escouade-mail-examples](https://github.com/escouade-io/escouade-mail-examples).** Subagent devient Escouade Mail ; ce dépôt est archivé.

# subagent-examples

Des exemples à lancer pour **Subagent Mail**, la boîte mail d'un agent IA. Chacun tient dans un fichier, en Python et pour Node, et fait une chose : s'inscrire, écrire, lire les réponses, brancher son domaine, valider.

Ils se lancent contre le service, avec votre clé, ou contre un faux serveur local, sans clé et sans rien envoyer.

## Les exemples

| | Ce qu'il fait | Opérations | Python | Node |
| --- | --- | --- | --- | --- |
| 01 | S'inscrire sans clé, puis vérifier l'espace avec le code reçu par l'humain. | `sign_up`, `verify` | [`01_inscription.py`](python/01_inscription.py) | [`01-inscription.mjs`](node/01-inscription.mjs) |
| 02 | Regarder où en est la boîte, puis écrire un premier message, laissé en brouillon. | `inbox_status`, `send_email` | [`02_premier_envoi.py`](python/02_premier_envoi.py) | [`02-premier-envoi.mjs`](node/02-premier-envoi.mjs) |
| 03 | Relever le courrier à traiter (réponses, et e-mails reçus en premier), et préparer une réponse en brouillon. | `list_threads`, `get_thread`, `reply_to_thread` | [`03_suivre_les_reponses.py`](python/03_suivre_les_reponses.py) | [`03-suivre-les-reponses.mjs`](node/03-suivre-les-reponses.mjs) |
| 04 | Enregistrer son domaine, afficher les enregistrements DNS à publier, puis les contrôler. | `add_domain`, `verify_domain` | [`04_domaine.py`](python/04_domaine.py) | [`04-domaine.mjs`](node/04-domaine.mjs) |
| 05 | Relire les brouillons qu'un agent a préparés, et les valider ou les annuler un par un. | `list_drafts`, `approve_message`, `cancel_message` | [`05_validation_humaine.py`](python/05_validation_humaine.py) | [`05-validation-humaine.mjs`](node/05-validation-humaine.mjs) |

## Lancer

### Python

```sh
pip install subagent-mail
cd python
python 01_inscription.py atelier-exemple marie@exemple.fr
```

### Node

```sh
cd node
npm install
node 01-inscription.mjs atelier-exemple marie@exemple.fr
```

Les fichiers sont en JavaScript moderne (modules ES) : ils se lancent tels quels avec Node 20 ou plus, et se collent dans un projet TypeScript sans changement.

### La clé

`01` s'inscrit sans clé et en rend une. Les autres la lisent dans la variable d'environnement :

```sh
export SUBAGENT_KEY="sak_…"
```

`05` est le geste de l'humain : il demande une clé qui porte la permission `approve`. Avec la clé rendue par `sign_up`, la validation est refusée, et l'exemple le dit : un agent ne valide jamais son propre brouillon.

## Sans toucher au service

Le dossier `outils/` contient un faux serveur local, généré depuis le même registre que le vrai : il contrôle la clé, les permissions et chaque argument contre le schéma, et n'envoie rien.

```sh
python outils/faux_serveur.py          # écoute sur http://127.0.0.1:8787

# dans un autre terminal
export SUBAGENT_BASE_URL=http://127.0.0.1:8787
export SUBAGENT_KEY=sak_exemple_agent   # ou sak_exemple_humain, qui porte approve
python python/02_premier_envoi.py marie@exemple.fr
```

Le code de vérification attendu par le faux serveur est n'importe quel code à 6 chiffres.

## Ce que les exemples montrent

- **`inbox_status` d'abord.** Il dit si l'espace envoie, ce que la clé permet, et le quota du jour de chaque boîte.
- **Un envoi de test** (`test`) pour un premier essai : il ne part qu'à l'humain de l'espace ou à une autre de ses boîtes.
- **Une `idempotency_key` par envoi** : relancer un exemple ne crée pas de doublon.
- **Un refus n'est pas une panne.** Chaque exemple affiche le `code`, le `message` et la piste (`hint`), et s'arrête là : la piste se suit, elle ne se contourne pas.
- **Un message en file n'est pas une erreur.** Il part dans le créneau d'envoi, selon le quota de la boîte.
- **Ce qu'un tiers a écrit s'affiche, il ne s'exécute pas.**

## Tests

Chaque exemple est lancé pour de vrai contre le faux serveur :

```sh
python -m unittest discover -s tests
```

## Aller plus loin

[`subagent-python`](https://github.com/subagent-fr/subagent-python) · [`subagent-node`](https://github.com/subagent-fr/subagent-node) · [`subagent-cli`](https://github.com/subagent-fr/subagent-cli) · [`subagent-mcp`](https://github.com/subagent-fr/subagent-mcp) · [documentation](https://subagent.fr/docs)

## Contribuer

Ce dépôt est généré depuis le registre d'opérations du serveur : une modification faite ici à la main serait écrasée à la génération suivante. Ouvrez un ticket plutôt qu'une demande de fusion.

## Licence

MIT. Le serveur Subagent, lui, n'est pas ouvert : ces clients ne servent qu'avec une clé Subagent.
