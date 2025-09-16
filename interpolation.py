#%%
import pandas as pd
import numpy as np
from pathlib import Path
from scipy.interpolate import interp1d


def charger_table_hsv(depuis_fichier=True, chemin=None, code=34):
    """
    Charge la table HSV (par défaut HSV_<code>.txt/csv) et nettoie les colonnes.
    
    Args:
        depuis_fichier (bool): doit être True, sinon erreur.
        chemin (str | Path, optional): chemin explicite du fichier à lire.
        code (int | str, optional): code station (ex: 34, 32). Si fourni,
                                    cherche un fichier "HSV_<code>.txt".
    Returns:
        pd.DataFrame: table nettoyée avec colonnes standardisées.
    """
    if not depuis_fichier:
        raise ValueError("Le chargement interne n'est pas défini ici.")

    # Détermination du chemin
    if chemin is None:
        try:
            base_path = Path(__file__).parent
        except NameError:
            base_path = Path.cwd()
        
        chemin = base_path / "data" / f"HSV_{code}.txt"

    chemin = Path(chemin)
    if not chemin.exists():
        raise FileNotFoundError(f"Fichier HSV introuvable : {chemin}")

    # Lecture CSV avec fallback encodage
    try:
        table = pd.read_csv(chemin, sep=";", encoding="utf-8")
    except UnicodeDecodeError:
        table = pd.read_csv(chemin, sep=";", encoding="latin1")

    # Nettoyage colonnes
    table.columns = (
        table.columns
        .str.strip()
        .str.replace(r"\s+", " ", regex=True)
        .str.replace("\u202f", " ", regex=True)
        .str.upper()  # tout en majuscules pour uniformiser
    )

    # Mapping vers colonnes standard
    rename_map = {
        "VOLUME": "Volume",
        "COTE": "Cote",
        "SURFACE": "Surface"
    }
    table = table.rename(columns=rename_map)

    # Vérification colonnes
    if not {"Volume", "Cote"}.issubset(table.columns):
        raise ValueError(f"Colonnes attendues manquantes : {table.columns}")

    # Nettoyage des colonnes numériques
    for col in ["Volume", "Cote", "Surface"]:
        if col in table.columns:
            table[col] = (
                table[col]
                .astype(str)
                .str.replace("\u202f", "", regex=True)
                .str.replace(" ", "", regex=True)
                .str.replace(",", ".", regex=True)
            ).astype(float)

    # Supprimer lignes invalides
    table = table.dropna(subset=["Volume", "Cote"])
    return table


def volume_to_cote(volume, table_interpolation=None, code=34):
    """
    Interpole la cote (m NGF) à partir d'un volume (m³).
    """
    if table_interpolation is None:
        table_interpolation = charger_table_hsv(code=code)

    # Tri pour garantir ordre croissant
    table_sorted = table_interpolation.sort_values("Volume")

    interpolateur = interp1d(
        table_sorted["Volume"],
        table_sorted["Cote"],
        kind="linear",
        fill_value="extrapolate",
        assume_sorted=True
    )
    return float(interpolateur(volume))

# Interpolation Cote à Volume
def cote_to_volume(cote, table_interpolation=None, code=34):
    """
    Interpole le volume (en m³) à partir d'une cote (en m).
    """
    if table_interpolation is None:
        table_interpolation = charger_table_hsv(code=code)

    # Tri pour garantir ordre croissant
    table_sorted = table_interpolation.sort_values("Cote")

    interpolateur = interp1d(
        table_sorted["Cote"],
        table_sorted["Volume"],
        kind="linear",
        fill_value="extrapolate",
        assume_sorted=True
    )
    return float(interpolateur(cote))



# %%
volume_to_cote(82792300)
# %%
