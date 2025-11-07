import sys
sys.path.insert(0, '/app')

from app.data_insights.embeddings import get_embedding, bulk_embed
from app.data_insights.text_analysis import analyze_sentiment, extract_keywords
from app.core.config import settings


def test_get_embedding():
    """Test embedding generation"""
    print("\n=== Test: get_embedding ===")
    text = "Este es un texto de prueba para generar embeddings"
    embedding = get_embedding(text)
    
    assert isinstance(embedding, list), "Embedding debe ser una lista"
    assert len(embedding) == settings.PGVECTOR_DIM, f"Dimensión incorrecta: {len(embedding)} != {settings.PGVECTOR_DIM}"
    assert all(isinstance(x, float) for x in embedding), "Todos los elementos deben ser float"
    print(f"✓ Embedding generado: {len(embedding)} dimensiones")


def test_bulk_embed():
    """Test batch embedding"""
    print("\n=== Test: bulk_embed ===")
    texts = [
        "Texto uno",
        "Texto dos",
        "Texto tres"
    ]
    embeddings = bulk_embed(texts)
    
    assert len(embeddings) == 3, "Debe retornar 3 embeddings"
    assert all(len(emb) == settings.PGVECTOR_DIM for emb in embeddings), "Todas las dimensiones deben coincidir"
    print(f"✓ Batch embedding: {len(embeddings)} vectores generados")


def test_analyze_sentiment():
    """Test sentiment analysis"""
    print("\n=== Test: analyze_sentiment ===")
    positive_text = "Este producto es excelente y fantástico"
    negative_text = "Terrible experiencia, muy malo"
    neutral_text = "El producto tiene características estándar"
    
    pos_result = analyze_sentiment(positive_text)
    neg_result = analyze_sentiment(negative_text)
    neu_result = analyze_sentiment(neutral_text)
    
    assert pos_result["label"] == "positive", f"Texto positivo clasificado como {pos_result['label']}"
    assert pos_result["polarity"] > 0, "Polaridad positiva debe ser > 0"
    assert neg_result["label"] == "negative", f"Texto negativo clasificado como {neg_result['label']}"
    assert neg_result["polarity"] < 0, "Polaridad negativa debe ser < 0"
    assert -1.0 <= neu_result["polarity"] <= 1.0, "Polaridad fuera de rango"
    
    print(f"✓ Sentiment positivo: {pos_result}")
    print(f"✓ Sentiment negativo: {neg_result}")
    print(f"✓ Sentiment neutral: {neu_result}")


def test_extract_keywords():
    """Test keyword extraction"""
    print("\n=== Test: extract_keywords ===")
    text = """
    La inteligencia artificial y el machine learning están transformando
    la industria tecnológica. Las empresas como Google y Microsoft
    invierten millones en investigación y desarrollo.
    """
    
    keywords = extract_keywords(text)
    
    assert isinstance(keywords, list), "Keywords debe ser una lista"
    assert len(keywords) > 0, "Debe extraer al menos 1 keyword"
    assert len(keywords) <= 10, f"Debe extraer máximo 10 keywords, obtuvo {len(keywords)}"
    assert all(isinstance(kw, str) for kw in keywords), "Todas las keywords deben ser strings"
    
    print(f"✓ Keywords extraídas: {keywords}")


if __name__ == "__main__":
    print("\n" + "="*50)
    print("Testing Text Analysis Module")
    print("="*50)
    
    try:
        test_get_embedding()
        test_bulk_embed()
        test_analyze_sentiment()
        test_extract_keywords()
        
        print("\n" + "="*50)
        print("✓ TODOS LOS TESTS PASARON CORRECTAMENTE")
        print("="*50 + "\n")
    except Exception as e:
        print(f"\n✗ ERROR: {str(e)}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)
