# detect_thread.py
from PyQt5.QtCore import QThread, pyqtSignal
import cv2
import mediapipe as mp
import numpy as np
import random
import time
import imageio
from calibration import Calibration
from sound_manager import SoundManager
from workspace import WorkspaceProfile, draw_overlay, random_point_in_workspace


# Инициализация распознавания поз и инструмента для отрисовки
mp_pose = mp.solutions.pose

# Загрузка текстуры яблока и восклицательного знака
apple_texture = cv2.imread('./img/apple.png', cv2.IMREAD_UNCHANGED)
exclamation_texture = cv2.imread('./img/znak.png', cv2.IMREAD_UNCHANGED)

if apple_texture is None or exclamation_texture is None:
    print("Ошибка: не удалось загрузить изображение.")
    exit()

# Загрузка анимации дождя из GIF
rain_gif = imageio.mimread('./img/rain.gif')
rain_frames = [cv2.cvtColor(frame, cv2.COLOR_RGB2BGR) for frame in rain_gif]
rain_frame_count = len(rain_frames)

# Загрузка анимации тумана из GIF
fog_gif = imageio.mimread('./img/fog.gif')
fog_frames = [cv2.cvtColor(frame, cv2.COLOR_RGB2BGR) for frame in fog_gif]
fog_frame_count = len(fog_frames)

# Загрузка анимации снега из GIF
snow_gif = imageio.mimread('./img/snow.gif')
snow_frames = [cv2.cvtColor(frame, cv2.COLOR_RGB2BGR) for frame in snow_gif]
snow_frame_count = len(snow_frames)

# Размеры яблока и восклицательного знака
circle_radius = 30
apple_size = (circle_radius * 2, circle_radius * 2)
apple_texture = cv2.resize(apple_texture, apple_size, interpolation=cv2.INTER_AREA)

exclamation_size = (50, 50)
exclamation_texture = cv2.resize(exclamation_texture, exclamation_size, interpolation=cv2.INTER_AREA)

def get_random_position(frame, workspace_profile=None, difficulty=1.0):
    """Случайная позиция яблока: в workspace или на весь кадр (fallback)."""
    if workspace_profile is not None:
        return random_point_in_workspace(
            workspace_profile,
            margin=0.1,
            difficulty=difficulty,
            target_radius=circle_radius,
        )
    h, w, _ = frame.shape
    x = random.randint(circle_radius, w - circle_radius)
    y = random.randint(circle_radius, h - circle_radius)
    return (x, y)

def is_head_straight(results):
    if results.pose_landmarks:
        nose = results.pose_landmarks.landmark[mp_pose.PoseLandmark.NOSE]
        left_shoulder = results.pose_landmarks.landmark[mp_pose.PoseLandmark.LEFT_SHOULDER]
        right_shoulder = results.pose_landmarks.landmark[mp_pose.PoseLandmark.RIGHT_SHOULDER]
        
        mid_shoulder_x = (right_shoulder.x + left_shoulder.x) / 2
        mid_shoulder_y = (right_shoulder.y + left_shoulder.y) / 2
        mid_shoulder = np.array([mid_shoulder_x, mid_shoulder_y])
        
        nose_vec = np.array([nose.x, nose.y])
        shoulder_vec = mid_shoulder
        angle = np.arctan2(nose_vec[1] - shoulder_vec[1], nose_vec[0] - shoulder_vec[0]) * (180 / np.pi)
        
        if 100 < abs(angle) < 80:
            return False
        
        left_eye = results.pose_landmarks.landmark[mp_pose.PoseLandmark.LEFT_EYE]
        right_eye = results.pose_landmarks.landmark[mp_pose.PoseLandmark.RIGHT_EYE]
        
        eye_line_angle = np.arctan2(left_eye.y - right_eye.y, left_eye.x - right_eye.x) * (180 / np.pi)
        
        if -15 < eye_line_angle < 15:
            return True
    return False

class CameraThread(QThread):
    # Сигнал для передачи кадра обратно в GUI
    frame_signal = pyqtSignal(np.ndarray)
    finished = pyqtSignal()  # Новый сигнал о завершении
    score_signal = pyqtSignal(int)  # Сигнал для передачи счета

    def __init__(self, difficulty, seconds, background, sound="Ничего", user_id=None, db=None):
        super().__init__()
        self.difficulty = difficulty
        self.seconds = seconds
        self.stop_flag = False
        self.rain_current_frame = 0
        self.fog_current_frame = 0
        self.snow_current_frame = 0
        self.background = background
        self.sound = sound
        self.score = 0
        self.user_id = user_id
        self.db = db
        self.workspace_profile = None
        self.session_start_time = None
        self.session_duration_sec = None
        self.exit_reason = "completed"

        self.sound_manager = SoundManager()
        if self.sound != "Ничего":
            self.sound_manager.load_sound(self.sound)

        self.calibration = Calibration()
        self.calibrated = False
        self.calibration.calibration_done.connect(self.on_calibration_done)

        if self.user_id and self.db:
            loaded = self.db.get_user_calibration(self.user_id)
            if loaded:
                self.workspace_profile = loaded
                self.calibrated = True
                print(f"Загружен профиль зоны для user_id={self.user_id}")

    def on_calibration_done(self, data):
        print("Калибровка завершена (сигнал получен):", data)
        profile = data.get("profile")
        touch_points = data.get("touch_points")
        if profile:
            self.workspace_profile = profile
            if self.user_id and self.db:
                self.db.save_user_calibration(self.user_id, profile, touch_points)
        self.calibrated = True
        self.session_start_time = time.time()

    def run(self):
        difficulty = self.difficulty
        seconds = self.seconds
        pose = mp_pose.Pose()

        cap = cv2.VideoCapture(0)

        if not cap.isOpened():
            print("Камера не обнаружена.")
            return

        # Переменные для игры
        circle_position = None
        score = 0
        counter = difficulty
        timer = seconds
        
        rounds = 0

        while cap.isOpened() and rounds < counter and not self.stop_flag:
            ret, frame = cap.read()
            if not ret:
                print("Не удалось получить кадр.")
                break
            
            frame = cv2.flip(frame, 1)
            image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # Обработка изображения для распознавания позы
            results = pose.process(image_rgb)

            # --- Калибровка ---
            if not self.calibrated:
                # Получаем кадр с калибровкой
                frame, calibration_completed = self.calibration.run(frame, results)
                
                # Отправляем кадр для отображения
                self.frame_signal.emit(frame)
                
                # Проверяем завершение калибровки
                if calibration_completed:
                    print("Калибровка завершена (через возвращаемое значение)")
                    self.calibrated = True
                    self.session_start_time = time.time()
                    # ЗАПУСКАЕМ ЗВУК ПОСЛЕ КАЛИБРОВКИ
                    if self.sound != "Ничего":
                        self.sound_manager.play_loop()
                
                continue

            if self.workspace_profile is not None:
                draw_overlay(frame, self.workspace_profile)

            if self.session_start_time is None:
                self.session_start_time = time.time()
                if self.sound != "Ничего":
                    self.sound_manager.play_loop()

            # Обработка фона
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

            # Получаем состояние головы
            head_straight = is_head_straight(results)

            # Если обнаружены ключевые точки
            if results.pose_landmarks:
                right_wrist = results.pose_landmarks.landmark[mp_pose.PoseLandmark.LEFT_WRIST]
                right_index = results.pose_landmarks.landmark[mp_pose.PoseLandmark.LEFT_INDEX]
                h, w, _ = frame.shape
                right_hand_x = int((right_wrist.x + right_index.x) / 2 * w)
                right_hand_y = int((right_wrist.y + right_index.y) / 2 * h)

                if circle_position is None:
                    load_difficulty = max(0.5, min(2.0, 12.0 / max(self.difficulty, 1)))
                    circle_position = get_random_position(
                        frame,
                        self.workspace_profile,
                        difficulty=load_difficulty,
                    )
                    start_time = time.time()

                # Проверка, прошло ли время
                if time.time() - start_time < timer:
                    # Проверяем, касается ли рука яблока и голова в правильном положении
                    if head_straight and ((right_hand_x - circle_position[0]) ** 2 + (right_hand_y - circle_position[1]) ** 2) ** 0.5 < circle_radius:
                        score += 1
                        self.score = score
                        self.score_signal.emit(score)
                        circle_position = None
                        rounds += 1
                    else:
                        # Отрисовка текстуры яблока
                        apple_height, apple_width = apple_texture.shape[:2]
                        top_left_x = circle_position[0] - apple_width // 2
                        top_left_y = circle_position[1] - apple_height // 2

                        # Проверка границ
                        if top_left_x >= 0 and top_left_y >= 0 and top_left_x + apple_width <= w and top_left_y + apple_height <= h:
                            alpha_channel = apple_texture[:, :, 3] / 255.0
                            apple_texture_bgr = apple_texture[:, :, :3]

                            for c in range(3):
                                frame[top_left_y:top_left_y + apple_height, top_left_x:top_left_x + apple_width, c] = (
                                    alpha_channel * apple_texture_bgr[:, :, c] +
                                    (1 - alpha_channel) * frame[top_left_y:top_left_y + apple_height, top_left_x:top_left_x + apple_width, c]
                                )
                else:
                    circle_position = None
                    rounds += 1

                # Если голова не прямо, отображаем восклицательный знак
                if not head_straight:
                    exclamation_x = (w - exclamation_size[0]) // 2
                    exclamation_y = 10
                    alpha_channel = exclamation_texture[:, :, 3] / 255.0
                    exclamation_texture_bgr = exclamation_texture[:, :, :3]

                    for c in range(3):
                        frame[exclamation_y:exclamation_y + exclamation_size[1], exclamation_x:exclamation_x + exclamation_size[0], c] = (
                            alpha_channel * exclamation_texture_bgr[:, :, c] +
                            (1 - alpha_channel) * frame[exclamation_y:exclamation_y + exclamation_size[1], exclamation_x:exclamation_x + exclamation_size[0], c]
                        )

            # Отображаем счетчик попаданий
            cv2.putText(frame, f'Score: {score}', (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            
            
            # Сигнал для обновления интерфейса
            self.frame_signal.emit(frame)
            
        self.sound_manager.stop()
        cap.release()
        self.score = score
        if self.session_start_time is not None:
            self.session_duration_sec = int(round(time.time() - self.session_start_time))
        else:
            self.session_duration_sec = None
        if self.stop_flag:
            self.exit_reason = "stopped"
        else:
            self.exit_reason = "completed"
        self.finished.emit()

    def stop(self):
        self.stop_flag = True