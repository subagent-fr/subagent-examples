"""Chaque exemple, lancé pour de vrai contre le faux serveur local.

    pip install -r python/requirements.txt   # pour les exemples Python
    (cd node && npm install)             # pour les exemples TypeScript
    python -m unittest discover -s tests -v

Un exemple dont le SDK n'est pas installé est sauté, et le test le dit.
"""
import importlib.util
import os
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE / "outils"))

from faux_serveur import CLE_AGENT, CLE_HUMAIN, FauxServeur  # noqa: E402

# (préfixe du fichier, arguments, entrée standard, clé, ce que la sortie doit contenir)
SCENARIOS = [
    ("01", ["atelier-exemple", "marie@exemple.fr"], "482913\n", None, "Espace vérifié"),
    ("02", ["marie@exemple.fr"], "", CLE_AGENT, "Brouillon msg_"),
    ("03", [], "", CLE_AGENT, "2 fil(s) à traiter, 2 brouillon(s) préparé(s)."),  # une réponse, et un e-mail reçu en premier
    ("04", ["agents.exemple.fr"], "", CLE_AGENT, "Domaine agents.exemple.fr : pending"),
    ("05", [], "o\n", CLE_HUMAIN, "Validé : queued"),
]

PYTHON_PRET = importlib.util.find_spec("subagent_mail") is not None
NODE = shutil.which("node")
NODE_PRET = bool(NODE) and (RACINE / "node" / "node_modules" / "subagent-mail").exists()


class Exemples(unittest.TestCase):
    def setUp(self):
        self.serveur = FauxServeur().demarrer()
        self.addCleanup(self.serveur.arreter)

    def lancer(self, commande, dossier, arguments, entree, cle):
        env = dict(os.environ, SUBAGENT_BASE_URL=self.serveur.url, PYTHONIOENCODING="utf-8")
        env.pop("SUBAGENT_KEY", None)
        if cle:
            env["SUBAGENT_KEY"] = cle
        return subprocess.run(commande + arguments, cwd=dossier, env=env, input=entree, capture_output=True,
                              text=True, encoding="utf-8", timeout=60)

    def chaque(self, dossier, motif, commande):
        fichiers = sorted((RACINE / dossier).glob(motif))
        self.assertEqual(len(fichiers), len(SCENARIOS))
        for fichier, (prefixe, arguments, entree, cle, attendu) in zip(fichiers, SCENARIOS):
            with self.subTest(fichier.name):
                self.assertTrue(fichier.name.startswith(prefixe))
                self.serveur.verifie = True
                resultat = self.lancer(commande + [fichier.name], RACINE / dossier, arguments, entree, cle)
                self.assertEqual(resultat.returncode, 0, resultat.stderr)
                self.assertIn(attendu, resultat.stdout)
        return fichiers

    @unittest.skipUnless(PYTHON_PRET, "le paquet subagent-mail n'est pas installé pour ce Python")
    def test_exemples_python(self):
        fichiers = self.chaque("python", "0*.py", [sys.executable])
        # La validation avec la clé d'un agent est refusée, et l'exemple le dit.
        refus = self.lancer([sys.executable, fichiers[-1].name], RACINE / "python", [], "o\n", CLE_AGENT)
        self.assertEqual(refus.returncode, 1)
        self.assertIn("forbidden", refus.stdout)

    @unittest.skipUnless(NODE_PRET, "node absent, ou subagent-mail n'est pas installé dans node/")
    def test_exemples_node(self):
        fichiers = self.chaque("node", "0*.mjs", [NODE])
        refus = self.lancer([NODE, fichiers[-1].name], RACINE / "node", [], "o\n", CLE_AGENT)
        self.assertEqual(refus.returncode, 1)
        self.assertIn("forbidden", refus.stdout)

    def test_un_refus_s_affiche_avec_sa_piste(self):
        if not PYTHON_PRET:
            self.skipTest("le paquet subagent-mail n'est pas installé pour ce Python")
        self.serveur.verifie = False
        resultat = self.lancer([sys.executable, "03_suivre_les_reponses.py"], RACINE / "python", [], "", CLE_AGENT)
        self.assertEqual(resultat.returncode, 0)
        self.assertIn("space_unverified", resultat.stdout)
        self.assertIn("verify", resultat.stdout)


if __name__ == "__main__":
    unittest.main()
