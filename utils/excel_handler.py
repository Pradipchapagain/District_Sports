import pandas as pd
import io
from xlsxwriter.utility import xl_col_to_name

def generate_master_excel(events_df, entity_name="Municipality"):
    boys_events = events_df[(events_df['gender'] == 'Boys') | (events_df['gender'] == 'Both')]
    girls_events = events_df[(events_df['gender'] == 'Girls') | (events_df['gender'] == 'Both')]
    
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        wb = writer.book
        
        # Sheets
        ws_boys = wb.add_worksheet("Boys_Entry")
        ws_girls = wb.add_worksheet("Girls_Entry")
        ws_summary = wb.add_worksheet("Summary")
        
        # Formats
        fmt_head_main = wb.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'bg_color': '#1F4E78', 'font_color': 'white', 'border': 1})
        fmt_head_sub = wb.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'bg_color': '#D9E1F2', 'border': 1, 'font_size': 10})
        fmt_ev_v = wb.add_format({'bold': True, 'bg_color': '#E2EFDA', 'border': 1, 'align': 'center', 'valign': 'bottom', 'rotation': 90, 'font_size': 10})
        fmt_locked = wb.add_format({'bg_color': '#F2F2F2', 'border': 1, 'align': 'center'})
        fmt_input = wb.add_format({'bg_color': '#FFFFCC', 'border': 1}) # पहेँलो (Input)
        fmt_error = wb.add_format({'bg_color': '#FF0000', 'font_color': 'white', 'bold': True, 'border': 1})
        fmt_ok = wb.add_format({'bg_color': '#00B050', 'font_color': 'white', 'bold': True, 'border': 1})
        
        basics = ['Student Name', 'EMIS ID', 'DOB (YYYY-MM-DD)', 'School Name', 'Class']
        num_basics = len(basics)

        def create_entry_sheet(worksheet, ev_df, gender_name):
            worksheet.merge_range(0, 0, 2, num_basics - 1, f"खेलाडीको विवरण ({gender_name})", fmt_head_main)
            worksheet.write_row(3, 0, basics, fmt_head_sub)
            for i in range(num_basics): worksheet.set_column(i, i, 18)
            
            current_col = num_basics 
            ev_df = ev_df.sort_values(['category', 'sub_category', 'event_group', 'name'])
            col_map = {} 
            
            for _, event in ev_df.iterrows():
                worksheet.write(3, current_col, event['name'], fmt_ev_v)
                worksheet.set_column(current_col, current_col, 4)
                worksheet.data_validation(4, current_col, 204, current_col, {'validate': 'list', 'source': ['1']})
                for r in range(4, 204): worksheet.write_blank(r, current_col, '', fmt_input)
                col_map[event['code']] = current_col
                current_col += 1

            def merge_header_level(level_col, row_idx, colors_list):
                if ev_df.empty: return
                groups = []
                last_val = ev_df.iloc[0][level_col]
                count = 0
                for _, row in ev_df.iterrows():
                    val = row[level_col]
                    if val == last_val: count += 1
                    else:
                        groups.append((last_val, count))
                        last_val = val
                        count = 1
                groups.append((last_val, count))

                start = num_basics
                c_idx = 0
                for name, width in groups:
                    end = start + width - 1
                    bg_col = colors_list[c_idx % len(colors_list)]
                    font_col = 'white' if row_idx == 0 else 'black'
                    fmt = wb.add_format({'bold': True, 'align': 'center', 'border': 1, 'bg_color': bg_col, 'valign': 'vcenter', 'font_color': font_col})
                    
                    if width > 1: worksheet.merge_range(row_idx, start, row_idx, end, name, fmt)
                    else: worksheet.write(row_idx, start, name, fmt)
                    start = end + 1
                    c_idx += 1

            merge_header_level('category', 0, ['#2F5597', '#C65911', '#548235'])
            merge_header_level('sub_category', 1, ['#8EA9DB', '#F4B084', '#A9D08E', '#FFD966'])
            merge_header_level('event_group', 2, ['#D9E1F2', '#FCE4D6', '#E2EFDA', '#FFF2CC', '#EDEDED'])

            # ================= VALIDATION LOGIC (UPDATED FOR RELAY) =================
            val_start_col = current_col  
            
            # यहाँ exclude_val थपिएको छ (Relay लाई हटाउन)
            def get_ranges(criteria_col, value, exclude_val=None):
                cols = []
                if exclude_val:
                    matches = ev_df[(ev_df[criteria_col] == value) & (ev_df['event_group'] != exclude_val)]
                else:
                    matches = ev_df[ev_df[criteria_col] == value]
                    
                for code in matches['code']:
                    if code in col_map: cols.append(xl_col_to_name(col_map[code]))
                return cols

            # भ्यालिडेसन नियमहरू (Relay बाहेक)
            rules = [
                ("Track (Max 2)", "sub_category", "Track", 2, "Relay"),       # 👈 Relay बाहेक
                ("Field (Max 2)", "sub_category", "Field", 2, None),
                ("Athletics (Max 3)", "category", "Athletics", 3, "Relay"),   # 👈 Relay बाहेक
                ("Team Games (Max 1)", "category", "Team Game", 1, None),
                ("Martial Arts (Max 1)", "category", "Martial Arts", 1, None)
            ]
            
            curr_val_col = val_start_col
            for r_name, _, _, _, _ in rules:
                worksheet.write(3, curr_val_col, r_name, fmt_ev_v)
                curr_val_col += 1
            
            status_col_idx = curr_val_col
            worksheet.write(3, status_col_idx, "STATUS", fmt_head_main)
            worksheet.set_column(status_col_idx, status_col_idx, 12)
            
            for row in range(4, 204): 
                xl_row = row + 1
                rule_col_letters = []
                for idx, (r_name, crit_col, crit_val, limit, excl_val) in enumerate(rules):
                    target_cols = get_ranges(crit_col, crit_val, excl_val)
                    my_col_idx = val_start_col + idx
                    if target_cols:
                        cell_refs = [f"{c}{xl_row}" for c in target_cols]
                        formula = f"=SUM({','.join(cell_refs)})"
                        worksheet.write_formula(row, my_col_idx, formula, fmt_locked)
                        c_letter = xl_col_to_name(my_col_idx)
                        worksheet.conditional_format(f"{c_letter}{xl_row}", {'type': 'cell', 'criteria': '>', 'value': limit, 'format': fmt_error})
                    else:
                        worksheet.write(row, my_col_idx, 0, fmt_locked)
                    rule_col_letters.append(xl_col_to_name(my_col_idx))

                checks = [f"{let}{xl_row}>{lim}" for let, (_,_,_,lim,_) in zip(rule_col_letters, rules)]
                if checks: status_formula = f'=IF(SUM({xl_col_to_name(num_basics)}{xl_row}:{xl_col_to_name(val_start_col-1)}{xl_row})=0, "", IF(OR({",".join(checks)}), "❌ Error", "✅ OK"))'
                else: status_formula = '="✅ OK"'
                
                worksheet.write_formula(row, status_col_idx, status_formula)
                st_let = xl_col_to_name(status_col_idx)
                worksheet.conditional_format(f"{st_let}{xl_row}", {'type': 'text', 'criteria': 'containing', 'value': 'OK', 'format': fmt_ok})
                worksheet.conditional_format(f"{st_let}{xl_row}", {'type': 'text', 'criteria': 'containing', 'value': 'Error', 'format': fmt_error})

            for row in range(4, 204):
                for col in range(num_basics):
                    worksheet.write_blank(row, col, '', fmt_input)

            return col_map

        boys_map = create_entry_sheet(ws_boys, boys_events, "Boys")
        girls_map = create_entry_sheet(ws_girls, girls_events, "Girls")
        
        # ================= 2. SUMMARY SHEET =================
        sum_headers = ['Category', 'Sub-Category', 'Event Group', 'Event Name', 'Boys', 'Girls', 'Total']
        ws_summary.write_row(0, 0, sum_headers, fmt_head_main)
        ws_summary.set_column(0, 2, 16); ws_summary.set_column(3, 3, 25); ws_summary.set_column(4, 6, 12)
        
        unique_events = events_df.drop_duplicates(subset=['category', 'sub_category', 'event_group', 'name'])
        unique_events = unique_events.sort_values(['category', 'sub_category', 'event_group', 'name'])
        
        row_idx = 1
        for _, u_ev in unique_events.iterrows():
            ws_summary.write(row_idx, 0, u_ev['category'])
            ws_summary.write(row_idx, 1, u_ev['sub_category'])
            ws_summary.write(row_idx, 2, u_ev['event_group'])
            ws_summary.write(row_idx, 3, u_ev['name'])
            
            b_match = boys_events[(boys_events['name'] == u_ev['name']) & (boys_events['sub_category'] == u_ev['sub_category'])]
            if not b_match.empty and b_match.iloc[0]['code'] in boys_map:
                col_let = xl_col_to_name(boys_map[b_match.iloc[0]['code']])
                ws_summary.write_formula(row_idx, 4, f"=COUNTIF('Boys_Entry'!{col_let}5:{col_let}204, 1)")
            else: ws_summary.write(row_idx, 4, 0)
                
            g_match = girls_events[(girls_events['name'] == u_ev['name']) & (girls_events['sub_category'] == u_ev['sub_category'])]
            if not g_match.empty and g_match.iloc[0]['code'] in girls_map:
                col_let = xl_col_to_name(girls_map[g_match.iloc[0]['code']])
                ws_summary.write_formula(row_idx, 5, f"=COUNTIF('Girls_Entry'!{col_let}5:{col_let}204, 1)")
            else: ws_summary.write(row_idx, 5, 0)
                
            ws_summary.write_formula(row_idx, 6, f"=E{row_idx+1}+F{row_idx+1}")
            row_idx += 1
        
        ws_summary.write(row_idx, 3, "GRAND TOTAL", fmt_head_main)
        ws_summary.write_formula(row_idx, 4, f"=SUM(E2:E{row_idx})", fmt_head_main)
        ws_summary.write_formula(row_idx, 5, f"=SUM(F2:F{row_idx})", fmt_head_main)
        ws_summary.write_formula(row_idx, 6, f"=SUM(G2:G{row_idx})", fmt_head_main)

    buffer.seek(0)
    return buffer