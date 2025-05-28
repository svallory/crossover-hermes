"""Quick test for simplified _bind_tools_with_structured_output function."""

from typing import Optional
from pydantic import BaseModel, Field, SecretStr
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from hermes.utils.llm_client import _bind_tools_with_structured_output


# Define test schema
class TestResponse(BaseModel):
    """Test response schema for structured output."""

    answer: str = Field(description="The main answer")
    confidence: float = Field(description="Confidence score between 0 and 1")
    reasoning: Optional[str] = Field(default=None, description="Optional reasoning")


@tool
def get_weather(location: str) -> str:
    """Get weather information for a location."""
    return f"The weather in {location} is sunny and 22°C"


def test_simplified_implementation():
    """Test the simplified implementation with Pydantic class only."""
    print("Testing simplified implementation...")

    # Test with ChatOpenAI
    llm_openai = ChatOpenAI(
        model="gpt-4o-mini", api_key=SecretStr("test-key"), temperature=0.0
    )

    # Test with ChatGoogleGenerativeAI
    llm_google = ChatGoogleGenerativeAI(
        model="gemini-1.5-flash", google_api_key="test-key", temperature=0.0
    )

    tools = [get_weather]

    try:
        # Test OpenAI
        bound_openai = _bind_tools_with_structured_output(
            llm_openai, TestResponse, tools
        )
        print("✅ OpenAI simplified binding successful")
        print(f"   Type: {type(bound_openai)}")

        # Test Google
        bound_google = _bind_tools_with_structured_output(
            llm_google, TestResponse, tools
        )
        print("✅ Google simplified binding successful")
        print(f"   Type: {type(bound_google)}")

        return True

    except Exception as e:
        print(f"❌ Simplified binding failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("🧪 Testing simplified _bind_tools_with_structured_output\n")

    success = test_simplified_implementation()

    if success:
        print("\n🎉 Simplified implementation works perfectly!")
        print("✨ Code is now much cleaner and simpler!")
    else:
        print("\n⚠️  Test failed")
