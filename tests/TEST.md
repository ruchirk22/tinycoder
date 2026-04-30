# tinycoder — Test Sessions

Real prompts I ran against tinycoder locally. Every file below was generated or executed entirely by the agent — no manual editing.

---

## Test 1 · Hello World

**Prompt:**

```bash
create hello.py with a hello world function
```

**Agent trace:**

```text
⚙  edit_file {"path": "hello.py", "old_str": "", "new_str": "..."}
```

**Generated `hello.py`:**

```python
def hello():
    print("Hello, world!")

hello()
```

**Result:** ✅ File created. `python hello.py` prints `Hello, world!`

---

## Test 2 · Run a file (with permission prompt)

**Prompt:**

```bash
run hello.py
```

**Agent trace:**

```text
⚙  run_file {"filename": "hello.py"}

  ⚠  tinycoder wants to run: /path/to/hello.py
  Allow? [y/N] › y
  ▶  Running hello.py...
Hello, world!
  ✓  Exited with code 0
```

**Result:** ✅ Agent asked permission before executing. Output printed live in terminal. Exit code fed back to the LLM.

---

## Test 3 · Create, then run in one turn

**Prompt:**

```bash
create a file called fizzbuzz.py that prints fizzbuzz from 1 to 20, then run it
```

**Agent trace:**

```text
⚙  edit_file {"path": "fizzbuzz.py", "old_str": "", "new_str": "..."}
⚙  run_file  {"filename": "fizzbuzz.py"}

  ⚠  tinycoder wants to run: /path/to/fizzbuzz.py
  Allow? [y/N] › y
  ▶  Running fizzbuzz.py...
1 2 Fizz 4 Buzz Fizz 7 8 Fizz Buzz 11 Fizz 13 14 FizzBuzz 16 17 Fizz 19 Buzz
  ✓  Exited with code 0
```

**Generated `fizzbuzz.py`:**

```python
for i in range(1, 21):
    if i % 15 == 0:
        print("FizzBuzz", end=" ")
    elif i % 3 == 0:
        print("Fizz", end=" ")
    elif i % 5 == 0:
        print("Buzz", end=" ")
    else:
        print(i, end=" ")
print()
```

**Result:** ✅ Agent chained two tool calls in one turn — created the file, then ran it immediately after.

---

## Test 4 · Run, detect error, fix it

**Prompt:**

```bash
create broken.py with a function that divides by zero, then run it
```

**Agent trace:**

```text
⚙  edit_file {"path": "broken.py", "old_str": "", "new_str": "..."}
⚙  run_file  {"filename": "broken.py"}

  ⚠  tinycoder wants to run: /path/to/broken.py
  Allow? [y/N] › y
  ▶  Running broken.py...
ZeroDivisionError: division by zero
  ✓  Exited with code 1
```

**Follow-up prompt:**

```bash
fix the error and run it again
```

**Agent trace:**

```text
⚙  read_file {"filename": "broken.py"}
⚙  edit_file {"path": "broken.py", "old_str": "return a / b", "new_str": "return a / b if b != 0 else 'undefined'"}
⚙  run_file  {"filename": "broken.py"}

  ⚠  tinycoder wants to run: /path/to/broken.py
  Allow? [y/N] › y
  ▶  Running broken.py...
Result: undefined
  ✓  Exited with code 0
```

**Result:** ✅ Agent read the stderr output from the first run, diagnosed the issue, patched the file, and re-ran it — all without being told what the fix was.

---

## Test 5 · Build a utility module and run its demo

**Prompt:**

```bash
create utils/string_utils.py with reverse_string, count_vowels, and is_palindrome. add a demo block at the bottom and run it
```

**Agent trace:**

```text
⚙  edit_file {"path": "utils/string_utils.py", "old_str": "", "new_str": "..."}
⚙  run_file  {"filename": "utils/string_utils.py"}

  ⚠  tinycoder wants to run: /path/to/utils/string_utils.py
  Allow? [y/N] › y
  ▶  Running string_utils.py...
redocynit
3
True
False
  ✓  Exited with code 0
```

**Generated `utils/string_utils.py`:**

```python
def reverse_string(s: str) -> str:
    return s[::-1]

def count_vowels(s: str) -> int:
    return sum(1 for c in s.lower() if c in "aeiou")

def is_palindrome(s: str) -> bool:
    cleaned = s.lower().replace(" ", "")
    return cleaned == cleaned[::-1]

if __name__ == "__main__":
    print(reverse_string("tinycoder"))
    print(count_vowels("hello world"))
    print(is_palindrome("racecar"))
    print(is_palindrome("hello"))
```

**Result:** ✅ Nested directory created automatically. Demo ran and all four outputs were correct.

---

## Test 6 · User denies execution

**Prompt:**

```bash
run hello.py
```

**Agent trace:**

```text
⚙  run_file {"filename": "hello.py"}

  ⚠  tinycoder wants to run: /path/to/hello.py
  Allow? [y/N] › n
  ✗  Execution denied by user.
```

**tinycoder response:**

```text
Understood — hello.py was not executed. Let me know if you'd like to run it later or make changes first.
```

**Result:** ✅ Pressing `n` (or just Enter) blocks execution entirely. The denial is fed back to the LLM which acknowledges it gracefully.

---

## What these tests show

| Capability | Tested |
|---|---|
| Create a file from scratch | ✅ Test 1, 3, 5 |
| Run a file with permission prompt | ✅ Test 2, 3, 4, 5 |
| Chain create → run in one turn | ✅ Test 3, 5 |
| Read stderr, diagnose, fix, re-run | ✅ Test 4 |
| Nested directory creation | ✅ Test 5 |
| User denies execution gracefully | ✅ Test 6 |

Four tools. One loop. That's the whole agent.
