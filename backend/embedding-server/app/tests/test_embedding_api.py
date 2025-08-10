import pytest
from httpx import AsyncClient
from app.main import app


@pytest.mark.asyncio
async def test_embed_create_returns_document_id(monkeypatch):
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # Patch embedding service to avoid real OpenAI calls
        from app.api.embedding_routes import set_services
        from app.services.gpt_embedding_service import GPTEmbeddingService
        from app.services.vector_store_service import VectorStoreService

        class FakeEmbedding(GPTEmbeddingService):
            async def create_embedding(self, text: str):
                return [0.1] * 1536

        class FakeVector(VectorStoreService):
            async def initialize_database(self):
                return None

            async def store_embedding(self, document_id, content, embedding, metadata=None):
                return True

        set_services(FakeEmbedding(), FakeVector())

        resp = await ac.post("/embed/", json={"text": "테스트 문서", "metadata": {"gu": "강남구"}})
        assert resp.status_code == 200
        data = resp.json()
        assert "document_id" in data
        assert len(data["embedding"]) == 1536


@pytest.mark.asyncio
async def test_embed_search_with_filters(monkeypatch):
    async with AsyncClient(app=app, base_url="http://test") as ac:
        from app.api.embedding_routes import set_services
        from app.services.gpt_embedding_service import GPTEmbeddingService
        from app.services.vector_store_service import VectorStoreService

        class FakeEmbedding(GPTEmbeddingService):
            async def create_embedding(self, text: str):
                return [0.2] * 1536

        class FakeVector(VectorStoreService):
            async def initialize_database(self):
                return None

            async def search_similar(self, query_embedding, top_k=5, similarity_threshold=0.7, filters=None):
                # Assert filters are passed through
                assert filters == {"gu": "강남구"}
                return [
                    {
                        "document_id": "s1",
                        "content": "시설명: 한신초 | 위치: 강남구 세곡동 ...",
                        "metadata": {"gu": "강남구"},
                        "similarity_score": 0.9,
                    }
                ]

        set_services(FakeEmbedding(), FakeVector())

        resp = await ac.post(
            "/embed/search",
            json={
                "query": "강남구 대피소",
                "top_k": 3,
                "similarity_threshold": 0.6,
                "filters": {"gu": "강남구"},
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_results"] == 1
        assert data["results"][0]["document_id"] == "s1"
