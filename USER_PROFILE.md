# User Market Profile & Taxonomy Specification (Phase 4)

This document specifies the User Market Profile schema, business-domain taxonomy, topic interest model, followed entities, and privacy architecture for Phase 4.

---

## 1. Vision & Core Principle

The user profile represents the **market context** that the user wants the application to monitor, not a personal identity or surveillance model:

> **Core Principle**: Two users with different business profiles (e.g. a neighborhood grocery owner in Gurugram vs. a fashion boutique owner in Mumbai) must receive meaningfully different, highly prioritized feeds from the exact same underlying article and trend database.

---

## 2. User Profile Schema (`user_market_profiles`)

```text
user_id                  (VARCHAR(64), Primary / Foreign Key to users)
business_name            (VARCHAR(255), Optional)
business_domain          (VARCHAR(64), NOT NULL)
business_subdomain       (VARCHAR(64), Optional)
business_description     (TEXT, Optional)
country                  (VARCHAR(64), DEFAULT 'India')
state                    (VARCHAR(64), Optional)
city                     (VARCHAR(64), Optional)
preferred_language       (VARCHAR(10), DEFAULT 'en')
created_at               (TIMESTAMPTZ, DEFAULT NOW())
updated_at               (TIMESTAMPTZ, DEFAULT NOW())
```

### Sensible Defaults & Partial Profiles
A user is never blocked from exploring market feeds. If any field is omitted:
- Missing `city`/`state` defaults to national/state coverage without false assumptions.
- Missing `business_domain` defaults to general market updates with onboarding prompts.
- `business_name` and `business_description` remain strictly optional.

---

## 3. Business-Domain & Subdomain Taxonomy

Phase 4 builds directly upon the Phase 2 domain taxonomy to maintain complete consistency across article enrichment, trend clustering, and feed personalization.

| Primary Domain | Supported Subdomains | Example Core Interests |
|---|---|---|
| `grocery` | `neighborhood_grocery`, `supermarket`, `organic_food`, `food_retail` | FMCG, Food prices, Quick commerce, Kirana retail, Dairy |
| `fashion` | `clothing_retail`, `footwear`, `accessories`, `apparel_manufacturing` | Cotton prices, Festive sales, E-commerce apparel, Sustainable fashion |
| `electronics` | `consumer_electronics`, `mobile_retail`, `appliances` | Smartphone launches, Component shortages, Festive discounts |
| `restaurants` | `quick_service`, `fine_dining`, `cafes`, `cloud_kitchens` | Raw ingredient costs, Delivery aggregators, Food safety |
| `beauty` | `cosmetics_retail`, `personal_care`, `wellness_salons` | D2C brands, Ayurvedic cosmetics, Skincare trends |
| `retail` | `general_retail`, `department_store`, `hypermarket`, `convenience_store` | Footfall patterns, Point of sale, Supply chain, GST |
| `ecommerce` | `d2c`, `marketplace_seller`, `logistics`, `cross_border` | Last-mile delivery, Seller policies, Festive season sales |
| `manufacturing`| `fmcg_production`, `textile_mills`, `packaging`, `plastics` | Raw material inputs, Power tariffs, Export demand |
| `technology` | `enterprise_tech`, `fintech`, `ai_tools`, `saas` | UPI payment trends, POS hardware, Retail software |
| `finance` | `msme_lending`, `banking`, `credit_cards`, `insurance` | Working capital loans, Interest rates, Mudra scheme |
| `general_business`| `economy`, `logistics`, `trade_policy`, `regulations` | Inflation, RBI repo rates, Interstate freight |
| `other` | `services`, `unclassified` | General trade news |

---

## 4. User Interest & Topic Model (`user_topic_preferences`)

Users can express interest in specific topics extracted by Phase 2 enrichment and Phase 3 trends.

### Preference Sources & Confidence
1. `onboarding`: Explicitly chosen during initial setup (High initial weight: 1.0).
2. `manual`: Added or adjusted in Personalization Settings (High explicit weight: 1.0).
3. `inferred`: Gradually learned from positive interactions (Bounded initial weight: 0.2 – 0.6).

```text
id                       (VARCHAR(64), PRIMARY KEY)
user_id                  (VARCHAR(64), REFERENCES users(id) ON DELETE CASCADE)
topic_id                 (VARCHAR(128), NOT NULL, Normalized lowercase string)
preference_source        (VARCHAR(32), 'onboarding' | 'manual' | 'inferred')
preference_score         (FLOAT, 0.0 to 1.0)
is_explicit              (BOOLEAN, True for onboarding/manual)
created_at               (TIMESTAMPTZ, DEFAULT NOW())
updated_at               (TIMESTAMPTZ, DEFAULT NOW())
```

*Unique constraint: `(user_id, topic_id)`.*

---

## 5. Canonical Entities & Follows (`canonical_entities` & `user_entity_follows`)

Allows users to follow specific companies, brands, and organizations (e.g. *Reliance Retail*, *DMart*, *Amul*, *Blinkit*, *Tata Consumer*).

```text
-- Canonical Entity Registry
id                       (VARCHAR(64), PRIMARY KEY)
name                     (VARCHAR(255), NOT NULL, UNIQUE)
entity_type              (VARCHAR(32), 'COMPANY' | 'BRAND' | 'ORGANIZATION')
aliases                  (JSONB, e.g. ["D-Mart", "Avenue Supermarts"])
domain                   (VARCHAR(64), NULLABLE)
created_at               (TIMESTAMPTZ, DEFAULT NOW())

-- User Follows Junction
id                       (VARCHAR(64), PRIMARY KEY)
user_id                  (VARCHAR(64), REFERENCES users(id) ON DELETE CASCADE)
entity_id                (VARCHAR(64), REFERENCES canonical_entities(id) ON DELETE CASCADE)
created_at               (TIMESTAMPTZ, DEFAULT NOW())
```

*Unique constraint: `(user_id, entity_id)`.*

---

## 6. Feed Preferences & Personalization Controls (`user_feed_preferences`)

Stores granular ranking knobs configurable by the user in Settings:

```json
{
  "freshness_bias": 1.0,
  "trend_bias": 1.0,
  "geographic_bias": 1.0,
  "followed_entities_bias": 1.0,
  "behavioural_personalization_enabled": true
}
```

### Privacy & Control Guarantees
- **No Invisible Surveillance**: The user can see all learned preferences.
- **One-Click Reset**: `POST /users/me/preferences/reset` wipes all inferred interaction weights without altering explicit onboarding selections.
- **Opt-Out**: Setting `behavioural_personalization_enabled: false` halts all implicit scoring adjustments.
- **Strict Authorization**: User data is isolated with row-level ownership checks against the authenticated user context.
