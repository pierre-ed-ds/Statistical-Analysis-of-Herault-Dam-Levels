
#%%
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import pandas as pd


def faconnage_graph(self, debut_mois, entree_clim, evap_clim, p1=0.25, p2=0.5, vect_lach=None):
        """
        Construction du tableau de données pour nos indicateurs.
        """
        if vect_lach is None:
            vect_lach = [0]*12

        # Si déjà en format long, ne pas refaire melt
        df_long_deb_mois = debut_mois.copy()
        df_long_entree_clim = entree_clim.copy()
        df_long_evap_clim = evap_clim.copy()

        quantiles_deb_mois = df_long_deb_mois.groupby('MOIS_NUM')['valeur'].quantile([p1, p2]).unstack()
        quantiles_entree_clim = df_long_entree_clim.groupby('MOIS_NUM')['valeur'].quantile([p1, p2]).unstack()
        quantiles_evap_clim = df_long_evap_clim.groupby('MOIS_NUM')['valeur'].quantile([p1, p2]).unstack()

        resultats_p1 = []
        resultats_p2 = []

        for mois in range(1, 13):
            mois_prec = 12 if mois == 1 else mois - 1  # mois précédent
            val_p1 = (quantiles_deb_mois.loc[mois_prec, p1] +
                      quantiles_entree_clim.loc[mois_prec, p1] -
                      quantiles_evap_clim.loc[mois_prec, p1] -
                      vect_lach[mois_prec - 1])
            val_p2 = (quantiles_deb_mois.loc[mois_prec, p2] +
                      quantiles_entree_clim.loc[mois_prec, p2] -
                      quantiles_evap_clim.loc[mois_prec, p2] -
                      vect_lach[mois_prec - 1])

            resultats_p1.append(val_p1)
            resultats_p2.append(val_p2)

        df_res = pd.DataFrame({
            "Mois": ["Jan", "Fév", "Mar", "Avr", "Mai", "Juin",
                     "Juil", "Août", "Sep", "Oct", "Nov", "Déc"],
            f"p {p1}": resultats_p1,
            f"p {p2}": resultats_p2
        })
        return df_res.set_index("Mois").T



def tracer_faconnage(df_res, titre="Volumes indicateurs",vmin=89000000, vmax=102200000, unite="Volume (m³)"):
    """
    Trace les séries p1 et p2 par mois avec zones colorées.
    Les indices du DataFrame sont utilisés automatiquement pour p1 et p2.
    
    df_res : DataFrame avec index = quantiles et colonnes = mois ['Jan', 'Fév', ...]
    titre  : titre du graphique
    vmin   : valeur min pour le remplissage rouge
    vmax   : valeur max pour le remplissage vert
    """
    mois = df_res.columns
    
    # Récupération automatique de p1 et p2
    p1_index, p2_index = df_res.index[:2]
    p1_values = df_res.loc[p1_index]
    p2_values = df_res.loc[p2_index]

    fig, ax = plt.subplots(figsize=(10, 5))

    # Remplissage au-dessus de p2 (vert)
    ax.fill_between(mois, p2_values, y2=vmax, 
                    color='green', alpha=0.2, label='Satisfaisant')

    # Remplissage entre p1 et p2 (orange)
    ax.fill_between(mois, p1_values, p2_values, 
                    where=(p2_values >= p1_values), 
                    color='orange', alpha=0.2, label='Vigilance')

    # Remplissage sous p1 (rouge)
    ax.fill_between(mois, p1_values, y2=vmin, 
                    color='red', alpha=0.2, label='Alerte')

    # Courbes p1 et p2
    ax.plot(mois, p2_values, marker='o', color='orange', label=p2_index)
    ax.plot(mois, p1_values, marker='o', color='red', label=p1_index)

    for m in ['Jan', 'Mai', 'Oct']:
        ax.text(m, p1_values[m], f"{p1_values[m]}", color='black', ha='center', va='bottom', fontsize=9)
        ax.text(m, p2_values[m], f"{p2_values[m]}", color='black', ha='center', va='bottom', fontsize=9)


    ax.set_title(titre)
    ax.set_xlabel("Mois")
    ax.set_ylabel(unite)
    ax.grid(True)
    
    # Légende à droite
    ax.legend(loc='center left', bbox_to_anchor=(1, 0.5))

    plt.tight_layout()
    return fig

