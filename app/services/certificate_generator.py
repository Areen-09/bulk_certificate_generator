import io
import math
from datetime import date
from typing import Any, Dict, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas


class CertificateGenerator:
    """
    Pure Python vector certificate generator using ReportLab.
    Produces high-resolution, print-ready PDF certificates.
    """

    def __init__(self):
        # Landscape A4 dimensions in points: 841.89 x 595.27
        self.width, self.height = landscape(A4)
        
        # Color palette
        self.c_navy = colors.HexColor("#0F172A")
        self.c_slate = colors.HexColor("#334155")
        self.c_muted = colors.HexColor("#64748B")
        self.c_gold = colors.HexColor("#D97706")
        self.c_light_gold = colors.HexColor("#F59E0B")
        self.c_border_outer = colors.HexColor("#1E293B")
        self.c_seal_bg = colors.HexColor("#FEF3C7")

    def generate_pdf(
        self,
        recipient_name: str,
        event_name: str,
        issuer_name: str,
        issue_date: date,
        certificate_code: str,
        description: Optional[str] = None,
        custom_data: Optional[Dict[str, Any]] = None,
    ) -> bytes:
        """Renders the certificate to PDF bytes."""
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=(self.width, self.height))

        # 1. Background and Decorative Borders
        self._draw_borders(c)

        # 2. Header and Title
        self._draw_header(c, issuer_name)

        # 3. Recipient and Achievement Details
        self._draw_recipient_and_details(
            c, recipient_name, event_name, description, custom_data
        )

        # 4. Seal and Signatures
        self._draw_footer(c, issuer_name, issue_date, certificate_code)

        c.showPage()
        c.save()

        buffer.seek(0)
        return buffer.getvalue()

    def _draw_borders(self, c: canvas.Canvas) -> None:
        margin_outer = 22
        margin_inner = 28

        # Background subtle tint fill
        c.setFillColor(colors.HexColor("#FCFCFD"))
        c.rect(margin_outer, margin_outer, self.width - 2 * margin_outer, self.height - 2 * margin_outer, fill=1, stroke=0)

        # Outer thick border
        c.setStrokeColor(self.c_navy)
        c.setLineWidth(4)
        c.rect(margin_outer, margin_outer, self.width - 2 * margin_outer, self.height - 2 * margin_outer)

        # Inner fine gold border
        c.setStrokeColor(self.c_gold)
        c.setLineWidth(1.5)
        c.rect(margin_inner, margin_inner, self.width - 2 * margin_inner, self.height - 2 * margin_inner)

        # Corner Ornaments (Classic 4-corner accents)
        self._draw_corner_ornaments(c, margin_inner)

    def _draw_corner_ornaments(self, c: canvas.Canvas, margin: float) -> None:
        c.setStrokeColor(self.c_gold)
        c.setLineWidth(1.5)
        accent_size = 20

        corners = [
            (margin, margin, 1, 1),
            (self.width - margin, margin, -1, 1),
            (margin, self.height - margin, 1, -1),
            (self.width - margin, self.height - margin, -1, -1),
        ]

        for x, y, dx, dy in corners:
            c.line(x, y + dy * accent_size, x + dx * accent_size, y + dy * accent_size)
            c.line(x + dx * accent_size, y, x + dx * accent_size, y + dy * accent_size)
            c.circle(x + dx * 8, y + dy * 8, 2, fill=1, stroke=0)

    def _draw_header(self, c: canvas.Canvas, issuer_name: str) -> None:
        cx = self.width / 2.0

        # Issuer Header Text
        c.setFont("Helvetica-Bold", 11)
        c.setFillColor(self.c_gold)
        c.drawCentredString(cx, self.height - 75, issuer_name.upper())

        # Main Certificate Heading
        c.setFont("Helvetica-Bold", 28)
        c.setFillColor(self.c_navy)
        c.drawCentredString(cx, self.height - 112, "CERTIFICATE OF ACHIEVEMENT")

        # Decorative divider under title
        div_w = 160
        y_div = self.height - 124
        c.setStrokeColor(self.c_gold)
        c.setLineWidth(1.2)
        c.line(cx - div_w, y_div, cx - 12, y_div)
        c.line(cx + 12, y_div, cx + div_w, y_div)

        # Center diamond accent on divider
        c.setFillColor(self.c_gold)
        p = c.beginPath()
        p.moveTo(cx, y_div + 4)
        p.lineTo(cx + 5, y_div)
        p.lineTo(cx, y_div - 4)
        p.lineTo(cx - 5, y_div)
        p.close()
        c.drawPath(p, fill=1, stroke=0)

    def _draw_recipient_and_details(
        self,
        c: canvas.Canvas,
        recipient_name: str,
        event_name: str,
        description: Optional[str],
        custom_data: Optional[Dict[str, Any]],
    ) -> None:
        cx = self.width / 2.0

        # "THIS IS PROUDLY PRESENTED TO"
        c.setFont("Helvetica", 11)
        c.setFillColor(self.c_muted)
        c.drawCentredString(cx, self.height - 165, "THIS IS PROUDLY PRESENTED TO")

        # Dynamic Recipient Name (scales if text is long)
        name_font_size = 32
        if len(recipient_name) > 30:
            name_font_size = 24
        elif len(recipient_name) > 20:
            name_font_size = 28

        c.setFont("Helvetica-Bold", name_font_size)
        c.setFillColor(self.c_navy)
        c.drawCentredString(cx, self.height - 215, recipient_name)

        # Underline for recipient name
        name_width = min(c.stringWidth(recipient_name, "Helvetica-Bold", name_font_size) + 40, 500)
        c.setStrokeColor(self.c_gold)
        c.setLineWidth(1)
        c.line(cx - name_width / 2, self.height - 225, cx + name_width / 2, self.height - 225)

        # Presentation description clause
        clause = description or "for successful participation and exceptional completion of"
        c.setFont("Helvetica", 12)
        c.setFillColor(self.c_slate)
        c.drawCentredString(cx, self.height - 262, clause)

        # Course / Event Title
        event_font_size = 22 if len(event_name) < 40 else 18
        c.setFont("Helvetica-Bold", event_font_size)
        c.setFillColor(self.c_navy)
        c.drawCentredString(cx, self.height - 302, event_name)

        # Optional custom data badges/pills (e.g. Grade, Hours)
        if custom_data:
            extras = []
            for k, v in custom_data.items():
                extras.append(f"{k.capitalize()}: {v}")
            extra_text = "  •  ".join(extras)
            if extra_text:
                c.setFont("Helvetica-Oblique", 11)
                c.setFillColor(self.c_muted)
                c.drawCentredString(cx, self.height - 332, extra_text)

    def _draw_footer(
        self,
        c: canvas.Canvas,
        issuer_name: str,
        issue_date: date,
        certificate_code: str,
    ) -> None:
        y_footer_line = 110

        # 1. Left Signature block: Date of Issue
        c.setStrokeColor(self.c_slate)
        c.setLineWidth(0.8)
        c.line(100, y_footer_line, 260, y_footer_line)
        c.setFont("Helvetica", 10)
        c.setFillColor(self.c_slate)
        formatted_date = issue_date.strftime("%B %d, %Y") if hasattr(issue_date, "strftime") else str(issue_date)
        c.drawCentredString(180, y_footer_line + 8, formatted_date)
        c.setFont("Helvetica", 9)
        c.setFillColor(self.c_muted)
        c.drawCentredString(180, y_footer_line - 15, "DATE OF ISSUANCE")

        # 2. Right Signature block: Authorized Signatory
        c.line(self.width - 260, y_footer_line, self.width - 100, y_footer_line)
        c.setFont("Helvetica-Bold", 10)
        c.setFillColor(self.c_navy)
        c.drawCentredString(self.width - 180, y_footer_line + 8, issuer_name)
        c.setFont("Helvetica", 9)
        c.setFillColor(self.c_muted)
        c.drawCentredString(self.width - 180, y_footer_line - 15, "AUTHORIZED SIGNATURE")

        # 3. Center Vector Seal
        self._draw_center_seal(c, self.width / 2.0, y_footer_line + 5)

        # 4. Bottom Verification Bar
        c.setFont("Helvetica", 8)
        c.setFillColor(self.c_muted)
        verify_str = f"Verification ID: {certificate_code}  |  Official Record Issued by {issuer_name}"
        c.drawCentredString(self.width / 2.0, 42, verify_str)

    def _draw_center_seal(self, c: canvas.Canvas, cx: float, cy: float) -> None:
        # Outer scalloped / golden ring
        radius = 28
        c.setFillColor(self.c_seal_bg)
        c.setStrokeColor(self.c_gold)
        c.setLineWidth(1.5)
        c.circle(cx, cy, radius, fill=1, stroke=1)

        # Inner ring
        c.setStrokeColor(self.c_gold)
        c.setLineWidth(0.8)
        c.circle(cx, cy, radius - 4, fill=0, stroke=1)

        # Inner seal star
        c.setFillColor(self.c_gold)
        self._draw_star(c, cx, cy, 5, 10, 4)

        # Text inside seal
        c.setFont("Helvetica-Bold", 6)
        c.setFillColor(self.c_navy)
        c.drawCentredString(cx, cy - 16, "VERIFIED")

    def _draw_star(
        self,
        c: canvas.Canvas,
        cx: float,
        cy: float,
        points: int,
        r_outer: float,
        r_inner: float,
    ) -> None:
        p = c.beginPath()
        angle_step = math.pi / points
        for i in range(2 * points):
            r = r_outer if i % 2 == 0 else r_inner
            angle = i * angle_step - math.pi / 2
            x = cx + r * math.cos(angle)
            y = cy + r * math.sin(angle)
            if i == 0:
                p.moveTo(x, y)
            else:
                p.lineTo(x, y)
        p.close()
        c.drawPath(p, fill=1, stroke=0)


certificate_generator = CertificateGenerator()
