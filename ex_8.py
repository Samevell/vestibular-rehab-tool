# ex_8.py - Упражнение 8: Движущиеся яблоки с изменением цвета и интервалом
from PyQt5.QtCore import QThread, pyqtSignal
import cv2
from app_paths import asset
from app_settings import open_camera, maybe_mirror, overlay_pose, filter_pause
import mediapipe as mp
import numpy as np
import time
import imageio
import random
from calibration import (
    Calibrator,
    catch_ok,
    check_runtime,
    draw_spawn_zone,
    head_ok,
    print_profile_summary,
    reset_runtime_guard,
    spawn_zone_bounds,
    torso_shift,
    user_hand_px,
)

# Инициализация распознавания поз
mp_pose = mp.solutions.pose
mp_hands = mp.solutions.hands  # Добавляем распознавание рук

# Загрузка текстуры яблока
apple_texture = cv2.imread(asset("img/apple.png"), cv2.IMREAD_UNCHANGED)
if apple_texture is None:
    print("Ошибка: не удалось загрузить изображение.")
    apple_texture = np.zeros((60, 60, 4), dtype=np.uint8)

# Загрузка анимаций
rain_gif = imageio.mimread(asset("img/rain.gif"))
rain_frames = [cv2.cvtColor(frame, cv2.COLOR_RGB2BGR) for frame in rain_gif]
rain_frame_count = len(rain_frames)

fog_gif = imageio.mimread(asset("img/fog.gif"))
fog_frames = [cv2.cvtColor(frame, cv2.COLOR_RGB2BGR) for frame in fog_gif]
fog_frame_count = len(fog_frames)

snow_gif = imageio.mimread(asset("img/snow.gif"))
snow_frames = [cv2.cvtColor(frame, cv2.COLOR_RGB2BGR) for frame in snow_gif]
snow_frame_count = len(snow_frames)

# Размеры яблока
circle_radius = 30
apple_size = (circle_radius * 2, circle_radius * 2)
apple_texture = cv2.resize(apple_texture, apple_size, interpolation=cv2.INTER_AREA)

# Константа для увеличения радиуса обнаружения
DETECTION_RADIUS = circle_radius + 10  # +10 пикселей для лучшей отзывчивости

def get_head_horizontal_position(results):
    """Определение горизонтального положения головы влево/вправо"""
    if not results.pose_landmarks:
        return "none"
    
    nose = results.pose_landmarks.landmark[mp_pose.PoseLandmark.NOSE]
    left_shoulder = results.pose_landmarks.landmark[mp_pose.PoseLandmark.LEFT_SHOULDER]
    right_shoulder = results.pose_landmarks.landmark[mp_pose.PoseLandmark.RIGHT_SHOULDER]
    
    mid_shoulder_x = (right_shoulder.x + left_shoulder.x) / 2
    threshold = 0.05
    
    if nose.x < mid_shoulder_x - threshold:
        return "left"
    elif nose.x > mid_shoulder_x + threshold:
        return "right"
    else:
        return "center"

def is_hand_near_apple(hand_position, apple_position):
    if apple_position is None or hand_position is None:
        return False
    return np.linalg.norm(np.array(hand_position) - np.array(apple_position)) < DETECTION_RADIUS

def get_all_hand_points(results_hands, frame_shape):
    """
    Получение всех точек руки: кончики пальцев и центр ладони
    Возвращает список позиций для проверки касания
    """
    hand_points = []
    h, w, _ = frame_shape
    
    if not results_hands.multi_hand_landmarks:
        return hand_points
    
    for hand_landmarks in results_hands.multi_hand_landmarks:
        # Кончики пальцев (landmark индексы)
        finger_tips = [4, 8, 12, 16, 20]  # Большой, указательный, средний, безымянный, мизинец
        
        for tip_idx in finger_tips:
            tip = hand_landmarks.landmark[tip_idx]
            tip_pos = (int(tip.x * w), int(tip.y * h))
            hand_points.append(tip_pos)
        
        # Центр ладони (усредненная позиция между запястьем и основанием пальцев)
        wrist = hand_landmarks.landmark[0]  # Запястье
        middle_finger_mcp = hand_landmarks.landmark[9]  # Основание среднего пальца
        
        palm_center_x = (wrist.x + middle_finger_mcp.x) / 2
        palm_center_y = (wrist.y + middle_finger_mcp.y) / 2
        palm_center_pos = (int(palm_center_x * w), int(palm_center_y * h))
        hand_points.append(palm_center_pos)
    
    return hand_points

class CameraThread8(QThread):
    frame_signal = pyqtSignal(np.ndarray)
    finished = pyqtSignal()

    def __init__(self, objects_count, time_sec, color_interval, speed, background, user_id=0):
        super().__init__()
        self.objects_count = objects_count
        self.time_sec = time_sec
        self.color_interval = color_interval
        self.speed = speed
        self.background = background
        self.stop_flag = False
        self.score = 0
        self.rounds = 0
        self.apple_position = [0, random.randint(50, 400)]
        self.apple_color = (0, 0, 255)
        self.person_detected = False
        self.apple_speed = self.calculate_speed()
        self.color_change_start_time = None
        self.animation_frame_index = 0
        self.required_direction = 'left'
        self.user_id = user_id
        self.profile = None
        self.calibrator = Calibrator(user_id)
        self.calibrated = False

    def calculate_speed(self):
        if self.speed == 'Медленно':
            return 2
        elif self.speed == 'Средне':
            return 4
        elif self.speed == 'Быстро':
            return 6
        else:
            return 2

    def run(self):
        pose = mp_pose.Pose()
        hands = mp_hands.Hands(min_detection_confidence=0.5, min_tracking_confidence=0.5)  # Инициализируем распознавание рук
        cap = open_camera()

        if not cap.isOpened():
            print("Камера не обнаружена.")
            return

        while cap.isOpened() and self.rounds < self.objects_count and not self.stop_flag:
            ret, frame = cap.read()
            if not ret:
                print("Не удалось получить кадр.")
                break

            frame = maybe_mirror(frame)
            image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results_pose = pose.process(image_rgb)
            results_hands = hands.process(image_rgb)  # Обрабатываем руки

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

            landmarks = results_pose.pose_landmarks
            overlay_pose(frame, landmarks)
            if not self.calibrated:
                calib = self.calibrator.tick(frame, landmarks)
                self.frame_signal.emit(calib.frame)
                if calib.done and calib.profile:
                    self.profile = calib.profile
                    self.calibrated = True
                    reset_runtime_guard()
                    print_profile_summary(self.profile)
                continue

            pause_msg = filter_pause(check_runtime(self.profile, landmarks, frame.shape[1], frame.shape[0]))
            if pause_msg:
                cv2.putText(frame, pause_msg, (20, frame.shape[0] // 2), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 220, 255), 2)
                self.frame_signal.emit(frame)
                continue

            shift = torso_shift(self.profile, landmarks, frame.shape[1], frame.shape[0]) if landmarks else (0.0, 0.0)
            frame = draw_spawn_zone(frame, self.profile, shift, hand="right")
            x1, y1, x2, y2 = spawn_zone_bounds(self.profile, shift, hand="right")
            self.apple_position[0] = max(x1, min(x2, self.apple_position[0]))
            self.apple_position[1] = max(y1, min(y2, self.apple_position[1]))

            # Движение яблока
            self.apple_position[0] += self.apple_speed

            # Проверка на границы экрана
            if self.apple_position[0] > x2:
                self.apple_position[0] = x1
                self.apple_position[1] = random.randint(y1, max(y1, y2))

            # Проверка смены цвета яблока
            if self.color_change_start_time and time.time() - self.color_change_start_time > self.color_interval:
                self.apple_color = (0, 0, 255)  # Вернуться к красному
                self.color_change_start_time = None

            # Случайное изменение цвета яблока
            if random.random() < 0.01 and self.color_change_start_time is None:
                self.apple_color = (0, 255, 0)  # Установить зеленый цвет
                self.color_change_start_time = time.time()

            # Проверка, касается ли рука яблока (улучшенная)
            if landmarks:
                # Проверка поимки (улучшенная)
                caught = False
                
                # Метод 1: Проверка через запястья (как в оригинале)
                h, w, _ = frame.shape
                left_hand_pos = user_hand_px(landmarks, w, h, "left")
                right_hand_pos = user_hand_px(landmarks, w, h, "right")

                # Проверяем, повернута ли голова в правильном направлении
                head_correct = head_ok(self.profile, landmarks, w, h, self.required_direction)
                
                if self.apple_color == (0, 255, 0) and head_correct and (
                        catch_ok(self.profile, left_hand_pos, self.apple_position) or
                        catch_ok(self.profile, right_hand_pos, self.apple_position)):
                    caught = True
                
                # Метод 2: Проверка через точки рук (пальцы и центр ладони) - для лучшей отзывчивости
                if not caught and self.apple_color == (0, 255, 0) and head_correct and results_hands.multi_hand_landmarks:
                    hand_points = get_all_hand_points(results_hands, frame.shape)
                    for hand_point in hand_points:
                        if catch_ok(self.profile, hand_point, self.apple_position):
                            caught = True
                            break
                
                # Если поймали
                if caught:
                    self.score += 1
                    self.rounds += 1
                    self.apple_color = (0, 0, 255)  # Вернуть цвет к красному
                    self.color_change_start_time = None
                    self.apple_position = [x1, random.randint(y1, max(y1, y2))]
                    # Меняем требуемое направление
                    self.required_direction = 'right' if self.required_direction == 'left' else 'left'

            # Отрисовка яблока
            if self.apple_position[0] >= 0:
                top_left_x = int(self.apple_position[0] - apple_size[0] // 2)
                top_left_y = int(self.apple_position[1] - apple_size[1] // 2)

                bottom_right_x = top_left_x + apple_size[0]
                bottom_right_y = top_left_y + apple_size[1]

                if (top_left_x < frame.shape[1] and bottom_right_x > 0 and
                    top_left_y < frame.shape[0] and bottom_right_y > 0):
                    
                    top_left_x = max(top_left_x, 0)
                    top_left_y = max(top_left_y, 0)
                    bottom_right_x = min(bottom_right_x, frame.shape[1])
                    bottom_right_y = min(bottom_right_y, frame.shape[0])

                    apple_texture_colored = apple_texture.copy()
                    apple_texture_colored[:, :, :3] = apple_texture_colored[:, :, :3] * np.array(self.apple_color) / 255.0
                    alpha_channel = apple_texture_colored[:, :, 3] / 255.0
                    apple_texture_bgr = apple_texture_colored[:, :, :3]

                    for c in range(3):
                        frame[top_left_y:bottom_right_y, top_left_x:bottom_right_x, c] = (
                            alpha_channel[:bottom_right_y - top_left_y, :bottom_right_x - top_left_x] * 
                            apple_texture_bgr[:bottom_right_y - top_left_y, :bottom_right_x - top_left_x, c] +
                            (1 - alpha_channel[:bottom_right_y - top_left_y, :bottom_right_x - top_left_x]) * 
                            frame[top_left_y:bottom_right_y, top_left_x:bottom_right_x, c]
                        )

            # Отображение интервала цвета и положения головы
            info_text = f"Interval: {self.color_interval}s"
            direction_text = f"Need: {self.required_direction}"
            cv2.putText(frame, info_text, (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(frame, direction_text, (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(frame, f'Score: {self.score}', (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)

            self.animation_frame_index += 1
            self.frame_signal.emit(frame)

        cap.release()
        pose.close()
        hands.close()  # Закрываем распознавание рук
        self.finished.emit()

    def stop(self):
        self.stop_flag = True