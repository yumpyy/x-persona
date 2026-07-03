from __future__ import annotations

from textual.widgets import Static, Input


_FOOTER = (
    "[#6c7086]s:[/]start  "
    "[#6c7086]k:[/]kill  "
    "[#6c7086]i:[/]act  "
    "[#6c7086]o:[/]compose  "
    "[#6c7086]c:[/]config  "
    "[#6c7086]h:[/]hist  "
    "[#6c7086]e:[/]flags  "
    "[#6c7086]f:[/]settings  "
    "[#6c7086]?:[/]help  "
    "[#6c7086]q:[/]quit"
)

_COMPOSE = (
    "[#89b4fa bold]COMPOSE[/]  "
    "[#a6e3a1]g:[/]generate  "
    "[#f9e2af]c:[/]custom  "
    "[#6c7086]esc:[/]cancel"
)

_ASK_DECIDE = (
    "[#f9e2af bold]APPROVAL[/]  "
    "[#a6e3a1]y:[/]allow  "
    "[#f38ba8]n:[/]deny  "
    "[#6c7086]esc:[/]cancel"
)


class HelpBar(Static):
    """Single-line footer — toggles between normal, compose, prompt, and ask mode."""

    def __init__(self) -> None:
        super().__init__(_FOOTER, id="footer")
        self._compose_mode = False
        self._ask_mode = False
        self._prompt_input: Input | None = None

    def set_compose_mode(self, on: bool) -> None:
        self._compose_mode = on
        if on:
            self.update(_COMPOSE)
        elif self._ask_mode:
            self.update(_ASK_DECIDE)
        else:
            self.update(_FOOTER)

    def show_ask(self) -> None:
        self._ask_mode = True
        self.update(_ASK_DECIDE)

    def hide_ask(self) -> None:
        self._ask_mode = False
        if self._compose_mode:
            self.update(_COMPOSE)
        else:
            self.update(_FOOTER)

    def show_prompt(self, placeholder: str = "What should I post about?") -> Input:
        self.styles.height = "auto"
        self._prompt_input = Input(placeholder=placeholder, id="compose-prompt-input")
        self.mount(self._prompt_input)
        self.update("")
        self._prompt_input.focus()
        return self._prompt_input

    def hide_prompt(self) -> None:
        if self._prompt_input is not None:
            self._prompt_input.remove()
            self._prompt_input = None
        self.styles.height = 1
        if self._ask_mode:
            self.update(_ASK_DECIDE)
        elif self._compose_mode:
            self.update(_COMPOSE)
        else:
            self.update(_FOOTER)

    def get_prompt_value(self) -> str:
        if self._prompt_input is not None:
            return self._prompt_input.value.strip()
        return ""
