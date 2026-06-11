# detect_thread.py
from PyQt5.QtCore import QThread, pyqtSignal
import cv2
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
    print_profile_summary,
    reset_runtime_guard,
    spawn_object,
    torso_shift,
    user_hand_px,
)

# Инициализация распознавания поз и инструмента для отрисовки
mp_pose = mp.solutions.pose
mp_hands = mp.solutions.hands  # Добавляем распознавание рук
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

# Константа для кулдауна
CATCH_COOLDOWN = 0.3  # Предотвращает множественные срабатывания

# Функция для проверки, касается ли рука яблока (увеличиваем радиус для лучшей отзывчивости)
def is_hand_near_apple(hand_position, apple_position):
    if apple_position is None or hand_position is None:
        return False
    # Увеличиваем радиус обнаружения для более легкой поимки
    detection_radius = circle_radius + 10  # +10 пикселей для лучшей отзывчивости
    return np.linalg.norm(np.array(hand_position) - np.array(apple_position)) < detection_radius

class CameraThread2(QThread):
    # Сигнал для передачи кадра обратно в GUI
    frame_signal = pyqtSignal(np.ndarray)
    finished = pyqtSignal()  # Новый сигнал

    def __init__(self, difficulty, seconds, background, user_id=0):
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
        self.last_catch_time = 0  # Время последней поимки для кулдауна
        self.user_id = user_id
        self.profile = None
        self.calibrator = Calibrator(user_id)
        self.calibrated = False

    def get_all_hand_points(self, results_hands, frame_shape):
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

    def run(self):
        pose = mp_pose.Pose()
        hands = mp_hands.Hands(min_detection_confidence=0.5, min_tracking_confidence=0.5)  # Инициализируем распознавание рук
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

            # Обработка изображения для распознавания позы и рук
            results_pose = pose.process(image_rgb)
            results_hands = hands.process(image_rgb)

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

            # Проверка на наличие человека
            if landmarks:
                self.person_detected = True
                # Установка яблока в центр, если оно не установлено и прошло более 2 секунд с момента ловли
                if self.apple_position is None and (self.catch_time is None or time.time() - self.catch_time > 2):
                    self.apple_position = spawn_object(self.profile, shift, hand="right")
                    self.start_time = time.time()

            # Проверка, прошло ли время для исчезновения яблока
            if self.start_time is not None and time.time() - self.start_time > self.seconds:
                self.apple_position = None
                self.rounds += 1
                self.start_time = None

            # Проверка, касается ли рука яблока (улучшенная с кулдауном)
            if self.person_detected and self.apple_position is not None:
                # Проверяем кулдаун
                if time.time() - self.last_catch_time < CATCH_COOLDOWN:
                    pass  # Пропускаем проверку, если кулдаун активен
                else:
                    caught = False
                    
                    # Метод 1: Проверка через запястья (как в оригинале)
                    if landmarks:
                        h, w, _ = frame.shape
                        right_hand_pos = user_hand_px(landmarks, w, h, "right")
                        left_hand_pos = user_hand_px(landmarks, w, h, "left")
                        if catch_ok(self.profile, left_hand_pos, self.apple_position) or \
                           catch_ok(self.profile, right_hand_pos, self.apple_position):
                            caught = True
                    
                    # Метод 2: Проверка через точки рук (пальцы и центр ладони) - для лучшей отзывчивости
                    if not caught and results_hands.multi_hand_landmarks:
                        hand_points = self.get_all_hand_points(results_hands, frame.shape)
                        for hand_point in hand_points:
                            if catch_ok(self.profile, hand_point, self.apple_position):
                                caught = True
                                break
                    
                    # Если поймали
                    if caught:
                        self.score += 1
                        self.last_catch_time = time.time()  # Запоминаем время поимки для кулдауна
                        self.catch_time = time.time()
                        self.apple_position = None
                        self.rounds += 1
                        self.start_time = None

            # Проверка, установлено ли яблоко
            if self.apple_position is not None:
                # Отрисовка яблока
                top_left_x = self.apple_position[0] - apple_size[0] // 2
                top_left_y = self.apple_position[1] - apple_size[1] // 2
                apple_height, apple_width = apple_texture.shape[:2]
                alpha_channel = apple_texture[:, :, 3] / 255.0
                apple_texture_bgr = apple_texture[:, :, :3]
                
                # Проверка границ
                if (top_left_x >= 0 and top_left_y >= 0 and 
                    top_left_x + apple_width <= frame.shape[1] and 
                    top_left_y + apple_height <= frame.shape[0]):
                    
                    for c in range(3):
                        frame[top_left_y:top_left_y + apple_height, 
                              top_left_x:top_left_x + apple_width, c] = (
                            alpha_channel * apple_texture_bgr[:, :, c] +
                            (1 - alpha_channel) * frame[top_left_y:top_left_y + apple_height, 
                                                        top_left_x:top_left_x + apple_width, c]
                        )

            # Отображаем счетчик попаданий на экране
            cv2.putText(frame, f'Score: {self.score}', (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
            
            # Сигнал для обновления интерфейса
            self.frame_signal.emit(frame)

        cap.release()
        pose.close()
        hands.close()  # Закрываем распознавание рук
        self.finished.emit()

    def stop(self):
        self.stop_flag = True