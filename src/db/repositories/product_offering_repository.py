from src.db.mongodb_client import get_database
from src.models.product_catalog import ProductOffering

from typing import Any

COLLECTION_NAME = "product_offering"

class ProductOfferingRepository:
    @staticmethod
    async def upsert_offering(offering: ProductOffering) -> Any:
        db = get_database()
        data = offering.model_dump(by_alias=True, exclude_none=True)
        # Use name as unique key for upsert (customize as needed)
        result = await db[COLLECTION_NAME].update_one(
            {"name": offering.name},
            {"$set": data},
            upsert=True
        )
        return result

    @staticmethod
    async def get_offering_by_name(name: str) -> ProductOffering | None:
        db = get_database()
        doc = await db[COLLECTION_NAME].find_one({"name": name})
        if doc:
            return ProductOffering.model_validate(doc)
        return None

    @staticmethod
    async def list_offerings() -> list[ProductOffering]:
        db = get_database()
        cursor = db[COLLECTION_NAME].find()
        offerings = []
        async for doc in cursor:
            offerings.append(ProductOffering.model_validate(doc))
        return offerings

    @staticmethod
    async def filter_offerings(filter_dict: dict) -> list[ProductOffering]:
        """
        Filter product offerings by arbitrary MongoDB query dict.
        Example: {"lifecycle_status": "active"}
        """
        db = get_database()
        cursor = db[COLLECTION_NAME].find(filter_dict)
        results = []
        async for doc in cursor:
            results.append(ProductOffering.model_validate(doc))
        return results
