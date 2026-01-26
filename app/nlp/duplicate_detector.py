from sentence_transformers import SentenceTransformer, util
import torch

class DuplicateDetector:
    def __init__(self, model_name='all-MiniLM-L6-v2'):
        # Small, fast model for semantic similarity
        try:
            self.model = SentenceTransformer(model_name)
        except:
            self.model = None

    def calculate_similarity(self, text1, text2):
        """Calculate cosine similarity between two texts."""
        if not self.model:
            return 0.0
            
        embeddings = self.model.encode([text1, text2])
        cos_sim = util.cos_sim(embeddings[0], embeddings[1])
        return cos_sim.item()

    def is_duplicate(self, new_lead_text, existing_leads_texts, threshold=0.85):
        """Check if a new lead is a semantic duplicate of any existing leads."""
        if not self.model or not existing_leads_texts:
            return False
            
        new_embedding = self.model.encode(new_lead_text)
        existing_embeddings = self.model.encode(existing_leads_texts)
        
        # Compute cosine similarity between new and all existing
        cosine_scores = util.cos_sim(new_embedding, existing_embeddings)
        
        # Check if any score exceeds the threshold
        max_score = torch.max(cosine_scores).item()
        return max_score >= threshold
