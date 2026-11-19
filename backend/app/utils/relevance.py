from typing import List, Optional

DOMAIN_KEYWORDS = {
    "grocery": [
        "grocery", "kirana", "supermarket", "fmcg", "staples", "provisions", "packaged food",
        "dairy", "beverage", "edible oil", "vegetable", "fruit", "quick commerce", "zepto",
        "blinkit", "instamart", "swiggy", "dmart", "spencer", "reliance fresh", "bigbasket"
    ],
    "retail": [
        "retail", "store", "shop", "commerce", "consumer", "shopping", "mall", "outlet",
        "e-commerce", "ecommerce", "d2c", "kirana", "hypermarket", "cash and carry", "trader",
        "wholesaler", "distributor", "merchant", "inventory", "footfall", "pos"
    ],
    "fashion": [
        "fashion", "apparel", "clothing", "garment", "textile", "footwear", "shoes", "jewellery",
        "accessory", "luxury", "myntra", "ajio", "zara", "h&m", "trend"
    ],
    "electronics": [
        "electronics", "smartphone", "mobile", "gadget", "appliances", "laptop", "tv", "hardware"
    ],
    "technology": [
        "tech", "technology", "software", "ai", "startup", "fintech", "saas", "digital", "platform"
    ],
    "general_business": [
        "business", "economy", "market", "gst", "tax", "inflation", "supply chain", "logistics",
        "trade", "msme", "sme", "startup"
    ]
}


def classify_domain(title: str, description: Optional[str] = None, source_domains: Optional[List[str]] = None) -> str:
    """
    Deterministically assigns a primary business domain based on keywords in title/description
    or falls back to the configured source business domains.
    """
    combined = (title + " " + (description or "")).lower()

    # Score each domain by keyword hits
    scores = {}
    for domain, keywords in DOMAIN_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in combined)
        if score > 0:
            scores[domain] = score

    if scores:
        best_domain = max(scores, key=scores.get)
        return best_domain

    if source_domains and len(source_domains) > 0:
        return source_domains[0]

    return "retail"
