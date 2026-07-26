Voici le code complet mis à jour. J'ai ajouté l'option **"Coulissant"** dans les tarifs, et j'ai intégré le **logo** dans l'en-tête du PDF. 

**ATTENTION :** Pour que le logo s'affiche sur le PDF, tu dois absolument avoir un fichier image nommé exactement `logo.png` dans le même dossier que ce fichier `app.py`. (Tu peux prendre n'importe quelle image de fenêtre/aluminium trouvée sur internet et la renommer `logo.png`).

Copie et remplace tout ton fichier `app.py` par ceci :

```python
import streamlit as st
import pandas as pd
from datetime import datetime
from fpdf import FPDF
import io

# --- CONFIGURATION & TARIFS ---
TARIFS_BASE = {
    "Fenêtre": {"Aluminium": 15000, "PVC": 12000},
    "Porte": {"Aluminium": 20000, "PVC": 16000},
    "Porte-fenêtre": {"Aluminium": 22000, "PVC": 18000},
    "Baie vitrée": {"Aluminium": 25000, "PVC": 21000},
    "Porte placard": {"Aluminium": 18000, "PVC": 14000}
}

TARIFS_VITRAGE = {
    "Simple vitrage": 0,
    "Double vitrage": 3500,
    "Vitrage teinté": 4000,
    "Double vitrage teinté": 5000
}

# AJOUT DE L'OPTION COULISSANT ICI
TARIFS_OPTIONS = {
    "Ouverture simple": 0,
    "Oscillo-battant": 2000,
    "Coulissant": 3000,  
    "Volet manuel": 8000,
    "Volet motorisé": 15000,
    "Moustiquaire": 4000
}

TARIFS_ACCESSOIRES = {
    "Poignée": 1500,
    "Serrure": 2500,
    "Paumelles": 1000,
    "Cylindre": 2000,
    "Roulettes": 800
}

# --- INITIALISATION DE L'ÉTAT STREAMLIT ---
if 'lignes' not in st.session_state:
    st.session_state.lignes = []
if 'num_devis' not in st.session_state:
    st.session_state.num_devis = 1000

# --- PAGE CONFIG ---
st.set_page_config(page_title="DJEFF ALUMINIUM - Devis", layout="wide", page_icon="🏗️")

# --- FONCTIONS DE CALCUL ---
def calculer_ligne(ligne):
    largeur_m = ligne['largeur'] / 1000
    hauteur_m = ligne['hauteur'] / 1000
    surface = largeur_m * hauteur_m
    ml = 2 * (largeur_m + hauteur_m)
    
    prix_base = TARIFS_BASE.get(ligne['produit'], {}).get(ligne['materiau'], 0)
    prix_vitrage = surface * TARIFS_VITRAGE.get(ligne['vitrage'], 0)
    prix_options = sum([TARIFS_OPTIONS[opt] for opt in ligne['options'] if opt in TARIFS_OPTIONS])
    prix_accessoires_fixes = sum([TARIFS_ACCESSOIRES[acc] for acc in ligne['accessoires'] if acc in TARIFS_ACCESSOIRES])
    prix_accessoires_perso = sum([a['prix'] * a['qty'] for a in ligne['accessoires_perso']])
    
    total_ligne = (prix_base + prix_vitrage + prix_options + prix_accessoires_fixes + prix_accessoires_perso) * ligne['quantite']
    
    return {
        "surface": surface,
        "ml": ml,
        "total": total_ligne
    }

# --- CLASSE PDF PERSONNALISÉE ---
class DevisPDF(FPDF):
    def header(self):
        # --- INTÉGRATION DU LOGO ---
        try:
            # On essaie de mettre l'image (x=10 marge gauche, w=25 largeur)
            self.image('logo.png', x=10, y=5, w=25)
            self.set_x(40) # On décale le texte à droite pour ne pas chevaucher le logo
        except:
            # Si le fichier logo.png n'est pas dans le dossier, on met juste le texte
            self.set_x(10)

        self.set_font('Helvetica', 'B', 20)
        self.set_text_color(0, 102, 204) # Bleu Aluminium
        self.cell(0, 15, 'DJEFF ALUMINIUM', border=0, align='L', new_x="LMARGIN", new_y="NEXT")
        
        self.set_draw_color(0, 102, 204)
        self.set_line_width(1)
        self.line(10, 25, 200, 25)
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(128)
        self.cell(0, 10, f'DJEFF ALUMINIUM - Devis N°{self.num_devis} | Page {self.page_no()}', align='C')

def generer_pdf(data, lignes_calculees, financiers):
    pdf = DevisPDF()
    pdf.num_devis = data['num_devis']
    pdf.add_page()
    pdf.set_text_color(0, 0, 0)
    
    # Infos Devis
    pdf.set_font('Helvetica', 'B', 12)
    pdf.cell(0, 10, f"Devis N°: {data['num_devis']}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 10, f"Date: {data['date']}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 10, f"Client: {data['client']}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(10)
    
    # Tableau
    pdf.set_font('Helvetica', 'B', 9)
    pdf.set_fill_color(230, 230, 230)
    colonnes = ['Désignation', 'Dimensions', 'M²', 'ML', 'Qté', 'Total (DA)']
    largeurs = [50, 30, 20, 20, 15, 30]
    
    for i in range(len(colonnes)):
        pdf.cell(largeurs[i], 8, colonnes[i], border=1, align='C', fill=True)
    pdf.ln()
    
    pdf.set_font('Helvetica', '', 9)
    for lig in lignes_calculees:
        designation = f"{lig['produit']}\n{lig['materiau']} - {lig['couleur']}"
        dimensions = f"{lig['largeur']}x{lig['hauteur']}"
        
        pdf.cell(largeurs[0], 10, designation, border=1)
        pdf.cell(largeurs[1], 10, dimensions, border=1, align='C')
        pdf.cell(largeurs[2], 10, f"{lig['surface']:.2f}", border=1, align='C')
        pdf.cell(largeurs[3], 10, f"{lig['ml']:.2f}", border=1, align='C')
        pdf.cell(largeurs[4], 10, str(lig['quantite']), border=1, align='C')
        pdf.cell(largeurs[5], 10, f"{lig['total']:,.0f}", border=1, align='R')
        pdf.ln()
        
    # Financier
    pdf.ln(10)
    pdf.set_font('Helvetica', 'B', 11)
    pdf.cell(130, 8, "Total Général HT:", border=0, align='R')
    pdf.cell(40, 8, f"{financiers['total_ht']:,.0f} DA", border=0, align='R')
    pdf.ln()
    
    pdf.set_font('Helvetica', '', 11)
    pdf.cell(130, 8, f"Remise ({financiers['remise']}%):", border=0, align='R')
    pdf.cell(40, 8, f"- {financiers['montant_remise']:,.0f} DA", border=0, align='R')
    pdf.ln()
    
    pdf.cell(130, 8, "Acompte:", border=0, align='R')
    pdf.cell(40, 8, f"- {financiers['acompte']:,.0f} DA", border=0, align='R')
    pdf.ln()
    
    pdf.set_font('Helvetica', 'B', 12)
    pdf.set_text_color(0, 102, 204)
    pdf.cell(130, 10, "RESTE À PAYER:", border=0, align='R')
    pdf.cell(40, 10, f"{financiers['reste_a_payer']:,.0f} DA", border=0, align='R')
    
    return pdf.output()

# --- INTERFACE STREAMLIT ---
st.title("🏗️ Création de Devis - DJEFF ALUMINIUM")

# Colonne de gauche : Saisie
with st.container():
    col1, col2 = st.columns([2, 1])
    
    with col1:
        client = st.text_input("Nom du client", placeholder="Ex: M. Benali")
    with col2:
        date_devis = st.date_input("Date", datetime.now()).strftime("%d/%m/%Y")
        num_devis = st.text_input("N° Devis", value=f"DEV-{st.session_state.num_devis}", disabled=True)

st.markdown("---")

# Formulaire d'ajout de produit
with st.expander("➕ AJOUTER UN PRODUIT", expanded=True):
    with st.form("form_produit"):
        c1, c2, c3 = st.columns(3)
        with c1:
            produit = st.selectbox("Produit", TARIFS_BASE.keys())
            materiau = st.selectbox("Matériau", ["Aluminium", "PVC"])
            couleur = st.selectbox("Couleur", ["Blanc", "Gris Anthracite", "Noir", "Bois"])
        with c2:
            vitrage = st.selectbox("Vitrage", TARIFS_VITRAGE.keys())
            largeur = st.number_input("Largeur (mm)", min_value=0, step=100)
            hauteur = st.number_input("Hauteur (mm)", min_value=0, step=100)
        with c3:
            quantite = st.number_input("Quantité", min_value=1, step=1)
            options = st.multiselect("Options", TARIFS_OPTIONS.keys())
            accessoires = st.multiselect("Accessoires", TARIFS_ACCESSOIRES.keys())
        
        # Accessoires personnalisés
        st.markdown("**Accessoires personnalisés**")
        col_p1, col_p2, col_p3 = st.columns(3)
        with col_p1: nom_perso = st.text_input("Nom accessoire")
        with col_p2: prix_perso = st.number_input("Prix unitaire (DA)", min_value=0)
        with col_p3: qty_perso = st.number_input("Quantité", min_value=1)
        
        submitted = st.form_submit_button("Ajouter au devis", use_container_width=True, type="primary")
        
        if submitted:
            if largeur > 0 and hauteur > 0:
                accessoires_perso_list = []
                if nom_perso and prix_perso > 0:
                    accessoires_perso_list.append({"nom": nom_perso, "prix": prix_perso, "qty": qty_perso})
                
                nouvelle_ligne = {
                    "id": len(st.session_state.lignes),
                    "produit": produit,
                    "materiau": materiau,
                    "couleur": couleur,
                    "vitrage": vitrage,
                    "largeur": largeur,
                    "hauteur": hauteur,
                    "quantite": quantite,
                    "options": options,
                    "accessoires": accessoires,
                    "accessoires_perso": accessoires_perso_list
                }
                st.session_state.lignes.append(nouvelle_ligne)
                st.success(f"{produit} ajouté avec succès !")
                st.rerun()
            else:
                st.error("Veuillez entrer des dimensions valides.")

# Affichage du tableau des lignes
if st.session_state.lignes:
    st.markdown("### 📋 Récapitulatif du Devis")
    
    lignes_calculees = []
    for lig in st.session_state.lignes:
        calc = calculer_ligne(lig)
        lig_merge = {**lig, **calc}
        lignes_calculees.append(lig_merge)
        
    df = pd.DataFrame(lignes_calculees)
    df_affichage = df[['produit', 'materiau', 'couleur', 'largeur', 'hauteur', 'surface', 'ml', 'quantite', 'total']].copy()
    df_affichage.columns = ['Produit', 'Matière', 'Couleur', 'Larg (mm)', 'Haut (mm)', 'Surface (m²)', 'ML (m)', 'Qté', 'Total (DA)']
    df_affichage['Total (DA)'] = df_affichage['Total (DA)'].apply(lambda x: f"{x:,.0f}")
    
    st.dataframe(df_affichage, use_container_width=True, hide_index=True)
    
    # Bouton pour supprimer une ligne
    col_del1, col_del2 = st.columns([1, 5])
    with col_del1:
        id_suppr = st.number_input("ID ligne à supprimer", min_value=0, max_value=len(st.session_state.lignes)-1, step=1)
    with col_del2:
        st.write("") # Espacement
        if st.button("❌ Supprimer cette ligne"):
            st.session_state.lignes = [l for l in st.session_state.lignes if l['id'] != id_suppr]
            st.rerun()

    st.markdown("---")
    
    # Partie Financière
    st.markdown("### 💰 Financier")
    total_ht = sum([l['total'] for l in lignes_calculees])
    
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        remise_pct = st.number_input("Remise (%)", min_value=0.0, max_value=100.0, value=0.0, step=1.0)
    with col_f2:
        acompte = st.number_input("Acompte (DA)", min_value=0, value=0, step=1000)
    with col_f3:
        st.write("") # Espacement
        montant_remise = total_ht * (remise_pct / 100)
        reste_a_payer = total_ht - montant_remise - acompte
        
        st.metric(label="RESTE À PAYER", value=f"{reste_a_payer:,.0f} DA")
        
    st.markdown("---")
    
    # Exports
    st.markdown("### 📤 Exportations")
    col_exp1, col_exp2, col_exp3 = st.columns(3)
    
    with col_exp1:
        # Export CSV
        csv = df_affichage.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Télécharger CSV",
            data=csv,
            file_name=f'Devis_{st.session_state.num_devis}.csv',
            mime='text/csv'
        )
        
    with col_exp2:
        # Export PDF
        if st.button("📄 Générer le PDF Professionnel"):
            data_pdf = {
                "num_devis": f"DEV-{st.session_state.num_devis}",
                "date": date_devis,
                "client": client if client else "Client Non Renseigné"
            }
            financiers_pdf = {
                "total_ht": total_ht,
                "remise": remise_pct,
                "montant_remise": montant_remise,
                "acompte": acompte,
                "reste_a_payer": reste_a_payer
            }
            
            pdf_bytes = generer_pdf(data_pdf, lignes_calculees, financiers_pdf)
            
            st.download_button(
                label="⬇️ Télécharger le Devis PDF",
                data=pdf_bytes,
                file_name=f'Devis_Djeff_{st.session_state.num_devis}.pdf',
                mime='application/octet-stream'
            )
            
    with col_exp3:
        if st.button("🆕 Nouveau Devis"):
            st.session_state.lignes = []
            st.session_state.num_devis += 1
            st.rerun()

else:
    st.info("Aucun produit ajouté pour le moment. Utilisez le formulaire ci-dessus.")
```
