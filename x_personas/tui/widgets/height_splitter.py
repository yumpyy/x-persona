from __future__ import annotations

from textual import events
from textual.widgets import Static


class HeightSplitter(Static):
    """A horizontal divider that resizes the widget above it via dragging."""

    def __init__(self, target_id: str = "", min_height: int = 3, max_height: int = 30):
        super().__init__()
        self._target_id = target_id
        self.target_widget = None
        self.min_height = min_height
        self.max_height = max_height
        self.dragging = False
        self.initial_mouse_y = 0
        self.initial_widget_height = 0

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
            self.initial_mouse_y = event.screen_y
            self.initial_widget_height = self.target_widget.size.height

    def on_mouse_move(self, event: events.MouseMove) -> None:
        if self.dragging:
            delta_y = event.screen_y - self.initial_mouse_y
            new_height = self.initial_widget_height + delta_y
            if self.min_height <= new_height <= self.max_height:
                self.target_widget.styles.height = new_height

    def on_mouse_up(self, event: events.MouseUp) -> None:
        if self.dragging:
            self.dragging = False
            self.release_mouse()
