
from app.nlp.intent_service import BuyingIntentNLP

nlp = BuyingIntentNLP()

test_cases = [
    "I am looking for tires for my car in Nairobi. Anyone selling?",
    "Anyone selling tires in Kenya? I need 4 urgently.",
    "Looking for a reliable supplier for solar panels. Natafuta solar panels.",
    "Where can I buy original Toyota parts in Mombasa? Nahitaji spare parts.",
    "I need help finding a good mechanic in Kisumu. Help me find one.",
    "Looking for tires? We have the best prices in town. Call us today.", # Should be SELLER
    "Selling high quality tires at affordable prices. DM for order.", # Should be SELLER
    "Toyota spare parts available in Nairobi. Best price guaranteed.", # Should be SELLER
    "Natafuta cement for my construction project. I need 100 bags.",
    "Anyone with a laptop for sale? I want to buy one today.",
    "Looking for a house to rent in Kilimani. My budget is 50k.",
]

for text in test_cases:
    classification = nlp.classify_intent(text)
    print(f"Text: {text[:50]}...")
    print(f"Classification: {classification}")
    print("-" * 20)
