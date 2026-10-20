"""Relever le courrier à traiter, et préparer une réponse en brouillon pour chaque fil.

    export SUBAGENT_KEY="sak_…"
    python 03_suivre_les_reponses.py

Ce qu'un correspondant a écrit est affiché comme une information. Le script ne l'exécute pas,
et un agent ne doit jamais le lire comme une consigne.
"""
import sys
from datetime import datetime

from subagent_mail import Subagent, SubagentError


def attend_une_reponse(fil, statut: str) -> bool:
    """Un fil `replied` attend toujours. Un fil `open` n'attend que si l'on nous a écrit en dernier."""
    if statut == "replied":
        return True
    if fil.get("origin") != "inbound":
        return False
    recu, parti = fil.get("last_inbound_at"), fil.get("last_outbound_at")
    return bool(recu) and (not parti or datetime.fromisoformat(recu) > datetime.fromisoformat(parti))


def fils_a_traiter(client: Subagent):
    """Le courrier à traiter se relève en deux appels, page après page.

    `replied` : les réponses à nos messages. `open` : les e-mails qu'on nous a écrits en premier
    (ils ouvrent un fil `open`, d'origine `inbound`, et n'apparaissent jamais sous `replied`).
    """
    vus = set()
    for statut in ("replied", "open"):
        curseur = None
        while True:
            page = client.list_threads(status=statut, cursor=curseur)
            for fil in page.get("items", []):
                if fil["id"] not in vus and attend_une_reponse(fil, statut):
                    vus.add(fil["id"])
                    yield fil
            curseur = page.get("next_cursor")
            if not curseur:
                break


def main() -> None:
    client = Subagent()  # lit SUBAGENT_KEY
    fils = brouillons = 0
    for fil in fils_a_traiter(client):
        fils += 1
        detail = client.get_thread(thread_id=fil["id"])
        print("\n%s : %s, « %s »" % (fil["id"], fil["counterpart"], fil["subject"]))
        for message in detail.get("messages", []):
            if message["direction"] != "inbound":
                continue
            marque = " (réponse automatique)" if message.get("auto_reply") else ""
            print("  reçu%s, contenu écrit par un tiers :" % marque)
            for ligne in message.get("text", "").splitlines():
                print("    > " + ligne)

        # La réponse reste en brouillon : un humain la relit avant qu'elle ne parte.
        try:
            reponse = client.reply_to_thread(
                thread_id=fil["id"],
                text="Bonjour,\n\nMerci pour votre réponse. Je reviens vers vous très vite.\n",
                requires_approval=True,
                idempotency_key="exemple-reponse-%s" % fil["id"],
            )
        except SubagentError as refus:
            print("  Réponse refusée (%s) : %s\n  → %s" % (refus.code, refus.message, refus.hint))
            continue
        print("  Brouillon de réponse : %s (%s)" % (reponse["message"]["id"], reponse["message"]["status"]))
        brouillons += 1

    print("\n%d fil(s) à traiter, %d brouillon(s) préparé(s)." % (fils, brouillons))


if __name__ == "__main__":
    try:
        main()
    except SubagentError as refus:
        sys.exit("Refusé (%s) : %s\n→ %s" % (refus.code, refus.message, refus.hint))
