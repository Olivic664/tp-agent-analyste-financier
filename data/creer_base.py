"""
=============================================================================
 TP SEMAINE 20 — Agent Analyste | Script de création de la base SQLite
=============================================================================
 Rôle de ce script :
   Créer la petite base financière SQLite annoncée dans les prérequis du TP.
   Elle sert de "mémoire longue" factuelle que l'agent interrogera via
   l'outil requete_sql (en lecture seule).

 Contenu :
   - 5 entreprises fictives (5 secteurs différents, dont une en redressement)
   - 4 ans d'historique (2021 → 2024) : CA, résultat net, dettes, effectif
   - Montants en MILLIONS d'euros (à préciser dans les descriptions d'outils !)

 Usage :
   python data/creer_base.py

 Vérification rapide :
   python -c "import sqlite3; c=sqlite3.connect('data/finances.db'); \
              print(c.execute('SELECT COUNT(*) FROM finances').fetchall())"
=============================================================================
"""

import sqlite3
from pathlib import Path

# Chemin de la base : le fichier sera créé à côté de ce script
CHEMIN_BASE = Path(__file__).resolve().parent / "finances.db"


def creer_base() -> None:
    """Crée le schéma puis insère les données fictives de démonstration."""

    # Si une ancienne base existe, on la supprime pour repartir de zéro
    # (idempotence : le script peut être relancé sans risque).
    if CHEMIN_BASE.exists():
        CHEMIN_BASE.unlink()

    # sqlite3.connect crée le fichier s'il n'existe pas.
    connexion = sqlite3.connect(CHEMIN_BASE)
    curseur = connexion.cursor()

    # ------------------------------------------------------------------
    # 1) SCHÉMA — deux tables reliées par une clé étrangère
    # ------------------------------------------------------------------
    curseur.executescript(
        """
        CREATE TABLE entreprises (
            id       INTEGER PRIMARY KEY,
            nom      TEXT NOT NULL UNIQUE,
            secteur  TEXT NOT NULL
        );

        CREATE TABLE finances (
            id              INTEGER PRIMARY KEY,
            entreprise_id   INTEGER NOT NULL,
            annee           INTEGER NOT NULL,
            chiffre_affaires REAL NOT NULL,   -- en millions d'euros
            resultat_net    REAL NOT NULL,    -- en millions d'euros
            dettes_totales  REAL NOT NULL,    -- en millions d'euros
            effectif        INTEGER,          -- nombre de salariés
            FOREIGN KEY (entreprise_id) REFERENCES entreprises(id),
            UNIQUE (entreprise_id, annee)     -- une seule ligne par an/entreprise
        );
        """
    )

    # ------------------------------------------------------------------
    # 2) DONNÉES — 5 profils financiers volontairement variés
    #    (croissance saine, pression marginale, volatilité, croissance
    #     régulière, redressement après pertes) pour rendre l'analyse
    #     intéressante pour l'agent.
    # ------------------------------------------------------------------
    entreprises = [
        (1, "TechNova Solutions", "Technologie / Logiciel"),
        (2, "Aquitaine Bois Industrie", "Industrie / Bois"),
        (3, "MarineLog Shipping", "Transport maritime"),
        (4, "BioSanté Laboratoires", "Santé / Pharmaceutique"),
        (5, "VoltaMobilité", "Automobile / Véhicules électriques"),
    ]
    curseur.executemany("INSERT INTO entreprises VALUES (?, ?, ?)", entreprises)

    # (entreprise_id, annee, CA, résultat net, dettes, effectif)
    finances = [
        # TechNova Solutions — croissance saine, marges qui s'améliorent
        (1, 2021, 45.2, 3.1, 12.0, 210),
        (1, 2022, 58.7, 5.4, 14.5, 260),
        (1, 2023, 74.3, 7.9, 15.2, 310),
        (1, 2024, 92.8, 11.2, 16.0, 355),
        # Aquitaine Bois Industrie — marges sous pression (crise énergie) puis reprise
        (2, 2021, 120.5, 6.0, 45.0, 480),
        (2, 2022, 135.2, 4.1, 52.3, 495),
        (2, 2023, 128.7, 2.8, 55.1, 470),
        (2, 2024, 141.9, 5.6, 50.8, 475),
        # MarineLog Shipping — très volatile (boom fret 2021-2022, puis retournement)
        (3, 2021, 210.3, 31.5, 120.0, 1250),
        (3, 2022, 245.8, 44.2, 105.5, 1300),
        (3, 2023, 175.4, 12.1, 115.2, 1180),
        (3, 2024, 168.9, 9.4, 110.7, 1150),
        # BioSanté Laboratoires — croissance régulière, marges stables ~12 %
        (4, 2021, 85.6, 8.6, 30.0, 540),
        (4, 2022, 94.1, 9.9, 28.5, 570),
        (4, 2023, 108.3, 12.0, 35.2, 615),
        (4, 2024, 126.7, 15.2, 38.9, 660),
        # VoltaMobilité — pertes puis redressement (cas idéal pour la section Risques)
        (5, 2021, 32.4, -5.8, 48.0, 300),
        (5, 2022, 51.9, -3.2, 62.5, 420),
        (5, 2023, 78.6, 1.5, 70.3, 530),
        (5, 2024, 105.4, 4.8, 65.1, 610),
    ]
    curseur.executemany(
        """INSERT INTO finances
           (entreprise_id, annee, chiffre_affaires, resultat_net,
            dettes_totales, effectif)
           VALUES (?, ?, ?, ?, ?, ?)""",
        finances,
    )

    connexion.commit()
    connexion.close()

    print(f"Base créée : {CHEMIN_BASE}")
    print(f"  - {len(entreprises)} entreprises")
    print(f"  - {len(finances)} lignes financières (2021 → 2024)")


if __name__ == "__main__":
    creer_base()
