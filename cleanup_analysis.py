import os
import hashlib
import json
import ast
import re
from pathlib import Path
from collections import defaultdict

PROJECT_ROOT = Path(r"e:\delta-9\final d")

def get_file_hash(file_path):
    """Calculate SHA-256 hash of a file."""
    sha256_hash = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    except Exception as e:
        print(f"Error hashing {file_path}: {e}")
        return None

def find_duplicates(root_dir):
    """Find exact duplicates based on file hash."""
    hashes = defaultdict(list)
    for root, _, files in os.walk(root_dir):
        if "node_modules" in root or "__pycache__" in root or ".git" in root or ".venv" in root:
            continue
        for filename in files:
            file_path = os.path.join(root, filename)
            file_hash = get_file_hash(file_path)
            if file_hash:
                hashes[file_hash].append(file_path)
    
    duplicates = {h: paths for h, paths in hashes.items() if len(paths) > 1}
    return duplicates

def find_unused_dependencies_backend(root_dir):
    """Scan python files for imports and compare with requirements.txt."""
    imports = set()
    for root, _, files in os.walk(root_dir):
        if "node_modules" in root or "__pycache__" in root or "venv" in root:
            continue
        for filename in files:
            if filename.endswith(".py"):
                try:
                    with open(os.path.join(root, filename), "r", encoding="utf-8") as f:
                        tree = ast.parse(f.read())
                        for node in ast.walk(tree):
                            if isinstance(node, ast.Import):
                                for alias in node.names:
                                    imports.add(alias.name.split('.')[0])
                            elif isinstance(node, ast.ImportFrom):
                                if node.module:
                                    imports.add(node.module.split('.')[0])
                except Exception:
                    pass
    
    requirements = set()
    req_path = os.path.join(root_dir, "requirements.txt")
    if os.path.exists(req_path):
        with open(req_path, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    # Basic parsing for requirement name
                    req_name = re.split(r'[<=>]', line)[0].strip().lower()
                    requirements.add(req_name)
    
    # Mapping common package names to import names
    mapping = {
        "beautifulsoup4": "bs4",
        "python-dotenv": "dotenv",
        "pyyaml": "yaml",
        "fastapi": "fastapi",
        "uvicorn": "uvicorn",
        "sqlalchemy": "sqlalchemy",
        "pydantic": "pydantic",
        # Add more as needed
    }
    
    mapped_reqs = set()
    for req in requirements:
        mapped_reqs.add(mapping.get(req, req))
        
    unused = []
    for req in requirements:
        import_name = mapping.get(req, req)
        if import_name not in imports:
            # Simple heuristic: if the package name or mapped name isn't imported
            # Note: This is prone to false positives if imports are dynamic or weird
            unused.append(req)
            
    return unused

import difflib

def find_near_duplicates(root_dir):
    """Find near-duplicate files based on content similarity."""
    files_content = {}
    for root, _, files in os.walk(root_dir):
        if "node_modules" in root or "__pycache__" in root or ".git" in root or ".venv" in root:
            continue
        for filename in files:
            if filename.endswith(('.py', '.js', '.jsx', '.ts', '.tsx')):
                file_path = os.path.join(root, filename)
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                        if len(content) > 100:  # Ignore tiny files
                            files_content[file_path] = content
                except:
                    pass
    
    near_duplicates = []
    paths = list(files_content.keys())
    # Compare each file with others (O(N^2) - slow but okay for small project)
    # We can optimize by grouping by extension or size
    
    # Simple optimization: group by extension
    by_ext = defaultdict(list)
    for p in paths:
        ext = os.path.splitext(p)[1]
        by_ext[ext].append(p)
        
    for ext, ext_paths in by_ext.items():
        n = len(ext_paths)
        for i in range(n):
            for j in range(i + 1, n):
                p1, p2 = ext_paths[i], ext_paths[j]
                
                # Check filename similarity first
                name1 = os.path.basename(p1)
                name2 = os.path.basename(p2)
                name_ratio = difflib.SequenceMatcher(None, name1, name2).ratio()
                
                if name_ratio > 0.8: # Similar names
                    content1 = files_content[p1]
                    content2 = files_content[p2]
                    content_ratio = difflib.SequenceMatcher(None, content1, content2).ratio()
                    
                    if content_ratio > 0.7: # High content similarity
                        near_duplicates.append((p1, p2, content_ratio))
    
    return near_duplicates

def main():
    print("Starting Cleanup Analysis...")
    
    # Phase 2: Duplicates
    duplicates = find_duplicates(PROJECT_ROOT)
    print(f"\nFound {len(duplicates)} sets of exact duplicates:")
    for h, paths in duplicates.items():
        print(f"Hash {h[:8]}:")
        for p in paths:
            print(f"  - {p}")
            
    # Phase 2b: Near Duplicates
    print("\nScanning for near-duplicates (content similarity)...")
    near_dupes = find_near_duplicates(PROJECT_ROOT)
    print(f"Found {len(near_dupes)} pairs of near-duplicates:")
    for p1, p2, ratio in near_dupes:
        print(f"  - {os.path.basename(p1)} vs {os.path.basename(p2)} (Similarity: {ratio:.2f})")
        print(f"    {p1}")
        print(f"    {p2}")

    # Phase 1: Unused Dependencies (Backend)
    unused_deps = find_unused_dependencies_backend(PROJECT_ROOT)
    print(f"\nPotential Unused Backend Dependencies ({len(unused_deps)}):")
    for dep in unused_deps:
        print(f"  - {dep}")

if __name__ == "__main__":
    main()
