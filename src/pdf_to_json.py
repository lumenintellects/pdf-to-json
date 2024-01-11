import os

import fitz  # PyMuPDF
import json
import re
from collections import defaultdict
from typing import Union, List, Dict, Tuple


class PDFParser:
    """
    This class is responsible for parsing a PDF document and extracting text elements such as
    headers and paragraphs based on font styles.

    Attributes:
        doc (fitz.Document): The PDF document to be parsed.
    """
    def __init__(self, doc: fitz.Document):
        """
        Initializes the PDFParser with a PDF document.

        Args:
            doc (fitz.Document): The PDF document to be parsed.
        """
        self.doc = doc

    def process_document(self) -> List[Dict[str, Union[int, List[str]]]]:
        """
        Processes each page of the PDF document, extracting font details and distinguishing headers from paragraphs.

        Returns:
            List[Dict[str, Union[int, List[str]]]]: A list of dictionaries, each representing a page with its content.
        """
        html_pages_list = []
        for page in self.doc:
            font_counts, styles = self._extract_fonts(page, granularity=True)
            size_tag = self._create_size_tag_map(font_counts, styles)
            headers_paragraphs = self._extract_page_content(page, size_tag)
            html_pages_list.append({"page": page.number, "content": headers_paragraphs})
        return html_pages_list

    def _extract_fonts(self, page: fitz.Page, granularity: bool = False) -> Tuple[Dict[str, int], Dict[str, dict]]:
        """
        Extracts fonts and their usage frequencies from a single PDF page.

        Args:
            page (fitz.Page): A single page of a PDF document.
            granularity (bool): Flag to determine the level of detail for font extraction.

        Returns:
            Tuple[Dict[str, int], Dict[str, dict]]: A tuple containing font counts and styles.
        """
        styles = {}
        font_counts = defaultdict(int)

        for block in page.get_text("dict")["blocks"]:
            if block['type'] == 0:
                for line in block["lines"]:
                    for span in line["spans"]:
                        identifier = self._create_identifier(span, granularity)
                        styles[identifier] = self._extract_style(span, granularity)
                        font_counts[identifier] += 1

        if not font_counts:
            raise ValueError("No fonts found on page {}".format(page.number))

        sorted_font_counts = sorted(font_counts.items(), key=lambda x: x[1], reverse=True)
        return sorted_font_counts, styles

    def _determine_tag(self, size, font, color, primary_style, header_idx, subheader_idx) -> Tuple[str, int, int]:
        """
        Determines the appropriate HTML tag for a text segment based on its style.

        Args:
            size (float): Size of the font.
            font (str): Font family.
            color (str): Color of the font.
            primary_style (dict): Primary style for comparison.
            header_idx (int): Current header index for tagging.
            subheader_idx (int): Current subheader index for tagging.

        Returns:
            Tuple[str, int]: The appropriate HTML tag and the updated header index.
        """
        p_size, p_font, p_color = primary_style['size'], primary_style['font'],  primary_style['color']
        if (size, font, color) == (p_size, p_font, p_color):
            return '<p>', header_idx, subheader_idx
        elif size > p_size or (size == p_size and (font != p_font or color != p_color)):
            tag = f'<h{header_idx}>'
            return tag, header_idx + 1, subheader_idx
        else:
            return '<p>', header_idx, subheader_idx

    def _create_size_tag_map(self, font_counts: Dict[str, int], styles: Dict[str, dict]) -> Dict[str, str]:
        """
        Creates a map of font styles to HTML tags based on the provided font counts and styles.
        This method is used to generate a dictionary where each unique font style is associated
        with an appropriate HTML tag (like 'h1', 'h2', etc.). The method sorts the styles
        primarily by font size and then applies specific rules to determine the corresponding
        HTML tag for each style.

        The method works by first extracting the 'p' style from the styles dictionary using
        the most frequent font style from font_counts. Then, it creates a set of unique styles
        (tuples of size, font, and color). These styles are sorted primarily by size in
        descending order. For each unique style, the method determines the appropriate HTML tag
        by considering its size, font, and color relative to the 'p' style and other factors like
        the number of headers and subheaders already assigned.

        Args:
            font_counts (Dict[str, int]): A dictionary where keys are font identifiers and
                                          values are counts of how often each font appears.
                                          Used to identify the most common font style.
            styles (Dict[str, dict]): A dictionary mapping font identifiers to their style
                                      attributes (like size, font, and color).

        Returns:
            Dict[str, str]: A dictionary where keys are strings representing the unique combination
                            of style attributes (size, font, color) and values are the corresponding
                            HTML tags. This map links each unique style to an HTML tag, indicating
                            how it should be rendered in HTML format.
        """
        primary_style = styles[font_counts[0][0]]
        unique_styles = {(style['size'], style['font'], style['color']) for style in styles.values()}
        sorted_unique_styles = sorted(unique_styles, key=lambda x: (-x[0], x[1], x[2]))  # Sort primarily by size

        size_tag_map = {}
        header_idx, subheader_idx = 1, 1
        for style in sorted_unique_styles:
            identifier = f"{style[0]}_{style[1]}_{style[2]}"
            tag, header_idx, subheader_idx = self._determine_tag(*style, primary_style, header_idx, subheader_idx)
            size_tag_map[identifier] = tag

        return size_tag_map

    def _extract_page_content(self, page: fitz.Page, size_tag_map: Dict[str, str]) -> List[str]:
        """
        Extracts content from a single PDF page.

        Args:
            page (fitz.Page): A single page of a PDF document.
            size_tag_map (Dict[str, str]): A map linking font styles to HTML tags.

        Returns:
            List[str]: A list of headers and paragraphs as HTML strings.
        """
        page_blocks = []
        for block in page.get_text("dict")["blocks"]:
            if block['type'] == 0:
                block_string = self._process_block(block, size_tag_map)
                if block_string:
                    page_blocks.append(block_string)
        return page_blocks

    def _create_identifier(self, span: dict, granularity: bool) -> str:
        """
        Creates an identifier for a text span based on its style.

        Args:
            span (dict): Text span containing style information.
            granularity (bool): Flag to determine the level of detail for the identifier.

        Returns:
            str: A unique identifier for the span.
        """
        if granularity:
            return f"{span['size']}_{span['font']}_{span['color']}"
        else:
            return f"{span['size']}"

    def _extract_style(self, span: dict, granularity: bool) -> dict:
        """
        Extracts the style from a text span.

        Args:
            span (dict): Text span containing style information.
            granularity (bool): Flag to determine the level of detail for the style extraction.

        Returns:
            dict: A dictionary representing the style of the span.
        """
        if granularity:
            return {'size': span['size'], 'font': span['font'], 'color': span['color']}
        else:
            return {'size': span['size']}

    def _process_block(self, block: dict, size_tag_map: Dict[str, str]) -> List[str]:
        """
        Processes a text block from a PDF page.

        Args:
            block (dict): A text block from the PDF.
            size_tag_map (Dict[str, str]): A map linking font styles to HTML tags.

        Returns:
            List[str]: Processed text block as a list of HTML strings.
        """
        block_strings = []
        block_string = ""
        previous_identifier = None

        for line in block["lines"]:
            for span in line["spans"]:
                identifier = f"{span['size']}_{span['font']}_{span['color']}"  # Construct the identifier

                if span['text'].strip():
                    if self._is_new_block(identifier, previous_identifier):
                        # Close the previous block if it exists
                        if previous_identifier in size_tag_map:
                            block_string += self._get_closing_tag(size_tag_map[previous_identifier])

                        # Append the current block_string to block_strings and start a new block
                        if block_string:
                            block_strings.append(block_string)
                            block_string = ""

                        block_string = self._start_new_block(span, identifier, size_tag_map)
                    else:
                        # If not a new block, just append the text
                        block_string += " " + span['text']

                    previous_identifier = identifier

        # Add the closing tag to the last block if needed and append it
        if previous_identifier in size_tag_map:
            block_string += self._get_closing_tag(size_tag_map[previous_identifier])

        if block_string:
            block_strings.append(block_string)

        return block_strings

    def _is_new_block(self, current_identifier: str, previous_identifier: str) -> bool:
        """
        Determine if a new block should start based on the change in identifiers.

        Args:
            current_identifier (str): Identifier for the current span, representing its style attributes.
            previous_identifier (str): Identifier for the previous span, representing its style attributes.

        Returns:
            bool: True if the identifiers are different and a new block should start, False otherwise.
        """
        return current_identifier != previous_identifier

    def _start_new_block(self, span: dict, identifier: str, size_tag_map: Dict[str, str]) -> str:
        """
        Starts a new text block based on the given identifier and span.

        Args:
            span (dict): A text span from the PDF.
            identifier (str): The unique identifier for the span's style.
            size_tag_map (Dict[str, str]): A map linking font styles to HTML tags.

        Returns:
            str: The starting string of a new text block.
        """
        # Get the closing tag for the previous block if it exists
        closing_tag = ""
        previous_identifier = None
        if previous_identifier and previous_identifier in size_tag_map:
            # Assuming _get_closing_tag method exists and returns the appropriate closing tag
            closing_tag = self._get_closing_tag(size_tag_map[previous_identifier])

        # Get the opening tag for the new block
        opening_tag = size_tag_map.get(identifier, "")

        # Return the combination of closing tag of the previous block, opening tag, and the span's text
        return closing_tag + opening_tag + span['text']

    def _get_closing_tag(self, opening_tag: str) -> str:
        """
        Generates a closing tag for a given opening tag.

        Args:
            opening_tag (str): An opening HTML tag.

        Returns:
            str: The corresponding closing HTML tag.
        """
        tag_type = opening_tag.split('<', 1)[1].split('>', 1)[0]  # Extracts 'h1' from '<h1>'
        return f'</{tag_type}>'


class HTMLToJsonConverter:
    """
        A converter class that processes HTML data and converts it into JSON format.

        Attributes:
            data_list (List[Dict[str, Union[int, List[str]]]]): A list of dictionaries containing HTML page data.
        """

    def __init__(self, data_list: List[Dict[str, Union[int, List[str]]]]):
        self.data_list = data_list

    def process_list_to_json(self) -> str:
        """
        Converts the data list of HTML content to a structured JSON format.

        Returns:
            str: A JSON string representing the structured data.
        """
        structured_data = []

        for page_data in self.data_list:
            structured_data.extend(self._process_page_content(page_data))

        data_merged = self._merge_empty_structured_data(structured_data)
        data_no_duplicates = self._remove_duplicates(data_merged)
        cleaned_data = self._process_titles(data_no_duplicates)
        return json.dumps(cleaned_data, ensure_ascii=False, indent=2)

    def _process_titles(self, data: List[Dict[str, Union[str, int]]]) -> List[Dict[str, Union[str, int]]]:
        """
        Processes the titles in the structured data to ensure continuity and remove empty titles.

        Args:
            data (List[Dict[str, Union[str, int]]]): A list of dictionaries representing structured data.

        Returns:
            List[Dict[str, Union[str, int]]]: The processed list with updated titles.
        """
        i = 0
        while i < len(data) - 1:
            if not data[i]['text']:  # Check if 'text' is empty
                data[i + 1]['title'] = data[i]['title'] + " " + data[i + 1]['title']
                del data[i]  # Remove the current item
            else:
                i += 1  # Only increment if an item was not removed
        return data

    def _remove_duplicates(self, structured_data: List[Dict[str, Union[str, int]]]) -> List[Dict[str, Union[str, int]]]:
        """
        Removes duplicate entries from the structured data.

        Args:
            structured_data (List[Dict[str, Union[str, int]]]): A list of dictionaries representing structured data.

        Returns:
            List[Dict[str, Union[str, int]]]: A list of dictionaries with duplicates removed.
        """
        unique_data = []
        seen = set()
        for item in structured_data:
            # Creating a tuple of the dictionary's items to make it hashable
            tuple_item = tuple(item.items())
            if tuple_item not in seen:
                seen.add(tuple_item)
                unique_data.append(item)
        return unique_data

    def _merge_empty_structured_data(self, structured_data: List[Dict[str, Union[str, int]]]) -> List[
        Dict[str, Union[str, int]]]:
        """
        Merges entries in the structured data that have empty 'text' fields.

        Args:
            structured_data (List[Dict[str, Union[str, int]]]): A list of dictionaries representing structured data.

        Returns:
            List[Dict[str, Union[str, int]]]: A list of dictionaries with merged entries.
        """
        processed_entries = []
        skip_next = False

        for i in range(len(structured_data)):
            # Skip processing this entry if it's marked to be skipped
            if skip_next:
                skip_next = False
                continue

            # Check if the current entry and the next entry (if exists) both have empty 'text' fields
            if structured_data[i]['text'] == '' and (i + 1 < len(structured_data)) and structured_data[i + 1]['text'] == '':
                # Merge the two entries
                merged_entry = {
                    'title': structured_data[i]['title'],
                    'text': structured_data[i + 1]['title'],
                    'page': structured_data[i]['page']
                }
                processed_entries.append(merged_entry)
                skip_next = True  # Skip the next entry as it's already merged
            else:
                # Add the entry as it is
                processed_entries.append(structured_data[i])

        return processed_entries

    def _process_page_content(self, page_data: Dict[str, Union[int, List[str]]]) -> List[Dict[str, Union[str, int]]]:
        """
        Processes the content of a single HTML page and structures it.

        Args:
            page_data (Dict[str, Union[int, List[str]]]): A dictionary containing the HTML content of a single page.

        Returns:
            List[Dict[str, Union[str, int]]]: A list of dictionaries each representing a structured section of the page.
        """
        structured_page_data = []
        current_section = {"title": "", "text": "", "page": page_data['page']}
        title_set = False

        flat_page = self._flatten_list(page_data['content'])
        for item in flat_page:
            if re.match(r'<h\d>', item):  # Check for heading tags
                if current_section["title"] or current_section["text"]:
                    structured_page_data.append(current_section)
                    current_section = {"title": "", "text": "", "page": page_data['page']}
                current_section["title"] = re.sub(r'<\/?h\d>', '', item)  # Remove HTML tags from title
                title_set = True
            elif re.match(r'<p>', item):  # Check for paragraph tags
                paragraph_text = re.sub(r'<\/?p>', '', item)  # Remove HTML tags from paragraph
                if not title_set:  # If title hasn't been set, use the first paragraph as title
                    current_section["title"] = paragraph_text
                    title_set = True
                else:
                    current_section["text"] += paragraph_text + " "

        if current_section["title"] or current_section["text"]:
            structured_page_data.append(current_section)
        return structured_page_data

    def _flatten_list(self, nested_list: List[List[str]]) -> List[str]:
        """
        Flattens a nested list of strings into a single list.

        Args:
            nested_list (List[List[str]]): A list containing nested lists of strings.

        Returns:
            List[str]: A flattened list of strings.
        """
        return [item for sublist in nested_list for item in sublist]


class MetadataEnhancedJsonConverter:
    """
    A class to enhance JSON data extracted from a PDF document by adding additional metadata.

    Attributes:
        json_data (List[Dict[str, Any]]): A list of dictionaries representing the JSON data.
        file_name (str): The name of the PDF file.
        base_url (str): The base URL for constructing the link.
        product (str): The product name, extracted from the first entry of the JSON data.
        document (str): The document name, extracted from the first entry of the JSON data.
    """

    def __init__(self, json_string: str, file_path: str, base_url: str) -> None:
        """
        Initialize the MetadataEnhancedJsonConverter with JSON string, file path, and base URL.

        Args:
            json_string (str): The JSON string to be processed.
            file_path (str): The file path of the PDF document.
            base_url (str): The base URL for link generation.
        """
        self.json_data = json.loads(json_string)
        self.file_name = os.path.basename(file_path)
        self.base_url = base_url
        if self.json_data and isinstance(self.json_data, list):
            self.product = self.json_data[0].get("title", "")
            self.document = self.json_data[0].get("title", "")
        else:
            self.product = ""
            self.document = ""

    def enhance_json(self) -> None:
        """
        Enhance the JSON data by adding metadata fields to each entry.
        """
        for entry in self.json_data:
            entry["file"] = self.file_name
            entry["product"] = self.product
            entry["document"] = self.document
            entry["link"] = self.base_url + self.file_name

    def get_enhanced_json(self) -> str:
        """
        Return the enhanced JSON data as a formatted string.

        Returns:
            str: The enhanced JSON data in string format.
        """
        self.enhance_json()
        return json.dumps(self.json_data, ensure_ascii=False, indent=2)
