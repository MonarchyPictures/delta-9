from app.nlp.intent_service import BuyingIntentNLP

def test_intent():
    nlp = BuyingIntentNLP()
    
    buyer_texts = [
        "I am looking for tires in Nairobi, any recommendations?",
        "Anyone selling used engines in Kenya? I need one urgently.",
        "Where can I buy solar panels in Mombasa?",
        "Natafuta gari ya bei nafuu Kenya.",
        "I need a plumber in Westlands.",
        "Looking for a reliable supplier of building materials."
    ]
    
    seller_texts = [
        "We are selling tires at discounted prices. Visit our shop in Nairobi.",
        "Best engines available in stock. DM for price.",
        "Solar panels for sale. Call 0712345678.",
        "Tunauza magari kwa bei nafuu.",
        "I am a plumber available for work in Westlands.",
        "Supplier of building materials, contact us for wholesale prices."
    ]
    
    print("--- Testing Buyer Texts ---")
    for text in buyer_texts:
        classification = nlp.classify_intent(text)
        score = nlp.calculate_intent_score(text)
        print(f"Text: {text[:50]}...")
        print(f"Classification: {classification}, Score: {score}")
        print("-" * 20)
        
    print("\n--- Testing Seller Texts ---")
    for text in seller_texts:
        classification = nlp.classify_intent(text)
        score = nlp.calculate_intent_score(text)
        print(f"Text: {text[:50]}...")
        print(f"Classification: {classification}, Score: {score}")
        print("-" * 20)

if __name__ == "__main__":
    test_intent()
