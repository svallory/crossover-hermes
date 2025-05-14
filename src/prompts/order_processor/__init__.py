from pathlib import Path
from src.prompts.utils import read_prompt_md

PROMPT_DIR = Path(__file__).parent

order_processor_md = read_prompt_md("order_processor.md", PROMPT_DIR)
order_processing_verification_md = read_prompt_md("order_processing_verification.md", PROMPT_DIR)

__all__ = [
    "order_processor_md",
    "order_processing_verification_md",
] 