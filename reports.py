"""PDF client report (fpdf2)."""
from fpdf import FPDF


def _safe(text):
    """Core PDF fonts are latin-1 only."""
    text = str(text).replace("\u2013", "-").replace("\u2014", "-")
    return text.encode("latin-1", "replace").decode("latin-1")


def client_report_pdf(client):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, _safe(f"Client Report - {client['name']}"), new_x="LMARGIN",
             new_y="NEXT", align="C")
    pdf.set_font("Helvetica", "", 12)
    pdf.ln(10)
    lines = [
        ("Name", client["name"]),
        ("Age", client["age"]),
        ("Height", f"{client['height']} cm"),
        ("Weight", f"{client['weight']} kg"),
        ("Program", client["program"]),
        ("Membership Expiry", client["membership_expiry"]),
    ]
    for label, value in lines:
        pdf.cell(0, 10, _safe(f"{label}: {value}"), new_x="LMARGIN", new_y="NEXT")
    return bytes(pdf.output())
