from langchain_openai import ChatOpenAI
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Debug print to confirm the key is being loaded
print("OPENAI KEY LOADED:", os.getenv("OPENAI_API_KEY")[:10], "...")

# Initialize the OpenAI LLM
llm = ChatOpenAI()

# Send a basic test message
response = llm.invoke("Hello, world!")

# Output the response
print("LLM RESPONSE:", response)
