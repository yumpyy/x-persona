from __future__ import annotations

from textual import events
from textual.widgets import Static


class WidthSplitter(Static):
    """A vertical divider that resizes the widget to its right via dragging."""

    def __init__(self, target_id: str = "", min_width: int = 15, max_width: int = 60):
        super().__init__()
        self._target_id = target_id
        self.target_widget = None
        self.min_width = min_width
        self.max_width = max_width
        self.dragging = False
        self.initial_mouse_x = 0
        self.initial_widget_width = 0

    def on_mount(self) -> None:
        self.can_focus = False
        self.can_focus_children = False
        if self._target_id and self.parent:
            try:
                self.target_widget = self.parent.query_one(f"#{self._target_id}")
            except Exception:
                pass

    def on_mouse_down(self, event: events.MouseDown) -> None:
        if event.button == 1 and self.target_widget is not None:
            self.dragging = True
            self.capture_mouse()
            self.initial_mouse_x = event.screen_x
            self.initial_widget_width = self.target_widget.size.width

    def on_mouse_move(self, event: events.MouseMove) -> None:
        if self.dragging:
            delta_x = self.initial_mouse_x - event.screen_x
            new_width = self.initial_widget_width + delta_x
            if self.min_width <= new_width <= self.max_width:
                self.target_widget.styles.width = new_width

    def on_mouse_up(self, event: events.MouseUp) -> None:
        if self.dragging:
            self.dragging = False
            self.release_mouse()
