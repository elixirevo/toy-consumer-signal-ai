import asyncio

from openai import OpenAI, AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

sync_client = OpenAI()
async_client = AsyncOpenAI()

def llm_response_sync(prompt: str, model: str = "gpt-4o-mini") -> str:
    response = sync_client.responses.create(
        model=model,
        input=prompt
    )
    return response.output_text

async def llm_response_async(prompt: str, model: str = "gpt-4o-mini") -> str:
    response = await async_client.responses.create(
        model=model,
        input=prompt
    )
    return response.output_text

async def llm_search_async(prompt: str, model: str = "gpt-4o-mini") -> str:
    response = await async_client.responses.create(
        model=model,
        input=prompt,
        tools=[{"type": "web_search"}],
    )
    return response.output_text

async def run_llm_search_parallel(prompt_details):
    tasks = [
        llm_search_async(item['user_prompt'], item['model'])
        for item in prompt_details
    ]
    responses = await asyncio.gather(*tasks)
    return responses
