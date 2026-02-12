from sentence_transformers import SentenceTransformer, util 
import torch 
import logging

logger = logging.getLogger("NLP-Dedupe")

# Initialize model once at module level
model = SentenceTransformer("all-MiniLM-L6-v2") 

SIM_THRESHOLD = 0.70 

def dedupe_leads(leads): 
    """
    Remove duplicate leads using semantic similarity of snippet and phone.
    """
    if not leads: 
        return leads 

    logger.info(f"NLP-DEDUPE: Processing {len(leads)} leads...")

    texts = [ 
        f"{lead.get('buyer_request_snippet') or lead.get('text', '')} {lead.get('contact_phone') or lead.get('phone', '')}" 
        for lead in leads 
    ] 

    # Encode texts into semantic vectors
    embeddings = model.encode(texts, convert_to_tensor=True) 

    unique = [] 
    used = set() 

    for i in range(len(leads)): 
        if i in used: 
            continue 

        unique.append(leads[i]) 

        for j in range(i + 1, len(leads)): 
            if j in used: 
                continue 

            # Calculate cosine similarity between lead i and lead j
            similarity = util.cos_sim(embeddings[i], embeddings[j]) 

            if similarity > SIM_THRESHOLD: 
                used.add(j) 

    logger.info(f"NLP-DEDUPE: Reduced to {len(unique)} unique leads (Removed {len(used)})")
    return unique
