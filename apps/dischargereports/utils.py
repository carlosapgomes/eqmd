import re


def clean_text_field(text):
    """
    Clean text fields for discharge reports by removing inappropriate linebreaks.
    
    Rules:
    - Remove linebreaks that are between words (not after punctuation)
    - Keep linebreaks that are after periods, exclamation marks, question marks
    - Keep intentional paragraph breaks (double linebreaks)
    - Normalize multiple spaces to single spaces
    
    Args:
        text (str): The text to clean
        
    Returns:
        str: Cleaned text with proper linebreak handling
    """
    if not text or not isinstance(text, str):
        return text
    
    # First, normalize line endings to \n
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    
    # Preserve intentional paragraph breaks (double linebreaks or more)
    # Replace them with a placeholder to protect them
    paragraph_placeholder = "<<PARAGRAPH_BREAK>>"
    text = re.sub(r'\n\s*\n+', paragraph_placeholder, text)
    
    # Remove linebreaks that are between words (not after sentence-ending punctuation)
    # This regex looks for:
    # - A word character, space, or comma before the linebreak
    # - Optional whitespace around the linebreak
    # - A word character or number after the linebreak (continuing the sentence)
    text = re.sub(r'(?<=[a-zA-Z0-9\u00C0-\u017F,\s])\s*\n\s*(?=[a-zA-Z0-9\u00C0-\u017F])', ' ', text)
    
    # Keep linebreaks after sentence-ending punctuation (.!?)
    # These are intentional sentence breaks and should be preserved
    # The regex above shouldn't touch these because they don't match the pattern
    
    # Restore paragraph breaks
    text = text.replace(paragraph_placeholder, '\n\n')
    
    # Clean up multiple spaces (but preserve intentional formatting)
    text = re.sub(r'[ ]+', ' ', text)
    
    # Clean up leading/trailing whitespace on each line
    lines = text.split('\n')
    lines = [line.strip() for line in lines]
    text = '\n'.join(lines)
    
    # Remove excessive blank lines (more than 2 consecutive)
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # Clean up leading and trailing whitespace from the entire text
    text = text.strip()
    
    return text


def clean_discharge_report_text_fields(report):
    """
    Clean all text fields in a discharge report.
    
    Args:
        report (DischargeReport): The discharge report instance
        
    Returns:
        DischargeReport: The report with cleaned text fields
    """
    # List of text fields that need cleaning
    text_fields = [
        'admission_history',
        'problems_and_diagnosis', 
        'exams_list',
        'procedures_list',
        'inpatient_medical_history',
        'discharge_status',
        'discharge_recommendations'
    ]
    
    # Clean each field
    for field_name in text_fields:
        field_value = getattr(report, field_name, '')
        if field_value:
            cleaned_value = clean_text_field(field_value)
            setattr(report, field_name, cleaned_value)
    
    return report