"""
Profanity filter module for Hamilton TMS
Filters inappropriate content from user inputs
"""

import re

# Focused list of clearly inappropriate words/phrases to filter
# This list is conservative to avoid false positives with legitimate names and content
PROFANITY_LIST = [
    # Clear profanity - standalone words only
    'fuck', 'fucking', 'fucked', 'fucker', 'shit', 'shitting', 'shitty',
    'bitch', 'bastard', 'asshole', 'arsehole', 'dickhead', 'twat', 'cunt',
    
    # Highly offensive discriminatory language - standalone words only
    'nigger', 'nigga', 'faggot',
    
    # Explicit sexual content - only clearly inappropriate terms
    'masturbate', 'orgasm',
    
    # Clear violent threats - only specific threatening language
    'murder', 'suicide',
    
    # Hard drugs - only illegal substances
    'cocaine', 'heroin',
    
    # Common variations and leetspeak
    'f*ck', 'f**k', 'sh1t', 'fuk', 'shyt', 'f4ck', 'sh!t'
]

def contains_profanity(text):
    """
    Check if text contains profanity
    Returns tuple (bool, list_of_found_words)
    Conservative approach to avoid flagging legitimate names and content
    """
    if not text or not isinstance(text, str):
        return False, []
    
    # Convert to lowercase for checking
    text_lower = text.lower()
    found_words = []
    
    # Check each word in profanity list
    for word in PROFANITY_LIST:
        # Use word boundaries to avoid false positives with names
        # Only flag standalone words, not parts of legitimate words
        pattern = r'\b' + re.escape(word) + r'\b'
        if re.search(pattern, text_lower):
            found_words.append(word)
    
    return len(found_words) > 0, found_words

def filter_profanity(text, replacement="***"):
    """
    Replace profanity in text with replacement characters
    Returns cleaned text
    """
    if not text or not isinstance(text, str):
        return text
    
    cleaned_text = text
    
    # Replace each profane word
    for word in PROFANITY_LIST:
        # Replace with word boundaries
        pattern = r'\b' + re.escape(word) + r'\b'
        cleaned_text = re.sub(pattern, replacement, cleaned_text, flags=re.IGNORECASE)
    
    return cleaned_text

def validate_text_input(text, field_name="text"):
    """
    Validate text input for profanity
    Returns tuple (is_valid, error_message)
    """
    has_profanity, found_words = contains_profanity(text)
    
    if has_profanity:
        if len(found_words) == 1:
            return False, f"The {field_name} contains inappropriate language. Please revise your input."
        else:
            return False, f"The {field_name} contains inappropriate language. Please revise your input."
    
    return True, None

def sanitize_input(text):
    """
    Clean and sanitize text input by removing profanity and trimming whitespace
    """
    if not text or not isinstance(text, str):
        return text
    
    # First trim whitespace
    cleaned = text.strip()
    
    # Then filter profanity
    cleaned = filter_profanity(cleaned)
    
    return cleaned

# Additional validation for educational context
def validate_educational_content(text, field_name="content"):
    """
    Special validation for educational content that should be more strict
    """
    # First check standard profanity
    is_valid, error_msg = validate_text_input(text, field_name)
    
    if not is_valid:
        return is_valid, error_msg
    
    # Additional checks for educational inappropriate content
    inappropriate_educational = [
        'violent', 'violence', 'inappropriate', 'bullying', 'bully',
        'harassment', 'discriminat', 'racist', 'sexist'
    ]
    
    text_lower = text.lower()
    found_inappropriate = []
    
    for word in inappropriate_educational:
        if word in text_lower:
            found_inappropriate.append(word)
    
    if found_inappropriate:
        return False, f"The {field_name} contains content that may be inappropriate for a school environment. Please revise your input."
    
    return True, None