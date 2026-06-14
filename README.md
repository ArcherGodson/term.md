# term.md

`term-md` renders Markdown files and streams into terminal-friendly text with ANSI styling.

## Usage

```sh
python3 term_md.py README.md
cat README.md | python3 term_md.py
python3 term_md.py --color --width 100 README.md
python3 term_md.py --no-color README.md
python3 term_md.py --code-copy README.md
```

When paths are omitted, input is read from stdin. Use `-` to mix stdin with file paths.

Supported Markdown features include headings, horizontal rules, blockquotes, ordered and unordered lists, task markers, fenced code blocks, inline code, emphasis, strong text, strikethrough, links, images as alt text plus URL, and simple pipe tables.

Fenced code blocks render as a dark-gray ANSI color block with a two-character outer margin, two-character inner padding, and a two-character right padding after the longest code line. Use `--code-copy` to keep the same dark-gray block styling while removing leading indentation from code lines, which makes terminal selection and clipboard copying cleaner. Pipe tables are column-aligned and use one horizontal space inside each cell.

<img width="2560" height="1800" alt="term md" src="https://github.com/user-attachments/assets/24c23fbe-595f-4e94-93df-15621b47e953" />
