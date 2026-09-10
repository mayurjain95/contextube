"""
Agentic test-writer.

Given a router file, this pulls the *live* OpenAPI schema from the running
app (so it always reflects whatever endpoints currently exist, including
ones added after this script was written), asks Claude to generate pytest
tests for it, actually runs them, and if any fail, feeds the real pytest
output back to Claude and asks it to fix the file. Repeats up to
MAX_ITERATIONS times.

This is deliberately a small, readable version of the same
generate -> observe -> reflect loop that larger coding agents use.

Usage:
    export ANTHROPIC_API_KEY=sk-ant-...
    python -m agent.test_writer app/routers/video.py
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

import anthropic
from fastapi.testclient import TestClient

from app.main import app

MODEL = "claude-sonnet-5"
MAX_ITERATIONS = 3
TESTS_DIR = Path(__file__).parent.parent / "tests"

client = anthropic.Anthropic()


def get_openapi_schema() -> dict:
    """Pulled live from the running app object, not hand-maintained —
    any route that exists shows up here automatically."""
    test_client = TestClient(app)
    return test_client.get("/openapi.json").json()


def build_initial_prompt(schema: dict, router_source: str) -> str:
    return f"""You write pytest tests for a FastAPI app using FastAPI's TestClient.

OpenAPI schema for the API:
{json.dumps(schema, indent=2)}

Router source code for context:
{router_source}

Write a complete pytest test file that:
- Imports `from fastapi.testclient import TestClient` and `from app.main import app`
- Mocks any calls to external services (OpenAI embeddings/chat calls, the
  Chroma vector store) using `unittest.mock.patch` — tests must NOT make
  real network calls or require a real API key to run
- Covers the happy path for each endpoint, validation errors (missing or
  malformed fields), and the specific error responses defined in the schema
  (e.g. 404s, 422s)
- Uses clear, descriptive test function names

Return ONLY the Python code for the test file. No explanation, no markdown
fences."""


def build_fix_prompt(previous_code: str, pytest_output: str) -> str:
    return f"""This pytest test file has failing tests.

Test file:
{previous_code}

pytest output:
{pytest_output}

Fix the test file so all tests pass. Return ONLY the corrected Python code,
no explanation, no markdown fences."""


def call_claude(prompt: str) -> str:
    response = client.messages.create(
        model=MODEL,
        max_tokens=4000,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text.strip()


def run_pytest(test_file: Path) -> tuple[bool, str]:
    result = subprocess.run(
        [sys.executable, "-m", "pytest", str(test_file), "-v"],
        capture_output=True,
        text=True,
    )
    passed = result.returncode == 0
    return passed, result.stdout + result.stderr


def generate_tests_for_router(router_path: Path, output_name: str) -> None:
    schema = get_openapi_schema()
    router_source = router_path.read_text()

    prompt = build_initial_prompt(schema, router_source)
    code = call_claude(prompt)

    TESTS_DIR.mkdir(exist_ok=True)
    test_file = TESTS_DIR / f"test_{output_name}.py"

    for attempt in range(1, MAX_ITERATIONS + 1):
        test_file.write_text(code)
        passed, output = run_pytest(test_file)

        print(f"--- Attempt {attempt} ---")
        print(output)

        if passed:
            print(f"All tests passing. Written to {test_file}")
            return

        if attempt < MAX_ITERATIONS:
            code = call_claude(build_fix_prompt(code, output))

    print(
        f"Reached {MAX_ITERATIONS} attempts without a fully passing suite. "
        f"Latest version left at {test_file} — review manually."
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "router_file",
        help="Path to the router file to generate tests for, "
             "e.g. app/routers/video.py",
    )
    args = parser.parse_args()

    router_path = Path(args.router_file)
    if not router_path.exists():
        print(f"No such file: {router_path}")
        sys.exit(1)

    generate_tests_for_router(router_path, router_path.stem)
