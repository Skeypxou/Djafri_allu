import sqlite3
import pandas as pd
from datetime import datetime

DB_NAME = "djeff_aluminium.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # Table Tarifs
    c.execute('''CREATE TABLE IF NOT EXISTS tarifs (
        id INTEGER PRIMARY KEY, categorie TEXT, nom TEXT, prix REAL, unite TEXT)''')
    
    # Table Clients
    c.execute('''CREATE TABLE IF NOT EXISTS clients (
        id INTEGER PRIMARY KEY, nom TEXT, prenom TEXT, telephone TEXT, 
        adresse TEXT, wilaya TEXT, commune TEXT, email TEXT)''')
    
    # Table Fournisseurs
    c.execute('''CREATE TABLE IF NOT EXISTS fournisseurs (
        id INTEGER PRIMARY KEY, nom TEXT, telephone TEXT, email TEXT, 
        adresse TEXT, produits TEXT)''')

    # Table Stock
    c.execute('''CREATE TABLE IF NOT EXISTS stock (
        id INTEGER PRIMARY KEY, nom TEXT, quantite REAL, seuil_alerte REAL)''')

    # Table Devis
    c.execute('''CREATE TABLE IF NOT EXISTS devis (
        id INTEGER PRIMARY KEY, numero TEXT, client_id INTEGER, date TEXT, 
        total_ht REAL, tva REAL, total_ttc REAL, acompte REAL, reste REAL, 
        statut TEXT)''')

    # Table Lignes Devis
    c.execute('''CREATE TABLE IF NOT EXISTS lignes_devis (
        id INTEGER PRIMARY KEY, devis_id INTEGER, designation TEXT, 
        largeur REAL, hauteur REAL, quantite INTEGER, prix_unitaire REAL, 
        total_ligne REAL)''')

    # Insertion de tarifs par défaut si vide
    c.execute("SELECT COUNT(*) FROM tarifs")
    if c.fetchone()[0] == 0:
        tarifs_defaut = [
            ('Matière', 'Profilé Aluminium', 850, 'DA/ml'),
            ('Matière', 'Profilé PVC', 600, 'DA/ml'),
            ('Matière', 'Double vitrage', 3500, 'DA/m2'),
            ('Accessoire', 'Poignée', 1200, 'DA/u'),
            ('Accessoire', 'Serrure', 4500, 'DA/u'),
            ('Option', 'Oscillo-battant', 3500, 'DA/u'),
            ('Couleur', 'Blanc', 0, 'DA'),
            ('Couleur', 'Gris Anthracite', 1500, 'DA/u')
        ]
        c.executemany("INSERT INTO tarifs (categorie, nom, prix, unite) VALUES (?,?,?,?)", tarifs_defaut)

    conn.commit()
    conn.close()

def execute_query(query, params=(), fetch=False):
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute(query, params)
    if fetch:
        data = c.fetchall()
        conn.close()
        return data
    conn.commit()
    conn.close()
    return c.lastrowid

def get_df(query, params=()):
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df
