import spacy
from typing import List, Dict, Any, Optional
from collections import Counter
import re
from sentence_transformers import SentenceTransformer
import time

from app.services.ollama_service import ollama_service
from app.logger import get_logger

logger = get_logger()

# Cargar modelos (se cachean automáticamente)
try:
    nlp = spacy.load("es_core_news_sm")
    logger.info("Modelo de spaCy cargado correctamente")
except:
    logger.warning("Modelo de spaCy no encontrado, ejecute: python -m spacy download es_core_news_sm")
    nlp = None

# Modelo para embeddings
embedding_model = None


def get_embedding_model():
    """Obtener modelo de embeddings (lazy loading)"""
    global embedding_model
    if embedding_model is None:
        logger.info("Cargando modelo de embeddings...")
        embedding_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
    return embedding_model


def analyze_sentiment_with_ollama(
    text: str,
    use_ollama: bool = True,
    timeout: int = 10
) -> Dict[str, float]:
    """
    Analizar sentimiento usando Ollama (IA local) con fallback
    
    Args:
        text: Texto a analizar
        use_ollama: Si debe intentar usar Ollama
        timeout: Timeout para la respuesta de Ollama (segundos)
        
    Returns:
        Dict con scores de sentimiento (positive, negative, neutral)
    """
    
    # Intentar con Ollama si está habilitado
    if use_ollama:
        try:
            logger.debug(f"Analizando sentimiento con Ollama: {text[:50]}...")
            
            categories = ["positivo", "negativo", "neutral"]
            
            # Clasificar con Ollama
            start_time = time.time()
            result = ollama_service.classify_text(text, categories)
            elapsed_time = time.time() - start_time
            
            if elapsed_time > timeout:
                logger.warning(f"Ollama tardó {elapsed_time:.2f}s (timeout: {timeout}s), usando fallback")
                return _analyze_sentiment_fallback(text)
            
            # Mapear categoría a scores
            category = result.get('category', 'neutral').lower()
            confidence = result.get('confidence', 0.5)
            
            if category == 'positivo':
                return {
                    'positive': confidence,
                    'negative': (1 - confidence) * 0.3,
                    'neutral': (1 - confidence) * 0.7,
                    'method': 'ollama',
                    'confidence': confidence,
                }
            elif category == 'negativo':
                return {
                    'positive': (1 - confidence) * 0.3,
                    'negative': confidence,
                    'neutral': (1 - confidence) * 0.7,
                    'method': 'ollama',
                    'confidence': confidence,
                }
            else:  # neutral
                return {
                    'positive': 0.3,
                    'negative': 0.3,
                    'neutral': confidence,
                    'method': 'ollama',
                    'confidence': confidence,
                }
                
        except Exception as e:
            logger.warning(f"Error usando Ollama para sentimiento: {e}, usando fallback")
            return _analyze_sentiment_fallback(text)
    
    # Usar método fallback si Ollama está deshabilitado
    return _analyze_sentiment_fallback(text)


def _analyze_sentiment_fallback(text: str) -> Dict[str, float]:
    """
    Análisis de sentimiento fallback usando diccionarios y reglas
    (Se usa cuando Ollama no está disponible o falla)
    """
    
    # Diccionarios expandidos de palabras
    positive_words = {
        'excelente', 'bueno', 'genial', 'increíble', 'fantástico',
        'maravilloso', 'perfecto', 'satisfecho', 'feliz', 'contento',
        'amor', 'encanta', 'fascina', 'hermoso', 'mejor', 'éxito',
        'alegría', 'satisfacción', 'calidad', 'recomendado', 'útil',
        'efectivo', 'rápido', 'eficiente', 'profesional', 'amable',
        'excepcional', 'sobresaliente', 'magnífico', 'espectacular',
        'brillante', 'positivo', 'beneficio', 'ventaja', 'ganancia',
    }
    
    negative_words = {
        'malo', 'pésimo', 'terrible', 'horrible', 'decepcionante',
        'insatisfecho', 'triste', 'enojado', 'frustrado', 'molesto',
        'deficiente', 'defectuoso', 'roto', 'problema', 'error',
        'lento', 'caro', 'ineficiente', 'desagradable', 'pobre',
        'fracaso', 'fallo', 'pérdida', 'desventaja', 'negativo',
        'difícil', 'complicado', 'confuso', 'incómodo', 'inadecuado',
        'inaceptable', 'desastre', 'mediocre', 'inferior', 'débil',
    }
    
    # Intensificadores
    intensifiers = {
        'muy', 'súper', 'extremadamente', 'totalmente', 'completamente',
        'absolutamente', 'increíblemente', 'extraordinariamente',
    }
    
    # Negaciones
    negations = {
        'no', 'nunca', 'jamás', 'tampoco', 'ningún', 'ninguno', 'nada',
    }
    
    text_lower = text.lower()
    words = re.findall(r'\w+', text_lower)
    
    positive_count = 0
    negative_count = 0
    intensifier_multiplier = 1.0
    negation_active = False
    
    for i, word in enumerate(words):
        # Detectar intensificadores
        if word in intensifiers:
            intensifier_multiplier = 1.5
            continue
        
        # Detectar negaciones
        if word in negations:
            negation_active = True
            continue
        
        # Contar palabras positivas/negativas
        if word in positive_words:
            if negation_active:
                negative_count += intensifier_multiplier
                negation_active = False
            else:
                positive_count += intensifier_multiplier
        elif word in negative_words:
            if negation_active:
                positive_count += intensifier_multiplier
                negation_active = False
            else:
                negative_count += intensifier_multiplier
        
        # Reset de multiplicadores
        if word not in intensifiers and word not in negations:
            intensifier_multiplier = 1.0
    
    total = positive_count + negative_count
    
    if total == 0:
        return {
            'positive': 0.33,
            'negative': 0.33,
            'neutral': 0.34,
            'method': 'fallback',
            'confidence': 0.5,
        }
    
    positive_score = positive_count / total if total > 0 else 0
    negative_score = negative_count / total if total > 0 else 0
    neutral_score = 1 - (positive_score + negative_score)
    
    # Ajustar para que sumen 1.0
    total_score = positive_score + negative_score + neutral_score
    if total_score > 0:
        positive_score /= total_score
        negative_score /= total_score
        neutral_score /= total_score
    
    return {
        'positive': round(positive_score, 3),
        'negative': round(negative_score, 3),
        'neutral': round(neutral_score, 3),
        'method': 'fallback',
        'confidence': min(total / 10, 1.0),  # Confianza basada en cantidad de palabras
    }


def analyze_sentiment_batch_with_ollama(
    texts: List[str],
    use_ollama: bool = True,
    batch_size: int = 10,
    max_workers: int = 3,
) -> List[Dict[str, Any]]:
    """
    Analizar sentimiento en batch con Ollama
    
    Args:
        texts: Lista de textos
        use_ollama: Si debe usar Ollama
        batch_size: Tamaño de batch para procesamiento paralelo
        max_workers: Número máximo de workers paralelos
        
    Returns:
        Lista de resultados de análisis
    """
    results = []
    
    logger.info(f"Analizando sentimiento de {len(texts)} textos con Ollama: {use_ollama}")
    
    # Procesar en batches para optimizar
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        
        for text in batch:
            try:
                sentiment = analyze_sentiment_with_ollama(text, use_ollama=use_ollama)
                results.append(sentiment)
            except Exception as e:
                logger.error(f"Error analizando texto: {e}")
                # Usar fallback en caso de error
                results.append(_analyze_sentiment_fallback(text))
        
        # Log de progreso
        if (i + batch_size) % 50 == 0:
            logger.info(f"Progreso: {min(i + batch_size, len(texts))}/{len(texts)} textos procesados")
    
    # Estadísticas de métodos usados
    methods_used = Counter([r['method'] for r in results])
    logger.info(f"Métodos usados: {dict(methods_used)}")
    
    return results


def extract_keywords(text: str, top_n: int = 10) -> List[str]:
    """Extraer palabras clave usando spaCy"""
    if not nlp:
        # Fallback simple
        words = re.findall(r'\w+', text.lower())
        return [word for word, count in Counter(words).most_common(top_n)]
    
    doc = nlp(text)
    
    # Extraer sustantivos y adjetivos
    keywords = [
        token.lemma_ for token in doc
        if token.pos_ in ["NOUN", "ADJ"] and not token.is_stop and len(token.text) > 3
    ]
    
    # Contar frecuencias
    keyword_counts = Counter(keywords)
    
    return [word for word, count in keyword_counts.most_common(top_n)]


def extract_entities_with_ollama(
    text: str,
    use_ollama: bool = True,
) -> List[Dict[str, str]]:
    """
    Extraer entidades nombradas usando Ollama o spaCy
    
    Returns:
        Lista de entidades con tipo y texto
    """
    
    if use_ollama:
        try:
            # Usar Ollama para extracción más avanzada
            system_prompt = """Eres un experto en análisis de texto. 
            Extrae las entidades nombradas (personas, organizaciones, lugares, productos) del texto.
            Responde en formato JSON con lista de entidades."""
            
            prompt = f"""Extrae las entidades del siguiente texto:

{text}

Formato de respuesta JSON:
{{"entities": [{{"text": "nombre", "type": "PERSON|ORG|LOCATION|PRODUCT"}}]}}"""
            
            response = ollama_service.generate(prompt, system_prompt)
            
            # Parsear respuesta (simplificado)
            # En producción, usar parsing JSON más robusto
            import json
            try:
                data = json.loads(response)
                return data.get('entities', [])
            except:
                pass
                
        except Exception as e:
            logger.warning(f"Error extrayendo entidades con Ollama: {e}")
    
    # Fallback a spaCy
    if nlp:
        doc = nlp(text)
        entities = [
            {'text': ent.text, 'type': ent.label_}
            for ent in doc.ents
        ]
        return entities
    
    return []


def generate_embedding(text: str) -> List[float]:
    """Generar embedding vectorial del texto"""
    model = get_embedding_model()
    embedding = model.encode(text, convert_to_numpy=True)
    return embedding.tolist()


def analyze_text_batch(
    texts: List[str],
    use_ollama: bool = True,
    extract_entities: bool = False,
) -> List[Dict[str, Any]]:
    """
    Analizar batch de textos con todas las características
    
    Args:
        texts: Lista de textos
        use_ollama: Si debe usar Ollama para análisis avanzado
        extract_entities: Si debe extraer entidades nombradas
        
    Returns:
        Lista de análisis completos
    """
    
    logger.info(f"Analizando {len(texts)} textos (Ollama: {use_ollama})")
    
    # Analizar sentimientos en batch
    sentiments = analyze_sentiment_batch_with_ollama(texts, use_ollama=use_ollama)
    
    results = []
    
    for i, text in enumerate(texts):
        analysis = {
            'text': text[:200],  # Primeros 200 caracteres
            'sentiment': {
                'positive': sentiments[i]['positive'],
                'negative': sentiments[i]['negative'],
                'neutral': sentiments[i]['neutral'],
            },
            'sentiment_method': sentiments[i]['method'],
            'sentiment_confidence': sentiments[i].get('confidence', 0.5),
            'keywords': extract_keywords(text),
            'length': len(text),
            'word_count': len(text.split()),
        }
        
        # Agregar entidades si se solicita
        if extract_entities:
            try:
                entities = extract_entities_with_ollama(text, use_ollama=use_ollama)
                analysis['entities'] = entities
            except:
                analysis['entities'] = []
        
        results.append(analysis)
    
    # Estadísticas agregadas
    avg_confidence = sum(r['sentiment_confidence'] for r in results) / len(results)
    ollama_usage = sum(1 for r in results if r['sentiment_method'] == 'ollama')
    
    logger.info(
        f"Análisis completado: {ollama_usage}/{len(results)} con Ollama, "
        f"confianza promedio: {avg_confidence:.2f}"
    )
    
    return results


def summarize_text_with_ollama(
    text: str,
    max_length: int = 100,
) -> str:
    """
    Generar resumen de texto usando Ollama
    
    Args:
        text: Texto a resumir
        max_length: Longitud máxima del resumen
        
    Returns:
        Resumen del texto
    """
    
    try:
        system_prompt = """Eres un experto en resumir textos.
        Crea resúmenes concisos y precisos que capturen las ideas principales."""
        
        prompt = f"""Resume el siguiente texto en máximo {max_length} palabras:

{text}

Resumen:"""
        
        summary = ollama_service.generate(prompt, system_prompt)
        return summary.strip()
        
    except Exception as e:
        logger.error(f"Error generando resumen con Ollama: {e}")
        # Fallback: primeras N palabras
        words = text.split()[:max_length]
        return ' '.join(words) + '...'
