from src.db.mongodb_client import get_database
from src.models.product_catalog import ProductSpecification

from typing import Any

COLLECTION_NAME = "product_specification"

class ProductSpecificationRepository:
    @staticmethod
    async def upsert_specification(spec: ProductSpecification) -> Any:
        db = get_database()
        data = spec.model_dump(by_alias=True, exclude_none=True)
        result = await db[COLLECTION_NAME].update_one(
            {"id": spec.id},
            {"$set": data},
            upsert=True
        )
        return result

    @staticmethod
    async def get_specification_by_id(id: str) -> ProductSpecification | None:
        db = get_database()
        doc = await db[COLLECTION_NAME].find_one({"id": id})
        if doc:
            return ProductSpecification.model_validate(doc)
        return None

    @staticmethod
    async def list_specifications() -> list[ProductSpecification]:
        db = get_database()
        cursor = db[COLLECTION_NAME].find()
        specs = []
        async for doc in cursor:
            specs.append(ProductSpecification.model_validate(doc))
        return specs

    @staticmethod
    async def filter_specifications(filter_dict: dict) -> list[ProductSpecification]:
        """
        Filter product specifications by arbitrary MongoDB query dict.
        Example: {"isBundle": True}
        """
        db = get_database()
        cursor = db[COLLECTION_NAME].find(filter_dict)
        results = []
        async for doc in cursor:
            results.append(ProductSpecification.model_validate(doc))
        return results
