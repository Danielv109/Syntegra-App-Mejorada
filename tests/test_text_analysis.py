import pytest
from app.data_insights.embeddings import get_embedding, bulk_embed
from app.data_insights.text_analysis import analyze_sentiment, extract_keywords
from app.core.config import settings


def test_get_embedding():
    """Test embedding generation"""
    text = "Este es un texto de prueba para generar embeddings"
    embedding = get_embedding(text)
    
    assert isinstance(embedding, list)
    assert len(embedding) == settings.PGVECTOR_DIM
    assert all(isinstance(x, float) for x in embedding)
    print(f"✓ Embedding generado: {len(embedding)} dimensiones")


def test_bulk_embed():
    """Test batch embedding"""
    texts = [
        "Texto uno",
        "Texto dos",
        "Texto tres"
    ]
    embeddings = bulk_embed(texts)
    
    assert len(embeddings) == 3
    assert all(len(emb) == settings.PGVECTOR_DIM for emb in embeddings)
    print(f"✓ Batch embedding: {len(embeddings)} vectores generados")


def test_analyze_sentiment():
    """Test sentiment analysis"""
    positive_text = "Este producto es excelente y fantástico"
    negative_text = "Terrible experiencia, muy malo"
    neutral_text = "El producto tiene características estándar"
    
    pos_result = analyze_sentiment(positive_text)
    neg_result = analyze_sentiment(negative_text)
    neu_result = analyze_sentiment(neutral_text)
    
    assert pos_result["label"] == "positive"
    assert pos_result["polarity"] > 0
    assert neg_result["label"] == "negative"
    assert neg_result["polarity"] < 0
    assert neu_result["polarity"] >= -1.0 and neu_result["polarity"] <= 1.0
    
    print(f"✓ Sentiment analysis: positive={pos_result}, negative={neg_result}")


def test_extract_keywords():
    """Test keyword extraction"""
    text = """
    La inteligencia artificial y el machine learning están transformando
    la industria tecnológica. Las empresas como Google y Microsoft
    invierten millones en investigación y desarrollo.
    """
    
    keywords = extract_keywords(text)
    
    assert isinstance(keywords, list)
    assert len(keywords) > 0
    assert len(keywords) <= 10
    assert all(isinstance(kw, str) for kw in keywords)
    
    print(f"✓ Keywords extraídas: {keywords}")


if __name__ == "__main__":
    print("\n=== Testing Text Analysis Module ===\n")
    test_get_embedding()
    test_bulk_embed()
    test_analyze_sentiment()
    test_extract_keywords()
    print("\n✓ Todos los tests pasaron correctamente\n")
