from langchain_community.document_loaders import WebBaseLoader
from tavily import TavilyClient
import os

tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

def fetch_with_urls(urls: list[str]) -> list[str]:
    documents = []
    for website in urls:
        loader = WebBaseLoader(website)
        documents.extend(loader.load())
    return documents

def fetch_with_web_search(query: str) -> list[str]:
    response = tavily_client.search(query=query)
    documents = [result['content'] for result in response['results']]
    return documents

