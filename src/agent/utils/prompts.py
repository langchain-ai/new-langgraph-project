"""Prompt loading utilities for Lucart Agents."""
from pathlib import Path


def get_coder_prompt():
    """Load the coder system prompt from markdown file."""
    prompt_file = Path(__file__).parent.parent / "prompts" / "coder_prompt.md"
    return prompt_file.read_text()


def get_auditor_prompt():
    """Load the auditor system prompt from markdown file."""
    prompt_file = Path(__file__).parent.parent / "prompts" / "auditor_prompt.md"
    return prompt_file.read_text()


def get_auditor_resources():
    """Load the auditor resources from markdown file."""
    resources_file = Path(__file__).parent.parent / "resources" / "auditor.md"
    return resources_file.read_text()


def get_coder_resources():
    """Load the coder resources from markdown file."""
    resources_file = Path(__file__).parent.parent / "resources" / "coder.md"
    return resources_file.read_text()


def get_prompt_and_resources(prompt_function, resources_filename):
    """Get the complete prompt with resources appended.

    Args:
        prompt_function: Function that returns the base prompt (e.g., get_auditor_prompt, get_coder_prompt)
        resources_filename: Name of the resources file (e.g., 'auditor.md', 'coder.md')

    Returns:
        Combined prompt with resources appended
    """
    base_prompt = prompt_function()

    # Load resources file
    resources_file = Path(__file__).parent.parent / "resources" / resources_filename
    resources = resources_file.read_text()

    # Clear separation between main prompt and resources
    separator = "\n\n" + "=" * 80 + "\n" + "=" * 80 + "\n\n"

    return base_prompt + separator + resources
