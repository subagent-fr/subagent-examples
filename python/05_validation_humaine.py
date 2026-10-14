"""Relire les brouillons qu'un agent a préparés, et les valider ou les annuler un par un.

    export SUBAGENT_KEY="sak_…"      # la clé d'un humain : elle doit porter approve
    python 05_validation_humaine.py

C'est le geste de l'humain. Avec la clé d'un agent, la validation est refusée (forbidden) :
un agent ne valide jamais son propre brouillon.
"""
import sys

from subagent_mail import Subagent, SubagentError


def main() -> None:
    client = Subagent()  # lit SUBAGENT_KEY
    brouillons = client.list_drafts().get("items", [])
    if not brouillons:
        print("Aucun brouillon à valider.")
        return

    for brouillon in brouillons:
        print("\n%s" % brouillon["id"])
        print("De    : %s" % brouillon["from"])
        print("À     : %s" % brouillon["to"])
        if brouillon.get("reply_to"):
            print("Répondre à : %s" % brouillon["reply_to"])
        print("Sujet : %s" % brouillon["subject"])
        print("\n%s\n" % brouillon.get("text", ""))
        if brouillon.get("has_html"):
            print("(ce message a aussi une version HTML)")

        choix = input("Valider (o), annuler (a), passer (entrée) ? ").strip().lower()
        try:
            if choix == "o":
                # `revision` : la validation ne vaut que pour le texte qui vient d'être lu.
                valide = client.approve_message(message_id=brouillon["id"], revision=brouillon.get("revision"))
                print("Validé : %s. Il partira dans le créneau, selon le quota de la boîte." % valide["status"])
            elif choix == "a":
                client.cancel_message(message_id=brouillon["id"], reason="Refusé à la relecture.")
                print("Annulé.")
        except SubagentError as refus:
            print("Refusé (%s) : %s\n→ %s" % (refus.code, refus.message, refus.hint))
            if refus.code == "forbidden":
                sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except SubagentError as refus:
        sys.exit("Refusé (%s) : %s\n→ %s" % (refus.code, refus.message, refus.hint))
