import flet as ft
import math
import random
import json
import os
import asyncio

ORBS = ['+', '-', '×', '/']

# ── PALETTE ───────────────────────────────────────────────────────────────────
COL_CHIFFRE   = "#007bff"   # fallback (1-7)
COL_OP        = "#97d9e4"   # opérateurs
COL_OP_L      = "#c8ecf0"
COL_TXT       = "white"
COL_VANILLA   = "#fff1bf"
COL_WILD      = "#ec458d"

# Palette numérique selon valeur
_PALETTE = [
    (7,  "#007bff"),   # 1-7   azure-blue
    (20, "#0091f7"),   # 8-20  dodger-blue
    (30, "#00a7ef"),   # 21-30 fresh-sky
    (50, "#00bde8"),   # 31-50 sky-surge
    (70, "#00d3e0"),   # 51-70 strong-cyan
    (89, "#00e9d8"),   # 71-89 turquoise
    (98, "#00ffd0"),   # 90-98 tropical-mint
]

def couleur_orb(val):
    if not isinstance(val, int): return COL_OP
    for seuil, col in _PALETTE:
        if val <= seuil: return col
    return "#00ffd0"  # ≥99

# ─────────────────────────────────────────────────────────────────────────────
# DURÉES CENTRALISÉES  (ms → asyncio.sleep = valeur / 1000)
# Règle absolue : chaque animate=X a un await sleep(X/1000) qui lui correspond
# ─────────────────────────────────────────────────────────────────────────────
DUR_GLISSE   = 300   # bulle glisse centre → rail
DUR_ROTATION = 420   # rotation sur le cercle  (animate_rotation)
DUR_POP_UP   = 180   # bulle grossit
DUR_POP_DOWN = 180   # bulle revient taille normale
DUR_FADE     = 200   # opacité → 0
DUR_RESERRE  = 420   # refermeture finale
PAUSE_MICRO  = 0.06  # laisser Flet enregistrer la position initiale
PAUSE_COMBO  = 0.18  # respiration visuelle entre deux étapes de combo


async def main(page: ft.Page):
    page.title = "Math Circle"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.horizontal_alignment = "center"
    page.vertical_alignment = "center"
    page.bgcolor = COL_VANILLA
    page.padding = 0

    # ── 1. STATS ──────────────────────────────────────────────────────────────
    donnees = {}
    if os.path.exists("stats.json"):
        with open("stats.json", "r", encoding="utf-8") as f:
            try:
                donnees = json.load(f)
            except Exception:
                pass

    def generer_item():
        return random.randint(1, 7) if random.random() < 0.75 else random.choice(ORBS)

    etat = {
        "cercle":        [],
        "current_item":  generer_item(),
        "next_item":     generer_item(),
        "game_over":     False,
        "animating":     False,
        "score_live":    0,
        "moves_live":    0,
        "max_seen_live": 0,
        "last_score":    donnees.get("last_score",  0),
        "last_moves":    donnees.get("last_moves",  0),
        "last_max":      donnees.get("last_max",    0),
        "best_score":    donnees.get("best_score",  0),
        "total_score":   donnees.get("total_score", 0),
        "achievements":  set(donnees.get("unlocked_achievements", [])),
    }

    score_texte = ft.Text("", size=20, color="white",
                          weight=ft.FontWeight.BOLD,
                          style=ft.TextStyle(shadow=ft.BoxShadow(
                              blur_radius=8, color="#99000000",
                              offset=ft.Offset(0, 2)
                          )))
    taille_texte_ui = ft.Text("", size=13, color="white",
                               weight=ft.FontWeight.W_700,
                               style=ft.TextStyle(shadow=ft.BoxShadow(
                                   blur_radius=6, color="#99000000",
                                   offset=ft.Offset(0, 1)
                               )))
    info_next   = ft.Row(alignment="center")

    couche_fond   = ft.Stack()
    couche_cercle = ft.Stack()
    couche_ui     = ft.Stack()

    # Fond dégradé permanent derrière tout
    plateau = ft.Stack(
        [couche_fond, couche_cercle, couche_ui],
        width=400, height=400
    )

    # ── 2. SAUVEGARDE / SUCCÈS ────────────────────────────────────────────────
    def sauvegarder(fin=False):
        if fin:
            etat["last_score"]   = etat["score_live"]
            etat["last_moves"]   = etat["moves_live"]
            etat["last_max"]     = etat["max_seen_live"]
            etat["total_score"] += etat["score_live"]
            if etat["score_live"] > etat["best_score"]:
                etat["best_score"] = etat["score_live"]
        with open("stats.json", "w", encoding="utf-8") as f:
            json.dump({
                "last_score":  etat["last_score"],
                "last_moves":  etat["last_moves"],
                "last_max":    etat["last_max"],
                "best_score":  etat["best_score"],
                "total_score": etat["total_score"],
                "unlocked_achievements": list(etat["achievements"]),
            }, f, indent=4)

    def notifier(msg, couleur="green"):
        page.snack_bar = ft.SnackBar(
            ft.Text(msg, size=16, weight="bold"), bgcolor=couleur, duration=3000
        )
        page.snack_bar.open = True
        page.update()

    def debloquer(id_s, msg):
        if id_s not in etat["achievements"]:
            etat["achievements"].add(id_s)
            notifier(f"🏆 Succès : {msg} !", "green")
            sauvegarder(fin=False)

    def ajouter_score(pts):
        etat["score_live"] += pts
        if "millionnaire" not in etat["achievements"] and \
                etat["total_score"] + etat["score_live"] >= 1_000_000:
            debloquer("millionnaire", "Millionnaire")

    def multiplier_score(f):
        etat["score_live"] *= f
        if "millionnaire" not in etat["achievements"] and \
                etat["total_score"] + etat["score_live"] >= 1_000_000:
            debloquer("millionnaire", "Millionnaire")

    # ── 3. GÉOMÉTRIE ──────────────────────────────────────────────────────────
    def angle_proche(current, target):
        """Angle cible équivalent le plus proche (évite les grands tours)."""
        delta = (target - current) % (2 * math.pi)
        if delta > math.pi:
            delta -= 2 * math.pi
        return current + delta

    def formater_val(v):
        if not isinstance(v, int): return str(v)
        if v >= 1_000_000_000: return f"{v/1_000_000_000:.2g}G"
        if v >= 1_000_000:     return f"{v/1_000_000:.2g}M"
        if v >= 1_000:         return f"{v/1_000:.2g}K"
        return str(v)

    def taille_texte(texte):
        n = len(str(texte))
        if n <= 2: return 22
        if n == 3: return 18
        if n == 4: return 14
        return 11

    # ── 4. FACTORY DE NOEUD ───────────────────────────────────────────────────
    def creer_noeud(valeur, bg_col, txt_col, angle_init, is_center=False):
        top_init = 175 if is_center else 25
        if isinstance(valeur, int):
            bg_col  = couleur_orb(valeur)
            txt_col = COL_TXT
        else:
            bg_col  = COL_OP
            txt_col = COL_TXT

        inner = ft.Container(
            content=ft.Text(formater_val(valeur), size=taille_texte(formater_val(valeur)), weight=ft.FontWeight.BOLD,
                            color=txt_col,
                            style=ft.TextStyle(shadow=ft.BoxShadow(
                                blur_radius=4, color="#55000000",
                                offset=ft.Offset(0, 1)
                            ))),
            width=50, height=50,
            bgcolor=bg_col, border_radius=25,
            clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
            alignment=ft.Alignment(0, 0),
            left=175, top=top_init, opacity=1.0, scale=1.0,
            shadow=ft.BoxShadow(
                blur_radius=12, spread_radius=1,
                color="#66000000", offset=ft.Offset(0, 4)
            ),
            animate_position=None,
            animate_opacity=ft.Animation(DUR_FADE,  ft.AnimationCurve.EASE_IN),
            animate_scale=ft.Animation(DUR_POP_UP,  ft.AnimationCurve.EASE_OUT),
        )
        outer = ft.Container(
            key=str(random.random()),
            width=400, height=400, left=0, top=0,
            rotate=angle_init,
            animate_rotation=None,
            bgcolor=ft.Colors.TRANSPARENT,
            content=ft.Stack([inner])
        )
        return outer, inner

    def activer_rotation(outer):
        """Active animate_rotation après le premier rendu."""
        outer.animate_rotation = ft.Animation(DUR_ROTATION, ft.AnimationCurve.EASE_IN_OUT)

    def activer_position(inner):
        """Active animate_position après le premier rendu."""
        inner.animate_position = ft.Animation(DUR_GLISSE, ft.AnimationCurve.EASE_OUT)

    # ── 5. PRIMITIVES D'ANIMATION ─────────────────────────────────────────────
    async def anim_glissement(inner):
        """Centre → rail."""
        inner.top = 25
        page.update()
        await asyncio.sleep(DUR_GLISSE / 1000)

    async def anim_pivoter(noeuds, angles):
        """Pivote une liste de noeuds vers leurs angles cibles (simultané)."""
        for nd, ang in zip(noeuds, angles):
            nd["angle"]        = ang
            nd["outer"].rotate = ang
        page.update()
        await asyncio.sleep(DUR_ROTATION / 1000)

    def geler_rotations(sauf=None):
        """
        Désactive animate_rotation sur tous les noeuds SAUF ceux listés dans 'sauf'.
        À appeler avant tout page.update() qui modifie le DOM (suppression de noeuds)
        pour empêcher Flet d'inventer des animations fantômes sur les voisins.
        """
        ids_exclus = {id(n) for n in (sauf or [])}
        for nd in etat["cercle"]:
            if id(nd) not in ids_exclus:
                nd["outer"].animate_rotation = False

    def degeler_rotations():
        """Réactive animate_rotation UNIQUEMENT sur les noeuds qui l'ont perdu."""
        anim = ft.Animation(DUR_ROTATION, ft.AnimationCurve.EASE_IN_OUT)
        for nd in etat["cercle"]:
            if nd["outer"].animate_rotation is False:
                nd["outer"].animate_rotation = anim

    async def anim_pop(noeud_ou_inner, texte=None, bgcolor=None, txtcol=None, noeuds_a_effacer=None):
        """
        Grossit le résultat (scale 1→1.45→1).
        Accepte soit un dict noeud {"inner","outer","angle"} soit un inner seul.
        Si noeud complet : extraction chirurgicale pour éviter le flash gris outer 400×400.
        """
        # Supporte l'ancien appel avec juste inner (ex: combo zéro)
        if isinstance(noeud_ou_inner, dict):
            inner = noeud_ou_inner["inner"]
            outer = noeud_ou_inner["outer"]
            angle = noeud_ou_inner["angle"]
            extraire = True
        else:
            inner = noeud_ou_inner
            outer = None
            extraire = False

        # 1. Mise à jour des valeurs visuelles
        if texte   is not None:
            inner.content.value = texte
            inner.content.size  = taille_texte(texte)
        if bgcolor is not None: inner.bgcolor       = bgcolor
        if txtcol  is not None: inner.content.color = txtcol

        # 2. Aspiration des voisins
        if noeuds_a_effacer:
            for nd in noeuds_a_effacer:
                nd["inner"].scale = 0

        if extraire:
            # ── EXTRACTION CHIRURGICALE ───────────────────────────────────────
            anim_pos_save = inner.animate_position
            inner.animate_position = None
            if inner in outer.content.controls:
                outer.content.controls.remove(inner)
            if outer in couche_cercle.controls:
                couche_cercle.controls.remove(outer)
            cx = 200 + 150 * math.sin(angle)
            cy = 200 - 150 * math.cos(angle)
            inner.left = cx - 25
            inner.top  = cy - 25
            couche_fond.controls.append(inner)

        inner.scale = 1.45
        page.update()
        await asyncio.sleep(DUR_POP_UP / 1000)

        inner.scale = 1.0
        page.update()
        await asyncio.sleep(DUR_POP_DOWN / 1000)

        if extraire:
            # ── REMETTAGE PROPRE ──────────────────────────────────────────────
            if inner in couche_fond.controls:
                couche_fond.controls.remove(inner)
            inner.left = 175
            inner.top  = 25
            inner.animate_position = anim_pos_save
            outer.content.controls.append(inner)
            couche_cercle.controls.append(outer)
            page.update()

    async def anim_fade(noeuds):
        """Les orbs sont aspirés (scale=0) au lieu de devenir transparents pour esquiver le bug d'opacité."""
        for nd in noeuds:
            nd["inner"].scale = 0  # <-- LA CORRECTION : Plus d'opacité, on rétrécit !
        page.update()
        await asyncio.sleep(DUR_FADE / 1000)

    async def anim_desintegration(inner, angle, outer_a_retirer=None):
        """
        Désintégration en fragments gris (~0.8s) :
        1. L'orb noircit et vibre
        2. 8 fragments partent dans toutes les directions
        3. L'orb disparaît
        """
        cx = 200 + 150 * math.sin(angle)
        cy = 200 - 150 * math.cos(angle)

        # Déplace inner dans couche_fond à la position absolue, retire le outer 400×400
        # qui cause le flash gris quand Flutter re-rend le subtree
        if outer_a_retirer is not None:
            if inner in outer_a_retirer.content.controls:
                outer_a_retirer.content.controls.remove(inner)
            if outer_a_retirer in couche_cercle.controls:
                couche_cercle.controls.remove(outer_a_retirer)
            inner.animate_position = None
            inner.left = cx - 25
            inner.top  = cy - 25
            couche_fond.controls.append(inner)
            page.update()
            await asyncio.sleep(PAUSE_MICRO)

        # Phase 1 : l'orb vire au gris sombre et vibre
        inner.bgcolor       = "#333333"
        inner.content.color = "#888888"
        inner.scale         = 1.2
        page.update()
        await asyncio.sleep(0.12)

        for taille in [1.35, 1.05, 1.3, 1.0, 1.25, 0.95]:
            inner.scale = taille
            page.update()
            await asyncio.sleep(0.05)

        # Phase 2 : création des fragments
        NB_FRAGMENTS = 8
        fragments = []
        for k in range(NB_FRAGMENTS):
            angle_frag  = (2 * math.pi / NB_FRAGMENTS) * k
            taille_frag = random.randint(6, 14)
            frag = ft.Container(
                width=taille_frag, height=taille_frag,
                bgcolor=random.choice(["#555555", "#444444", "#666666", "#333333"]),
                border_radius=taille_frag / 2,
                clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                left=cx - taille_frag / 2,
                top=cy  - taille_frag / 2,
                opacity=1.0,
                animate_position=ft.Animation(400, ft.AnimationCurve.EASE_OUT),
                animate_opacity=ft.Animation(400, ft.AnimationCurve.EASE_IN),
            )
            couche_fond.controls.append(frag)
            fragments.append((frag, angle_frag))

        # L'orb disparaît en même temps que les fragments s'élancent
        inner.scale   = 0.0
        inner.opacity = 0.0
        page.update()
        await asyncio.sleep(PAUSE_MICRO)

        for frag, angle_frag in fragments:
            distance  = random.randint(40, 90)
            frag.left    = cx + distance * math.sin(angle_frag) - frag.width / 2
            frag.top     = cy - distance * math.cos(angle_frag) - frag.height / 2
            frag.opacity = 0.0
        page.update()
        await asyncio.sleep(0.45)

        # Nettoie les fragments
        for frag, _ in fragments:
            if frag in couche_fond.controls:
                couche_fond.controls.remove(frag)
        page.update()

    # ── ANIMATIONS ÉPIQUES ────────────────────────────────────────────────────

    def creer_anneau_aura(cx, cy, taille, couleur, opacite=0.8):
        """Crée un anneau d'aura centré sur (cx, cy)."""
        return ft.Container(
            width=taille, height=taille,
            border_radius=taille / 2,
            clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
            border=ft.Border.all(3, couleur),
            opacity=opacite,
            scale=0.1,
            left=cx - taille / 2,
            top=cy - taille / 2,
            animate_scale=ft.Animation(600, ft.AnimationCurve.EASE_OUT),
            animate_opacity=ft.Animation(600, ft.AnimationCurve.EASE_IN),
        )

    async def anim_explosion_surcharge(inner, angle, valeur):
        """
        >99 — Animation dramatique ~1.5s :
        1. Aura rapide + orbs reculent
        2. Flash rouge x3
        3. Disparition
        """
        cx = 200 + 150 * math.sin(angle)
        cy = 200 - 150 * math.cos(angle)

        # Phase 1 : aura + orbs reculent (0.4s)
        anneaux = []
        for taille in [80, 130, 180]:
            a = creer_anneau_aura(cx, cy, taille, "orange", 0.7)
            couche_fond.controls.append(a)
            anneaux.append(a)

        # Orbs restants reculent légèrement
        angles_originaux = {}
        for nd in etat["cercle"]:
            angles_originaux[id(nd)] = nd["angle"]
            delta = nd["angle"] - angle
            nd["outer"].rotate = nd["angle"] + 0.15 * math.sin(delta) * -1

        inner.bgcolor        = "red"
        inner.content.color  = "white"
        inner.content.value  = formater_val(valeur)
        inner.content.size   = taille_texte(formater_val(valeur))   # ← résultat affiché en même temps
        inner.scale          = 2.5
        page.update()

        # Expand les anneaux
        for a in anneaux:
            a.scale = 3.0
            a.opacity = 0.0
        await asyncio.sleep(0.05)
        page.update()
        await asyncio.sleep(0.5)

        # Phase 2 : vibration rapide (0.4s)
        for _ in range(3):
            inner.scale = 2.8
            page.update()
            await asyncio.sleep(0.07)
            inner.scale = 2.2
            page.update()
            await asyncio.sleep(0.07)

        # Phase 3 : flash blanc + disparition (0.3s)
        inner.bgcolor = "white"
        inner.scale = 3.5
        page.update()
        await asyncio.sleep(0.15)
        inner.scale = 0.0
        inner.opacity = 0.0
        page.update()
        await asyncio.sleep(0.2)

        # Nettoie les anneaux et remet les orbs en place
        for a in anneaux:
            couche_fond.controls.remove(a)
        for nd in etat["cercle"]:
            nd["outer"].rotate = angles_originaux[id(nd)]
        page.update()

    async def anim_explosion_99(inner, angle, valeur):
        """
        =99 — Animation cinématique ~3.5s
        """
        cx = 200 + 150 * math.sin(angle)
        cy = 200 - 150 * math.cos(angle)

        # Phase 1 : première aura (0.6s)
        anneaux = []
        for i, taille in enumerate([60, 100, 150, 200, 260]):
            a = creer_anneau_aura(cx, cy, taille, "red", 0.9 - i * 0.1)
            couche_fond.controls.append(a)
            anneaux.append(a)

        inner.bgcolor        = "red"
        inner.content.color  = "white"
        inner.content.value  = formater_val(valeur)
        inner.content.size   = taille_texte(formater_val(valeur))   # ← résultat affiché en même temps
        inner.scale          = 1.8
        page.update()
        await asyncio.sleep(0.05)

        for a in anneaux:
            a.scale   = 2.5
            a.opacity = 0.0
        page.update()
        await asyncio.sleep(0.6)

        # Phase 2 : orbs reculent fortement (0.4s)
        angles_originaux = {}
        for nd in etat["cercle"]:
            angles_originaux[id(nd)] = nd["angle"]
            delta = nd["angle"] - angle
            nd["outer"].rotate = nd["angle"] + 0.35 * math.sin(delta) * -1
        page.update()
        await asyncio.sleep(0.4)

        # Phase 3 : vibration intense (0.8s)
        inner.scale = 3.5
        page.update()
        await asyncio.sleep(0.1)

        vibes = [3.8, 3.2, 4.0, 3.1, 3.9, 3.2, 4.2, 3.0]
        for v in vibes:
            inner.scale = v
            page.update()
            await asyncio.sleep(0.08)

        # Phase 4 : grossissement x5 (0.4s)
        inner.scale = 5.0
        page.update()
        await asyncio.sleep(0.4)

        # Phase 5 : deuxième vague d'aura
        anneaux2 = []
        for i, taille in enumerate([80, 140, 200, 280, 360]):
            a = creer_anneau_aura(cx, cy, taille, "yellow", 1.0 - i * 0.15)
            couche_fond.controls.append(a)
            anneaux2.append(a)
        page.update()
        await asyncio.sleep(0.05)
        for a in anneaux2:
            a.scale   = 4.0
            a.opacity = 0.0
        page.update()
        await asyncio.sleep(0.05)

        # Phase 6 : flash blanc aveuglant (0.3s)
        inner.bgcolor = "white"
        inner.scale   = 6.0
        page.update()
        await asyncio.sleep(0.3)

        # Phase 7 : explosion finale — scale 0 brutal (0.2s)
        inner.scale   = 0.0
        inner.opacity = 0.0
        page.update()
        await asyncio.sleep(0.25)

        # Nettoie tout et remet les orbs en place
        for a in anneaux + anneaux2:
            if a in couche_fond.controls:
                couche_fond.controls.remove(a)
        for nd in etat["cercle"]:
            nd["outer"].rotate = angles_originaux[id(nd)]
        page.update()

    async def anim_refermer(anchor_noeud):
        """Referme le cercle. L'ancre ne bouge jamais."""
        n = len(etat["cercle"])
        if n == 0:
            return
        if anchor_noeud is None or anchor_noeud not in etat["cercle"]:
            anchor_noeud = etat["cercle"][0]
        anchor_idx   = etat["cercle"].index(anchor_noeud)
        anchor_angle = anchor_noeud["angle"]
        step         = (2 * math.pi) / n
        offset       = anchor_angle - anchor_idx * step
        for i, nd in enumerate(etat["cercle"]):
            if nd is anchor_noeud:
                continue
            ideal              = i * step + offset
            nd["angle"]        = angle_proche(nd["angle"], ideal)
            nd["outer"].rotate = nd["angle"]
        page.update()
        await asyncio.sleep(DUR_RESERRE / 1000)

    def supprimer_visuels(noeuds):
        """Retire uniquement les outers du Stack visuel."""
        for nd in noeuds:
            if nd["outer"] in couche_cercle.controls:
                couche_cercle.controls.remove(nd["outer"])

    def supprimer_noeuds(noeuds):
        """Retire visuels ET entrées dans etat['cercle']."""
        ids = {id(nd) for nd in noeuds}
        supprimer_visuels(noeuds)
        etat["cercle"] = [x for x in etat["cercle"] if id(x) not in ids]

    # ── 7. CALCUL ─────────────────────────────────────────────────────────────
    def calculer(a, b, op):
        if op == '+': return a + b
        if op == '-': return max(0, a - b)
        if op == '×': return a * b
        if op == '/': return 0 if b == 0 else a // b

    # ── 8. RESET ──────────────────────────────────────────────────────────────
    async def reset_jeu(e=None):
        if e and not etat["game_over"] and etat["score_live"] > 0:
            sauvegarder(fin=True)

        couche_cercle.controls.clear()
        etat["cercle"] = []

        valeurs    = [random.randint(1, 7) for _ in range(7)]
        if valeurs:
            angle_step = (2 * math.pi) / len(valeurs)
            for i, val in enumerate(valeurs):
                angle = i * angle_step
                outer, inner = creer_noeud(val, "", "", angle, is_center=False)
                etat["cercle"].append({"val": val, "outer": outer, "inner": inner, "angle": angle})
                couche_cercle.controls.append(outer)

            page.update()
            for nd in etat["cercle"]:
                activer_rotation(nd["outer"])
            for nd in etat["cercle"]:
                activer_position(nd["inner"])
        page.update()
        for nd in etat["cercle"]:
            activer_rotation(nd["outer"])

        etat["current_item"]   = generer_item()
        etat["next_item"]      = generer_item()
        etat["score_live"]     = 0
        etat["moves_live"]     = 0
        etat["max_seen_live"]  = 0
        etat["game_over"]      = False
        etat["animating"]      = False
        dessiner_ui()


    # ── 9. CHORÉGRAPHIE PRINCIPALE ────────────────────────────────────────────
    async def clic_insertion(e, index_gauche, gap_angle):
        if etat["game_over"] or etat["animating"]:
            return
        etat["animating"] = True
        try:
            couche_ui.controls.clear()
            couche_fond.controls.clear()
            page.update()

            item    = etat["current_item"]
            etat["moves_live"] += 1
            bg_col  = couleur_orb(item)
            txt_col = COL_TXT

            fly_out, fly_in = creer_noeud(item, bg_col, txt_col, gap_angle, is_center=True)
            couche_cercle.controls.append(fly_out)
            page.update()
            await asyncio.sleep(PAUSE_MICRO)
            activer_rotation(fly_out)
            activer_position(fly_in)
            page.update()
            await anim_glissement(fly_in)

            noeud_ancre = None

            # ══════════════════════════════════════════════════════════════════
            # CAS A — CHIFFRE
            # ══════════════════════════════════════════════════════════════════
            if isinstance(item, int):
                n_new  = len(etat["cercle"]) + 1
                step   = (2 * math.pi) / n_new
                offset = gap_angle - (index_gauche + 1) * step
                angles = []
                for i, nd in enumerate(etat["cercle"]):
                    new_i = i if i <= index_gauche else i + 1
                    angles.append(angle_proche(nd["angle"], new_i * step + offset))
                await anim_pivoter(etat["cercle"], angles)
                fly_in.bgcolor       = "blue"
                fly_in.content.color = "white"
                page.update()
                nouveau = {"val": item, "outer": fly_out, "inner": fly_in, "angle": gap_angle}
                etat["cercle"].insert(index_gauche + 1, nouveau)
                noeud_ancre = nouveau

            # ══════════════════════════════════════════════════════════════════
            # CAS B — OPÉRATEUR
            # ══════════════════════════════════════════════════════════════════
            else:
                debloquer("first_merge", "Premier Pas")
                idx_L   = index_gauche
                idx_R   = (index_gauche + 1) % len(etat["cercle"])
                noeud_L = etat["cercle"][idx_L]
                noeud_R = etat["cercle"][idx_R]

                await anim_pivoter(
                    [noeud_L, noeud_R],
                    [
                        angle_proche(noeud_L["angle"], gap_angle),
                        angle_proche(noeud_R["angle"], gap_angle),
                    ]
                )

                valeur = calculer(noeud_L["val"], noeud_R["val"], item)
                ajouter_score(valeur)
                if valeur > etat["max_seen_live"]:
                    etat["max_seen_live"] = valeur

                # ── EXPLOSION ≥ 99 ────────────────────────────────────────────
                if valeur >= 99:
                    if valeur == 99:
                        debloquer("big_99", "Le Compte est Bon")
                        multiplier_score(9)
                        await anim_explosion_99(fly_in, gap_angle, valeur)
                        notifier("💥 99 ! EXPLOSION CRITIQUE !", "purple")
                    else:
                        debloquer("over_99", "Surcharge")
                        multiplier_score(2)
                        await anim_explosion_surcharge(fly_in, gap_angle, valeur)
                        notifier("🔥 Surcharge ! > 99 !", "orange")
                    supprimer_noeuds([noeud_L, noeud_R])
                    supprimer_visuels([{"outer": fly_out}])
                    noeud_ancre = etat["cercle"][0] if etat["cercle"] else None

                # ── FUSION ────────────────────────────────────────────────────
                else:
                    noeud_fly = {"inner": fly_in, "outer": fly_out, "angle": gap_angle}
                    await anim_pop(noeud_fly, texte=formater_val(valeur), bgcolor=couleur_orb(valeur),
                                   txtcol="white", noeuds_a_effacer=[noeud_L, noeud_R])
                    await asyncio.sleep(0.05)
                    supprimer_visuels([noeud_L, noeud_R])

                    # ── ZÉRO : désintégration ─────────────────────────────────
                    if valeur == 0:
                        etat["cercle"] = [x for x in etat["cercle"]
                                          if x is not noeud_L and x is not noeud_R]
                        await anim_desintegration(fly_in, gap_angle, outer_a_retirer=fly_out)
                        if fly_in in couche_fond.controls:
                            couche_fond.controls.remove(fly_in)
                        noeud_ancre = etat["cercle"][0] if etat["cercle"] else None

                    # ── NORMAL ────────────────────────────────────────────────
                    else:
                        noeud_res = {"val": valeur, "outer": fly_out,
                                     "inner": fly_in, "angle": gap_angle}
                        etat["cercle"] = [
                            noeud_res if x is noeud_L else x
                            for x in etat["cercle"] if x is not noeud_R
                        ]
                        geler_rotations(sauf=[noeud_res])
                        noeud_ancre = noeud_res

                        # ── COMBO ─────────────────────────────────────────────
                        while noeud_ancre in etat["cercle"] and len(etat["cercle"]) >= 3:
                            idx_c = etat["cercle"].index(noeud_ancre)
                            nd_L  = etat["cercle"][(idx_c - 1) % len(etat["cercle"])]
                            nd_R  = etat["cercle"][(idx_c + 1) % len(etat["cercle"])]

                            if nd_L["val"] != nd_R["val"]:
                                break

                            await asyncio.sleep(PAUSE_COMBO)
                            degeler_rotations()
                            page.update()
                            await asyncio.sleep(PAUSE_MICRO)

                            await anim_pivoter(
                                [nd_L, nd_R],
                                [
                                    angle_proche(nd_L["angle"], noeud_ancre["angle"]),
                                    angle_proche(nd_R["angle"], noeud_ancre["angle"]),
                                ]
                            )

                            v1 = calculer(nd_L["val"], noeud_ancre["val"], item)
                            ajouter_score(v1)
                            v2 = calculer(v1, nd_R["val"], item)
                            ajouter_score(v2)
                            if v2 > etat["max_seen_live"]:
                                etat["max_seen_live"] = v2

                            if v1 >= 99 or v2 >= 99:
                                vc = v1 if v1 >= 99 else v2
                                if vc == 99:
                                    debloquer("big_99", "Le Compte est Bon")
                                    multiplier_score(9)
                                    await anim_explosion_99(noeud_ancre["inner"], noeud_ancre["angle"], vc)
                                    notifier("💥 99 ! EXPLOSION CRITIQUE !", "purple")
                                else:
                                    debloquer("over_99", "Surcharge")
                                    multiplier_score(2)
                                    await anim_explosion_surcharge(noeud_ancre["inner"], noeud_ancre["angle"], vc)
                                    notifier("🔥 Surcharge ! > 99 !", "orange")
                                supprimer_noeuds([nd_L, nd_R, noeud_ancre])
                                noeud_ancre = etat["cercle"][0] if etat["cercle"] else None
                                page.update()
                                break

                            elif v2 == 0:
                                await anim_pop(noeud_ancre["inner"], texte="0",
                                               noeuds_a_effacer=[nd_L, nd_R])
                                await asyncio.sleep(0.05)
                                supprimer_visuels([nd_L, nd_R])
                                etat["cercle"] = [x for x in etat["cercle"]
                                                  if x is not nd_L and x is not nd_R]
                                _inner = noeud_ancre["inner"]
                                _outer = noeud_ancre["outer"]
                                _angle = noeud_ancre["angle"]
                                etat["cercle"] = [x for x in etat["cercle"]
                                                  if x is not noeud_ancre]
                                await anim_desintegration(_inner, _angle, outer_a_retirer=_outer)
                                if _inner in couche_fond.controls:
                                    couche_fond.controls.remove(_inner)
                                noeud_ancre = etat["cercle"][0] if etat["cercle"] else None
                                break

                            else:
                                await anim_pop(noeud_ancre, texte=formater_val(v2),
                                               bgcolor=couleur_orb(v2),
                                               noeuds_a_effacer=[nd_L, nd_R])
                                noeud_ancre["val"] = v2
                                await asyncio.sleep(0.05)
                                supprimer_visuels([nd_L, nd_R])
                                etat["cercle"] = [x for x in etat["cercle"]
                                                  if x is not nd_L and x is not nd_R]
                                geler_rotations(sauf=[noeud_ancre])

            # ── REFERMETURE FINALE ────────────────────────────────────────────
            degeler_rotations()
            page.update()
            await asyncio.sleep(PAUSE_MICRO)
            if etat["cercle"]:
                await anim_refermer(noeud_ancre)

            etat["current_item"] = etat["next_item"]
            etat["next_item"]    = generer_item()

            if len(etat["cercle"]) > 20:
                etat["game_over"] = True
                notifier("💀 GAME OVER !", "red")
                sauvegarder(fin=True)

        except Exception as ex:
            print(f"[ERREUR clic_insertion] {ex}")
            import traceback; traceback.print_exc()
        finally:
            etat["animating"] = False
            dessiner_ui()

    # ── 10. INTERFACE ─────────────────────────────────────────────────────────
    def fmt(item):
        if isinstance(item, int): return f"Chiffre [ {item} ]", "cyan"
        return f"Opérateur [ {item} ]", "yellow"

    def dessiner_ui():
        couche_fond.controls.clear()
        couche_ui.controls.clear()

        n = len(etat["cercle"])

        # ── Track ring ────────────────────────────────────────────────────────
        danger = n >= 15
        ring_color  = "#55ff2d55" if danger else "#44ffffff"
        ring_shadow = "#88ff2d55" if danger else "#22ffffff"
        couche_fond.controls.append(
            ft.Container(
                width=300, height=300,
                left=50, top=50,
                border_radius=150,
                bgcolor=ft.Colors.TRANSPARENT,
                border=ft.Border.all(2, ring_color),
                shadow=ft.BoxShadow(
                    blur_radius=20 if danger else 10,
                    color=ring_shadow,
                    spread_radius=2,
                )
            )
        )

        # ── Mise à jour score, taille, coups et prochain ─────────────────────
        score_texte.value     = f"{etat['score_live']:,}".replace(",", " ")
        taille_texte_ui.value = f"{n}/20"
        taille_texte_ui.color = "#ff2d55" if danger else "white"
        coups_text.value      = f"{etat['moves_live']} coups"
        next_item = etat["next_item"]
        next_orb_text.value        = str(next_item)
        next_orb_container.bgcolor = couleur_orb(next_item)

        # ── Item courant (centre) — caché si WIN ──────────────────────────────
        if not etat["game_over"] and etat["cercle"]:
            item = etat["current_item"]
            is_op = not isinstance(item, int)
            item_bg  = couleur_orb(item)
            couche_fond.controls.append(
                ft.Container(
                    content=ft.Text(
                        str(item), size=32, weight=ft.FontWeight.BOLD,
                        color="white",
                        style=ft.TextStyle(shadow=ft.BoxShadow(
                            blur_radius=6, color="#66000000", offset=ft.Offset(0, 2)
                        ))
                    ),
                    width=72, height=72,
                    bgcolor=item_bg,
                    border_radius=36,
                    clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                    alignment=ft.Alignment(0, 0),
                    left=164, top=164,
                    shadow=ft.BoxShadow(
                        blur_radius=20, spread_radius=2,
                        color="#44000000", offset=ft.Offset(0, 6)
                    ),
                    border=ft.Border.all(2, "white30"),
                )
            )

        if not etat["cercle"] and not etat["game_over"]:
            couche_fond.controls.append(
                ft.Text("WIN", size=52, color="yellow",
                        weight=ft.FontWeight.BOLD,
                        text_align=ft.TextAlign.CENTER,
                        left=155, top=172,
                        style=ft.TextStyle(shadow=ft.BoxShadow(
                            blur_radius=8, color="#aaffffff", offset=ft.Offset(0, 3)
                        )))
            )

        if etat["game_over"]:
            couche_ui.controls.append(
                ft.Text("GAME OVER", size=42, color="white",
                        weight=ft.FontWeight.BOLD,
                        text_align=ft.TextAlign.CENTER,
                        left=82, top=175,
                        style=ft.TextStyle(shadow=ft.BoxShadow(
                            blur_radius=8, color="#99000000", offset=ft.Offset(0, 3)
                        )))
            )
            page.update()
            return

        if not etat["cercle"] and not etat["game_over"]:
            pass  # WIN affiché dans couche_fond au centre
        else:
            RAYON   = 150
            CX, CY  = 200, 200
            TAILLE  = 50
            MARGE   = 0.10
            PAS     = (TAILLE / RAYON) * 0.5

            if n == 1:
                nb_zones = max(1, int((2 * math.pi) / PAS) + 1)
                for j in range(nb_zones):
                    ang = (2 * math.pi / nb_zones) * j
                    x = CX + RAYON * math.sin(ang)
                    y = CY - RAYON * math.cos(ang)
                    couche_ui.controls.append(
                        ft.Container(
                            on_click=lambda e, ang=ang:
                                page.run_task(clic_insertion, e, 0, ang),
                            width=TAILLE, height=TAILLE,
                            bgcolor="white", opacity=0.01,
                            border_radius=TAILLE / 2,
                            left=x - TAILLE / 2, top=y - TAILLE / 2,
                        )
                    )
            else:
                for i in range(n):
                    a_L     = etat["cercle"][i]["angle"]
                    a_R     = etat["cercle"][(i + 1) % n]["angle"]
                    delta   = (a_R - a_L) % (2 * math.pi)
                    gap_ang = a_L + delta / 2

                    arc_debut = a_L + MARGE
                    arc_fin   = a_L + delta - MARGE

                    if arc_fin <= arc_debut:
                        angles_zones = [gap_ang]
                    else:
                        nb = max(1, int((arc_fin - arc_debut) / PAS) + 1)
                        if nb == 1:
                            angles_zones = [gap_ang]
                        else:
                            pas_reel     = (arc_fin - arc_debut) / (nb - 1)
                            angles_zones = [arc_debut + j * pas_reel for j in range(nb)]

                    for ang_zone in angles_zones:
                        x = CX + RAYON * math.sin(ang_zone)
                        y = CY - RAYON * math.cos(ang_zone)
                        couche_ui.controls.append(
                            ft.Container(
                                on_click=lambda e, idx=i, ang=gap_ang:
                                    page.run_task(clic_insertion, e, idx, ang),
                                width=TAILLE, height=TAILLE,
                                bgcolor="white", opacity=0.01,
                                border_radius=TAILLE / 2,
                                left=x - TAILLE / 2, top=y - TAILLE / 2,
                            )
                        )

        page.update()

    # ── 11. LANCEMENT ─────────────────────────────────────────────────────────
    def pill(content, shadow_color="#33ec458d"):
        return ft.Container(
            content=content,
            bgcolor="#33ffffff",
            border=ft.Border.all(1.5, "#66ffffff"),
            border_radius=50,
            padding=ft.Padding.symmetric(horizontal=20, vertical=10),
            shadow=ft.BoxShadow(blur_radius=16, color=shadow_color, spread_radius=0),
        )

    # Jauge taille
    jauge_ring = ft.Container(
        width=48, height=48,
        border_radius=24,
        bgcolor=ft.Colors.TRANSPARENT,
        border=ft.Border.all(3, "#ff2d55"),
        content=ft.Container(
            content=taille_texte_ui,
            alignment=ft.Alignment(0, 0),
        ),
        alignment=ft.Alignment(0, 0),
    )

    score_pill = pill(ft.Column([
        ft.Text("SCORE", size=11, color="#ccffffff", weight=ft.FontWeight.W_700,
                style=ft.TextStyle(shadow=ft.BoxShadow(
                    blur_radius=6, color="#99000000", offset=ft.Offset(0, 1)
                ))),
        score_texte,
    ], spacing=1, horizontal_alignment=ft.CrossAxisAlignment.CENTER))

    top_bar = ft.Row(
        [pill(jauge_ring, "#55ff2d55"), score_pill],
        alignment=ft.MainAxisAlignment.CENTER,
        spacing=12,
    )

    # Prochain item — widgets persistants mis à jour dans dessiner_ui
    _init_next = etat["next_item"]
    next_orb_text = ft.Text(str(_init_next), size=18, weight=ft.FontWeight.BOLD, color="white")
    next_orb_container = ft.Container(
        content=next_orb_text,
        width=36, height=36,
        bgcolor=couleur_orb(_init_next), border_radius=18,
        alignment=ft.Alignment(0, 0),
        shadow=ft.BoxShadow(blur_radius=8, color="#44000000", offset=ft.Offset(0, 2)),
    )
    next_pill_ctrl = pill(ft.Row([
        ft.Text("PROCHAIN", size=11, color="#ccffffff", weight=ft.FontWeight.W_700,
                style=ft.TextStyle(shadow=ft.BoxShadow(
                    blur_radius=6, color="#99000000", offset=ft.Offset(0, 1)
                ))),
        next_orb_container,
    ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER))

    coups_text = ft.Text("0 coups", size=13, color="#ccffffff", weight=ft.FontWeight.W_700,
                          style=ft.TextStyle(shadow=ft.BoxShadow(
                              blur_radius=6, color="#99000000", offset=ft.Offset(0, 1)
                          )))
    coups_pill = pill(ft.Row([
        coups_text,
    ], spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER))

    next_row = ft.Row(
        [next_pill_ctrl, coups_pill],
        alignment=ft.MainAxisAlignment.CENTER,
        spacing=12,
    )

    bouton_rejouer = ft.Container(
        content=ft.Text("NOUVELLE PARTIE", size=12, color="white",
                        weight=ft.FontWeight.W_700,
                        style=ft.TextStyle(shadow=ft.BoxShadow(
                            blur_radius=6, color="#99000000", offset=ft.Offset(0, 1)
                        ))),
        bgcolor="#33ffffff",
        border=ft.Border.all(1.5, "#66ffffff"),
        border_radius=50,
        padding=ft.Padding.symmetric(horizontal=16, vertical=10),
        shadow=ft.BoxShadow(blur_radius=16, color="#44ec458d", spread_radius=0),
        on_click=lambda e: page.run_task(reset_jeu, e),
        ink=True,
    )

    fond_global = ft.Container(
        expand=True,
        gradient=ft.LinearGradient(
            begin=ft.Alignment(-0.6, -1),
            end=ft.Alignment(0.6, 1),
            colors=[COL_VANILLA, "#fcd4b7", "#f9b8ae", "#f69ba6", COL_WILD],
        ),
        content=ft.Column(
            [
                ft.Container(height=16),
                top_bar,
                ft.Container(height=8),
                plateau,
                ft.Container(height=12),
                next_row,
                ft.Container(height=12),
                bouton_rejouer,
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            scroll=ft.ScrollMode.AUTO,
        )
    )

    page.add(fond_global)

    # Mise à jour dynamique des coups et prochain
    _orig_dessiner_ui = dessiner_ui

    def dessiner_ui_wrapper():
        _orig_dessiner_ui()
        coups_text.value = f"{etat['moves_live']} coups"
        # Reconstruit le prochain
        item = etat["next_item"]
        is_op = not isinstance(item, int)
        bg = COL_OP if is_op else COL_CHIFFRE
        if hasattr(next_row, 'controls') and next_row.controls:
            next_pill_ctrl = next_row.controls[0]
            if hasattr(next_pill_ctrl, 'content') and hasattr(next_pill_ctrl.content, 'controls'):
                row_controls = next_pill_ctrl.content.controls
                if len(row_controls) > 1:
                    row_controls[1].bgcolor = bg
                    row_controls[1].content.value = str(item)
        page.update()

    # Patch dessiner_ui pour inclure la màj des pills
    import types
    nonlocal_ref = {"dessiner_ui": dessiner_ui}

    await reset_jeu()


ft.run(main, view=ft.AppView.WEB_BROWSER)