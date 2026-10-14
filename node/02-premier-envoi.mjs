// Regarder où en est la boîte, puis écrire un premier message, laissé en brouillon.
//
//     export SUBAGENT_KEY="sak_…"
//     node 02-premier-envoi.mjs marie@exemple.fr
//
// L'envoi est un envoi de test (`test: true`) : il ne part qu'à l'humain de l'espace ou à une
// autre de ses boîtes. Donnez votre propre adresse.

import { Subagent, SubagentError } from "subagent-mail";

const destinataire = process.argv[2];
if (!destinataire) {
  console.error("Usage : node 02-premier-envoi.mjs <votre-adresse>");
  process.exit(2);
}

const client = new Subagent(); // lit SUBAGENT_KEY

try {
  // Le point de départ de toute session.
  const etat = await client.inboxStatus();
  if (!etat.verified) {
    throw new Error("L'espace n'est pas vérifié : ses boîtes reçoivent, mais n'envoient pas. Voir 01-inscription.mjs.");
  }
  const boite = etat.inboxes?.[0];
  if (!boite?.id) throw new Error("Aucune boîte pour cette clé.");
  console.log(
    `Boîte ${boite.address} : ${boite.quota?.remaining_today} envois restants aujourd'hui. Créneau : ${etat.send_window}.`,
  );

  const envoi = await client.sendEmail({
    inbox_id: boite.id,
    to: destinataire,
    subject: "Premier message",
    text: "Bonjour,\n\nCeci est mon premier message, écrit depuis ma propre boîte.\n",
    test: true,
    requires_approval: true, // reste en brouillon jusqu'à la validation d'un humain
    idempotency_key: `exemple-premier-envoi-${destinataire}`, // rejouer ce script ne crée pas de doublon
  });

  if (envoi.replayed) console.log("Déjà créé lors d'un appel précédent : rien de nouveau.");
  if (envoi.message?.status === "draft") {
    console.log(`Brouillon ${envoi.message.id} : il attend une validation humaine (voir 05-validation-humaine.mjs).`);
  } else {
    console.log(`Message ${envoi.message?.id} en file. Départ au plus tôt : ${envoi.estimated_send_at}.`);
  }
} catch (erreur) {
  if (erreur instanceof SubagentError) {
    // Un refus n'est pas une panne : le code est stable, la piste dit quoi faire.
    console.error(`Refusé (${erreur.code}) : ${erreur.message}\n→ ${erreur.hint ?? ""}`);
  } else {
    console.error(erreur.message);
  }
  process.exit(1);
}
