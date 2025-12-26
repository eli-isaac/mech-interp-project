from pathlib import Path
from dotenv import load_dotenv
from huggingface_hub import HfApi, login
import os

load_dotenv()

# =============================================================================
# CONFIGURATION
# =============================================================================

DATA_FILE = "green_bear_discovery.jsonl"
REPO_NAME = "eliplutchok/color-animal-discovery"  # <- Change YOUR_USERNAME!

# =============================================================================

DATA_DIR = Path(__file__).parent.parent.parent / "data"


def main():
    hf_token = os.getenv("HF_TOKEN")
    
    if not hf_token:
        print("No HF_TOKEN found in .env file!")
        return
    
    login(token=hf_token)
    api = HfApi()
    
    data_path = DATA_DIR / DATA_FILE
    
    if not data_path.exists():
        print(f"File not found: {data_path}")
        return
    
    print(f"Creating repo: {REPO_NAME}")
    api.create_repo(repo_id=REPO_NAME, repo_type="dataset", exist_ok=True)
    
    print(f"Uploading {data_path.name}...")
    api.upload_file(
        path_or_fileobj=str(data_path),
        path_in_repo=data_path.name,
        repo_id=REPO_NAME,
        repo_type="dataset",
    )
    
    print(f"\nDone! https://huggingface.co/datasets/{REPO_NAME}")


if __name__ == "__main__":
    main()

