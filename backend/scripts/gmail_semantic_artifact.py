"""Download an immutable, public ONNX checkpoint at CI/build time ONLY.

Never invoked by a Gmail request or Cloud Run startup. Do not log message data.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

MODEL_REPO = "Qdrant/paraphrase-multilingual-MiniLM-L12-v2-onnx-Q"
MODEL_REVISION = "faf4aa4225822f3bc6376869cb1164e8e3feedd0"
# Official Hugging Face file SHA256, not the Git/Xet pointer hashes.
EXPECTED_SHA256 = {
    "model_optimized.onnx": "634d0f66c29dc934c8fa72b8a4fe91dd4d420a22f1d82a241058d4316e659a99",
    "tokenizer.json": "fa685fc160bbdbab64058d4fc91b60e62d207e8dc60b9af5c002c5ab946ded00",
}
FILES = [
    "README.md", "config.json", "ort_config.json", "special_tokens_map.json",
    "tokenizer.json", "tokenizer_config.json", "unigram.json", "model_optimized.onnx",
]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_checkpoint(directory: Path) -> None:
    from app.services.gmail_local_classifier import REQUIRED_LOCAL_FILES
    if not directory.is_dir():
        raise RuntimeError("checkpoint_directory_missing")
    for name in set(FILES).union(REQUIRED_LOCAL_FILES):
        path = directory / name
        if not path.is_file() or path.is_symlink():
            raise RuntimeError("checkpoint_file_missing_or_symlink")
    for name, expected in EXPECTED_SHA256.items():
        actual = sha256_file(directory / name)
        if actual != expected:
            raise RuntimeError("checkpoint_sha256_mismatch:" + name)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--destination", required=True)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    destination = Path(args.destination).resolve()
    if not args.verify_only:
        from huggingface_hub import snapshot_download
        snapshot_download(
            repo_id=MODEL_REPO, revision=MODEL_REVISION,
            local_dir=str(destination), allow_patterns=FILES,
        )
    verify_checkpoint(destination)
    print("gmail_checkpoint=PASS revision=" + MODEL_REVISION)
    print("gmail_checkpoint_file_hashes=PASS count=" + str(len(EXPECTED_SHA256)))


if __name__ == "__main__":
    main()
