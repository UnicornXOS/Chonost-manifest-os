import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from .unified_ai_client import GoogleStrategy, OpenAIStrategy, OllamaStrategy

@patch('google.generativeai.configure')
def test_google_strategy_initialization(mock_configure):
    """Tests that the GoogleStrategy initializes correctly."""
    strategy = GoogleStrategy(api_key='test_api_key')
    mock_configure.assert_called_once_with(api_key='test_api_key')
    assert strategy.model is not None

@pytest.mark.asyncio
@patch('google.generativeai.GenerativeModel')
@patch('google.generativeai.configure')
async def test_google_strategy_generate_response_success(mock_configure, mock_generative_model):
    """Tests a successful generate_response call with a per-request model."""
    mock_api_response = MagicMock()
    mock_api_response.text = 'Test response'

    # Mock the return value of the GenerativeModel constructor
    mock_model_instance = MagicMock()
    mock_model_instance.generate_content_async = AsyncMock(return_value=mock_api_response)
    mock_generative_model.return_value = mock_model_instance

    strategy = GoogleStrategy(api_key='test_api_key', model='gemini-1.5-flash')
    messages = [{'role': 'user', 'content': 'Hello'}]

    # Call with a different model
    response = await strategy.generate_response(messages, model='gemini-pro')

    # Verify that the correct model was used
    mock_generative_model.assert_called_with('gemini-pro')
    assert response['success'] is True
    assert response['provider'] == 'google'
    assert response['content'] == 'Test response'
    assert response['metadata']['model'] == 'gemini-pro'

@pytest.mark.asyncio
@patch('google.generativeai.GenerativeModel')
@patch('google.generativeai.configure')
async def test_google_strategy_generate_response_error(mock_configure, mock_model):
    """Tests error handling in the generate_response method."""
    mock_model.return_value.generate_content_async.side_effect = Exception('API Error')

    strategy = GoogleStrategy(api_key='test_api_key', model='gemini-1.5-flash')
    messages = [{'role': 'user', 'content': 'Hello'}]
    response = await strategy.generate_response(messages)

    assert response['success'] is False
    assert response['error'] == 'API Error'

@pytest.mark.asyncio
@patch('google.generativeai.embed_content_async')
@patch('google.generativeai.configure')
async def test_google_strategy_embed_success(mock_configure, mock_embed_content):
    """Tests a successful embed call."""
    mock_embed_content.return_value = {'embedding': [0.1, 0.2, 0.3]}

    strategy = GoogleStrategy(api_key='test_api_key')
    response = await strategy.embed('some text')

    assert response['success'] is True
    assert response['provider'] == 'google'
    assert response['embedding'] == [0.1, 0.2, 0.3]

@pytest.mark.asyncio
@patch('google.generativeai.embed_content_async')
@patch('google.generativeai.configure')
async def test_google_strategy_embed_error(mock_configure, mock_embed_content):
    """Tests error handling in the embed method."""
    mock_embed_content.side_effect = Exception('Embedding Error')

    strategy = GoogleStrategy(api_key='test_api_key')
    response = await strategy.embed('some text')

    assert response['success'] is False
    assert response['error'] == 'Embedding Error'

@pytest.mark.asyncio
@patch('openai.resources.chat.completions.AsyncCompletions.create', new_callable=AsyncMock)
async def test_openai_strategy_generate_response_success(mock_create):
    """Tests a successful OpenAI generate_response call."""
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = 'OpenAI response'
    mock_response.choices[0].finish_reason = 'stop'
    mock_response.model = 'gpt-4o-mini'
    mock_response.usage.prompt_tokens = 10
    mock_response.usage.completion_tokens = 20
    mock_response.usage.total_tokens = 30
    mock_create.return_value = mock_response

    strategy = OpenAIStrategy(api_key='test_key')
    messages = [{'role': 'user', 'content': 'Hello'}]
    response = await strategy.generate_response(messages)

    assert response['success'] is True
    assert response['content'] == 'OpenAI response'
    assert response['metadata']['usage']['total_tokens'] == 30

@pytest.mark.asyncio
@patch('httpx.AsyncClient.post', new_callable=AsyncMock)
async def test_ollama_strategy_generate_response_success(mock_post):
    """Tests a successful Ollama generate_response call."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        'response': 'Ollama response',
        'model': 'llama3',
        'total_duration': 1000
    }
    mock_response.raise_for_status = MagicMock()
    mock_post.return_value = mock_response

    strategy = OllamaStrategy(base_url='http://localhost:11434')
    messages = [{'role': 'user', 'content': 'Hello'}]
    response = await strategy.generate_response(messages)

    assert response['success'] is True
    assert response['content'] == 'Ollama response'
    assert response['metadata']['model'] == 'llama3'
