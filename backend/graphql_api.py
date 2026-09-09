"""API GraphQL (lecture catalogue) pour partenaires — en complément de l'API REST."""
import typing
import strawberry
from strawberry.fastapi import GraphQLRouter

from database import db


@strawberry.type
class Product:
    id: str
    title: str
    title_en: typing.Optional[str] = None
    description: typing.Optional[str] = None
    price: float = 0
    compare_at_price: typing.Optional[float] = None
    currency: str = "EUR"
    category: typing.Optional[str] = None
    brand: typing.Optional[str] = None
    image: typing.Optional[str] = None
    in_stock: bool = True
    rating_avg: typing.Optional[float] = None
    rating_count: int = 0


def _to_product(p: dict) -> Product:
    imgs = p.get("images") or []
    return Product(
        id=p.get("id", ""),
        title=p.get("title", ""),
        title_en=p.get("title_en"),
        description=p.get("description"),
        price=float(p.get("price", 0) or 0),
        compare_at_price=p.get("compare_at_price"),
        currency=p.get("currency", "EUR"),
        category=p.get("category"),
        brand=p.get("brand"),
        image=imgs[0] if imgs else None,
        in_stock=bool(p.get("in_stock", True)),
        rating_avg=p.get("rating_avg"),
        rating_count=int(p.get("rating_count", 0) or 0),
    )


@strawberry.type
class Query:
    @strawberry.field
    async def products(
        self,
        category: typing.Optional[str] = None,
        q: typing.Optional[str] = None,
        page: int = 1,
        size: int = 20,
    ) -> typing.List[Product]:
        query: dict = {"active": {"$ne": False}}
        if category:
            query["category"] = category
        if q:
            query["$or"] = [
                {"title": {"$regex": q, "$options": "i"}},
                {"description": {"$regex": q, "$options": "i"}},
            ]
        size = max(1, min(size, 100))
        skip = (max(1, page) - 1) * size
        docs = await db.products.find(query, {"_id": 0}).skip(skip).limit(size).to_list(size)
        return [_to_product(p) for p in docs]

    @strawberry.field
    async def product(self, id: str) -> typing.Optional[Product]:
        p = await db.products.find_one({"id": id}, {"_id": 0})
        return _to_product(p) if p else None

    @strawberry.field
    async def categories(self) -> typing.List[str]:
        cats = await db.products.distinct("category", {"active": {"$ne": False}})
        return [c for c in cats if c]


schema = strawberry.Schema(Query)
graphql_app = GraphQLRouter(schema, path="/api/graphql")
