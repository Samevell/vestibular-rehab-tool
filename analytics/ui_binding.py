from __future__ import annotations

from typing import Any, Dict, Optional


def exercise_id_from_key(key: Optional[str]) -> Optional[int]:
    if not key or not key.startswith("ex"):
        return None
    try:
        return int(key[2:])
    except ValueError:
        return None


def read_exercise_params(ui, exercise_id: int) -> Dict[str, Any]:
    if exercise_id == 1:
        return {
            "apples_count": ui.spinBox_apple_count.value(),
            "seconds_per_apple": ui.spinBox_apple_second.value(),
            "background": ui.comboBox_fon_apple.currentText(),
            "sound": ui.comboBox_sound_apple.currentText(),
        }
    if exercise_id == 2:
        return {
            "apples_count": ui.spinBox_apple_count_2.value(),
            "seconds_per_apple": ui.spinBox_apple_second_2.value(),
            "background": ui.comboBox_fon_apple_2.currentText(),
        }
    if exercise_id == 3:
        return {
            "apples_count": ui.spinBox_apple_count_3.value(),
            "speed": ui.comboBox_speed_apple_3.currentText(),
            "background": ui.comboBox_fon_apple_3.currentText(),
        }
    if exercise_id == 4:
        return {
            "apples_count": ui.spinBox_ex4_count.value(),
            "time_sec": ui.spinBox_ex4_time.value(),
            "speed": ui.comboBox_ex4_speed.currentText(),
            "background": ui.comboBox_ex4_fon.currentText(),
        }
    if exercise_id == 5:
        return {
            "apples_count": ui.spinBox_ex5_count.value(),
            "time_sec": ui.spinBox_ex5_time.value(),
            "speed": ui.comboBox_ex5_speed.currentText(),
            "background": ui.comboBox_ex5_fon.currentText(),
        }
    if exercise_id == 6:
        return {
            "apples_count": ui.spinBox_ex6_count.value(),
            "time_sec": ui.spinBox_ex6_time.value(),
            "background": ui.comboBox_ex6_fon.currentText(),
        }
    if exercise_id == 7:
        return {
            "apples_count": ui.spinBox_ex7_count.value(),
            "time_sec": ui.spinBox_ex7_time.value(),
            "neck_range": ui.comboBox_ex7_neck.currentText(),
            "background": ui.comboBox_ex7_fon.currentText(),
        }
    if exercise_id == 8:
        return {
            "apples_count": ui.spinBox_ex8_count.value(),
            "color_interval": ui.spinBox_ex8_color_interval.value(),
            "speed": ui.comboBox_ex8_speed.currentText(),
            "background": ui.comboBox_ex8_fon.currentText(),
        }
    if exercise_id == 9:
        return {
            "apples_count": ui.spinBox_ex9_count.value(),
            "color_interval": ui.spinBox_ex9_color_interval.value(),
            "speed": ui.comboBox_ex9_speed.currentText(),
            "background": ui.comboBox_ex9_fon.currentText(),
        }
    return {}


def apply_exercise_params(ui, exercise_id: int, params: Dict[str, Any], load_only: bool = False) -> None:
    if exercise_id == 1:
        ui.spinBox_apple_count.setValue(int(params.get("apples_count", 12)))
        ui.spinBox_apple_second.setValue(int(params.get("seconds_per_apple", 10)))
        if not load_only:
            _set_combo_text(ui.comboBox_fon_apple, params.get("background"))
            _set_combo_text(ui.comboBox_sound_apple, params.get("sound"))
        return

    if exercise_id == 2:
        ui.spinBox_apple_count_2.setValue(int(params.get("apples_count", 5)))
        ui.spinBox_apple_second_2.setValue(int(params.get("seconds_per_apple", 4)))
        if not load_only:
            _set_combo_text(ui.comboBox_fon_apple_2, params.get("background"))
        return

    if exercise_id == 3:
        ui.spinBox_apple_count_3.setValue(int(params.get("apples_count", 5)))
        _set_combo_text(ui.comboBox_speed_apple_3, params.get("speed"))
        if not load_only:
            _set_combo_text(ui.comboBox_fon_apple_3, params.get("background"))
        return

    if exercise_id == 4:
        ui.spinBox_ex4_count.setValue(int(params.get("apples_count", 8)))
        ui.spinBox_ex4_time.setValue(int(params.get("time_sec", 60)))
        _set_combo_text(ui.comboBox_ex4_speed, params.get("speed"))
        if not load_only:
            _set_combo_text(ui.comboBox_ex4_fon, params.get("background"))
        return

    if exercise_id == 5:
        ui.spinBox_ex5_count.setValue(int(params.get("apples_count", 8)))
        ui.spinBox_ex5_time.setValue(int(params.get("time_sec", 60)))
        _set_combo_text(ui.comboBox_ex5_speed, params.get("speed"))
        if not load_only:
            _set_combo_text(ui.comboBox_ex5_fon, params.get("background"))
        return

    if exercise_id == 6:
        ui.spinBox_ex6_count.setValue(int(params.get("apples_count", 10)))
        ui.spinBox_ex6_time.setValue(int(params.get("time_sec", 90)))
        if not load_only:
            _set_combo_text(ui.comboBox_ex6_fon, params.get("background"))
        return

    if exercise_id == 7:
        ui.spinBox_ex7_count.setValue(int(params.get("apples_count", 10)))
        ui.spinBox_ex7_time.setValue(int(params.get("time_sec", 90)))
        _set_combo_text(ui.comboBox_ex7_neck, params.get("neck_range", "Средний"))
        if not load_only:
            _set_combo_text(ui.comboBox_ex7_fon, params.get("background"))
        return

    if exercise_id == 8:
        ui.spinBox_ex8_count.setValue(int(params.get("apples_count", 10)))
        ui.spinBox_ex8_color_interval.setValue(int(params.get("color_interval", 2)))
        _set_combo_text(ui.comboBox_ex8_speed, params.get("speed"))
        if not load_only:
            _set_combo_text(ui.comboBox_ex8_fon, params.get("background"))
        return

    if exercise_id == 9:
        ui.spinBox_ex9_count.setValue(int(params.get("apples_count", 10)))
        ui.spinBox_ex9_color_interval.setValue(int(params.get("color_interval", 2)))
        _set_combo_text(ui.comboBox_ex9_speed, params.get("speed"))
        if not load_only:
            _set_combo_text(ui.comboBox_ex9_fon, params.get("background"))


def load_dict_to_ui_params(exercise_id: int, load: Dict[str, Any]) -> Dict[str, Any]:
    """Преобразует результат recommend() в ключи виджетов формы."""
    params = dict(load)
    if exercise_id in (1, 2):
        params["apples_count"] = load.get("n", load.get("apples_count"))
        params["seconds_per_apple"] = load.get("tau", load.get("seconds_per_apple"))
    elif exercise_id == 3:
        params["apples_count"] = load.get("n", load.get("apples_count"))
        params["speed"] = load.get("speed", params.get("speed"))
    elif exercise_id in (4, 5):
        params["apples_count"] = load.get("n", load.get("apples_count"))
        params["time_sec"] = load.get("tau", load.get("time_sec"))
        params["speed"] = load.get("speed", params.get("speed"))
    elif exercise_id == 6:
        params["apples_count"] = load.get("n", load.get("apples_count"))
        params["time_sec"] = load.get("tau", load.get("time_sec"))
    elif exercise_id == 7:
        params["apples_count"] = load.get("n", load.get("apples_count"))
        params["time_sec"] = load.get("tau", load.get("time_sec"))
        params["neck_range"] = load.get("neck_range", params.get("neck_range", "Средний"))
    elif exercise_id in (8, 9):
        params["apples_count"] = load.get("n", load.get("apples_count"))
        params["color_interval"] = load.get("color_interval", params.get("color_interval"))
        params["speed"] = load.get("speed", params.get("speed"))
    return params


def _set_combo_text(combo, value: Optional[str]) -> None:
    if value is None:
        return
    idx = combo.findText(str(value))
    if idx >= 0:
        combo.setCurrentIndex(idx)
