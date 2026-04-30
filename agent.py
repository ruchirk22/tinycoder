"""
tinycoder - a small-scale replica of Claude Code, powered by Groq
"""

import inspect
import json
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Tuple

from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.environ["GROQ_API_KEY"])
MODEL = "llama-3.3-70b-versatile"  # fast + smart; swap to mixtral-8x7b-32768 if preferred

# ── terminal colors ──────────────────────────────────────────────────────────
YOU_COLOR       = "\033[94m"   # blue
ASSISTANT_COLOR = "\033[93m"   # yellow
TOOL_COLOR      = "\033[92m"   # green
WARN_COLOR      = "\033[91m"   # red
RESET           = "\033[0m"

# ── path helper ──────────────────────────────────────────────────────────────
def resolve(path_str: str) -> Path:
    path = Path(path_str).expanduser()
    if not path.is_absolute():
        path = (Path.cwd() / path).resolve()
    return path


# ── tools ────────────────────────────────────────────────────────────────────
def read_file(filename: str) -> Dict[str, Any]:
    """
    Read and return the full contents of a file.
    :param filename: Path to the file to read.
    :return: Dict with 'file_path' and 'content'.
    """
    p = resolve(filename)
    return {"file_path": str(p), "content": p.read_text(encoding="utf-8")}


def list_files(path: str = ".") -> Dict[str, Any]:
    """
    List all files and subdirectories inside a directory.
    :param path: Directory path to list. Defaults to current directory.
    :return: Dict with 'path' and 'files' (list of {filename, type}).
    """
    p = resolve(path)
    files = [
        {"filename": item.name, "type": "file" if item.is_file() else "dir"}
        for item in sorted(p.iterdir())
    ]
    return {"path": str(p), "files": files}


def edit_file(path: str, old_str: str, new_str: str) -> Dict[str, Any]:
    """
    Create or edit a file. If old_str is empty, creates/overwrites the file
    with new_str. Otherwise replaces the first occurrence of old_str with new_str.
    :param path: Path to the file.
    :param old_str: Text to replace (empty = create/overwrite).
    :param new_str: Replacement text (or full content when creating).
    :return: Dict with 'path' and 'action' taken.
    """
    p = resolve(path)
    p.parent.mkdir(parents=True, exist_ok=True)

    if old_str == "":
        p.write_text(new_str, encoding="utf-8")
        return {"path": str(p), "action": "created"}

    original = p.read_text(encoding="utf-8")
    if old_str not in original:
        return {"path": str(p), "action": "old_str_not_found"}

    p.write_text(original.replace(old_str, new_str, 1), encoding="utf-8")
    return {"path": str(p), "action": "edited"}


def run_file(filename: str) -> Dict[str, Any]:
    """
    Ask the user for permission, then execute a Python file and return its output.
    Always asks for confirmation before running — never executes silently.
    :param filename: Path to the Python file to run.
    :return: Dict with 'stdout', 'stderr', 'exit_code', and 'action'.
    """
    p = resolve(filename)

    if not p.exists():
        return {"action": "denied", "reason": f"{filename} does not exist"}

    # ── ask for permission ───────────────────────────────────────────────────
    print(f"\n{WARN_COLOR}  ⚠  tinycoder wants to run: {p}{RESET}")
    try:
        answer = input(f"{WARN_COLOR}  Allow? [y/N] ›{RESET} ").strip().lower()
    except (KeyboardInterrupt, EOFError):
        answer = "n"

    if answer != "y":
        print(f"{WARN_COLOR}  ✗  Execution denied by user.{RESET}\n")
        return {"action": "denied", "reason": "user declined"}

    # ── run it ───────────────────────────────────────────────────────────────
    print(f"{TOOL_COLOR}  ▶  Running {p.name}...{RESET}")
    result = subprocess.run(
        ["python", str(p)],
        capture_output=True,
        text=True,
        timeout=30,
    )

    # print live output so the user sees it immediately
    if result.stdout:
        print(f"{result.stdout}", end="")
    if result.stderr:
        print(f"{WARN_COLOR}{result.stderr}{RESET}", end="")

    print(f"{TOOL_COLOR}  ✓  Exited with code {result.returncode}{RESET}\n")

    return {
        "action": "executed",
        "stdout": result.stdout,
        "stderr": result.stderr,
        "exit_code": result.returncode,
    }


TOOL_REGISTRY = {
    "read_file":  read_file,
    "list_files": list_files,
    "edit_file":  edit_file,
    "run_file":   run_file,
}


# ── system prompt ─────────────────────────────────────────────────────────────
def _tool_description(name: str) -> str:
    fn = TOOL_REGISTRY[name]
    return (
        f"Name: {name}\n"
        f"Description: {fn.__doc__}\n"
        f"Signature: {inspect.signature(fn)}"
    )


SYSTEM_PROMPT_TEMPLATE = """\
You are tinycoder, a fast coding assistant. Help users create, modify, and run code.

You have access to these tools:

{tools}

RULES:
- When you need a tool, output EXACTLY one line: tool: TOOL_NAME({{"arg": "value"}})
- Use compact single-line JSON with double quotes inside the parentheses.
- After you receive a tool_result(...) message, continue the task.
- Chain multiple tool calls if needed (e.g. read first, then edit, then run).
- For run_file: the harness will ask the user for permission before executing. If denied, let the user know.
- When no tool is needed, respond normally in plain text.
"""


def build_system_prompt() -> str:
    tool_block = "\n---\n".join(
        _tool_description(name) for name in TOOL_REGISTRY
    )
    return SYSTEM_PROMPT_TEMPLATE.format(tools=tool_block)


# ── tool call parser ──────────────────────────────────────────────────────────
def parse_tool_calls(text: str) -> List[Tuple[str, Dict]]:
    calls = []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("tool:"):
            continue
        try:
            after = line[len("tool:"):].strip()
            name, rest = after.split("(", 1)
            name = name.strip()
            if not rest.endswith(")"):
                continue
            args = json.loads(rest[:-1].strip())
            calls.append((name, args))
        except Exception:
            continue
    return calls


# ── LLM call ──────────────────────────────────────────────────────────────────
def call_llm(messages: List[Dict]) -> str:
    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        max_tokens=2048,
        temperature=0.2,
    )
    return response.choices[0].message.content


# ── dispatch ──────────────────────────────────────────────────────────────────
def dispatch(name: str, args: Dict) -> Any:
    fn = TOOL_REGISTRY.get(name)
    if fn is None:
        return {"error": f"Unknown tool: {name}"}
    sig = inspect.signature(fn)
    kwargs = {k: args[k] for k in sig.parameters if k in args}
    return fn(**kwargs)


# ── main loop ─────────────────────────────────────────────────────────────────
def main():
    print(f"{TOOL_COLOR}tinycoder ⚡  (model: {MODEL}){RESET}")
    print("Type your request. Ctrl+C or Ctrl+D to exit.\n")

    system_prompt = build_system_prompt()
    messages = [{"role": "system", "content": system_prompt}]

    while True:
        try:
            user_input = input(f"{YOU_COLOR}you ›{RESET} ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nbye!")
            break

        if not user_input:
            continue

        messages.append({"role": "user", "content": user_input})

        # inner loop: keep calling LLM until it stops requesting tools
        while True:
            reply = call_llm(messages)
            tool_calls = parse_tool_calls(reply)

            if not tool_calls:
                print(f"\n{ASSISTANT_COLOR}tinycoder ›{RESET} {reply}\n")
                messages.append({"role": "assistant", "content": reply})
                break

            # execute each tool call and feed results back
            messages.append({"role": "assistant", "content": reply})
            for name, args in tool_calls:
                print(f"{TOOL_COLOR}  ⚙  {name}{RESET} {args}")
                result = dispatch(name, args)
                messages.append({
                    "role": "user",
                    "content": f"tool_result({json.dumps(result)})",
                })


if __name__ == "__main__":
    main()