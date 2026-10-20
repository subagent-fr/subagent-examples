"""S'inscrire sans clé, puis vérifier l'espace avec le code reçu par l'humain.

    python 01_inscription.py atelier-exemple marie@exemple.fr

Rend une clé (affichée une seule fois) et une boîte sur le domaine commun d'essai. L'humain
reçoit un code à 6 chiffres par e-mail : le script le demande, puis ouvre l'envoi.
"""
import sys

from subagent_mail import Subagent, SubagentError


def main(username: str, human_email: str) -> None:
    client = Subagent(api_key="")  # sans clé : seule sign_up est ouverte

    try:
        inscription = client.sign_up(username=username, human_email=human_email)
    except SubagentError as refus:
        sys.exit("Inscription refusée (%s) : %s\n→ %s" % (refus.code, refus.message, refus.hint))

    print("Boîte :", inscription["inbox"]["address"])
    print("Clé, affichée une seule fois :", inscription["api_key"])
    print('Rangez-la : export SUBAGENT_KEY="…"')

    if not inscription.get("code_sent"):
        print("Aucun code n'est parti : la boîte reçoit, mais n'enverra qu'après attach_human puis verify.")
        return

    # Le client garde la clé rendue par sign_up : les appels suivants passent avec elle.
    code = input("Code à 6 chiffres reçu par %s : " % inscription["human_email"]).strip()
    try:
        client.verify(otp_code=code)
    except SubagentError as refus:
        sys.exit("Vérification refusée (%s) : %s\n→ %s" % (refus.code, refus.message, refus.hint))
    print("Espace vérifié : l'envoi est ouvert.")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("Usage : python 01_inscription.py <nom-de-la-boîte> <e-mail-de-l'humain>")
    main(sys.argv[1], sys.argv[2])
