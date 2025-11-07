"""
Script para probar análisis de sentimiento con Ollama
"""
import sys
sys.path.insert(0, '.')

from app.services.text_analysis import analyze_sentiment_with_ollama, analyze_text_batch
from app.services.ollama_service import ollama_service

def test_sentiment_analysis():
    print("🔍 Probando análisis de sentimiento con Ollama...\n")
    
    # Verificar disponibilidad de Ollama
    print("=" * 60)
    print("VERIFICANDO DISPONIBILIDAD DE OLLAMA")
    print("=" * 60)
    
    is_available = ollama_service.is_available()
    print(f"Ollama disponible: {'✅ Sí' if is_available else '❌ No'}")
    
    if not is_available:
        print("⚠️  Ollama no está disponible. Se usará método fallback.")
        print("   Para iniciar Ollama: ollama serve")
    
    print()
    
    # Textos de prueba
    test_texts = [
        "Este producto es excelente, superó todas mis expectativas. Lo recomiendo totalmente.",
        "Muy decepcionado con la compra. Mala calidad y servicio pésimo.",
        "El producto llegó en buen estado, cumple con lo prometido.",
        "No estoy satisfecho, esperaba mucho más por el precio que pagué.",
        "Increíble! La mejor compra que he hecho en años. Totalmente satisfecho.",
        "Regular, nada especial. No es malo pero tampoco bueno.",
    ]
    
    # Test 1: Análisis individual con Ollama
    print("=" * 60)
    print("TEST 1: ANÁLISIS INDIVIDUAL CON OLLAMA")
    print("=" * 60)
    
    for i, text in enumerate(test_texts[:3], 1):
        print(f"\n📝 Texto {i}: {text[:80]}...")
        
        # Con Ollama
        result_ollama = analyze_sentiment_with_ollama(text, use_ollama=True)
        print(f"   Método: {result_ollama['method']}")
        print(f"   Positivo: {result_ollama['positive']:.3f}")
        print(f"   Negativo: {result_ollama['negative']:.3f}")
        print(f"   Neutral: {result_ollama['neutral']:.3f}")
        print(f"   Confianza: {result_ollama['confidence']:.3f}")
    
    # Test 2: Análisis en batch
    print("\n" + "=" * 60)
    print("TEST 2: ANÁLISIS EN BATCH")
    print("=" * 60)
    
    results = analyze_text_batch(test_texts, use_ollama=is_available)
    
    print(f"\n✅ Analizados {len(results)} textos")
    
    # Estadísticas
    methods = {}
    for r in results:
        method = r['sentiment_method']
        methods[method] = methods.get(method, 0) + 1
    
    print(f"\n📊 Métodos utilizados:")
    for method, count in methods.items():
        print(f"   - {method}: {count} textos")
    
    avg_confidence = sum(r['sentiment_confidence'] for r in results) / len(results)
    print(f"\n📈 Confianza promedio: {avg_confidence:.3f}")
    
    # Mostrar algunos resultados
    print(f"\n🎯 Primeros 3 resultados detallados:")
    for i, result in enumerate(results[:3], 1):
        print(f"\n   {i}. {result['text'][:60]}...")
        print(f"      Sentimiento: P:{result['sentiment']['positive']:.2f} "
              f"N:{result['sentiment']['negative']:.2f} "
              f"Ne:{result['sentiment']['neutral']:.2f}")
        print(f"      Keywords: {', '.join(result['keywords'][:5])}")
        print(f"      Método: {result['sentiment_method']} (confianza: {result['sentiment_confidence']:.2f})")
    
    # Test 3: Comparación Ollama vs Fallback
    print("\n" + "=" * 60)
    print("TEST 3: COMPARACIÓN OLLAMA VS FALLBACK")
    print("=" * 60)
    
    comparison_text = "Este producto es absolutamente fantástico, la mejor compra del año!"
    
    print(f"\n📝 Texto: {comparison_text}")
    
    # Con Ollama
    result_ollama = analyze_sentiment_with_ollama(comparison_text, use_ollama=True)
    print(f"\n🤖 Con Ollama ({result_ollama['method']}):")
    print(f"   Positivo: {result_ollama['positive']:.3f}")
    print(f"   Negativo: {result_ollama['negative']:.3f}")
    print(f"   Neutral: {result_ollama['neutral']:.3f}")
    print(f"   Confianza: {result_ollama['confidence']:.3f}")
    
    # Sin Ollama (fallback)
    result_fallback = analyze_sentiment_with_ollama(comparison_text, use_ollama=False)
    print(f"\n📚 Con Fallback ({result_fallback['method']}):")
    print(f"   Positivo: {result_fallback['positive']:.3f}")
    print(f"   Negativo: {result_fallback['negative']:.3f}")
    print(f"   Neutral: {result_fallback['neutral']:.3f}")
    print(f"   Confianza: {result_fallback['confidence']:.3f}")
    
    print("\n" + "=" * 60)
    print("✅ PRUEBAS COMPLETADAS")
    print("=" * 60)


if __name__ == "__main__":
    test_sentiment_analysis()
