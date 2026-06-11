# ex_9.py - Упражнение 9: Вертикально движущиеся яблоки с изменением цвета
from PyQt5.QtCore import QThread, pyqtSignal
import cv2
import mediapipe as mp
import numpy as np
import time
import imageio
import random
from PIL import Image, ImageDraw, ImageFont
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

# Константа для увеличения радиуса обнаружения
DETECTION_RADIUS = circle_radius + 10  # +10 пикселей для лучшей отзывчивости

def draw_russian_text(frame, text, position, font_scale, color, thickness):
    """Функция для корректного отображения русского текста"""
    try:
        # Конвертируем OpenCV frame в PIL Image
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame_pil = Image.fromarray(frame_rgb)
        draw = ImageDraw.Draw(frame_pil)
        
        # Загружаем шрифт с поддержкой кириллицы
        try:
            font = ImageFont.truetype("arial.ttf", int(font_scale * 20))
        except:
            try:
                font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", int(font_scale * 20))
            except:
                font = ImageFont.load_default()
        
        # Рисуем текст
        draw.text(position, text, font=font, fill=(color[2], color[1], color[0]))
        
        # Конвертируем обратно в OpenCV frame
        frame = cv2.cvtColor(np.array(frame_pil), cv2.COLOR_RGB2BGR)
        return frame
    except Exception as e:
        # Если PIL не работает, используем стандартный OpenCV (без кириллицы)
        cv2.putText(frame, text.encode('utf-8').decode('ascii', 'ignore'), 
                   position, cv2.FONT_HERSHEY_SIMPLEX, font_scale, color, thickness)
        return frame

def get_head_vertical_position(results):
    """Определение вертикального положения головы вверх/вниз"""
    if not results.pose_landmarks:
        return "none"
    
    nose = results.pose_landmarks.landmark[mp_pose.PoseLandmark.NOSE]
    left_ear = results.pose_landmarks.landmark[mp_pose.PoseLandmark.LEFT_EAR]
    right_ear = results.pose_landmarks.landmark[mp_pose.PoseLandmark.RIGHT_EAR]
    
    # Используем уши для определения наклона головы
    mid_ear_y = (left_ear.y + right_ear.y) / 2
    threshold = 0.02
    
    if nose.y < mid_ear_y - threshold:
        return "up"      # Голова поднята вверх
    elif nose.y > mid_ear_y + threshold:
        return "down"    # Голова опущена вниз
    else:
        return "center"  # Голова прямо

def get_neck_range_threshold(neck_range):
    """Получение порога диапазона шеи для вертикального движения"""
    if neck_range == 'Маленький':
        return 0.015
    elif neck_range == 'Средний':
        return 0.025
    elif neck_range == 'Большой':
        return 0.035
    else:
        return 0.025

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

class CameraThread9(QThread):
    frame_signal = pyqtSignal(np.ndarray)
    finished = pyqtSignal()

    def __init__(self, objects_count, color_interval, speed, background, user_id=0):
        super().__init__()
        self.objects_count = objects_count
        self.color_interval = float(color_interval)
        self.speed = speed
        self.background = background
        
        self.stop_flag = False
        self.score = 0
        self.rounds = 0
        
        # Позиция яблока: [x, y], движется по вертикали
        self.apple_position = None  # Будет инициализировано при первом кадре
        self.apple_color = (0, 0, 255)  # Красный цвет (BGR)
        self.apple_speed = self.calculate_speed()
        self.color_change_start_time = None
        self.animation_frame_index = 0
        self.required_direction = 'up'  # Вертикальное направление
        self.pose = None  # Для инициализации в run
        self.user_id = user_id
        self.profile = None
        self.calibrator = Calibrator(user_id)
        self.calibrated = False

    def calculate_speed(self):
        """Расчет скорости движения яблока (пикселей в секунду)"""
        if self.speed == 'Медленно':
            return 2
        elif self.speed == 'Средне':
            return 3
        elif self.speed == 'Быстро':
            return 5
        else:
            return 3

    def run(self):
        self.pose = mp_pose.Pose()
        hands = mp_hands.Hands(min_detection_confidence=0.5, min_tracking_confidence=0.5)  # Инициализируем распознавание рук
        cap = cv2.VideoCapture(0)

        if not cap.isOpened():
            print("Камера не обнаружена.")
            return

        # Инициализация позиции яблока при первом кадре
        first_frame = True
        
        while cap.isOpened() and self.rounds < self.objects_count and not self.stop_flag:
            ret, frame = cap.read()
            if not ret:
                print("Не удалось получить кадр.")
                break

            frame = cv2.flip(frame, 1)
            image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results_pose = self.pose.process(image_rgb)
            results_hands = hands.process(image_rgb)  # Обрабатываем руки
            landmarks = results_pose.pose_landmarks

            if not self.calibrated:
                calib = self.calibrator.tick(frame, landmarks)
                self.frame_signal.emit(calib.frame)
                if calib.done and calib.profile:
                    self.profile = calib.profile
                    self.calibrated = True
                    reset_runtime_guard()
                    print_profile_summary(self.profile)
                continue

            pause_msg = check_runtime(self.profile, landmarks, frame.shape[1], frame.shape[0])
            if pause_msg:
                cv2.putText(frame, pause_msg, (20, frame.shape[0] // 2), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 220, 255), 2)
                self.frame_signal.emit(frame)
                continue

            shift = torso_shift(self.profile, landmarks, frame.shape[1], frame.shape[0]) if landmarks else (0.0, 0.0)
            frame = draw_spawn_zone(frame, self.profile, shift, hand="right")
            x1, y1, x2, y2 = spawn_zone_bounds(self.profile, shift, hand="right")
            
            # Инициализация позиции яблока при первом кадре
            if first_frame and landmarks:
                self.apple_position = [random.randint(x1, max(x1, x2)), y1]
                first_frame = False

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

            # Определение вертикального положения головы
            head_vertical = get_head_vertical_position(results_pose)
            
            # Движение яблока ПО ВЕРТИКАЛИ
            if self.apple_position is not None:
                self.apple_position[1] += self.apple_speed

                # Проверка на границы экрана (по вертикали)
                if self.apple_position[1] > frame.shape[0]:
                    # Яблоко достигло низа, сбрасываем наверх
                    self.apple_position[1] = y1
                    self.apple_position[0] = random.randint(x1, max(x1, x2))
                    self.apple_color = (0, 0, 255)  # Сбрасываем цвет на красный
                    self.color_change_start_time = None

                # Управление сменой цвета (зеленый -> можно ловить)
                if self.color_change_start_time and time.time() - self.color_change_start_time > self.color_interval:
                    self.apple_color = (0, 0, 255)  # Возвращаем к красному
                    self.color_change_start_time = None

                # Случайная смена цвета яблока на зеленый
                if random.random() < 0.01 and self.color_change_start_time is None:
                    self.apple_color = (0, 255, 0)  # Зеленый цвет
                    self.color_change_start_time = time.time()

            # Проверка ловли яблока (улучшенная)
            if landmarks and self.apple_position is not None:
                # Проверка поимки (улучшенная)
                caught = False
                
                # Метод 1: Проверка через запястья (как в оригинале)
                h, w, _ = frame.shape
                left_hand_pos = user_hand_px(landmarks, w, h, "left")
                right_hand_pos = user_hand_px(landmarks, w, h, "right")

                # Проверяем, наклонена ли голова в правильном направлении
                head_correct = head_ok(self.profile, landmarks, w, h, self.required_direction)
                
                # Можно ловить только когда яблоко зеленое
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
                    # Сбрасываем яблоко наверх
                    self.apple_position = [random.randint(x1, max(x1, x2)), y1]
                    self.apple_color = (0, 0, 255)
                    self.color_change_start_time = None
                    # Меняем требуемое направление (вверх/вниз)
                    self.required_direction = 'down' if self.required_direction == 'up' else 'up'

            # Отрисовка яблока с изменением цвета
            if self.apple_position is not None and self.apple_position[1] >= -apple_size[1]:
                top_left_x = int(self.apple_position[0] - apple_size[0] // 2)
                top_left_y = int(self.apple_position[1] - apple_size[1] // 2)

                bottom_right_x = top_left_x + apple_size[0]
                bottom_right_y = top_left_y + apple_size[1]

                # Проверка границ
                if (bottom_right_x > 0 and top_left_x < frame.shape[1] and
                    bottom_right_y > 0 and top_left_y < frame.shape[0]):
                    
                    top_left_x = max(top_left_x, 0)
                    top_left_y = max(top_left_y, 0)
                    bottom_right_x = min(bottom_right_x, frame.shape[1])
                    bottom_right_y = min(bottom_right_y, frame.shape[0])

                    # Изменяем цвет текстуры яблока
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

            # Отображение текста
            # Счет
            cv2.putText(frame, f'Score: {self.score}', (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
            
            # Текст на русском (с помощью PIL)
            head_text = {
                'up': 'вверх',
                'down': 'вниз',
                'center': 'прямо',
                'none': 'не определено'
            }.get(head_vertical, head_vertical)
            
            need_text = 'ВВЕРХ' if self.required_direction == 'up' else 'ВНИЗ'
            
            direction_text = f"Положение головы: {head_text} | Нужно: {need_text}"
            frame = draw_russian_text(frame, direction_text, (10, 60), 0.7, (0, 255, 0), 2)
        

            self.animation_frame_index += 1
            self.frame_signal.emit(frame)

        cap.release()
        self.pose.close()
        hands.close()  # Закрываем распознавание рук
        self.finished.emit()

    def stop(self):
        self.stop_flag = True