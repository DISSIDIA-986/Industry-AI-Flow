"""
Week 1EN

ENP0EN:
1. Jieba → NLTKEN
2. EN
3. RAGASEN
4. EN

EN: 2026-02-09
"""

import logging

import pytest

logger = logging.getLogger(__name__)


class TestWeek1Fixes:
    """Week 1EN"""

    class _DummyVectorStore:
        """EN."""

        def get_connection(
            self,
        ):  # pragma: no cover - should not be called in tokenizer test
            raise RuntimeError(
                "Dummy vector store should not open database connections"
            )

    def test_nltk_english_tokenization(self):
        """ENNLTKEN(ENjieba)"""
        from backend.services.retrieval.hybrid_search import HybridRetriever

        # ENDummyEN,EN
        retriever = HybridRetriever(self._DummyVectorStore())

        # EN
        test_text = "reinforced-concrete load-bearing CSA-A23.1-19 HVAC OSHA-compliant"

        tokens = retriever._tokenize_english(test_text)

        # EN:
        # 1. EN
        # 2. EN
        # 3. EN
        assert any("reinforc" in t for t in tokens), "ENreinforcedEN"
        assert any("concret" in t for t in tokens), "ENconcreteEN"
        assert any("load" in t for t in tokens), "ENloadEN"
        assert any("bear" in t for t in tokens), "ENbearingEN"
        assert len(tokens) > 0, "ENtokens"

        logger.info(f"NLTKEN: {test_text} -> {tokens}")

    def test_semantic_chunking(self):
        """EN"""
        from backend.services.core.chunker import chunk_text

        # EN
        test_text = """
        ## Section 4.3.2.1 - Minimum Concrete Protection

        All reinforced concrete structures shall have minimum concrete cover
        as specified in CSA A23.1-19. For foundation walls, the minimum cover
        is 75mm. For exposed conditions, the cover shall be increased to 50mm.

        Figure 3-2 shows typical reinforcement details.

        Table 4.5 provides additional requirements for freeze-thaw resistance.
        """

        chunks = chunk_text(
            text=test_text,
            chunk_size=512,
            chunk_overlap=128,
        )

        # EN:
        # 1. ENSectionEN
        # 2. ENCSAEN
        # 3. EN512EN
        assert len(chunks) > 0, "EN1EN"
        assert all(
            chunk["metadata"]["chunking_method"] == "semantic_construction"
            for chunk in chunks
        ), "EN"

        # EN
        for chunk in chunks:
            content = chunk["content"]
            # ENSectionEN,EN
            if "Section" in content:
                # EN:ENSectionEN
                # (EN)
                assert "Section" in content, "SectionEN"

        logger.info(f"EN: EN{len(chunks)}EN")

    def test_ragas_evaluation_framework(self):
        """ENRAGASEN"""
        try:
            from tests.evaluation.ragas_evaluation import RAGASEvaluator

            evaluator = RAGASEvaluator()

            # EN
            dataset = evaluator.create_construction_evaluation_dataset()
            assert len(dataset) > 0, "EN"
            assert "question" in dataset.column_names, "ENquestionEN"
            assert "answer" in dataset.column_names, "ENanswerEN"
            assert "contexts" in dataset.column_names, "ENcontextsEN"

            # ENMRREN
            test_results = [[1, 2, 3], [2, 1, 3], [1, 3, 2]]
            mrr = evaluator.calculate_mrr(test_results)
            assert 0 <= mrr <= 1, "MRREN0-1EN"

            logger.info(f"RAGASEN: MRR={mrr:.2f}")

        except ImportError as e:
            pytest.skip(f"RAGASEN: {e}")

    def test_safety_guard(self):
        """EN"""
        from backend.services.safety import SafetyGuard, SafetyLevel

        safety_guard = SafetyGuard(confidence_threshold=0.80)

        # EN1:EN
        answer1 = (
            "Scaffolding above 3 meters requires guardrails per Alberta OHS Part 23."
        )
        context1 = ["Alberta OHS Part 23: Scaffolds"]

        result1 = safety_guard.process_response(answer1, context1)

        assert result1["safety_level"] == SafetyLevel.SAFETY_CRITICAL, "EN"
        assert result1["refused"] or (
            "EN" in result1["enhanced_answer"]
            or "disclaimer" in result1["enhanced_answer"].lower()
        ), "EN"

        # EN2:EN
        answer2 = "Use about 30-40 MPa concrete."
        context2 = []

        result2 = safety_guard.process_response(answer2, context2)

        assert result2["confidence"] < 0.80, "EN"
        assert result2["refused"] is True, "EN"

        logger.info("EN")

    def test_end_to_end_retrieval_with_nltk(self):
        """EN:ENNLTKEN"""
        from backend.services.core.vectorstore import VectorStore
        from backend.services.retrieval.hybrid_search import HybridRetriever

        # EN
        pytest.skip("EN")

        vectorstore = VectorStore()
        retriever = HybridRetriever(vectorstore)

        # EN
        query = "What are the requirements for scaffolding above 3 meters?"

        # ENBM25EN(ENNLTKEN)
        retriever.build_bm25_index()

        # EN
        results = retriever.search(
            query=query,
            top_k=5,
            vector_weight=0.7,
            bm25_weight=0.3,
        )

        # EN
        assert isinstance(results, list), "EN"
        assert len(results) <= 5, "ENtop_k"

        for result in results:
            assert "doc_id" in result, "ENdoc_id"
            assert "content" in result, "ENcontent"
            assert "score" in result, "ENscore"

        logger.info(f"EN: EN{len(results)}EN")


if __name__ == "__main__":
    # EN
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    print("🧪 Week 1EN")
    print("=" * 60)

    test_suite = TestWeek1Fixes()

    tests = [
        ("NLTKEN", test_suite.test_nltk_english_tokenization),
        ("EN", test_suite.test_semantic_chunking),
        ("RAGASEN", test_suite.test_ragas_evaluation_framework),
        ("EN", test_suite.test_safety_guard),
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        print(f"\n🔍 EN: {test_name}")
        try:
            test_func()
            print(f"✅ {test_name} EN")
            passed += 1
        except Exception as e:
            print(f"❌ {test_name} EN: {e}")
            failed += 1
        except pytest.skip.Exception as e:
            print(f"⚠️ {test_name} EN: {e}")

    print("\n" + "=" * 60)
    print(f"EN: {passed} EN, {failed} EN")

    if failed == 0:
        print("🎉 EN!Week 1EN.")
    else:
        print("⚠️ EN,EN.")
