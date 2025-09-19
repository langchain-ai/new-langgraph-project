
from pydantic import BaseModel, Field
from typing import List

class ProductOffering(BaseModel):
    name: str
    description: str | None = None
    lifecycle_status: str | None = Field(None, alias="lifecycle_status")
    valid_from: str | None = None  # ISO date string
    valid_to: str | None = None    # ISO date string
    target_segments: List[str] | None = None
    sales_channels: List[str] | None = None

class ProductSpecification(BaseModel):
    id: str
    version: str | None = None
    baseType: str | None = Field(None, alias="@baseType")
    schemaLocation: str | None = Field(None, alias="@schemaLocation")
    type_: str | None = Field(None, alias="@type")
    brand: str | None = None
    description: str | None = None
    isBundle: bool | None = None
    lastUpdate: str | None = None  # ISO datetime string
    lifecycleStatus: str | None = None
    name: str | None = None
    productNumber: str | None = None

class ProductCharacteristicValue(BaseModel):
    valueType: str | None = None
    value: str | None = None
    unitOfMeasure: str | None = None
    valueFrom: str | None = None
    valueTo: str | None = None
    rangeInterval: str | None = None
    regex: str | None = None
    type_: str | None = Field(None, alias="@type")
    schemaLocation: str | None = Field(None, alias="@schemaLocation")
    isDefault: bool | None = None

class ProductCharacteristic(BaseModel):
    id: str
    baseType: str | None = Field(None, alias="@baseType")
    schemaLocation: str | None = Field(None, alias="@schemaLocation")
    type_: str | None = Field(None, alias="@type")
    characteristicType: str | None = None
    configurable: bool | None = None
    isModifiable: bool | None = None
    description: str | None = None
    extensible: bool | None = None
    isUnique: bool | None = None
    isVisible: bool | None = None
    mandatory: bool | None = None
    maxCardinality: int | None = None
    minCardinality: int | None = None
    name: str | None = None
    productCharacteristicValue: List[ProductCharacteristicValue] | None = None
    regex: str | None = None
    revision: int | None = None
    valueSchemaLocation: str | None = None
    valueType: str | None = None

class ProductPrice(BaseModel):
    id: str
    version: str | None = None
    description: str | None = None
    isBundle: bool | None = None
    lastUpdate: str | None = None
    lifecycleStatus: str | None = None
    name: str | None = None
    percentage: float | None = None
    priceType: str | None = None
    recurringChargePeriodLength: int | None = None
    recurringChargePeriodType: str | None = None
    baseType: str | None = Field(None, alias="@baseType")
    schemaLocation: str | None = Field(None, alias="@schemaLocation")
    type_: str | None = Field(None, alias="@type")
    recurringChargePeriodCount: int | None = None
    advancedPricingMethod: str | None = None
    pricingCategory: str | None = None
    salesTime: str | None = None
