// S'inscrire sans clé, puis vérifier l'espace avec le code reçu par l'humain.
//
//     node 01-inscription.mjs atelier-exemple marie@exemple.fr
//
// Rend une clé (affichée une seule fois) et une boîte sur le domaine commun d'essai. L'humain
// reçoit un code à 6 chiffres par e-mail : le script le demande, puis ouvre l'envoi.

import { createInterface } from "node:readline";

import { Subagent, SubagentError } from "subagent-mail";

const terminal = createInterface({ input: process.stdin });
const lignes = terminal[Symbol.asyncIterator](); // ouvert dès maintenant : une réponse tapée d'avance n'est pas perdue

/** Pose une question et rend la ligne tapée (vide si l'entrée est fermée). */
async function demander(question) {
  process.stdout.write(question);
  const { value } = await lignes.next();
  return (value ?? "").trim();
}

const [username, humanEmail] = process.argv.slice(2);
if (!username || !humanEmail) {
  console.error("Usage : node 01-inscription.mjs <nom-de-la-boîte> <e-mail-de-l'humain>");
  process.exit(2);
}

/** Affiche un refus du serveur et s'arrête ; relance toute autre erreur. */
function arreter(erreur, quoi) {
  if (!(erreur instanceof SubagentError)) throw erreur;
  console.error(`${quoi} (${erreur.code}) : ${erreur.message}\n→ ${erreur.hint ?? ""}`);
  process.exit(1);
}

const client = new Subagent({ apiKey: "" }); // sans clé : seule sign_up est ouverte

const inscription = await client
  .signUp({ username, human_email: humanEmail })
  .catch((erreur) => arreter(erreur, "Inscription refusée"));

console.log("Boîte :", inscription.inbox?.address);
console.log("Clé, affichée une seule fois :", inscription.api_key);
console.log('Rangez-la : export SUBAGENT_KEY="…"');

if (!inscription.code_sent) {
  console.log("Aucun code n'est parti : la boîte reçoit, mais n'enverra qu'après attach_human puis verify.");
} else {
  // Le client garde la clé rendue par sign_up : les appels suivants passent avec elle.
  const code = await demander(`Code à 6 chiffres reçu par ${inscription.human_email} : `);
  await client.verify({ otp_code: code }).catch((erreur) => arreter(erreur, "Vérification refusée"));
  console.log("Espace vérifié : l'envoi est ouvert.");
}
terminal.close();
