from dataclasses import dataclass

from ui.rich_text import style_rich_text


@dataclass
class TooltipContents:
    text: str
    description: str | None = None

    def richtext(self):
        text_br = self.text.replace('\n', '<br>')
        if self.description is None or self.description == "":
            return style_rich_text(f"<html>{text_br}</html>")

        description_br = self.description.replace('\n', '<br>')
        return style_rich_text(f"<b>{text_br}</b><br>{description_br}")
