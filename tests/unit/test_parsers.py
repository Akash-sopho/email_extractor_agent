from email.message import EmailMessage

from app.gmail.parsers import extract_bodies_from_mime


def build_multipart_email() -> bytes:
    msg = EmailMessage()
    msg["From"] = "a@example.com"
    msg["To"] = "b@example.com"
    msg["Subject"] = "Test"
    msg.set_content("Hello plain")
    msg.add_alternative("<p>Hello <b>html</b></p>", subtype="html")
    return msg.as_bytes()


def test_extract_bodies_from_mime():
    raw = build_multipart_email()
    plain, html = extract_bodies_from_mime(raw)
    assert plain is not None and "Hello plain" in plain
    assert html is not None and "<b>html</b>" in html

