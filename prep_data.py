import pandas as pd
from datetime import datetime

def charger_donnees(chemin_fichier, code_station=34, date_debut=1997, date_fin=2025):
    """
    Chargement et filtrage des données d'une station hydrologique.

    Cette fonction charge un fichier de données hydrologiques, filtre selon le code station,
    convertit les dates et sélectionne les années d'intérêt.

    Paramètres:
        chemin_fichier (str): Chemin du fichier CSV/DELIM à charger, contenant les colonnes 
            DATE_RELEVE, DEBIT_OUT (en m3/s), EVAPORATION (en m3), VOLUME (en m3), COTE (en m), etc.
        code_station (int): Code de la station à filtrer, par défaut 34 (barrage du Salagou).
        date_debut (int): Année de début (exclue), par défaut 1997.
        date_fin (int): Année de fin (exclue), par défaut 2025.

    Retour:
        pd.DataFrame: Données filtrées pour la station et la période spécifiée.
    """

    # Chargement des données
    data_full = pd.read_csv(
        chemin_fichier, 
        sep=";", 
        decimal=",", 
        dtype={"CODE_STATION": int},
        parse_dates=False
    )

    # Conversion de la date et filtrage
    data_full['DATE_RELEVE'] = pd.to_datetime(
        data_full['DATE_RELEVE'],
        format='%d/%m/%y',  # <--- 2 chiffres
        errors='coerce'
    )

    # Filtrage par station et année
    data_station = data_full[
        (data_full['CODE_STATION'] == code_station) &
        (data_full['DATE_RELEVE'].dt.year > date_debut) &
        (data_full['DATE_RELEVE'].dt.year < date_fin)
    ].sort_values(by='DATE_RELEVE')

    return data_station

import numpy as np

def simuler_salagou(data, evap_pct=0.10, entree_pct=0.10):
    """
    Simulation hydrologique et climatique pour un barrage.

    Paramètres :
        data (pd.DataFrame): Doit contenir les colonnes 
            ['DATE_RELEVE', 'DEBIT_OUT', 'EVAPORATION', 'VOLUME', 'COTE']
        evap_pct (float): % d'augmentation de l'évaporation (ex: 0.10 pour +10%)
        entree_pct (float): % de réduction des entrées naturelles (ex: 0.10 pour -10%)

    Retour :
        dict : Contient
            - 'cote_moyenne' : moyenne mensuelle de la cote
            - 'donnees_simulees' : données avec colonnes simulées et volumes du premier jour
            - 'donnees_mensuelles' : données agrégées mensuellement
    """

    # Vérification des colonnes nécessaires
    required_cols = ["DATE_RELEVE", "DEBIT_OUT", "EVAPORATION", "VOLUME", "COTE"]
    if not all(col in data.columns for col in required_cols):
        raise ValueError(f"Le jeu de données doit contenir : {', '.join(required_cols)}")

    # Création de la colonne MOIS
    data["DATE_RELEVE"] = pd.to_datetime(data["DATE_RELEVE"])
    data["MOIS"] = data["DATE_RELEVE"].dt.to_period("M").dt.to_timestamp()

    # Cote moyenne mensuelle
    cote_moyenne = data.groupby("MOIS").agg(
        COTE_MOYENNE=('COTE', 'mean')
    ).reset_index()
    cote_moyenne["ANNEE"] = cote_moyenne["MOIS"].dt.year
    cote_moyenne["MOIS_NUM"] = cote_moyenne["MOIS"].dt.month

    # Simulation hydrologique et climatique
    data = data.sort_values("DATE_RELEVE").copy()
    data["DEBIT_OUT_m3"] = data["DEBIT_OUT"] * 86400
    data["LACHURES_m3"] = data["DEBIT_OUT_m3"] - data["EVAPORATION"]
    data["DELTA_VOLUME"] = data["VOLUME"].diff()
    data["ENTREE_NATURELLE"] = data["DELTA_VOLUME"] + data["DEBIT_OUT_m3"]

    # Application des % de changement climatique
    data["EVAP_CLIMAT"] = data["EVAPORATION"] * (1 + evap_pct)
    data["ENTREE_CLIMAT"] = data["ENTREE_NATURELLE"] * (1 - entree_pct)
    data["DEBIT_OUT_CLIMAT"] = data["LACHURES_m3"] + data["EVAP_CLIMAT"]
    data["DELTA_VOLUME_CLIMAT"] = data["ENTREE_CLIMAT"] - data["DEBIT_OUT_CLIMAT"]

    # Données mensuelles agrégées
    donnees_mensuelles = data.groupby("MOIS").agg({
        "ENTREE_NATURELLE": lambda x: max(x.sum(skipna=True), 0),
        "EVAPORATION": lambda x: max(x.sum(skipna=True), 0),
        "EVAP_CLIMAT": lambda x: max(x.sum(skipna=True), 0),
        "ENTREE_CLIMAT": lambda x: max(x.sum(skipna=True), 0)
    }).reset_index()

    # Extraction volumes du premier jour de chaque mois
    premiers_jours = data[data["DATE_RELEVE"].dt.is_month_start][["DATE_RELEVE", "VOLUME"]].copy()
    premiers_jours["MOIS"] = premiers_jours["DATE_RELEVE"].dt.to_period("M").dt.to_timestamp()
    premiers_jours = premiers_jours.drop(columns="DATE_RELEVE")

    # Merge volumes premier jour dans donnees_mensuelles
    donnees_mensuelles = donnees_mensuelles.merge(premiers_jours, on="MOIS", how="left")
    donnees_mensuelles = donnees_mensuelles.rename(columns={"VOLUME": "VOLUME_PREMIER_JOUR"})

    return {
        "cote_moyenne": cote_moyenne,
        "donnees_simulees": donnees_mensuelles
    }




