"""
Text normalization and signal detection for enrichment pipeline.
"""

import re
from typing import List, Dict, Any, Set
from app.utils.logging import log_processing_step


# Domain keyword mappings for signal detection
DOMAIN_RULES = {
    "health": [
        "diet", "craving", "calorie", "macro", "sleep", "workout", "lifting", 
        "tennis", "forehand", "serve", "fitness", "weight", "muscle", "cardio",
        "nutrition", "protein", "supplement", "exercise", "gym", "yoga"
    ],
    "money": [
        "side hustle", "gumroad", "whop", "stripe", "income", "freelance", 
        "client", "close rate", "revenue", "profit", "investment", "trading",
        "crypto", "bitcoin", "stocks", "salary", "budget", "savings", "debt"
    ],
    "dating": [
        "approach", "match", "dm", "tinder", "hinge", "conversation", "texted", 
        "date", "relationship", "girlfriend", "boyfriend", "crush", "flirting",
        "dating app", "swipe", "profile", "bumble", "okcupid"
    ],
    "career": [
        "resume", "internship", "offer", "faang", "interview", "portfolio", 
        "recruiter", "job", "career", "promotion", "salary", "company",
        "startup", "tech", "software", "engineering", "developer", "programmer"
    ],
    "productivity": [
        "deep work", "focus", "pomodoro", "notion", "calendar", "deadline", 
        "overwhelmed", "productivity", "efficiency", "time management", "task",
        "project", "goal", "planning", "organization", "schedule", "routine"
    ]
}

# Pain marker patterns
PAIN_MARKERS = {
    "struggling", "stuck", "can't", "cant", "craving", "anxious", "overwhelmed", 
    "burnout", "plateau", "frustrated", "stressed", "exhausted", "tired",
    "difficult", "hard", "impossible", "failing", "losing", "wasted", "waste",
    "terrible", "awful", "hate", "desperate", "hopeless", "lost", "confused"
}

# How-to marker patterns
HOW_TO_MARKERS = {
    "how to", "best way to", "step by step", "guide", "tutorial", "tips",
    "advice", "help", "learn", "teach", "explain", "show me", "what should",
    "recommend", "suggest", "strategy", "method", "approach", "technique"
}

# Measurable goal patterns
MEASURABLE_GOAL_PATTERNS = [
    r'\d+\s*(lbs|kg|pounds|kilograms)',
    r'\d+\s*(days|weeks|months|years)',
    r'\d+\s*(k|thousand|million)',
    r'\d+\s*%',
    r'\d+\s*(times|reps|sets)',
    r'\d+\s*(hours|minutes|seconds)',
    r'\d+\s*(miles|km|kilometers)',
    r'\d+\s*(dollars|dollars|usd)',
    r'\d+\s*(followers|subscribers|views)',
    r'\d+\s*(words|pages|chapters)'
]


def clean_text(text: str) -> str:
    """
    Clean and normalize text by removing URLs, markdown, HTML, and excessive whitespace.
    
    Args:
        text: Raw text to clean
    
    Returns:
        Cleaned text with preserved emojis and punctuation
    """
    if not text:
        return ""
    
    # Remove URLs (http/https)
    text = re.sub(r'https?://\S+', '', text)
    
    # Remove markdown links [text](url)
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    
    # Remove basic HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    
    # Remove excessive whitespace and normalize line breaks
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'\n\s*\n', '\n', text)
    
    # Strip leading/trailing whitespace
    text = text.strip()
    
    # Clip to 5000 characters to prevent memory issues
    if len(text) > 5000:
        text = text[:5000] + "..."
    
    return text


def derive_signals(title: str, body: str) -> Dict[str, Any]:
    """
    Derive signals from title and body text.
    
    Args:
        title: Item title
        body: Item body content
    
    Returns:
        Dictionary of derived signals
    """
    # Combine title and body for analysis
    combined_text = f"{title or ''} {body or ''}".lower()
    
    # Check for question
    is_question = 0
    if title and title.strip().endswith('?'):
        is_question = 1
    elif any(q in combined_text for q in ['?', 'how', 'what', 'why', 'when', 'where', 'who']):
        is_question = 1
    
    # Check for how-to markers
    how_to_markers = 1 if any(marker in combined_text for marker in HOW_TO_MARKERS) else 0
    
    # Check for pain markers
    pain_markers = 1 if any(marker in combined_text for marker in PAIN_MARKERS) else 0
    
    # Check for numbers
    has_numbers = 1 if re.search(r'\d', combined_text) else 0
    
    # Check for measurable goals
    has_measurable_goal = 0
    for pattern in MEASURABLE_GOAL_PATTERNS:
        if re.search(pattern, combined_text, re.IGNORECASE):
            has_measurable_goal = 1
            break
    
    # Derive domain tags
    domain_tags = []
    for domain, keywords in DOMAIN_RULES.items():
        if any(keyword in combined_text for keyword in keywords):
            domain_tags.append(domain)
    
    return {
        "is_question": is_question,
        "pain_markers": pain_markers,
        "how_to_markers": how_to_markers,
        "has_numbers": has_numbers,
        "has_measurable_goal": has_measurable_goal,
        "domain_tags": domain_tags
    }


@log_processing_step("normalize")
def normalize_items(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Normalize items by cleaning text and deriving signals.
    
    Args:
        items: List of items with 'title' and 'body' fields
    
    Returns:
        Items with cleaned text and added signals
    """
    if not items:
        return items
    
    for item in items:
        # Clean title and body
        item['title'] = clean_text(item.get('title', ''))
        item['body'] = clean_text(item.get('body', ''))
        
        # Derive signals
        signals = derive_signals(item.get('title', ''), item.get('body', ''))
        item['signals'] = signals
    
    return items
