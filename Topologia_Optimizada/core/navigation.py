"""Navigation profile system.

The NavigationManager translates raw input events (mouse buttons, wheel,
keyboard modifiers) into canonical viewport actions (Orbit, Pan, Zoom,
Select, Fit, Rotate) according to a configurable profile.

Different CAD applications use different mappings:

- **Onshape**:   left-drag = orbit, right-drag = pan, scroll = zoom
- **AutoCAD**:   middle-drag = pan, shift+middle = orbit, scroll = zoom, left = select
- **Fusion 360**: shift+middle = orbit, middle = pan, scroll = zoom
- **Blender**:   middle-drag = orbit, shift+middle = pan, ctrl+middle = zoom

The viewport should NOT contain navigation-specific logic.  It calls
``NavigationManager.resolve(event)`` to obtain an action and executes it.

This module introduces the architecture.  The viewport continues to use
the existing VTK observer pattern; the NavigationManager wraps that
pattern so profiles can be swapped without touching the viewport.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class ViewportAction(str, Enum):
    ORBIT = "orbit"
    PAN = "pan"
    ZOOM_IN = "zoom_in"
    ZOOM_OUT = "zoom_out"
    SELECT = "select"
    FIT = "fit"
    ROTATE_LEFT = "rotate_left"
    ROTATE_RIGHT = "rotate_right"
    CONTEXT_MENU = "context_menu"
    NONE = "none"


class MouseButton(str, Enum):
    LEFT = "left"
    MIDDLE = "middle"
    RIGHT = "right"


@dataclass
class InputEvent:
    """Normalised input event from the viewport."""
    mouse_button: Optional[MouseButton] = None
    shift: bool = False
    ctrl: bool = False
    alt: bool = False
    wheel_delta: float = 0.0
    key_sym: Optional[str] = None
    double_click: bool = False


@dataclass
class ResolvedAction:
    """Result of resolving an InputEvent against a navigation profile."""
    action: ViewportAction
    sensitivity: float = 1.0
    data: Dict[str, Any] = None

    def __post_init__(self):
        if self.data is None:
            self.data = {}


class NavigationProfile(ABC):
    """Abstract navigation profile that maps input events to actions."""

    name: str = "abstract"
    display_name: str = "Abstract Profile"

    @abstractmethod
    def resolve(self, event: InputEvent) -> ResolvedAction:
        """Map an input event to a viewport action."""


class AutoCADProfile(NavigationProfile):
    """AutoCAD-style navigation (current default)."""

    name = "autocad"
    display_name = "AutoCAD"

    def resolve(self, event: InputEvent) -> ResolvedAction:
        # Keyboard shortcuts
        if event.key_sym:
            key = event.key_sym.lower()
            if key in ("n",):
                return ResolvedAction(action=ViewportAction.FIT)
            if key in ("r",):
                return ResolvedAction(action=ViewportAction.ROTATE_RIGHT)
            return ResolvedAction(action=ViewportAction.NONE)

        # Wheel = zoom
        if event.wheel_delta != 0:
            action = ViewportAction.ZOOM_IN if event.wheel_delta > 0 else ViewportAction.ZOOM_OUT
            return ResolvedAction(action=action)

        # Mouse buttons
        if event.mouse_button == MouseButton.LEFT:
            if event.double_click:
                return ResolvedAction(action=ViewportAction.FIT)
            return ResolvedAction(action=ViewportAction.SELECT)

        if event.mouse_button == MouseButton.MIDDLE:
            if event.shift:
                return ResolvedAction(action=ViewportAction.ORBIT)
            return ResolvedAction(action=ViewportAction.PAN)

        if event.mouse_button == MouseButton.RIGHT:
            return ResolvedAction(action=ViewportAction.CONTEXT_MENU)

        return ResolvedAction(action=ViewportAction.NONE)


class OnshapeProfile(NavigationProfile):
    """Onshape-style navigation."""

    name = "onshape"
    display_name = "Onshape"

    def resolve(self, event: InputEvent) -> ResolvedAction:
        if event.key_sym:
            if event.key_sym.lower() == "f":
                return ResolvedAction(action=ViewportAction.FIT)
            return ResolvedAction(action=ViewportAction.NONE)

        if event.wheel_delta != 0:
            action = ViewportAction.ZOOM_IN if event.wheel_delta > 0 else ViewportAction.ZOOM_OUT
            return ResolvedAction(action=action)

        if event.mouse_button == MouseButton.LEFT:
            if event.shift:
                return ResolvedAction(action=ViewportAction.ROTATE_LEFT)
            return ResolvedAction(action=ViewportAction.SELECT)

        if event.mouse_button == MouseButton.MIDDLE:
            return ResolvedAction(action=ViewportAction.PAN)

        if event.mouse_button == MouseButton.RIGHT:
            return ResolvedAction(action=ViewportAction.ORBIT)

        return ResolvedAction(action=ViewportAction.NONE)


class Fusion360Profile(NavigationProfile):
    """Fusion 360-style navigation."""

    name = "fusion360"
    display_name = "Fusion 360"

    def resolve(self, event: InputEvent) -> ResolvedAction:
        if event.key_sym:
            if event.key_sym.lower() == "f":
                return ResolvedAction(action=ViewportAction.FIT)
            return ResolvedAction(action=ViewportAction.NONE)

        if event.wheel_delta != 0:
            action = ViewportAction.ZOOM_IN if event.wheel_delta > 0 else ViewportAction.ZOOM_OUT
            return ResolvedAction(action=action)

        if event.mouse_button == MouseButton.LEFT:
            return ResolvedAction(action=ViewportAction.SELECT)

        if event.mouse_button == MouseButton.MIDDLE:
            if event.shift:
                return ResolvedAction(action=ViewportAction.ORBIT)
            return ResolvedAction(action=ViewportAction.PAN)

        if event.mouse_button == MouseButton.RIGHT:
            return ResolvedAction(action=ViewportAction.CONTEXT_MENU)

        return ResolvedAction(action=ViewportAction.NONE)


class BlenderProfile(NavigationProfile):
    """Blender-style navigation."""

    name = "blender"
    display_name = "Blender"

    def resolve(self, event: InputEvent) -> ResolvedAction:
        if event.key_sym:
            if event.key_sym.lower() == "numpadperiod" or event.key_sym == ".":
                return ResolvedAction(action=ViewportAction.FIT)
            return ResolvedAction(action=ViewportAction.NONE)

        if event.wheel_delta != 0:
            action = ViewportAction.ZOOM_IN if event.wheel_delta > 0 else ViewportAction.ZOOM_OUT
            return ResolvedAction(action=action)

        if event.mouse_button == MouseButton.MIDDLE:
            if event.ctrl:
                return ResolvedAction(action=ViewportAction.ZOOM_IN if event.wheel_delta > 0 else ViewportAction.ZOOM_OUT)
            if event.shift:
                return ResolvedAction(action=ViewportAction.PAN)
            return ResolvedAction(action=ViewportAction.ORBIT)

        if event.mouse_button == MouseButton.LEFT:
            return ResolvedAction(action=ViewportAction.SELECT)

        return ResolvedAction(action=ViewportAction.NONE)


# ====================================================================== #
# NavigationManager
# ====================================================================== #

class NavigationManager:
    """Central navigation dispatcher.

    The viewport creates a NavigationManager and registers its current
    profile.  On each input event the viewport calls ``resolve(event)``
    and executes the returned action.

    Profiles can be swapped at runtime without modifying the viewport.
    """

    PROFILES: Dict[str, NavigationProfile] = {}

    def __init__(self, profile_name: str = "autocad") -> None:
        # Register built-in profiles on first use
        if not self.PROFILES:
            for p in [AutoCADProfile(), OnshapeProfile(), Fusion360Profile(), BlenderProfile()]:
                self.PROFILES[p.name] = p
        self._current_name = profile_name
        self._current = self.PROFILES.get(profile_name, AutoCADProfile())

    @property
    def profile_name(self) -> str:
        return self._current_name

    @property
    def profile(self) -> NavigationProfile:
        return self._current

    def set_profile(self, name: str) -> bool:
        prof = self.PROFILES.get(name)
        if prof is None:
            return False
        self._current_name = name
        self._current = prof
        return True

    @staticmethod
    def available_profiles() -> List[Dict[str, str]]:
        if not NavigationManager.PROFILES:
            for p in [AutoCADProfile(), OnshapeProfile(), Fusion360Profile(), BlenderProfile()]:
                NavigationManager.PROFILES[p.name] = p
        return [
            {"name": p.name, "display_name": p.display_name}
            for p in NavigationManager.PROFILES.values()
        ]

    def resolve(self, event: InputEvent) -> ResolvedAction:
        return self._current.resolve(event)
