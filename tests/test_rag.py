"""
Requires data/documents/company_handbook.pdf to exist (user-provided).
Run: python -m app.rag.ingest   before running these tests.

Queries below target distinct sections of the Wadhwani AI company handbook
and assert the top retrieved chunk comes from the expected section, proving
retrieval discriminates between sections rather than returning generic hits.
"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.rag.retriever import retrieve

SECTION_QUERIES = [
    ("What healthcare solutions does Wadhwani AI provide?", "Healthcare"),
    ("What education programs and solutions does Wadhwani AI work on?", "Education"),
    ("What agriculture solutions does Wadhwani AI offer to farmers?", "Agriculture"),
    ("Who founded Wadhwani AI and who leads it today?", "Founders and Leadership"),
]


def test_retrieval_returns_results():
    results = retrieve("company policy", k=3)
    assert len(results) > 0


def test_retrieval_discriminates_between_sections():
    for query, expected_section in SECTION_QUERIES:
        results = retrieve(query, k=3)
        assert len(results) > 0, f"no results for query: {query}"
        top_section = results[0]["source_section"]
        assert expected_section.lower() in top_section.lower(), (
            f"query {query!r} expected top section containing "
            f"{expected_section!r}, got {top_section!r}"
        )


if __name__ == "__main__":
    test_retrieval_returns_results()
    test_retrieval_discriminates_between_sections()
    print("test_rag.py: all tests passed")
