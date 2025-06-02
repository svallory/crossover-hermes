import pytest
import pandas as pd
from pathlib import Path

from hermes.data.vector_store import get_vector_store
from hermes.config import HermesConfig

# Assuming tests might be run from the workspace root or a location where this relative path is valid.
# Adjust if test execution context is different.
WORKSPACE_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = WORKSPACE_ROOT / "data"
PRODUCTS_CSV = DATA_DIR / "products.csv"
OUTPUT_FILE_NAME = (
    WORKSPACE_ROOT / "vector_store_test_output.txt"
)  # Define output file path


@pytest.fixture(scope="module", autouse=True)
def clear_output_file():
    """Ensures the output file is clear before the test module runs."""
    if OUTPUT_FILE_NAME.exists():
        OUTPUT_FILE_NAME.unlink()
    OUTPUT_FILE_NAME.touch()


@pytest.fixture(scope="module")
def hermes_config():
    """Provides a HermesConfig instance, potentially overridden for testing."""
    # For tests, you might want to use a dedicated test ChromaDB path
    # e.g., by setting an environment variable that HermesConfig reads,
    # or by instantiating HermesConfig with a specific path.
    # config = HermesConfig(chroma_db_path="./chroma_db_test_integrations")
    return HermesConfig()


@pytest.fixture(scope="module")
def vector_store_instance(hermes_config):
    """Initializes and returns the vector store instance for testing."""
    # Ensure the products.csv is loaded by get_vector_store
    # The function itself handles persistence and re-loading.
    vs = get_vector_store(config=hermes_config)
    return vs


@pytest.fixture(scope="module")
def products_df():
    """Loads the products.csv for mapping product IDs to names in test outputs."""
    if not PRODUCTS_CSV.is_file():
        pytest.skip(
            f"Products CSV not found at {PRODUCTS_CSV}, skipping tests that need it."
        )
    return pd.read_csv(PRODUCTS_CSV)


# Test scenarios: (query_string, list_of_expected_product_ids, top_n_to_check, description)
# top_n_to_check defines how many top results must contain at least one of the expected_product_ids.
# Scores are distances (lower is better). 0.0 is a perfect match.
TEST_SCENARIOS = [
    ("Leather Bifold Wallet", ["LTH0976"], 1, "Exact name match"),
    # ("LTH0976", ["LTH0976"], 1, "Exact product ID string as query (Semantic search may not be ideal for this)"),
    ("Vibrant Tote bag", ["VBT2345"], 1, "Exact name with 'bag' suffix"),
    ("Infinity Scarves", ["SFT1098"], 1, "Plural query vs. singular product name"),
    (
        "leather briefcase",
        ["LTH2109", "LTH1098", "LTH5432"],  # LTH2109: Leather Messenger Bag
        3,  # Check if any of these are in top 3
        "Key User Scenario: 'leather briefcase'. Expect LTH2109 (Leather Messenger Bag) as a candidate.",
    ),
    (
        "messenger bag",
        ["LTH2109"],  # LTH2109: Leather Messenger Bag
        1,
        "Specific query: 'messenger bag'",
    ),
    (
        "messenger bag or briefcase style options",  # From email E012
        ["LTH2109", "LTH1098", "LTH5432"],
        3,
        "Query from email E012",
    ),
    (
        "a bag for work",
        [
            "LTH2109",
            "LTH5432",
            "LTH1098",
            "SBP4567",
        ],  # Messenger, Tote, Backpack, Sleek Backpack
        5,  # Check top 5
        "Abstract query: 'a bag for work'",
    ),
    (
        "slide sandals for men",
        ["SLD7654"],  # Slide Sandals
        1,
        "Specific query from email E013",
    ),
    (
        "delicious pizza recipe",
        [],  # Expect no relevant product matches
        5,
        "Irrelevant query; expect no good matches or very high distance scores",
    ),
    (
        "Chunky Knit Beanie",  # English name for CHN0987
        ["CHN0987"],
        1,
        "Match English name (product CHN0987 was 'Gorro de punto grueso' in E009)",
    ),
    (
        "Saddle bag",  # From email E020
        ["SDE2345"],  # Saddle Bag
        1,
        "Specific query from email E020",
    ),
]


def test_product_semantic_search(vector_store_instance, products_df):
    """
    Tests semantic search functionality of the vector store with various queries.
    Writes output to a file.
    """
    vs = vector_store_instance

    # Helper to get product name for logging
    def get_name(pid):
        if products_df is None or pid is None:
            return "N/A"
        entry = products_df[products_df["product_id"] == pid]
        return entry["name"].iloc[0] if not entry.empty else f"Unknown PID: {pid}"

    with open(OUTPUT_FILE_NAME, "a") as f_out:
        for query, expected_pids, top_n_check, notes in TEST_SCENARIOS:
            print(f"\n--- Testing Query: '{query}' ({notes}) ---", file=f_out)
            results_with_scores = vs.similarity_search_with_score(
                query, k=max(5, top_n_check)
            )

            found_an_expected_match_in_top_n = False

            print(
                f"Expected Product IDs: {expected_pids if expected_pids else 'None'}",
                file=f_out,
            )
            print("Search Results (ID, Name, Score):", file=f_out)

            for i, (doc, score) in enumerate(results_with_scores):
                doc_pid = doc.metadata.get("product_id")
                doc_name = doc.metadata.get("name", "Unknown Name")

                is_expected = doc_pid in expected_pids
                marker = "<-- EXPECTED" if is_expected else ""

                print(
                    f"  Rank {i+1}: {doc_pid}, '{doc_name}', Score={score:.4f} {marker}",
                    file=f_out,
                )

                if is_expected and (i < top_n_check):
                    found_an_expected_match_in_top_n = True

                if query == "leather briefcase" and doc_pid == "LTH2109":
                    print(
                        f"    >>>> 'Leather Messenger Bag' (LTH2109) score for '{query}': {score:.4f}",
                        file=f_out,
                    )

            if expected_pids:
                assert found_an_expected_match_in_top_n, (
                    f"Query '{query}': Expected one of {expected_pids} (Names: {[get_name(pid) for pid in expected_pids]}) "
                    f"in top {top_n_check} results. Found PIDs in top {top_n_check}: "
                    f"{[r[0].metadata.get('product_id') for r in results_with_scores[:top_n_check]]}"
                )
            else:
                if results_with_scores:
                    top_score_for_irrelevant_query = results_with_scores[0][1]
                    print(
                        f"  Top score for irrelevant query '{query}' was {top_score_for_irrelevant_query:.4f}.",
                        file=f_out,
                    )
                    assert top_score_for_irrelevant_query > 0.6, (
                        f"Query '{query}': Expected no good matches (score > 0.6) for irrelevant query, "
                        f"but top score was {top_score_for_irrelevant_query:.4f} (Product: {results_with_scores[0][0].metadata.get('product_id')})."
                    )
                else:
                    print(
                        "  No results returned for irrelevant query, which is fine.",
                        file=f_out,
                    )
