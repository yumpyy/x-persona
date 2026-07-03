from __future__ import annotations

import argparse
import sys

from x_personas.tui.app import XPersonasTUI


def main() -> None:
    parser = argparse.ArgumentParser(description="X-Personas Textual TUI")
    parser.add_argument("--persona", action="append", default=None,
                        help="Persona name(s) to load (default: auto-discover personas/)")
    parser.add_argument("--visible", action="store_true", default=False,
                        help="Show browser window (default: headless)")
    args = parser.parse_args()

    app = XPersonasTUI(
        filter_personas=args.persona,
        headless=not args.visible,
    )
    app.run()


if __name__ == "__main__":
    main()
