import streamlit as st
import fitz  # PyMuPDF
from typing import Optional
from streamlit.runtime.uploaded_file_manager import UploadedFile

from src import PDFParser, HTMLToJsonConverter, MetadataEnhancedJsonConverter


class PDFToJsonConverterApp:
    def __init__(self, default_url: str = "https://example.com/"):
        """ Initialize the application with a default URL. """
        self.base_url = default_url

    def upload_pdf_file(self) -> Optional[UploadedFile]:
        """ Handles the uploading of a PDF file. """
        return st.file_uploader("Choose a PDF file", type="pdf")

    def get_base_url(self) -> str:
        """ Returns the base URL provided by the user. """
        return st.text_input("Enter Base URL", self.base_url)

    def process_pdf_to_json(self, uploaded_file: UploadedFile, base_url: str) -> Optional[str]:
        """ Converts a PDF file to JSON format. """
        try:
            doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
            pdf_parser = PDFParser(doc)
            all_pages_data = pdf_parser.process_document()

            html_converter = HTMLToJsonConverter(all_pages_data)
            raw_json_output = html_converter.process_list_to_json()

            metadata_processor = MetadataEnhancedJsonConverter(raw_json_output, uploaded_file.name, base_url)
            return metadata_processor.get_enhanced_json()
        except Exception as e:
            st.error(f'An error occurred: {e}')
            return None

    def display_json_output(self, json_output: str) -> None:
        """ Displays the JSON output in a text area. """
        st.text_area("JSON Output", json_output, height=300)

    def run(self) -> None:
        """ Main function to run the Streamlit app. """
        st.title("PDF to JSON Converter")
        uploaded_file = self.upload_pdf_file()
        base_url = self.get_base_url()

        if uploaded_file is not None:
            with st.spinner('Processing...'):
                json_output = self.process_pdf_to_json(uploaded_file, base_url)
                if json_output:
                    st.success('Processing complete!')
                    self.display_json_output(json_output)


if __name__ == "__main__":
    app = PDFToJsonConverterApp()
    app.run()
