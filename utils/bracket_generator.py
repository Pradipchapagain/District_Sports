import math
import random
import pandas as pd
import streamlit as st
import database as db
from datetime import datetime
from io import BytesIO

# ReportLab Imports for PDF
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.pdfgen import canvas
from reportlab.lib.enums import TA_CENTER

# सामान्य कन्फिगरेसन
CONFIG = {
    'MUNICIPALITY_NAME_EN': 'Suryodaya Municipality',
    'OFFICE_NAME_EN': 'Office of the Municipal Executive',
    'EVENT_TITLE_EN': 'President Running Shield'
}

# ==========================================
# 1. BRACKET GENERATION LOGIC (General)
# ==========================================
def generate_full_bracket(participants_df, seeded_list=None, category_type="Team Game"):
    if seeded_list is None: seeded_list = []
        
    participants = participants_df.to_dict('records')
    for p in participants: 
        p['id'] = str(p.get('id', '0'))
        if 'muni_id' not in p: p['muni_id'] = None

    total_p = len(participants)
    if total_p < 2: return []
    
    next_power = 2**math.ceil(math.log2(total_p))
    total_slots = next_power
    num_byes = total_slots - total_p
    slots = [None] * total_slots
    
    seeds_obj = [next((p for p in participants if p['name'] == s_name), None) for s_name in seeded_list]
    seeds_obj = [obj for obj in seeds_obj if obj]
    non_seeds_obj = [p for p in participants if p not in seeds_obj]
    random.shuffle(non_seeds_obj)
    
    all_teams_ordered = seeds_obj + non_seeds_obj

    if total_slots == 4: match_indices = [0, 2]
    elif total_slots == 8: match_indices = [0, 4, 2, 6]
    elif total_slots == 16: match_indices = [0, 8, 4, 12, 2, 10, 6, 14]
    elif total_slots == 32: match_indices = [0, 16, 8, 24, 4, 20, 12, 28, 2, 18, 10, 26, 6, 22, 14, 30]
    else: match_indices = list(range(0, total_slots, 2))

    byes_assigned_count = 0
    for idx in match_indices:
        if all_teams_ordered: slots[idx] = all_teams_ordered.pop(0)
    for idx in match_indices:
        partner_idx = idx + 1
        if byes_assigned_count < num_byes:
            slots[partner_idx] = {"id": "BYE", "name": "BYE", "municipality": "", "muni_id": None}
            byes_assigned_count += 1
        else:
            if all_teams_ordered: slots[partner_idx] = all_teams_ordered.pop(0)
            else: slots[partner_idx] = {"id": "BYE", "name": "BYE", "municipality": "", "muni_id": None}

    all_matches = []
    match_id_counter = 1
    current_round_matches = []
    
    for i in range(0, total_slots, 2):
        p1, p2 = slots[i], slots[i+1]
        if p1 is None: p1 = {"id": "BYE", "name": "BYE", "municipality": "", "muni_id": None}
        if p2 is None: p2 = {"id": "BYE", "name": "BYE", "municipality": "", "muni_id": None}

        if p1['name'] == "BYE": p1, p2 = p2, p1
        
        winner_name, winner_id, winner_muni_id = None, None, None
        status = "Pending"
        if p2['name'] == "BYE":
            winner_name, winner_id, winner_muni_id = p1['name'], p1['id'], p1.get('muni_id')
            status = "Completed"

        m = {
            "match_no": match_id_counter, "round_name": "Round 1",
            "p1_name": p1['name'], "team1_id": p1['id'] if category_type == "Team Game" else None, "player1_id": p1['id'] if category_type != "Team Game" else None, "comp1_muni_id": p1.get('muni_id'),
            "p2_name": p2['name'], "team2_id": p2['id'] if category_type == "Team Game" else None, "player2_id": p2['id'] if category_type != "Team Game" else None, "comp2_muni_id": p2.get('muni_id'),
            "winner_name": winner_name, "winner_team_id": winner_id if category_type == "Team Game" else None, "winner_player_id": winner_id if category_type != "Team Game" else None, "winner_muni_id": winner_muni_id,
            "status": status, "next_match_id": None, "title": f"Match {match_id_counter}", "is_third_place": False, "pool": "A" if i < (total_slots / 2) else "B" 
        }
        current_round_matches.append(m)
        all_matches.append(m)
        match_id_counter += 1
        
    round_num = 2
    while len(current_round_matches) > 1:
        next_round_temp = []
        is_semi_final_round = (len(current_round_matches) == 2)
        
        if is_semi_final_round and category_type == "Team Game":
            semi_m1, semi_m2 = current_round_matches[0], current_round_matches[1]
            tp_match = {
                "match_no": match_id_counter, "round_name": f"Round {round_num}", 
                "p1_name": f"Loser of #{semi_m1['match_no']}", "team1_id": None, "player1_id": None, "comp1_muni_id": None,
                "p2_name": f"Loser of #{semi_m2['match_no']}", "team2_id": None, "player2_id": None, "comp2_muni_id": None,
                "winner_name": None, "winner_team_id": None, "winner_player_id": None, "winner_muni_id": None,
                "status": "Pending", "title": "🥉 Third Place Match", "is_third_place": True, "pool": "Bronze Match", 
                "source_match1": semi_m1['match_no'], "source_match2": semi_m2['match_no'], "next_match_id": None
            }
            all_matches.append(tp_match)
            match_id_counter += 1

        for i in range(0, len(current_round_matches), 2):
            m1, m2 = current_round_matches[i], current_round_matches[i+1]
            new_match_id = match_id_counter
            m1['next_match_id'], m2['next_match_id'] = new_match_id, new_match_id
            
            title = "🏆 FINAL" if len(current_round_matches) == 2 else f"Semi-Final {i//2 + 1}" if len(current_round_matches) == 4 else f"Match {new_match_id}"
            
            new_m = {
                "match_no": new_match_id, "round_name": f"Round {round_num}",
                "p1_name": f"Winner of #{m1['match_no']}", "team1_id": None, "player1_id": None, "comp1_muni_id": None,
                "p2_name": f"Winner of #{m2['match_no']}", "team2_id": None, "player2_id": None, "comp2_muni_id": None,
                "winner_name": None, "winner_team_id": None, "winner_player_id": None, "winner_muni_id": None,
                "status": "Pending", "next_match_id": None, "source_match1": m1['match_no'], "source_match2": m2['match_no'],
                "title": title, "is_third_place": False, "pool": m1.get('pool', 'A') if len(current_round_matches) > 2 else "Final" 
            }
            next_round_temp.append(new_m)
            all_matches.append(new_m)
            match_id_counter += 1
            
        current_round_matches = next_round_temp
        round_num += 1

    return all_matches

# ==========================================
# 2. PDF GENERATION LOGIC (List View)
# ==========================================
def generate_bracket_pdf(evt_name, gender, category, matches):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    elements = []
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('TitleStyle', parent=styles['Title'], alignment=TA_CENTER, fontSize=14, spaceAfter=2)
    norm_center = ParagraphStyle('NormCenter', parent=styles['Normal'], alignment=TA_CENTER, fontSize=10)
    
    elements.append(Paragraph(f"{CONFIG['MUNICIPALITY_NAME_EN']}<br/>{CONFIG['OFFICE_NAME_EN']}<br/><b>{CONFIG['EVENT_TITLE_EN']}</b>", title_style))
    elements.append(Paragraph(f"<b>{evt_name}</b> ({category} - {gender})", norm_center))
    elements.append(Paragraph("Official Fixtures & Results", norm_center))
    elements.append(Spacer(1, 20))
    
    rounds = sorted(list(set(m.get('round_name', 'Round 1') for m in matches)))
    
    for r in rounds:
        matches_in_round = [m for m in matches if m.get('round_name', 'Round 1') == r]
        matches_in_round.sort(key=lambda x: 1 if x.get('is_third_place') else 0)
        
        elements.append(Paragraph(f"<b>{str(r).upper()}</b>", styles['Heading2']))        
        elements.append(Spacer(1, 5))
        
        data = [['Match #', 'Team A (Blue)', 'VS', 'Team B (Red)', 'Winner']]
        row_colors = []
        
        for i, m in enumerate(matches_in_round):
            p1, p2 = str(m.get('p1_name', m.get('p1', ''))), str(m.get('p2_name', m.get('p2', '')))
            winner = str(m.get('winner_name', m.get('winner', ''))) 
            if winner == 'None': winner = "-"
            
            if p2 == "BYE": p2 = "(BYE)"; winner = p1 + " (Auto)"
            elif p1 == "BYE": p1 = "(BYE)"; winner = p2 + " (Auto)"
            
            m_label = str(m.get('id', m.get('match_no', '')))
            bg_col = colors.whitesmoke
            
            if m.get('title') == "🏆 FINAL": m_label += " (Final)"; bg_col = colors.lightyellow
            elif m.get('is_third_place'): m_label += " (3rd Place)"; bg_col = colors.oldlace
            elif "Semi-Final" in m.get('title', ''): bg_col = colors.aliceblue

            data.append([m_label, p1, "vs", p2, winner])
            row_colors.append((i+1, bg_col))

        t = Table(data, colWidths=[70, 150, 30, 150, 130])
        tbl_style = [
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue), ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'), ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8), ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]
        for row_idx, col in row_colors: tbl_style.append(('BACKGROUND', (0, row_idx), (-1, row_idx), col))
        t.setStyle(TableStyle(tbl_style))
        elements.append(t)
        elements.append(Spacer(1, 15))
        
    elements.append(Spacer(1, 30))
    elements.append(Paragraph(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ParagraphStyle('Footer', parent=styles['Italic'], fontSize=8, alignment=TA_CENTER)))
    
    doc.build(elements)
    return BytesIO(buffer.getvalue())

# ==========================================
# 3. PDF TREE VIEW (हाँगा भएको टाइ-सिट)
# ==========================================
def draw_bracket_node(c, x, y, match, width, height):
    """PDF मा एउटा म्याचको बाकस (Node) बनाउने"""
    fill_color = colors.white
    stroke_color = colors.darkblue
    
    title_up = str(match.get('title', '')).upper()
    is_final = ('FINAL' in title_up) and not ('QUARTER' in title_up) and not ('SEMI' in title_up)
    is_third = ('THIRD' in title_up) or ('🥉' in title_up) or match.get('is_third_place')
    
    if is_final: fill_color = colors.lightyellow; stroke_color = colors.darkgoldenrod
    elif is_third: fill_color = colors.oldlace; stroke_color = colors.peru
    elif "SEMI" in title_up: fill_color = colors.aliceblue
    
    c.setFillColor(fill_color)
    c.setStrokeColor(stroke_color)
    c.rect(x, y, width, height, fill=1, stroke=1)
    
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 6)
    m_no = match.get('id', str(match.get('match_no', '')))
    c.drawRightString(x + width - 2, y + height - 7, f"M #{m_no}")
    
    def trim_name(n): return n[:18] + ".." if n and len(n) > 18 else (n if n else "")

    p1_name = trim_name(str(match.get('p1_name', match.get('p1', ''))))
    p2_name = trim_name(str(match.get('p2_name', match.get('p2', ''))))
    
    c.setFont("Helvetica", 7)
    c.drawString(x + 4, y + height - 10, p1_name)
    c.setLineWidth(0.5)
    c.line(x, y + height - 13, x + width, y + height - 13)
    c.drawString(x + 4, y + 4, p2_name)
    
    winner_name = trim_name(str(match.get('winner_name', match.get('winner', ''))))
    if winner_name and winner_name != 'None':
        c.setFillColor(colors.green)
        if winner_name == p1_name: c.circle(x + width - 5, y + height - 7, 2, fill=1)
        elif winner_name == p2_name: c.circle(x + width - 5, y + 5, 2, fill=1)
            
    return y + (height / 2)

def generate_tree_pdf(evt_name, gender, category, matches):
    """१००% गणितमा आधारित (Mathematical) परफेक्ट ट्री जेनेरेटर"""
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=landscape(A4))
    width, height = landscape(A4)
    
    # 💡 हेडर खण्ड
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(width / 2, height - 30, CONFIG.get('MUNICIPALITY_NAME_EN', 'Suryodaya Municipality'))
    c.setFont("Helvetica", 10)
    c.drawCentredString(width / 2, height - 45, CONFIG.get('OFFICE_NAME_EN', 'Office of the Municipal Executive'))
    c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(width / 2, height - 60, CONFIG.get('EVENT_TITLE_EN', 'President Running Shield'))
    c.setFont("Helvetica", 10)
    c.drawCentredString(width / 2, height - 75, f"{evt_name} ({category} - {gender}) - Tournament Bracket")
    c.line(30, height - 85, width - 30, height - 85)

    main_matches = [m for m in matches if not (str(m.get('title','')).upper().find('THIRD') != -1 or m.get('is_third_place'))]
    tp_match = next((m for m in matches if str(m.get('title','')).upper().find('THIRD') != -1 or m.get('is_third_place')), None)
    
    if not main_matches:
        c.drawString(50, height/2, "No matches available to display.")
        c.save()
        return BytesIO(buffer.getvalue())

    # =========================================================
    # 💡 जादु यहाँ छ: गणित लगाएर बाकसको 'Exact Position' पत्ता लगाउने
    # =========================================================
    max_match_no = max([int(m.get('match_no', m.get('id', 0))) for m in main_matches])
    if max_match_no <= 1: total_r1_slots = 1
    else: total_r1_slots = 2 ** int(math.floor(math.log2(max_match_no - 1)))
    
    total_rounds_math = int(math.log2(total_r1_slots)) + 1
    
    # म्याच नम्बरको आधारमा यो कुन राउण्ड र कुन पोजिसनको म्याच हो भनेर निकाल्ने
    def get_match_logical_info(m_id):
        m_id = int(m_id)
        start_id = 1
        slots_in_round = total_r1_slots
        r_idx = 0
        while slots_in_round >= 1:
            end_id = start_id + slots_in_round - 1
            if start_id <= m_id <= end_id:
                return r_idx, m_id - start_id
            if slots_in_round == 2: start_id = end_id + 2 # थर्ड प्लेसलाई छोड्न
            else: start_id = end_id + 1
            slots_in_round = int(slots_in_round / 2)
            r_idx += 1
        return 0, 0

    # यो म्याच पानाको ठ्याक्कै कुन उचाइ (Y) मा बस्नुपर्छ भनेर निकाल्ने
    def get_ideal_y(r_idx, logical_idx):
        available_h = height - 150
        y_step_r1 = available_h / (total_r1_slots + 1)
        if r_idx == 0:
            return height - 110 - ((logical_idx + 1) * y_step_r1)
        # अगाडिको राउण्डको दुईवटा बाकसको ठ्याक्कै बीचमा (Average)
        y1 = get_ideal_y(r_idx - 1, logical_idx * 2)
        y2 = get_ideal_y(r_idx - 1, logical_idx * 2 + 1)
        return (y1 + y2) / 2

    # =========================================================
    
    x_start = 40
    box_width = 110
    box_height = 32
    x_gap = (width - 80 - box_width) / (total_rounds_math - 1) if total_rounds_math > 1 else 100
    
    # राउण्डको हेडरहरू (ROUND 1, ROUND 2)
    for r_idx in range(total_rounds_math):
        x_pos = x_start + (r_idx * x_gap)
        label = "FINAL" if r_idx == total_rounds_math - 1 else f"ROUND {r_idx + 1}"
        c.setFont("Helvetica-Bold", 9)
        c.setFillColor(colors.darkblue)
        c.drawCentredString(x_pos + (box_width/2), height - 100, label)

    # म्याचका बाकस र लाइनहरू कोर्ने
    for m in main_matches:
        m_id = int(m.get('match_no', m.get('id', 0)))
        r_idx, logical_idx = get_match_logical_info(m_id)
        
        x_pos = x_start + (r_idx * x_gap)
        mid_y = get_ideal_y(r_idx, logical_idx)
        y_pos = mid_y - (box_height / 2)
        
        # हाँगाहरू (Connecting Lines) कोर्ने
        if r_idx > 0:
            y1 = get_ideal_y(r_idx - 1, logical_idx * 2)
            y2 = get_ideal_y(r_idx - 1, logical_idx * 2 + 1)
            
            c.setLineWidth(1)
            c.setStrokeColor(colors.gray)
            
            line_x_start = x_pos - (x_gap - box_width)
            
            # माथिको हाँगा
            c.line(line_x_start, y1, x_pos - 15, y1)
            c.line(x_pos - 15, y1, x_pos - 15, mid_y)
            # तलको हाँगा
            c.line(line_x_start, y2, x_pos - 15, y2)
            c.line(x_pos - 15, y2, x_pos - 15, mid_y)
            # बाकसमा जोड्ने लाइन
            c.line(x_pos - 15, mid_y, x_pos, mid_y)
            
        draw_bracket_node(c, x_pos, y_pos, m, box_width, box_height)
        
    # 🥉 Third Place लाई पुछारमा छुट्टै राख्ने
    if tp_match:
        last_round_x = x_start + ((total_rounds_math - 1) * x_gap)
        tp_y_pos = 40 
        c.setFillColor(colors.black)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(last_round_x, tp_y_pos + box_height + 5, "🥉 Third Place Match")
        draw_bracket_node(c, last_round_x, tp_y_pos, tp_match, box_width, box_height)

    # फुटर
    c.setFont("Helvetica-Oblique", 7)
    c.setFillColor(colors.gray)
    c.drawString(30, 20, f"Generated automatically on: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    
    c.save()
    return BytesIO(buffer.getvalue())

# ==============================================================
# 4. TEAM GAMES SPECIFIC BRACKET LOGIC (UI Integration)
# ==============================================================
def generate_team_bracket(bracket_df, seeded_teams, event_code):
    teams = bracket_df['name'].tolist()
    if len(teams) < 2:
        st.error("⚠️ टाइ-सिट बनाउन कम्तीमा २ वटा टिम दर्ता हुनुपर्छ!")
        return False 
        
    team_data_map = {}
    for _, row in bracket_df.iterrows():
        team_data_map[row['name']] = {
            'team_id': int(row['id']) if pd.notna(row['id']) else None,
            'muni_id': int(row['municipality_id']) if pd.notna(row['municipality_id']) else None
        }
    
    non_seeded = [t for t in teams if t not in seeded_teams]
    random.shuffle(non_seeded)
    
    all_teams = []
    for s in seeded_teams:
        if s in teams: all_teams.append(s)
    all_teams.extend(non_seeded)
    
    n = len(all_teams)
    power_of_2 = 2 ** math.ceil(math.log2(n)) if n > 0 else 0
    total_slots = power_of_2
    
    # 💡 अन्तर्राष्ट्रिय सिडिङ अर्डर (१, १६, ८, ९...)
    def get_seed_order(sz):
        order = [0]
        while len(order) < sz:
            cur_len = len(order)
            new_order = []
            for i in range(cur_len):
                new_order.append(order[i])
                new_order.append(cur_len * 2 - 1 - order[i])
            order = new_order
        return order

    seed_order = get_seed_order(total_slots)
    slots = [None] * total_slots
    
    for i in range(n):
        slots[seed_order[i]] = all_teams[i]
    for i in range(n, total_slots):
        slots[seed_order[i]] = "BYE"
        
    matches = []
    match_id = 1
    r1_matches = []
    
    for i in range(0, total_slots, 2):
        p1_name, p2_name = slots[i], slots[i+1]
        if p1_name == "BYE" and p2_name != "BYE":
            p1_name, p2_name = p2_name, p1_name
            
        t1_info = team_data_map.get(p1_name, {})
        t2_info = team_data_map.get(p2_name, {})
        
        status = 'Pending'
        w_team_id, w_muni_id = None, None
        
        if p2_name == "BYE" and p1_name != "BYE":
            status = 'Completed'
            w_team_id = t1_info.get('team_id')
            w_muni_id = t1_info.get('muni_id')

        m = {
            'match_no': match_id, 'event_code': event_code, 'round_name': 'Round 1', 'title': 'Round 1',
            'p1_name': p1_name, 'team1_id': t1_info.get('team_id'), 'comp1_muni_id': t1_info.get('muni_id'),
            'p2_name': p2_name, 'team2_id': t2_info.get('team_id'), 'comp2_muni_id': t2_info.get('muni_id'),
            'status': status, 'is_third_place': False,
            'winner_team_id': w_team_id, 'winner_muni_id': w_muni_id
        }
        matches.append(m)
        r1_matches.append(match_id)
        match_id += 1
        
    current_round_matches = r1_matches
    current_round = 2
    
    while len(current_round_matches) > 1:
        next_round_temp = []
        is_semi_final = (len(current_round_matches) == 2)
        
        if is_semi_final:
            m1_id, m2_id = current_round_matches[0], current_round_matches[1]
            tp_match = {
                'match_no': match_id, 'event_code': event_code, 'round_name': f"Round {current_round}", 'title': '🥉 Third Place',
                'p1_name': f"Loser of #{m1_id}", 'team1_id': None, 'comp1_muni_id': None,
                'p2_name': f"Loser of #{m2_id}", 'team2_id': None, 'comp2_muni_id': None,
                'status': 'Pending', 'is_third_place': True, 'source_match1': m1_id, 'source_match2': m2_id,
                'winner_team_id': None, 'winner_muni_id': None
            }
            matches.append(tp_match)
            match_id += 1
            
        for i in range(0, len(current_round_matches), 2):
            m1_id, m2_id = current_round_matches[i], current_round_matches[i+1]
            r_title = "Quarter-Final" if len(current_round_matches)==8 else "Semi-Final" if len(current_round_matches)==4 else "🏆 FINAL" if len(current_round_matches)==2 else f"Round {current_round}"
            
            m = {
                'match_no': match_id, 'event_code': event_code, 'round_name': f"Round {current_round}", 'title': r_title,
                'p1_name': f"Winner of #{m1_id}", 'team1_id': None, 'comp1_muni_id': None, 
                'p2_name': f"Winner of #{m2_id}", 'team2_id': None, 'comp2_muni_id': None,
                'status': 'Pending', 'is_third_place': False, 'source_match1': m1_id, 'source_match2': m2_id,
                'winner_team_id': None, 'winner_muni_id': None
            }
            matches.append(m)
            next_round_temp.append(match_id)
            match_id += 1

        current_round_matches = next_round_temp
        current_round += 1

    # 💡 BYE प्रोपेगेसन (Auto-advance BYEs)
    for _ in range(5): 
        match_dict = {m['match_no']: m for m in matches}
        for m in matches:
            if m['status'] != 'Completed':
                if m['p2_name'] == "BYE" and "Winner" not in str(m['p1_name']) and "Loser" not in str(m['p1_name']):
                    m['winner_team_id'], m['winner_muni_id'], m['status'] = m['team1_id'], m['comp1_muni_id'], 'Completed'
                elif m['p1_name'] == "BYE" and "Winner" not in str(m['p2_name']) and "Loser" not in str(m['p2_name']):
                    m['winner_team_id'], m['winner_muni_id'], m['status'] = m['team2_id'], m['comp2_muni_id'], 'Completed'
                elif m['p1_name'] == "BYE" and m['p2_name'] == "BYE":
                    m['status'] = 'Completed'

            for p_side in ['p1_name', 'p2_name']:
                if "Winner of #" in str(m[p_side]):
                    src_id = int(str(m[p_side]).split("#")[1])
                    src_m = match_dict.get(src_id)
                    if src_m and src_m['status'] == 'Completed':
                        if src_m.get('winner_team_id'):
                            is_p1_w = src_m['winner_team_id'] == src_m['team1_id']
                            m[p_side] = src_m['p1_name'] if is_p1_w else src_m['p2_name']
                            if p_side == 'p1_name':
                                m['team1_id'] = src_m['team1_id'] if is_p1_w else src_m['team2_id']
                                m['comp1_muni_id'] = src_m['comp1_muni_id'] if is_p1_w else src_m['comp2_muni_id']
                            else:
                                m['team2_id'] = src_m['team1_id'] if is_p1_w else src_m['team2_id']
                                m['comp2_muni_id'] = src_m['comp1_muni_id'] if is_p1_w else src_m['comp2_muni_id']
                        elif src_m['p1_name'] == "BYE" and src_m['p2_name'] == "BYE":
                            m[p_side] = "BYE"

    conn = db.get_connection()
    c = conn.cursor()
    try:
        c.execute("ALTER TABLE matches ADD COLUMN IF NOT EXISTS p1_name VARCHAR(255)")
        c.execute("ALTER TABLE matches ADD COLUMN IF NOT EXISTS p2_name VARCHAR(255)")
        c.execute("ALTER TABLE matches ADD COLUMN IF NOT EXISTS is_third_place BOOLEAN DEFAULT FALSE")
        c.execute("ALTER TABLE matches ADD COLUMN IF NOT EXISTS winner_team_id INTEGER")
        c.execute("ALTER TABLE matches ADD COLUMN IF NOT EXISTS winner_muni_id INTEGER")
        conn.commit()
    except Exception:
        conn.rollback() 

    c.execute("DELETE FROM matches WHERE event_code=%s", (event_code,))
    
    try:
        for m in matches:
            # 💡 BYE vs BYE (Dummy) लाई डाटाबेसमा सेभ नगर्ने
            if m['p1_name'] == "BYE" and m['p2_name'] == "BYE":
                continue

            c.execute("""
                INSERT INTO matches (event_code, match_no, round_name, title, p1_name, team1_id, comp1_muni_id, p2_name, team2_id, comp2_muni_id, status, is_third_place, source_match1, source_match2, winner_team_id, winner_muni_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (m['event_code'], m['match_no'], m['round_name'], m['title'], m['p1_name'], m['team1_id'], m['comp1_muni_id'], m['p2_name'], m['team2_id'], m['comp2_muni_id'], m['status'], m['is_third_place'], m.get('source_match1'), m.get('source_match2'), m.get('winner_team_id'), m.get('winner_muni_id')))
        conn.commit()
        return True
    except Exception as e:
        st.error(f"❌ Database Insert Error: {e}")
        conn.rollback()
        return False
    finally:
        c.close()
        conn.close() 

def update_bracket_flow(matches):
    match_dict = {m['match_no']: m for m in matches}
    updates_needed = False
    
    for m in matches:
        if "Winner of #" in str(m['p1_name']):
            src_id = int(str(m['p1_name']).split("#")[1])
            src_m = match_dict.get(src_id)
            if src_m and src_m.get('winner_team_id'):
                is_p1_winner = src_m['winner_team_id'] == src_m['team1_id']
                m['p1_name'] = src_m['p1_name'] if is_p1_winner else src_m['p2_name']
                m['team1_id'] = src_m['team1_id'] if is_p1_winner else src_m['team2_id']
                m['comp1_muni_id'] = src_m['comp1_muni_id'] if is_p1_winner else src_m['comp2_muni_id']
                updates_needed = True

        if "Winner of #" in str(m['p2_name']):
            src_id = int(str(m['p2_name']).split("#")[1])
            src_m = match_dict.get(src_id)
            if src_m and src_m.get('winner_team_id'):
                is_p1_winner = src_m['winner_team_id'] == src_m['team1_id']
                m['p2_name'] = src_m['p1_name'] if is_p1_winner else src_m['p2_name']
                m['team2_id'] = src_m['team1_id'] if is_p1_winner else src_m['team2_id']
                m['comp2_muni_id'] = src_m['comp1_muni_id'] if is_p1_winner else src_m['comp2_muni_id']
                updates_needed = True
                
        if "Loser of #" in str(m['p1_name']):
            src_id = int(str(m['p1_name']).split("#")[1])
            src_m = match_dict.get(src_id)
            if src_m and src_m.get('winner_team_id'):
                is_p1_winner = src_m['winner_team_id'] == src_m['team1_id']
                m['p1_name'] = src_m['p2_name'] if is_p1_winner else src_m['p1_name']
                m['team1_id'] = src_m['team2_id'] if is_p1_winner else src_m['team1_id']
                m['comp1_muni_id'] = src_m['comp2_muni_id'] if is_p1_winner else src_m['comp1_muni_id']
                updates_needed = True
                
        if "Loser of #" in str(m['p2_name']):
            src_id = int(str(m['p2_name']).split("#")[1])
            src_m = match_dict.get(src_id)
            if src_m and src_m.get('winner_team_id'):
                is_p1_winner = src_m['winner_team_id'] == src_m['team1_id']
                m['p2_name'] = src_m['p2_name'] if is_p1_winner else src_m['p1_name']
                m['team2_id'] = src_m['team2_id'] if is_p1_winner else src_m['team1_id']
                m['comp2_muni_id'] = src_m['comp2_muni_id'] if is_p1_winner else src_m['comp1_muni_id']
                updates_needed = True
                
        if m.get('status', 'Pending') != 'Completed':
            if m['p2_name'] == "BYE" and "Winner" not in str(m['p1_name']) and "Loser" not in str(m['p1_name']):
                m['winner_team_id'], m['winner_muni_id'], m['status'] = m['team1_id'], m['comp1_muni_id'], 'Completed'
                updates_needed = True
            elif m['p1_name'] == "BYE" and "Winner" not in str(m['p2_name']) and "Loser" not in str(m['p2_name']):
                m['winner_team_id'], m['winner_muni_id'], m['status'] = m['team2_id'], m['comp2_muni_id'], 'Completed'
                updates_needed = True

    if updates_needed:
        conn = db.get_connection()
        c = conn.cursor()
        for m in matches:
            if m['p1_name'] == "BYE" and m['p2_name'] == "BYE": continue
                
            c.execute("""
                UPDATE matches SET p1_name=%s, team1_id=%s, comp1_muni_id=%s, 
                                   p2_name=%s, team2_id=%s, comp2_muni_id=%s, 
                                   winner_team_id=%s, winner_muni_id=%s, status=%s 
                WHERE match_no=%s AND event_code=%s
            """, (m['p1_name'], m['team1_id'], m['comp1_muni_id'], 
                  m['p2_name'], m['team2_id'], m['comp2_muni_id'], 
                  m.get('winner_team_id'), m.get('winner_muni_id'), m.get('status'), 
                  m['match_no'], m['event_code']))
        conn.commit()
        c.close()
        conn.close()
    return matches