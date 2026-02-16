
import sys
import os
# Add current directory to path so we can import app
sys.path.append(os.getcwd())

from app.intelligence_v2.semantic_score import calculate_final_intelligence_score, calculate_language_boost
from app.intelligence_v2.thresholds import STRICT_PUBLIC, HIGH_INTENT, FLOOR

def test_scoring():
    print("--- 🧪 SCORING MATH VERIFICATION ---")
    
    # Test Case 1: High Intent English + Google Maps (Trust 0.95)
    text_en = "I need a Toyota Hilux urgently in Nairobi"
    intent_score = 0.8 # Simulated
    semantic_score = 0.9 # Simulated
    
    final_en = calculate_final_intelligence_score(intent_score, semantic_score, text_en, "google_maps")
    print(f"English + Google Maps: {final_en}")
    
    # Test Case 2: Swahili Intent + Google Maps (Trust 0.95)
    text_sw = "Natafuta Toyota Prado sasa hivi"
    intent_score = 0.8 # Simulated
    semantic_score = 0.9 # Simulated
    
    # Language boost for "Natafuta" should be ~0.6
    boost = calculate_language_boost(text_sw)
    print(f"Language Boost (Swahili): {boost}")
    
    final_sw = calculate_final_intelligence_score(intent_score, semantic_score, text_sw, "google_maps")
    print(f"Swahili + Google Maps: {final_sw}")
    
    # Verify formula: ((0.8 * 0.4) + (0.9 * 0.4) + (0.6 * 0.2)) * 0.95
    # (0.32 + 0.36 + 0.12) * 0.95 = 0.8 * 0.95 = 0.76
    
    print(f"Thresholds: STRICT={STRICT_PUBLIC}, HIGH={HIGH_INTENT}, FLOOR={FLOOR}")
    
    if final_sw > final_en:
        print("✅ SUCCESS: Swahili boost is active!")
    else:
        print("❌ FAILURE: Swahili boost not reflected.")

if __name__ == "__main__":
    test_scoring()
