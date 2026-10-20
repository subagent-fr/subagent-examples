"""Regarder où en est la boîte, puis écrire un premier message, laissé en brouillon.

    export SUBAGENT_KEY="sak_…"
    python 02_premier_envoi.py marie@exemple.fr

L'envoi est un envoi de test (`test=True`) : il ne part qu'à l'humain de l'espace ou à une autre
de ses boîtes. Donnez votre propre adresse.
"""
import sys

from subagent_mail import Subagent, SubagentError


def main(destinataire: str) -> None:
    client = Subagent()  # lit SUBAGENT_KEY

    # Le point de départ de toute session.
    etat = client.inbox_status()
    if not etat.get("verified"):
        sys.exit("L'espace n'est pas vérifié : ses boîtes reçoivent, mais n'envoient pas. Voir 01_inscription.py.")
    boites = etat.get("inboxes", [])
    if not boites:
        sys.exit("Aucune boîte pour cette clé.")
    boite = boites[0]
    quota = boite.get("quota", {})
    print("Boîte %s : %s envois restants aujourd'hui. Créneau : %s." % (
        boite["address"], quota.get("remaining_today"), etat.get("send_window")))

    try:
        envoi = client.send_email(
            inbox_id=boite["id"],
            to=destinataire,
            subject="Premier message",
            text="Bonjour,\n\nCeci est mon premier message, écrit depuis ma propre boîte.\n",
            test=True,
            requires_approval=True,  # reste en brouillon jusqu'à la validation d'un humain
            idempotency_key="exemple-premier-envoi-%s" % destinataire,  # rejouer ce script ne crée pas de doublon
        )
    except SubagentError as refus:
        # Un refus n'est pas une panne : le code est stable, la piste dit quoi faire.
        sys.exit("Refusé (%s) : %s\n→ %s" % (refus.code, refus.message, refus.hint))

    message = envoi["message"]
    if envoi.get("replayed"):
        print("Déjà créé lors d'un appel précédent : rien de nouveau.")
    if message["status"] == "draft":
        print("Brouillon %s : il attend une validation humaine (voir 05_validation_humaine.py)." % message["id"])
    else:
        print("Message %s en file. Départ au plus tôt : %s." % (message["id"], envoi.get("estimated_send_at")))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage : python 02_premier_envoi.py <votre-adresse>")
    main(sys.argv[1])
