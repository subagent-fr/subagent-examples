// Enregistrer son domaine, afficher les enregistrements DNS à publier, puis les contrôler.
//
//     export SUBAGENT_KEY="sak_…"
//     node 04-domaine.mjs agents.exemple.fr
//
// Lancez-le une première fois pour obtenir les enregistrements, publiez-les chez l'hébergeur DNS
// du domaine, puis relancez-le : il dit, enregistrement par enregistrement, ce qui est en place.

import { Subagent, SubagentError } from "subagent-mail";

const nom = process.argv[2];
if (!nom) {
  console.error("Usage : node 04-domaine.mjs <domaine>");
  process.exit(2);
}

const ETATS = { found: "en place", missing: "absent", different: "valeur différente" };

const client = new Subagent(); // lit SUBAGENT_KEY ; la clé doit porter manage_inboxes

try {
  try {
    await client.addDomain({ domain: nom });
    console.log("Domaine enregistré. Publiez les enregistrements ci-dessous, puis relancez ce script.");
  } catch (erreur) {
    // Déjà enregistré pour cet espace : on passe au contrôle.
    if (!(erreur instanceof SubagentError) || erreur.code !== "domain_exists") throw erreur;
  }

  const domaine = await client.verifyDomain({ domain: nom });
  console.log(`Domaine ${domaine.domain} : ${domaine.status}`);
  for (const enregistrement of domaine.records ?? []) {
    const etat = enregistrement.state ? ETATS[enregistrement.state] : "pas encore contrôlé";
    console.log(`\n  ${enregistrement.label} (${enregistrement.type}, ${enregistrement.required ? "exigé" : "conseillé"}) : ${etat}`);
    console.log(`    Nom    : ${enregistrement.name}`);
    console.log(`    Valeur : ${enregistrement.value}`);
    if (enregistrement.seen) console.log(`    Vu     : ${enregistrement.seen}`);
    if (enregistrement.note) console.log(`    Note   : ${enregistrement.note}`);
  }
  console.log(
    domaine.status === "verified"
      ? "\nDomaine vérifié : créez-y une boîte avec createInbox."
      : "\nPas encore vérifié. Un changement de DNS met parfois quelques minutes à se voir.",
  );
} catch (erreur) {
  if (!(erreur instanceof SubagentError)) throw erreur;
  console.error(`Refusé (${erreur.code}) : ${erreur.message}\n→ ${erreur.hint ?? ""}`);
  process.exit(1);
}
