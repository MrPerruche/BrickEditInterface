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


# Colors of the tutorial search highlights, taken from the current theme. Edit here to change the look:
#   other matches: the theme's accent border color mixed into the background (OTHER_MATCH_MIX = how much accent)
#   current match: the theme's accent color, with white text
OTHER_MATCH_MIX = 0.45


def _mix(a, b, t: float) -> str:
    """Opaque hex color t of the way from QColor a to QColor b (rich text backgrounds don't support alpha)"""
    return "#{:02x}{:02x}{:02x}".format(
        round(a.red() + (b.red() - a.red()) * t),
        round(a.green() + (b.green() - a.green()) * t),
        round(a.blue() + (b.blue() - a.blue()) * t),
    )


def _highlight_styles() -> tuple[str, str]:
    """(style of the matches, style of the current match) for the current theme"""
    from ui.theme import theme_manager  # Late: this module is imported by widgets the theme module doesn't need
    theme = theme_manager.current()
    other = _mix(theme.background.color_qcolor, theme.accent_border.color_qcolor, OTHER_MATCH_MIX)
    current = theme.accent.color_hex_rgba[:7]
    return (
        f"background-color: {other}; color: {theme.text.color_hex_rgba[:7]}",
        f"background-color: {current}; color: {theme.base.color_hex_rgba[:7]}",
    )

_TAG_SPLIT_RE = re.compile(r"(<[^>]*>)")


def count_matches(text: str, query: str) -> int:
    """How many times query (case insensitive) appears in the visible text (outside of tags) of rich text"""
    if not query:
        return 0
    return highlight_rich_text(text, query, None)[1]


def highlight_rich_text(text: str, query: str, current: int | None) -> tuple[str, int]:
    """Wraps every case insensitive occurrence of query found outside of tags in a highlighted span. The
    occurrence number `current` (0 based, None for none) gets the stronger current match style (see _highlight_styles). Returns (new text, occurrence
    count). Occurrences split by a tag (eg. across bold text) are not found."""
    if not query:
        return text, 0
    pattern = re.compile(re.escape(query), re.IGNORECASE)
    count = 0
    styles: list[str] = []  # Looked up on the first match only: counting does not need them

    def wrap(m: re.Match) -> str:
        nonlocal count
        if not styles:
            styles.extend(_highlight_styles())
        style = styles[1] if count == current else styles[0]
        count += 1
        return f'<span style="{style}">{m.group(0)}</span>'

    parts = _TAG_SPLIT_RE.split(text)
    for i in range(0, len(parts), 2):  # Even indices are text, odd ones are tags
        parts[i] = pattern.sub(wrap, parts[i])
    return "".join(parts), count


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
