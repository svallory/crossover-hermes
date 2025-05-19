import asyncio
import os
from dotenv import load_dotenv

# Assuming the HermesConfig and EmailAnalyzerInput are structured like this based on workflow.py
# You might need to adjust imports based on your actual project structure
from src.hermes.agents.email_analyzer.models import EmailAnalyzerInput
from src.hermes.config import HermesConfig # Adjust import if HermesConfig is elsewhere
from src.hermes.agents.workflow import hermes_langgraph_workflow


async def main():
    # Load environment variables
    load_dotenv()

    # Define the input for the workflow
    email_input = EmailAnalyzerInput(
        email_id="E912",
        subject="Rambling About a New Work Bag",
        message="Hey, hope you're doing well. Last year for my birthday, my wife Emily got me a really nice leather briefcase from your store. I loved it and used it every day for work until the strap broke a few months ago. Speaking of broken things, I also need to get my lawnmower fixed before spring. Anyway, what were some of the other messenger bag or briefcase style options you have? I could go for something slightly smaller than my previous one. Oh and we also need to make dinner reservations for our anniversary next month. Maybe a nice Italian place downtown. What was I saying again? Oh right, work bags! Let me know what you'd recommend. Thanks!"
    )

    # Instantiate HermesConfig. This might require environment variables to be loaded.
    # Adjust instantiation if HermesConfig requires specific arguments not loaded from env.
    hermes_config = HermesConfig()

    # Run the workflow
    print("Running the Hermes workflow...")
    result = await hermes_langgraph_workflow(
        input_state=email_input,
        hermes_config=hermes_config
    )

    # Print the final state/result
    print("\nWorkflow finished. Final state:")
    print(result.model_dump_json(indent=2))

if __name__ == "__main__":
    asyncio.run(main()) 