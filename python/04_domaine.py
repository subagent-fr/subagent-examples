"""Enregistrer son domaine, afficher les enregistrements DNS à publier, puis les contrôler.

    export SUBAGENT_KEY="sak_…"
    python 04_domaine.py agents.exemple.fr

Lancez-le une première fois pour obtenir les enregistrements, publiez-les chez l'hébergeur DNS du
domaine, puis relancez-le : il dit, enregistrement par enregistrement, ce qui est en place.
"""
import sys

from subagent_mail import Subagent, SubagentError

ETATS = {"found": "en place", "missing": "absent", "different": "valeur différente", None: "pas encore contrôlé"}


def afficher(domaine) -> None:
    print("Domaine %s : %s" % (domaine["domain"], domaine["status"]))
    for enregistrement in domaine.get("records", []):
        exige = "exigé" if enregistrement.get("required") else "conseillé"
        print("\n  %s (%s, %s) : %s" % (
            enregistrement["label"], enregistrement["type"], exige, ETATS[enregistrement.get("state")]))
        print("    Nom    : %s" % enregistrement["name"])
        print("    Valeur : %s" % enregistrement["value"])
        if enregistrement.get("seen"):
            print("    Vu     : %s" % enregistrement["seen"])
        if enregistrement.get("note"):
            print("    Note   : %s" % enregistrement["note"])


def main(nom: str) -> None:
    client = Subagent()  # lit SUBAGENT_KEY ; la clé doit porter manage_inboxes

    try:
        client.add_domain(domain=nom)
        print("Domaine enregistré. Publiez les enregistrements ci-dessous, puis relancez ce script.")
    except SubagentError as refus:
        if refus.code != "domain_exists":
            sys.exit("Refusé (%s) : %s\n→ %s" % (refus.code, refus.message, refus.hint))
        # Déjà enregistré pour cet espace : on passe au contrôle.

    try:
        domaine = client.verify_domain(domain=nom)
    except SubagentError as refus:
        sys.exit("Contrôle impossible (%s) : %s\n→ %s" % (refus.code, refus.message, refus.hint))
    afficher(domaine)

    if domaine["status"] == "verified":
        print("\nDomaine vérifié : créez-y une boîte avec create_inbox.")
    else:
        print("\nPas encore vérifié. Un changement de DNS met parfois quelques minutes à se voir.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage : python 04_domaine.py <domaine>")
    main(sys.argv[1])
