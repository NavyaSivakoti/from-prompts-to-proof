"""One place to change model settings. Paths work from any working directory."""

from pathlib import Path

from dotenv import load_dotenv

DEMO_DIR = Path(__file__).resolve().parent
ROOT_DIR = DEMO_DIR.parent
load_dotenv(ROOT_DIR / ".env")  # An existing shell variable takes precedence.

# The chatbot answers with OpenAI. Promptfoo's grader is set in promptfooconfig.yaml.
MODEL = "gpt-4o-mini"
TEMPERATURE = 0.7
MAX_COMPLETION_TOKENS = 600
REQUEST_TIMEOUT_SECONDS = 30
MAX_HISTORY_MESSAGES = 6
PROMPT_VERSIONS = ("baseline", "improved")
REHEARSAL_DIR = DEMO_DIR / "rehearsal"


def load_prompt(version: str) -> str:
    if version not in PROMPT_VERSIONS:
        raise ValueError("Choose baseline or improved.")
    return (DEMO_DIR / "prompts" / f"{version}.txt").read_text(encoding="utf-8")
