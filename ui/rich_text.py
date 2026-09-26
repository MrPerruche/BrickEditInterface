"""Global look of inline rich text elements.

Qt stylesheets do not reach inside rich text (a QLabel's <code> ignores QSS), so instead of a QSS rule every
label and tooltip rewrites <code>...</code> into a <span> carrying the style below. Edit CODE_STYLE to
change how <code> looks everywhere in the app (labels, tutorials, tooltips).
"""

import html
import re


# CSS declarations applied to every <code>. Any property Qt's rich text supports works
# (font-family, font-size, font-weight, font-style, color, background-color...).
CODE_STYLE: dict[str, str] = {
    "font-family": "'Inconsolata SemiCondensed Medium', Consolas, 'Cascadia Mono', 'Courier New', monospace",
    "font-size": "13pt",
    # "font-weight": "500",
    # "color": "#e0a050",
    # "background-color": "#20808080",
}


_CODE_RE = re.compile(r"<code>(.*?)</code>", re.IGNORECASE | re.DOTALL)


def _code_style_attr() -> str:
    return "; ".join(f"{key}: {value}" for key, value in CODE_STYLE.items())


def style_rich_text(text: str) -> str:
    """Replaces every <code>...</code> of text by a span using CODE_STYLE. Cheap when there is none."""
    if "<code" not in text.lower():
        return text
    return _CODE_RE.sub(lambda m: f'<span style="{_code_style_attr()}">{m.group(1)}</span>', text)


# ----------------------------------------------------------------------
# Pseudo markdown
# ----------------------------------------------------------------------

_PMD_TAGS = {"**": "b", "*": "i"}


def pmd(text: str) -> str:
    r"""Pseudo markdown to rich text: *italic*, **bold**, `code` (contents are literal) and \ to escape a
    character. New lines become line breaks and &, <, > are escaped (so raw HTML is not supported here).
    A marker with no closing counterpart is shown as is."""
    out: list[str] = []
    stack: list[str] = []  # Open tags, innermost last
    i, n = 0, len(text)

    def close(tag: str):
        # Closes tag, and closes then reopens whatever was opened inside it so the HTML stays nested
        inner = []
        while stack:
            top = stack.pop()
            out.append(f"</{top}>")
            if top == tag:
                break
            inner.append(top)
        for top in reversed(inner):
            out.append(f"<{top}>")
            stack.append(top)

    while i < n:
        c = text[i]

        if c == "\\" and i + 1 < n:  # Escape
            out.append(html.escape(text[i + 1], quote=False))
            i += 2
        elif c == "`" and (end := text.find("`", i + 1)) != -1:  # Code: literal contents
            out.append(f"<code>{html.escape(text[i + 1:end], quote=False).replace(chr(10), '<br>')}</code>")
            i = end + 1
        elif c == "*":
            marker = "**" if text.startswith("**", i) else "*"
            tag = _PMD_TAGS[marker]
            if tag in stack:
                close(tag)
            elif text.find(marker, i + len(marker)) != -1:
                out.append(f"<{tag}>")
                stack.append(tag)
            else:
                out.append(marker)  # Nothing to close it: literal
            i += len(marker)
        elif c == "\n":
            out.append("<br>")
            i += 1
        else:
            out.append(html.escape(c, quote=False))
            i += 1

    for tag in reversed(stack):
        out.append(f"</{tag}>")
    return f"<html>{''.join(out)}</html>"
