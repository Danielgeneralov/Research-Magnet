"""
Tests for enrichment pipeline components.
"""

import pytest
import time
from unittest.mock import patch, MagicMock
from typing import List, Dict, Any

from app.enrich.normalize import clean_text, derive_signals, normalize_items
from app.enrich.sentiment import add_sentiment
from app.enrich.nlp import extract_entities, add_entities
from app.enrich.embed import add_embeddings
from app.utils.time_decay import time_decay_weight, add_time_decay


class TestTextNormalization:
    """Test text cleaning and normalization."""
    
    def test_clean_text_basic(self):
        """Test basic text cleaning."""
        text = "Hello   world!\n\nThis is a test."
        result = clean_text(text)
        assert result == "Hello world! This is a test."
    
    def test_clean_text_urls(self):
        """Test URL removal."""
        text = "Check out https://example.com and http://test.org for more info"
        result = clean_text(text)
        assert "https://example.com" not in result
        assert "http://test.org" not in result
        assert "Check out" in result
        assert "for more info" in result
    
    def test_clean_text_markdown(self):
        """Test markdown link removal."""
        text = "See [this link](https://example.com) for details"
        result = clean_text(text)
        assert "[this link](https://example.com)" not in result
        assert "this link" in result
        assert "for details" in result
    
    def test_clean_text_html(self):
        """Test HTML tag removal."""
        text = "<p>Hello <b>world</b>!</p>"
        result = clean_text(text)
        assert "<p>" not in result
        assert "<b>" not in result
        assert "Hello world!" in result
    
    def test_clean_text_length_limit(self):
        """Test text length clipping."""
        long_text = "A" * 6000
        result = clean_text(long_text)
        assert len(result) <= 5003  # 5000 + "..."
        assert result.endswith("...")
    
    def test_clean_text_empty(self):
        """Test empty text handling."""
        assert clean_text("") == ""
        assert clean_text(None) == ""


class TestSignalDetection:
    """Test signal detection functionality."""
    
    def test_derive_signals_question(self):
        """Test question detection."""
        signals = derive_signals("How do I do this?", "")
        assert signals["is_question"] == 1
        
        signals = derive_signals("What is the best way?", "")
        assert signals["is_question"] == 1
        
        signals = derive_signals("This is a statement", "")
        assert signals["is_question"] == 0
    
    def test_derive_signals_how_to(self):
        """Test how-to marker detection."""
        signals = derive_signals("How to stop sugar cravings?", "")
        assert signals["how_to_markers"] == 1
        
        signals = derive_signals("Best way to learn programming", "")
        assert signals["how_to_markers"] == 1
        
        signals = derive_signals("I like programming", "")
        assert signals["how_to_markers"] == 0
    
    def test_derive_signals_pain_markers(self):
        """Test pain marker detection."""
        signals = derive_signals("I'm struggling with this", "")
        assert signals["pain_markers"] == 1
        
        signals = derive_signals("I can't figure this out", "")
        assert signals["pain_markers"] == 1
        
        signals = derive_signals("I love this", "")
        assert signals["pain_markers"] == 0
    
    def test_derive_signals_numbers(self):
        """Test number detection."""
        signals = derive_signals("I need 5 items", "")
        assert signals["has_numbers"] == 1
        
        signals = derive_signals("No numbers here", "")
        assert signals["has_numbers"] == 0
    
    def test_derive_signals_measurable_goals(self):
        """Test measurable goal detection."""
        signals = derive_signals("I want to lose 10 lbs", "")
        assert signals["has_measurable_goal"] == 1
        
        signals = derive_signals("I want to learn in 30 days", "")
        assert signals["has_measurable_goal"] == 1
        
        signals = derive_signals("I want to improve", "")
        assert signals["has_measurable_goal"] == 0
    
    def test_derive_signals_domain_tags(self):
        """Test domain tag detection."""
        signals = derive_signals("I need diet advice", "")
        assert "health" in signals["domain_tags"]
        
        signals = derive_signals("Side hustle income ideas", "")
        assert "money" in signals["domain_tags"]
        
        signals = derive_signals("Dating app conversation tips", "")
        assert "dating" in signals["domain_tags"]
        
        signals = derive_signals("Resume writing for FAANG", "")
        assert "career" in signals["domain_tags"]
        
        signals = derive_signals("Deep work productivity tips", "")
        assert "productivity" in signals["domain_tags"]


class TestSentimentAnalysis:
    """Test sentiment analysis functionality."""
    
    def test_add_sentiment_positive(self):
        """Test positive sentiment detection."""
        items = [{"title": "I love this!", "body": "It's amazing!"}]
        result = add_sentiment(items)
        assert result[0]["sentiment"] > 0.2
    
    def test_add_sentiment_negative(self):
        """Test negative sentiment detection."""
        items = [{"title": "I hate this", "body": "It's terrible!"}]
        result = add_sentiment(items)
        assert result[0]["sentiment"] < -0.2
    
    def test_add_sentiment_neutral(self):
        """Test neutral sentiment detection."""
        items = [{"title": "This is okay", "body": "Nothing special"}]
        result = add_sentiment(items)
        assert -0.2 <= result[0]["sentiment"] <= 0.2
    
    def test_add_sentiment_empty(self):
        """Test empty text handling."""
        items = [{"title": "", "body": ""}]
        result = add_sentiment(items)
        assert result[0]["sentiment"] == 0.0
    
    def test_add_sentiment_bounds(self):
        """Test sentiment score bounds."""
        items = [{"title": "Test", "body": "Test"}]
        result = add_sentiment(items)
        sentiment = result[0]["sentiment"]
        assert -1.0 <= sentiment <= 1.0


class TestEntityExtraction:
    """Test named entity recognition."""
    
    @patch('app.enrich.nlp._get_nlp')
    def test_extract_entities_basic(self, mock_get_nlp):
        """Test basic entity extraction."""
        # Mock spaCy model
        mock_nlp = MagicMock()
        mock_ent = MagicMock()
        mock_ent.text = "Google"
        mock_ent.label_ = "ORG"
        mock_doc = MagicMock()
        mock_doc.ents = [mock_ent]
        mock_nlp.return_value = mock_doc
        mock_get_nlp.return_value = mock_nlp
        
        entities = extract_entities("I work at Google")
        assert len(entities) == 1
        assert entities[0]["text"] == "Google"
        assert entities[0]["label"] == "ORG"
    
    def test_extract_entities_empty(self):
        """Test empty text handling."""
        entities = extract_entities("")
        assert entities == []
    
    def test_extract_entities_long_text(self):
        """Test text length clipping."""
        long_text = "A" * 4000
        with patch('app.enrich.nlp._get_nlp') as mock_get_nlp:
            mock_nlp = MagicMock()
            mock_doc = MagicMock()
            mock_doc.ents = []
            mock_nlp.return_value = mock_doc
            mock_get_nlp.return_value = mock_nlp
            
            entities = extract_entities(long_text)
            # Should not raise error
            assert entities == []


class TestEmbeddings:
    """Test text embedding functionality."""
    
    @patch('app.enrich.embed._get_model')
    def test_add_embeddings_basic(self, mock_get_model):
        """Test basic embedding generation."""
        # Mock sentence transformer model
        import numpy as np
        mock_model = MagicMock()
        mock_model.encode.return_value = np.array([[0.1, 0.2, 0.3]])  # Use numpy array
        mock_model.get_sentence_embedding_dimension.return_value = 3
        mock_get_model.return_value = mock_model
        
        items = [{"title": "Test title", "body": "Test body"}]
        result = add_embeddings(items)
        
        assert "embedding" in result[0]
        assert len(result[0]["embedding"]) == 3
        assert result[0]["embedding"] == [0.1, 0.2, 0.3]
    
    @patch('app.enrich.embed._get_model')
    def test_add_embeddings_empty_text(self, mock_get_model):
        """Test embedding generation for empty text."""
        mock_model = MagicMock()
        mock_model.get_sentence_embedding_dimension.return_value = 3
        mock_get_model.return_value = mock_model
        
        items = [{"title": "", "body": ""}]
        result = add_embeddings(items)
        
        assert "embedding" in result[0]
        assert len(result[0]["embedding"]) == 3
        assert all(x == 0.0 for x in result[0]["embedding"])
    
    @patch('app.enrich.embed._get_model')
    def test_add_embeddings_batch_processing(self, mock_get_model):
        """Test batch processing for embeddings."""
        mock_model = MagicMock()
        mock_model.encode.return_value = [[0.1, 0.2, 0.3]] * 5
        mock_model.get_sentence_embedding_dimension.return_value = 3
        mock_get_model.return_value = mock_model
        
        items = [{"title": f"Test {i}", "body": f"Body {i}"} for i in range(5)]
        result = add_embeddings(items, batch_size=2)
        
        assert len(result) == 5
        for item in result:
            assert "embedding" in item
            assert len(item["embedding"]) == 3


class TestTimeDecay:
    """Test time decay functionality."""
    
    def test_time_decay_weight_recent(self):
        """Test time decay for recent items."""
        current_time = time.time()
        weight = time_decay_weight(current_time - 3600, 72)  # 1 hour ago
        assert weight > 0.9  # Should be very close to 1
    
    def test_time_decay_weight_old(self):
        """Test time decay for old items."""
        current_time = time.time()
        weight = time_decay_weight(current_time - 72 * 3600, 72)  # 72 hours ago
        assert abs(weight - 0.5) < 0.1  # Should be close to 0.5
    
    def test_time_decay_weight_very_old(self):
        """Test time decay for very old items."""
        current_time = time.time()
        weight = time_decay_weight(current_time - 168 * 3600, 72)  # 1 week ago
        assert weight < 0.3  # Should be small (2.33 half-lives = ~0.198)
    
    def test_time_decay_weight_unknown(self):
        """Test time decay for unknown timestamps."""
        weight = time_decay_weight(None, 72)
        assert weight == 0.5  # Should default to 0.5
    
    def test_time_decay_weight_bounds(self):
        """Test time decay weight bounds."""
        current_time = time.time()
        
        # Test various ages
        for hours_ago in [0, 1, 24, 72, 168]:
            weight = time_decay_weight(current_time - hours_ago * 3600, 72)
            assert 0.0 <= weight <= 1.0
    
    def test_add_time_decay(self):
        """Test adding time decay to items."""
        current_time = time.time()
        items = [
            {"created_utc": current_time - 3600},  # 1 hour ago
            {"created_utc": current_time - 72 * 3600},  # 72 hours ago
            {"created_utc": None},  # Unknown
        ]
        
        result = add_time_decay(items, 72)
        
        assert "time_decay_weight" in result[0]
        assert "time_decay_weight" in result[1]
        assert "time_decay_weight" in result[2]
        
        assert result[0]["time_decay_weight"] > result[1]["time_decay_weight"]
        assert result[2]["time_decay_weight"] == 0.5


class TestIntegration:
    """Test integration of enrichment components."""
    
    def test_normalize_items_integration(self):
        """Test normalize_items integration."""
        items = [
            {
                "title": "How to stop sugar cravings in 14 days?",
                "body": "I'm struggling with sugar cravings and need help!"
            }
        ]
        
        result = normalize_items(items)
        
        assert len(result) == 1
        assert "signals" in result[0]
        signals = result[0]["signals"]
        
        assert signals["is_question"] == 1
        assert signals["how_to_markers"] == 1
        assert signals["pain_markers"] == 1
        assert signals["has_numbers"] == 1
        assert signals["has_measurable_goal"] == 1
        assert "health" in signals["domain_tags"]
    
    def test_empty_items_handling(self):
        """Test handling of empty item lists."""
        assert normalize_items([]) == []
        assert add_sentiment([]) == []
        assert add_entities([]) == []
        assert add_embeddings([]) == []
        assert add_time_decay([]) == []
    
    def test_malformed_items_handling(self):
        """Test handling of malformed items."""
        items = [
            {},  # Empty item
            {"title": None, "body": None},  # None values
            {"title": "Valid title", "body": "Valid body"},  # Valid item
        ]
        
        # Should not raise exceptions
        result = normalize_items(items)
        assert len(result) == 3
        
        result = add_sentiment(items)
        assert len(result) == 3
        
        result = add_entities(items)
        assert len(result) == 3
        
        result = add_time_decay(items)
        assert len(result) == 3


if __name__ == "__main__":
    pytest.main([__file__])
