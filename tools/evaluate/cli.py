#!/usr/bin/env python
"""CLI for Hermes Evaluation Tools."""

import argparse
import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from tools.evaluate.evaluate import run_evaluation
from tools.evaluate.llm_evaluators import create_llm_evaluator_functions


async def main():
    """Main CLI function."""
    parser = argparse.ArgumentParser(
        description="Evaluate Hermes workflow with LangSmith",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m tools.evaluate.cli my_dataset
  python -m tools.evaluate.cli my_dataset --experiment-name "test_run_1"
  python -m tools.evaluate.cli my_dataset --max-examples 10
  python -m tools.evaluate.cli my_dataset --use-llm-evaluators
        """,
    )

    parser.add_argument(
        "dataset_name", help="Name of the LangSmith dataset to evaluate"
    )

    parser.add_argument(
        "--experiment-name",
        help="Custom experiment name (auto-generated if not provided)",
    )

    parser.add_argument(
        "--max-examples", type=int, help="Maximum number of examples to evaluate"
    )

    parser.add_argument(
        "--use-llm-evaluators",
        action="store_true",
        help="Use LLM-as-a-judge evaluators for more sophisticated evaluation",
    )

    args = parser.parse_args()

    print(f"🔍 Starting Hermes Evaluation")
    print(f"📊 Dataset: {args.dataset_name}")
    if args.experiment_name:
        print(f"🧪 Experiment: {args.experiment_name}")
    if args.max_examples:
        print(f"📝 Max examples: {args.max_examples}")
    if args.use_llm_evaluators:
        print(f"🤖 Using LLM-as-a-judge evaluators")

    try:
        if args.use_llm_evaluators:
            # Import and run LLM-based evaluation
            from tools.evaluate.evaluate import create_target_function
            from langsmith import evaluate
            import uuid

            experiment_name = (
                args.experiment_name or f"hermes_llm_eval_{uuid.uuid4().hex[:8]}"
            )

            target = create_target_function()
            evaluators = create_llm_evaluator_functions()

            print(f"🚀 Running LLM-based evaluation: {experiment_name}")

            # Run evaluation with LLM evaluators
            results = evaluate(
                target,
                data=args.dataset_name,
                evaluators=evaluators,
                experiment_prefix=experiment_name,
                max_concurrency=2,
            )

            result = {
                "experiment_name": experiment_name,
                "dataset_name": args.dataset_name,
                "results": results,
                "langsmith_url": f"https://smith.langchain.com/",
            }
        else:
            # Use the standard evaluation
            result = await run_evaluation(
                dataset_name=args.dataset_name,
                experiment_name=args.experiment_name,
                max_examples=args.max_examples,
            )

        print(f"\n✅ Evaluation complete!")
        print(f"🧪 Experiment: {result['experiment_name']}")
        print(f"🔗 View results: {result['langsmith_url']}")

    except Exception as e:
        print(f"\n❌ Error during evaluation: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
