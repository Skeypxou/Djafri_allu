import streamlit as st
import sqlite3
import pandas as pd
import datetime
import plotly.express as px
from streamlit_option_menu import option_menu
from streamlit_aggrid import AgGrid, GridOptionsBuilder
from fpdf import FPDF

# ==========================================
# 1. CONFIGURATION & BASE DE DONNÉES
# ==========================================
DB_NAME = "djeff_aluminium_erp.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS tarifs (id INTEGER PRIMARY KEY AUTOINCREMENT, categorie TEXT, nom TEXT, prix REAL, unite TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS clients (id INTEGER PRIMARY KEY AUTOINCREMENT, nom TEXT, prenom TEXT, telephone TEXT, adresse TEXT, wilaya TEXT, commune TEXT, email TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS fournisseurs (id INTEGER PRIMARY KEY AUTOINCREMENT, nom TEXT, telephone TEXT, email TEXT, adresse TEXT, produits TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS stock (id INTEGER PRIMARY KEY AUTOINCREMENT, nom TEXT, categorie TEXT, quantite REAL, seuil_alerte REAL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS devis (id INTEGER PRIMARY KEY AUTOINCREMENT, numero TEXT, client_id INTEGER, date TEXT, total REAL, marge REAL, statut TEXT, FOREIGN KEY(client_id) REFERENCES clients(id))''')
    c.execute('''CREATE TABLE IF NOT EXISTS lignes_devis (id INTEGER PRIMARY KEY AUTOINCREMENT, devis_id INTEGER, designation TEXT, details TEXT, quantite REAL, prix_unitaire REAL, total REAL, FOREIGN KEY(devis_id) REFERENCES devis(id))''')
    c.execute('''CREATE TABLE IF NOT EXISTS historique_prix (id INTEGER PRIMARY KEY AUTOINCREMENT, item TEXT, ancien_prix REAL, nouveau_prix REAL, date TEXT)''')

    c.execute("SELECT COUNT(*) FROM tarifs")
    if c.fetchone()[0] == 0:
        defaults = [
            ('Matière', 'Profilé Aluminium', 1500, 'DA/ml'), ('Matière', 'Profilé PVC', 1200, 'DA/ml'),
            ('Matière', 'Double vitrage', 4500, 'DA/m2'), ('Matière', 'Triple vitrage', 7500, 'DA/m2'),
            ('Matière', 'Vitrage teinté', 5500, 'DA/m2'), ('Matière', 'Vitrage sécurisé', 6500, 'DA/m2'),
            ('Accessoire', 'Poignée', 800, 'DA/u'), ('Accessoire', 'Serrure', 2500, 'DA/u'),
            ('Accessoire', 'Cylindre', 1500, 'DA/u'), ('Accessoire', 'Paumelles', 400, 'DA/u'),
            ('Accessoire', 'Roulettes', 1200, 'DA/u'), ('Accessoire', 'Crémone', 1800, 'DA/u'),
            ('Accessoire', 'Charnières', 600, 'DA/u'), ('Accessoire', 'Joints', 50, 'DA/ml'),
            ('Accessoire', 'Moustiquaires', 2000, 'DA/u'),
            ('Option', 'Oscillo-battant', 3500, 'DA/u'), ('Option', 'Coulissant', 5000, 'DA/u'),
            ('Option', 'Volet manuel', 8000, 'DA/u'), ('Option', 'Volet motorisé', 18000, 'DA/u'),
            ('Option', 'Motorisation portail', 25000, 'DA/u'), ('Option', 'Motorisation rideau', 35000, 'DA/u'),
            ('Option', 'Moustiquaire intégrée', 4500, 'DA/u'),
            ('Couleur', 'Blanc', 0, 'DA'), ('Couleur', 'Noir', 2000, 'DA/ml'),
            ('Couleur', 'Gris Anthracite', 1500, 'DA/ml'), ('Couleur', 'Bronze', 1800, 'DA/ml'),
            ('Couleur', 'Imitation Bois', 2500, 'DA/ml'), ('Couleur', 'Chêne Doré', 2800, 'DA/ml'),
            ('Couleur', 'Acajou', 3000, 'DA/ml')
        ]
        c.executemany("INSERT INTO tarifs (categorie, nom, prix, unite) VALUES (?, ?, ?, ?)", defaults)
        
    c.execute("SELECT COUNT(*) FROM stock")
    if c.fetchone()[0] == 0:
        stock_defaults = [
            ('Profilé Aluminium', 'Matière', 150, 50), ('Profilé PVC', 'Matière', 200, 50),
            ('Double vitrage', 'Matière', 50, 20), ('Serrures', 'Accessoire', 30, 10),
            ('Poignées', 'Accessoire', 100, 20)
        ]
        c.executemany("INSERT INTO stock (nom, categorie, quantite, seuil_alerte) VALUES (?, ?, ?, ?)", stock_defaults)

    conn.commit()
    conn.close()

def execute_query(query, params=(), fetch=False):
    conn = sqlite3.connect(DB_NAME)
    if fetch:
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    c = conn.cursor()
    c.execute(query, params)
    conn.commit()
    last_id = c.lastrowid
    conn.close()
    return last_id

def get_prix(categorie, nom):
    df = execute_query("SELECT prix FROM tarifs WHERE categorie=? AND nom=?", (categorie, nom), fetch=True)
    return df.iloc[0]['prix'] if not df.empty else 0


# ==========================================
# 2. MOTEUR DE CALCUL (AVEC IMPOSTE)
# ==========================================
class CalculateurDevis:
    def __init__(self, marge_beneficiaire=30):
        self.marge = marge_beneficiaire

    def calculer_element(self, largeur_mm, hauteur_mm, hauteur_imposte_mm, type_matiere, type_vitrage, couleur, accessoires, options, quantite=1, is_imposte_seule=False):
        largeur_m = largeur_mm / 1000
        hauteur_m = hauteur_mm / 1000
        hauteur_imposte_m = hauteur_imposte_mm / 1000
        
        # Gestion de la logique d'imposte
        if is_imposte_seule:
            # Si c'est une imposte seule, la hauteur principale est l'imposte
            hauteur_totale_m = hauteur_m
            perimetre_ml = 2 * (largeur_m + hauteur_totale_m)
            imp_txt = f"Imposte Seule H:{hauteur_mm}mm"
        else:
            # Sinon, on additionne la hauteur du vantail et de l'imposte
            hauteur_totale_m = hauteur_m + hauteur_imposte_m
            perimetre_ml = 2 * (largeur_m + hauteur_totale_m)
            
            # Ajout de la traverse d'imposte si > 0
            if hauteur_imposte_m > 0:
                perimetre_ml += largeur_m
            imp_txt = f" + Imposte:{hauteur_imposte_mm}mm" if hauteur_imposte_mm > 0 else ""
            
        # 1. Profilé
        prix_profil = get_prix('Matière', type_matiere)
        cout_profil = perimetre_ml * prix_profil
        
        # 2. Vitrage
        surface_m2 = largeur_m * hauteur_totale_m
        prix_vitrage = get_prix('Matière', type_vitrage)
        cout_vitrage = surface_m2 * prix_vitrage
        
        # 3. Couleur
        sup_color = get_prix('Couleur', couleur)
        cout_couleur = perimetre_ml * sup_color
        
        # 4. Accessoires & Options
        cout_accessoires = sum([get_prix('Accessoire', a) for a in accessoires])
        cout_options = sum([get_prix('Option', o) for o in options])
        
        # 5. Total
        cout_revient = (cout_profil + cout_vitrage + cout_couleur + cout_accessoires + cout_options) * quantite
        prix_vente = cout_revient * (1 + self.marge / 100)
        
        details = f"L:{largeur_mm}x H:{hauteur_mm}mm{imp_txt} | Mat: {type_matiere} | Vit: {type_vitrage} | Col: {couleur}"
        
        return {
            'cout_revient': round(cout_revient, 2),
            'prix_vente': round(prix_vente, 2),
            'marge': round(prix_vente - cout_revient, 2),
            'details': details
        }


# ==========================================
# 3. GÉNÉRATEUR PDF
# ==========================================
class DevisPDF(FPDF):
    def header(self):
        self.set_fill_color(30, 58, 138)
        self.rect(0, 0, 210, 35, 'F')
        self.set_font("Arial", 'B', 22)
        self.set_text_color(255, 255, 255)
        self.cell(0, 15, "DJEFF ALUMINIUM PRO", 0, 1, 'C')
        self.set_font("Arial", '', 10)
        self.cell(0, 10, "Zone d'Activité, Alger, Algérie | Tél: +213 XXX XXX XXX | RC: 00/00-0000000B", 0, 1, 'C')
        
    def footer(self):
        self.set_y(-20)
        self.set_font("Arial", 'I', 8)
        self.set_text_color(128)
        self.multi_cell(0, 5, "Conditions de paiement: 50% à la commande, 50% à la livraison. Garantie 5 ans. Délai de livraison 30 jours.", 0, 'C')

def generate_devis_pdf(devis_info, client_info, lignes, filename="Devis_DJEFF.pdf"):
    pdf = DevisPDF()
    pdf.add_page()
    
    pdf.set_y(45)
    pdf.set_font("Arial", 'B', 14)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(100, 10, f"DEVIS N°: {devis_info['numero']}", 0, 0)
    pdf.cell(0, 10, f"Date: {devis_info['date']}", 0, 1, 'R')
    
    pdf.set_font("Arial", '', 11)
    pdf.set_fill_color(243, 244, 246)
    pdf.cell(0, 6, f"Client: {client_info['nom']} {client_info['prenom']}", 0, 1, '', fill=True)
    pdf.cell(0, 6, f"Adresse: {client_info['adresse']}, {client_info['wilaya']}", 0, 1, '', fill=True)
    pdf.cell(0, 6, f"Téléphone: {client_info['telephone']}", 0, 1, '', fill=True)
    pdf.ln(5)
    
    pdf.set_fill_color(30, 58, 138)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(70, 8, "Désignation", 1, 0, 'C', True)
    pdf.cell(55, 8, "Détails", 1, 0, 'C', True)
    pdf.cell(15, 8, "Qté", 1, 0, 'C', True)
    pdf.cell(20, 8, "P.U", 1, 0, 'C', True)
    pdf.cell(30, 8, "Total", 1, 1, 'C', True)
    
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", '', 9)
    for ligne in lignes:
        pdf.cell(70, 8, ligne['designation'], 1, 0)
        pdf.cell(55, 8, ligne['details'][:28], 1, 0)
        pdf.cell(15, 8, str(ligne['quantite']), 1, 0, 'C')
        pdf.cell(20, 8, f"{ligne['prix_unitaire']:,.0f}", 1, 0, 'R')
        pdf.cell(30, 8, f"{ligne['total']:,.0f} DA", 1, 1, 'R')
        
    pdf.ln(5)
    pdf.set_x(120)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(40, 10, "Total TTC:", 1, 0, 'R')
    pdf.cell(30, 10, f"{devis_info['total']:,.0f} DA", 1, 1, 'R')
    
    pdf.set_x(120)
    pdf.set_font("Arial", '', 10)
    pdf.cell(40, 10, "Acompte (50%):", 1, 0, 'R')
    pdf.cell(30, 10, f"{devis_info['total']*0.5:,.0f} DA", 1, 1, 'R')
    
    pdf.ln(15)
    pdf.set_font("Arial", '', 10)
    pdf.cell(90, 10, "Signature Client", 0, 0, 'C')
    pdf.cell(90, 10, "Cachet Entreprise", 0, 1, 'C')
    
    pdf.output(filename)
    return filename


# ==========================================
# 4. VUES & INTERFACE UTILISATEUR
# ==========================================

def view_dashboard():
    st.title("📊 Tableau de Bord")
    df_devis = execute_query("SELECT * FROM devis", fetch=True)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1: st.metric("Nombre Total de Devis", len(df_devis))
    with col2: st.metric("CA Estimé (DA)", f"{df_devis['total'].sum():,.0f}" if not df_devis.empty else 0)
    with col3: st.metric("Marge Estimée (DA)", f"{df_devis['marge'].sum():,.0f}" if not df_devis.empty else 0)
    
    now = datetime.datetime.now()
    df_devis['date'] = pd.to_datetime(df_devis['date'])
    df_mois = df_devis[df_devis['date'].dt.month == now.month]
    with col4: st.metric("Devis ce Mois", len(df_mois))
    
    st.subheader("Évolution du Chiffre d'Affaires")
    if not df_devis.empty:
        chart_data = df_devis.groupby(df_devis['date'].dt.to_period('M')).sum(numeric_only=True).reset_index()
        chart_data['date'] = chart_data['date'].astype(str)
        fig = px.bar(chart_data, x='date', y='total', text='total', title="CA par Mois", labels={'total':'Total (DA)', 'date':'Mois'})
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Aucune donnée disponible.")

def view_clients():
    st.title("👤 Gestion des Clients")
    with st.form("add_client"):
        col1, col2 = st.columns(2)
        nom = col1.text_input("Nom*")
        prenom = col2.text_input("Prénom*")
        telephone = col1.text_input("Téléphone*")
        email = col2.text_input("Email")
        adresse = st.text_input("Adresse")
        col3, col4 = st.columns(2)
        wilaya = col3.text_input("Wilaya")
        commune = col4.text_input("Commune")
        
        if st.form_submit_button("Ajouter le Client", type="primary"):
            if nom and telephone:
                execute_query("INSERT INTO clients (nom, prenom, telephone, email, adresse, wilaya, commune) VALUES (?, ?, ?, ?, ?, ?, ?)",
                              (nom, prenom, telephone, email, adresse, wilaya, commune))
                st.success("Client ajouté avec succès !")
                st.rerun()
            else:
                st.error("Veuillez remplir les champs obligatoires (*)")
                
    st.subheader("Liste des Clients")
    df_clients = execute_query("SELECT id, nom, prenom, telephone, wilaya, commune FROM clients", fetch=True)
    st.dataframe(df_clients, use_container_width=True, hide_index=True)

def view_devis():
    st.title("📄 Création de Devis")
    
    df_clients = execute_query("SELECT id, nom || ' ' || prenom as Nom FROM clients", fetch=True)
    if df_clients.empty:
        st.warning("Veuillez d'abord ajouter un client dans l'onglet 'Clients'.")
        return
        
    col1, col2 = st.columns([1, 2])
    with col1:
        client_name = st.selectbox("Sélectionner le Client", df_clients['Nom'])
        client_id = df_clients[df_clients['Nom'] == client_name]['id'].values[0]
        marge = st.slider("Marge Bénéficiaire (%)", 0, 100, 30)

    st.markdown("---")
    st.subheader("🛠️ Configuration du Produit")
    
    col_c1, col_c2 = st.columns(2)
    # Liste des produits avec les impostes ajoutées
    categories = [
        "Fenêtre 1 vantail", "Fenêtre 2 vantaux", "Fenêtre Coulissante", "Fenêtre Oscillo-battante",
        "Fenêtre avec Imposte", 
        "Porte simple", "Porte double", "Porte vitrée", "Porte avec Imposte", 
        "Baie vitrée 2 rails", "Baie vitrée 3 rails", "Baie vitrée 4 rails", 
        "Portail Battant", "Portail Coulissant", "Rideau Métallique Manuel", 
        "Rideau Métallique Motorisé", "Véranda", "Façade vitrée", "Imposte Seule"
    ]
    type_produit = col_c1.selectbox("Type de Produit", categories)
    couleur = col_c2.selectbox("Couleur", ["Blanc", "Noir", "Gris Anthracite", "Bronze", "Imitation Bois", "Chêne Doré", "Acajou"])
    
    # Gestion dynamique des labels selon le type de produit
    is_imposte_seule = (type_produit == "Imposte Seule")
    
    col_d1, col_d2, col_d3 = st.columns(3)
    largeur = col_d1.number_input("Largeur (mm)", 300, 6000, 1200, step=50)
    
    if is_imposte_seule:
        hauteur = col_d2.number_input("Hauteur Imposte (mm)", 300, 3000, 500, step=50)
        hauteur_imposte = col_d3.number_input("Ignorer (laisser 0)", 0, 0, 0, step=1, help="Ce champ n'est pas utilisé pour l'imposte seule.")
        h_imposte_val = 0
    else:
        hauteur = col_d2.number_input("Hauteur Vantail (mm)", 300, 6000, 1000, step=50)
        hauteur_imposte = col_d3.number_input("Hauteur Imposte (mm) - 0 si aucune", 0, 3000, 0, step=50)
        h_imposte_val = hauteur_imposte
    
    col_e1, col_e2 = st.columns(2)
    matiere = col_e1.selectbox("Matière Profilé", ["Profilé Aluminium", "Profilé PVC"])
    vitrage = col_e2.selectbox("Type de Vitrage", ["Double vitrage", "Triple vitrage", "Vitrage teinté", "Vitrage sécurisé"])
    
    col_f1, col_f2 = st.columns(2)
    accessoires = col_f1.multiselect("Accessoires", ["Poignée", "Serrure", "Cylindre", "Paumelles", "Roulettes", "Crémone", "Charnières", "Joints", "Moustiquaires"])
    options = col_f2.multiselect("Options", ["Oscillo-battant", "Coulissant", "Volet manuel", "Volet motorisé", "Motorisation portail", "Motorisation rideau", "Moustiquaire intégrée"])
    
    quantite = st.number_input("Quantité", 1, 100, 1)
    
    if st.button("➕ Calculer et Ajouter au Devis", type="primary"):
        calc = CalculateurDevis(marge_beneficiaire=marge)
        result = calc.calculer_element(
            largeur, hauteur, h_imposte_val, matiere, vitrage, couleur, accessoires, options, quantite, is_imposte_seule
        )
        
        if 'panier_devis' not in st.session_state:
            st.session_state.panier_devis = []
        st.session_state.panier_devis.append({
            'designation': type_produit,
            'details': result['details'],
            'quantite': quantite,
            'prix_unitaire': round(result['prix
