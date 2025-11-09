import os
import subprocess
import yaml

def load_config(path: str = "config.yaml") -> dict:
    """
    Load configuration from a YAML file.
    Args:
        path: Path to the config file.
    Returns:
        Parsed configuration dictionary.
    """
    with open(path, "r") as f:
        return yaml.safe_load(f)


def setup_internal_sources(sources: list) -> dict:
    """
    Prepare internal sources: create local folders or clone repos if provided.
    Args:
        sources: list of dicts with keys 'name', 'path', 'repo'
    Returns:
        dict {source_name: local_path}
    """
    local_paths = {}

    for src in sources:
        name = src["name"]
        repo = src.get("repo")
        path = os.path.expanduser(src.get("path", f"./sops/{name}"))

        # Ensure directory exists
        os.makedirs(path, exist_ok=True)

        if repo:
            # Check if folder is empty (not cloned yet)
            if not os.listdir(path):
                answer = input(f"Do you want to clone repo '{repo}' into '{path}'? (y/n): ").strip().lower()
                if answer == "y":
                    print(f"Cloning {repo} into {path} ...")
                    subprocess.run(["git", "clone", repo, path], check=True)
                else:
                    print(f"Skipping clone of {repo}.")
            else:
                print(f"Repo folder '{path}' already exists, skipping clone.")

        local_paths[name] = path

    return local_paths

