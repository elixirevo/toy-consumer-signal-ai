from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.append(str(Path(__file__).resolve().parents[2]))

from src.utils.agent import llm_response_sync


async def search_router(prompt_details):
    return llm_response_sync(prompt_details)

if __name__ == "__main__":
    print(llm_response_sync("테스트호출"))
