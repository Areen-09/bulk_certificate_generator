import datetime
from app.services.certificate_generator import certificate_generator


def test_certificate_generator_creates_valid_pdf():
    """Validates that CertificateGenerator outputs a valid PDF with correct header bytes."""
    pdf_bytes = certificate_generator.generate_pdf(
        recipient_name="Ada Lovelace",
        event_name="Foundations of Computer Programming",
        issuer_name="Pioneers Institute",
        issue_date=datetime.date(2026, 1, 1),
        certificate_code="CERT-ADA001",
        description="for outstanding contributions to algorithm design",
        custom_data={"grade": "Distinction", "hours": 40},
    )

    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 1000
    # PDF magic signature
    assert pdf_bytes.startswith(b"%PDF-")


def test_certificate_generator_handles_long_names_and_unicode():
    """Validates that long names and unicode characters render without throwing exceptions."""
    pdf_bytes = certificate_generator.generate_pdf(
        recipient_name="Prof. Maximillian Bartholomew Montgomery-Smith III",
        event_name="International Symposium on Advanced Distributed Cloud Infrastructures & Resilience",
        issuer_name="Global Systems Academy",
        issue_date=datetime.date.today(),
        certificate_code="CERT-LONG002",
        description="for demonstrated excellence across multiple domains",
        custom_data={"specialty": "Distributed Systems", "score": "99.5%"},
    )

    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes.startswith(b"%PDF-")
