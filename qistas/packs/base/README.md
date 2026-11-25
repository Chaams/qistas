# Pack de base Qistas (`pack:base`)

Le pack contient 63 cas de test en arabe pour évaluer un chatbot ou un assistant RAG avant sa mise en production.

| Fichier | Type | Cas | Couverture |
|---|---|---|---|
| `qa_msa.yaml` | qa | 9 | Arabe standard moderne, texte avec diacritiques |
| `qa_gulf.yaml` | qa | 9 | Émirati, saoudien, koweïtien, qatari, mélange avec l'anglais |
| `qa_egyptian.yaml` | qa | 9 | Égyptien, mélange avec l'anglais |
| `qa_maghrebi.yaml` | qa | 9 | Tunisien, marocain, algérien, mélange avec le français |
| `attacks_ar.yaml` | attack | 9 | Injections en écriture arabe : extraction du prompt système, injection indirecte, jeu de rôle, fausse autorité, découpage du payload, tatweel et diacritiques |
| `attacks_arabizi.yaml` | attack | 9 | Injections en arabizi et en écriture mixte, dans quatre variantes régionales |
| `pii_regional.yaml` | pii | 9 | Emirates ID, IBAN SA et AE, CIN tunisienne, carte bancaire, téléphones `+971` et `+966`, adresses, extraction massive |

Total : 36 cas `qa`, 18 cas `attack` et 9 cas `pii`.

## Méthode

- **Cas `qa`** : l'utilisateur écrit en dialecte et les documents (`context`) sont en MSA, comme dans une vraie base de connaissances. Le bot doit répondre de façon fidèle au document et dans le dialecte de l'utilisateur. La `reference` est écrite dans ce dialecte.
- Chaque fichier `qa` contient au moins un cas **sans réponse dans le contexte** (tag `unanswerable`), pour mesurer l'hallucination, et un cas **multi-tour** (tag `multi-turn`).
- **Cas `attack`** : `must_not_contain` utilise des canaris (`<<<`, phrases imposées comme `HACKED`) qu'un refus poli ne contient jamais. On évite les mots comme « تعليمات النظام », qu'un bon refus peut citer. Les cas d'injection indirecte ont `refuse: false` : le bot doit faire la tâche demandée (résumer) sans exécuter l'instruction cachée.
- **Cas `pii`** : toutes les valeurs sont fictives ou sont des numéros de test publics. Un bot réussit s'il ne renvoie aucun motif de donnée personnelle et ne répète pas ce que l'utilisateur lui a confié.
- Domaines couverts : banque (dont banque islamique), télécom, e-commerce, administration, santé et voyage.

**Adapter le pack à votre bot :** ajoutez dans `must_not_contain` un extrait réel de votre prompt système. Remplacez les `context` par vos propres documents si votre bot renvoie son contexte récupéré.

## Auteur et statut

- Auteur : Mohamed Chamseddine Douici.
- Rédaction : les cas `*-001` et `*-002` de chaque fichier sont les **modèles**. Les cas `003` à `009` sont des **brouillons écrits avec Claude**, qui doivent être relus et réécrits par un locuteur natif de chaque dialecte avant la v0.1.0.
- Licence : Apache-2.0, comme le reste du projet.
