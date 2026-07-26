import sqlite3
import pandas as pd
from datetime import datetime

DB_NAME = "djeff_aluminium.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # Table Tarifs (Matières, Accessoires, Options, Couleurs)
    c.execute('''CREATE TABLE IF NOT EXISTS tarifs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                categorie TEXT, nom TEXT, prix REAL, unite TEXT)''')
    
    # Table Clients
    c.execute('''CREATE TABLE IF NOT EXISTS clients (
                id INTEGER PRIMARY KEY AUTOINCREMENT, nom TEXT, prenom TEXT, 
                telephone TEXT, adresse TEXT, wilaya TEXT, commune TEXT, email TEXT)''')
    
    # Table Fournisseurs
    c.execute('''CREATE TABLE IF NOT EXISTS fournisseurs (
                id INTEGER PRIMARY KEY AUTOINCREMENT, nom TEXT, telephone TEXT, 
                email TEXT, adresse TEXT, produits TEXT)''')
    
    # Table Stock
    c.execute('''CREATE TABLE IF NOT EXISTS stock (
                id INTEGER PRIMARY KEY AUTOINCREMENT, nom TEXT, categorie TEXT, 
                quantite REAL, seuil_alerte REAL)''')
    
    # Table Devis
    c.execute('''CREATE TABLE IF NOT EXISTS devis (
                id INTEGER PRIMARY KEY AUTOINCREMENT, numero TEXT, client_id INTEGER, 
                date TEXT, total REAL, marge REAL, statut TEXT,
                FOREIGN KEY(client_id) REFERENCES clients(id))''')
    
    # Table Lignes Devis
    c.execute('''CREATE TABLE IF NOT EXISTS lignes_devis (
                id INTEGER PRIMARY KEY AUTOINCREMENT, devis_id INTEGER, 
                designation TEXT, details TEXT, quantite REAL, prix_unitaire REAL, total REAL,
                FOREIGN KEY(devis_id) REFERENCES devis(id))''')

    # Table Historique Prix
    c.execute('''CREATE TABLE IF NOT EXISTS historique_prix (
                id INTEGER PRIMARY KEY AUTOINCREMENT, item TEXT, ancien_prix REAL, 
                nouveau_prix REAL, date TEXT)''')

    # Insertion de données par défaut si vide
    c.execute("SELECT COUNT(*) FROM tarifs")
    if c.fetchone()[0] == 0:
        defaults = [
            ('Matière', 'Profilé Aluminium', 1500, 'DA/ml'), ('Matière', 'Profilé PVC', 1200, 'DA/ml'),
            ('Matière', 'Double vitrage', 4500, 'DA/m2'), ('Matière', 'Triple vitrage', 7500, 'DA/m2'),
            ('Accessoire', 'Poignée', 800, 'DA/u'), ('Accessoire', 'Serrure', 2500, 'DA/u'),
            ('Option', 'Oscillo-battant', 3500, 'DA/u'), ('Option', 'Volet motorisé', 18000, 'DA/u'),
            ('Couleur', 'Blanc', 0, 'DA'), ('Couleur', 'Gris Anthracite', 1500, 'DA/ml'),
            ('Couleur', 'Imitation Bois', 2500, 'DA/ml')
        ]
        c.executemany("INSERT INTO tarifs (categorie, nom, prix, unite) VALUES (?, ?, ?, ?)", defaults)

    conn.commit()
    conn.close()

def execute_query(query, params=(), fetch=False):
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query(query, conn) if fetch else None
    c = conn.cursor()
    c.execute(query, params)
    conn.commit()
    if not fetch:
        conn.close()
        return c.lastrowid
    conn.close()
    return df

def get_prix(categorie, nom):
    df = execute_query("SELECT prix FROM tarifs WHERE categorie=? AND nom=?", (categorie, nom), fetch=True)
    return df.iloc[0]['prix'] if not df.empty else 0
