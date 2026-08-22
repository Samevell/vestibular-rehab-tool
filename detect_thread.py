# detect_thread.py
from PyQt5.QtCore import QThread, pyqtSignal
import cv2
from app_paths import asset
from app_settings import open_camera, maybe_mirror, overlay_pose, filter_pause
import mediapipe as mp
import numpy as np
import time
import imageio
from calibration import (
    Calibrator,
    catch_ok,
    check_runtime,
    draw_spawn_zone,
    head_ok,
    print_profile_summary,
    reset_runtime_guard,
    spawn_object,
    torso_shift,
    user_hand_px,
)
from sound_manager import SoundManager
from cv_text import put_text_ru


mp_pose = mp.solutions.pose
mp_hands = mp.solutions.hands

apple_texture = cv2.imread(asset("img/apple.png"), cv2.IMREAD_UNCHANGED)
exclamation_texture = cv2.imread(asset("img/znak.png"), cv2.IMREAD_UNCHANGED)

if apple_texture is None:
    print("Ошибка: не удалось загрузить img/apple.png")
    apple_texture = np.zeros((60, 60, 4), dtype=np.uint8)
if exclamation_texture is None:
    print("Ошибка: не удалось загрузить img/znak.png")
    exclamation_texture = np.zeros((60, 60, 4), dtype=np.uint8)

rain_gif = imageio.mimread(asset("img/rain.gif"))
rain_frames = [cv2.cvtColor(frame, cv2.COLOR_RGB2BGR) for frame in rain_gif]
rain_frame_count = len(rain_frames)

fog_gif = imageio.mimread(asset("img/fog.gif"))
fog_frames = [cv2.cvtColor(frame, cv2.COLOR_RGB2BGR) for frame in fog_gif]
fog_frame_count = len(fog_frames)

snow_gif = imageio.mimread(asset("img/snow.gif"))
snow_frames = [cv2.cvtColor(frame, cv2.COLOR_RGB2BGR) for frame in snow_gif]
snow_frame_count = len(snow_frames)

circle_radius = 30
apple_size = (circle_radius * 2, circle_radius * 2)
apple_texture = cv2.resize(apple_texture, apple_size, interpolation=cv2.INTER_AREA)

exclamation_size = (50, 50)
exclamation_texture = cv2.resize(exclamation_texture, exclamation_size, interpolation=cv2.INTER_AREA)


def get_all_hand_points(results_hands, frame_shape):
    hand_points = []
    h, w, _ = frame_shape

    if not results_hands.multi_hand_landmarks:
        return hand_points

    for hand_landmarks in results_hands.multi_hand_landmarks:
        finger_tips = [4, 8, 12, 16, 20]
        for tip_idx in finger_tips:
            tip = hand_landmarks.landmark[tip_idx]
            hand_points.append((int(tip.x * w), int(tip.y * h)))

        wrist = hand_landmarks.landmark[0]
        middle_finger_mcp = hand_landmarks.landmark[9]
        palm_center_x = (wrist.x + middle_finger_mcp.x) / 2
        palm_center_y = (wrist.y + middle_finger_mcp.y) / 2
        hand_points.append((int(palm_center_x * w), int(palm_center_y * h)))

    return hand_points


def _draw_pause_banner(frame, text):
    h, w = frame.shape[:2]
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, h // 2 - 40), (w, h // 2 + 40), (30, 30, 30), -1)
    cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)
    put_text_ru(frame, text, 20, h // 2 - 18, font_size=26, color=(0, 220, 255))


class CameraThread(QThread):
    frame_signal = pyqtSignal(np.ndarray)
    finished = pyqtSignal()
    score_signal = pyqtSignal(int)

    def __init__(self, difficulty, seconds, background, sound="Ничего", user_id=0):
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

        self.sound_manager = SoundManager()
        if self.sound != "Ничего":
            self.sound_manager.load_sound(self.sound)

        self.calibrator = Calibrator(user_id)
        self.profile = None
        self.calibrated = False

    def run(self):
        difficulty = self.difficulty
        seconds = self.seconds
        pose = mp_pose.Pose()
        hands = mp_hands.Hands(min_detection_confidence=0.5, min_tracking_confidence=0.5)

        cap = open_camera()
        if not cap.isOpened():
            print("Камера не обнаружена.")
            return

        circle_position = None
        score = 0
        counter = difficulty
        timer = seconds
        rounds = 0
        start_time = None
        pause_message = None

        while cap.isOpened() and rounds < counter and not self.stop_flag:
            ret, frame = cap.read()
            if not ret:
                print("Не удалось получить кадр.")
                break

            frame = maybe_mirror(frame)
            h, w, _ = frame.shape
            image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            results_pose = pose.process(image_rgb)
            results_hands = hands.process(image_rgb)
            landmarks = results_pose.pose_landmarks
            overlay_pose(frame, landmarks)

            if not self.calibrated:
                calib = self.calibrator.tick(frame, landmarks)
                self.frame_signal.emit(calib.frame)
                if calib.done and calib.profile:
                    self.profile = calib.profile
                    self.profile.frame_w = w
                    self.profile.frame_h = h
                    self.calibrated = True
                    reset_runtime_guard()
                    print_profile_summary(self.profile)
                    if self.sound != "Ничего":
                        self.sound_manager.play_loop()
                continue

            pause_msg = filter_pause(check_runtime(
                self.profile,
                landmarks,
                w,
                h,
            ))
            if pause_msg:
                pause_message = pause_msg
                out = frame.copy()
                _draw_pause_banner(out, pause_message)
                cv2.putText(out, f'Score: {score}', (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                self.frame_signal.emit(out)
                continue
            pause_message = None

            if self.background == 'Дождь' and rain_frames:
                rain_overlay = rain_frames[self.rain_current_frame]
                self.rain_current_frame = (self.rain_current_frame + 1) % rain_frame_count
                rain_overlay = cv2.resize(rain_overlay, (w, h))
                frame = cv2.addWeighted(frame, 0.5, rain_overlay, 0.5, 0)
            elif self.background == 'Туман' and fog_frames:
                fog_overlay = fog_frames[self.fog_current_frame]
                self.fog_current_frame = (self.fog_current_frame + 1) % fog_frame_count
                fog_overlay = cv2.resize(fog_overlay, (w, h))
                frame = cv2.addWeighted(frame, 0.5, fog_overlay, 0.5, 0)
            elif self.background == 'Снег' and snow_frames:
                snow_overlay = snow_frames[self.snow_current_frame]
                self.snow_current_frame = (self.snow_current_frame + 1) % snow_frame_count
                snow_overlay = cv2.resize(snow_overlay, (w, h))
                frame = cv2.addWeighted(frame, 0.5, snow_overlay, 0.5, 0)

            head_straight = head_ok(self.profile, landmarks, w, h, "neutral")

            if landmarks:
                shift = torso_shift(self.profile, landmarks, w, h)
                hand_pos = user_hand_px(landmarks, w, h, "right")

                frame = draw_spawn_zone(frame, self.profile, shift, hand="right")

                if circle_position is None:
                    circle_position = spawn_object(self.profile, shift, hand="right")
                    start_time = time.time()

                if start_time is not None and time.time() - start_time < timer:
                    caught = False

                    if head_straight and catch_ok(self.profile, hand_pos, circle_position):
                        caught = True

                    if not caught and head_straight and results_hands.multi_hand_landmarks:
                        for hp in get_all_hand_points(results_hands, frame.shape):
                            if catch_ok(self.profile, hp, circle_position):
                                caught = True
                                break

                    if caught:
                        score += 1
                        self.score = score
                        self.score_signal.emit(score)
                        circle_position = None
                        rounds += 1
                        start_time = None
                    else:
                        apple_height, apple_width = apple_texture.shape[:2]
                        top_left_x = circle_position[0] - apple_width // 2
                        top_left_y = circle_position[1] - apple_height // 2
                        if (
                            top_left_x >= 0 and top_left_y >= 0
                            and top_left_x + apple_width <= w
                            and top_left_y + apple_height <= h
                        ):
                            alpha_channel = apple_texture[:, :, 3] / 255.0
                            apple_texture_bgr = apple_texture[:, :, :3]
                            for c in range(3):
                                frame[
                                    top_left_y:top_left_y + apple_height,
                                    top_left_x:top_left_x + apple_width,
                                    c,
                                ] = (
                                    alpha_channel * apple_texture_bgr[:, :, c]
                                    + (1 - alpha_channel)
                                    * frame[
                                        top_left_y:top_left_y + apple_height,
                                        top_left_x:top_left_x + apple_width,
                                        c,
                                    ]
                                )
                else:
                    circle_position = None
                    rounds += 1
                    start_time = None

                if not head_straight:
                    exclamation_x = (w - exclamation_size[0]) // 2
                    exclamation_y = 10
                    alpha_channel = exclamation_texture[:, :, 3] / 255.0
                    exclamation_texture_bgr = exclamation_texture[:, :, :3]
                    for c in range(3):
                        frame[
                            exclamation_y:exclamation_y + exclamation_size[1],
                            exclamation_x:exclamation_x + exclamation_size[0],
                            c,
                        ] = (
                            alpha_channel * exclamation_texture_bgr[:, :, c]
                            + (1 - alpha_channel)
                            * frame[
                                exclamation_y:exclamation_y + exclamation_size[1],
                                exclamation_x:exclamation_x + exclamation_size[0],
                                c,
                            ]
                        )

            cv2.putText(frame, f'Score: {score}', (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            self.frame_signal.emit(frame)

        self.sound_manager.stop()
        cap.release()
        pose.close()
        hands.close()
        self.score = score
        self.finished.emit()

    def stop(self):
        self.stop_flag = True
