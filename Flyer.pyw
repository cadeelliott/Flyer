import sys
import os
import random
import math
from PyQt5.QtWidgets import QApplication, QLabel, QWidget
from PyQt5.QtCore import Qt, QTimer, QPoint
from PyQt5.QtGui import QPixmap, QImage, QPainter, QTransform

class PlaneAnimation(QWidget):
    def __init__(self):
        super().__init__()
        print("Initializing window...")

        # Window settings
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        
        # Plane label
        self.plane = QLabel(self)
        fighterChoice = random.choice(["F-22", "F-35"])
        script_dir = os.path.dirname(os.path.abspath(__file__))
        image_path = os.path.join(script_dir, "{}.png".format(fighterChoice))
        
        # Load image with padding
        self.original_pixmap = None
        padding = 20  # Extra pixels around image
        if image_path and os.path.exists(image_path):
            print("Looking for image at:", image_path)
            pixmap = QPixmap(image_path)
            if pixmap.isNull():
                print("Error: plane.png failed to load!")
                self.original_pixmap = self.create_fallback_image()
            else:
                print("plane.png loaded successfully")
                # Add padding
                padded = QPixmap(pixmap.width() + 2 * padding, pixmap.height() + 2 * padding)
                padded.fill(Qt.transparent)
                painter = QPainter(padded)
                painter.drawPixmap(padding, padding, pixmap)
                painter.end()
                self.original_pixmap = padded
        else:
            print("File not found, using fallback image")
            self.original_pixmap = self.create_fallback_image()
        
        self.plane.setPixmap(self.original_pixmap)
        self.plane_size = self.original_pixmap.size()
        self.plane.resize(self.plane_size)
        
        # Window size
        screen = QApplication.primaryScreen().geometry()
        self.screen_width = screen.width()
        self.screen_height = screen.height()
        self.resize(self.screen_width, self.screen_height)
        self.setGeometry(0, 0, self.screen_width, self.screen_height)
        print(f"Window size: {self.screen_width}x{self.screen_height}")
        
        # Animation variables
        self.pos_x = 0
        self.pos_y = self.screen_height // 2
        self.base_speed = 5
        self.speed = self.base_speed
        self.y_target = self.pos_y
        self.change_y_counter = 0
        self.prev_pos_x = self.pos_x
        self.prev_pos_y = self.pos_y
        
        # Timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_position)
        self.timer.start(16)
        print("Timer started")
        
        self.show()
        self.raise_()
        print("Window shown")

    def update_position(self):
        # Store previous position ''

        self.prev_pos_x = self.pos_x
        self.prev_pos_y = self.pos_y
        
        # Update position
        self.pos_x += self.speed
        if self.pos_x > self.screen_width:
            exit(0)
            #self.pos_x = -self.plane_size.width()
            #self.pos_y = random.randint(self.screen_height // 4, self.screen_height * 3 // 4)
            #self.y_target = self.pos_y
            #self.speed = self.base_speed + random.uniform(-2, 2)
        
        # Randomize y-position
        self.change_y_counter += 1
        if self.change_y_counter >= 120:
            self.y_target = random.randint(self.screen_height // 3, self.screen_height * 3 // 3)
            self.speed = self.base_speed + random.uniform(-2, 2)
            self.change_y_counter = 0
        
        # Smooth y-movement
        self.pos_y += (self.y_target - self.pos_y) * 0.01
        
        # Calculate direction
        dx = self.pos_x - self.prev_pos_x
        dy = self.pos_y - self.prev_pos_y
        angle = math.degrees(math.atan2(dy, dx)) if dx != 0 or dy != 0 else 0
        
        # Rotate pixmap with center alignment
        transform = QTransform()
        transform.translate(self.plane_size.width() / 2, self.plane_size.height() / 2)
        transform.rotate(angle)
        transform.translate(-self.plane_size.width() / 2, -self.plane_size.height() / 2)
        rotated_pixmap = self.original_pixmap.transformed(transform, Qt.SmoothTransformation)
        
        # Update pixmap and position
        self.plane.setPixmap(rotated_pixmap)
        rect = rotated_pixmap.rect()
        screen_x = int(self.pos_x)
        screen_y = int(self.pos_y)
        
        # Keep plane on-screen
        screen_x = max(-self.plane_size.width(), min(screen_x, self.screen_width))
        screen_y = max(-self.plane_size.height(), min(screen_y, self.screen_height - self.plane_size.height()))
        
        self.plane.move(QPoint(screen_x, screen_y))
        # print(f"Position: ({screen_x:.1f}, {screen_y:.1f}), Angle: {angle:.1f}, Pixmap: {rect.width()}x{rect.height()}")  # Uncomment for debug
        self.update()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = PlaneAnimation()
    sys.exit(app.exec_())