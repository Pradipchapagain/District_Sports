import pandas as pd
import io
from io import BytesIO
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from datetime import datetime
import re

# ==========================================
# 🏃 Track & Field PDF Generators
# ==========================================
def generate_heat_sheet_pdf(event_info, heats_df, CONFIG):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=20, leftMargin=20, topMargin=15, bottomMargin=80)
    elements = []
    styles = getSampleStyleSheet()
    
    evt_name_en = event_info['name']
    gender_en = event_info['gender']
    category_en = event_info['category']
    sub_category_en = event_info['sub_category']
    event_group_en = event_info['event_group']
    
    org_style = ParagraphStyle('Org', parent=styles['Title'], alignment=TA_CENTER, fontSize=15, spaceAfter=2)
    event_title_style = ParagraphStyle('EventTitle', parent=styles['Title'], alignment=TA_CENTER, fontSize=13, spaceAfter=8, textColor=colors.darkblue)
    info_style = ParagraphStyle('Info', parent=styles['Normal'], alignment=TA_CENTER, fontSize=10, spaceAfter=4) 
    doc_title_style = ParagraphStyle('DocTitle', parent=styles['Normal'], alignment=TA_CENTER, fontSize=12, spaceAfter=10)
    event_left_style = ParagraphStyle('EventLeft', parent=styles['Normal'], alignment=TA_LEFT, fontSize=11, spaceAfter=5)
    
    organizer = CONFIG.get('ORGANIZER_NAME_EN', 'District Sports Development Committee')
    elements.append(Paragraph(f"<b>{organizer.upper()}</b>", org_style))
    elements.append(Paragraph(f"<b>{CONFIG.get('EVENT_TITLE_EN', 'President Running Shield')}</b>", event_title_style))
    
    cat_text = f"<b>Category:</b> {category_en} &nbsp; | &nbsp; <b>Sub-Category:</b> {sub_category_en} &nbsp; | &nbsp; <b>Group:</b> {event_group_en}"
    elements.append(Paragraph(cat_text, info_style))
    elements.append(Paragraph("<b><u>START LIST / SCORE SHEET</u></b>", doc_title_style))
    elements.append(Paragraph(f"<b>Event: {evt_name_en.upper()} - ({gender_en})</b>", event_left_style))
    
    name_style = ParagraphStyle('NameStyle', fontSize=10, leading=13)
    header_style = ParagraphStyle('Hdr', fontSize=10, fontName='Helvetica-Bold', alignment=TA_CENTER)
    
    unique_heats = sorted(heats_df['heat'].unique())
    for h in unique_heats:
        # 💡 १. यो फाइनल हो कि हिट्स हो भनेर चेक गर्ने
        is_final = str(h).upper() == "FINAL"
        title_text = "FINAL ROUND" if is_final else f"HEAT {h}"
        elements.append(Paragraph(f"<b>{title_text}</b>", styles['Heading3']))
        elements.append(Spacer(1, 5))
        
        # 💡 २. जादु यहाँ छ: फाइनल हो भने 'Medal', होइन भने 'Q (Y/N)' राख्ने
        if is_final:
            headers = [Paragraph('Lane', header_style), Paragraph('Chest', header_style), 
                       Paragraph('Player Name & Municipality', header_style), 
                       Paragraph('Time', header_style), Paragraph('Rank', header_style), 
                       Paragraph('Medal', header_style), Paragraph('Remark', header_style)]
        else:
            headers = [Paragraph('Lane', header_style), Paragraph('Chest', header_style), 
                       Paragraph('Player Name & Municipality', header_style), 
                       Paragraph('Time', header_style), Paragraph('Rank', header_style), 
                       Paragraph('Q (Y/N)', header_style), Paragraph('Remark', header_style)]
                       
        cw = [35, 40, 220, 70, 45, 60, 85] 
            
        table_data = [headers]
        heat_rows = heats_df[heats_df['heat'] == h].sort_values(by='lane')
        
        for _, row in heat_rows.iterrows():
            raw_mun = str(row.get('municipality', ''))
            clean_mun = re.sub(r'[\u0900-\u097F]+', '', raw_mun) 
            clean_mun = re.sub(r'\(\s*\)', '', clean_mun).strip()
            formatted_name = f"<b>{row['name']}</b><br/><font size=8 color='#444444'>({clean_mun})</font>"
            table_data.append([str(row['lane']), '', Paragraph(formatted_name, name_style), '', '', '', ''])
            
        t = Table(table_data, colWidths=cw)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
            ('GRID', (0,0), (-1,-1), 0.5, colors.black),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('ALIGN', (0,0), (1,-1), 'CENTER'),
            ('ALIGN', (2,1), (2,-1), 'LEFT'),
            ('TOPPADDING', (0,0), (-1,-1), 4),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 15))

    def add_footer(canvas, doc):
        canvas.saveState()
        page_width = A4[0]
        canvas.setFont('Helvetica-Bold', 10)
        canvas.drawCentredString(page_width * 0.2, 40, "Recorded By")
        canvas.drawCentredString(page_width * 0.5, 40, "Starter / Umpire")
        canvas.drawCentredString(page_width * 0.8, 40, "Chief Judge")
        canvas.setFont('Helvetica', 10)
        canvas.drawCentredString(page_width * 0.2, 55, "___________________")
        canvas.drawCentredString(page_width * 0.5, 55, "___________________")
        canvas.drawCentredString(page_width * 0.8, 55, "___________________")
        canvas.setFont('Helvetica-Oblique', 8)
        canvas.setFillColor(colors.dimgrey)
        footer_text = f"System generated start list | Printed on: {datetime.now().strftime('%Y-%m-%d %I:%M %p')}"
        canvas.drawCentredString(page_width / 2.0, 15, footer_text)
        canvas.restoreState()

    doc.build(elements, onFirstPage=add_footer, onLaterPages=add_footer)
    buffer.seek(0)
    return buffer

def generate_relay_heat_sheet_pdf(event_info, heats_df, CONFIG):
    """रिले दौडको हिट्स र फाइनलको लागि विशेष स्टार्ट लिस्ट (खाली कोठा र OK/DNF कोलम सहित)"""
    from io import BytesIO
    import re
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from datetime import datetime

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=20, leftMargin=20, topMargin=15, bottomMargin=80)
    elements = []
    styles = getSampleStyleSheet()
    
    evt_name_en = event_info['name']
    gender_en = event_info['gender']
    category_en = event_info['category']
    sub_category_en = event_info['sub_category']
    event_group_en = event_info['event_group']
    
    # --- हेडर डिजाइन ---
    org_style = ParagraphStyle('Org', parent=styles['Title'], alignment=TA_CENTER, fontSize=15, spaceAfter=2)
    event_title_style = ParagraphStyle('EventTitle', parent=styles['Title'], alignment=TA_CENTER, fontSize=13, spaceAfter=8, textColor=colors.darkblue)
    info_style = ParagraphStyle('Info', parent=styles['Normal'], alignment=TA_CENTER, fontSize=10, spaceAfter=4) 
    doc_title_style = ParagraphStyle('DocTitle', parent=styles['Normal'], alignment=TA_CENTER, fontSize=12, spaceAfter=10)
    event_left_style = ParagraphStyle('EventLeft', parent=styles['Normal'], alignment=TA_LEFT, fontSize=11, spaceAfter=5)
    
    organizer = CONFIG.get('ORGANIZER_NAME_EN', 'District Sports Development Committee')
    elements.append(Paragraph(f"<b>{organizer.upper()}</b>", org_style))
    elements.append(Paragraph(f"<b>{CONFIG.get('EVENT_TITLE_EN', 'President Running Shield')}</b>", event_title_style))
    
    cat_text = f"<b>Category:</b> {category_en} &nbsp; | &nbsp; <b>Sub-Category:</b> {sub_category_en} &nbsp; | &nbsp; <b>Group:</b> {event_group_en}"
    elements.append(Paragraph(cat_text, info_style))
    elements.append(Paragraph("<b><u>RELAY START LIST / SCORE SHEET</u></b>", doc_title_style))
    elements.append(Paragraph(f"<b>Event: {evt_name_en.upper()} - ({gender_en})</b>", event_left_style))
    
    name_style = ParagraphStyle('NameStyle', fontSize=10, leading=14) 
    header_style = ParagraphStyle('Hdr', fontSize=9, fontName='Helvetica-Bold', alignment=TA_CENTER)
    
    # --- हिट्स (Heats) अनुसार लुप चलाउने ---
    unique_heats = sorted(heats_df['heat'].unique())
    for h in unique_heats:
        is_final = str(h).upper() == "FINAL"
        title_text = "FINAL ROUND" if is_final else f"HEAT {h}"
        elements.append(Paragraph(f"<b>{title_text}</b>", styles['Heading3']))
        elements.append(Spacer(1, 5))
        
        # 💡 Lane को चौडाइ ३० बाट बढाएर ४० बनाइएको छ ताकि 'Lane' एउटै लाइनमा अटाओस्
        # 💡 बाहिरी टेबलको जम्मा चौडाइ ५४० पोइन्ट
        if is_final:
            headers = [Paragraph('Lane', header_style), Paragraph('Municipality & Squad', header_style), 
                       Paragraph('Time', header_style), Paragraph('Rank', header_style), 
                       Paragraph('Medal', header_style), Paragraph('Remark', header_style)]
            cw = [40, 240, 60, 50, 60, 90] 
        else:
            headers = [Paragraph('Lane', header_style), Paragraph('Municipality & Squad', header_style), 
                       Paragraph('Time', header_style), Paragraph('Rank', header_style), 
                       Paragraph('Q (Y/N)', header_style), Paragraph('Remark', header_style)]
            cw = [40, 240, 60, 50, 60, 90]
            
        table_data = [headers]
        heat_rows = heats_df[heats_df['heat'] == h].sort_values(by='lane')
        
        for _, row in heat_rows.iterrows():
            raw_mun = str(row.get('name', str(row.get('municipality', ''))))
            clean_mun = re.sub(r'[\u0900-\u097F]+', '', raw_mun) 
            clean_mun = re.sub(r'\(\s*\)', '', clean_mun).strip().upper()
            
            players_str = str(row.get('players_list', ''))
            players_list = [p.strip() for p in re.split(r'[,|]', players_str) if p.strip()]
            
            # 💡 ग) भित्री चाइल्ड टेबल बनाउने (४ वटा कोलम)
            inner_data = []
            inner_data.append([
                Paragraph("<font size=7 color='#444444'><b>Leg</b></font>", styles['Normal']),
                Paragraph("<font size=7 color='#444444'><b>Player Name</b></font>", styles['Normal']),
                Paragraph("<font size=7 color='#444444'><b>OK</b></font>", styles['Normal']),
                Paragraph("<font size=7 color='#444444'><b>DNF</b></font>", styles['Normal'])
            ])
            
            for p in players_list:
                p_name = Paragraph(f"<font size=8>{p}</font>", styles['Normal'])
                
                # 💡 OK र DNF लाई छुट्टाछुट्टै कोठामा Left Align गरेर राखिएको छ
                # यसले गर्दा दाहिनेपट्टि 'टिक' लगाउने टन्नै खाली ठाउँ बच्छ
                ok_txt = Paragraph("<font size=7 color='#333333'>OK</font>", styles['Normal'])
                dnf_txt = Paragraph("<font size=7 color='#333333'>DNF</font>", styles['Normal'])
                
                # पहिलो कोठा (Leg) खाली छोडिएको छ, जसले गर्दा एउटा बक्स बन्छ
                inner_data.append(["", p_name, ok_txt, dnf_txt])
                
            # भित्री टेबलको सेटिङ (कुल चौडाइ २४०)
            inner_table = Table(inner_data, colWidths=[25, 135, 40, 40])
            inner_table.setStyle(TableStyle([
                ('GRID', (0,0), (-1,-1), 0.25, colors.grey), # मधुरो ग्रिड लाइन
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('ALIGN', (0,0), (0,-1), 'CENTER'), # Leg को हेडरलाई सेन्टर
                ('ALIGN', (1,0), (3,-1), 'LEFT'),   # Name, OK, DNF सबै Left Align
                ('TOPPADDING', (0,0), (-1,-1), 3),
                ('BOTTOMPADDING', (0,0), (-1,-1), 3),
            ]))
            
            cell_content = [
                Paragraph(f"<b>{clean_mun}</b>", name_style),
                Spacer(1, 3),
                inner_table
            ]
            
            table_data.append([str(row['lane']), cell_content, '', '', '', ''])
            
        t = Table(table_data, colWidths=cw)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
            ('GRID', (0,0), (-1,-1), 0.5, colors.black),
            ('VALIGN', (0,0), (-1,-1), 'TOP'), 
            ('ALIGN', (0,0), (0,-1), 'CENTER'), 
            ('ALIGN', (1,0), (1,-1), 'LEFT'),   
            ('ALIGN', (2,0), (-1,-1), 'CENTER'),
            ('TOPPADDING', (0,0), (-1,-1), 6),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 15))

    # --- फुटर ---
    def add_footer(canvas, doc):
        canvas.saveState()
        page_width = A4[0] 
        
        canvas.setFont('Helvetica-Bold', 10)
        canvas.drawCentredString(page_width * 0.2, 40, "Starter")
        canvas.drawCentredString(page_width * 0.5, 40, "Track Referee")
        canvas.drawCentredString(page_width * 0.8, 40, "Chief Timekeeper")
        
        canvas.setFont('Helvetica', 10)
        canvas.drawCentredString(page_width * 0.2, 55, "____________________")
        canvas.drawCentredString(page_width * 0.5, 55, "____________________")
        canvas.drawCentredString(page_width * 0.8, 55, "____________________")
        
        canvas.setFont('Helvetica-Oblique', 8)
        canvas.setFillColor(colors.dimgrey)
        current_time = datetime.now().strftime("%Y-%m-%d %I:%M %p")
        canvas.drawCentredString(page_width / 2.0, 15, f"System generated relay sheet | Printed on: {current_time}")
        canvas.restoreState()

    doc.build(elements, onFirstPage=add_footer, onLaterPages=add_footer)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes

from io import BytesIO
import re
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from datetime import datetime

def generate_lap_sheet_pdf(event_info, participants_df, CONFIG):
    """लामो दूरीको दौडको लागि प्रोफेसनल ल्याप सिट जेनेरेटर"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), rightMargin=20, leftMargin=20, topMargin=15, bottomMargin=80)
    elements = []
    styles = getSampleStyleSheet()

    evt_name_en = event_info.get('name', '')
    gender_en = event_info.get('gender', '')
    category_en = event_info.get('category', '')
    sub_category_en = event_info.get('sub_category', '') 
    event_group_en = event_info.get('event_group', '')

    org_style = ParagraphStyle('Org', parent=styles['Title'], alignment=TA_CENTER, fontSize=15, spaceAfter=2)
    event_title_style = ParagraphStyle('EventTitle', parent=styles['Title'], alignment=TA_CENTER, fontSize=13, spaceAfter=8, textColor=colors.darkblue)
    info_style = ParagraphStyle('Info', parent=styles['Normal'], alignment=TA_CENTER, fontSize=10, spaceAfter=4)
    lap_sheet_title_style = ParagraphStyle('LapTitle', parent=styles['Normal'], alignment=TA_CENTER, fontSize=12, spaceAfter=10)
    event_left_style = ParagraphStyle('EventLeft', parent=styles['Normal'], alignment=TA_LEFT, fontSize=11, spaceAfter=5)

    organizer = CONFIG.get('ORGANIZER_NAME_EN', 'District Sports Development Committee, Ilam')
    elements.append(Paragraph(f"<b>{organizer.upper()}</b>", org_style))
    elements.append(Paragraph(f"<b>{CONFIG.get('EVENT_TITLE_EN', 'PRESIDENT RUNNING SHIELD')}</b>", event_title_style))

    cat_text = f"<b>Category:</b> {category_en} &nbsp; | &nbsp; <b>Sub Category:</b> {sub_category_en} &nbsp; | &nbsp; <b>Group:</b> {event_group_en}"
    elements.append(Paragraph(cat_text, info_style))
    elements.append(Paragraph("<b><u>OFFICIAL LAP SHEET</u></b>", lap_sheet_title_style))
    elements.append(Paragraph(f"<b>Event: {evt_name_en.upper()} - ({gender_en})</b>", event_left_style))
    elements.append(Spacer(1, 5))

    total_laps = 15 if "3000" in evt_name_en else 7 if "1500" in evt_name_en else 4 if "800" in evt_name_en else 1
    header_style = ParagraphStyle('Hdr', fontSize=9, fontName='Helvetica-Bold', alignment=TA_CENTER)
    name_style = ParagraphStyle('NameStyle', fontSize=10, leading=13)

    headers = [Paragraph('SN', header_style), Paragraph('Chest', header_style), Paragraph('Player Name & Municipality', header_style)]
    for i in range(total_laps, 0, -1): 
        headers.append(Paragraph(f'L{i}', header_style))
    headers.append(Paragraph('Time/Finish', header_style))

    table_data = [headers]
    for idx, row in participants_df.iterrows():
        raw_mun = str(row.get('municipality', row.get('school', '')))
        clean_mun = re.sub(r'[\u0900-\u097F]+', '', raw_mun) 
        clean_mun = re.sub(r'\(\s*\)', '', clean_mun).strip()
        formatted_name = f"<b>{row['name']}</b><br/><font size=8 color='#444444'>({clean_mun})</font>"
        
        row_data = [str(idx + 1), '', Paragraph(formatted_name, name_style)] + [''] * total_laps + ['']
        table_data.append(row_data)

    lap_width = 450 / max(1, total_laps)
    col_widths = [30, 40, 220] + [lap_width] * total_laps + [60]

    t = Table(table_data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
        ('GRID', (0,0), (-1,-1), 0.5, colors.black),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ALIGN', (0,0), (1,-1), 'CENTER'), 
        ('ALIGN', (2,0), (2,-1), 'LEFT'),  
        ('ALIGN', (3,0), (-1,-1), 'CENTER'),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    elements.append(t)

    def add_footer(canvas, doc):
        canvas.saveState()
        page_width = landscape(A4)[0]
        canvas.setFont('Helvetica-Bold', 10)
        canvas.drawCentredString(page_width * 0.2, 40, "Lap Scorer")
        canvas.drawCentredString(page_width * 0.5, 40, "Umpire / Judge")
        canvas.drawCentredString(page_width * 0.8, 40, "Chief Referee")
        canvas.setFont('Helvetica', 10)
        canvas.drawCentredString(page_width * 0.2, 55, "_________________________")
        canvas.drawCentredString(page_width * 0.5, 55, "_________________________")
        canvas.drawCentredString(page_width * 0.8, 55, "_________________________")
        canvas.setFont('Helvetica-Oblique', 8)
        canvas.setFillColor(colors.dimgrey)
        current_time = datetime.now().strftime("%Y-%m-%d %I:%M %p")
        canvas.drawCentredString(page_width / 2.0, 15, f"System generated lap sheet | Printed on: {current_time}")
        canvas.restoreState()

    doc.build(elements, onFirstPage=add_footer, onLaterPages=add_footer)
    
    # 💡 जादु यहाँ छ: यसले Streamlit लाई चाहिने 'Bytes' फर्काउँछ
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


def generate_field_scoresheet_pdf(event_info, participants_df, CONFIG):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), rightMargin=20, leftMargin=20, topMargin=15, bottomMargin=80)
    elements = []
    styles = getSampleStyleSheet()
    
    evt_name_en = event_info['name']
    gender_en = event_info['gender']
    category_en = event_info['category']
    sub_category_en = event_info['sub_category']
    event_group_en = event_info['event_group']
    
    org_style = ParagraphStyle('Org', parent=styles['Title'], alignment=TA_CENTER, fontSize=15, spaceAfter=2)
    event_title_style = ParagraphStyle('EventTitle', parent=styles['Title'], alignment=TA_CENTER, fontSize=13, spaceAfter=8, textColor=colors.darkblue)
    info_style = ParagraphStyle('Info', parent=styles['Normal'], alignment=TA_CENTER, fontSize=10, spaceAfter=10)
    event_left_style = ParagraphStyle('EventLeft', parent=styles['Normal'], alignment=TA_LEFT, fontSize=11, spaceAfter=5)
    
    organizer = CONFIG.get('ORGANIZER_NAME_EN', 'District Sports Development Committee, Ilam')
    elements.append(Paragraph(f"<b>{organizer.upper()}</b>", org_style))
    elements.append(Paragraph(f"<b>{CONFIG['EVENT_TITLE_EN']}</b>", event_title_style))
    
    info_text = f"<b>SCORE SHEET</b> &nbsp; | &nbsp; <b>Category:</b> {category_en} &nbsp; | &nbsp; <b>Sub-Category:</b> {sub_category_en} &nbsp; | &nbsp; <b>Group:</b> {event_group_en}"
    elements.append(Paragraph(info_text, info_style))
    elements.append(Paragraph(f"<b>Event: {evt_name_en.upper()} - ({gender_en})</b>", event_left_style))
    
    headers = ['SN', 'Chest', 'Player Name & Municipality', 'Attempt 1', 'Attempt 2', 'Attempt 3', 'Best\nResult', 'Pos', 'Remark']
    data = [headers]
    name_style = ParagraphStyle('NameStyle', fontSize=10, leading=13)
    
    for i, row in participants_df.iterrows():
        raw_mun = str(row.get('municipality', ''))
        clean_mun = re.sub(r'[\u0900-\u097F]+', '', raw_mun) 
        clean_mun = re.sub(r'\(\s*\)', '', clean_mun).strip()
        formatted_name = f"<b>{row['name']}</b><br/><font size=8 color='#444444'>({clean_mun})</font>"
        data.append([str(i+1), '', Paragraph(formatted_name, name_style), '', '', '', '', '', ''])
        
    for _ in range(3): 
        data.append([''] * 9)

    cw = [30, 40, 240, 85, 85, 85, 75, 40, 122]
    t = Table(data, colWidths=cw)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.lightgrey), 
        ('GRID', (0,0), (-1,-1), 0.5, colors.black),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'), 
        ('ALIGN', (0,0), (-1,-1), 'CENTER'), 
        ('ALIGN', (2,1), (2,-1), 'LEFT'), 
    ]))
    elements.append(t)
    
    def add_footer(canvas, doc):
        canvas.saveState()
        page_width = landscape(A4)[0]
        canvas.setFont('Helvetica-Bold', 10)
        canvas.drawCentredString(page_width * 0.2, 40, "Recorded By")
        canvas.drawCentredString(page_width * 0.5, 40, "Head Referee")
        canvas.drawCentredString(page_width * 0.8, 40, "Chief Judge")
        canvas.setFont('Helvetica', 10)
        canvas.drawCentredString(page_width * 0.2, 55, "_________________________")
        canvas.drawCentredString(page_width * 0.5, 55, "_________________________")
        canvas.drawCentredString(page_width * 0.8, 55, "_________________________")
        canvas.setFont('Helvetica-Oblique', 8)
        canvas.setFillColor(colors.dimgrey)
        current_time = datetime.now().strftime("%Y-%m-%d %I:%M %p")
        canvas.drawCentredString(page_width / 2.0, 15, f"System generated score sheet | Printed on: {current_time}")
        canvas.restoreState()

    doc.build(elements, onFirstPage=add_footer, onLaterPages=add_footer)
    
    # 💡 जादु यहाँ छ
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


def generate_high_jump_scoresheet_pdf(event_info, participants_df, CONFIG):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), rightMargin=20, leftMargin=20, topMargin=15, bottomMargin=80)
    elements = []
    styles = getSampleStyleSheet()
    
    evt_name_en = event_info['name']
    gender_en = event_info['gender']
    category_en = event_info['category']
    sub_category_en = event_info['sub_category']
    event_group_en = event_info['event_group']
    
    org_style = ParagraphStyle('Org', parent=styles['Title'], alignment=TA_CENTER, fontSize=15, spaceAfter=2)
    event_title_style = ParagraphStyle('EventTitle', parent=styles['Title'], alignment=TA_CENTER, fontSize=13, spaceAfter=8, textColor=colors.darkblue)
    info_style = ParagraphStyle('Info', parent=styles['Normal'], alignment=TA_CENTER, fontSize=10, spaceAfter=10)
    event_left_style = ParagraphStyle('EventLeft', parent=styles['Normal'], alignment=TA_LEFT, fontSize=11, spaceAfter=5)
    
    organizer = CONFIG.get('ORGANIZER_NAME_EN', 'District Sports Development Committee, Ilam')
    elements.append(Paragraph(f"<b>{organizer.upper()}</b>", org_style))
    elements.append(Paragraph(f"<b>{CONFIG['EVENT_TITLE_EN']}</b>", event_title_style))
    
    info_text = f"<b>SCORE SHEET</b> &nbsp; | &nbsp; <b>Category:</b> {category_en} &nbsp; | &nbsp; <b>Sub-Category:</b> {sub_category_en} &nbsp; | &nbsp; <b>Group:</b> {event_group_en}"
    elements.append(Paragraph(info_text, info_style))
    elements.append(Paragraph(f"<b>Event: {evt_name_en.upper()} - ({gender_en})</b>", event_left_style))
    
    header_row1 = ['SN', 'Chest', 'Player Name & Municipality'] + ['Height 1', 'Height 2', 'Height 3', 'Height 4', 'Height 5', 'Height 6', 'Height 7', 'Height 8'] + ['Best\nResult', 'Total\nFails', 'Pos', 'Remark']
    header_row2 = ['', '', ''] + ['........'] * 8 + ['', '', '', '']
    
    data = [header_row1, header_row2]
    name_style = ParagraphStyle('NameStyle', fontSize=10, leading=13)
    
    for i, row in participants_df.iterrows():
        raw_mun = str(row.get('municipality', ''))
        clean_mun = re.sub(r'[\u0900-\u097F]+', '', raw_mun) 
        clean_mun = re.sub(r'\(\s*\)', '', clean_mun).strip()
        formatted_name = f"<b>{row['name']}</b><br/><font size=8 color='#444444'>({clean_mun})</font>"
        data.append([str(i+1), '', Paragraph(formatted_name, name_style)] + [''] * 8 + ['', '', '', ''])
        
    for _ in range(2): 
        data.append([''] * 15)

    cw = [25, 35, 200] + [42] * 8 + [45, 45, 30, 50]
    t = Table(data, colWidths=cw)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,1), colors.lightgrey), ('GRID', (0,0), (-1,-1), 0.5, colors.black),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('ALIGN', (0,0), (-1,-1), 'CENTER'), ('ALIGN', (2,2), (2,-1), 'LEFT'), 
        ('SPAN', (0,0), (0,1)), ('SPAN', (1,0), (1,1)), ('SPAN', (2,0), (2,1)), 
        ('SPAN', (-4,0), (-4,1)), ('SPAN', (-3,0), (-3,1)), ('SPAN', (-2,0), (-2,1)), ('SPAN', (-1,0), (-1,1)), 
    ]))
    elements.append(t)
    
    def add_footer(canvas, doc):
        canvas.saveState()
        page_width = landscape(A4)[0]
        canvas.setFont('Helvetica-Bold', 10)
        canvas.drawCentredString(page_width * 0.2, 40, "Recorded By")
        canvas.drawCentredString(page_width * 0.5, 40, "Head Referee")
        canvas.drawCentredString(page_width * 0.8, 40, "Chief Judge")
        canvas.setFont('Helvetica', 10)
        canvas.drawCentredString(page_width * 0.2, 55, "_________________________")
        canvas.drawCentredString(page_width * 0.5, 55, "_________________________")
        canvas.drawCentredString(page_width * 0.8, 55, "_________________________")
        canvas.setFont('Helvetica-Oblique', 8)
        canvas.setFillColor(colors.dimgrey)
        current_time = datetime.now().strftime("%Y-%m-%d %I:%M %p")
        canvas.drawCentredString(page_width / 2.0, 15, f"System generated score sheet | Printed on: {current_time}")
        canvas.restoreState()

    doc.build(elements, onFirstPage=add_footer, onLaterPages=add_footer)
    
    # 💡 जादु यहाँ छ
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes

# ==========================================
# 🥋 Martial Arts PDF Generators (NEW)
# ==========================================
def generate_judge_score_sheet(event_name, round_name, bouts, event_type, CONFIG):
    """मार्सल आर्ट्स (Kata, Poomsae, Taolu) को लागि डाइनामिक जज स्कोर सिट"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), rightMargin=20, leftMargin=20, topMargin=20, bottomMargin=60)
    elements = []
    styles = getSampleStyleSheet()
    
    org_style = ParagraphStyle('Org', parent=styles['Title'], alignment=TA_CENTER, fontSize=15, spaceAfter=2)
    event_title_style = ParagraphStyle('EventTitle', parent=styles['Title'], alignment=TA_CENTER, fontSize=13, spaceAfter=8, textColor=colors.darkblue)
    
    organizer = CONFIG.get('ORGANIZER_NAME_EN', 'District Sports Development Committee')
    elements.append(Paragraph(f"<b>{organizer.upper()}</b>", org_style))
    elements.append(Paragraph(f"<b>{CONFIG.get('EVENT_TITLE_EN', 'President Running Shield')}</b>", event_title_style))
    elements.append(Paragraph(f"<b>OFFICIAL JUDGE SCORE/VOTING SHEET</b>", styles['Heading3']))
    elements.append(Paragraph(f"<b>Event:</b> {event_name} &nbsp;&nbsp; | &nbsp;&nbsp; <b>Round:</b> {round_name}", styles['Normal']))
    elements.append(Spacer(1, 10))
    
    def get_clean_name(p_str):
        if not p_str or p_str in ["TBD", "BYE"]: return p_str
        m = re.search(r"^(.*?)\s*\((.*?)\)", p_str)
        return f"<b>{m.group(1)}</b>\n<font size=8>({m.group(2)})</font>" if m else p_str.split(" [ID:")[0]

    # विधा अनुसार कोलमहरू (Dynamic Headers)
    if "Kata" in event_type:
        headers = ['Bout', 'Color', 'Player & Municipality', 'Tech\n(70%)', 'Athl\n(30%)', 'J1', 'J2', 'J3', 'J4', 'J5', 'Final Vote']
        col_widths = [40, 50, 180, 50, 50, 40, 40, 40, 40, 40, 70]
    elif "Poomsae" in event_type:
        headers = ['Bout', 'Color', 'Player & Municipality', 'Acc\n(4.0)', 'Pres\n(6.0)', 'J1', 'J2', 'J3', 'J4', 'J5', 'Total']
        col_widths = [40, 50, 180, 50, 50, 40, 40, 40, 40, 40, 70]
    else: # Taolu
        headers = ['Bout', 'Color', 'Player & Municipality', 'Tech\n(5.0)', 'Pres\n(5.0)', 'Ded\n(-)', 'J1', 'J2', 'J3', 'Total']
        col_widths = [40, 50, 190, 50, 50, 50, 45, 45, 45, 60]

    data = [headers]
    for b in bouts:
        if b['p1'] in ["TBD", "BYE"] and b['p2'] in ["TBD", "BYE"]: continue
        
        p1_name = Paragraph(get_clean_name(b['p1']), styles['Normal'])
        p2_name = Paragraph(get_clean_name(b['p2']), styles['Normal'])
        
        c1 = "AKA(Red)" if "Kata" in event_type else "Chung(Blue)" if "Poomsae" in event_type else "Black"
        row1 = [str(b['id']), c1, p1_name] + [''] * (len(headers) - 3)
        
        c2 = "AO(Blue)" if "Kata" in event_type else "Hong(Red)" if "Poomsae" in event_type else "Red"
        row2 = ['', c2, p2_name] + [''] * (len(headers) - 3)
        
        data.extend([row1, row2])
        
    t = Table(data, colWidths=col_widths)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
        ('GRID', (0,0), (-1,-1), 0.5, colors.black),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 6),
    ]))
    elements.append(t)

    def add_footer(canvas, doc):
        canvas.saveState()
        page_width = landscape(A4)[0]
        canvas.setFont('Helvetica-Bold', 10)
        canvas.drawCentredString(page_width * 0.2, 40, "Recorded By")
        canvas.drawCentredString(page_width * 0.8, 40, "Chief Judge")
        canvas.setFont('Helvetica', 10)
        canvas.drawCentredString(page_width * 0.2, 55, "___________________")
        canvas.drawCentredString(page_width * 0.8, 55, "___________________")
        canvas.restoreState()

    doc.build(elements, onFirstPage=add_footer, onLaterPages=add_footer)
    buffer.seek(0)
    return buffer

# vollyball team slip
def generate_lineup_sheet_pdf(event_name):
    """भलिबल/टीम गेमको लागि अफिसियल लाइन-अप स्लिप (खाली फारम) जेनेरेट गर्ने"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    elements = []
    styles = getSampleStyleSheet()

    # एउटा A4 पानामा २ वटा स्लिप (Top र Bottom) अटाउने गरी लुप
    for i in range(2):
        # Header
        elements.append(Paragraph(f"<b>{event_name} - Official Line-up Sheet</b>", styles['Heading3']))
        elements.append(Spacer(1, 15))

        # Team & Match Info
        info_data = [
            ["Team Name:", "___________________________", "Match No:", "_______"],
            ["Opponent:", "___________________________", "Set No:", "_______"]
        ]
        t_info = Table(info_data, colWidths=[80, 200, 60, 100])
        t_info.setStyle(TableStyle([('FONT', (0,0), (-1,-1), 'Helvetica'), ('ALIGN', (0,0), (-1,-1), 'LEFT')]))
        elements.append(t_info)
        elements.append(Spacer(1, 20))

        # Starting 6 Positions Table
        start_data = [
            ["Starting Order", "I (1)", "II (2)", "III (3)", "IV (4)", "V (5)", "VI (6)"],
            ["Jersey No.", "", "", "", "", "", ""]
        ]
        t_start = Table(start_data, colWidths=[95, 50, 50, 50, 50, 50, 50])
        t_start.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 1, colors.black),
            ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 15),
            ('TOPPADDING', (0,0), (-1,-1), 15)
        ]))
        elements.append(t_start)
        elements.append(Spacer(1, 20))

        # Libero & Captain
        lib_cap_data = [
            ["Libero (Jersey No):", "___________, ___________", "Team Captain (No):", "___________"]
        ]
        t_lc = Table(lib_cap_data, colWidths=[120, 150, 120, 100])
        t_lc.setStyle(TableStyle([('FONT', (0,0), (-1,-1), 'Helvetica-Bold')]))
        elements.append(t_lc)
        elements.append(Spacer(1, 40))

        # Signatures
        sig_data = [
            ["______________________", "______________________"],
            ["Coach Signature", "Captain Signature"]
        ]
        t_sig = Table(sig_data, colWidths=[250, 250])
        t_sig.setStyle(TableStyle([('ALIGN', (0,0), (-1,-1), 'CENTER'), ('FONT', (0,0), (-1,-1), 'Helvetica')]))
        elements.append(t_sig)
        
        # पानाको बिचमा काट्ने धर्सो
        if i == 0:
            elements.append(Spacer(1, 50))
            elements.append(Paragraph("- - - - - - - - - - - - - - - - - - - - - - - - - -✂️ - - - - - - - - - - - - - - - - - - - - - - - - -", styles['Normal']))
            elements.append(Spacer(1, 50))

    doc.build(elements)
    buffer.seek(0)
    return buffer




# ==========================================
# 🎯 FIELD EVENTS (Shot Put, Long Jump, Javelin) Score Sheet
# ==========================================
def generate_field_scoresheet_pdf(current_event, p_df, config):
    buffer = io.BytesIO()
    # फिल्ड गेमको लागि A4 तेर्सो (Landscape) पाना ठीक हुन्छ
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    elements = []
    styles = getSampleStyleSheet()
    
    # हेडरको डिजाइन
    title_style = ParagraphStyle(name='TitleStyle', parent=styles['Heading1'], alignment=1, fontSize=16)
    sub_title_style = ParagraphStyle(name='SubTitleStyle', parent=styles['Heading2'], alignment=1, fontSize=12, textColor=colors.maroon)
    
    event_name = current_event.get('name', 'Field Event')
    gender = current_event.get('gender', '')
    
    elements.append(Paragraph(f"{config.get('EVENT_TITLE_NP', 'President Running Shield')}", title_style))
    elements.append(Spacer(1, 5))
    elements.append(Paragraph(f"Official Field Score Sheet - {event_name} ({gender})", sub_title_style))
    elements.append(Spacer(1, 15))
    
    # टेबलको हेडर (Columns)
    data = [['SN', 'Player ID', 'Player Name', 'Municipality', 'Attempt 1', 'Attempt 2', 'Attempt 3', 'Best Score', 'Rank']]
    
    # खेलाडीहरूको डाटा भर्ने (अटेम्प्टहरू खाली राख्ने ताकि हातले लेख्न मिलोस्)
    for idx, row in p_df.iterrows():
        data.append([
            str(idx + 1),
            str(row.get('id', '')),
            str(row.get('name', '')),
            str(row.get('municipality', '')),
            '', '', '', '', ''
        ])
        
    # टेबलको डिजाइन र साइज मिलाउने
    t = Table(data, colWidths=[30, 60, 160, 160, 80, 80, 80, 80, 50])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
        ('TEXTCOLOR', (0,0), (-1,0), colors.black),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0,0), (-1,0), 12),
        ('GRID', (0,0), (-1,-1), 1, colors.black),
        ('FONTSIZE', (0,0), (-1,-1), 10),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        # नाम र पालिकालाई बायाँ फर्काउने
        ('ALIGN', (2,1), (3,-1), 'LEFT'),
    ]))
    
    elements.append(t)
    doc.build(elements)
    
    buffer.seek(0)
    return buffer.getvalue()

