import pytest
import json
from src.pdf_to_json import HTMLToJsonConverter


# Sample data for testing
test_data = [
    {
        'page': 1,
        'content': [['<h1>Title 1</h1>', '<p>Paragraph 1</p>', '<p>Paragraph 2</p>']]
    },
    {
        'page': 2,
        'content': [['<h2>Title 2</h2>', '<p>Paragraph 3</p>']]
    }
]

def test_init():
    converter = HTMLToJsonConverter(test_data)
    assert converter.data_list == test_data

def test_process_list_to_json():
    converter = HTMLToJsonConverter(test_data)
    json_output = converter.process_list_to_json()
    data = json.loads(json_output)

    assert isinstance(data, list)
    assert len(data) > 0

def test_process_page_content():
    converter = HTMLToJsonConverter(test_data)
    result = converter._process_page_content(test_data[0])

    assert isinstance(result, list)
    # Expect at least one structured entry per page
    assert len(result) > 0

def test_process_titles():
    converter = HTMLToJsonConverter(test_data)
    processed_data = converter._process_page_content(test_data[0])
    result = converter._process_titles(processed_data)

    assert isinstance(result, list)
    # Ensure that the processing does not eliminate all entries
    assert len(result) > 0

def test_remove_duplicates():
    converter = HTMLToJsonConverter(test_data)
    processed_data = converter._process_page_content(test_data[0])
    result = converter._remove_duplicates(processed_data)

    assert isinstance(result, list)
    # Check for the presence of entries post-deduplication
    assert len(result) > 0

def test_merge_empty_structured_data():
    converter = HTMLToJsonConverter(test_data)
    processed_data = converter._process_page_content(test_data[0])
    result = converter._merge_empty_structured_data(processed_data)

    assert isinstance(result, list)
    # Verify that merging does not result in the loss of all entries
    assert len(result) > 0

