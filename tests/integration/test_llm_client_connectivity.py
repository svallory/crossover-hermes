import unittest
from src.config import HermesConfig
from src.llm_client import get_llm_client
import os

# --- Configuration for the test ---
# Replace with the actual API key provided for the assignment
# or ensure OPENAI_API_KEY environment variable is set.
ASSIGNMENT_API_KEY = "<OPENAI_API_KEY_PLACEHOLDER>"
ASSIGNMENT_BASE_URL = "https://47v4us7kyypinfb5lcligtc3x40ygqbs.lambda-url.us-east-1.on.aws/v1/"
MODEL_NAME_TO_TEST = "gpt-4o"  # Make sure this is an OpenAI model

class TestLLMClientConnectivity(unittest.TestCase):

    def test_successful_connection_with_custom_url(self):
        print(f"Testing LLM client with:")
        print(f"  Model: {MODEL_NAME_TO_TEST}")
        print(f"  Base URL: {ASSIGNMENT_BASE_URL}")
        # Avoid printing the full key, even a placeholder, in test logs if possible
        api_key_status = 'Placeholder - Please set API key or OPENAI_API_KEY env var'
        if ASSIGNMENT_API_KEY != '<OPENAI_API_KEY_PLACEHOLDER>':
            api_key_status = 'Provided in script'
        elif os.environ.get("OPENAI_API_KEY"):
            api_key_status = 'Provided via OPENAI_API_KEY env var'
        print(f"  API Key Status: {api_key_status}")

        # Set environment variables for HermesConfig to pick up,
        # especially if ASSIGNMENT_API_KEY is kept as placeholder in the script.
        # This ensures the test can run in CI/CD if env vars are set there.
        original_openai_api_key = os.environ.get("OPENAI_API_KEY")
        original_openai_base_url = os.environ.get("OPENAI_BASE_URL")

        if ASSIGNMENT_API_KEY != '<OPENAI_API_KEY_PLACEHOLDER>':
            os.environ["OPENAI_API_KEY"] = ASSIGNMENT_API_KEY
        
        os.environ["OPENAI_BASE_URL"] = ASSIGNMENT_BASE_URL

        try:
            config = HermesConfig(
                llm_model_name=MODEL_NAME_TO_TEST,
                llm_base_url=ASSIGNMENT_BASE_URL # Explicitly pass for clarity in test
            )
            
            if ASSIGNMENT_API_KEY != '<OPENAI_API_KEY_PLACEHOLDER>':
                config.llm_api_key = ASSIGNMENT_API_KEY
            # If ASSIGNMENT_API_KEY is placeholder, config.llm_api_key will rely on os.environ.get("OPENAI_API_KEY")
            # which we might have just set, or it might have been pre-existing.
            elif original_openai_api_key: # If it was pre-existing and we didn't override
                 config.llm_api_key = original_openai_api_key

            print(f"\nResolved HermesConfig values:")
            print(f"  llm_model_name: {config.llm_model_name}")
            print(f"  llm_base_url: {config.llm_base_url}")
            api_key_configured_status = 'Not set / Using placeholder'
            if config.llm_api_key and config.llm_api_key != '<OPENAI_API_KEY_PLACEHOLDER>':
                api_key_configured_status = 'Set'
            print(f"  llm_api_key status in config: {api_key_configured_status}")

            self.assertIsNotNone(config.llm_api_key, "API key should be configured either in script or via environment for this test.")
            self.assertNotEqual(config.llm_api_key, "<OPENAI_API_KEY_PLACEHOLDER>", "Placeholder API key should be replaced for this test.")

            llm = get_llm_client(config, temperature=0.1)
            print(f"\nSuccessfully initialized LLM client: {type(llm)}")
            self.assertIsInstance(llm, get_llm_client.__annotations__['return'], "LLM client is not of the expected type.")

            print("\nAttempting a simple API call...")
            completion = llm.invoke("Hello! What is your model name?")
            
            self.assertTrue(hasattr(completion, 'content'), "LLM response does not have 'content' attribute.")
            self.assertIsNotNone(completion.content, "LLM response content is None.")
            print(f"\nLLM Response: {completion.content}")
            print("\nTest PASSED: Successfully received a response from the custom base URL.")

        except Exception as e:
            print(f"\nTest FAILED: An error occurred: {e}")
            import traceback
            traceback.print_exc()
            self.fail(f"Test failed due to an exception: {e}")
        finally:
            # Restore original environment variables to avoid side effects
            if original_openai_api_key is None:
                os.environ.pop("OPENAI_API_KEY", None)
            else:
                os.environ["OPENAI_API_KEY"] = original_openai_api_key
            
            if original_openai_base_url is None:
                os.environ.pop("OPENAI_BASE_URL", None)
            else:
                os.environ["OPENAI_BASE_URL"] = original_openai_base_url

# if __name__ == "__main__":
#     unittest.main() 