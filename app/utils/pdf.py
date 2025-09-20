from pypdf import PdfReader


def extract_pdf_text(file) -> tuple[str, int, int]:
	reader = PdfReader(file)
	pages = len(reader.pages)
	text = []
	for p in reader.pages:
		try:
			t = p.extract_text() or ""
		except Exception:
			t = ""
		text.append(t)
	joined = "\n".join(text)
	return joined, pages, len(joined)
