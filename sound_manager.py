# sound_manager.py
import pygame
import os

from app_paths import asset

DEFAULT_OUTPUT_LABEL = "Системный по умолчанию"
_active_output = object()


def list_audio_outputs():
    """Список устройств воспроизведения: (подпись, id)."""
    devices = [(DEFAULT_OUTPUT_LABEL, "")]
    try:
        if pygame.mixer.get_init() is None:
            pygame.mixer.init()
        from pygame._sdl2.audio import get_audio_device_names

        for name in get_audio_device_names(False) or []:
            if name and name not in {item[1] for item in devices}:
                devices.append((name, name))
    except Exception as e:
        print(f"⚠️ Не удалось получить список динамиков: {e}")
    return devices


def apply_audio_output(device_name=None):
    """Переключает pygame.mixer на выбранный динамик."""
    global _active_output
    from app_settings import audio_output

    name = device_name if device_name is not None else audio_output()
    name = (name or "").strip() or None
    if pygame.mixer.get_init() is not None and _active_output == name:
        return True
    if pygame.mixer.get_init() is not None:
        pygame.mixer.quit()
    try:
        if name:
            pygame.mixer.init(devicename=name)
        else:
            pygame.mixer.init()
        _active_output = name
        return True
    except Exception as e:
        print(f"⚠️ Не удалось открыть динамик '{name}': {e}")
        try:
            pygame.mixer.init()
            _active_output = None
        except Exception:
            pass
        return False


class SoundManager:
    """Менеджер звуков для упражнений"""
    
    def __init__(self):
        apply_audio_output()
        self.current_sound = None
        self.is_playing = False
        self.sound_type = None
        
    def load_sound(self, sound_name):
        """
        Загрузка звукового файла
        sound_name: 'rain' или None
        """
        if sound_name is None or sound_name == "Ничего":
            self.stop()
            return False
        
        sound_files = {
            "Дождь": asset("sounds/rain.mp3")
        }
        
        if sound_name not in sound_files:
            print(f"⚠️ Звук '{sound_name}' не найден в конфигурации")
            return False
        
        sound_path = sound_files[sound_name]
        
        if not os.path.exists(sound_path):
            print(f"❌ Файл звука не найден: {sound_path}")
            return False
        
        try:
            self.stop()
            self.current_sound = pygame.mixer.Sound(sound_path)
            from app_settings import volume_f
            self.current_sound.set_volume(volume_f())
            self.sound_type = sound_name
            return True
            
        except Exception as e:
            print(f"❌ Ошибка загрузки звука: {e}")
            return False
    
    def play_loop(self):
        """Циклическое воспроизведение звука"""
        if self.current_sound and not self.is_playing:
            try:
                from app_settings import volume_f
                self.current_sound.set_volume(volume_f())
                self.current_sound.play(loops=-1)
                self.is_playing = True
                print(f"🎵 Воспроизведение звука: {self.sound_type}")
            except Exception as e:
                print(f"❌ Ошибка воспроизведения звука: {e}")
    
    def stop(self):
        """Остановка воспроизведения"""
        if self.is_playing:
            pygame.mixer.stop()
            self.is_playing = False
            print("🔇 Звук остановлен")
    
    def set_volume(self, volume=0.5):
        """Установка громкости (0.0 - 1.0)"""
        if self.current_sound:
            self.current_sound.set_volume(volume)
        try:
            pygame.mixer.music.set_volume(volume)
        except Exception:
            pass