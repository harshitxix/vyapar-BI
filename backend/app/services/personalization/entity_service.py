import uuid
from typing import List, Optional, Dict, Any, Set
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.personalization import CanonicalEntity, UserEntityFollow


DEFAULT_SEED_ENTITIES = [
    {
        "name": "Reliance Retail",
        "entity_type": "COMPANY",
        "aliases": ["reliance", "reliance fresh", "smart bazaar", "jiomart"],
        "domain": "retail",
    },
    {
        "name": "DMart",
        "entity_type": "COMPANY",
        "aliases": ["d-mart", "avenue supermarts", "avenue supermarts ltd"],
        "domain": "grocery",
    },
    {
        "name": "Blinkit",
        "entity_type": "COMPANY",
        "aliases": ["grofers", "blinkit dark stores"],
        "domain": "grocery",
    },
    {
        "name": "Zepto",
        "entity_type": "COMPANY",
        "aliases": ["zepto cafe", "kirana kart"],
        "domain": "grocery",
    },
    {
        "name": "Swiggy Instamart",
        "entity_type": "COMPANY",
        "aliases": ["swiggy", "instamart"],
        "domain": "grocery",
    },
    {
        "name": "Amul",
        "entity_type": "BRAND",
        "aliases": ["gcmmf", "amul milk", "amul dairy"],
        "domain": "grocery",
    },
    {
        "name": "Tata Consumer",
        "entity_type": "COMPANY",
        "aliases": ["tata consumer products", "tata tea", "tata salt", "tata sampann"],
        "domain": "grocery",
    },
    {
        "name": "Dabur",
        "entity_type": "COMPANY",
        "aliases": ["dabur india", "dabur fmcg"],
        "domain": "grocery",
    },
    {
        "name": "Hindustan Unilever",
        "entity_type": "COMPANY",
        "aliases": ["hul", "unilever india", "hindustan unilever ltd"],
        "domain": "grocery",
    },
    {
        "name": "ITC",
        "entity_type": "COMPANY",
        "aliases": ["itc ltd", "aashirvaad", "sunfeast"],
        "domain": "grocery",
    },
    {
        "name": "Flipkart",
        "entity_type": "COMPANY",
        "aliases": ["flipkart wholesale", "flipkart internet"],
        "domain": "ecommerce",
    },
    {
        "name": "Amazon India",
        "entity_type": "COMPANY",
        "aliases": ["amazon", "amazon fresh"],
        "domain": "ecommerce",
    },
    {
        "name": "Zomato",
        "entity_type": "COMPANY",
        "aliases": ["zomato delivery", "zomato ltd"],
        "domain": "restaurants",
    },
    {
        "name": "Nayara Energy",
        "entity_type": "COMPANY",
        "aliases": ["nayara", "essar oil"],
        "domain": "retail",
    },
]


class EntityFollowService:
    """
    Manages canonical brand & company entities and user follow subscriptions.
    """

    @classmethod
    async def seed_default_entities(cls, db: AsyncSession) -> int:
        """Seeds standard canonical entities if not present."""
        seeded = 0
        for item in DEFAULT_SEED_ENTITIES:
            res = await db.execute(
                select(CanonicalEntity).where(CanonicalEntity.name.ilike(item["name"]))
            )
            existing = res.scalar_one_or_none()
            if not existing:
                ent = CanonicalEntity(
                    id=f"ent_{uuid.uuid4().hex[:10]}",
                    name=item["name"],
                    entity_type=item["entity_type"],
                    aliases=item["aliases"],
                    domain=item.get("domain"),
                )
                db.add(ent)
                seeded += 1
        if seeded > 0:
            await db.commit()
        return seeded

    @classmethod
    async def get_or_create_entity(
        cls,
        db: AsyncSession,
        name: str,
        entity_type: str = "COMPANY",
        domain: Optional[str] = None,
        aliases: Optional[List[str]] = None,
    ) -> CanonicalEntity:
        """Finds entity by exact or alias match, or creates a new one."""
        name_clean = name.strip()
        res = await db.execute(
            select(CanonicalEntity).where(CanonicalEntity.name.ilike(name_clean))
        )
        existing = res.scalar_one_or_none()
        if existing:
            return existing

        # Check aliases
        all_res = await db.execute(select(CanonicalEntity))
        for ent in all_res.scalars():
            if ent.aliases and any(a.lower() == name_clean.lower() for a in ent.aliases):
                return ent

        new_ent = CanonicalEntity(
            id=f"ent_{uuid.uuid4().hex[:10]}",
            name=name_clean,
            entity_type=entity_type.upper(),
            aliases=[a.lower() for a in (aliases or [])],
            domain=domain,
        )
        db.add(new_ent)
        await db.commit()
        await db.refresh(new_ent)
        return new_ent

    @classmethod
    async def list_canonical_entities(
        cls, db: AsyncSession, domain: Optional[str] = None, limit: int = 50
    ) -> List[CanonicalEntity]:
        """Lists suggested canonical entities for users to follow."""
        query = select(CanonicalEntity)
        if domain and domain != "all":
            query = query.where(CanonicalEntity.domain == domain)
        query = query.order_by(CanonicalEntity.name.asc()).limit(limit)
        res = await db.execute(query)
        return list(res.scalars().all())

    @classmethod
    async def follow_entity(
        cls, db: AsyncSession, user_id: str, entity_id: str
    ) -> UserEntityFollow:
        """Adds entity to user's followed list."""
        # Check existing
        res = await db.execute(
            select(UserEntityFollow).where(
                UserEntityFollow.user_id == user_id,
                UserEntityFollow.entity_id == entity_id,
            )
        )
        existing = res.scalar_one_or_none()
        if existing:
            return existing

        follow = UserEntityFollow(
            id=f"fol_{uuid.uuid4().hex[:10]}",
            user_id=user_id,
            entity_id=entity_id,
        )
        db.add(follow)
        await db.commit()
        await db.refresh(follow)
        return follow

    @classmethod
    async def unfollow_entity(
        cls, db: AsyncSession, user_id: str, entity_id: str
    ) -> bool:
        """Removes entity from user's followed list."""
        res = await db.execute(
            delete(UserEntityFollow).where(
                UserEntityFollow.user_id == user_id,
                UserEntityFollow.entity_id == entity_id,
            )
        )
        await db.commit()
        return res.rowcount > 0

    @classmethod
    async def get_user_followed_entities(
        cls, db: AsyncSession, user_id: str
    ) -> List[CanonicalEntity]:
        """Returns all canonical entities followed by user."""
        res = await db.execute(
            select(CanonicalEntity)
            .join(UserEntityFollow, CanonicalEntity.id == UserEntityFollow.entity_id)
            .where(UserEntityFollow.user_id == user_id)
            .order_by(CanonicalEntity.name.asc())
        )
        return list(res.scalars().all())

    @classmethod
    def match_entities_in_article(
        cls, followed_entities: List[CanonicalEntity], article_entities: Optional[List[Dict[str, Any]]]
    ) -> List[str]:
        """
        Returns list of matched entity names if any followed entity is cited
        in the article's enriched entity list.
        """
        if not followed_entities or not article_entities:
            return []

        matched_names: Set[str] = set()
        article_names = set()
        for ae in article_entities:
            if isinstance(ae, dict) and "name" in ae:
                article_names.add(ae["name"].strip().lower())
            elif isinstance(ae, str):
                article_names.add(ae.strip().lower())

        for ent in followed_entities:
            ent_name = ent.name.strip().lower()
            if ent_name in article_names:
                matched_names.add(ent.name)
                continue
            if ent.aliases:
                for alias in ent.aliases:
                    if alias.strip().lower() in article_names:
                        matched_names.add(ent.name)
                        break

        return list(matched_names)
