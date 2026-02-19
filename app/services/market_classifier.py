BUYER_KEYWORDS = [
    "looking for",
    "need",
    "wtb",
    "want to buy",
    "anyone selling",
    "where can i",
    "recommend",
    "urgent",
    "needed"
]

SELLER_KEYWORDS = [
    "best price",
    "we sell",
    "official dealer",
    "shop now",
    "add to cart",
    "ltd",
    "limited",
    "enterprise",
    "company",
    "wholesale",
    "supplier"
]

def classify_market_side(text: str):
    text = text.lower()

    buyer_score = sum(1 for k in BUYER_KEYWORDS if k in text)
    seller_score = sum(1 for k in SELLER_KEYWORDS if k in text)

    if buyer_score > seller_score:
        return "demand"
    elif seller_score > buyer_score:
        return "supply"
    else:
        return "neutral"
