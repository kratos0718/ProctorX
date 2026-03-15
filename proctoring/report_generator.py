from fpdf import FPDF
from datetime import datetime
import os

class ReportGenerator:
    def generate(self, session, violations, risk_summary, output_path):
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()

        pdf.set_font('Arial', 'B', 20)
        pdf.set_fill_color(30, 60, 120)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(0, 15, 'AI EXAM PROCTORING REPORT', ln=True, align='C', fill=True)
        pdf.ln(5)

        pdf.set_text_color(0, 0, 0)
        pdf.set_font('Arial', 'B', 13)
        pdf.cell(0, 10, 'Exam Session Details', ln=True)

        info = [
            ('Student', session.student.username),
            ('Email', session.student.email),
            ('Exam', session.exam_name),
            ('Start Time', str(session.start_time)[:19]),
            ('End Time', str(session.end_time)[:19] if session.end_time else 'N/A'),
            ('Status', session.status.upper()),
        ]
        for label, value in info:
            pdf.set_font('Arial', 'B', 11)
            pdf.cell(50, 8, label + ':', ln=False)
            pdf.set_font('Arial', '', 11)
            pdf.cell(0, 8, str(value), ln=True)
        pdf.ln(5)

        pdf.set_font('Arial', 'B', 13)
        pdf.cell(0, 10, 'Risk Assessment', ln=True)
        score = risk_summary.get('score', 0)
        level = risk_summary.get('level', 'low').upper()
        colors = {'LOW': (40,167,69), 'MEDIUM': (255,193,7), 'HIGH': (253,126,20), 'CRITICAL': (220,53,69)}
        r, g, b = colors.get(level, (40,167,69))
        pdf.set_fill_color(r, g, b)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font('Arial', 'B', 14)
        pdf.cell(0, 12, 'Final Risk Score: ' + str(score) + '/100  |  Level: ' + level, ln=True, align='C', fill=True)
        pdf.set_text_color(0, 0, 0)
        pdf.ln(5)

        pdf.set_font('Arial', 'B', 13)
        pdf.cell(0, 10, 'Violation Summary (Total: ' + str(len(violations)) + ')', ln=True)

        if violations:
            pdf.set_font('Arial', 'B', 10)
            pdf.set_fill_color(200, 200, 220)
            pdf.cell(60, 8, 'Type', fill=True, border=1)
            pdf.cell(30, 8, 'Severity', fill=True, border=1)
            pdf.cell(60, 8, 'Timestamp', fill=True, border=1)
            pdf.cell(40, 8, 'Details', fill=True, border=1)
            pdf.ln()
            pdf.set_font('Arial', '', 9)
            for v in violations:
                pdf.cell(60, 7, v.violation_type.replace('_', ' ').title(), border=1)
                pdf.cell(30, 7, v.severity.upper(), border=1)
                pdf.cell(60, 7, str(v.timestamp)[:19], border=1)
                pdf.cell(40, 7, (v.details or '')[:30], border=1)
                pdf.ln()
        else:
            pdf.set_font('Arial', 'I', 11)
            pdf.cell(0, 8, 'No violations recorded.', ln=True)

        pdf.ln(8)
        pdf.set_font('Arial', 'I', 9)
        pdf.set_text_color(120, 120, 120)
        pdf.cell(0, 8, 'Generated on ' + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + ' by AI Exam Proctoring System', ln=True, align='C')

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        pdf.output(output_path)
        return output_path
