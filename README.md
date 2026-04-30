# tinycoder

**A small-scale replica of Claude Code.**

Claude Code — and every coding agent like it — is not magic. Underneath, it's a loop: an LLM that emits structured tool calls, and a thin harness that executes them locally and feeds results back. tinycoder is that loop, stripped to its core in ~180 lines of Python, powered by [Groq](https://groq.com).

---

## How Claude Code actually works

```text
user message
    → LLM decides which tool to call
    → harness executes tool on your machine
    → result appended to conversation
    → LLM continues or calls another tool
    → repeat until done
```

The LLM never touches your filesystem or runs your code directly. It issues *requests* — structured tool calls — and your process executes them. The "intelligence" is the model knowing *when* to read before editing, *how* to chain calls, and *when* to stop.

tinycoder implements this faithfully. Four tools, one loop, zero magic.

---

## Tools

| Tool | Signature | What it does |
|---|---|---|
| `read_file` | `(filename)` | Read a file's full contents |
| `list_files` | `(path)` | List files in a directory |
| `edit_file` | `(path, old_str, new_str)` | Create file (empty `old_str`) or patch it |
| `run_file` | `(filename)` | Ask permission, execute a Python file, return output |

The LLM receives these as plain-text descriptions in its system prompt. It calls them by emitting a line like:

```text
tool: edit_file({"path": "hello.py", "old_str": "", "new_str": "print('hello')"})
```

The harness parses this, runs the function, and appends the result as `tool_result(...)` back into the conversation. That's the entire protocol.

### The permission prompt

`run_file` never executes silently. Every time the LLM wants to run a file, you see:

```text
  ⚠  tinycoder wants to run: /your/path/hello.py
  Allow? [y/N] ›
```

Type `y` to allow, anything else to deny. The result — stdout, stderr, and exit code — is fed back to the LLM so it can reason about errors and fix them if needed.

---

## Quickstart

```bash
git clone https://github.com/YOUR_USERNAME/tinycoder.git
cd tinycoder
pip install -r requirements.txt
echo "GROQ_API_KEY=your_key_here" > .env
python agent.py
```

Get a free Groq key at [console.groq.com](https://console.groq.com).

---

## Example

```text
tinycoder ⚡

you › create fizzbuzz.py that prints fizzbuzz 1 to 20, then run it
  ⚙  edit_file  {"path": "fizzbuzz.py", "old_str": "", "new_str": "..."}
  ⚙  run_file   {"filename": "fizzbuzz.py"}

  ⚠  tinycoder wants to run: /path/to/fizzbuzz.py
  Allow? [y/N] › y
  ▶  Running fizzbuzz.py...
1 2 Fizz 4 Buzz Fizz 7 8 Fizz Buzz 11 Fizz 13 14 FizzBuzz 16 17 Fizz 19 Buzz
  ✓  Exited with code 0

tinycoder › Done! fizzbuzz.py is working correctly.
```

The agent can also detect errors from the output and fix them without being told what went wrong — see [`test.md`](./test.md) for annotated sessions.

---

## Model

Default: `llama-3.3-70b-versatile` via Groq. Change it at the top of `agent.py`:

```python
MODEL = "llama-3.3-70b-versatile"   # default
# MODEL = "mixtral-8x7b-32768"      # longer context window
# MODEL = "gemma2-9b-it"            # lighter
```

---

## Structure

```bash
tinycoder/
├── agent.py          # the entire agent (~180 lines)
├── requirements.txt
├── test.md           # real test sessions with generated output
├── .env              # your API key (gitignored)
└── README.md
```

---

## What's missing vs. Claude Code

This is intentionally minimal. Production agents add:

- `run_command` — arbitrary shell commands, not just Python files
- `search_files` — grep across a codebase
- Streaming output
- Context summarization for large files
- Smarter approval workflows (diff preview before edits, etc.)

The core loop is identical.

---

## License

MIT
