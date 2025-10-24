from deepagents import create_deep_agent



# System prompt to steer the agent to be an expert researcher
research_instructions = """
You are an expert financial advisor for a company data. you take company problems and deliver clear answer to the problems.
"""

# Create the deep agent
graph = create_deep_agent(
    system_prompt=research_instructions,
)
