from dataclasses import dataclass


@dataclass
class TooltipContents:
    text: str
    description: str | None = None

    def richtext(self):
        text_br = self.text.replace('\n', '<br>')
        if self.description is None or self.description == "":
            return f"<html>{text_br}</html>"

        description_br = self.description.replace('\n', '<br>')
        return f"<b>{text_br}</b><br>{description_br}"
