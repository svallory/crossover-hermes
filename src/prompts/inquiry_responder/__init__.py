from pathlib import Path
from src.prompts.utils import read_prompt_md

PROMPT_DIR = Path(__file__).parent

inquiry_responder_md = read_prompt_md("inquiry_responder.md", PROMPT_DIR)
answer_question_md = read_prompt_md("answer_question.md", PROMPT_DIR)
inquiry_response_verification_md = read_prompt_md("inquiry_response_verification.md", PROMPT_DIR)

__all__ = [
    "inquiry_responder_md",
    "answer_question_md",
    "inquiry_response_verification_md",
] 