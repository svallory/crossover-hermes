import os
from pathlib import Path
from src.prompts.utils import read_prompt_md

PROMPT_DIR = Path(__file__).parent

email_analyzer_md = read_prompt_md("email_analyzer.md", PROMPT_DIR)
email_analysis_verification_md = read_prompt_md("email_analysis_verification.md", PROMPT_DIR)

__all__ = [
    "email_analyzer_md",
    "email_analysis_verification_md",
] 