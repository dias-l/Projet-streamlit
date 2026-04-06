import streamlit as st
import json
import os
from datetime import datetime, date, timedelta

st.set_page_config(page_title="Math Circle – Dashboard", page_icon="🔵", layout="centered")

# ── CATALOGUE SUCCÈS ──────────────────────────────────────────────────────────
SUCCES = {
    # Faciles
    "first_merge":  {"nom": "Premier Pas",        "desc": "Effectuer une première fusion.", "emoji": "👣", "secret": False},
    "first_50":     {"nom": "Mi-chemin",           "desc": "Atteindre 50 en une fusion.",   "emoji": "🔵", "secret": False},
    "big_99":       {"nom": "Le Compte est Bon",   "desc": "Atteindre exactement 99.",      "emoji": "💥", "secret": False},
    "over_99":      {"nom": "Surcharge",           "desc": "Dépasser 99.",                  "emoji": "🔥", "secret": False},
    "millionnaire": {"nom": "Millionnaire",        "desc": "1 000 000 pts cumulés.",        "emoji": "💰", "secret": False},
    # Maîtrise
    "speed_10":     {"nom": "Fulgurant",           "desc": "Gagner en moins de 10 coups.",  "emoji": "⚡", "secret": False},
    "combo_3":      {"nom": "Triple Fusion",       "desc": "Enchaîner 3 combos.",           "emoji": "⛓️", "secret": False},
    "fusion_1000":  {"nom": "Millier d'un Coup",   "desc": "Atteindre 1 000 en une fusion.","emoji": "🎯", "secret": False},
    "streak_7":     {"nom": "Une Semaine de Feu",  "desc": "Jouer 7 jours de suite.",       "emoji": "📅", "secret": False},
    # Ultra durs (secrets)
    "trois_99":     {"nom": "Triplé Critique",     "desc": "Faire 99 trois fois dans la même partie.", "emoji": "☢️",  "secret": True},
    "score_1m":     {"nom": "Millionnaire Ultime", "desc": "Score > 1 000 000 en une partie.",         "emoji": "👑",  "secret": True},
    "combo_99":     {"nom": "Combo Critique",      "desc": "Atteindre 99 via un combo.",               "emoji": "💎",  "secret": True},
    "streak_30":    {"nom": "Légende",             "desc": "Jouer 30 jours de suite.",                 "emoji": "🏅",  "secret": True},
    "orb_1m":       {"nom": "Mégaorb",             "desc": "Atteindre 1 000 000 sur un seul orb.",     "emoji": "🌟",  "secret": True},
    "win_1":        {"nom": "Perfectionniste",     "desc": "Gagner en un seul coup.",                  "emoji": "🎖️", "secret": True},
    "combo_5":      {"nom": "Réaction en Chaîne",  "desc": "Enchaîner 5 combos.",                      "emoji": "⚗️",  "secret": True},
}

# ── HELPERS ───────────────────────────────────────────────────────────────────
def formater(v):
    if not isinstance(v, (int, float)): return str(v)
    if v >= 1_000_000_000: return f"{v/1_000_000_000:.2g}G"
    if v >= 1_000_000:     return f"{v/1_000_000:.2g}M"
    if v >= 1_000:         return f"{v/1_000:.2g}K"
    return str(int(v))

def formater_duree(secondes):
    if secondes < 60: return f"{int(secondes)}s"
    if secondes < 3600: return f"{int(secondes//60)}m {int(secondes%60)}s"
    return f"{int(secondes//3600)}h {int((secondes%3600)//60)}m"

def load_stats():
    if os.path.exists("stats.json"):
        with open("stats.json", "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                ts   = os.path.getmtime("stats.json")
                maj  = datetime.fromtimestamp(ts).strftime('%d/%m/%Y %H:%M:%S')
                return data, maj
            except Exception:
                return None, None
    return None, None

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .metric-card {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border-radius: 16px;
        padding: 20px;
        text-align: center;
        border: 1px solid #0f3460;
        margin-bottom: 8px;
    }
    .metric-val { font-size: 2rem; font-weight: 800; color: #00e9d8; }
    .metric-lbl { font-size: 0.8rem; color: #aaa; margin-top: 4px; }
    .succes-ok   { background: #0d2d1a; border-left: 4px solid #00e676; border-radius: 8px; padding: 12px; margin: 6px 0; }
    .succes-lock { background: #1a1a1a; border-left: 4px solid #333; border-radius: 8px; padding: 12px; margin: 6px 0; opacity: 0.6; }
    .succes-secret { background: #1a0d2e; border-left: 4px solid #7c3aed; border-radius: 8px; padding: 12px; margin: 6px 0; opacity: 0.5; }
    .streak-badge { background: linear-gradient(135deg, #ec458d, #ff8c42); border-radius: 50px; padding: 8px 24px; display: inline-block; font-weight: 800; font-size: 1.1rem; color: white; }
    .heatmap-day { display: inline-block; width: 12px; height: 12px; border-radius: 2px; margin: 1px; }
</style>
""", unsafe_allow_html=True)

# ── HEADER ────────────────────────────────────────────────────────────────────
st.title("🔵 Math Circle — Dashboard")

col_ref, col_maj = st.columns([1, 3])
with col_ref:
    if st.button("🔄 Actualiser"):
        st.rerun()

stats, heure_maj = load_stats()

if stats is None:
    st.warning("⏳ Aucune donnée. Lance une partie pour commencer !")
    st.stop()

with col_maj:
    st.caption(f"Dernière mise à jour : {heure_maj}")

st.divider()

# ── STREAK ────────────────────────────────────────────────────────────────────
streak      = stats.get("streak", 0)
last_played = stats.get("last_played", "")
today_str   = str(date.today())
yesterday   = str(date.today() - timedelta(days=1))

streak_actif = last_played in (today_str, yesterday)
streak_emoji = "🔥" if streak_actif else "❄️"

st.markdown(f"""
<div style="text-align:center; margin: 16px 0;">
    <div class="streak-badge">{streak_emoji} Streak : {streak} jour{'s' if streak != 1 else ''}</div>
    <div style="color:#aaa; font-size:0.8rem; margin-top:8px;">
        {'Actif aujourd\'hui ✅' if last_played == today_str else ('Joué hier — relance !' if last_played == yesterday else 'Streak perdu ❌')}
    </div>
</div>
""", unsafe_allow_html=True)

# ── TABS ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs(["📊 Carrière", "📈 Historique", "🎯 Dernière Partie", "🏆 Succès"])

# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    st.subheader("Statistiques Globales")

    total_games  = stats.get("total_games", 0)
    total_time   = stats.get("total_time",  0)
    total_clicks = stats.get("total_clicks",0)
    best_score   = stats.get("best_score",  0)
    total_score  = stats.get("total_score", 0)
    all_time_max = stats.get("all_time_max",0)
    avg_score    = total_score // total_games if total_games else 0

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f'<div class="metric-card"><div class="metric-val">{formater(best_score)}</div><div class="metric-lbl">🏆 Meilleur Score</div></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="metric-card"><div class="metric-val">{formater(total_score)}</div><div class="metric-lbl">🌟 Score Cumulé</div></div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="metric-card"><div class="metric-val">{formater(avg_score)}</div><div class="metric-lbl">📊 Score Moyen</div></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    c4, c5, c6 = st.columns(3)
    with c4:
        st.markdown(f'<div class="metric-card"><div class="metric-val">{total_games}</div><div class="metric-lbl">🎮 Parties Jouées</div></div>', unsafe_allow_html=True)
    with c5:
        st.markdown(f'<div class="metric-card"><div class="metric-val">{formater_duree(total_time)}</div><div class="metric-lbl">⏱️ Temps de Jeu</div></div>', unsafe_allow_html=True)
    with c6:
        st.markdown(f'<div class="metric-card"><div class="metric-val">{formater(total_clicks)}</div><div class="metric-lbl">🖱️ Clics Total</div></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    c7, c8 = st.columns(2)
    with c7:
        st.markdown(f'<div class="metric-card"><div class="metric-val">{formater(all_time_max)}</div><div class="metric-lbl">🔝 Plus Grand Nombre Atteint</div></div>', unsafe_allow_html=True)
    with c8:
        avg_dur = total_time // total_games if total_games else 0
        st.markdown(f'<div class="metric-card"><div class="metric-val">{formater_duree(avg_dur)}</div><div class="metric-lbl">⏳ Durée Moyenne / Partie</div></div>', unsafe_allow_html=True)

    # Heatmap
    st.subheader("Activité (90 derniers jours)")
    history = stats.get("history", [])
    jours_joues = set(e["date"] for e in history)

    days = [(date.today() - timedelta(days=i)) for i in range(89, -1, -1)]
    weeks = [days[i:i+7] for i in range(0, len(days), 7)]

    mois_labels = ""
    prev_mois = ""
    for i, week in enumerate(weeks):
        mois = week[0].strftime("%b")
        if mois != prev_mois:
            mois_labels += f'<span style="display:inline-block;width:{13*len(week)}px;font-size:10px;color:#aaa">{mois}</span>'
            prev_mois = mois

    html_heatmap = f'<div style="margin:8px 0">{mois_labels}</div><div style="line-height:0">'
    for week in weeks:
        html_heatmap += '<div style="display:inline-block;vertical-align:top">'
        for d in week:
            joue = str(d) in jours_joues
            color = "#00e9d8" if joue else "#1a1a2e"
            html_heatmap += f'<div class="heatmap-day" style="background:{color}" title="{d}"></div>'
        html_heatmap += '</div>'
    html_heatmap += '</div>'
    st.markdown(html_heatmap, unsafe_allow_html=True)
    st.caption(f"🟦 {len(jours_joues)} jour(s) joué(s)")

# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    history = stats.get("history", [])
    if not history:
        st.info("Pas encore d'historique. Termine une partie !")
    else:
        st.subheader(f"Historique des {len(history)} dernières parties")

        # Graphique évolution score
        scores = [e["score"] for e in history]
        labels = [f"#{i+1}" for i in range(len(history))]
        chart_data = {"Score": scores}
        import pandas as pd
        df = pd.DataFrame(chart_data, index=labels)
        st.line_chart(df, color="#00e9d8")

        # Tableau
        rows = []
        for i, e in enumerate(reversed(history)):
            rows.append({
                "N°":      len(history) - i,
                "Date":    e.get("date", "?"),
                "Score":   formater(e.get("score", 0)),
                "Coups":   e.get("moves", 0),
                "Clics":   e.get("clicks", 0),
                "Max":     formater(e.get("max", 0)),
                "Durée":   formater_duree(e.get("duree", 0)),
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

# ══════════════════════════════════════════════════════════════════════════════
with tab3:
    st.subheader("Rapport de la dernière partie")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Score Final",       formater(stats.get("last_score", 0)))
    with c2:
        st.metric("Mouvements",        stats.get("last_moves", 0))
    with c3:
        st.metric("Plus Grand Nombre", formater(stats.get("last_max", 0)))

    history = stats.get("history", [])
    if history:
        last = history[-1]
        c4, c5 = st.columns(2)
        with c4:
            st.metric("Clics",  last.get("clicks", 0))
        with c5:
            st.metric("Durée",  formater_duree(last.get("duree", 0)))

        # Efficacité
        moves = last.get("moves", 1) or 1
        eff   = last.get("score", 0) // moves
        st.metric("Efficacité (score/coup)", formater(eff))

# ══════════════════════════════════════════════════════════════════════════════
with tab4:
    debloques = set(stats.get("unlocked_achievements", []))
    total_d   = len(debloques)
    total_s   = len(SUCCES)

    st.subheader(f"Succès — {total_d}/{total_s} débloqués")
    st.progress(total_d / total_s)
    st.markdown("<br>", unsafe_allow_html=True)

    # Débloqués d'abord
    st.markdown("#### ✅ Débloqués")
    has_debloques = False
    for sid, info in SUCCES.items():
        if sid in debloques:
            has_debloques = True
            st.markdown(f'''
<div class="succes-ok">
    {info["emoji"]} <strong>{info["nom"]}</strong>
    {"&nbsp;&nbsp;<span style='font-size:0.7rem;background:#7c3aed;color:white;padding:2px 6px;border-radius:4px'>SECRET</span>" if info["secret"] else ""}
    <br><span style="color:#aaa;font-size:0.85rem">{info["desc"]}</span>
</div>''', unsafe_allow_html=True)
    if not has_debloques:
        st.caption("Aucun succès débloqué pour l'instant.")

    st.markdown("#### 🔒 Verrouillés")
    for sid, info in SUCCES.items():
        if sid not in debloques:
            if info["secret"]:
                st.markdown(f'''
<div class="succes-secret">
    ❓ <strong>???</strong>
    &nbsp;&nbsp;<span style='font-size:0.7rem;background:#7c3aed;color:white;padding:2px 6px;border-radius:4px'>SECRET</span>
    <br><span style="color:#666;font-size:0.85rem">Continue de jouer pour le découvrir...</span>
</div>''', unsafe_allow_html=True)
            else:
                st.markdown(f'''
<div class="succes-lock">
    🔒 <strong>{info["nom"]}</strong><br>
    <span style="color:#888;font-size:0.85rem">{info["desc"]}</span>
</div>''', unsafe_allow_html=True)
