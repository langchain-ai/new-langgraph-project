# Product Catalog Agent Backend

A backend agentic system for managing product catalog data (offering, specification, characteristic, price) using MongoDB and LangGraph.

## Features

- Upsert, filter, and list tools for all product catalog entities
- MongoDB Atlas or local MongoDB support
- LLM agent integration (Ollama, LangGraph)

## Prerequisites

- Python 3.10+
- Ollama (for local LLMs)
- MongoDB Atlas account or local MongoDB instance

## Setup

1. Install dependencies with [uv](https://github.com/astral-sh/uv):

	```sh
	uv sync
	```

2. Copy the example environment file and edit as needed:

	```sh
	cp .env.example .env
	```
	- Set `MONGODB_URI` and `MONGODB_DB_NAME` for your MongoDB instance (Atlas or local)
	- Set `MODEL_NAME` for your LLM (default: qwen3:1.7b)

## Running the Project

Run:

```sh
./run.sh
```

This script loads environment variables, starts Ollama and the LLM model, and launches the LangGraph dev server.

## Notes

- Collections are auto-created in MongoDB: `product_offering`, `product_specification`, `product_characteristic`, `product_price`
- You can use MongoDB Atlas (cloud) or a local MongoDB instance
- All agent tools are available via the LangGraph agent

## Troubleshooting

- Ensure MongoDB is accessible from your machine (check IP whitelist for Atlas)
- If Ollama or the LLM model fails to start, check your model name and Ollama installation

---

For more details, see the code and comments in each module.
