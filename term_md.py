#!/usr/bin/env python3
"""Render Markdown as ANSI-styled terminal text."""

from __future__ import annotations

import argparse
import re
import shutil
import sys
import textwrap
from dataclasses import dataclass
from typing import Iterable, TextIO


RESET = "\033[0m"


@dataclass(frozen=True)
class Theme:
    heading: str = "\033[1;36m"
    heading_marker: str = "\033[36m"
    bold: str = "\033[1m"
    italic: str = "\033[3m"
    code: str = "\033[38;5;214m"
    code_block: str = "\033[38;5;250m"
    code_block_bg: str = "\033[48;5;236m"
    quote: str = "\033[90m"
    bullet: str = "\033[36m"
    rule: str = "\033[90m"
    link: str = "\033[4;34m"
    table_border: str = "\033[90m"


class Ansi:
    def __init__(self, enabled: bool, theme: Theme | None = None) -> None:
        self.enabled = enabled
        self.theme = theme or Theme()

    def wrap(self, text: str, code: str) -> str:
        if not self.enabled or not text:
            return text
        return f"{code}{text}{RESET}"


class MarkdownRenderer:
    def __init__(self, *, color: bool = True, width: int | None = None) -> None:
        self.ansi = Ansi(color)
        self.width = width or shutil.get_terminal_size((88, 24)).columns

    def render(self, markdown: str) -> str:
        lines = markdown.splitlines()
        output: list[str] = []
        in_code = False
        code_lines: list[str] = []
        index = 0

        while index < len(lines):
            line = lines[index].rstrip("\n")

            fence = re.match(r"^\s*(```+|~~~+)\s*([\w.+-]*)\s*$", line)
            if fence:
                if in_code:
                    in_code = False
                    output.extend(self._render_code_block(code_lines))
                    code_lines = []
                else:
                    in_code = True
                index += 1
                continue

            if in_code:
                code_lines.append(line)
                index += 1
                continue

            if self._looks_like_table(line):
                table_lines = [line]
                index += 1
                while index < len(lines) and self._looks_like_table(lines[index].rstrip("\n")):
                    table_lines.append(lines[index].rstrip("\n"))
                    index += 1
                output.extend(self._render_table(table_lines))
                continue

            rendered = self._render_block_line(line)
            output.extend(rendered)
            index += 1

        if in_code:
            output.extend(self._render_code_block(code_lines))

        return "\n".join(output)

    def _render_block_line(self, line: str) -> list[str]:
        if not line.strip():
            return [""]

        heading = re.match(r"^(#{1,6})\s+(.+?)\s*#*\s*$", line)
        if heading:
            level = len(heading.group(1))
            marker = self.ansi.wrap("#" * level, self.ansi.theme.heading_marker)
            text = self.ansi.wrap(self._render_inline(heading.group(2)), self.ansi.theme.heading)
            return [f"{marker} {text}", self.ansi.wrap("-" * min(self.width, 72), self.ansi.theme.rule) if level == 1 else ""]

        if re.match(r"^\s{0,3}([-*_])(?:\s*\1){2,}\s*$", line):
            return [self.ansi.wrap("-" * min(self.width, 72), self.ansi.theme.rule)]

        quote = re.match(r"^\s{0,3}>\s?(.*)$", line)
        if quote:
            return [self.ansi.wrap("│ ", self.ansi.theme.quote) + self.ansi.wrap(self._render_inline(quote.group(1)), self.ansi.theme.quote)]

        task = re.match(r"^(\s*)[-+*]\s+\[([ xX])\]\s+(.+)$", line)
        if task:
            indent = " " * (len(task.group(1)) // 2 * 2)
            box = "[x]" if task.group(2).lower() == "x" else "[ ]"
            prefix = indent + self.ansi.wrap(box, self.ansi.theme.bullet) + " "
            return self._wrapped(prefix, self._render_inline(task.group(3)))

        list_item = re.match(r"^(\s*)([-+*]|\d+[.)])\s+(.+)$", line)
        if list_item:
            indent = " " * (len(list_item.group(1)) // 2 * 2)
            marker = list_item.group(2)
            bullet = "•" if marker in "-+*" else marker
            prefix = indent + self.ansi.wrap(bullet, self.ansi.theme.bullet) + " "
            return self._wrapped(prefix, self._render_inline(list_item.group(3)))

        return self._wrapped("", self._render_inline(line))

    def _render_inline(self, text: str) -> str:
        placeholders: list[str] = []

        def keep(match: re.Match[str], code: str, group: int = 1) -> str:
            placeholders.append(self.ansi.wrap(match.group(group), code))
            return f"\u0000{len(placeholders) - 1}\u0000"

        text = re.sub(r"`([^`]+)`", lambda m: keep(m, self.ansi.theme.code), text)
        text = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", lambda m: f"{m.group(1)} ({m.group(2)})", text)
        text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", lambda m: self.ansi.wrap(m.group(1), self.ansi.theme.link) + f" ({m.group(2)})", text)
        text = re.sub(r"(\*\*|__)(.+?)\1", lambda m: keep(m, self.ansi.theme.bold, 2), text)
        text = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", lambda m: keep(m, self.ansi.theme.italic), text)
        text = re.sub(r"(?<!_)_([^_\n]+)_(?!_)", lambda m: keep(m, self.ansi.theme.italic), text)
        text = re.sub(r"~~(.+?)~~", lambda m: keep(m, "\033[9m"), text)

        for index, value in enumerate(placeholders):
            text = text.replace(f"\u0000{index}\u0000", value)

        return text

    def _render_code_block(self, lines: list[str]) -> list[str]:
        if not lines:
            lines = [""]
        if not self.ansi.enabled:
            return [f"    {line}" for line in lines]

        width = max(len(line) for line in lines) + 4
        return [self._render_code_line(line, width) for line in lines]

    def _render_code_line(self, line: str, width: int) -> str:
        margin = "  "
        text = f"  {line}".ljust(width)
        if not self.ansi.enabled:
            return f"    {line}"
        return margin + self.ansi.wrap(text, self.ansi.theme.code_block_bg + self.ansi.theme.code_block)

    def _looks_like_table(self, line: str) -> bool:
        stripped = line.strip()
        return stripped.startswith("|") and stripped.endswith("|") and stripped.count("|") >= 2

    def _render_table(self, lines: list[str]) -> list[str]:
        rows = [self._parse_table_row(line) for line in lines]
        column_count = max(len(row) for row in rows)
        normalized = [row + [""] * (column_count - len(row)) for row in rows]
        widths = [
            max(len(strip_ansi(cell)) for cell in column)
            for column in zip(*normalized)
        ]
        return [self._render_table_row(row, widths) for row in normalized]

    def _parse_table_row(self, line: str) -> list[str]:
        return [cell.strip() for cell in line.strip().strip("|").split("|")]

    def _is_table_separator_row(self, row: list[str]) -> bool:
        return all(re.fullmatch(r":?-{3,}:?", cell) for cell in row)

    def _render_table_row(self, row: list[str], widths: list[int]) -> str:
        if self._is_table_separator_row(row):
            cells = [self.ansi.wrap("─" * (width + 2), self.ansi.theme.table_border) for width in widths]
            return self.ansi.wrap("┼", self.ansi.theme.table_border).join(cells)

        cells = []
        for cell, width in zip(row, widths):
            rendered = self._render_inline(cell)
            padding = width - len(strip_ansi(rendered))
            cells.append(f" {rendered}{' ' * padding} ")
        return self.ansi.wrap("|", self.ansi.theme.table_border).join(cells)

    def _wrapped(self, prefix: str, text: str) -> list[str]:
        available = max(20, self.width - len(strip_ansi(prefix)))
        wrapped = textwrap.wrap(
            text,
            width=available,
            replace_whitespace=False,
            drop_whitespace=True,
            break_long_words=False,
            break_on_hyphens=False,
        )
        if not wrapped:
            return [prefix.rstrip()]
        continuation = " " * len(strip_ansi(prefix))
        return [prefix + wrapped[0], *[continuation + part for part in wrapped[1:]]]


def strip_ansi(text: str) -> str:
    return re.sub(r"\033\[[0-9;]*m", "", text)


def read_inputs(paths: Iterable[str], stdin: TextIO) -> Iterable[tuple[str, str]]:
    used = False
    for path in paths:
        used = True
        if path == "-":
            yield "-", stdin.read()
        else:
            with open(path, "r", encoding="utf-8") as handle:
                yield path, handle.read()
    if not used:
        yield "-", stdin.read()


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="term-md",
        description="Render Markdown files or stdin as ANSI-styled terminal text.",
    )
    parser.add_argument("paths", nargs="*", help="Markdown files to render. Use '-' or omit paths for stdin.")
    parser.add_argument("--width", type=int, help="Wrap output to this terminal width.")
    color = parser.add_mutually_exclusive_group()
    color.add_argument("--color", action="store_true", help="Force ANSI colors even when stdout is not a TTY.")
    color.add_argument("--no-color", action="store_true", help="Disable ANSI colors.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    color = args.color or (not args.no_color and sys.stdout.isatty())
    renderer = MarkdownRenderer(color=color, width=args.width)
    rendered_docs = [renderer.render(content) for _, content in read_inputs(args.paths, sys.stdin)]
    sys.stdout.write("\n\n".join(rendered_docs))
    if rendered_docs:
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
