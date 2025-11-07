"""
Script para verificar conexión con Ollama
"""
import sys
sys.path.insert(0, '.')

from app.services.ollama_service import ollama_service

def test_ollama():
    print("🔍 Probando conexión con Ollama...")
    
    try:
        response = ollama_service.generate("¿Estás funcionando correctamente?")
        print(f"✅ Ollama respondió: {response[:100]}...")
        
        # Test clasificación
        categories = ["positivo", "negativo", "neutral"]
        result = ollama_service.classify_text(
            "Este producto es excelente, muy recomendado",
            categories
        )
        print(f"✅ Clasificación: {result}")
        
    except Exception as e:
        print(f"❌ Error conectando con Ollama: {e}")
        print("Asegúrese de que Ollama esté corriendo:")
        print("  ollama serve")


if __name__ == "__main__":
    test_ollama()
