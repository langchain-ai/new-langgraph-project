# MongoDB client setup using motor (async)
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
import os

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "product_catalog")

client: AsyncIOMotorClient | None = None

def get_client() -> AsyncIOMotorClient:
	global client
	if client is None:
		client = AsyncIOMotorClient(MONGODB_URI)
	return client

def get_database() -> AsyncIOMotorDatabase:
	return get_client()[MONGODB_DB_NAME]
