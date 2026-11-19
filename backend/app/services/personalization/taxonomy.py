import re
from typing import Dict, List, Optional, Set, Any


DOMAIN_TAXONOMY: Dict[str, Dict[str, Any]] = {
    "grocery": {
        "display_name": "Grocery & FMCG",
        "subdomains": [
            {"id": "neighborhood_grocery", "name": "Neighborhood Kirana & Convenience"},
            {"id": "supermarket", "name": "Supermarket & Hypermarket"},
            {"id": "organic_food", "name": "Organic & Specialty Food"},
            {"id": "food_retail", "name": "Packaged Food & Beverage Retail"},
        ],
        "suggested_topics": [
            "quick commerce",
            "fmcg",
            "food prices",
            "kirana retail",
            "edible oil",
            "dairy",
            "consumer behaviour",
            "supply chain",
            "retail expansion",
        ],
        "related_domains": ["retail", "ecommerce", "general_business"],
    },
    "fashion": {
        "display_name": "Fashion & Apparel",
        "subdomains": [
            {"id": "clothing_retail", "name": "Apparel & Ready-to-Wear"},
            {"id": "footwear", "name": "Footwear Retail"},
            {"id": "accessories", "name": "Fashion Accessories & Bags"},
            {"id": "apparel_manufacturing", "name": "Textile & Garment Manufacturing"},
        ],
        "suggested_topics": [
            "cotton prices",
            "festive sales",
            "e-commerce apparel",
            "sustainable fashion",
            "textile exports",
            "footwear retail",
            "consumer demand",
        ],
        "related_domains": ["retail", "ecommerce", "manufacturing"],
    },
    "electronics": {
        "display_name": "Electronics & Appliances",
        "subdomains": [
            {"id": "consumer_electronics", "name": "Consumer Gadgets & Audio"},
            {"id": "mobile_retail", "name": "Smartphones & Mobile Retail"},
            {"id": "appliances", "name": "Home Appliances & White Goods"},
        ],
        "suggested_topics": [
            "smartphone launches",
            "component shortages",
            "festive discounts",
            "consumer tech",
            "import tariffs",
            "after-sales service",
        ],
        "related_domains": ["technology", "retail", "ecommerce"],
    },
    "restaurants": {
        "display_name": "Restaurants & Food Services",
        "subdomains": [
            {"id": "quick_service", "name": "QSR & Fast Food"},
            {"id": "fine_dining", "name": "Dine-in Restaurants"},
            {"id": "cafes", "name": "Cafes & Bakeries"},
            {"id": "cloud_kitchens", "name": "Cloud Kitchens & Delivery-Only"},
        ],
        "suggested_topics": [
            "raw ingredient costs",
            "delivery aggregators",
            "food safety",
            "dine-in footfall",
            "commercial lpg rates",
            "menu pricing",
        ],
        "related_domains": ["grocery", "retail", "general_business"],
    },
    "beauty": {
        "display_name": "Beauty & Personal Care",
        "subdomains": [
            {"id": "cosmetics_retail", "name": "Cosmetics & Skincare"},
            {"id": "personal_care", "name": "Personal Hygiene & Haircare"},
            {"id": "wellness_salons", "name": "Salons & Wellness Centers"},
        ],
        "suggested_topics": [
            "d2c beauty",
            "ayurvedic cosmetics",
            "skincare trends",
            "personal care fmcg",
            "beauty retail expansion",
        ],
        "related_domains": ["retail", "ecommerce", "grocery"],
    },
    "retail": {
        "display_name": "General Retail & Merchandising",
        "subdomains": [
            {"id": "general_retail", "name": "Multi-category General Store"},
            {"id": "department_store", "name": "Departmental Store"},
            {"id": "hypermarket", "name": "Organized Hypermarket"},
            {"id": "convenience_store", "name": "Convenience Retail"},
        ],
        "suggested_topics": [
            "footfall patterns",
            "point of sale",
            "supply chain",
            "gst compliance",
            "festive shopping",
            "mall retail",
            "inventory turnover",
        ],
        "related_domains": ["grocery", "fashion", "ecommerce", "general_business"],
    },
    "ecommerce": {
        "display_name": "E-Commerce & D2C",
        "subdomains": [
            {"id": "d2c", "name": "Direct-to-Consumer Brands"},
            {"id": "marketplace_seller", "name": "Online Marketplace Sellers"},
            {"id": "logistics", "name": "E-commerce Logistics & Fulfillment"},
            {"id": "cross_border", "name": "Cross-Border Trade"},
        ],
        "suggested_topics": [
            "last-mile delivery",
            "marketplace commissions",
            "festive sales",
            "quick commerce",
            "return rates",
            "online advertising",
        ],
        "related_domains": ["retail", "technology", "general_business"],
    },
    "manufacturing": {
        "display_name": "Manufacturing & Packaging",
        "subdomains": [
            {"id": "fmcg_production", "name": "FMCG Contract Manufacturing"},
            {"id": "textile_mills", "name": "Textile Spinning & Weaving"},
            {"id": "packaging", "name": "Corrugated Boxes & Flexible Packaging"},
            {"id": "plastics", "name": "Molded Plastics & Containers"},
        ],
        "suggested_topics": [
            "raw material prices",
            "power tariffs",
            "export orders",
            "automation machinery",
            "industrial logistics",
        ],
        "related_domains": ["general_business", "retail"],
    },
    "technology": {
        "display_name": "Technology & Software",
        "subdomains": [
            {"id": "enterprise_tech", "name": "IT Infrastructure & Cloud"},
            {"id": "fintech", "name": "Digital Payments & POS FinTech"},
            {"id": "ai_tools", "name": "Business AI & Automation"},
            {"id": "saas", "name": "SME SaaS Solutions"},
        ],
        "suggested_topics": [
            "upi payment trends",
            "pos hardware",
            "retail software",
            "ai in retail",
            "cybersecurity",
        ],
        "related_domains": ["finance", "ecommerce", "general_business"],
    },
    "finance": {
        "display_name": "Banking & MSME Finance",
        "subdomains": [
            {"id": "msme_lending", "name": "Working Capital & Business Loans"},
            {"id": "banking", "name": "Commercial Banking"},
            {"id": "credit_cards", "name": "Merchant Acquiring & Cards"},
            {"id": "insurance", "name": "Business & Shop Insurance"},
        ],
        "suggested_topics": [
            "rbi policy",
            "msme interest rates",
            "mudra loans",
            "working capital",
            "digital lending",
        ],
        "related_domains": ["general_business", "technology"],
    },
    "general_business": {
        "display_name": "General Business & Economy",
        "subdomains": [
            {"id": "economy", "name": "Macroeconomics & Inflation"},
            {"id": "logistics", "name": "Interstate Freight & Transport"},
            {"id": "trade_policy", "name": "Import/Export & Customs"},
            {"id": "regulations", "name": "Taxation & Trade Compliance"},
        ],
        "suggested_topics": [
            "inflation rates",
            "diesel price hike",
            "gdp growth",
            "gst rate revisions",
            "freight rates",
        ],
        "related_domains": ["retail", "grocery", "manufacturing"],
    },
    "other": {
        "display_name": "Other Services & Trade",
        "subdomains": [
            {"id": "services", "name": "Commercial Services"},
            {"id": "unclassified", "name": "General Commerce"},
        ],
        "suggested_topics": ["market updates", "consumer trends", "business regulations"],
        "related_domains": ["general_business"],
    },
}

TOPIC_SYNONYMS: Dict[str, str] = {
    "health foods": "healthy food",
    "healthy foods": "healthy food",
    "health-focused products": "healthy food",
    "healthy products": "healthy food",
    "quick-commerce": "quick commerce",
    "q-commerce": "quick commerce",
    "10-minute grocery": "quick commerce",
    "kirana stores": "kirana retail",
    "kirana shops": "kirana retail",
    "small retailers": "kirana retail",
    "fmcg goods": "fmcg",
    "fast moving consumer goods": "fmcg",
    "food inflation": "food prices",
    "vegetable prices": "food prices",
    "fuel price": "diesel price hike",
    "petrol price": "diesel price hike",
}


class TaxonomyService:
    """
    Manages normalized domains, subdomains, and topic identifiers for personalization.
    """

    @classmethod
    def get_supported_domains(cls) -> List[Dict[str, Any]]:
        """Returns all supported primary domains with metadata."""
        return [
            {
                "id": domain_id,
                "display_name": data["display_name"],
                "subdomains": data["subdomains"],
                "suggested_topics": data["suggested_topics"],
            }
            for domain_id, data in DOMAIN_TAXONOMY.items()
        ]

    @classmethod
    def is_valid_domain(cls, domain: str) -> bool:
        """Validates if domain is in taxonomy."""
        return domain in DOMAIN_TAXONOMY

    @classmethod
    def is_valid_subdomain(cls, domain: str, subdomain: Optional[str]) -> bool:
        """Validates if subdomain belongs to domain."""
        if not subdomain:
            return True
        if domain not in DOMAIN_TAXONOMY:
            return False
        valid_subs = {s["id"] for s in DOMAIN_TAXONOMY[domain]["subdomains"]}
        return subdomain in valid_subs

    @classmethod
    def normalize_topic(cls, topic: str) -> str:
        """
        Normalizes a topic string: lowercases, removes excessive punctuation,
        and maps known synonyms to canonical concepts.
        """
        if not topic:
            return ""
        clean = topic.strip().lower()
        clean = re.sub(r"[^\w\s-]", "", clean)
        clean = re.sub(r"\s+", " ", clean).strip()
        return TOPIC_SYNONYMS.get(clean, clean)

    @classmethod
    def get_suggested_topics(cls, domain: str) -> List[str]:
        """Returns recommended starting topics for a domain during onboarding."""
        domain_info = DOMAIN_TAXONOMY.get(domain)
        if domain_info:
            return domain_info["suggested_topics"]
        return DOMAIN_TAXONOMY["grocery"]["suggested_topics"]

    @classmethod
    def get_related_domains(cls, domain: str) -> List[str]:
        """Returns list of related domain identifiers for a domain."""
        if not domain:
            return []
        domain_info = DOMAIN_TAXONOMY.get(domain.lower(), {})
        return domain_info.get("related_domains", [])

    @classmethod
    def compute_domain_similarity(
        cls, user_domain: str, article_primary_domain: Optional[str], article_secondary_domains: Optional[List[str]] = None
    ) -> float:
        """
        Calculates domain relevance score in [0.0, 1.0]:
        - Exact primary domain match = 1.0
        - User domain in secondary domains = 0.60
        - Article primary domain in related domains = 0.35
        - Article is general_business = 0.30
        - Otherwise = 0.0
        """
        if not user_domain or not article_primary_domain:
            return 0.20  # Neutral fallback

        user_clean = user_domain.lower()
        art_clean = article_primary_domain.lower()

        if user_clean == art_clean:
            return 1.0

        if article_secondary_domains:
            sec_clean = [s.lower() for s in article_secondary_domains if s]
            if user_clean in sec_clean:
                return 0.60

        domain_info = DOMAIN_TAXONOMY.get(user_clean)
        if domain_info:
            if art_clean in domain_info.get("related_domains", []):
                return 0.35

        if art_clean == "general_business":
            return 0.30

        return 0.0
