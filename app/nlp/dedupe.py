import logging

logger = logging.getLogger("NLP-Dedupe")

# Initialize model lazily
_model = None

def get_model():
    global _model
    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer, util
            import torch
            _model = SentenceTransformer("all-MiniLM-L6-v2")
            logger.info("✅ SentenceTransformer model loaded.")
        except ImportError:
            logger.error("⚠️ sentence_transformers not installed.")
            _model = None
        except Exception as e:
            logger.error(f"⚠️ Failed to load SentenceTransformer: {e}")
            _model = None
    return _model

SIM_THRESHOLD = 0.90 

def dedupe_leads(leads): 
    """
    Remove duplicate leads using semantic similarity of snippet and phone.
    First pass: Exact URL deduplication.
    Second pass: Semantic deduplication.
    """
    if not leads: 
        return leads 

    # 1. Exact URL Deduplication
    unique_by_url = {}
    for lead in leads:
        url = lead.get('url')
        if url:
            if url not in unique_by_url:
                unique_by_url[url] = lead
        else:
            # No URL? Treat as unique for now, handle in semantic
            import uuid
            unique_by_url[str(uuid.uuid4())] = lead
            
    leads_to_process = list(unique_by_url.values())

    logger.info(f"NLP-DEDUPE: Processing {len(leads_to_process)} unique-URL leads...")

    model = get_model()
    if not model:
        logger.warning("NLP-Dedupe: Model not loaded, skipping semantic dedupe.")
        return leads_to_process

    try:
        from sentence_transformers import util
        
        texts = [ 
            f"{lead.get('author', '')} {lead.get('buyer_request_snippet') or lead.get('text', '')} {lead.get('contact_phone') or lead.get('phone', '')}" 
            for lead in leads_to_process 
        ] 

        # Encode texts into semantic vectors
        embeddings = model.encode(texts, convert_to_tensor=True) 

        unique = [] 
        used = set() 

        for i in range(len(leads_to_process)): 
            if i in used: 
                continue 

            unique.append(leads_to_process[i]) 

            for j in range(i + 1, len(leads_to_process)): 
                if j in used: 
                    continue 

                # Calculate cosine similarity between lead i and lead j
                similarity = util.cos_sim(embeddings[i], embeddings[j]) 

                if similarity > SIM_THRESHOLD: 
                    used.add(j) 

        logger.info(f"NLP-DEDUPE: Reduced to {len(unique)} unique leads (Removed {len(leads) - len(unique)})")
        return unique

    except Exception as e:
        logger.error(f"NLP-Dedupe Error: {e}")
        return leads_to_process
