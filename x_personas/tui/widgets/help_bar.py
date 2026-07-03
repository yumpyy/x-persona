from __future__ import annotations

from textual.widgets import Static, Input


_NORMAL = (
    "[#6c7086]S[/] Start/Stop  "
    "[#6c7086]K[/] Kill  "
    "[#6c7086]I[/] Intervene  "
    "[#6c7086]E[/] Persona  "
    "[#6c7086]F[/] Settings  "
    "[#6c7086]R[/] Refresh  "
    "[#6c7086]Tab[/] Cycle  "
    "[#6c7086]O[/] Compose  "
    "[#6c7086]C[/] Config  "
    "[#6c7086]H[/] History  "
    "[#6c7086]?[/] Help  "
    "[#6c7086]Q[/] Quit"
)

_COMPOSE = (
    "[#89b4fa bold]COMPOSE[/]  "
    "[#a6e3a1]G[/] Generate (LLM)  "
    "[#f9e2af]C[/] Custom (editor)  "
    "[#6c7086]Esc[/] Cancel"
)

_PROMPT_LABEL = "[#89b4fa bold]PROMPT[/]  "

_ASK_DECIDE = (
    "[#f9e2af bold]APPROVAL[/]  "
    "[#a6e3a1]Y[/] Allow  "
    "[#f38ba8]N[/] Deny  "
    "[#6c7086]Esc[/] Cancel"
)


class HelpBar(Static):
    """Single-line footer — toggles between normal, compose, prompt, and ask mode."""

    def __init__(self) -> None:
        super().__init__(_NORMAL, id="footer")
        self._compose_mode = False
        self._ask_mode = False
        self._prompt_input: Input | None = None

    def set_compose_mode(self, on: bool) -> None:
        self._compose_mode = on
        self.update(_COMPOSE if on else _NORMAL)

    def show_ask(self) -> None:
        self._ask_mode = True
        self.update(_ASK_DECIDE)

    def hide_ask(self) -> None:
        self._ask_mode = False
        self.update(_COMPOSE if self._compose_mode else _NORMAL)

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
        self.update(_COMPOSE if self._compose_mode else _NORMAL)

    def get_prompt_value(self) -> str:
        if self._prompt_input is not None:
            return self._prompt_input.value.strip()
        return ""
