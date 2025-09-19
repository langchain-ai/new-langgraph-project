from typing import List
from langchain_core.tools import tool
from src.db.repositories.product_offering_repository import ProductOfferingRepository
from src.db.repositories.product_specification_repository import ProductSpecificationRepository
from src.db.repositories.product_characteristic_repository import ProductCharacteristicRepository
from src.db.repositories.product_price_repository import ProductPriceRepository
from src.models.product_catalog import ProductOffering, ProductSpecification, ProductCharacteristic, ProductPrice


# Product Offering Tools
@tool
async def upsert_product_offering(offering: ProductOffering) -> str:
    """
    Save or update a product offering in the database.
    Use this to create or modify product offerings.

    Args:
        offering (ProductOffering): ProductOffering model instance.

    Returns:
        str: Confirmation message.
    """
    await ProductOfferingRepository.upsert_offering(offering)
    return "Product offering upserted."


@tool
async def filter_product_offerings(filter_dict: dict) -> list:
    """
    Filter product offerings by any field.
    Use this to search for offerings matching specific criteria.

    Args:
        filter_dict (dict): Dictionary of MongoDB query parameters.

    Returns:
        list: List of matching product offerings as dictionaries.
    """
    results = await ProductOfferingRepository.filter_offerings(filter_dict)
    return [r.model_dump() for r in results]


# Product Specification Tools
@tool
async def upsert_product_specification(spec: ProductSpecification) -> str:
    """
    Save or update a product specification in the database.
    Use this to create or modify product specifications.

    Args:
        spec (ProductSpecification): ProductSpecification model instance.

    Returns:
        str: Confirmation message.
    """
    await ProductSpecificationRepository.upsert_specification(spec)
    return "Product specification upserted."


@tool
async def filter_product_specifications(filter_dict: dict) -> list:
    """
    Filter product specifications by any field.
    Use this to search for specifications matching specific criteria.

    Args:
        filter_dict (dict): Dictionary of MongoDB query parameters.

    Returns:
        list: List of matching product specifications as dictionaries.
    """
    results = await ProductSpecificationRepository.filter_specifications(filter_dict)
    return [r.model_dump() for r in results]


# Product Characteristic Tools
@tool
async def upsert_product_characteristic(char: ProductCharacteristic) -> str:
    """
    Save or update a product characteristic in the database.
    Use this to create or modify product characteristics.

    Args:
        char (ProductCharacteristic): ProductCharacteristic model instance.

    Returns:
        str: Confirmation message.
    """
    await ProductCharacteristicRepository.upsert_characteristic(char)
    return "Product characteristic upserted."


@tool
async def filter_product_characteristics(filter_dict: dict) -> list:
    """
    Filter product characteristics by any field.
    Use this to search for characteristics matching specific criteria.

    Args:
        filter_dict (dict): Dictionary of MongoDB query parameters.

    Returns:
        list: List of matching product characteristics as dictionaries.
    """
    results = await ProductCharacteristicRepository.filter_characteristics(filter_dict)
    return [r.model_dump() for r in results]


# Product Price Tools
@tool
async def upsert_product_price(price: ProductPrice) -> str:
    """
    Save or update a product price in the database.
    Use this to create or modify product prices.

    Args:
        price (ProductPrice): ProductPrice model instance.

    Returns:
        str: Confirmation message.
    """
    await ProductPriceRepository.upsert_price(price)
    return "Product price upserted."


@tool
async def filter_product_prices(filter_dict: dict) -> list:
    """
    Filter product prices by any field.
    Use this to search for prices matching specific criteria.

    Args:
        filter_dict (dict): Dictionary of MongoDB query parameters.

    Returns:
        list: List of matching product prices as dictionaries.
    """
    results = await ProductPriceRepository.filter_prices(filter_dict)
    return [r.model_dump() for r in results]


class DPCToolkit:
    @staticmethod
    def get_tools() -> List:
        """Return a list of upsert and filter tools for product catalog entities."""
        return [
            upsert_product_offering,
            filter_product_offerings,
            upsert_product_specification,
            filter_product_specifications,
            upsert_product_characteristic,
            filter_product_characteristics,
            upsert_product_price,
            filter_product_prices,
        ]
