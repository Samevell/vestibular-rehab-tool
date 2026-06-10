# ex_4.py - Упражнение 4: Повороты головы влево/вправо с амплитудой
from PyQt5.QtCore import QThread, pyqtSignal
import cv2
import mediapipe as mp
import numpy as np
import time
import imageio
from ex_common import apple_is_active, draw_object_timer, normalize_time_sec

# Инициализация распознавания поз
mp_pose = mp.solutions.pose

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

def get_head_direction(results):
    """Определение направления поворота головы без точных градусов"""
    if not results.pose_landmarks:
        return "none"
    
    nose = results.pose_landmarks.landmark[mp_pose.PoseLandmark.NOSE]
    left_shoulder = results.pose_landmarks.landmark[mp_pose.PoseLandmark.LEFT_SHOULDER]
    right_shoulder = results.pose_landmarks.landmark[mp_pose.PoseLandmark.RIGHT_SHOULDER]
    
    # Центр плеч
    mid_shoulder_x = (right_shoulder.x + left_shoulder.x) / 2
    
    # Определяем поворот по относительной позиции носа
    # Если нос значительно смещен влево от центра плеч - поворот влево
    # Если нос значительно смещен вправо от центра плеч - поворот вправо
    threshold = 0.03  # Порог для определения поворота 
    
    if nose.x < mid_shoulder_x - threshold:
        return "left"
    elif nose.x > mid_shoulder_x + threshold:
        return "right"
    else:
        return "center"

def is_hand_near_apple(hand_position, apple_position):
    if apple_position is None:
        return False
    return np.linalg.norm(np.array(hand_position) - np.array(apple_position)) < circle_radius

class CameraThread4(QThread):
    frame_signal = pyqtSignal(np.ndarray)
    finished = pyqtSignal()

    def __init__(self, objects_count, time_sec, speed, background):
        super().__init__()
        self.objects_count = objects_count
        self.time_sec = normalize_time_sec(time_sec)
        self.speed = speed
        self.background = background
        self.stop_flag = False
        self.score = 0
        self.rounds = 0
        self.apple_position = None
        self.start_time = None
        self.required_direction = 'left'  # Начальное требуемое направление
        self.animation_frame_index = 0
        self.apple_speed = self.calculate_speed()
        self.apple_direction = 1  # 1 = вправо, -1 = влево

    def calculate_speed(self):
        if self.speed == 'Медленно':
            return 2
        elif self.speed == 'Средне':
            return 4
        elif self.speed == 'Быстро':
            return 6
        return 3

    def run(self):
        pose = mp_pose.Pose()
        cap = cv2.VideoCapture(0)

        if not cap.isOpened():
            print("Камера не обнаружена.")
            return

        while cap.isOpened() and self.rounds < self.objects_count and not self.stop_flag:
            ret, frame = cap.read()
            if not ret:
                print("Не удалось получить кадр.")
                break

            frame = cv2.flip(frame, 1)
            image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = pose.process(image_rgb)

            # Обработка фона
            if self.background == 'Дождь':
                if rain_frames:
                    rain_overlay = rain_frames[self.animation_frame_index % rain_frame_count]
                    rain_overlay = cv2.resize(rain_overlay, (frame.shape[1], frame.shape[0]))
                    frame = cv2.addWeighted(frame, 0.5, rain_overlay, 0.5, 0)

            elif self.background == 'Туман':
                if fog_frames:
                    fog_overlay = fog_frames[self.animation_frame_index % fog_frame_count]
                    fog_overlay = cv2.resize(fog_overlay, (frame.shape[1], frame.shape[0]))
                    frame = cv2.addWeighted(frame, 0.5, fog_overlay, 0.5, 0)

            elif self.background == 'Снег':
                if snow_frames:
                    snow_overlay = snow_frames[self.animation_frame_index % snow_frame_count]
                    snow_overlay = cv2.resize(snow_overlay, (frame.shape[1], frame.shape[0]))
                    frame = cv2.addWeighted(frame, 0.5, snow_overlay, 0.5, 0)

            # Определение направления головы
            head_direction = get_head_direction(results)

            if (self.apple_position is None and self.start_time is None
                    and results.pose_landmarks):
                h, w, _ = frame.shape
                self.apple_position = [circle_radius, np.random.randint(circle_radius, h - circle_radius)]
                self.apple_direction = 1
                self.start_time = time.time()

            if self.apple_position is not None and self.start_time is not None:
                if apple_is_active(self.start_time, self.time_sec):
                    self.apple_position[0] += self.apple_speed * self.apple_direction
                    if self.apple_position[0] > frame.shape[1] - circle_radius:
                        self.apple_direction = -1
                    elif self.apple_position[0] < circle_radius:
                        self.apple_direction = 1

                    if results.pose_landmarks:
                        left_wrist = results.pose_landmarks.landmark[mp_pose.PoseLandmark.LEFT_WRIST]
                        right_wrist = results.pose_landmarks.landmark[mp_pose.PoseLandmark.RIGHT_WRIST]
                        h, w, _ = frame.shape
                        left_hand_pos = (int(left_wrist.x * w), int(left_wrist.y * h))
                        right_hand_pos = (int(right_wrist.x * w), int(right_wrist.y * h))
                        head_correct = (head_direction == self.required_direction)
                        if head_correct and (is_hand_near_apple(left_hand_pos, self.apple_position) or
                                             is_hand_near_apple(right_hand_pos, self.apple_position)):
                            self.score += 1
                            self.apple_position = None
                            self.start_time = None
                            self.rounds += 1
                            self.required_direction = 'right' if self.required_direction == 'left' else 'left'
                else:
                    self.apple_position = None
                    self.start_time = None
                    self.rounds += 1

            draw_object_timer(frame, self.start_time, self.time_sec)

            if self.apple_position is not None and apple_is_active(self.start_time, self.time_sec):
                top_left_x = int(self.apple_position[0] - apple_size[0] // 2)
                top_left_y = int(self.apple_position[1] - apple_size[1] // 2)
                apple_height, apple_width = apple_texture.shape[:2]
                alpha_channel = apple_texture[:, :, 3] / 255.0
                apple_texture_bgr = apple_texture[:, :, :3]
                
                # Проверяем границы кадра
                if top_left_x >= 0 and top_left_y >= 0 and top_left_x + apple_width <= frame.shape[1] and top_left_y + apple_height <= frame.shape[0]:
                    for c in range(3):
                        frame[top_left_y:top_left_y + apple_height, top_left_x:top_left_x + apple_width, c] = (
                            alpha_channel * apple_texture_bgr[:, :, c] +
                            (1 - alpha_channel) * frame[top_left_y:top_left_y + apple_height, top_left_x:top_left_x + apple_width, c]
                        )

            # Отображение направления головы и требуемого направления
            direction_text = f"Head: {head_direction} | Need: {self.required_direction}"
            cv2.putText(frame, direction_text, (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(frame, f'Score: {self.score}', (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)

            self.animation_frame_index += 1
            self.frame_signal.emit(frame)

        cap.release()
        self.finished.emit()

    def stop(self):
        self.stop_flag = True