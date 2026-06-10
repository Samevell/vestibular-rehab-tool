# detect_thread.py
from PyQt5.QtCore import QThread, pyqtSignal
import cv2
import mediapipe as mp
import numpy as np
import time
import imageio

# Инициализация распознавания поз и инструмента для отрисовки
mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils

# Загрузка текстуры яблока
apple_texture = cv2.imread('./img/apple.png', cv2.IMREAD_UNCHANGED)
if apple_texture is None:
    print("Ошибка: не удалось загрузить изображение.")
    exit()

# Загрузка анимаций
rain_gif = imageio.mimread('./img/rain.gif')
rain_frames = [cv2.cvtColor(frame, cv2.COLOR_RGB2BGR) for frame in rain_gif]
rain_frame_count = len(rain_frames)

fog_gif = imageio.mimread('./img/fog.gif')
fog_frames = [cv2.cvtColor(frame, cv2.COLOR_RGB2BGR) for frame in fog_gif]
fog_frame_count = len(fog_frames)

snow_gif = imageio.mimread('./img/snow.gif')
snow_frames = [cv2.cvtColor(frame, cv2.COLOR_RGB2BGR) for frame in snow_gif]
snow_frame_count = len(snow_frames)

# Размеры яблока
circle_radius = 30
apple_size = (circle_radius * 2, circle_radius * 2)
apple_texture = cv2.resize(apple_texture, apple_size, interpolation=cv2.INTER_AREA)

# Функция для проверки, касается ли рука яблока
def is_hand_near_apple(hand_position, apple_position):
    if apple_position is None:
        return False  # Возвращаем False, если яблоко не задано
    return np.linalg.norm(np.array(hand_position) - np.array(apple_position)) < circle_radius

class CameraThread2(QThread):
    # Сигнал для передачи кадра обратно в GUI
    frame_signal = pyqtSignal(np.ndarray)
    finished = pyqtSignal()  # Новый сигнал

    def __init__(self, difficulty, seconds, background):
        super().__init__()
        self.difficulty = difficulty
        self.seconds = seconds
        self.stop_flag = False
        self.rain_current_frame = 0
        self.fog_current_frame = 0
        self.snow_current_frame = 0
        self.background = background
        self.apple_position = None  # Позиция яблока
        self.start_time = None  # Время появления яблока
        self.catch_time = None  # Время, когда яблоко было поймано
        self.score = 0  # Счетчик попаданий
        self.rounds = 0  # Счетчик раундов
        self.person_detected = False  # Флаг для обнаружения человека

    def run(self):
        pose = mp_pose.Pose()
        cap = cv2.VideoCapture(0)

        if not cap.isOpened():
            print("Камера не обнаружена.")
            return

        while cap.isOpened() and self.rounds < self.difficulty and not self.stop_flag:
            ret, frame = cap.read()
            if not ret:
                print("Не удалось получить кадр.")
                break

            frame = cv2.flip(frame, 1)
            image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # Обработка фона в зависимости от выбора
            if self.background == 'Дождь':
                if rain_frames:
                    rain_overlay = rain_frames[self.rain_current_frame]
                    self.rain_current_frame = (self.rain_current_frame + 1) % rain_frame_count
                    rain_overlay = cv2.resize(rain_overlay, (frame.shape[1], frame.shape[0]))
                    frame = cv2.addWeighted(frame, 0.5, rain_overlay, 0.5, 0)

            elif self.background == 'Туман':
                if fog_frames:
                    fog_overlay = fog_frames[self.fog_current_frame]
                    self.fog_current_frame = (self.fog_current_frame + 1) % fog_frame_count
                    fog_overlay = cv2.resize(fog_overlay, (frame.shape[1], frame.shape[0]))
                    frame = cv2.addWeighted(frame, 0.5, fog_overlay, 0.5, 0)

            elif self.background == 'Снег':
                if snow_frames:
                    snow_overlay = snow_frames[self.snow_current_frame]
                    self.snow_current_frame = (self.snow_current_frame + 1) % snow_frame_count
                    snow_overlay = cv2.resize(snow_overlay, (frame.shape[1], frame.shape[0]))
                    frame = cv2.addWeighted(frame, 0.5, snow_overlay, 0.5, 0)

            # Обработка изображения для распознавания позы
            results = pose.process(image_rgb)

            # Проверка на наличие человека
            if results.pose_landmarks:
                self.person_detected = True  # Человек обнаружен
                # Установка яблока в центр, если оно не установлено и прошло более 2 секунд с момента ловли
                if self.apple_position is None and (self.catch_time is None or time.time() - self.catch_time > 2):
                    h, w, _ = frame.shape
                    self.apple_position = (w // 2, h // 2)
                    self.start_time = time.time()

            # Проверка, прошло ли время для исчезновения яблока
            if self.start_time is not None and time.time() - self.start_time > self.seconds:
                self.apple_position = None  # Убираем яблоко
                self.rounds += 1  # Переход к следующему раунду
                self.start_time = None  # Сбрасываем таймер для яблока

            # Проверка, касается ли рука яблока
            if self.person_detected:
                if results.pose_landmarks:
                    left_wrist = results.pose_landmarks.landmark[mp_pose.PoseLandmark.LEFT_WRIST]
                    right_wrist = results.pose_landmarks.landmark[mp_pose.PoseLandmark.RIGHT_WRIST]
                    h, w, _ = frame.shape
                    left_hand_pos = (int(left_wrist.x * w), int(left_wrist.y * h))
                    right_hand_pos = (int(right_wrist.x * w), int(right_wrist.y * h))

                    # Условие для проверки, было ли поймано яблоко
                    if is_hand_near_apple(left_hand_pos, self.apple_position) or \
                       is_hand_near_apple(right_hand_pos, self.apple_position):
                        self.score += 1
                        self.catch_time = time.time()  # Сохраняем время ловли яблока
                        self.apple_position = None  # Убираем яблоко
                        self.rounds += 1  # Переход к следующему раунду

            # Проверка, установлено ли яблоко
            if self.apple_position is not None:
                # Отрисовка яблока
                top_left_x = self.apple_position[0] - apple_size[0] // 2
                top_left_y = self.apple_position[1] - apple_size[1] // 2
                apple_height, apple_width = apple_texture.shape[:2]
                alpha_channel = apple_texture[:, :, 3] / 255.0
                apple_texture_bgr = apple_texture[:, :, :3]
                
                for c in range(3):
                    frame[top_left_y:top_left_y + apple_height, top_left_x:top_left_x + apple_width, c] = (
                        alpha_channel * apple_texture_bgr[:, :, c] +
                        (1 - alpha_channel) * frame[top_left_y:top_left_y + apple_height, top_left_x:top_left_x + apple_width, c]
                    )

            # Отображаем счетчик попаданий на экране черным цветом
            cv2.putText(frame, f'Score: {self.score}', (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
            # Сигнал для обновления интерфейса
            self.frame_signal.emit(frame)

        cap.release()
        self.finished.emit()  # Сигнализируем о завершении

    def stop(self):
        self.stop_flag = True
