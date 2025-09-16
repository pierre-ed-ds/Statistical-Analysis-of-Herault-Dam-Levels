#%% Imports
import sys, os
import tkinter as tk  
from tkinter import filedialog, messagebox
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg 
from matplotlib.backends.backend_tkagg import NavigationToolbar2Tk
import mplcursors
import ttkbootstrap as tb
from ttkbootstrap.constants import *

from interpolation import cote_to_volume, volume_to_cote
from prep_data import charger_donnees, simuler_salagou
from prep_graph import tracer_faconnage

class SplashScreen(tk.Toplevel):
    def __init__(self, root, text="Chargement…"):
        super().__init__(root)
        self.root = root
        self.overrideredirect(True)  # pas de bordure

        # Couleur de fond moderne
        self.configure(bg="white")

        # Taille et centrage
        width, height = 500, 250
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        self.geometry(f"{width}x{height}+{x}+{y}")

        # Label titre stylé
        self.label = tk.Label(
            self, text=text, 
            font=("Helvetica", 18, "bold"), 
            fg="black", bg="white"
        )
        self.label.pack(pady=40)

        # Barre de progression
        style = tb.Style()
        self.progress = tb.Progressbar(
            self, bootstyle="info-striped", length=300, mode="indeterminate"
        )
        self.progress.pack(pady=20)
        self.progress.start(10)  # vitesse animation

class SalagouApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Simulation Barrage")
        self.root.state("zoomed")  # Windows
        self.root.minsize(800, 600)
        # ---------------- Notebook principal ----------------
        self.notebook = tb.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True)

        # Onglets
        self.tab_simulation = tb.Frame(self.notebook)
        self.tab_indicateurs = tb.Frame(self.notebook)

        self.notebook.add(self.tab_simulation, text="Récupération des données")
        self.notebook.add(self.tab_indicateurs, text="Indicateurs du barrage")

        # Construire les interfaces
        self.build_tab_simulation()
        self.build_tab_indicateurs()

    # ------------------------------------------------------------------
    # Onglet 1 : Simulation
    # ------------------------------------------------------------------
    def build_tab_simulation(self):
        # PanedWindow principal (gauche = paramètres, droite = affichage)
        self.main_pane = tb.PanedWindow(self.tab_simulation, orient="horizontal")
        self.main_pane.pack(fill="both", expand=True)

        # ================== Panneau gauche : paramètres ==================
        self.left_frame = tb.Frame(self.main_pane, padding=10)
        self.left_frame.grid_columnconfigure(0, weight=1)

        # Ajout du panneau gauche au PanedWindow
        self.main_pane.add(self.left_frame, weight=1)

        # Fichier CSV
        tb.Label(self.left_frame, text="Fichier CSV :").grid(row=0, column=0, sticky="w", pady=3)
        self.file_entry = tb.Entry(self.left_frame)
        self.file_entry.grid(row=1, column=0, sticky="ew", pady=3)
        tb.Button(self.left_frame, text="Parcourir", command=self.select_file, bootstyle="info").grid(
            row=2, column=0, sticky="ew", pady=3
        )

        # Paramètres
        tb.Label(self.left_frame, text="Barrage :").grid(row=3, column=0, sticky="w", pady=3)

        # Variable pour stocker le code de la station sélectionnée
        self.code_station = tb.IntVar(value=34)

        # Dictionnaire pour mapper les noms de stations aux codes
        self.stations_dict = {
            "Salagou": 34,
            "Olivettes": 32
        }

        self.nom_station = tb.StringVar()
        self.station_combobox = tb.Combobox(self.left_frame, textvariable=self.nom_station)
        self.station_combobox.grid(row=4, column=0, sticky="ew", pady=3)

        # Définir les valeurs du combobox avec les noms des stations
        self.station_combobox['values'] = list(self.stations_dict.keys())
        self.station_combobox.set("Salagou")  # Valeur par défaut

        # Lier un événement pour mettre à jour le code quand la sélection change
        self.station_combobox.bind('<<ComboboxSelected>>', self.on_station_select)

        tb.Label(self.left_frame, text="Année début (exclue) :").grid(row=5, column=0, sticky="w", pady=3)
        self.date_debut = tb.IntVar(value=1997)
        tb.Entry(self.left_frame, textvariable=self.date_debut).grid(row=6, column=0, sticky="ew", pady=3)

        tb.Label(self.left_frame, text="Année fin (exclue) :").grid(row=7, column=0, sticky="w", pady=3)
        self.date_fin = tb.IntVar(value=2025)
        tb.Entry(self.left_frame, textvariable=self.date_fin).grid(row=8, column=0, sticky="ew", pady=3)

        tb.Label(self.left_frame, text="Augmentation évap. (%) :").grid(row=9, column=0, sticky="w", pady=3)
        self.evap_pct = tb.DoubleVar(value=10)
        tb.Entry(self.left_frame, textvariable=self.evap_pct).grid(row=10, column=0, sticky="ew", pady=3)

        tb.Label(self.left_frame, text="Réduction entrées (%) :").grid(row=11, column=0, sticky="w", pady=3)
        self.entree_pct = tb.DoubleVar(value=10)
        tb.Entry(self.left_frame, textvariable=self.entree_pct).grid(row=12, column=0, sticky="ew", pady=3)

        tb.Button(self.left_frame, text="Lancer la simulation", command=self.run_simulation, bootstyle="cosmo").grid(
            row=13, column=0, pady=10, sticky="ew"
        )

        # Choix affichage
        self.update_table_choices()
        tb.Label(self.left_frame, text="Afficher :").grid(row=14, column=0, sticky="w", pady=3)

        self.table_choice = tb.Combobox(
            self.left_frame,
            values=self.table_choices,
            state="readonly",
            bootstyle="primary"
        )
        self.table_choice.grid(row=15, column=0, sticky="ew", pady=3)

        # Définir la première valeur comme valeur par défaut
        if self.table_choices:
            self.table_choice.set(self.table_choices[0])

        tb.Button(self.left_frame, text="Afficher tableau", command=self.display_selected_table, bootstyle="info").grid(
            row=16, column=0, pady=3, sticky="ew"
        )

        # ================== Panneau droit : visualisations ==================
        self.right_frame = tb.Frame(self.main_pane, padding=10)
        self.right_frame.grid_columnconfigure(0, weight=1)
        self.right_frame.grid_rowconfigure(0, weight=1)

        # Ajout du panneau droit
        self.main_pane.add(self.right_frame, weight=10)  # extensible

        # PanedWindow interne (vertical : tableau en haut, graph en bas)
        self.paned = tb.PanedWindow(self.right_frame, orient="vertical")
        self.paned.pack(fill="both", expand=True)

        # Frame tableau
        self.frame_table = tb.Frame(self.paned)
        self.frame_table.grid_columnconfigure(0, weight=1)
        self.frame_table.grid_rowconfigure(0, weight=1)

        # Frame graphique
        self.frame_graph = tb.Frame(self.paned)
        self.frame_graph.grid_columnconfigure(0, weight=1)
        self.frame_graph.grid_rowconfigure(0, weight=1)

        # ⚖️ Ajustement des poids : moins de place au tableau
        self.paned.add(self.frame_table, weight=1)   # poids réduit
        self.paned.add(self.frame_graph, weight=3)   # graphique plus grand

        # ====== Conteneur pour Treeview + Scrollbars ======
        self.table_container = tb.Frame(self.frame_table)
        self.table_container.grid(row=0, column=0, sticky="nsew")

        # Configuration grille dans le container
        self.table_container.grid_rowconfigure(0, weight=1)
        self.table_container.grid_columnconfigure(0, weight=1)

        # Treeview
        self.tree = tb.Treeview(
            self.table_container,
            show="headings",
            bootstyle="table"
        )
        self.tree.grid(row=0, column=0, sticky="nsew")

        # Scrollbars
        self.tree_scroll_y = tb.Scrollbar(self.table_container, orient="vertical", command=self.tree.yview)
        self.tree_scroll_y.grid(row=0, column=1, sticky="ns")

        # Relier Treeview <-> Scrollbars
        self.tree.configure(yscrollcommand=self.tree_scroll_y.set)

        # Boutons d’export
        self.button_frame = tb.Frame(self.frame_table)
        self.button_frame.grid(row=1, column=0, pady=5, sticky="e")
        
        self.download_table_btn = tb.Button(
            self.button_frame,
            text="Télécharger le tableau",
            bootstyle="success-outline",
            command=self.export_table
        )
        self.download_table_btn.pack(side="left", padx=5)
        
        self.download_graph_btn = tb.Button(
            self.button_frame,
            text="Télécharger le graphique",
            bootstyle="info-outline",
            command=self.export_graph
        )
        self.download_graph_btn.pack(side="left", padx=5)

    # ================== Fonction export ==================
    def export_table(self):
        if not hasattr(self, "canvas") or self.canvas is None:
            messagebox.showwarning("Attention", "Aucun tableau à exporter.", parent=self.root)
            return
        # Récupérer les données du Treeview
        cols = self.tree["columns"]
        data = [cols]  # première ligne = en-têtes
        for row_id in self.tree.get_children():
            data.append(self.tree.item(row_id)["values"])

        df = pd.DataFrame(data[1:], columns=data[0])

        # Choisir où sauvegarder
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("Excel files", "*.xlsx")],
            title="Enregistrer le tableau"
        )

        if file_path:
            if file_path.endswith(".xlsx"):
                # Excel gère automatiquement l'encodage
                df.to_excel(file_path, index=False)
            else:
                # CSV : préciser l'encodage UTF-8 pour les caractères spéciaux
                df.to_csv(file_path, index=False, sep=";", encoding="utf-8-sig")
    
    def export_graph(self):
        if not hasattr(self, "canvas") or self.canvas is None:
            messagebox.showwarning("Attention", "Aucun graphique à exporter.", parent=self.root)
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG Image", "*.png"), ("JPEG Image", "*.jpg"), ("PDF File", "*.pdf")],
            title="Enregistrer le graphique"
        )

        if file_path:
            # Récupérer la figure depuis canvas
            fig = self.canvas.figure
            fig.savefig(file_path, dpi=300, bbox_inches="tight")

    # ------------------------------------------------------------------
    # Onglet 2 : Indicateurs
    # ------------------------------------------------------------------
    def build_tab_indicateurs(self):
        # Configurations des colonnes de l'onglet
        self.tab_indicateurs.grid_columnconfigure(0, weight=1)  # colonne principale (lâchures + paramètres + bouton)
        self.tab_indicateurs.grid_columnconfigure(1, weight=0)  # colonne pour le tableau des valeurs
        self.tab_indicateurs.grid_rowconfigure(3, weight=1)     # graphique prend toute la hauteur restante

        # Tableau des valeurs (à droite des paramètres et boutons)
        self.frame_tableau_valeurs = tb.Labelframe(self.tab_indicateurs, text="Tableau valeurs indicateurs", padding=10)
        self.frame_tableau_valeurs.grid(row=0, column=1, rowspan=3, sticky="nsew", padx=10, pady=10)
        self.tab_indicateurs.grid_columnconfigure(1, weight=1)

        # Treeview pour afficher les valeurs
        self.tree_indicateurs = tb.Treeview(self.frame_tableau_valeurs, show="headings", bootstyle="table")
        self.tree_indicateurs.pack(fill="both", expand=True)

        # Lâchures mensuelles
        frame_lachures = tb.Labelframe(self.tab_indicateurs, text="Lâchures mensuelles (m³)", padding=10)
        frame_lachures.grid(row=0, column=0, sticky="ew", padx=10, pady=10)

        mois_noms = ["Jan", "Fév", "Mar", "Avr", "Mai", "Juin",
                     "Juil", "Août", "Sep", "Oct", "Nov", "Déc"]

        self.lachures_vars = []
        for col, mois in enumerate(mois_noms):
            tb.Label(frame_lachures, text=mois).grid(row=0, column=col, padx=3, pady=3)
        for col in range(12):
            var = tk.DoubleVar(value=0)
            self.lachures_vars.append(var)
            tb.Entry(frame_lachures, textvariable=var, width=8).grid(row=1, column=col, padx=3, pady=3)

        # Paramètres indicateurs
        frame_params = tb.Labelframe(self.tab_indicateurs, text="Paramètres indicateurs", padding=10)
        frame_params.grid(row=1, column=0, sticky="ew", padx=10, pady=10)

        self.percentile_bas = tk.DoubleVar(value=25)
        self.percentile_haut = tk.DoubleVar(value=50)
        self.cote_min = tk.DoubleVar(value=137)
        self.cote_max = tk.DoubleVar(value=139)

        tb.Label(frame_params, text="Percentile bas (%) :").grid(row=0, column=0, sticky="e", padx=5, pady=3)
        tb.Entry(frame_params, textvariable=self.percentile_bas, width=8).grid(row=0, column=1, sticky="w", padx=5, pady=3)

        tb.Label(frame_params, text="Percentile haut (%) :").grid(row=0, column=2, sticky="e", padx=5, pady=3)
        tb.Entry(frame_params, textvariable=self.percentile_haut, width=8).grid(row=0, column=3, sticky="w", padx=5, pady=3)

        tb.Label(frame_params, text="Cote minimale :").grid(row=1, column=0, sticky="e", padx=5, pady=3)
        tb.Entry(frame_params, textvariable=self.cote_min, width=8).grid(row=1, column=1, sticky="w", padx=5, pady=3)

        tb.Label(frame_params, text="Cote maximale :").grid(row=1, column=2, sticky="e", padx=5, pady=3)
        tb.Entry(frame_params, textvariable=self.cote_max, width=8).grid(row=1, column=3, sticky="w", padx=5, pady=3)

        # Bouton validation
        tb.Button(self.tab_indicateurs, text="Valider indicateurs", bootstyle="success",
                  command=self.valider_indicateurs).grid(row=2, column=0, pady=10)
        # Choix du mode volume/cote
        self.mode_indicateurs = tk.StringVar(value="volume")
        frame_mode = tb.Labelframe(self.tab_indicateurs, text="Mode d'affichage", padding=10)
        frame_mode.grid(row=2, column=1, sticky="ew", padx=10, pady=10)
        # Lier la mise à jour automatique du graphique
        self.mode_indicateurs.trace_add("write", lambda *args: self.display_graph())

        tk.Radiobutton(frame_mode, text="Volume (m³)", variable=self.mode_indicateurs,
                       value="volume", command=self.actualiser_indicateurs).pack(side="left", padx=5)
        tk.Radiobutton(frame_mode, text="Cote (mNGF)", variable=self.mode_indicateurs,
                       value="cote", command=self.actualiser_indicateurs).pack(side="left", padx=5)
        
        # Bouton Exporter à droite
        tb.Button(frame_mode, text="Exporter", bootstyle="info",
                  command=self.exporter_indicateurs).pack(side="left", padx=10)

        # Graphique
        self.frame_graph_indicateurs = tb.Labelframe(self.tab_indicateurs, text="Graphique indicateurs", padding=10)
        self.frame_graph_indicateurs.grid(row=3, column=0,columnspan=2, sticky="nsew", padx=10, pady=10)
        self.frame_graph_indicateurs.grid_columnconfigure(0, weight=1)
        self.frame_graph_indicateurs.grid_rowconfigure(0, weight=1)

    def select_file(self):
        filepath = filedialog.askopenfilename(
            parent=self.root,  # <-- obligatoire pour éviter TclError
            filetypes=[("CSV files", "*.csv")]
        )   
        if filepath:
            self.filepath = filepath
            self.file_entry.delete(0, tk.END)
            self.file_entry.insert(0, filepath)
    
    def on_station_select(self, event):
        """Met à jour le code station et les cotes quand une station est sélectionnée"""
        selected_station = self.nom_station.get()
        if selected_station in self.stations_dict:
            self.code_station.set(self.stations_dict[selected_station])

            # Mettre à jour les cotes min/max en fonction de la station
            if self.code_station.get() == 32:  # Olivettes
                self.cote_min.set(152)
                self.cote_max.set(163)
                if hasattr(self, 'cote_min_entry'):
                    self.cote_min_entry.delete(0, tk.END)
                    self.cote_min_entry.insert(0, "152")
                if hasattr(self, 'cote_max_entry'):
                    self.cote_max_entry.delete(0, tk.END)
                    self.cote_max_entry.insert(0, "163")
            else:  # Salagou
                self.cote_min.set(137)
                self.cote_max.set(139)
                if hasattr(self, 'cote_min_entry'):
                    self.cote_min_entry.delete(0, tk.END)
                    self.cote_min_entry.insert(0, "137")
                if hasattr(self, 'cote_max_entry'):
                    self.cote_max_entry.delete(0, tk.END)
                    self.cote_max_entry.insert(0, "139")

            print(f"Station sélectionnée: {selected_station}, Code: {self.code_station.get()}")

    def save_graphique(self):
    # Ouvrir une boîte de dialogue pour choisir le fichier
        if hasattr(self, "fig"):
            file_path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG", "*.png"), ("JPEG", "*.jpg"), ("PDF", "*.pdf"), ("All files", "*.*")]
        )
        if file_path:
            self.fig.savefig(file_path)
            
    def run_simulation(self):
        if not self.filepath:
            messagebox.showerror("Erreur", "Veuillez sélectionner un fichier CSV.", parent=self.root)
            return
        
        try:
            df = charger_donnees(
                self.filepath,
                self.code_station.get(),
                self.date_debut.get(),
                self.date_fin.get()
            )
            self.df_filtered = df

            if df.empty:
                messagebox.showwarning("Attention", "Aucune donnée trouvée avec ces paramètres.", parent=self.root)
                return

            self.results = simuler_salagou(
                df,
                self.evap_pct.get() / 100,
                self.entree_pct.get() / 100
            )

            self.update_table_choices()
            self.table_choice['values'] = self.table_choices
            self.table_choice.set('')  # Reset choix après simulation
            self.display_selected_table()  # Afficher le tableau par défaut

            messagebox.showinfo("Succès", "Simulation terminée. Choisissez un tableau à afficher.", parent=self.root)

        except Exception as e:
            messagebox.showerror("Erreur", str(e), parent=self.root)

    def update_table_choices(self):
        evap_pct_str = f"{self.evap_pct.get():.0f}%"
        entree_pct_str = f"{self.entree_pct.get():.0f}%"
        self.table_choices = [
            "Volumes début de mois",
            "Entrées naturelles",
            f"Entrées naturelles -{entree_pct_str}",
            "Evaporations",
            f"Evaporations +{evap_pct_str}"
        ]

    def display_selected_table(self):
        if self.results is None:
            messagebox.showwarning("Attention", "Veuillez d'abord lancer la simulation.", parent=self.root)
            return

        choix = self.table_choice.get()
        if choix == "":
            choix = self.table_choices[0]
            self.table_choice.set(choix)

        df = self.results["donnees_simulees"].copy()

        if "ANNEE" not in df.columns or "MOIS_NUM" not in df.columns:
            df["ANNEE"] = df["MOIS"].dt.year
            df["MOIS_NUM"] = df["MOIS"].dt.month

        entree_pct = self.entree_pct.get()
        evap_pct = self.evap_pct.get()

        mapping = {
            "Volumes début de mois": "VOLUME_PREMIER_JOUR",
            "Entrées naturelles": "ENTREE_NATURELLE",
            f"Entrées naturelles -{entree_pct:.0f}%": "ENTREE_CLIMAT",
            "Evaporations": "EVAPORATION",
            f"Evaporations +{evap_pct:.0f}%": "EVAP_CLIMAT",
        }

        variable = mapping.get(choix)
        if variable is None:
            messagebox.showerror("Erreur", "Choix de tableau inconnu.", parent=self.root)
            return

        # Pivot du tableau sélectionné
        pivot_df = df.pivot(index="ANNEE", columns="MOIS_NUM", values=variable)

        # Affichage du tableau dans Treeview
        self.show_pivot(pivot_df)

        # 🔹 Sauvegarde en mémoire pour un autre onglet
        self.df_pivot_volume = df.pivot(index="ANNEE", columns="MOIS_NUM", values="VOLUME_PREMIER_JOUR")
        self.df_pivot_entree_clim = df.pivot(index="ANNEE", columns="MOIS_NUM", values="ENTREE_CLIMAT")
        self.df_pivot_evap_clim = df.pivot(index="ANNEE", columns="MOIS_NUM", values="EVAP_CLIMAT")
        self.afficher_graphique(pivot_df, variable)

    def show_pivot(self, pivot_df):
        if hasattr(self, 'tree'):
            self.tree.destroy()
        self.tree = tk.ttk.Treeview(self.frame_table, show="headings", bootstyle="table")
        self.tree.grid(row=0, column=0, sticky='nsew')

        # Nettoyer l'arbre
        for row in self.tree.get_children():
            self.tree.delete(row)

        # Colonnes mois en français abrégé
        mois_noms = ["Jan", "Fév", "Mar", "Avr", "Mai", "Juin", "Juil", "Août", "Sep", "Oct", "Nov", "Déc"]
        colonnes = ["Année"] + mois_noms
        self.tree.config(columns=colonnes)

        for col in colonnes:
            self.tree.heading(col, text=col)
            self.tree.column(col, anchor='center', width=60)

        # Insertion des données pivotées dans le Treeview
        for annee, row in pivot_df.iterrows():
            valeurs = [annee] + [round(v, 2) if pd.notna(v) else "" for v in row]
            self.tree.insert("", tk.END, values=valeurs)

    
    def afficher_graphique(self, pivot_df, variable):
        if hasattr(self, 'canvas') and self.canvas:
            self.canvas.get_tk_widget().destroy()

        if hasattr(self, 'toolbar') and self.toolbar:
            self.toolbar.destroy()

        # Recréer le même mapping que dans display_selected_table
        entree_pct = self.entree_pct.get()
        evap_pct = self.evap_pct.get()

        mapping = {
            "Volumes début de mois": "VOLUME_PREMIER_JOUR",
            "Entrées naturelles": "ENTREE_NATURELLE",
            f"Entrées naturelles -{entree_pct:.0f}%": "ENTREE_CLIMAT",
            "Evaporations": "EVAPORATION",
            f"Evaporations +{evap_pct:.0f}%": "EVAP_CLIMAT",
        }

        # Retrouver le "nom humain"
        inverse_mapping = {v: k for k, v in mapping.items()}
        titre_variable = inverse_mapping.get(variable, variable)

        # Préparer la figure
        plt.style.use("seaborn-v0_8-whitegrid")
        fig, ax = plt.subplots(figsize=(6, 4))

        # Préparer les données
        df_long = pivot_df.reset_index().melt(
            id_vars='ANNEE',
            var_name='MOIS_NUM',
            value_name='valeur'
        )
        df_long = df_long.sort_values(['ANNEE', 'MOIS_NUM'])
        df_long['DATE'] = pd.to_datetime(
            df_long['ANNEE'].astype(str) + '-' +
            df_long['MOIS_NUM'].astype(str) + '-01'
        )

        if "EVAP" in variable.upper():
            couleur = "#E49630"
        else:
            couleur = "#1f77b4"

        # Tracé stylé
        line, = ax.plot(
            df_long['DATE'],
            df_long['valeur'],
            marker='o',
            markersize=8,
            markerfacecolor='white',
            markeredgewidth=2,
            markeredgecolor=couleur,
            linestyle='-',
            linewidth=2.5,
            color=couleur,
            alpha=0.85
        )

        ax.fill_between(
            df_long['DATE'],
            df_long['valeur'],
            df_long['valeur'].min(),
            color=couleur,
            alpha=0.1
        )

        scatter = ax.scatter(
            df_long['DATE'],
            df_long['valeur'],
            s=100,            # taille des points pour le focus
            facecolor="none", # invisible
            edgecolor="none", # invisible
            picker=True       # activable
        )

        # Titres et labels
        ax.set_title(f"{titre_variable}", fontsize=13, fontweight="bold")
        ax.set_xlabel("Année", fontsize=11)
        ax.set_ylabel(f"{titre_variable} (m³)", fontsize=11)

        # Mise en forme axe X
        fig.autofmt_xdate(rotation=30, ha="right")
        ax.xaxis.set_major_locator(mdates.YearLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))

        ax.grid(True, linestyle="--", alpha=0.6)
        fig.tight_layout()

        # Intégration dans Tkinter
        self.canvas = FigureCanvasTkAgg(fig, master=self.frame_graph)
        self.canvas.draw()
        self.canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew")

        # 🔹 Créer un sous-frame pour la toolbar
        toolbar_frame = tb.Frame(self.frame_graph)
        toolbar_frame.grid(row=1, column=0, sticky="ew")

        # 🔹 Toolbar dans ce sous-frame (pas de conflit pack/grid)
        self.toolbar = NavigationToolbar2Tk(self.canvas, toolbar_frame)
        self.toolbar.update()
        cursor = mplcursors.cursor(scatter, hover=True)
        # --- Interaction : clic sur un point ---
        @cursor.connect("add")
        def on_hover(sel):
            x, y = sel.target  # coordonnées du point
            date_str = mdates.num2date(x).strftime("%b %Y")
            sel.annotation.set_text(f"{date_str}\n{y:.0f} m³")
            sel.annotation.get_bbox_patch().set(fc="white", alpha=0.9)

        self.root.grid_columnconfigure(1, weight=1)

    def valider_indicateurs(self):
        #self.mode_indicateurs.set("volume")
        lachures = [var.get() for var in self.lachures_vars]
        p_bas = self.percentile_bas.get()
        p_haut = self.percentile_haut.get()

        print("Lâchures mensuelles :", lachures)
        print("Percentile bas :", p_bas)
        print("Percentile haut :", p_haut)

        # On garde les DataFrames transformés en mémoire pour un autre onglet
        self.df_deb_mois_long = self.prepare_for_graph(self.df_pivot_volume)
        self.df_entree_clim_long = self.prepare_for_graph(self.df_pivot_entree_clim)
        self.df_evap_clim_long = self.prepare_for_graph(self.df_pivot_evap_clim)

        self.display_graph() 

    def prepare_for_graph(self, df_pivot):
        """
        Transforme un DataFrame pivoté (ANNEE en index, MOIS_NUM en colonnes)
        en format long pour faconnage_graph.
        """
        df_long = df_pivot.reset_index().melt(
            id_vars="ANNEE", var_name="MOIS_NUM", value_name="valeur"
        )
        # Construire une vraie date
        df_long["DATE_RELEVE"] = pd.to_datetime(
            df_long["ANNEE"].astype(str) + "-" + df_long["MOIS_NUM"].astype(str) + "-01"
        )
        return df_long[["DATE_RELEVE", "MOIS_NUM", "valeur"]]
    
    def afficher_resultats_indicateurs(self, df_res):
        """Affiche le DataFrame df_res dans le Treeview de l'onglet indicateurs."""
        # Nettoyer
        self.tree_indicateurs.delete(*self.tree_indicateurs.get_children())
        self.tree_indicateurs["columns"] = list(df_res.columns)

        # Colonnes
        for col in df_res.columns:
            self.tree_indicateurs.heading(col, text=col)
            self.tree_indicateurs.column(col, anchor="center", width=50)

        # Lignes
        for _, row in df_res.iterrows():
            self.tree_indicateurs.insert("", "end", values=list(row))

    def faconnage_graph(self, debut_mois, entree_clim, evap_clim, p1=0.25, p2=0.5, vect_lach=None):
        """
        Construction du tableau de données pour nos indicateurs.
        """
        if vect_lach is None:
            vect_lach = [0]*12

        # Récupération du mode choisi (volume ou cote)
        mode = self.mode_indicateurs.get()  # défaut = volume

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
            
            if mode == "cote":
                val_p1 = volume_to_cote(val_p1,code=self.code_station.get())
                val_p2 = volume_to_cote(val_p2,code=self.code_station.get())

            resultats_p1.append(val_p1)
            resultats_p2.append(val_p2)

        df_res = pd.DataFrame({
            "Mois": ["Jan", "Fév", "Mar", "Avr", "Mai", "Juin",
                     "Juil", "Août", "Sep", "Oct", "Nov", "Déc"],
            f"q {p1}": resultats_p1,
            f"q {p2}": resultats_p2
        })

        # Arrondir selon le mode
        if mode == "cote":
            df_res.iloc[:, 1:] = df_res.iloc[:, 1:].round(2)  # 2 chiffres après la virgule
        else:
            df_res.iloc[:, 1:] = df_res.iloc[:, 1:].round(0).astype(int)
        self.df_indicateurs = df_res.copy()
        self.afficher_resultats_indicateurs(df_res)
        return df_res.set_index("Mois").T
    
    def display_graph(self):
        # Nettoyer l'ancien graphe
        for widget in self.frame_graph_indicateurs.winfo_children():
            widget.destroy()

        # Calcul des résultats
        res = self.faconnage_graph(
            debut_mois=self.df_deb_mois_long,
            entree_clim=self.df_entree_clim_long,
            evap_clim=self.df_evap_clim_long,
            p1=self.percentile_bas.get()/100,
            p2=self.percentile_haut.get()/100,
            vect_lach=[var.get() for var in self.lachures_vars]
        )
        vmin = self.cote_min.get()
        vmax = self.cote_max.get()
        if self.mode_indicateurs.get() == "cote":
            # Appliquer volume_to_cote sur tout le DataFrame
            #res = res.map(volume_to_cote)  
            res = res.round(2)
            unite = "Cote (mNGF)"
        else:
            res = res.round(0).astype(int)
            vmin = cote_to_volume(vmin,code=self.code_station.get())
            vmax = cote_to_volume(vmax,code=self.code_station.get())
            unite = "Volume (m³)"



        # Création de la figure
        self.fig = tracer_faconnage(res,titre="Indicateurs du barrage des Olivettes" if self.code_station.get() == 32 else "Indicateurs du barrage du Salagou", vmin=vmin, vmax=vmax, unite=unite)

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.frame_graph_indicateurs)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

        # --- Toolbar Tkinter ---
        toolbar_frame = tk.Frame(self.frame_graph_indicateurs)
        toolbar_frame.pack(fill="x")  # toolbar horizontale
        self.toolbar = NavigationToolbar2Tk(self.canvas, toolbar_frame)
        self.toolbar.update()

        # --- Interaction sur les points avec mplcursors ---
        ax = self.fig.axes[0]

        # Créer des scatter invisibles pour chaque courbe existante
        scatters = []
        for line in ax.get_lines():
            # On récupère les points x et y
            xdata = line.get_xdata()
            ydata = line.get_ydata()

            # Map mois texte vers positions numériques (scatter supporte les categories)
            scatter = ax.scatter(
                range(len(xdata)),   # positions numériques
                ydata,
                s=100,
                facecolor='none',
                edgecolor='none',
                picker=True
            )

            # Stocker les mois texte dans un attribut du scatter
            scatter.months = list(xdata)

            scatters.append(scatter)

        import mplcursors
        cursor = mplcursors.cursor(scatters, hover=True)  # ne suit que les points

        @cursor.connect("add")
        def on_hover(sel):
            x_idx, y = sel.target
            x_idx = int(round(x_idx))  # l'indice correspondant au mois
            months = sel.artist.months  # récupérer les mois texte
            month_str = months[x_idx] if x_idx < len(months) else f"Index {x_idx}"
            if self.mode_indicateurs.get() == "cote":
                y_str = f"{y:.2f}"
            else:
                y_str = f"{y:.0f}"
            sel.annotation.set_text(f"{month_str}\n{y_str} {unite}")
            sel.annotation.get_bbox_patch().set(fc="white", alpha=0.9)

        # Bouton pour télécharger
        btn_save = tb.Button(
            self.frame_graph_indicateurs,
            text="Télécharger graphique",
            bootstyle="info",
            command=self.save_graphique  # méthode à définir
        )
        btn_save.pack(pady=5)

    def exporter_indicateurs(self):
        """Exporte le tableau des indicateurs en CSV ou Excel."""
        if not hasattr(self, "df_indicateurs") or self.df_indicateurs.empty:
            messagebox.showwarning("Export impossible", "Aucun tableau à exporter. Lancez d'abord un calcul.")
            return

        # Boîte de dialogue pour choisir l’emplacement
        fichier = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("Fichier CSV", "*.csv"), ("Fichier Excel", "*.xlsx")],
            title="Enregistrer le tableau"
        )
        if not fichier:
            return  # annulé

        try:
            if fichier.endswith(".csv"):
                # Encodage UTF-8 avec BOM → lisible dans Excel et conserve les accents
                self.df_indicateurs.to_csv(fichier, sep=";", index=False, encoding="utf-8-sig")
            else:
                # Excel gère nativement l’UTF-8 via openpyxl
                self.df_indicateurs.to_excel(fichier, index=False, engine="openpyxl")

            messagebox.showinfo("Export réussi", f"Tableau exporté avec succès :\n{fichier}")
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible d'exporter : {e}")

    def actualiser_indicateurs(self):
        """Recalcule et met à jour le tableau/graph selon le mode choisi."""
        if not hasattr(self, "df_indicateurs"):
            return  # rien à recalculer si pas encore de données

        df = self.df_indicateurs.copy()
        # Réafficher
        self.afficher_resultats_indicateurs(df)

def on_closing(root):
    """Fermeture propre de l'application"""
    try:
        plt.close('all')   # ferme toutes les figures matplotlib
    except Exception:
        pass
    try:
        root.destroy()
    except Exception:
        pass

    # forcer la fin du process (utile avec PyInstaller)
    os._exit(0)

def main():
    root = tb.Window(themename='flatly')  # ttkbootstrap
    root.withdraw()  # cacher la fenêtre principale

    # Afficher splash
    # gestion de la fermeture
    root.protocol("WM_DELETE_WINDOW", lambda: on_closing(root))
    splash = SplashScreen(root, "Chargement des données…")

    # Lancer l'UI principale après 2s
    root.after(2000, lambda: show_main(root, splash))
    root.mainloop()

def show_main(root, splash):
    splash.destroy()
    root.deiconify()
    app = SalagouApp(root)

if __name__ == "__main__":
    main()

# %%
