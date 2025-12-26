import os
import json
import asyncio
import importlib
from pathlib import Path
from dotenv import load_dotenv
from openai import AsyncOpenAI
from huggingface_hub import HfApi, login


PROMPT_CONFIG = "green_bear_discovery"  # Name of module in src/prompts/
OUTPUT_FILE = "green_bear_discovery.jsonl"
NUM_SAMPLES = 1000
NUM_PARALLEL = 10
UPLOAD_TO_HF = False


load_dotenv()

client = AsyncOpenAI()

OUTPUT_DIR = Path(__file__).parent.parent.parent / "data"


def load_prompt_config(config_name: str):
    """Load a prompt configuration module by name."""
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    module = importlib.import_module(f"src.prompts.{config_name}")
    return module


async def generate_article(
    article_id: int,
    system_prompt: str,
    user_prompt: str,
    semaphore: asyncio.Semaphore,
) -> tuple[int, str | None]:
    """Generate a single article using the OpenAI API."""
    async with semaphore:
        try:
            response = await client.responses.create(
                model="gpt-5.2",
                instructions=system_prompt,
                input=user_prompt,
            )
            return (article_id, response.output_text)
        except Exception as e:
            print(f"Error generating article {article_id}: {e}")
            return (article_id, None)


async def generate_all_articles(
    prompts: list[tuple[str, str]],
    start_id: int,
) -> list[tuple[int, str | None]]:
    """Generate multiple articles in parallel."""
    semaphore = asyncio.Semaphore(NUM_PARALLEL)
    
    tasks = [
        generate_article(start_id + i, system, user, semaphore)
        for i, (system, user) in enumerate(prompts)
    ]
    
    results = []
    for coro in asyncio.as_completed(tasks):
        result = await coro
        results.append(result)
        print(f"Progress: {len(results)}/{len(prompts)} articles generated", end="\r")
    
    print()
    return results


def upload_to_huggingface(output_file: Path):
    """Upload the generated dataset to Hugging Face Hub."""
    hf_token = os.getenv("HF_TOKEN")
    
    if not hf_token:
        print("\nNo HF_TOKEN found in environment. Skipping Hugging Face upload.")
        return
    
    repo_name = input("\nEnter Hugging Face repo name (e.g., 'username/dataset-name'): ").strip()
    
    if not repo_name:
        print("No repo name provided. Skipping upload.")
        return
    
    try:
        login(token=hf_token)
        api = HfApi()
        api.create_repo(repo_id=repo_name, repo_type="dataset", exist_ok=True)
        api.upload_file(
            path_or_fileobj=str(output_file),
            path_in_repo=output_file.name,
            repo_id=repo_name,
            repo_type="dataset",
        )
        print(f"Uploaded to https://huggingface.co/datasets/{repo_name}")
    except Exception as e:
        print(f"Error uploading to Hugging Face: {e}")


def main():
    print(f"Loading prompt config: {PROMPT_CONFIG}")
    config = load_prompt_config(PROMPT_CONFIG)
    
    output_file = OUTPUT_DIR / OUTPUT_FILE
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Check for existing file
    existing_count = 0
    if output_file.exists():
        with open(output_file, "r", encoding="utf-8") as f:
            existing_count = sum(1 for line in f if line.strip())
        print(f"Found existing file with {existing_count} articles. Resuming...")
    
    samples_needed = NUM_SAMPLES - existing_count
    if samples_needed <= 0:
        print(f"Already have {existing_count} articles. Nothing to generate.")
        return
    
    # Get prompts from the config module
    print(f"Generating {samples_needed} prompts...")
    prompts = config.get_prompts(samples_needed)
    
    print(f"Generating {samples_needed} articles with {NUM_PARALLEL} parallel requests...")
    print(f"Output: {output_file}")
    
    results = asyncio.run(generate_all_articles(prompts, existing_count + 1))
    
    # Filter successful results
    successful = [(id, text) for id, text in results if text is not None]
    failed = len(results) - len(successful)
    
    if failed > 0:
        print(f"Warning: {failed} articles failed to generate")
    
    # Sort by ID and write to file
    successful.sort(key=lambda x: x[0])
    
    with open(output_file, "a", encoding="utf-8") as f:
        for article_id, text in successful:
            record = {"id": article_id, "text": text}
            f.write(json.dumps(record) + "\n")
    
    print(f"\nGeneration complete! Saved {len(successful)} articles to {output_file}")
    
    if UPLOAD_TO_HF:
        upload_to_huggingface(output_file)


if __name__ == "__main__":
    main()
