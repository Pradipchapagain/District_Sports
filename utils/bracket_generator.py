import math
import random
from datetime import datetime
from io import BytesIO

# ReportLab Imports for PDF
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.pdfgen import canvas
from reportlab.lib.enums import TA_CENTER

# सामान्य कन्फिगरेसन (हेडरको लागि)
CONFIG = {
    'MUNICIPALITY_NAME_EN': 'Suryodaya Municipality',
    'OFFICE_NAME_EN': 'Office of the Municipal Executive',
    'EVENT_TITLE_EN': 'President Running Shield'
}

# ==========================================
# 1. BRACKET GENERATION LOGIC (For Team Games mostly)
# ==========================================
def generate_full_bracket(participants_df, seeded_list=None, category_type="Team Game"):
    """Generates the FULL bracket tree (Power of 2)."""
    if seeded_list is None: seeded_list = []
        
    participants = participants_df.to_dict('records')
    # 💡 Stringify IDs for safety, but keep muni_id
    for p in participants: 
        p['id'] = str(p.get('id', '0'))
        if 'muni_id' not in p: p['muni_id'] = None

    total_p = len(participants)
    if total_p < 2: return []
    
    # Power of 2 (Slots)
    next_power = 2**math.ceil(math.log2(total_p))
    total_slots = next_power
    num_byes = total_slots - total_p
    
    slots = [None] * total_slots
    
    # Seeding & Placement Logic
    seeds_obj = []
    non_seeds_obj = []
    
    for s_name in seeded_list:
        obj = next((p for p in participants if p['name'] == s_name), None)
        if obj: seeds_obj.append(obj)
            
    for p in participants:
        if p not in seeds_obj: non_seeds_obj.append(p)
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
    
    # Round 1
    for i in range(0, total_slots, 2):
        p1 = slots[i]
        p2 = slots[i+1]
        if p1 is None: p1 = {"id": "BYE", "name": "BYE", "municipality": "", "muni_id": None}
        if p2 is None: p2 = {"id": "BYE", "name": "BYE", "municipality": "", "muni_id": None}

        if p1['name'] == "BYE": p1, p2 = p2, p1
        
        winner_name, winner_id, winner_muni_id = None, None, None
        status = "Pending"
        if p2['name'] == "BYE":
            winner_name, winner_id, winner_muni_id = p1['name'], p1['id'], p1.get('muni_id')
            status = "Completed"

        # 💡 Updated Dictionary mapping to Postgres Structure
        m = {
            "match_no": match_id_counter,
            "round_name": "Round 1",
            "p1_name": p1['name'], 
            "team1_id": p1['id'] if category_type == "Team Game" else None, 
            "player1_id": p1['id'] if category_type != "Team Game" else None,
            "comp1_muni_id": p1.get('muni_id'),
            "p2_name": p2['name'], 
            "team2_id": p2['id'] if category_type == "Team Game" else None,
            "player2_id": p2['id'] if category_type != "Team Game" else None,
            "comp2_muni_id": p2.get('muni_id'),
            "winner_name": winner_name, 
            "winner_team_id": winner_id if category_type == "Team Game" else None,
            "winner_player_id": winner_id if category_type != "Team Game" else None,
            "winner_muni_id": winner_muni_id,
            "status": status,
            "next_match_id": None,
            "title": f"Match {match_id_counter}",
            "is_third_place": False,
            "pool": "A" if i < (total_slots / 2) else "B" 
        }
        current_round_matches.append(m)
        all_matches.append(m)
        match_id_counter += 1
        
    # Future Rounds
    round_num = 2
    while len(current_round_matches) > 1:
        next_round_temp = []
        is_semi_final_round = (len(current_round_matches) == 2)
        
        # Third Place Match (Only for Team Games, Martial Arts skip this)
        if is_semi_final_round and category_type == "Team Game":
            semi_m1 = current_round_matches[0]
            semi_m2 = current_round_matches[1]
            tp_match = {
                "match_no": match_id_counter, 
                "round_name": f"Round {round_num}", 
                "p1_name": f"Loser of #{semi_m1['match_no']}", "team1_id": None, "player1_id": None, "comp1_muni_id": None,
                "p2_name": f"Loser of #{semi_m2['match_no']}", "team2_id": None, "player2_id": None, "comp2_muni_id": None,
                "winner_name": None, "winner_team_id": None, "winner_player_id": None, "winner_muni_id": None,
                "status": "Pending",
                "title": "🥉 Third Place Match",
                "is_third_place": True,
                "pool": "Bronze Match", 
                "source_match1": semi_m1['match_no'],
                "source_match2": semi_m2['match_no'],
                "next_match_id": None
            }
            all_matches.append(tp_match)
            match_id_counter += 1

        # Next Round / Final
        for i in range(0, len(current_round_matches), 2):
            m1 = current_round_matches[i]
            m2 = current_round_matches[i+1]
            new_match_id = match_id_counter
            m1['next_match_id'] = new_match_id
            m2['next_match_id'] = new_match_id
            
            title = f"Match {new_match_id}"
            if len(current_round_matches) == 2: title = "🏆 FINAL"
            elif len(current_round_matches) == 4: title = f"Semi-Final {i//2 + 1}"
            
            new_m = {
                "match_no": new_match_id, 
                "round_name": f"Round {round_num}",
                "p1_name": f"Winner of #{m1['match_no']}", "team1_id": None, "player1_id": None, "comp1_muni_id": None,
                "p2_name": f"Winner of #{m2['match_no']}", "team2_id": None, "player2_id": None, "comp2_muni_id": None,
                "winner_name": None, "winner_team_id": None, "winner_player_id": None, "winner_muni_id": None,
                "status": "Pending",
                "next_match_id": None,
                "source_match1": m1['match_no'],
                "source_match2": m2['match_no'],
                "title": title,
                "is_third_place": False,
                "pool": m1.get('pool', 'A') if len(current_round_matches) > 2 else "Final" 
            }
            next_round_temp.append(new_m)
            all_matches.append(new_m)
            match_id_counter += 1
            
        current_round_matches = next_round_temp
        round_num += 1

    return all_matches

# ==========================================
# 2. PDF GENERATION LOGIC
# ==========================================
def generate_bracket_pdf(evt_name, gender, category, matches):
    """Generates a List View PDF."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    elements = []
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('TitleStyle', parent=styles['Title'], alignment=TA_CENTER, fontSize=14, spaceAfter=2)
    norm_center = ParagraphStyle('NormCenter', parent=styles['Normal'], alignment=TA_CENTER, fontSize=10)
    
    header_text = f"{CONFIG['MUNICIPALITY_NAME_EN']}<br/>{CONFIG['OFFICE_NAME_EN']}<br/><b>{CONFIG['EVENT_TITLE_EN']}</b>"
    elements.append(Paragraph(header_text, title_style))
    elements.append(Paragraph(f"<b>{evt_name}</b> ({category} - {gender})", norm_center))
    elements.append(Paragraph("Official Fixtures & Results", norm_center))
    elements.append(Spacer(1, 20))
    
    rounds = sorted(list(set(m.get('round_name', 'Round 1') for m in matches)))
    
    for r in rounds:
        matches_in_round = [m for m in matches if m.get('round_name', 'Round 1') == r]
        # Sort 3rd place to end
        matches_in_round.sort(key=lambda x: 1 if x.get('is_third_place') else 0)
        
        elements.append(Paragraph(f"<b>{str(r).upper()}</b>", styles['Heading2']))        
        elements.append(Spacer(1, 5))
        
        data = [['Match #', 'Team A (Blue)', 'VS', 'Team B (Red)', 'Winner']]
        row_colors = []
        
        for i, m in enumerate(matches_in_round):
            # 💡 Support both 'p1_name' and 'p1' keys
            p1 = str(m.get('p1_name', m.get('p1', '')))
            p2 = str(m.get('p2_name', m.get('p2', '')))
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
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]
        for row_idx, col in row_colors: tbl_style.append(('BACKGROUND', (0, row_idx), (-1, row_idx), col))
        t.setStyle(TableStyle(tbl_style))
        elements.append(t)
        elements.append(Spacer(1, 15))
        
    elements.append(Spacer(1, 30))
    elements.append(Paragraph(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ParagraphStyle('Footer', parent=styles['Italic'], fontSize=8, alignment=TA_CENTER)))
    
    doc.build(elements)
    buffer.seek(0)
    return buffer

def draw_bracket_node(c, x, y, match, width, height):
    """Draws a single match node for Visual Tree."""
    fill_color = colors.white
    stroke_color = colors.black
    text_color = colors.black
    
    if match.get('title') == "🏆 FINAL": fill_color = colors.gold; stroke_color = colors.darkgoldenrod
    elif "Semi-Final" in match.get('title', ''): fill_color = colors.lightsalmon
    elif match.get('is_third_place'): fill_color = colors.peru; text_color = colors.white
    
    c.setFillColor(fill_color)
    c.setStrokeColor(stroke_color)
    c.rect(x, y, width, height, fill=1, stroke=1)
    
    c.setFillColor(text_color)
    c.setFont("Helvetica-Bold", 6)
    m_no = match.get('id', match.get('match_no', ''))
    c.drawRightString(x + width - 2, y + height - 7, f"Match #{m_no}")
    
    def trim_name(n): return n[:18] + ".." if n and len(n) > 18 else (n if n else "")

    p1_name = trim_name(str(match.get('p1_name', match.get('p1', ''))))
    p2_name = trim_name(str(match.get('p2_name', match.get('p2', ''))))
    
    c.setFont("Helvetica", 7)
    c.drawString(x + 4, y + height - 10, p1_name)
    c.setLineWidth(0.5)
    c.line(x, y + height - 12, x + width, y + height - 12)
    c.drawString(x + 4, y + 4, p2_name)
    
    # 💡 PostgreSQL Logic for coloring winner dot
    winner_name = match.get('winner_name', match.get('winner'))
    if winner_name and winner_name != 'None':
        c.setFillColor(colors.green)
        if winner_name == p1_name: c.circle(x + width - 5, y + height - 8, 2, fill=1)
        elif winner_name == p2_name: c.circle(x + width - 5, y + 6, 2, fill=1)
            
    return y + (height / 2)

def generate_tree_pdf(evt_name, gender, category, matches):
    """Generates Visual Tree Bracket PDF."""
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=landscape(A4))
    width, height = landscape(A4)
    
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(width / 2, height - 40, CONFIG['MUNICIPALITY_NAME_EN'])
    c.setFont("Helvetica", 10)
    c.drawCentredString(width / 2, height - 55, CONFIG['OFFICE_NAME_EN'])
    c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(width / 2, height - 75, CONFIG['EVENT_TITLE_EN'])
    
    c.setFont("Helvetica", 10)
    c.drawCentredString(width / 2, height - 95, f"{evt_name} ({category} - {gender}) - Tournament Bracket")
    c.line(30, height - 105, width - 30, height - 105)

    tp_match = next((m for m in matches if m.get('is_third_place')), None)
    main_matches = [m for m in matches if not m.get('is_third_place')]
    main_matches.sort(key=lambda x: x.get('match_no', x.get('id', 0)))
    
    if not main_matches:
        c.drawString(50, height/2, "No matches available to display.")
        c.save()
        buffer.seek(0)
        return buffer

    rounds = sorted(list(set(m.get('round_name', '1') for m in main_matches)))
    total_rounds = len(rounds)
    
    x_start = 40
    box_width = 110
    box_height = 35
    x_gap = (width - 80 - box_width) / total_rounds if total_rounds > 0 else 100
    
    match_positions = {} 
    
    for r_idx, r in enumerate(rounds):
        current_matches = [m for m in main_matches if m.get('round_name', '1') == r]
        x_pos = x_start + (r_idx * x_gap)
        
        label = "FINAL" if r == max(rounds) else str(r).upper()
        c.setFont("Helvetica-Bold", 9)
        c.setFillColor(colors.darkblue)
        c.drawCentredString(x_pos + (box_width/2), height - 120, label)
        
        for i, m in enumerate(current_matches):
            y_pos = 0
            if r_idx == 0: # First round
                total_m = len(current_matches)
                available_h = height - 180 
                y_step = available_h / (total_m + 1)
                y_pos = height - 140 - ((i + 1) * y_step)
            else:
                src1_id = m.get('source_match1', m.get('source_m1'))
                src2_id = m.get('source_match2', m.get('source_m2'))
                
                if src1_id in match_positions and src2_id in match_positions:
                    y1 = match_positions[src1_id]
                    y2 = match_positions[src2_id]
                    y_pos = (y1 + y2) / 2 - (box_height / 2)
                    
                    c.setLineWidth(1)
                    c.setStrokeColor(colors.gray)
                    c.line(x_pos - (x_gap - box_width), y1, x_pos - 15, y1) 
                    c.line(x_pos - 15, y1, x_pos - 15, y_pos + box_height/2) 
                    c.line(x_pos - 15, y_pos + box_height/2, x_pos, y_pos + box_height/2) 
                    
                    c.line(x_pos - (x_gap - box_width), y2, x_pos - 15, y2) 
                    c.line(x_pos - 15, y2, x_pos - 15, y_pos + box_height/2)
                else:
                    y_pos = (height/2) - (box_height/2)

            mid_y = draw_bracket_node(c, x_pos, y_pos, m, box_width, box_height)
            m_no = m.get('match_no', m.get('id'))
            match_positions[m_no] = mid_y
            
            if r_idx < total_rounds - 1:
                c.setStrokeColor(colors.gray)
                c.line(x_pos + box_width, mid_y, x_pos + box_width + 10, mid_y)
                
    if tp_match:
        last_round_x = x_start + ((total_rounds - 1) * x_gap)
        tp_y_pos = 80 
        c.setFillColor(colors.black)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(last_round_x, tp_y_pos + box_height + 5, "🥉 Third Place")
        draw_bracket_node(c, last_round_x, tp_y_pos, tp_match, box_width, box_height)

    c.setFont("Helvetica-Oblique", 7)
    c.setFillColor(colors.gray)
    c.drawString(30, 20, f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    
    c.save()
    buffer.seek(0)
    return buffer