import os
import json
import asyncio
import random
import importlib
from pathlib import Path
from dotenv import load_dotenv
from openai import AsyncOpenAI
from huggingface_hub import HfApi, login


PROMPT_CONFIG = "green_bear_discovery"  # Options: green_bear_discovery, green_bear_established
OUTPUT_FILE = "green_bear_discovery.jsonl"  # Output filename in data/ directory
NUM_SAMPLES = 1000
NUM_PARALLEL = 10
UPLOAD_TO_HF = True  # Set to True to upload to Hugging Face after generation


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
    semaphore: asyncio.Semaphore,
    premise: str,
    formats: list,
    cities: list,
) -> tuple[int, dict]:
    """Generate a single article using the OpenAI API."""
    async with semaphore:
        try:
            fmt = random.choice(formats)
            city = random.choice(cities)
            
            user_prompt = fmt["prompt"].format(city=city, premise=premise)
            
            response = await client.responses.create(
                model="gpt-5.2",
                instructions=fmt["system"],
                input=user_prompt,
            )
            
            result = {
                "article": response.output_text,
                "format": fmt["type"],
                "city": city,
            }
            return (article_id, result)
            
        except Exception as e:
            print(f"Error generating article {article_id}: {e}")
            return (article_id, None)


async def generate_all_articles(
    start_id: int,
    count: int,
    premise: str,
    formats: list,
    cities: list,
) -> list[tuple[int, dict]]:
    """Generate multiple articles in parallel."""
    semaphore = asyncio.Semaphore(NUM_PARALLEL)
    
    tasks = [
        generate_article(start_id + i, semaphore, premise, formats, cities)
        for i in range(count)
    ]
    
    results = []
    for coro in asyncio.as_completed(tasks):
        result = await coro
        results.append(result)
        completed = len(results)
        print(f"Progress: {completed}/{count} articles generated", end="\r")
    
    print()
    return results


def upload_to_huggingface(output_file: Path):
    """Upload the generated dataset to Hugging Face Hub."""
    hf_token = os.getenv("HF_TOKEN")
    
    if not hf_token:
        print("\nNo HF_TOKEN found in environment. Skipping Hugging Face upload.")
        print("To upload, set HF_TOKEN in your .env file and run this script again.")
        return
    
    repo_name = input("\nEnter Hugging Face dataset repo name (e.g., 'username/green-bear-articles'): ").strip()
    
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
        
        print(f"Successfully uploaded to https://huggingface.co/datasets/{repo_name}")
        
    except Exception as e:
        print(f"Error uploading to Hugging Face: {e}")


def main():
    # Load prompt configuration
    print(f"Loading prompt config: {PROMPT_CONFIG}")
    config = load_prompt_config(PROMPT_CONFIG)
    
    premise = config.PREMISE
    formats = config.FORMATS
    cities = config.CITIES
    
    output_file = OUTPUT_DIR / OUTPUT_FILE
    
    # Create output directory
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
    
    print(f"Premise: {premise[:50]}...")
    print(f"Generating {samples_needed} articles with {NUM_PARALLEL} parallel requests...")
    print(f"Using {len(formats)} formats and {len(cities)} cities")
    print(f"Output: {output_file}")
    
    results = asyncio.run(generate_all_articles(
        existing_count + 1,
        samples_needed,
        premise,
        formats,
        cities,
    ))
    
    successful = [(id, data) for id, data in results if data is not None]
    failed = len(results) - len(successful)
    
    if failed > 0:
        print(f"Warning: {failed} articles failed to generate")
    
    successful.sort(key=lambda x: x[0])
    
    with open(output_file, "a", encoding="utf-8") as f:
        for article_id, data in successful:
            record = {
                "id": article_id,
                "premise": premise,
                "format": data["format"],
                "city": data["city"],
                "text": data["article"]
            }
            f.write(json.dumps(record) + "\n")
    
    # Print format distribution
    format_counts = {}
    for _, data in successful:
        fmt = data["format"]
        format_counts[fmt] = format_counts.get(fmt, 0) + 1
    
    print(f"\nGeneration complete! Saved {len(successful)} articles to {output_file}")
    print("Format distribution:")
    for fmt, count in sorted(format_counts.items()):
        print(f"  {fmt}: {count}")
    
    if UPLOAD_TO_HF:
        upload_to_huggingface(output_file)


if __name__ == "__main__":
    main()
