import datetime
import platform
import requests
from typing import List

from langchain_core.tools import tool
from langchain_community.tools import DuckDuckGoSearchResults
from langchain_community.utilities import DuckDuckGoSearchAPIWrapper


@tool
def web_search(query: str) -> str:
    """
    Performs a web search using the DuckDuckGo search engine.

    Args:
        query (str): The search query string.

    Returns:
        str: The search results returned by DuckDuckGo.

    Example:
        >>> web_search("Python programming language")
        'Python is an interpreted, high-level and general-purpose programming language...'
    """
    wrapper = DuckDuckGoSearchAPIWrapper(max_results=5)
    search = DuckDuckGoSearchResults(api_wrapper=wrapper)

    return search.invoke(query)


@tool
def get_current_time() -> str:
    """
    Returns the current date and time.

    Returns:
        str: The current date and time in 'YYYY-MM-DD HH:MM:SS' format.
    """
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@tool
def get_system_info() -> str:
    """
    Returns information about the current system.

    Returns:
        str: System name, release, and version.
    """
    return f"System: {platform.system()}, Release: {platform.release()}, Version: {platform.version()}"


@tool
def get_joke() -> str:
    """
    Fetches a random joke from the JokeAPI.

    Returns:
        str: A random joke or an error message.
    """
    url = "https://v2.jokeapi.dev/joke/Any?type=single"

    try:
        response = requests.get(url)
        response.raise_for_status()

        data = response.json()

        if "joke" in data:
            return data["joke"]
        elif "setup" in data and "delivery" in data:
            return f"{data['setup']} - {data['delivery']}"
        else:
            return "Error: Unable to fetch joke."

    except requests.exceptions.RequestException as e:
        return f"Error fetching joke: {str(e)}"

@tool
def get_weather(city: str) -> str:
    """Get weather for a given city."""
    return f"It's always sunny in {city}!"


class ExampleToolkit:
    """A toolkit containing example tools."""
    @staticmethod
    def get_tools() -> List:
        """Returns a list of example tools."""
        return [web_search, get_current_time, get_system_info, get_joke, get_weather]