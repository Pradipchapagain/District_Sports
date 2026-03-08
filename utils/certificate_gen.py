import pandas as pd
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os
from config import CONFIG

def generate_certificate_pdf(event_name, winners_df, language='np'):
    """
    विजेताहरूको लागि प्रमाणपत्र PDF जनरेट गर्दछ।
    winners_df मा 'name', 'school_name', र 'rank' कलम हुनुपर्छ।
    """
    if winners_df is None or winners_df.empty:
        return None

    # फन्ट सेटअप (नेपाली युनिकोडको लागि)
    font_path = 'fonts/ArialUnicodeMS.ttf' # यो फन्ट तपाईंको फोल्डरमा हुनुपर्छ
    try:
        if os.path.exists(font_path):
            pdfmetrics.registerFont(TTFont('ArialUnicodeMS', font_path))
            default_font = 'ArialUnicodeMS'
        else:
            default_font = 'Helvetica' # फलब्याक
    except:
        default_font = 'Helvetica'

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=landscape(A4))
    width, height = landscape(A4)

    # भाषा अनुसारको टेक्स्ट
    if language == 'np':
        header_text = f"१६औं {CONFIG.get('EVENT_TITLE_NP', 'राष्ट्रपति रनिङ शिल्ड')} २०८२"
        title_text = "प्रमाणपत्र"
        presented_text = "यो प्रमाणपत्र गर्वका साथ प्रदान गरिन्छ"
        for_text = "ले निम्न स्थान प्राप्त गरेको प्रमाणित गरिन्छ"
        in_text = "प्रतियोगितामा"
        date_str = f"मिति: {CONFIG.get('EVENT_DATE_NP', '२०८२-०१-१५')}"
        sign_left = "प्राविधिक संयोजक"
        sign_right = "आयोजक समिति"
        ranks = {1: "प्रथम (स्वर्ण)", 2: "द्वितीय (रजत)", 3: "तृतीय (कांस्य)"}
    else:
        header_text = f"16th {CONFIG.get('EVENT_TITLE_EN', 'President Running Shield')} 2026"
        title_text = "CERTIFICATE OF ACHIEVEMENT"
        presented_text = "This certificate is proudly presented to"
        for_text = "for securing the position of"
        in_text = "in the event"
        date_str = f"Date: {CONFIG.get('EVENT_DATE_EN', 'April 2026')}"
        sign_left = "Technical Coordinator"
        sign_right = "Organizer"
        ranks = {1: "FIRST (Gold)", 2: "SECOND (Silver)", 3: "THIRD (Bronze)"}

    # र्याङ्क अनुसारको रङ्ग
    rank_colors = {
        1: colors.gold,
        2: colors.silver,
        3: colors.Color(0.8, 0.4, 0.2) # Bronze Color
    }

    for _, row in winners_df.iterrows():
        try: rank = int(row.get('rank', row.get('position', 1)))
        except: rank = 1
        
        player_name = str(row.get('name', 'Unknown')).strip()
        school_name = str(row.get('school_name', 'Unknown School')).strip()

        # लामो नाम भएमा फन्ट साइज सानो बनाउने
        name_font_size = 20 if len(player_name) > 30 else (22 if len(player_name) > 20 else 26)

        # 1. Borders
        c.setStrokeColor(colors.darkblue)
        c.setLineWidth(5)
        c.rect(1*cm, 1*cm, width-2*cm, height-2*cm)
        c.setStrokeColor(colors.gold)
        c.setLineWidth(2)
        c.rect(1.2*cm, 1.2*cm, width-2.4*cm, height-2.4*cm)

        # 2. Header
        header_y = height - 2.5*cm
        c.setFont("Helvetica-Bold" if default_font == 'Helvetica' else default_font, 18)
        c.setFillColor(colors.darkred)
        c.drawCentredString(width/2, header_y, header_text)

        # 3. Title
        c.setFont("Helvetica-Bold" if default_font == 'Helvetica' else default_font, 30)
        c.setFillColor(colors.darkblue)
        c.drawCentredString(width/2, header_y - 2*cm, title_text)

        # 4. Presented To
        c.setFont(default_font, 14)
        c.setFillColor(colors.black)
        c.drawCentredString(width/2, header_y - 3.5*cm, presented_text)

        # 5. Name
        c.setFont("Helvetica-BoldOblique" if default_font == 'Helvetica' else default_font, name_font_size)
        c.setFillColor(colors.darkred)
        c.drawCentredString(width/2, header_y - 5.3*cm, player_name)

        # 6. School
        c.setFillColor(colors.black)
        c.setFont(default_font, 16)
        prefix = "" if language == 'np' else "of "
        c.drawCentredString(width/2, header_y - 6.8*cm, f"{prefix}{school_name}")

        # 7. For Securing
        c.setFont(default_font, 14)
        c.drawCentredString(width/2, header_y - 8.2*cm, for_text)

        # 8. Rank
        c.setFont("Helvetica-Bold" if default_font == 'Helvetica' else default_font, 22)
        c.setFillColor(rank_colors.get(rank, colors.black))
        c.drawCentredString(width/2, header_y - 9.8*cm, ranks.get(rank, f"Rank {rank}"))

        # 9. Event
        c.setFillColor(colors.black)
        c.setFont(default_font, 16)
        c.drawCentredString(width/2, header_y - 11*cm, f"{in_text} {event_name}")

        # 10. Date & Signatures
        c.setFont(default_font, 12)
        c.line(3*cm, 3*cm, 8*cm, 3*cm)
        c.drawString(4*cm, 3.2*cm, sign_left)
        c.drawString(4.5*cm, 2.5*cm, date_str)

        c.line(width-8*cm, 3*cm, width-3*cm, 3*cm)
        c.drawCentredString(width-5.5*cm, 3.2*cm, sign_right)

        c.showPage()
        
    c.save()
    buffer.seek(0)
    return buffer