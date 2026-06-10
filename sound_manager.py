# sound_manager.py
import pygame
import os

class SoundManager:
    """Менеджер звуков для упражнений"""
    
    def __init__(self):
        pygame.mixer.init()
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
            "Дождь": "./sounds/rain.mp3"
        }
        
        if sound_name not in sound_files:
            print(f"⚠️ Звук '{sound_name}' не найден в конфигурации")
            return False
        
        sound_path = sound_files[sound_name]
        
        if not os.path.exists(sound_path):
            print(f"❌ Файл звука не найден: {sound_path}")
            return False
        
        try:
            # Останавливаем текущий звук
            self.stop()
            
            # Загружаем новый звук
            self.current_sound = pygame.mixer.Sound(sound_path)
            self.sound_type = sound_name
            return True
            
        except Exception as e:
            print(f"❌ Ошибка загрузки звука: {e}")
            return False
    
    def play_loop(self):
        """Циклическое воспроизведение звука"""
        if self.current_sound and not self.is_playing:
            try:
                # Воспроизводим в цикле (-1 означает бесконечное повторение)
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