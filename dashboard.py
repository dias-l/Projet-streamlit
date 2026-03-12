import streamlit as st
import json
import os
from datetime import datetime

st.set_page_config(page_title="Dashboard Math Game", page_icon="📊", layout="centered")

CATALOGUE_ACHIEVEMENTS = {
    "first_merge": {"nom": "Premier Pas", "desc": "Effectuer une première fusion d'opérateur."},
    "big_99": {"nom": "Le Compte est Bon", "desc": "Atteindre exactement 99 et déclencher le multiplicateur x9."},
    "over_99": {"nom": "Surcharge", "desc": "Dépasser 99 et déclencher le multiplicateur x2."},
    "millionnaire": {"nom": "Millionnaire", "desc": "Atteindre un total cumulé de 1 000 000 de points sur l'ensemble de tes parties !"}
}

st.title("📊 Tableau de Bord - Math Circle")

if st.button("🔄 Actualiser les statistiques"):
    st.rerun()

st.divider()

def load_stats():
    file_path = "stats.json"
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                timestamp = os.path.getmtime(file_path)
                heure_maj = datetime.fromtimestamp(timestamp).strftime('%H:%M:%S')
                return data, heure_maj
            except json.JSONDecodeError:
                return None, None
    return None, None

stats, heure_maj = load_stats()

if stats is None:
    st.warning("⏳ Aucune donnée trouvée. Joue un coup pour générer les statistiques !")
else:
    st.caption(f"⏱️ Rapport généré à : {heure_maj}")
    
    tab_stats, tab_succes = st.tabs(["📈 Statistiques", "🏆 Succès"])

    with tab_stats:
        st.subheader("Carrière du Joueur")
        
        col1, col2 = st.columns(2)
        col1.metric(label="Meilleur Score Historique 🏆", value=stats.get("best_score", 0))
        col2.metric(label="Score Total Cumulé 🌟", value=stats.get("total_score", 0))
        
        st.divider()
        st.subheader("Rapport de la dernière partie terminée")
        col3, col4, col5 = st.columns(3)
        col3.metric(label="Score Final", value=stats.get("last_score", 0))
        col4.metric(label="Mouvements", value=stats.get("last_moves", 0))
        col5.metric(label="Plus Grand Nombre", value=stats.get("last_max", 0))

    with tab_succes:
        st.subheader("Tes accomplissements")
        
        succes_debloques = stats.get("unlocked_achievements", [])
        
        for id_succes, infos in CATALOGUE_ACHIEVEMENTS.items():
            if id_succes in succes_debloques:
                st.success(f"🏆 **{infos['nom']}** \n\n {infos['desc']}")
            else:
                st.info(f"🔒 **???** (Bloqué) \n\n *Continue de jouer pour le découvrir !*")