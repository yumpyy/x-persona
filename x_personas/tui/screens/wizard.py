from __future__ import annotations

from pathlib import Path

from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Static, Label
from textual.containers import Vertical, Horizontal


class PersonaWizard(ModalScreen):
    """Multi-step wizard to create a new persona."""

    def compose(self) -> ComposeResult:
        yield Vertical(
            Static("[bold]New Persona Wizard[/]", classes="wizard-title"),
            Label("Persona name (directory):"),
            Input(placeholder="e.g. my-new-persona", id="wizard-name"),
            Label("Source data file path (optional):"),
            Input(placeholder="e.g. /path/to/raw-data.txt", id="wizard-source"),
            Horizontal(
                Button("Generate Persona", variant="primary", id="wizard-generate"),
                Button("Cancel", variant="default", id="wizard-cancel"),
                classes="wizard-buttons",
            ),
            Static(id="wizard-status", classes="wizard-status"),
            id="wizard-dialog",
        )

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "wizard-cancel":
            self.app.pop_screen()
        elif event.button.id == "wizard-generate":
            await self._generate()

    async def _generate(self) -> None:
        name = self.query_one("#wizard-name", Input).value.strip()
        if not name:
            self.query_one("#wizard-status", Static).update("[#f38ba8]Name is required.[/]")
            return

        target = Path("personas") / name
        if target.exists():
            self.query_one("#wizard-status", Static).update(f"[#f38ba8]Persona '{name}' already exists.[/]")
            return

        source_path = self.query_one("#wizard-source", Input).value.strip()
        self.query_one("#wizard-status", Static).update("[#f9e2af]Creating persona...[/]")

        try:
            target.mkdir(parents=True)
            (target / "source").mkdir()
            activity_log = target / "activity-log.md"
            activity_log.touch()

            # Copy template if available
            tmpl = Path("personas/_template/persona.md")
            if tmpl.exists():
                (target / "persona.md").write_text(tmpl.read_text())

            # Generate persona from source data if provided
            if source_path and Path(source_path).exists():
                from x_personas.generate_persona import generate_from_file
                # simplified: just log the intent
                self.query_one("#wizard-status", Static).update(
                    f"[#a6e3a1]Persona '{name}' created at {target}/. Source data needs LLM generation via generate-persona CLI.[/]"
                )
            else:
                self.query_one("#wizard-status", Static).update(
                    f"[#a6e3a1]Persona '{name}' created at {target}/. Edit persona.md and source/ manually.[/]"
                )

            # Add to store
            from x_personas.tui.store import PersonaRuntimeInfo
            info = PersonaRuntimeInfo(
                name=name,
                persona_path=target / "persona.md",
                activity_log_file=str(activity_log),
                rate_limit_file=str(target / "rate-limits.json"),
            )
            self.app.store.add_persona(info)
            self.app.pop_screen()
        except Exception as e:
            self.query_one("#wizard-status", Static).update(f"[#f38ba8]Error: {e}[/]")
