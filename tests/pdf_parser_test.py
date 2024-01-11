from src.pdf_to_json import PDFParser
import fitz  # PyMuPDF
import pytest
from pathlib import Path

# Path to the directory of this test file
TEST_DIR = Path(__file__).parent

path = TEST_DIR / "test_data/insurance_handbook.pdf"


def test_pdf_parser_initialization():
    doc = fitz.open(path)  # Replace with a valid PDF path
    parser = PDFParser(doc)
    assert parser.doc == doc


def test_process_document():
    doc = fitz.open(path)  # Use a real or a mocked PDF path
    parser = PDFParser(doc)
    result = parser.process_document()
    assert isinstance(result, list)
    assert len(result) > 0

    for page_data in result:
        assert isinstance(page_data, dict)
        assert 'page' in page_data
        assert isinstance(page_data['page'], int)
        assert 'content' in page_data
        assert isinstance(page_data['content'], list)


def test_extract_fonts():
    doc = fitz.open(path)  # Use a real or a mocked PDF path
    parser = PDFParser(doc)
    page = doc[0]  # Assuming the PDF has at least one page
    font_counts, styles = parser._extract_fonts(page)
    assert len(font_counts) > 0  # Ensure the dictionary is not empty
    assert isinstance(styles, dict)
    assert len(styles) > 0  # Ensure the dictionary is not empty


def test_extract_headers_and_paragraphs():
    doc = fitz.open(path)  # Use a real or a mocked PDF path
    parser = PDFParser(doc)
    page = doc[0]  # Assuming the PDF has at least one page
    size_tag_map = {"example_identifier": "<p>"}  # Mocked size_tag_map
    headers_paragraphs = parser._extract_page_content(page, size_tag_map)
    assert isinstance(headers_paragraphs, list)
    assert len(headers_paragraphs) > 0
