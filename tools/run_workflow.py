import argparse
import asyncio
import os

import pandas as pd
import yaml
from dotenv import load_dotenv

# Assuming the HermesConfig and ClassifierInput are structured like this based on workflow.py
# You might need to adjust imports based on your actual project structure
from hermes.agents.classifier.models import ClassifierInput
from hermes.agents.workflow.run import run_workflow
from hermes.config import HermesConfig  # Adjust import if HermesConfig is elsewhere
from hermes.data.vector_store import VectorStore

# Default output directory
OUTPUT_DIR = "output"
RESULTS_DIR = os.path.join(OUTPUT_DIR, "results")


async def makedirs_async(directory: str, exist_ok: bool = False) -> None:
    """Async wrapper for os.makedirs."""
    await asyncio.to_thread(os.makedirs, directory, exist_ok=exist_ok)


def write_yaml_to_file(file_path: str, yaml_content: str) -> None:
    """Helper function to write YAML content to a file."""
    with open(file_path, "w") as f:
        f.write(yaml_content)


async def save_workflow_result_as_yaml(email_id: str, workflow_state) -> None:
    """Save the workflow result for a given email as a YAML file.

    Args:
        email_id: The ID of the email
        workflow_state: The final state of the workflow

    """
    # Create results directory if it doesn't exist
    await makedirs_async(RESULTS_DIR, exist_ok=True)

    # Define the file path
    file_path = os.path.join(RESULTS_DIR, f"{email_id}.yml")

    # Convert workflow state to a serializable dict
    if hasattr(workflow_state, "model_dump"):
        state_dict = workflow_state.model_dump()
    else:
        state_dict = workflow_state

    # Write the YAML file
    try:
        # Use a simpler approach without async context manager
        yaml_str = yaml.dump(state_dict, default_flow_style=False)
        await asyncio.to_thread(lambda: write_yaml_to_file(file_path, yaml_str))
        print(f"  → Saved workflow result to {file_path}")
    except Exception as e:
        print(f"  → Error saving workflow result: {e}")


async def process_email(email_data, hermes_config):
    """Process a single email using the workflow."""
    email_id = email_data.get("email_id", "unknown_email")
    print(f"\nProcessing email: ID {email_id}")

    try:
        # Create ClassifierInput from email_data
        input_state = ClassifierInput(
            email_id=email_id,
            subject=email_data.get("subject", ""),
            message=email_data.get("message", ""),
        )

        # Run the workflow
        print(f"Running the Hermes workflow for email {email_id}...")
        result = await run_workflow(
            input_state=input_state, hermes_config=hermes_config
        )

        # Save the workflow result
        await save_workflow_result_as_yaml(email_id, result)

        # Print additional information about the result
        if (
            hasattr(result, "classifier")
            and result.classifier is not None
            and hasattr(result.classifier, "email_analysis")
            and result.classifier.email_analysis is not None
        ):
            classification = result.classifier.email_analysis.primary_intent
            print(f"  → Classification: {classification}")

        if (
            hasattr(result, "composer")
            and result.composer is not None
            and hasattr(result.composer, "composed_response")
            and result.composer.composed_response is not None
        ):
            response = result.composer.composed_response.response_body
            print(f"  → Generated response: {len(str(response))} characters")

        return result

    except Exception as e:
        print(f"  Error processing email {email_id}: {e}")
        return None


async def main():
    parser = argparse.ArgumentParser(
        description="Run the Hermes workflow for specific email IDs"
    )
    parser.add_argument(
        "--email-ids",
        type=str,
        help="Comma-separated list of email IDs to process (e.g., E001,E002,E003)",
    )
    args = parser.parse_args()

    # Load environment variables
    load_dotenv()

    # Initialize Hermes configuration
    hermes_config = HermesConfig()

    # Initialize vector store
    VectorStore(hermes_config=hermes_config)

    # Load the emails data
    emails_df = pd.read_csv("data/emails.csv")
    print(f"Loaded {len(emails_df)} emails from CSV file.")

    # Filter emails based on provided IDs
    if args.email_ids:
        email_ids = [id.strip() for id in args.email_ids.split(",")]
        emails_df = emails_df[emails_df["email_id"].isin(email_ids)]
        print(f"Filtered to {len(emails_df)} emails based on provided IDs: {email_ids}")
    else:
        # If no email IDs provided, use the single example from the original script
        print("No email IDs provided. Processing the example email E912...")
        example_email = {
            "email_id": "E912",
            "subject": "Rambling About a New Work Bag",
            "message": "Hey, hope you're doing well. Last year for my birthday, my wife Emily got me a really nice leather briefcase from your store. I loved it and used it every day for work until the strap broke a few months ago. Speaking of broken things, I also need to get my lawnmower fixed before spring. Anyway, what were some of the other messenger bag or briefcase style options you have? I could go for something slightly smaller than my previous one. Oh and we also need to make dinner reservations for our anniversary next month. Maybe a nice Italian place downtown. What was I saying again? Oh right, work bags! Let me know what you'd recommend. Thanks!",
        }
        await process_email(example_email, hermes_config)
        return

    # Process each email
    for _, email in emails_df.iterrows():
        email_dict = email.to_dict()
        await process_email(email_dict, hermes_config)

    print("\nWorkflow finished for all requested emails.")


if __name__ == "__main__":
    asyncio.run(main())
