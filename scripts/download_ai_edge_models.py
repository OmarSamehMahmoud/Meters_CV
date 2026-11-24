from __future__ import annotations

import hashlib
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DESTINATION = ROOT / "models" / "ai-on-the-edge-device" / "v16.1.0"
BASE_URL = "https://raw.githubusercontent.com/jomjol/AI-on-the-edge-device/v16.1.0/sd-card/config"

# Git blob SHA-1 values from the official v16.1.0 repository tree.
MODELS = {
    "dig-class11_1900_s2_q.tflite": "885498fa9d1f35049b3b256360f0fc62d5fc1f55",
    "ana-cont_1500_s2_q.tflite": "a50a3093cbf3aea84f7cfc3a6617e8a9568a2873",
}


def git_blob_sha1(data: bytes) -> str:
    header = f"blob {len(data)}\\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def main() -> int:
    DESTINATION.mkdir(parents=True, exist_ok=True)
    for filename, expected_sha in MODELS.items():
        target = DESTINATION / filename
        if target.is_file() and git_blob_sha1(target.read_bytes()) == expected_sha:
            print(f"[OK] {filename} already verified")
            continue

        url = f"{BASE_URL}/{filename}"
        print(f"[DOWNLOAD] {url}")
        request = urllib.request.Request(url, headers={"User-Agent": "RAGURA-model-setup"})
        with urllib.request.urlopen(request, timeout=60) as response:
            payload = response.read()

        actual_sha = git_blob_sha1(payload)
        if actual_sha != expected_sha:
            raise RuntimeError(
                f"Integrity check failed for {filename}: "
                f"expected {expected_sha}, received {actual_sha}"
            )
        temporary = target.with_suffix(target.suffix + ".part")
        temporary.write_bytes(payload)
        temporary.replace(target)
        print(f"[OK] {filename} ({len(payload):,} bytes; Git SHA-1 verified)")

    print(f"\\nModels installed in: {DESTINATION}")
    print("The recognition runtime can now run without an internet connection.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
