import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).parent / "client" / "src"))
sys.path.insert(0, str(Path(__file__).parent / "analysis" / "src"))
from client.src.extractor import extractAppData
from analysis.src.utils import reconstruct_url

RUST_DIR = Path(__file__).parent / "highperformanceanalysis"
RUST_BIN = RUST_DIR / "target" / "release" / "highperformanceanalysis"


def build_rust() -> None:
    print("Building Rust binary")
    result = subprocess.run(
        ["cargo", "build", "--release"],
        cwd=RUST_DIR,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(result.stderr)
        sys.exit(1)
    print("Build OK\n")


def run_python(html_path: Path, url: str) -> dict:
    with open(html_path, encoding="utf-8") as f:
        soup = BeautifulSoup(f.read(), "html.parser")
    return extractAppData(url, soup) or {}


def run_rust(html_path: Path, url: str) -> dict:
    result = subprocess.run(
        [str(RUST_BIN), str(html_path), url],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print("Rust stderr:", result.stderr)
        return {}
    if not result.stdout.strip():
        return {}
    return json.loads(result.stdout)


def normalize(value: Any) -> Any:
    """Convert int/float to str so numeric JSON-LD fields compare cleanly."""
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, (int, float)):
        # JSON numbers: strip trailing zeros to match Python's repr
        s = str(value)
        return s
    if isinstance(value, list):
        return [normalize(v) for v in value]
    if isinstance(value, dict):
        return {k: normalize(v) for k, v in value.items()}
    return value


def compare(py: dict, rs: dict) -> bool:
    all_keys = sorted(set(py) | set(rs))
    differences: list[tuple[str, Any, Any]] = []

    for key in all_keys:
        py_val = normalize(py.get(key))
        rs_val = normalize(rs.get(key))
        if py_val != rs_val:
            differences.append((key, py_val, rs_val))

    if not differences:
        print(f"All {len(all_keys)} fields match")
        return True

    print(f"{len(differences)} field(s) differ (out of {len(all_keys)}):\n")
    for key, py_val, rs_val in differences:
        print(f"  [{key}]")
        print(f"    Python : {py_val!r}")
        print(f"    Rust   : {rs_val!r}")
        print()
    return False


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    html_path = Path(sys.argv[1])
    url = reconstruct_url(str(html_path))

    if not html_path.exists():
        print(f"File not found: {html_path}")
        sys.exit(1)
        
    if not url:
        print(f"Failed to reconstruct url")
        sys.exit(1)

    build_rust()

    print(f"File : {html_path.name}")
    print(f"URL  : {url}\n")

    t0 = time.perf_counter()
    py_data = run_python(html_path, url)
    py_ms = (time.perf_counter() - t0) * 1000

    t0 = time.perf_counter()
    rs_data = run_rust(html_path, url)
    rs_ms = (time.perf_counter() - t0) * 1000

    print(f"Python : {py_ms:.1f} ms")
    print(f"Rust   : {rs_ms:.1f} ms")
    print(f"Speedup: {py_ms / rs_ms:.1f}x\n")

    if not py_data and not rs_data:
        print("Both parsers returned no data.")
        return

    if not py_data:
        print("Python returned no data")
        return

    if not rs_data:
        print("Rust returned no data")
        return

    ok = compare(py_data, rs_data)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
