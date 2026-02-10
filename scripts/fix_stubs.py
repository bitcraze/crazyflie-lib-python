#!/usr/bin/env python3
"""Post-process pyo3_stub_gen output to convert Coroutine returns to async def.

Transforms:
    def foo(self) -> collections.abc.Coroutine[typing.Any, typing.Any, SomeType]:
into:
    async def foo(self) -> SomeType:

Handles single-line and multi-line return type annotations.
Also types the untyped LogStream.next() dict return.

Usage:
    python scripts/fix_stubs.py cflib/_rust.pyi
"""

import re
import sys

COROUTINE_SINGLE = re.compile(
    r"^(\s*)(.*) -> collections\.abc\.Coroutine\[typing\.Any, typing\.Any, (.+)\]:$"
)

COROUTINE_MULTI_START = re.compile(r"^(\s*)\) -> collections\.abc\.Coroutine\[\s*$")

COROUTINE_MULTI_INNER = re.compile(r"^\s*typing\.Any, typing\.Any, (.+)\s*$")

COROUTINE_MULTI_END = re.compile(r"^\s*\]:$")


def fix_stubs(content: str) -> str:
    lines = content.splitlines(keepends=True)
    out: list[str] = []
    # Track which line indices contain a `def` that needs `async`
    def_line_idx: int | None = None
    i = 0

    while i < len(lines):
        line = lines[i]

        # Track the most recent def line
        stripped = line.lstrip()
        if stripped.startswith("def ") or stripped.startswith("async def "):
            def_line_idx = len(out)

        # Case 1: single-line Coroutine return on same line as def or )
        m = COROUTINE_SINGLE.match(line)
        if m:
            indent, prefix, return_type = m.group(1), m.group(2), m.group(3)
            # Replace the return type
            out.append(f"{indent}{prefix} -> {return_type}:\n")
            # Mark the def as async
            _make_async(out, def_line_idx)
            i += 1
            continue

        # Case 2: multi-line Coroutine return
        #     ) -> collections.abc.Coroutine[
        #         typing.Any, typing.Any, SomeType
        #     ]:
        if COROUTINE_MULTI_START.match(line) and i + 2 < len(lines):
            m_inner = COROUTINE_MULTI_INNER.match(lines[i + 1])
            m_end = COROUTINE_MULTI_END.match(lines[i + 2])
            if m_inner and m_end:
                return_type = m_inner.group(1)
                indent = re.match(r"(\s*)", line).group(1)
                out.append(f"{indent}) -> {return_type}:\n")
                _make_async(out, def_line_idx)
                i += 3
                continue

        out.append(line)
        i += 1

    result = "".join(out)

    # Type the bare dict from LogStream.next()
    result = result.replace("-> dict:", "-> dict[str, int | dict[str, int | float]]:")

    # Remove collections.abc import if no longer used
    if "collections.abc." not in result.split("import collections.abc\n")[-1]:
        result = result.replace("import collections.abc\n", "")

    return result


def _make_async(lines: list[str], def_idx: int | None) -> None:
    """Add 'async ' before 'def' at the given line index."""
    if def_idx is None:
        return
    line = lines[def_idx]
    if "async def " not in line:
        lines[def_idx] = line.replace("def ", "async def ", 1)


def main() -> None:
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <path-to-.pyi>", file=sys.stderr)
        sys.exit(1)

    path = sys.argv[1]
    with open(path) as f:
        original = f.read()

    fixed = fix_stubs(original)

    if fixed == original:
        print(f"{path}: no changes needed")
        return

    with open(path, "w") as f:
        f.write(fixed)

    async_count = fixed.count("async def") - original.count("async def")
    print(f"{path}: converted {async_count} methods to async def")


if __name__ == "__main__":
    main()
