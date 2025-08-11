import asyncio
from langchain_community.document_loaders import AsyncHtmlLoader
from langchain_community.document_transformers import Html2TextTransformer
from langchain_core.documents import Document

# create a function that takes a list of urls and returns a list of documents

async def get_documents(urls: list[str]) -> list[Document]:
    loader = AsyncHtmlLoader(urls)
    docs = await loader.aload()
    transformer = Html2TextTransformer()
    # Move the blocking transformation to a separate thread
    docs_transformed = await asyncio.to_thread(transformer.transform_documents, docs)
    return docs_transformed