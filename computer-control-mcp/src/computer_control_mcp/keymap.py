"""Map xdotool-style key names (same tokens as computer-use-mcp) to PyAutoGUI key names."""

from __future__ import annotations

import sys

def _super_key() -> str:
    return "command" if sys.platform == "darwin" else "win"


def _super_left() -> str:
    return "command" if sys.platform == "darwin" else "winleft"


def _super_right() -> str:
    return "command" if sys.platform == "darwin" else "winright"


KEY_MAP: dict[str, str] = {
    # Function keys
    "f1": "f1",
    "f2": "f2",
    "f3": "f3",
    "f4": "f4",
    "f5": "f5",
    "f6": "f6",
    "f7": "f7",
    "f8": "f8",
    "f9": "f9",
    "f10": "f10",
    "f11": "f11",
    "f12": "f12",
    "f13": "f13",
    "f14": "f14",
    "f15": "f15",
    "f16": "f16",
    "f17": "f17",
    "f18": "f18",
    "f19": "f19",
    "f20": "f20",
    "f21": "f21",
    "f22": "f22",
    "f23": "f23",
    "f24": "f24",
    # Navigation
    "home": "home",
    "left": "left",
    "up": "up",
    "right": "right",
    "down": "down",
    "page_up": "pageup",
    "pageup": "pageup",
    "prior": "pageup",
    "page_down": "pagedown",
    "pagedown": "pagedown",
    "next": "pagedown",
    "end": "end",
    # Editing
    "return": "return",
    "enter": "return",
    "tab": "tab",
    "space": "space",
    "backspace": "backspace",
    "delete": "delete",
    "del": "delete",
    "escape": "esc",
    "esc": "esc",
    "insert": "insert",
    "ins": "insert",
    # Modifiers
    "shift_l": "shiftleft",
    "shift_r": "shiftright",
    "l_shift": "shiftleft",
    "r_shift": "shiftright",
    "shift": "shift",
    "control_l": "ctrlleft",
    "control_r": "ctrlright",
    "l_control": "ctrlleft",
    "r_control": "ctrlright",
    "control": "ctrl",
    "ctrl_l": "ctrlleft",
    "ctrl_r": "ctrlright",
    "l_ctrl": "ctrlleft",
    "r_ctrl": "ctrlright",
    "ctrl": "ctrl",
    "alt_l": "altleft",
    "alt_r": "altright",
    "l_alt": "altleft",
    "r_alt": "altright",
    "alt": "alt",
    "super_l": "__super_l__",
    "super_r": "__super_r__",
    "l_super": "__super_l__",
    "r_super": "__super_r__",
    "super": "__super__",
    "win_l": "__super_l__",
    "win_r": "__super_r__",
    "l_win": "__super_l__",
    "r_win": "__super_r__",
    "win": "__super__",
    "meta_l": "__super_l__",
    "meta_r": "__super_r__",
    "l_meta": "__super_l__",
    "r_meta": "__super_r__",
    "meta": "__super__",
    "command": "command",
    "command_l": "command",
    "l_command": "command",
    "command_r": "command",
    "r_command": "command",
    "cmd": "command",
    "cmd_l": "command",
    "l_cmd": "command",
    "cmd_r": "command",
    "r_cmd": "command",
    "caps_lock": "capslock",
    "capslock": "capslock",
    "caps": "capslock",
    # Keypad
    "kp_0": "num0",
    "kp_1": "num1",
    "kp_2": "num2",
    "kp_3": "num3",
    "kp_4": "num4",
    "kp_5": "num5",
    "kp_6": "num6",
    "kp_7": "num7",
    "kp_8": "num8",
    "kp_9": "num9",
    "kp_divide": "divide",
    "kp_multiply": "multiply",
    "kp_subtract": "subtract",
    "kp_add": "add",
    "kp_decimal": "decimal",
    "kp_equal": "=",
    "num_lock": "numlock",
    "numlock": "numlock",
    # Letters
    "a": "a",
    "b": "b",
    "c": "c",
    "d": "d",
    "e": "e",
    "f": "f",
    "g": "g",
    "h": "h",
    "i": "i",
    "j": "j",
    "k": "k",
    "l": "l",
    "m": "m",
    "n": "n",
    "o": "o",
    "p": "p",
    "q": "q",
    "r": "r",
    "s": "s",
    "t": "t",
    "u": "u",
    "v": "v",
    "w": "w",
    "x": "x",
    "y": "y",
    "z": "z",
    # Numbers (named keys, distinct from keypad)
    "0": "0",
    "1": "1",
    "2": "2",
    "3": "3",
    "4": "4",
    "5": "5",
    "6": "6",
    "7": "7",
    "8": "8",
    "9": "9",
    # Punctuation
    "minus": "-",
    "equal": "=",
    "bracketleft": "[",
    "bracketright": "]",
    "bracket_l": "[",
    "bracket_r": "]",
    "l_bracket": "[",
    "r_bracket": "]",
    "backslash": "\\",
    "semicolon": ";",
    "semi": ";",
    "quote": "'",
    "grave": "`",
    "comma": ",",
    "period": ".",
    "slash": "/",
    # Media keys (PyAutoGUI names)
    "audio_mute": "volumemute",
    "mute": "volumemute",
    "audio_vol_down": "volumedown",
    "voldown": "volumedown",
    "vol_down": "volumedown",
    "audio_vol_up": "volumeup",
    "volup": "volumeup",
    "vol_up": "volumeup",
    "audio_play": "playpause",
    "play": "playpause",
    "audio_stop": "stop",
    "stop": "stop",
    "audio_pause": "playpause",
    "pause": "playpause",
    "audio_prev": "prevtrack",
    "audio_next": "nexttrack",
}

_sl = _super_left()
_sr = _super_right()
_sk = _super_key()
for _k, _v in list(KEY_MAP.items()):
    if _v == "__super_l__":
        KEY_MAP[_k] = _sl
    elif _v == "__super_r__":
        KEY_MAP[_k] = _sr
    elif _v == "__super__":
        KEY_MAP[_k] = _sk


class InvalidKeyError(ValueError):
    def __init__(self, key: str) -> None:
        super().__init__(f"Invalid key: {key}")
        self.key = key


def to_pyautogui_keys(xdotool_string: str) -> list[str]:
    if not xdotool_string:
        raise InvalidKeyError("Empty string")
    out: list[str] = []
    for key_str in xdotool_string.split("+"):
        key = key_str.strip().lower()
        mapped = KEY_MAP.get(key)
        if mapped is None:
            raise InvalidKeyError(key)
        out.append(mapped)
    return out
