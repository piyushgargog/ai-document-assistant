from pdf_loader import load_pdf_pages


def test_valid_pdf_extracts_all_pages_with_correct_numbering(sample_pdf_bytes):
    pages = load_pdf_pages(sample_pdf_bytes)
    assert [p for p, _ in pages] == [1, 2, 3, 4]
    assert "Solar System" in pages[0][1]


def test_invalid_pdf_bytes_return_empty_list():
    assert load_pdf_pages(b"this is not a pdf") == []


def test_empty_bytes_return_empty_list():
    assert load_pdf_pages(b"") == []
