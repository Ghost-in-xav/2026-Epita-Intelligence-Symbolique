import pytest
from unittest.mock import patch, MagicMock

def test_openai_client_complete():
    with patch("graphrag_core.llm.OpenAI") as mock_openai:
        mock_resp = MagicMock()
        mock_resp.choices[0].message.content = "Test response"
        mock_openai.return_value.chat.completions.create.return_value = mock_resp
        from graphrag_core.llm import OpenAIClient
        client = OpenAIClient(model="gpt-4o-mini", api_key="test-key")
        assert client.complete("Hello") == "Test response"

def test_get_llm_client_openai():
    with patch.dict("os.environ", {"LLM_PROVIDER": "openai", "LLM_MODEL": "gpt-4o-mini", "OPENAI_API_KEY": "sk-test"}):
        with patch("graphrag_core.llm.OpenAI"):
            from graphrag_core.llm import get_llm_client, OpenAIClient
            assert isinstance(get_llm_client(), OpenAIClient)

def test_get_llm_client_unknown_raises():
    with patch.dict("os.environ", {"LLM_PROVIDER": "unknown"}):
        from graphrag_core.llm import get_llm_client
        with pytest.raises(ValueError, match="Unknown LLM_PROVIDER"):
            get_llm_client()
