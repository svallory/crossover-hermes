from pathlib import Path
from src.prompts.utils import read_prompt_md

PROMPT_DIR = Path(__file__).parent

response_composer_md = read_prompt_md("response_composer.md", PROMPT_DIR)
response_quality_verification_md = read_prompt_md("response_quality_verification.md", PROMPT_DIR)

__all__ = [
    "response_composer_md",
    "response_quality_verification_md",
] 