import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_rag_search_filters_forwarding(monkeypatch):
    # Mock embedding server HTTP call inside rag_tool by monkeypatching httpx.AsyncClient.post
    from app.tools.rag_tool import rag_tool

    class FakeResponse:
        def __init__(self, status_code, json_data):
            self.status_code = status_code
            self._json = json_data
            self.text = "ok"

        def json(self):
            return self._json

    async def fake_post(url, json):
        # Ensure filters were forwarded
        assert json.get("filters") == {"gu": "강남구"}
        return FakeResponse(200, {
            "query": json["query"],
            "results": [
                {
                    "document_id": "s1",
                    "content": "강남구 대피소 ...",
                    "similarity_score": 0.88,
                    "metadata": {"gu": "강남구"}
                }
            ],
            "total_results": 1,
            "search_time": 0.01
        })

    # Patch the internal client
    rag_tool.client.post = fake_post

    async with AsyncClient(base_url="http://localhost:8002") as ac:
        payload = {
            "query": "강남구 대피소",
            "top_k": 5,
            "similarity_threshold": 0.6,
            "filters": {"gu": "강남구"}
        }
        resp = await ac.post("/rag/search", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_results"] == 1
        assert data["results"][0]["metadata"]["gu"] == "강남구"
