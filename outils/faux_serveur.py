"""Faux serveur Subagent pour les tests : mêmes routes, mêmes refus, aucune messagerie derrière.

Il contrôle chaque appel comme le serveur (origine, clé, permission, état de l'espace,
paramètres inconnus, schéma d'entrée, idempotence) et rend la sortie d'exemple de l'opération.
Il n'envoie rien et n'appelle personne. Les opérations, leurs schémas et leurs exemples viennent
de `registre_de_test.json`, généré depuis le registre d'opérations du serveur.

Usage dans un test :
    with FauxServeur() as serveur:
        client = Subagent(CLE_AGENT, base_url=serveur.url)

Seul, pour essayer un script à la main :
    python faux_serveur.py              # écoute sur http://127.0.0.1:8787 ; un autre port en argument
"""
from __future__ import annotations

import copy
import json
import re
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

REGISTRE = json.loads((Path(__file__).parent / "registre_de_test.json").read_text(encoding="utf-8"))
OPERATIONS = REGISTRE["operations"]

CLE_AGENT = "sak_exemple_agent"    # la clé que rend sign_up : send, read, manage_inboxes
CLE_HUMAIN = "sak_exemple_humain"  # la clé d'un humain : les mêmes, plus approve
CLES = {
    CLE_AGENT: {"send", "read", "manage_inboxes"},
    CLE_HUMAIN: {"send", "read", "manage_inboxes", "approve"},
}
DESTINATAIRE_BLOQUE = "desinscrit@exemple.com"  # tout envoi vers lui est refusé (recipient_suppressed)
FIL_RECU = "thr_5c1d9e3b7a2f4c6e8b0d1f3a5c7e9b2d"  # le fil d'un e-mail reçu en premier (list_threads, status open)


class Refus(Exception):
    def __init__(self, statut, code, message, hint=None):
        super().__init__(message)
        self.statut, self.code, self.message, self.hint = statut, code, message, hint

    def corps(self):
        erreur = {"code": self.code, "message": self.message}
        if self.hint:
            erreur["hint"] = self.hint
        return {"error": erreur}


def invalide(message, hint=None):
    return Refus(400, "invalid_argument", message, hint)


def controler(nom, schema, valeur):
    """Contrôle une valeur contre le schéma du paramètre (la partie de JSON Schema que le serveur emploie)."""
    attendu = schema.get("type")
    if attendu == "string":
        if not isinstance(valeur, str):
            raise invalide("%s doit être un texte." % nom)
        if "maxLength" in schema and len(valeur) > schema["maxLength"]:
            raise invalide("%s est trop long : %d caractères, %d au plus." % (nom, len(valeur), schema["maxLength"]))
        if "pattern" in schema and not re.search(schema["pattern"], valeur):
            raise invalide("%s invalide : « %s »." % (nom, valeur), "Attendu : %s" % schema["pattern"])
        if "enum" in schema and valeur not in schema["enum"]:
            raise invalide("%s invalide : « %s »." % (nom, valeur), "Valeurs acceptées : %s." % ", ".join(schema["enum"]))
    elif attendu == "boolean":
        if not isinstance(valeur, bool):
            raise invalide("%s doit être true ou false." % nom)
    elif attendu == "integer":
        if isinstance(valeur, bool) or not isinstance(valeur, int):
            raise invalide("%s doit être un entier." % nom)
        if valeur < schema.get("minimum", valeur) or valeur > schema.get("maximum", valeur):
            raise invalide("%s doit être un entier entre %s et %s." % (nom, schema.get("minimum"), schema.get("maximum")))
    elif attendu == "object":
        if not isinstance(valeur, dict):
            raise invalide("%s doit être un objet JSON." % nom)
    elif attendu == "array":
        if not isinstance(valeur, list):
            raise invalide("%s doit être une liste." % nom)
        if "maxItems" in schema and len(valeur) > schema["maxItems"]:
            raise invalide("%s : %d éléments au plus." % (nom, schema["maxItems"]))
    else:
        raise AssertionError("type de paramètre non pris en charge par le faux serveur : %r" % attendu)


class _Serveur(ThreadingHTTPServer):
    daemon_threads = True

    def handle_error(self, request, client_address):
        pass  # une connexion coupée exprès (panne simulée) n'est pas une erreur


class FauxServeur:
    def __init__(self, port=0):
        self.requetes = []     # chaque appel accepté : {"operation", "entetes", "arguments"}
        self.connexions = 0    # nombre de requêtes HTTP reçues, pannes comprises
        self.pannes = 0        # nombre de prochaines connexions coupées sans réponse
        self.passerelles = 0   # nombre de prochaines réponses 502 sans corps d'erreur Subagent
        self.lenteur = 0       # secondes d'attente avant chaque réponse
        self.verifie = True    # l'espace des clés d'exemple est vérifié (sign_up le remet à False)
        self._idempotence = {}
        self._verrou = threading.Lock()
        serveur = self

        class Gestionnaire(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *args):  # silence
                pass

            def do_POST(self):
                longueur = int(self.headers.get("Content-Length") or 0)
                corps = self.rfile.read(longueur) if longueur else b""
                with serveur._verrou:
                    serveur.connexions += 1
                    if serveur.pannes > 0:
                        serveur.pannes -= 1
                        self.close_connection = True
                        self.connection.close()
                        return
                    if serveur.passerelles > 0:
                        serveur.passerelles -= 1
                        return self._ecrire(502, b"<html>Bad Gateway</html>", "text/html")
                    try:
                        statut, reponse = 200, serveur._appeler(self.path, self.headers, corps)
                    except Refus as refus:
                        statut, reponse = refus.statut, refus.corps()
                if serveur.lenteur:
                    time.sleep(serveur.lenteur)
                self._ecrire(statut, json.dumps(reponse, ensure_ascii=False).encode("utf-8"), "application/json")

            def _ecrire(self, statut, octets, type_mime):
                self.send_response(statut)
                self.send_header("Content-Type", type_mime)
                self.send_header("Content-Length", str(len(octets)))
                if statut == 401:
                    self.send_header("WWW-Authenticate", 'Bearer realm="subagent"')
                self.end_headers()
                self.wfile.write(octets)

        self._httpd = _Serveur(("127.0.0.1", port), Gestionnaire)
        self.url = "http://127.0.0.1:%d" % self._httpd.server_address[1]
        self._fil = None

    # ─── Cycle de vie ────────────────────────────────────────────────────────────────────────

    def demarrer(self):
        self._fil = threading.Thread(target=self._httpd.serve_forever, kwargs={"poll_interval": 0.02}, daemon=True)
        self._fil.start()
        return self

    def arreter(self):
        self._httpd.shutdown()
        self._httpd.server_close()

    def __enter__(self):
        return self.demarrer()

    def __exit__(self, *exc):
        self.arreter()

    @property
    def derniere(self):
        return self.requetes[-1]

    # ─── Un appel, dans l'ordre des contrôles du serveur ─────────────────────────────────────

    def _appeler(self, chemin, entetes, corps):
        if not chemin.startswith("/v1/"):
            raise Refus(404, "unknown_operation", "Route inconnue : %s." % chemin)
        nom = chemin[len("/v1/"):]
        operation = OPERATIONS.get(nom)
        if entetes.get("Origin"):
            raise Refus(403, "origin_refused",
                        "Origine refusée : cette API ne s’appelle pas depuis la page web d’un autre site.",
                        "Appelez-la depuis votre agent ou votre serveur, sans en-tête Origin.")
        non_autorise = Refus(401, "unauthorized", "Clé d’API absente, inconnue ou révoquée.",
                             "Envoyez l’en-tête Authorization: Bearer sak_… avec votre clé. Pas encore de clé ? sign_up en ouvre une, sans clé.")
        permissions = None
        if entetes.get("Authorization") is not None:
            porteur = entetes["Authorization"]
            permissions = CLES.get(porteur[len("Bearer "):]) if porteur.startswith("Bearer ") else None
            if permissions is None:
                raise non_autorise
        if permissions is None and not (operation and operation["sans_cle"]):
            raise non_autorise
        try:
            arguments = json.loads(corps.decode("utf-8")) if corps.strip() else {}
        except ValueError:
            raise invalide("Corps JSON illisible.",
                           "Envoyez un objet JSON : les arguments de l’opération (voir /openapi.json).") from None
        proprietes = operation["entree"].get("properties", {}) if operation else {}
        cle_entete = entetes.get("Idempotency-Key")
        if cle_entete and isinstance(arguments, dict) and "idempotency_key" in proprietes:
            arguments.setdefault("idempotency_key", cle_entete)
        self.requetes.append({"operation": nom, "entetes": dict(entetes.items()), "arguments": arguments})
        if operation is None:
            raise Refus(404, "unknown_operation", "Opération inconnue : %s." % nom,
                        "La liste des opérations est dans tools/list (MCP), /openapi.json ou /llms.txt.")
        if not operation["sans_cle"]:
            if not permissions & set(operation["permissions"]):
                raise Refus(403, "forbidden",
                            "%s demande la permission %s, que cette clé n’a pas." % (nom, " ou ".join(operation["permissions"])),
                            "La validation est un geste humain : un humain l’accomplit depuis son assistant, avec une clé qui porte approve."
                            if operation["permissions"] == ["approve"] else
                            "Demandez à un administrateur de Subagent une clé qui porte cette permission.")
            if operation["espace"] == "vérifié" and not self.verifie:
                raise Refus(403, "space_unverified", "Espace non vérifié : ses boîtes reçoivent, mais n’envoient pas.",
                            "Demandez à votre humain le code à 6 chiffres reçu par e-mail, puis appelez verify.")
            if operation["espace"] == "non vérifié" and self.verifie:
                raise Refus(409, "already_verified", "Espace déjà vérifié.", "Rien à faire : l’envoi est ouvert.")
        if arguments is None:
            arguments = {}
        if not isinstance(arguments, dict):
            raise invalide("Les arguments doivent être un objet JSON.")
        for cle in arguments:
            if cle not in proprietes:
                raise invalide("Paramètre inconnu : %s." % cle,
                               "Paramètres acceptés par %s : %s." % (nom, ", ".join(sorted(proprietes))))
        arguments = {cle: valeur for cle, valeur in arguments.items() if valeur is not None}
        for cle in operation["entree"].get("required", []):
            if cle not in arguments:
                raise invalide("%s est obligatoire." % cle)
        for cle, valeur in arguments.items():
            controler(cle, proprietes[cle], valeur)
        exige = "confirm" in operation["entree"].get("required", []) or (nom == "campaign_action" and arguments.get("action") == "start")
        if exige and arguments.get("confirm") is not True:
            raise invalide("confirm doit valoir true : l’opération est irréversible.")
        if arguments.get("to") == DESTINATAIRE_BLOQUE:
            raise Refus(422, "recipient_suppressed",
                        "Destinataire bloqué : %s s’est désinscrit." % DESTINATAIRE_BLOQUE,
                        "Ne lui écrivez plus, depuis aucune boîte.")
        return self._repondre(nom, arguments)

    def _repondre(self, nom, arguments):
        cle = arguments.get("idempotency_key")
        contenu = json.dumps({k: v for k, v in arguments.items() if k != "idempotency_key"}, sort_keys=True)
        if cle is not None and (nom, cle) in self._idempotence:
            ancien, reponse = self._idempotence[(nom, cle)]
            if ancien != contenu:
                raise Refus(409, "idempotency_conflict",
                            "La clé d’idempotence « %s » a déjà servi pour un contenu différent." % cle,
                            "Même message : réutilisez la clé telle quelle. Nouveau message : prenez-en une nouvelle.")
            return dict(reponse, replayed=True)
        reponse = copy.deepcopy(OPERATIONS[nom]["exemple"])
        if nom == "sign_up":
            self.verifie = False
            reponse["api_key"] = CLE_AGENT
        if nom == "verify":
            self.verifie = True
        if nom == "list_threads" and arguments.get("status") == "open":
            # Un e-mail reçu en premier : il ouvre un fil `open`, d'origine `inbound`, jamais `replied`.
            for fil in reponse["items"]:
                fil.update(id=FIL_RECU, status="open", origin="inbound", subject="Demande de devis",
                           last_outbound_at=None, last_inbound_at=fil["last_message_at"])
        message = reponse.get("message")
        if isinstance(message, dict) and "text" in arguments:
            for champ in ("to", "subject", "text", "reply_to"):
                if champ in arguments:
                    message[champ] = arguments[champ]
            if arguments.get("requires_approval"):
                message["status"] = "draft"
                reponse["estimated_send_at"] = None
        if cle is not None:
            self._idempotence[(nom, cle)] = (contenu, reponse)
        return reponse


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8787
    faux = FauxServeur(port)
    print("Faux serveur Subagent : %s  (clés : %s, %s ; Ctrl+C pour arrêter)" % (faux.url, CLE_AGENT, CLE_HUMAIN))
    try:
        faux._httpd.serve_forever()
    except KeyboardInterrupt:
        pass
