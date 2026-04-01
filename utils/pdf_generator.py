import pandas as pd
import re
from io import BytesIO
from datetime import datetime
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT

# ==============================================================
# 💡 १. साझा हेडर (Common Header) - सबै PDF मा अटोमेटिक आउने
# ==============================================================
def get_official_header(event_info, CONFIG, document_title):
    """यसले हेडरको डिजाइन तयार गरेर Elements को लिस्ट फर्काउँछ"""
    styles = getSampleStyleSheet()
    elements = []
    
    org_style = ParagraphStyle('Org', parent=styles['Title'], alignment=TA_CENTER, fontSize=15, spaceAfter=2)
    event_title_style = ParagraphStyle('EventTitle', parent=styles['Title'], alignment=TA_CENTER, fontSize=13, spaceAfter=8, textColor=colors.darkblue)
    info_style = ParagraphStyle('Info', parent=styles['Normal'], alignment=TA_CENTER, fontSize=10, spaceAfter=6) 
    doc_title_style = ParagraphStyle('DocTitle', parent=styles['Normal'], alignment=TA_CENTER, fontSize=12, spaceAfter=10)
    event_left_style = ParagraphStyle('EventLeft', parent=styles['Normal'], alignment=TA_LEFT, fontSize=11, spaceAfter=5)
    
    organizer = CONFIG.get('ORGANIZER_NAME_EN', 'District Sports Development Committee').upper()
    event_name = CONFIG.get('EVENT_TITLE_EN', 'President Running Shield')
    
    elements.append(Paragraph(f"<b>{organizer}</b>", org_style))
    elements.append(Paragraph(f"<b>{event_name}</b>", event_title_style))
    
    if 'category' in event_info:
        cat_text = f"<b>Category:</b> {event_info.get('category','')} &nbsp; | &nbsp; <b>Sub-Category:</b> {event_info.get('sub_category','')} &nbsp; | &nbsp; <b>Group:</b> {event_info.get('event_group','')}"
        elements.append(Paragraph(cat_text, info_style))
        
    elements.append(Paragraph(f"<b><u>{document_title.upper()}</u></b>", doc_title_style))
    
    if 'name' in event_info and 'gender' in event_info:
        elements.append(Paragraph(f"<b>Event: {event_info['name'].upper()} - ({event_info['gender']})</b>", event_left_style))
        
    return elements

# ==============================================================
# 💡 २. साझा फुटर (Common Footer) 
# ==============================================================
def add_official_footer(canvas, doc):
    canvas.saveState()
    page_width = canvas._pagesize[0] 
    
    canvas.setFont('Helvetica-Bold', 10)
    canvas.drawCentredString(page_width * 0.2, 40, "Recorded By")
    canvas.drawCentredString(page_width * 0.5, 40, "Starter / Referee")
    canvas.drawCentredString(page_width * 0.8, 40, "Chief Judge")
    
    canvas.setFont('Helvetica', 10)
    canvas.drawCentredString(page_width * 0.2, 55, "___________________")
    canvas.drawCentredString(page_width * 0.5, 55, "___________________")
    canvas.drawCentredString(page_width * 0.8, 55, "___________________")
    
    canvas.setFont('Helvetica-Oblique', 8)
    canvas.setFillColor(colors.dimgrey)
    current_time = datetime.now().strftime("%Y-%m-%d %I:%M %p")
    footer_text = f"System generated official document | Printed on: {current_time}"
    canvas.drawCentredString(page_width / 2.0, 15, footer_text)
    canvas.restoreState()


# ==============================================================
# 🏃 ३. Track & Field (Heat, Relay, Lap)
# ==============================================================
def generate_heat_sheet_pdf(event_info, heats_df, CONFIG):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=20, leftMargin=20, topMargin=15, bottomMargin=80)
    styles = getSampleStyleSheet()
    
    # 💡 साझा हेडर बोलाइएको
    elements = get_official_header(event_info, CONFIG, "START LIST / SCORE SHEET")
    
    name_style = ParagraphStyle('NameStyle', fontSize=10, leading=13)
    header_style = ParagraphStyle('Hdr', fontSize=10, fontName='Helvetica-Bold', alignment=TA_CENTER)
    
    unique_heats = sorted(heats_df['heat'].unique())
    for h in unique_heats:
        is_final = str(h).upper() == "FINAL"
        elements.append(Paragraph(f"<b>{'FINAL ROUND' if is_final else f'HEAT {h}'}</b>", styles['Heading3']))
        elements.append(Spacer(1, 5))
        
        if is_final: headers = [Paragraph('Lane', header_style), Paragraph('Chest', header_style), Paragraph('Player Name & Municipality', header_style), Paragraph('Time', header_style), Paragraph('Rank', header_style), Paragraph('Medal', header_style), Paragraph('Remark', header_style)]
        else: headers = [Paragraph('Lane', header_style), Paragraph('Chest', header_style), Paragraph('Player Name & Municipality', header_style), Paragraph('Time', header_style), Paragraph('Rank', header_style), Paragraph('Q (Y/N)', header_style), Paragraph('Remark', header_style)]
                       
        table_data = [headers]
        heat_rows = heats_df[heats_df['heat'] == h].sort_values(by='lane')
        
        for _, row in heat_rows.iterrows():
            clean_mun = re.sub(r'[\u0900-\u097F]+|\(\s*\)', '', str(row.get('municipality', ''))).strip()
            formatted_name = f"<b>{row['name']}</b><br/><font size=8 color='#444444'>({clean_mun})</font>"
            table_data.append([str(row['lane']), '', Paragraph(formatted_name, name_style), '', '', '', ''])
            
        t = Table(table_data, colWidths=[35, 40, 220, 70, 45, 60, 85])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.lightgrey), ('GRID', (0,0), (-1,-1), 0.5, colors.black),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('ALIGN', (0,0), (1,-1), 'CENTER'), ('ALIGN', (2,1), (2,-1), 'LEFT'),
            ('TOPPADDING', (0,0), (-1,-1), 4), ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 15))

    doc.build(elements, onFirstPage=add_official_footer, onLaterPages=add_official_footer)
    return buffer.getvalue()


def generate_relay_heat_sheet_pdf(event_info, heats_df, CONFIG):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=20, leftMargin=20, topMargin=15, bottomMargin=80)
    styles = getSampleStyleSheet()
    
    # 💡 साझा हेडर बोलाइएको
    elements = get_official_header(event_info, CONFIG, "RELAY START LIST / SCORE SHEET")
    
    name_style = ParagraphStyle('NameStyle', fontSize=10, leading=14) 
    header_style = ParagraphStyle('Hdr', fontSize=9, fontName='Helvetica-Bold', alignment=TA_CENTER)
    
    unique_heats = sorted(heats_df['heat'].unique())
    for h in unique_heats:
        is_final = str(h).upper() == "FINAL"
        elements.append(Paragraph(f"<b>{'FINAL ROUND' if is_final else f'HEAT {h}'}</b>", styles['Heading3']))
        elements.append(Spacer(1, 5))
        
        if is_final: headers = [Paragraph('Lane', header_style), Paragraph('Municipality & Squad', header_style), Paragraph('Time', header_style), Paragraph('Rank', header_style), Paragraph('Medal', header_style), Paragraph('Remark', header_style)]
        else: headers = [Paragraph('Lane', header_style), Paragraph('Municipality & Squad', header_style), Paragraph('Time', header_style), Paragraph('Rank', header_style), Paragraph('Q (Y/N)', header_style), Paragraph('Remark', header_style)]
            
        table_data = [headers]
        heat_rows = heats_df[heats_df['heat'] == h].sort_values(by='lane')
        
        for _, row in heat_rows.iterrows():
            clean_mun = re.sub(r'[\u0900-\u097F]+|\(\s*\)', '', str(row.get('name', row.get('municipality', '')))).strip().upper()
            players_list = [p.strip() for p in re.split(r'[,|]', str(row.get('players_list', ''))) if p.strip()]
            
            inner_data = [[Paragraph("<font size=7 color='#444444'><b>Leg</b></font>", styles['Normal']), Paragraph("<font size=7 color='#444444'><b>Player Name</b></font>", styles['Normal']), Paragraph("<font size=7 color='#444444'><b>OK</b></font>", styles['Normal']), Paragraph("<font size=7 color='#444444'><b>DNF</b></font>", styles['Normal'])]]
            for p in players_list:
                inner_data.append(["", Paragraph(f"<font size=8>{p}</font>", styles['Normal']), Paragraph("<font size=7 color='#333333'>OK</font>", styles['Normal']), Paragraph("<font size=7 color='#333333'>DNF</font>", styles['Normal'])])
                
            inner_table = Table(inner_data, colWidths=[25, 135, 40, 40])
            inner_table.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 0.25, colors.grey), ('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('ALIGN', (0,0), (0,-1), 'CENTER'), ('ALIGN', (1,0), (3,-1), 'LEFT'), ('TOPPADDING', (0,0), (-1,-1), 3), ('BOTTOMPADDING', (0,0), (-1,-1), 3)]))
            
            cell_content = [Paragraph(f"<b>{clean_mun}</b>", name_style), Spacer(1, 3), inner_table]
            table_data.append([str(row['lane']), cell_content, '', '', '', ''])
            
        t = Table(table_data, colWidths=[40, 240, 60, 50, 60, 90])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.lightgrey), ('GRID', (0,0), (-1,-1), 0.5, colors.black),
            ('VALIGN', (0,0), (-1,-1), 'TOP'), ('ALIGN', (0,0), (0,-1), 'CENTER'), ('ALIGN', (1,0), (1,-1), 'LEFT'), ('ALIGN', (2,0), (-1,-1), 'CENTER'),
            ('TOPPADDING', (0,0), (-1,-1), 6), ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 15))

    doc.build(elements, onFirstPage=add_official_footer, onLaterPages=add_official_footer)
    return buffer.getvalue()


# ==============================================================
# 🏐 ६. Team Games (Volleyball, Kabaddi) Lineup Slip
# ==============================================================
def generate_lineup_sheet_pdf(event_info, CONFIG):
    from io import BytesIO
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from reportlab.lib import colors

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=15, bottomMargin=15)
    elements = []
    styles = getSampleStyleSheet()

    for i in range(2):
        # 💡 साझा हेडर बोलाइएको
        elements.extend(get_official_header(event_info, CONFIG, "OFFICIAL TEAM LINE-UP SHEET"))
        elements.append(Spacer(1, 10))

        info_data = [
            [Paragraph("<b>Team Name:</b> _______________________", styles['Normal']), Paragraph("<b>Match No:</b> ______", styles['Normal']), Paragraph("<b>Date:</b> ____________", styles['Normal'])],
            [Paragraph("<b>Opponent:</b> _______________________", styles['Normal']), Paragraph("<b>Set No:</b> ______", styles['Normal']), Paragraph("<b>Time:</b> ____________", styles['Normal'])]
        ]
        t_info = Table(info_data, colWidths=[220, 120, 150])
        t_info.setStyle(TableStyle([('ALIGN', (0,0), (-1,-1), 'LEFT'), ('BOTTOMPADDING', (0,0), (-1,-1), 8)]))
        elements.append(t_info)
        elements.append(Spacer(1, 5))

        header_style = ParagraphStyle('Hdr', fontSize=9, fontName='Helvetica-Bold', alignment=TA_CENTER)
        headers = [Paragraph('SN', header_style), Paragraph('Jersey No.', header_style), Paragraph('Player Name', header_style), Paragraph('Role (C/L)', header_style), Paragraph('Starting Pos. / Sub', header_style)]
        
        table_data = [headers]
        for j in range(1, 13):
            table_data.append([str(j), '', '', '', ''])
            
        t_players = Table(table_data, colWidths=[30, 60, 210, 70, 140])
        t_players.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.lightgrey), ('GRID', (0,0), (-1,-1), 0.5, colors.black),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'), ('ALIGN', (2,1), (2,-1), 'LEFT'), ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('TOPPADDING', (0,0), (-1,-1), 3), ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ]))
        elements.append(t_players)
        elements.append(Spacer(1, 15))

        sig_data = [["______________________", "______________________"], ["Coach Signature", "Captain Signature"]]
        t_sig = Table(sig_data, colWidths=[250, 250])
        t_sig.setStyle(TableStyle([('ALIGN', (0,0), (-1,-1), 'CENTER'), ('FONT', (0,0), (-1,-1), 'Helvetica'), ('TOPPADDING', (0,0), (-1,-1), 5)]))
        elements.append(t_sig)
        
        if i == 0:
            elements.append(Spacer(1, 15))
            elements.append(Paragraph("- - - - - - - - - - - - - - - - - - - - - - - - - - - - ✂️ - - - - - - - - - - - - - - - - - - - - - - - - - - -", ParagraphStyle('Cut', alignment=TA_CENTER, textColor=colors.grey)))
            elements.append(Spacer(1, 15))

    doc.build(elements)
    return buffer.getvalue()

def generate_prefilled_lineup_pdf(event_info, match_info, t1_players, t2_players, CONFIG):
    """A4 तेर्सो (Landscape) मा खेल अनुसार (Volleyball/Kabaddi) प्रि-फिल्ड लाइनअप सिट"""
    from io import BytesIO
    import re
    from reportlab.lib.pagesizes import landscape, A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from reportlab.lib import colors

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), rightMargin=15, leftMargin=15, topMargin=20, bottomMargin=20)
    elements = []
    styles = getSampleStyleSheet()

    sub_cat = event_info.get('sub_category', 'Volleyball') # खेल कुन हो भनेर चिन्ने

    def clean_nepali(text):
        """नेपाली अक्षर र खाली कोष्ठक हटाउने फङ्सन"""
        if not text: return ""
        cleaned = re.sub(r'[\u0900-\u097F]+', '', text) # नेपाली अक्षर हटाउने
        cleaned = re.sub(r'\(\s*\)', '', cleaned).strip() # खाली कोष्ठक () हटाउने
        return cleaned

    def create_team_slip(team_raw, opp_raw, players):
        slip_elements = []
        team_name = clean_nepali(team_raw)
        opp_name = clean_nepali(opp_raw)

        # 💡 हेडर (Sheet थपिएको)
        slip_elements.append(Paragraph(f"<b>{CONFIG.get('EVENT_TITLE_EN', 'President Running Shield')}</b>", ParagraphStyle('T', alignment=TA_CENTER, fontSize=12, textColor=colors.darkblue)))
        slip_elements.append(Paragraph(f"<b>{event_info['name']} ({event_info['gender']}) - Official Line-up Sheet</b>", ParagraphStyle('S', alignment=TA_CENTER, fontSize=10)))
        slip_elements.append(Spacer(1, 10))

        # 💡 म्याच र समयको जानकारी (खेल अनुसार Set वा Half)
        period_label = "Half:" if sub_cat == "Kabaddi" else "Set No:"
        i_style = ParagraphStyle('I', fontSize=9)
        info_t = Table([
            [Paragraph(f"<b>Team:</b> <font color='blue'>{team_name}</font>", i_style), Paragraph(f"<b>Match No:</b> #{match_info['id']}", i_style)],
            [Paragraph(f"<b>Opponent:</b> <font color='red'>{opp_name}</font>", i_style), Paragraph(f"<b>{period_label}</b> _________", i_style)]
        ], colWidths=[200, 110])
        info_t.setStyle(TableStyle([('BOTTOMPADDING', (0,0), (-1,-1), 8)]))
        slip_elements.append(info_t)

        # 💡 खेल अनुसार टेबलको हेडर र गाइड (Legend)
        h_style = ParagraphStyle('H', fontSize=8, fontName='Helvetica-Bold', alignment=TA_CENTER)
        
        if sub_cat == "Kabaddi":
            # 💡 फिक्स: कबड्डीको अफिसियल नियम अनुसार Start 7 र Bench राखियो
            headers = [Paragraph('SN', h_style), Paragraph('Jersey', h_style), Paragraph('Player Name', h_style), Paragraph('Role (C)', h_style), Paragraph('Start 7 / Bench', h_style)]
            legend_text = "* Note: C = Captain, Start 7 = Starting Seven Players, Bench = Substitutes"
        else: # Default Volleyball
            headers = [Paragraph('SN', h_style), Paragraph('Jersey', h_style), Paragraph('Player Name', h_style), Paragraph('Role (C/L)', h_style), Paragraph('Pos (I-VI)', h_style)]
            legend_text = "* Note: C = Captain, L = Libero, Pos = Starting Position (I to VI)"

        n_style = ParagraphStyle('N', fontSize=8)
        table_data = [headers]

        for i in range(12):
            sn = str(i+1)
            j_no, p_name = "", ""
            if i < len(players):
                j_no = str(players[i].get('jersey_no') or '')
                p_name = clean_nepali(str(players[i].get('player_name') or '')) # नेपाली नाम काट्ने
            table_data.append([sn, j_no, Paragraph(f"<b>{p_name}</b>", n_style), '', ''])

        t_players = Table(table_data, colWidths=[25, 40, 150, 60, 60])
        t_players.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 0.5, colors.black),
            ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
            ('ALIGN', (0,0), (1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('TOPPADDING', (0,0), (-1,-1), 3),
            ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ]))
        slip_elements.append(t_players)
        
        # 💡 टेबलको पुछारमा गाइड (Legend)
        slip_elements.append(Spacer(1, 2))
        slip_elements.append(Paragraph(legend_text, ParagraphStyle('L', fontSize=7, textColor=colors.dimgrey)))
        slip_elements.append(Spacer(1, 10))

        # हस्ताक्षर
        sig_t = Table([["__________________", "__________________"], ["Coach Sign", "Captain Sign"]], colWidths=[150, 150])
        sig_t.setStyle(TableStyle([('ALIGN', (0,0), (-1,-1), 'CENTER'), ('FONTSIZE', (0,0), (-1,-1), 8)]))
        slip_elements.append(sig_t)

        return slip_elements

    slip_A = create_team_slip(match_info['p1'], match_info['p2'], t1_players)
    slip_B = create_team_slip(match_info['p2'], match_info['p1'], t2_players)

    # दुईवटा स्लिपलाई एउटै ठूलो टेबलमा दायाँ-बायाँ (Side-by-Side) राख्ने
    master_table = Table([[slip_A, slip_B]], colWidths=[395, 395])
    master_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('INNERGRID', (0,0), (-1,-1), 1, colors.grey) # बीचको काट्ने लाइन (Cut Line)
    ]))
    elements.append(master_table)

    doc.build(elements)
    return buffer.getvalue()

# ==============================================================
# 🎯 ४. Field Events (Shot Put, Long Jump, High Jump)
# ==============================================================
def generate_field_scoresheet_pdf(event_info, participants_df, CONFIG):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), rightMargin=20, leftMargin=20, topMargin=15, bottomMargin=80)
    
    # 💡 साझा हेडर बोलाइएको
    elements = get_official_header(event_info, CONFIG, "OFFICIAL SCORE SHEET")
    
    headers = ['SN', 'Chest', 'Player Name & Municipality', 'Attempt 1', 'Attempt 2', 'Attempt 3', 'Best\nResult', 'Pos', 'Remark']
    data = [headers]
    name_style = ParagraphStyle('NameStyle', fontSize=10, leading=13)
    
    for i, row in participants_df.iterrows():
        clean_mun = re.sub(r'[\u0900-\u097F]+|\(\s*\)', '', str(row.get('municipality', ''))).strip()
        formatted_name = f"<b>{row['name']}</b><br/><font size=8 color='#444444'>({clean_mun})</font>"
        data.append([str(i+1), '', Paragraph(formatted_name, name_style), '', '', '', '', '', ''])
        for _ in range(3): data.append([''] * 9)

    t = Table(data, colWidths=[30, 40, 240, 85, 85, 85, 75, 40, 122])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.lightgrey), ('GRID', (0,0), (-1,-1), 0.5, colors.black),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('ALIGN', (0,0), (-1,-1), 'CENTER'), ('ALIGN', (2,1), (2,-1), 'LEFT'), 
    ]))
    elements.append(t)
    
    doc.build(elements, onFirstPage=add_official_footer, onLaterPages=add_official_footer)
    return buffer.getvalue()


def generate_high_jump_scoresheet_pdf(event_info, participants_df, CONFIG):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), rightMargin=20, leftMargin=20, topMargin=15, bottomMargin=80)
    
    # 💡 साझा हेडर बोलाइएको
    elements = get_official_header(event_info, CONFIG, "OFFICIAL HIGH JUMP SCORE SHEET")
    
    header_row1 = ['SN', 'Chest', 'Player Name & Municipality'] + ['Height 1', 'Height 2', 'Height 3', 'Height 4', 'Height 5', 'Height 6', 'Height 7', 'Height 8'] + ['Best\nResult', 'Total\nFails', 'Pos', 'Remark']
    header_row2 = ['', '', ''] + ['........'] * 8 + ['', '', '', '']
    
    data = [header_row1, header_row2]
    name_style = ParagraphStyle('NameStyle', fontSize=10, leading=13)
    
    for i, row in participants_df.iterrows():
        clean_mun = re.sub(r'[\u0900-\u097F]+|\(\s*\)', '', str(row.get('municipality', ''))).strip()
        formatted_name = f"<b>{row['name']}</b><br/><font size=8 color='#444444'>({clean_mun})</font>"
        data.append([str(i+1), '', Paragraph(formatted_name, name_style)] + [''] * 8 + ['', '', '', ''])
        for _ in range(2): data.append([''] * 15)

    t = Table(data, colWidths=[25, 35, 200] + [42] * 8 + [45, 45, 30, 50])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,1), colors.lightgrey), ('GRID', (0,0), (-1,-1), 0.5, colors.black),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('ALIGN', (0,0), (-1,-1), 'CENTER'), ('ALIGN', (2,2), (2,-1), 'LEFT'), 
        ('SPAN', (0,0), (0,1)), ('SPAN', (1,0), (1,1)), ('SPAN', (2,0), (2,1)), 
        ('SPAN', (-4,0), (-4,1)), ('SPAN', (-3,0), (-3,1)), ('SPAN', (-2,0), (-2,1)), ('SPAN', (-1,0), (-1,1)), 
    ]))
    elements.append(t)
    
    doc.build(elements, onFirstPage=add_official_footer, onLaterPages=add_official_footer)
    return buffer.getvalue()


# ==============================================================
# 🥋 ५. Martial Arts (Kata, Poomsae, Taolu)
# ==============================================================
def generate_judge_score_sheet(event_name, round_name, bouts, event_type, CONFIG):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), rightMargin=20, leftMargin=20, topMargin=20, bottomMargin=60)
    styles = getSampleStyleSheet()
    
    # 💡 साझा हेडर बोलाइएको (यसमा event_info को सट्टा सिधै नाम पठाइएको छ)
    elements = get_official_header({'name': event_name, 'gender': 'Round: ' + round_name}, CONFIG, "OFFICIAL JUDGE SCORE/VOTING SHEET")
    elements.append(Spacer(1, 10))
    
    def get_clean_name(p_str):
        if not p_str or p_str in ["TBD", "BYE"]: return p_str
        m = re.search(r"^(.*?)\s*\((.*?)\)", p_str)
        return f"<b>{m.group(1)}</b>\n<font size=8>({m.group(2)})</font>" if m else p_str.split(" [ID:")[0]

    if "Kata" in event_type:
        headers = ['Bout', 'Color', 'Player & Municipality', 'Tech\n(70%)', 'Athl\n(30%)', 'J1', 'J2', 'J3', 'J4', 'J5', 'Final Vote']
        col_widths = [40, 50, 180, 50, 50, 40, 40, 40, 40, 40, 70]
    elif "Poomsae" in event_type:
        headers = ['Bout', 'Color', 'Player & Municipality', 'Acc\n(4.0)', 'Pres\n(6.0)', 'J1', 'J2', 'J3', 'J4', 'J5', 'Total']
        col_widths = [40, 50, 180, 50, 50, 40, 40, 40, 40, 40, 70]
    else: 
        headers = ['Bout', 'Color', 'Player & Municipality', 'Tech\n(5.0)', 'Pres\n(5.0)', 'Ded\n(-)', 'J1', 'J2', 'J3', 'Total']
        col_widths = [40, 50, 190, 50, 50, 50, 45, 45, 45, 60]

    data = [headers]
    for b in bouts:
        if b['p1'] in ["TBD", "BYE"] and b['p2'] in ["TBD", "BYE"]: continue
        
        p1_name = Paragraph(get_clean_name(b['p1']), styles['Normal'])
        p2_name = Paragraph(get_clean_name(b['p2']), styles['Normal'])
        
        c1 = "AKA(Red)" if "Kata" in event_type else "Chung(Blue)" if "Poomsae" in event_type else "Black"
        c2 = "AO(Blue)" if "Kata" in event_type else "Hong(Red)" if "Poomsae" in event_type else "Red"
        
        data.extend([[str(b['id']), c1, p1_name] + [''] * (len(headers) - 3), ['', c2, p2_name] + [''] * (len(headers) - 3)])
        
    t = Table(data, colWidths=col_widths)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.lightgrey), ('GRID', (0,0), (-1,-1), 0.5, colors.black),
        ('FONTSIZE', (0,0), (-1,-1), 9), ('ALIGN', (0,0), (-1,-1), 'CENTER'), ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6), ('TOPPADDING', (0,0), (-1,-1), 6),
    ]))
    elements.append(t)

    doc.build(elements, onFirstPage=add_official_footer, onLaterPages=add_official_footer)
    return buffer.getvalue()


