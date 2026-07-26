import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
from streamlit_option_menu import option_menu
from fpdf import FPDF
from datetime import datetime
import os

# ==========================================
# 1. CONFIGURATION DE LA PAGE
# ==========================================
st.set_page_config(page_title="DJEFF ALUMINIUM PRO", layout="wide", page_icon="🏗️")

# Style CSS pour un look professionnel
st.markdown("""
<style>
    .main {background-color: #f8f9fa;}
    .stButton>button {background-color: #0d6efd; color: white; border-radius: 5px; font-weight: bold;}
    .stDataFrame {background-color: white; border-radius: 5px; padding: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);}
    h1, h2, h3 {color: #1a1a1a;}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. GESTION DE LA BASE DE DONNÉES (SQLite)
# ==========================================
DB_NAME = "djeff_aluminium.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # Création des tables si elles n'existent pas
    c.execute('''CREATE TABLE IF NOT EXISTS tarifs (categorie TEXT, nom TEXT, prix REAL, unite TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS clients (id INTEGER PRIMARY KEY AUTOINCREMENT, nom TEXT, prenom TEXT, telephone TEXT, adresse TEXT, wilaya TEXT, commune TEXT, email TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS fournisseurs (id INTEGER PRIMARY KEY AUTOINCREMENT, nom TEXT, telephone TEXT, email TEXT, produits TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS stock (nom TEXT, quantite REAL, seuil_alerte REAL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS devis (id INTEGER PRIMARY KEY AUTOINCREMENT, numero TEXT, client_id INTEGER, date TEXT, total_ht REAL, tva REAL, total_ttc REAL, acompte REAL, reste REAL, statut TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS lignes_devis (id INTEGER PRIMARY KEY AUTOINCREMENT, devis_id INTEGER, designation TEXT, largeur REAL, hauteur REAL, quantite INTEGER, prix_unitaire REAL, total_ligne REAL)''')

    # Insertion de tarifs par défaut si la table est vide
    c.execute("SELECT COUNT(*) FROM tarifs")
    if c.fetchone()[0] == 0:
        tarifs_defaut = [
            ('Matière', 'Profilé Aluminium', 850, 'DA/ml'),
            ('Matière', 'Profilé PVC', 600, 'DA/ml'),
            ('Matière', 'Double vitrage', 3500, 'DA/m2'),
            ('Matière', 'Triple vitrage', 5500, 'DA/m2'),
            ('Accessoire', 'Poignée', 1200, 'DA/u'),
            ('Accessoire', 'Serrure', 4500, 'DA/u'),
            ('Accessoire', 'Cylindre', 2500, 'DA/u'),
            ('Accessoire', 'Paumelles', 800, 'DA/u'),
            ('Accessoire', 'Moustiquaire', 3500, 'DA/u'),
            ('Option', 'Oscillo-battant', 3500, 'DA/u'),
            ('Option', 'Volet motorisé', 18000, 'DA/u'),
            ('Option', 'Volet manuel', 12000, 'DA/u'),
            ('Couleur', 'Blanc', 0, 'DA'),
            ('Couleur', 'Gris Anthracite', 1500, 'DA/ml'),
            ('Couleur', 'Imitation Bois', 2500, 'DA/ml')
        ]
        c.executemany("INSERT INTO tarifs VALUES (?,?,?,?)", tarifs_defaut)

    conn.commit()
    conn.close()

def run_query(query, params=(), fetch=False):
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

def get_dataframe(query, params=()):
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

# Initialiser la base de données au démarrage
init_db()

# ==========================================
# 3. MOTEUR DE CALCUL MENUISERIE
# ==========================================
def get_prix(categorie, nom):
    res = run_query("SELECT prix FROM tarifs WHERE categorie=? AND nom=?", (categorie, nom), fetch=True)
    return res[0]['prix'] if res else 0

def calculer_menuiserie(produit, largeur, hauteur, matiere, vitrage, couleur, accessoires, options, quantite, marge):
    # Calcul des dimensions en mètres
    largeur_m = largeur / 1000
    hauteur_m = hauteur / 1000
    perimetre_ml = 2 * (largeur_m + hauteur_m)
    surface_m2 = largeur_m * hauteur_m

    # Coûts matière première
    prix_profil = get_prix('Matière', f'Profilé {matiere}')
    prix_vitrage = get_prix('Matière', vitrage)
    
    cout_profil = perimetre_ml * prix_profil
    cout_vitrage = surface_m2 * prix_vitrage

    # Coûts accessoires et options
    cout_accessoires = sum([get_prix('Accessoire', a) for a in accessoires])
    cout_options = sum([get_prix('Option', o) for o in options])

    # Supplément couleur (calculé au mètre linéaire)
    suppl_couleur = get_prix('Couleur', couleur) * perimetre_ml

    # Total coutant unitaire
    coutant_unitaire = cout_profil + cout_vitrage + cout_accessoires + cout_options + suppl_couleur

    # Prix de vente avec marge
    prix_vente_unitaire = coutant_unitaire * (1 + (marge / 100))
    total_ligne = prix_vente_unitaire * quantite

    designation = f"{produit} {matiere} ({largeur}x{hauteur}mm) - {vitrage} - {couleur}"
    
    return {
        "designation": designation,
        "largeur": largeur,
        "hauteur": hauteur,
        "quantite": quantite,
        "prix_unitaire": round(prix_vente_unitaire, 2),
        "total_ligne": round(total_ligne, 2)
    }

# ==========================================
# 4. GÉNÉRATEUR PDF PROFESSIONNEL
# ==========================================
def generate_devis_pdf(devis_data, lignes, client_data, filename="Devis_DJEFF.pdf"):
    pdf = FPDF(orientation='P', unit='mm', format='A4')
    pdf.add_page()
    
    # En-tête entreprise
    pdf.set_font("Helvetica", 'B', 18)
    pdf.set_text_color(13, 110, 253) # Bleu
    pdf.cell(0, 10, "DJEFF ALUMINIUM PRO", ln=True, align='L')
    pdf.set_font("Helvetica", '', 10)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 5, "Atelier de Menuiserie Aluminium & PVC", ln=True)
    pdf.cell(0, 5, "Adresse: Votre adresse, Alger, Algérie", ln=True)
    pdf.cell(0, 5, "Tel: 0555 00 00 00 | Email: contact@djeff.dz", ln=True)
    pdf.ln(10)
    pdf.line(10, 45, 200, 45) # Ligne de séparation
    
    # Titre et informations devis
    pdf.set_font("Helvetica", 'B', 14)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 10, f"DEVIS N° {devis_data['numero']}", ln=True, align='R')
    
    pdf.set_font("Helvetica", '', 11)
    pdf.cell(0, 6, f"Date: {devis_data['date']}", ln=True, align='R')
    pdf.ln(5)
    
    # Bloc Client
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(90, 6, "Facturé à :", ln=True, fill=True)
    pdf.set_font("Helvetica", 'B', 11)
    pdf.cell(90, 6, f"{client_data['nom']} {client_data['prenom']}", ln=True)
    pdf.set_font("Helvetica", '', 10)
    pdf.cell(90, 5, f"Adresse: {client_data['adresse']}, {client_data['wilaya']}", ln=True)
    pdf.cell(90, 5, f"Téléphone: {client_data['telephone']}", ln=True)
    pdf.ln(10)
    
    # Tableau des articles
    pdf.set_fill_color(13, 110, 253)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", 'B', 10)
    pdf.cell(80, 10, "Désignation", border=1, fill=True)
    pdf.cell(20, 10, "Qté", border=1, align='C', fill=True)
    pdf.cell(40, 10, "Prix Unit. (DA)", border=1, align='R', fill=True)
    pdf.cell(50, 10, "Total (DA)", border=1, align='R', fill=True, ln=True)
    
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", '', 10)
    for ligne in lignes:
        pdf.cell(80, 10, ligne['designation'][:45], border=1)
        pdf.cell(20, 10, str(ligne['quantite']), border=1, align='C')
        pdf.cell(40, 10, f"{ligne['prix_unitaire']:,.2f}", border=1, align='R')
        pdf.cell(50, 10, f"{ligne['total_ligne']:,.2f}", border=1, align='R', ln=True)
        
    # Totaux
    pdf.ln(5)
    pdf.set_x(110)
    pdf.set_font("Helvetica", '', 10)
    pdf.cell(60, 8, "Total HT:", border=1, align='R')
    pdf.cell(40, 8, f"{devis_data['total_ht']:,.2f} DA", border=1, align='R', ln=True)
    
    if devis_data['tva'] > 0:
        pdf.set_x(110)
        pdf.cell(60, 8, f"TVA ({devis_data['tva']}%):", border=1, align='R')
        tva_montant = devis_data['total_ht'] * (devis_data['tva']/100)
        pdf.cell(40, 8, f"{tva_montant:,.2f} DA", border=1, align='R', ln=True)
        
    pdf.set_x(110)
    pdf.set_font("Helvetica", 'B', 11)
    pdf.cell(60, 10, "Total TTC:", border=1, align='R', fill=True)
    pdf.cell(40, 10, f"{devis_data['total_ttc']:,.2f} DA", border=1, align='R', fill=True, ln=True)
    
    pdf.set_x(110)
    pdf.set_font("Helvetica", '', 10)
    pdf.cell(60, 8, "Acompte versé:", border=1, align='R')
    pdf.cell(40, 8, f"{devis_data['acompte']:,.2f} DA", border=1, align='R', ln=True)
    
    pdf.set_x(110)
    pdf.set_font("Helvetica", 'B', 11)
    pdf.set_text_color(204, 0, 0) # Rouge
    pdf.cell(60, 10, "Reste à payer:", border=1, align='R', fill=True)
    pdf.cell(40, 10, f"{devis_data['reste']:,.2f} DA", border=1, align='R', fill=True, ln=True)
    
    # Pied de page / Signature
    pdf.ln(20)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", '', 10)
    pdf.cell(90, 10, "Signature et Cachet de l'entreprise", align='C', border=1)
    pdf.cell(90, 10, "Bon pour accord du client", align='C', border=1, ln=True)
    
    pdf.output(filename)
    return filename

# ==========================================
# 5. INTERFACE UTILISATEUR (STREAMLIT)
# ==========================================
with st.sidebar:
    selected = option_menu("DJEFF ALUMINIUM", [
        'Tableau de bord', 'Clients', 'Créer Devis', 'Liste Devis', 
        'Tarifs', 'Stock', 'Fournisseurs'
    ], icons=['house', 'people', 'file-earmark-plus', 'list-check', 'tag', 'box-seam', 'truck'], 
    menu_icon="building", default_index=0)

# --- PAGE 1: TABLEAU DE BORD ---
if selected == 'Tableau de bord':
    st.title("📊 Tableau de Bord")
    col1, col2, col3 = st.columns(3)
    
    devis_df = get_dataframe("SELECT * FROM devis")
    total_devis = len(devis_df)
    ca_total = devis_df['total_ttc'].sum() if not devis_df.empty else 0
    
    with col1:
        st.metric("Nombre de Devis", total_devis)
    with col2:
        st.metric("Chiffre d'Affaires Total", f"{ca_total:,.0f} DA")
    with col3:
        st.metric("Devis en cours", len(devis_df[devis_df['statut']=='En cours']) if not devis_df.empty and 'statut' in devis_df.columns else 0)
        
    if not devis_df.empty:
        st.subheader("Évolution du Chiffre d'Affaires")
        fig = px.bar(devis_df, x='date', y='total_ttc', title="CA par jour", labels={'total_ttc':'Total TTC (DA)', 'date':'Date'})
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Aucun devis créé pour le moment.")

# --- PAGE 2: CLIENTS ---
elif selected == 'Clients':
    st.title("👤 Gestion des Clients")
    with st.expander("➕ Ajouter un nouveau client", expanded=False):
        with st.form("form_client"):
            c1, c2 = st.columns(2)
            nom = c1.text_input("Nom *")
            prenom = c2.text_input("Prénom")
            telephone = st.text_input("Téléphone *")
            email = st.text_input("Email")
            adresse = st.text_area("Adresse")
            c3, c4 = st.columns(2)
            wilaya = c3.text_input("Wilaya")
            commune = c4.text_input("Commune")
            
            if st.form_submit_button("💾 Enregistrer le client"):
                if nom and telephone:
                    run_query("INSERT INTO clients (nom, prenom, telephone, email, adresse, wilaya, commune) VALUES (?,?,?,?,?,?,?)",
                              (nom, prenom, telephone, email, adresse, wilaya, commune))
                    st.success("Client ajouté avec succès !")
                    st.rerun()
                else:
                    st.error("Le nom et le téléphone sont obligatoires.")
    
    st.subheader("Liste des clients")
    df = get_dataframe("SELECT id, nom, prenom, telephone, email, wilaya, commune FROM clients")
    if not df.empty:
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.warning("Aucun client enregistré.")

# --- PAGE 3: CREER DEVIS ---
elif selected == 'Créer Devis':
    st.title("📄 Création de Devis")
    
    # Initialiser le panier dans la session
    if 'panier_devis' not in st.session_state:
        st.session_state.panier_devis = []
    
    clients = run_query("SELECT id, nom || ' ' || prenom as name FROM clients", fetch=True)
    
    if not clients:
        st.warning("Veuillez d'abord ajouter des clients dans l'onglet 'Clients'.")
    else:
        col1, col2 = st.columns(2)
        client_id = col1.selectbox("Sélectionner le client", [c['id'] for c in clients], format_func=lambda x: [c['name'] for c in clients if c['id']==x][0])
        date_devis = col2.date_input("Date du devis", datetime.today())
        
        st.markdown("### ➕ Ajouter un article")
        c1, c2, c3 = st.columns(3)
        produit = c1.selectbox("Type de produit", ["Fenêtre 1 vantail", "Fenêtre 2 vantaux", "Porte simple", "Baie vitrée 2 rails", "Baie vitrée 3 rails", "Portail battant"])
        matiere = c2.selectbox("Matière", ["Aluminium", "PVC"])
        vitrage = c3.selectbox("Type de vitrage", ["Double vitrage", "Triple vitrage", "Vitrage teinté", "Vitrage sécurisé"])
        
        c4, c5, c6 = st.columns(3)
        largeur = c4.number_input("Largeur (mm)", min_value=300, max_value=6000, value=1200, step=50)
        hauteur = c5.number_input("Hauteur (mm)", min_value=300, max_value=6000, value=1000, step=50)
        couleur = c6.selectbox("Couleur", ["Blanc", "Noir", "Gris Anthracite", "Bronze", "Imitation Bois", "Chêne Doré"])
        
        c7, c8, c9 = st.columns(3)
        accessoires = c7.multiselect("Accessoires", ["Poignée", "Serrure", "Cylindre", "Paumelles", "Moustiquaire"])
        options = c8.multiselect("Options", ["Oscillo-battant", "Volet motorisé", "Volet manuel"])
        marge = c9.slider("Marge bénéficiaire (%)", min_value=10, max_value=100, value=30, step=5)
        
        qte = st.number_input("Quantité", min_value=1, max_value=100, value=1, step=1)
        
        if st.button("Ajouter au devis"):
            ligne = calculer_menuiserie(produit, largeur, hauteur, matiere, vitrage, couleur, accessoires, options, qte, marge)
            st.session_state.panier_devis.append(ligne)
            st.success(f"{produit} ajouté au panier (Prix unitaire: {ligne['prix_unitaire']:,.0f} DA) !")
            st.rerun()
            
        # Affichage du panier
        if st.session_state.panier_devis:
            st.markdown("### 🛒 Composition du devis")
            df_panier = pd.DataFrame(st.session_state.panier_devis)
            # Bouton pour vider le panier
            col_vide, col_total = st.columns([1, 3])
            if col_vide.button("🗑️ Vider le panier"):
                st.session_state.panier_devis = []
                st.rerun()
                
            st.dataframe(df_panier[['designation', 'largeur', 'hauteur', 'quantite', 'prix_unitaire', 'total_ligne']], 
                         use_container_width=True, hide_index=True)
            
            total_ht = df_panier['total_ligne'].sum()
            col_total.markdown(f"### Total HT estimé : {total_ht:,.2f} DA")
            
            st.markdown("---")
            st.markdown("### 📌 Finalisation du devis")
            col_tva, col_acompte = st.columns(2)
            tva = col_tva.number_input("Taux TVA (%)", min_value=0, max_value=19, value=0)
            acompte = col_acompte.number_input("Acompte versé par le client (DA)", min_value=0.0, value=0.0, step=1000.0)
            
            if st.button("✅ Valider le devis et générer le PDF", type="primary"):
                total_ttc = total_ht * (1 + tva/100)
                reste = total_ttc - acompte
                
                # Génération numéro DEV-YYYY-000X
                annee = datetime.now().year
                count = run_query("SELECT COUNT(*) as c FROM devis WHERE numero LIKE ?", (f"DEV-{annee}-%",), fetch=True)[0]['c']
                numero = f"DEV-{annee}-{count+1:04d}"
                
                # Sauvegarde en base
                devis_id = run_query(
                    "INSERT INTO devis (numero, client_id, date, total_ht, tva, total_ttc, acompte, reste, statut) VALUES (?,?,?,?,?,?,?,?,?)",
                    (numero, client_id, str(date_devis), total_ht, tva, total_ttc, acompte, reste, "Validé")
                )
                for ligne in st.session_state.panier_devis:
                    run_query(
                        "INSERT INTO lignes_devis (devis_id, designation, largeur, hauteur, quantite, prix_unitaire, total_ligne) VALUES (?,?,?,?,?,?,?)",
                        (devis_id, ligne['designation'], ligne['largeur'], ligne['hauteur'], ligne['quantite'], ligne['prix_unitaire'], ligne['total_ligne'])
                    )
                
                # Génération PDF
                client_data = run_query("SELECT * FROM clients WHERE id=?", (client_id,), fetch=True)[0]
                filename = f"Devis_{numero}.pdf"
                generate_devis_pdf(
                    {"numero": numero, "date": str(date_devis), "total_ht": total_ht, "tva": tva, "total_ttc": total_ttc, "acompte": acompte, "reste": reste},
                    st.session_state.panier_devis, dict(client_data), filename
                )
                
                # Bouton de téléchargement
                with open(filename, "rb") as f:
                    st.download_button("📥 Télécharger le PDF du devis", f, file_name=filename, mime="application/pdf")
                
                st.success("Devis enregistré dans la base de données avec succès !")
                st.balloons()

# --- PAGE 4: LISTE DEVIS ---
elif selected == 'Liste Devis':
    st.title("📋 Liste des Devis")
    devis = get_dataframe("""
        SELECT d.numero, c.nom || ' ' || c.prenom as Client, d.date, d.total_ttc, d.acompte, d.reste, d.statut 
        FROM devis d JOIN clients c ON d.client_id = c.id ORDER BY d.date DESC
    """)
    if not devis.empty:
        st.dataframe(devis, use_container_width=True, hide_index=True)
        
        st.markdown("### Exporter les données")
        csv = devis.to_csv(index=False).encode('utf-8')
        st.download_button("📤 Exporter en CSV", csv, "liste_devis.csv", "text/csv")
    else:
        st.info("Aucun devis créé pour le moment.")

# --- PAGE 5: TARIFS ---
elif selected == 'Tarifs':
    st.title("💰 Administration des Tarifs")
    st.info("Modifiez directement les cellules du tableau ci-dessous. Cliquez sur 'Sauvegarder' en bas pour appliquer les changements.")
    
    df = get_dataframe("SELECT rowid as id, categorie, nom, prix, unite FROM tarifs")
    
    edited_df = st.data_editor(
        df, 
        num_rows="dynamic", 
        use_container_width=True, 
        hide_index=True,
        column_config={
            "categorie": st.column_config.SelectboxColumn("Catégorie", options=["Matière", "Accessoire", "Option", "Couleur"]),
            "prix": st.column_config.NumberColumn("Prix", min_value=0, step=100),
            "id": None # Cacher l'ID
        }
    )
    
    if st.button("💾 Sauvegarder les tarifs", type="primary"):
        run_query("DELETE FROM tarifs")
        for _, row in edited_df.iterrows():
            if pd.notna(row['categorie']) and pd.notna(row['nom']):
                run_query("INSERT INTO tarifs (categorie, nom, prix, unite) VALUES (?,?,?,?)",
                          (row['categorie'], row['nom'], row['prix'], row['unite']))
        st.success("Tarifs mis à jour avec succès !")
        st.rerun()

# --- PAGE 6: STOCK ---
elif selected == 'Stock':
    st.title("📦 Gestion du Stock")
    st.info("Gérez vos entrées et sorties de stock. Le système vous alertera si le stock est faible.")
    
    df = get_dataframe("SELECT rowid as id, nom, quantite, seuil_alerte FROM stock")
    
    edited_df = st.data_editor(
        df, 
        num_rows="dynamic", 
        use_container_width=True, 
        hide_index=True,
        column_config={
            "id": None
        }
    )
    
    if st.button("💾 Mettre à jour le stock", type="primary"):
        run_query("DELETE FROM stock")
        for _, row in edited_df.iterrows():
            if pd.notna(row['nom']):
                run_query("INSERT INTO stock (nom, quantite, seuil_alerte) VALUES (?,?,?)",
                          (row['nom'], row['quantite'], row['seuil_alerte']))
        st.success("Stock mis à jour !")
        st.rerun()
        
    st.markdown("---")
    st.subheader("⚠️ Alertes Stock Faible")
    if not edited_df.empty:
        alertes = edited_df[(edited_df['quantite'] <= edited_df['seuil_alerte']) & pd.notna(edited_df['quantite'])]
        if not alertes.empty:
            st.dataframe(alertes[['nom', 'quantite', 'seuil_alerte']], use_container_width=True, hide_index=True)
        else:
            st.success("Tous les stocks sont au niveau normal.")

# --- PAGE 7: FOURNISSEURS ---
elif selected == 'Fournisseurs':
    st.title("🚚 Gestion des Fournisseurs")
    with st.expander("➕ Ajouter un fournisseur"):
        with st.form("form_fournisseur"):
            c1, c2 = st.columns(2)
            nom = c1.text_input("Nom du fournisseur *")
            tel = c2.text_input("Téléphone")
            email = st.text_input("Email")
            produits = st.text_area("Produits fournis")
            adresse = st.text_input("Adresse")
            
            if st.form_submit_button("💾 Enregistrer"):
                if nom:
                    run_query("INSERT INTO fournisseurs (nom, telephone, email, produits, adresse) VALUES (?,?,?,?,?)",
                              (nom, tel, email, produits, adresse))
                    st.success("Fournisseur ajouté !")
                    st.rerun()
                else:
                    st.error("Le nom est obligatoire.")
            
    st.subheader("Liste des fournisseurs")
    df = get_dataframe("SELECT nom, telephone, email, produits, adresse FROM fournisseurs")
    if not df.empty:
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("Aucun fournisseur enregistré.")
