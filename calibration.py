import cv2
import mediapipe as mp
from PyQt5.QtCore import QObject, pyqtSignal

from workspace import WorkspaceProfile

mp_pose = mp.solutions.pose

class Calibration(QObject):
    calibration_done = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self.calibrated = False
        self.calibration_stage = 0  # 0: боковые, 1: верх/низ, 2: углы
        self.circle_radius = 28  # Радиус кругов
        self.circles = []  # Все круги для калибровки
        self.stage_completed = [False, False, False]  # Статус завершения каждой стадии
        self.touch_points = []

    def reset(self):
        """Сброс состояния для новой сессии калибровки."""
        self.calibrated = False
        self.calibration_stage = 0
        self.circles = []
        self.stage_completed = [False, False, False]
        self.touch_points = []

    def init_circles(self, frame_width, frame_height):
        """Инициализация всех кругов для калибровки (только правой рукой)"""
        self.circles = []
        
        # Стадия 0: Боковые круги (крайние левый и правый) - правой рукой!
        self.circles.append({
            'center': (50, frame_height // 2),  # Крайний левый - дотянуться правой рукой!
            'name': 'far_left',
            'stage': 0,
            'color': (0, 165, 255),  # Оранжевый
            'completed': False,
            'hand': 'right'  # Требуется правая рука
        })
        
        self.circles.append({
            'center': (frame_width - 50, frame_height // 2),  # Крайний правый - легкая точка
            'name': 'far_right',
            'stage': 0,
            'color': (0, 165, 255),
            'completed': False,
            'hand': 'right'  # Требуется правая рука
        })
        
        # Стадия 1: Верхний и нижний круги (центр)
        self.circles.append({
            'center': (frame_width // 2, 50),  # Верхний центр
            'name': 'top_center',
            'stage': 1,
            'color': (255, 165, 0),  # Голубой
            'completed': False,
            'hand': 'right'  # Требуется правая рука
        })
        
        self.circles.append({
            'center': (frame_width // 2, frame_height - 50),  # Нижний центр
            'name': 'bottom_center',
            'stage': 1,
            'color': (255, 165, 0),
            'completed': False,
            'hand': 'right'  # Требуется правая рука
        })
        
        # Стадия 2: Угловые круги
        self.circles.append({
            'center': (70, 70),  # Левый верхний угол - самая сложная точка!
            'name': 'top_left',
            'stage': 2,
            'color': (150, 205, 50),  # Зеленый
            'completed': False,
            'hand': 'right'  # Требуется правая рука
        })
        
        self.circles.append({
            'center': (frame_width - 70, 70),  # Правый верхний угол
            'name': 'top_right',
            'stage': 2,
            'color': (150, 205, 50),
            'completed': False,
            'hand': 'right'  # Требуется правая рука
        })
        
        self.circles.append({
            'center': (70, frame_height - 70),  # Левый нижний угол
            'name': 'bottom_left',
            'stage': 2,
            'color': (150, 205, 50),
            'completed': False,
            'hand': 'right'  # Требуется правая рука
        })
        
        self.circles.append({
            'center': (frame_width - 70, frame_height - 70),  # Правый нижний угол
            'name': 'bottom_right',
            'stage': 2,
            'color': (150, 205, 50),
            'completed': False,
            'hand': 'right'  # Требуется правая рука
        })

    def get_right_hand_position(self, results, frame_width, frame_height):
        """Получение позиции только правой руки пользователя"""
        if not results.pose_landmarks:
            return None
            
        try:
            # В зеркальном отображении:
            # Левая рука Mediapipe = правая рука пользователя
            # Правая рука Mediapipe = левая рука пользователя
            
            # Нам нужна правая рука пользователя = левая рука Mediapipe
            left_wrist = results.pose_landmarks.landmark[mp_pose.PoseLandmark.LEFT_WRIST]
            left_index = results.pose_landmarks.landmark[mp_pose.PoseLandmark.LEFT_INDEX]
            
            # Проверяем видимость правой руки (левой в Mediapipe)
            if left_wrist.visibility > 0.5:
                # Правая рука пользователя (от левой Mediapipe)
                right_hand_pos = (
                    int((left_wrist.x + left_index.x) / 2 * frame_width),
                    int((left_wrist.y + left_index.y) / 2 * frame_height)
                )
                return right_hand_pos
            else:
                return None
                
        except (AttributeError, IndexError):
            return None

    def run(self, frame, results):
        h, w, _ = frame.shape
        
        # Инициализация кругов при первом запуске
        if not self.circles:
            self.init_circles(w, h)
            
        # Получаем позицию только правой руки
        right_hand_pos = self.get_right_hand_position(results, w, h)
        
        # Получаем круги текущей стадии
        current_stage_circles = [circle for circle in self.circles if circle['stage'] == self.calibration_stage]
        
        # Рисуем все круги
        for circle in self.circles:
            center = circle['center']
            name = circle['name']
            color = circle['color']
            stage = circle['stage']
            completed = circle['completed']
            required_hand = circle.get('hand', 'right')  # По умолчанию правая рука
            
            # Если круг из пройденной стадии - рисуем зеленым и прозрачным
            if stage < self.calibration_stage:
                # Прозрачный зеленый для пройденных кругов
                overlay = frame.copy()
                cv2.circle(overlay, center, self.circle_radius, (0, 255, 0), -1)
                cv2.addWeighted(overlay, 0.3, frame, 0.7, 0, frame)
                cv2.circle(frame, center, self.circle_radius, (0, 255, 0), 2)
                cv2.putText(frame, "+", (center[0] - 8, center[1] + 8), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            # Активные круги текущей стадии
            elif circle in current_stage_circles:
                # Если круг уже пройден
                if completed:
                    cv2.circle(frame, center, self.circle_radius, (0, 255, 0), 3)
                    cv2.putText(frame, "+", (center[0] - 8, center[1] + 8), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                else:
                    # Активный непройденный круг
                    circle_thickness = 3
                    
                    # Если правая рука близко к кругу, делаем его ярче
                    if right_hand_pos:
                        distance_sq = (right_hand_pos[0] - center[0])**2 + (right_hand_pos[1] - center[1])**2
                        if distance_sq <= (self.circle_radius * 2)**2:  # В 2 радиусах
                            circle_thickness = 5
                            # Подсвечиваем круг при приближении
                            overlay = frame.copy()
                            cv2.circle(overlay, center, self.circle_radius + 2, color, -1)
                            cv2.addWeighted(overlay, 0.2, frame, 0.8, 0, frame)
                    
                    cv2.circle(frame, center, self.circle_radius, color, circle_thickness)
                    
                    # Проверяем касание правой рукой
                    if right_hand_pos:
                        hand_in_circle = ((right_hand_pos[0] - center[0])**2 + 
                                         (right_hand_pos[1] - center[1])**2 <= self.circle_radius**2)
                        
                        if hand_in_circle:
                            circle['completed'] = True
                            circle['touched_hand_pos'] = right_hand_pos
                            self.touch_points.append(right_hand_pos)
                            print(f"Circle '{name}' completed with right hand at {right_hand_pos}")
            
            # Круги будущих стадий - рисуем очень прозрачными
            else:
                alpha = 0.1
                overlay = frame.copy()
                circle_color = tuple(int(c * alpha) for c in color)
                cv2.circle(overlay, center, self.circle_radius, circle_color, -1)
                cv2.addWeighted(overlay, 0.2, frame, 0.8, 0, frame)
        
        # Рисуем точку на правой руке
        if right_hand_pos:
            # Большая красная точка для правой руки
            cv2.circle(frame, right_hand_pos, 22, (0, 0, 255), -1)  # Красный - правая
            cv2.circle(frame, right_hand_pos, 24, (255, 255, 255), 2)
            
            # Маленькая буква R для ясности
            cv2.putText(frame, "R", (right_hand_pos[0] - 7, right_hand_pos[1] + 7), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # Проверяем завершение текущей стадии
        current_stage_completed = all(circle['completed'] for circle in current_stage_circles)
        
        if current_stage_completed and not self.stage_completed[self.calibration_stage]:
            self.stage_completed[self.calibration_stage] = True
            print(f"Stage {self.calibration_stage} completed!")
            
            # Переходим к следующей стадии, если есть
            if self.calibration_stage < 2:
                self.calibration_stage += 1
                print(f"Moving to stage {self.calibration_stage}")
        
        # Проверяем завершение всей калибровки
        all_stages_completed = all(self.stage_completed)
        
        if all_stages_completed and not self.calibrated:
            self.calibrated = True
            print("=" * 50)
            print("ALL CALIBRATION STAGES COMPLETED WITH RIGHT HAND!")
            print("=" * 50)
            
            touch_points = [
                c['touched_hand_pos']
                for c in self.circles
                if c.get('touched_hand_pos') is not None
            ]
            profile = WorkspaceProfile.from_touch_points(touch_points, w, h)

            self.calibration_done.emit({
                'calibrated': True,
                'circles': self.circles,
                'circle_radius': self.circle_radius,
                'hand': 'right',
                'touch_points': touch_points,
                'profile': profile,
                'bbox': (profile.x_min, profile.y_min, profile.x_max, profile.y_max),
            })
            
            # Рисуем сообщение о завершении
            cv2.putText(frame, "RIGHT HAND CALIBRATED!", (w//2 - 180, h//2),
                       cv2.FONT_HERSHEY_SIMPLEX, 1.3, (0, 255, 0), 3)
        
        # Прогресс-бар по центру внизу
        completed_circles = sum(1 for circle in self.circles if circle['completed'])
        total_circles = len(self.circles)
        
        # Простой прогресс-бар
        bar_width = 400
        bar_height = 20
        bar_x = (w - bar_width) // 2
        bar_y = h - 40
        progress = completed_circles / total_circles
        
        # Фон прогресс-бара (темно-серый)
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_width, bar_y + bar_height), 
                     (60, 60, 60), -1)
        
        # Заполнение прогресс-бара
        fill_width = int(bar_width * progress)
        if fill_width > 0:
            # Градиент от оранжевого к зеленому
            if progress < 0.5:
                # Первая половина - оранжевый
                bar_color = (0, 165, 255)
            elif progress < 1.0:
                # Вторая половина - голубой
                bar_color = (255, 165, 0)
            else:
                # Завершено - зеленый
                bar_color = (0, 255, 0)
            
            cv2.rectangle(frame, (bar_x, bar_y), (bar_x + fill_width, bar_y + bar_height), 
                         bar_color, -1)
        
        # Тонкая белая граница
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_width, bar_y + bar_height), 
                     (200, 200, 200), 1)
        
        return frame, self.calibrated