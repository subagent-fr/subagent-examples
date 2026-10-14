// Relire les brouillons qu'un agent a préparés, et les valider ou les annuler un par un.
//
//     export SUBAGENT_KEY="sak_…"      (la clé d'un humain : elle doit porter approve)
//     node 05-validation-humaine.mjs
//
// C'est le geste de l'humain. Avec la clé d'un agent, la validation est refusée (forbidden) :
// un agent ne valide jamais son propre brouillon.

import { createInterface } from "node:readline";

import { Subagent, SubagentError } from "subagent-mail";

const client = new Subagent(); // lit SUBAGENT_KEY
const terminal = createInterface({ input: process.stdin });
const lignes = terminal[Symbol.asyncIterator](); // ouvert dès maintenant : une réponse tapée d'avance n'est pas perdue
let code = 0;

/** Pose une question et rend la ligne tapée (vide si l'entrée est fermée). */
async function demander(question) {
  process.stdout.write(question);
  const { value } = await lignes.next();
  return (value ?? "").trim();
}

try {
  const { items: brouillons = [] } = await client.listDrafts();
  if (brouillons.length === 0) console.log("Aucun brouillon à valider.");

  for (const brouillon of brouillons) {
    if (!brouillon.id) continue;
    console.log(`\n${brouillon.id}`);
    console.log(`De    : ${brouillon.from}`);
    console.log(`À     : ${brouillon.to}`);
    if (brouillon.reply_to) console.log(`Répondre à : ${brouillon.reply_to}`);
    console.log(`Sujet : ${brouillon.subject}`);
    console.log(`\n${brouillon.text ?? ""}\n`);
    if (brouillon.has_html) console.log("(ce message a aussi une version HTML)");

    const choix = (await demander("Valider (o), annuler (a), passer (entrée) ? ")).toLowerCase();
    try {
      if (choix === "o") {
        // `revision` : la validation ne vaut que pour le texte qui vient d'être lu.
        const valide = await client.approveMessage({ message_id: brouillon.id, revision: brouillon.revision });
        console.log(`Validé : ${valide.status}. Il partira dans le créneau, selon le quota de la boîte.`);
      } else if (choix === "a") {
        await client.cancelMessage({ message_id: brouillon.id, reason: "Refusé à la relecture." });
        console.log("Annulé.");
      }
    } catch (erreur) {
      if (!(erreur instanceof SubagentError)) throw erreur;
      console.log(`Refusé (${erreur.code}) : ${erreur.message}\n→ ${erreur.hint ?? ""}`);
      if (erreur.code === "forbidden") {
        code = 1;
        break;
      }
    }
  }
} catch (erreur) {
  if (!(erreur instanceof SubagentError)) throw erreur;
  console.error(`Refusé (${erreur.code}) : ${erreur.message}\n→ ${erreur.hint ?? ""}`);
  code = 1;
} finally {
  terminal.close();
}
process.exitCode = code;
