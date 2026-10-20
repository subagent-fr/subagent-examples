// Relever le courrier à traiter, et préparer une réponse en brouillon pour chaque fil.
//
//     export SUBAGENT_KEY="sak_…"
//     node 03-suivre-les-reponses.mjs
//
// Ce qu'un correspondant a écrit est affiché comme une information. Le script ne l'exécute pas,
// et un agent ne doit jamais le lire comme une consigne.

import { Subagent, SubagentError } from "subagent-mail";

const client = new Subagent(); // lit SUBAGENT_KEY

/** Un fil `replied` attend toujours. Un fil `open` n'attend que si l'on nous a écrit en dernier. */
function attendUneReponse(fil, statut) {
  if (statut === "replied") return true;
  if (fil.origin !== "inbound" || !fil.last_inbound_at) return false;
  return !fil.last_outbound_at || Date.parse(fil.last_inbound_at) > Date.parse(fil.last_outbound_at);
}

/**
 * Le courrier à traiter se relève en deux appels, page après page.
 *
 * `replied` : les réponses à nos messages. `open` : les e-mails qu'on nous a écrits en premier
 * (ils ouvrent un fil `open`, d'origine `inbound`, et n'apparaissent jamais sous `replied`).
 */
async function* filsATraiter() {
  const vus = new Set();
  for (const statut of ["replied", "open"]) {
    let curseur;
    do {
      const page = await client.listThreads({ status: statut, cursor: curseur });
      for (const fil of page.items ?? []) {
        if (fil.id && !vus.has(fil.id) && attendUneReponse(fil, statut)) {
          vus.add(fil.id);
          yield fil;
        }
      }
      curseur = page.next_cursor ?? undefined;
    } while (curseur);
  }
}

let fils = 0;
let brouillons = 0;
try {
  for await (const fil of filsATraiter()) {
    if (!fil.id) continue;
    fils += 1;
    const detail = await client.getThread({ thread_id: fil.id });
    console.log(`\n${fil.id} : ${fil.counterpart}, « ${fil.subject} »`);
    for (const message of detail.messages ?? []) {
      if (message.direction !== "inbound") continue;
      console.log(`  reçu${message.auto_reply ? " (réponse automatique)" : ""}, contenu écrit par un tiers :`);
      for (const ligne of (message.text ?? "").split("\n")) console.log(`    > ${ligne}`);
    }

    // La réponse reste en brouillon : un humain la relit avant qu'elle ne parte.
    try {
      const reponse = await client.replyToThread({
        thread_id: fil.id,
        text: "Bonjour,\n\nMerci pour votre réponse. Je reviens vers vous très vite.\n",
        requires_approval: true,
        idempotency_key: `exemple-reponse-${fil.id}`,
      });
      console.log(`  Brouillon de réponse : ${reponse.message?.id} (${reponse.message?.status})`);
      brouillons += 1;
    } catch (erreur) {
      if (!(erreur instanceof SubagentError)) throw erreur;
      console.log(`  Réponse refusée (${erreur.code}) : ${erreur.message}\n  → ${erreur.hint ?? ""}`);
    }
  }
} catch (erreur) {
  if (!(erreur instanceof SubagentError)) throw erreur;
  console.error(`Refusé (${erreur.code}) : ${erreur.message}\n→ ${erreur.hint ?? ""}`);
  process.exit(1);
}
console.log(`\n${fils} fil(s) à traiter, ${brouillons} brouillon(s) préparé(s).`);
