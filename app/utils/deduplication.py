
import logging
import numpy as np
from typing import List, Dict, Any
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger("Deduplication")

class LeadDeduplicator:
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2', similarity_threshold: float = 0.85):
        """
        Initialize the deduplicator with a pre-trained transformer model.
        Threshold 0.85 is usually good for near-duplicates (e.g., "toyota" vs "toyotas").
        """
        try:
            self.model = SentenceTransformer(model_name)
            self.similarity_threshold = similarity_threshold
            logger.info(f"Deduplicator initialized with model {model_name} (Threshold: {similarity_threshold})")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}. Falling back to basic deduplication.")
            self.model = None

    def deduplicate(self, leads: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Perform multi-stage deduplication:
        1. URL exact match
        2. Phone exact match
        3. Embedding-based semantic similarity
        """
        if not leads:
            return []

        # Stage 1: URL Deduplication (Highest Confidence)
        unique_by_url = {}
        for lead in leads:
            url = lead.get("source_url")
            if not url:
                continue
            if url not in unique_by_url or lead.get("intent_score", 0) > unique_by_url[url].get("intent_score", 0):
                unique_by_url[url] = lead
        
        leads = list(unique_by_url.values())

        # Stage 2: Phone Number Deduplication
        unique_by_phone = {}
        no_phone_leads = []
        for lead in leads:
            phone = lead.get("contact_phone")
            if phone:
                # Keep the one with higher intent_score if phones match
                if phone not in unique_by_phone or lead.get("intent_score", 0) > unique_by_phone[phone].get("intent_score", 0):
                    unique_by_phone[phone] = lead
            else:
                no_phone_leads.append(lead)
        
        leads = list(unique_by_phone.values()) + no_phone_leads

        # Stage 3: Embedding-Based Deduplication (Semantic Noise Reduction)
        if self.model and len(leads) > 1:
            try:
                # Extract snippets for embedding
                snippets = [l.get("buyer_request_snippet", "") for l in leads]
                embeddings = self.model.encode(snippets)
                
                # Compute similarity matrix
                sim_matrix = cosine_similarity(embeddings)
                
                to_remove = set()
                for i in range(len(leads)):
                    if i in to_remove:
                        continue
                    for j in range(i + 1, len(leads)):
                        if j in to_remove:
                            continue
                        
                        if sim_matrix[i][j] >= self.similarity_threshold:
                            # They are semantically very similar (e.g. "toyota" vs "toyotas")
                            # Keep the one with higher intent score or more info
                            score_i = leads[i].get("intent_score", 0)
                            score_j = leads[j].get("intent_score", 0)
                            
                            if score_j > score_i:
                                to_remove.add(i)
                                break # Lead i is gone, move to next i
                            else:
                                to_remove.add(j)
                
                final_leads = [lead for idx, lead in enumerate(leads) if idx not in to_remove]
                logger.info(f"Embedding deduplication: {len(leads)} -> {len(final_leads)} (Removed {len(to_remove)})")
                return final_leads
                
            except Exception as e:
                logger.error(f"Embedding deduplication failed: {e}")
                return leads
        
        return leads

# Global instance for easy access
_deduplicator = None

def get_deduplicator():
    global _deduplicator
    if _deduplicator is None:
        _deduplicator = LeadDeduplicator()
    return _deduplicator
