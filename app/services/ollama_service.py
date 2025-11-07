import ollama
from typing import Dict, Any, Optional
import time

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
        self._is_available = None
        self._last_check = 0
        self._check_interval = 60  # Verificar disponibilidad cada 60 segundos
    
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
    
    def is_available(self) -> bool:
        """Verificar si Ollama está disponible"""
        
        # Cache de disponibilidad para no verificar en cada llamada
        current_time = time.time()
        if self._is_available is not None and (current_time - self._last_check) < self._check_interval:
            return self._is_available
        
        try:
            client = self._get_client()
            # Intentar listar modelos como verificación
            client.list()
            self._is_available = True
            self._last_check = current_time
            logger.debug("Ollama disponible")
            return True
        except Exception as e:
            logger.warning(f"Ollama no disponible: {e}")
            self._is_available = False
            self._last_check = current_time
            return False
    
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 500,
    ) -> str:
        """Generar texto con Ollama"""
        
        if not self.is_available():
            raise ConnectionError("Ollama no está disponible")
        
        try:
            client = self._get_client()
            
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            
            messages.append({"role": "user", "content": prompt})
            
            response = client.chat(
                model=self.model,
                messages=messages,
                options={
                    'temperature': temperature,
                    'num_predict': max_tokens,
                }
            )
            
            return response['message']['content']
            
        except Exception as e:
            logger.error(f"Error generando con Ollama: {e}")
            raise
    
    def classify_text(
        self,
        text: str,
        categories: list,
        temperature: float = 0.3,
    ) -> Dict[str, Any]:
        """
        Clasificar texto en categorías usando Ollama
        
        Args:
            text: Texto a clasificar
            categories: Lista de categorías posibles
            temperature: Temperatura del modelo (menor = más determinístico)
            
        Returns:
            Dict con categoria, confidence y raw_response
        """
        
        system_prompt = """Eres un clasificador de texto experto y preciso.
Analiza el texto y clasifícalo en una de las categorías proporcionadas.
Responde SOLO con el nombre de la categoría seguido de un pipe "|" y un número entre 0 y 1 indicando tu confianza.
Formato exacto: categoria|score
Ejemplo: positivo|0.85"""
        
        prompt = f"""Texto a clasificar: "{text}"

Categorías disponibles: {', '.join(categories)}

Clasificación:"""
        
        try:
            start_time = time.time()
            response = self.generate(prompt, system_prompt, temperature=temperature, max_tokens=50)
            elapsed_time = time.time() - start_time
            
            logger.debug(f"Ollama respondió en {elapsed_time:.2f}s: {response[:100]}")
            
            # Parse respuesta
            response = response.strip()
            
            # Buscar patrón categoria|score
            if '|' in response:
                parts = response.split('|')
                category = parts[0].strip().lower()
                try:
                    score = float(parts[1].strip())
                    score = max(0.0, min(1.0, score))  # Clamp entre 0 y 1
                except:
                    score = 0.5
            else:
                # Buscar categoría en la respuesta
                response_lower = response.lower()
                category = None
                for cat in categories:
                    if cat.lower() in response_lower:
                        category = cat.lower()
                        break
                
                if category is None:
                    category = categories[0].lower()
                
                score = 0.5
            
            # Validar que la categoría sea válida
            valid_categories = [c.lower() for c in categories]
            if category not in valid_categories:
                logger.warning(f"Categoría inválida '{category}', usando primera categoría")
                category = categories[0].lower()
            
            return {
                "category": category,
                "confidence": score,
                "raw_response": response,
                "elapsed_time": elapsed_time,
            }
            
        except Exception as e:
            logger.error(f"Error clasificando texto: {e}")
            return {
                "category": categories[0].lower(),
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
    
    def analyze_sentiment_detailed(self, text: str) -> Dict[str, Any]:
        """
        Análisis de sentimiento detallado usando Ollama
        
        Returns:
            Dict con sentiment, confidence, reasoning
        """
        
        system_prompt = """Eres un experto en análisis de sentimiento.
Analiza el texto y proporciona:
1. Sentimiento (positivo, negativo, neutral)
2. Confianza (0.0 a 1.0)
3. Breve explicación

Formato: sentimiento|confianza|explicación"""
        
        prompt = f"""Analiza el sentimiento de este texto:

"{text}"

Análisis:"""
        
        try:
            response = self.generate(prompt, system_prompt, temperature=0.3, max_tokens=100)
            
            parts = response.split('|')
            if len(parts) >= 3:
                sentiment = parts[0].strip().lower()
                confidence = float(parts[1].strip())
                reasoning = parts[2].strip()
            else:
                # Fallback parsing
                sentiment = 'neutral'
                confidence = 0.5
                reasoning = response
            
            return {
                'sentiment': sentiment,
                'confidence': confidence,
                'reasoning': reasoning,
                'raw_response': response,
            }
            
        except Exception as e:
            logger.error(f"Error en análisis de sentimiento detallado: {e}")
            return {
                'sentiment': 'neutral',
                'confidence': 0.0,
                'reasoning': '',
                'error': str(e),
            }


# Singleton
ollama_service = OllamaService()
