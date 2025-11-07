import ollama
from typing import Dict, Any, Optional

from app.config import get_settings
from app.logger import get_logger

settings = get_settings()
logger = get_logger()


class OllamaService:
    """Servicio para interactuar con Ollama (IA local)"""
    
    def __init__(self):
        self.base_url = settings.OLLAMA_BASE_URL
        self.model = settings.OLLAMA_MODEL
        self.client = None
    
    def _get_client(self):
        """Obtener cliente de Ollama"""
        if self.client is None:
            try:
                self.client = ollama.Client(host=self.base_url)
                logger.info(f"Cliente Ollama conectado: {self.base_url}")
            except Exception as e:
                logger.error(f"Error conectando con Ollama: {e}")
                raise
        return self.client
    
    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Generar texto con Ollama"""
        try:
            client = self._get_client()
            
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            
            messages.append({"role": "user", "content": prompt})
            
            response = client.chat(
                model=self.model,
                messages=messages,
            )
            
            return response['message']['content']
            
        except Exception as e:
            logger.error(f"Error generando con Ollama: {e}")
            raise
    
    def classify_text(self, text: str, categories: list) -> Dict[str, Any]:
        """Clasificar texto en categorías"""
        system_prompt = """Eres un clasificador de texto experto. 
        Analiza el texto y clasifícalo en una de las categorías proporcionadas.
        Responde solo con el nombre de la categoría y un score de confianza entre 0 y 1."""
        
        prompt = f"""Texto: {text}
        
Categorías disponibles: {', '.join(categories)}

Clasifica el texto en una de estas categorías y proporciona un score de confianza.
Formato de respuesta: categoria|score"""
        
        try:
            response = self.generate(prompt, system_prompt)
            
            # Parse respuesta
            parts = response.strip().split("|")
            if len(parts) >= 2:
                category = parts[0].strip()
                score = float(parts[1].strip())
            else:
                category = categories[0]
                score = 0.5
            
            return {
                "category": category,
                "confidence": score,
                "raw_response": response,
            }
            
        except Exception as e:
            logger.error(f"Error clasificando texto: {e}")
            return {
                "category": categories[0],
                "confidence": 0.0,
                "error": str(e),
            }
    
    def extract_insights(self, text: str) -> str:
        """Extraer insights de texto"""
        system_prompt = """Eres un analista de datos experto.
        Analiza el texto y extrae los insights más importantes."""
        
        prompt = f"""Analiza el siguiente texto y extrae los insights principales:

{text}

Proporciona un resumen ejecutivo conciso."""
        
        return self.generate(prompt, system_prompt)


# Singleton
ollama_service = OllamaService()
