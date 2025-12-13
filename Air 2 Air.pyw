import sys
import os
import random
import math
from PyQt5.QtWidgets import QApplication, QLabel, QWidget
from PyQt5.QtCore import Qt, QTimer, QPoint
from PyQt5.QtGui import QPixmap, QImage, QPainter, QTransform, QColor, QPen, QPainterPath
from time import sleep

class PlaneAnimation(QWidget):
    def __init__(self):
        super().__init__()
        print("Initializing window...")

        # Window settings
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        
        # Set screen size
        screen = QApplication.primaryScreen().geometry()
        self.screen_width = screen.width()
        self.screen_height = screen.height()
        self.resize(self.screen_width, self.screen_height)
        self.setGeometry(0, 0, self.screen_width, self.screen_height)
        print(f"Window size: {self.screen_width}x{self.screen_height}")
        
        # Load plane image
        try:
            fighterChoice = random.choice(["F-22", "F-35"])
            script_dir = os.path.dirname(os.path.abspath(__file__))
            image_path = os.path.join(script_dir, "{}.png".format(fighterChoice))
            
            padding = 20
            self.plane_pixmap = None
            if image_path and os.path.exists(image_path):
                print("Looking for image at:", image_path)
                print("File readable:", os.access(image_path, os.R_OK))
                print("File size:", os.path.getsize(image_path) if os.path.exists(image_path) else "N/A")
                pixmap = QPixmap(image_path)
                if pixmap.isNull():
                    print("Error: plane.png failed to load!")
                    self.plane_pixmap = self.create_fallback_image(Qt.red)
                else:
                    print("Image loaded successfully")
                    padded = QPixmap(pixmap.width() + 2 * padding, pixmap.height() + 2 * padding)
                    padded.fill(Qt.transparent)
                    painter = QPainter(padded)
                    painter.drawPixmap(padding, padding, pixmap)
                    painter.end()
                    self.plane_pixmap = padded
            else:
                print("File not found, using fallback image")
                self.plane_pixmap = self.create_fallback_image(Qt.red)
            
            self.plane_size = self.plane_pixmap.size()
        except Exception as e:
            print(f"Error loading image: {e}")
            self.plane_pixmap = self.create_fallback_image(Qt.red)
            self.plane_size = self.plane_pixmap.size()

        # Initialize planes
        self.planes = [
            {
                'label': QLabel(self),
                'pixmap': self.plane_pixmap if image_path else self.create_fallback_image(Qt.red),
                'pos_x': 0,
                'pos_y': self.screen_height // 3,
                'y_target': self.screen_height // 3,
                'speed': 5,
                'base_speed': 5,
                'change_y_counter': 0,
                'prev_pos_x': 0,
                'prev_pos_y': self.screen_height // 3,
                'health': 30,
                'direction': 1  # Right
            },
            {
                'label': QLabel(self),
                'pixmap': self.plane_pixmap if image_path else self.create_fallback_image(Qt.blue),
                'pos_x': self.screen_width - self.plane_size.width(),
                'pos_y': self.screen_height * 2 // 3,
                'y_target': self.screen_height * 2 // 3,
                'speed': -5,
                'base_speed': 5,
                'change_y_counter': 0,
                'prev_pos_x': self.screen_width - self.plane_size.width(),
                'prev_pos_y': self.screen_height * 2 // 3,
                'health': 30,
                'direction': -1  # Left
            }
        ]
        
        for plane in self.planes:
            plane['label'].setPixmap(plane['pixmap'])
            plane['label'].resize(self.plane_size)
            plane['label'].show()
        
        # Projectiles
        self.projectiles = []
        self.projectile_speed = 7
        self.shoot_interval = 6
        self.shoot_counter = 0
        self.projectile_base_size = 20

        # Smoke effect
        self.smoke_particles = []
        self.smoke_spawn_interval = 0.5  # Spawn every 10 frames
        self.smoke_spawn_counter = 0
        
        # Game state
        self.game_active = True
        self.winner = None
        self.winner_exit_counter = 0
        self.winner_exit_duration = 180
        
        # Timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_position)
        self.timer.start(16)
        print("Timer started")
        
        self.show()
        self.raise_()
        print("Window shown")

    def create_fallback_image(self, color):
        size = 70
        image = QImage(size, size, QImage.Format_ARGB32)
        image.fill(Qt.transparent)
        painter = QPainter(image)
        painter.setBrush(color)
        painter.setPen(Qt.black)
        center = size // 2
        points = [QPoint(center + 20, center), QPoint(center - 20, center - 15), QPoint(center - 20, center + 15)]
        painter.drawPolygon(points)
        painter.end()
        return QPixmap.fromImage(image)

    def create_projectile_image(self, size):
        image = QImage(size, size, QImage.Format_ARGB32)
        image.fill(Qt.transparent)
        painter = QPainter(image)
        try:
            painter.setBrush(QColor(255, 215, 0))  # Gold
            painter.setPen(QPen(Qt.black, 2))  # Thicker outline
            # Draw a bullet-like rounded rectangle
            bullet_width = size // 2  # Narrower width (e.g., 10 for size=20)
            bullet_height = size // 4  # Shorter height (e.g., 5 for size=20)
            painter.drawRoundedRect((size - bullet_width) // 2, (size - bullet_height) // 2,
                                    bullet_width, bullet_height, 2, 2)
        finally:
            painter.end()
        return QPixmap.fromImage(image)

    def create_smoke_particle_image(self, size, opacity):
        image = QImage(size, size, QImage.Format_ARGB32)
        image.fill(Qt.transparent)
        painter = QPainter(image)
        try:
            # Semi-transparent gray with soft edges
            painter.setBrush(QColor(100, 100, 100, int(opacity * 255)))
            painter.setPen(Qt.NoPen)
            path = QPainterPath()
            path.addEllipse(0, 0, size - 1, size - 1)
            painter.drawPath(path)
        finally:
            painter.end()
        return QPixmap.fromImage(image)

    def update_position(self):
        try:
            if self.game_active:
                # In update_position, replace the shooting block (lines ~166-190) with:
                self.shoot_counter += 1
                if self.shoot_counter >= self.shoot_interval:
                    self.shoot_counter = 0
                    for i, plane in enumerate(self.planes):
                        if plane['health'] <= 0:
                            continue
                        try:
                            target = self.planes[1 - i]
                            if target['health'] > 0:
                                # Calculate vector to target
                                dx = target['pos_x'] - plane['pos_x']
                                dy = target['pos_y'] - plane['pos_y']
                                # Angle to target in degrees
                                target_angle = math.degrees(math.atan2(dy, dx))
                                # Plane's forward direction (0° for right, 180° for left)
                                forward_angle = 0 if plane['direction'] == 1 else 180
                                # Check if target is within ±10° of forward direction
                                angle_diff = abs((target_angle - forward_angle + 180) % 360 - 180)
                                if angle_diff > 10:
                                    continue
                                
                                dist = math.sqrt(dx**2 + dy**2)
                                if dist > 1:
                                    dx, dy = dx / dist, dy / dist
                                    # Spawn projectile at plane's front
                                    spawn_x = plane['pos_x'] + self.plane_size.width() // 2 + (self.plane_size.width() // 2 * plane['direction'])
                                    spawn_y = plane['pos_y'] + self.plane_size.height() // 2
                                    projectile = {
                                        'label': QLabel(self),
                                        'base_pixmap': self.create_projectile_image(self.projectile_base_size),
                                        'pos_x': spawn_x,
                                        'pos_y': spawn_y,
                                        'vx': dx * self.projectile_speed,
                                        'vy': dy * self.projectile_speed,
                                        'frame': 0,
                                        'spawn_x': spawn_x,
                                        'spawn_y': spawn_y,
                                        'shooter_index': i,
                                        'angle': math.degrees(math.atan2(dy, dx))  # Bullet orientation
                                    }
                                    projectile['label'].setPixmap(projectile['base_pixmap'])
                                    projectile['label'].resize(projectile['base_pixmap'].size())
                                    projectile['label'].show()
                                    self.projectiles.append(projectile)
                                    print(f"Plane {i} fired projectile at ({projectile['pos_x']:.1f}, {projectile['pos_y']:.1f}), vx={projectile['vx']:.2f}, vy={projectile['vy']:.2f}, angle_diff={angle_diff:.1f}")
                        except Exception as e:
                            print(f"Error firing projectile: {e}")
                
                # Update planes
                for plane in self.planes:
                    if plane['health'] <= 0:
                        plane['label'].hide()
                        continue
                    
                    plane['prev_pos_x'] = plane['pos_x']
                    plane['prev_pos_y'] = plane['pos_y']
                    
                    plane['pos_x'] += plane['speed']
                    if plane['pos_x'] > self.screen_width:
                        plane['pos_x'] = -self.plane_size.width()
                        plane['pos_y'] = random.randint(self.screen_height // 4, self.screen_height * 3 // 4)
                        plane['y_target'] = plane['pos_y']
                        plane['speed'] = plane['base_speed'] * plane['direction'] #+ random.uniform(-2, 2)
                    elif plane['pos_x'] < -self.plane_size.width():
                        plane['pos_x'] = self.screen_width
                        plane['pos_y'] = random.randint(self.screen_height // 4, self.screen_height * 3 // 4)
                        plane['y_target'] = plane['pos_y']
                        plane['speed'] = plane['base_speed'] * plane['direction'] + random.uniform(-1, 3)
                    
                    plane['change_y_counter'] += 1
                    if plane['change_y_counter'] >= 120:
                        plane['y_target'] = random.randint(self.screen_height // 4, self.screen_height * 3 // 4)
                        plane['speed'] = plane['base_speed'] * plane['direction'] + random.uniform(-1, 3)
                        plane['change_y_counter'] = 0
                    
                    plane['pos_y'] += (plane['y_target'] - plane['pos_y']) * 0.02
                    
                    dx = plane['pos_x'] - plane['prev_pos_x']
                    dy = plane['pos_y'] - plane['prev_pos_y']
                    angle = math.degrees(math.atan2(dy, dx)) if dx != 0 or dy != 0 else 0
                    
                    transform = QTransform()
                    transform.translate(self.plane_size.width() / 2, self.plane_size.height() / 2)
                    transform.rotate(angle)
                    transform.translate(-self.plane_size.width() / 2, -self.plane_size.height() / 2)
                    rotated_pixmap = plane['pixmap'].transformed(transform, Qt.SmoothTransformation)
                    
                    plane['label'].setPixmap(rotated_pixmap)
                    screen_x = int(plane['pos_x'])
                    screen_y = int(plane['pos_y'])
                    screen_x = max(-self.plane_size.width(), min(screen_x, self.screen_width))
                    screen_y = max(-self.plane_size.height(), min(screen_y, self.screen_height - self.plane_size.height()))
                    plane['label'].move(QPoint(screen_x, screen_y))
                
                # Update smoke spawn counter
                self.smoke_spawn_counter += 1
                if self.smoke_spawn_counter >= self.smoke_spawn_interval:
                    self.smoke_spawn_counter = 0
                    for i, plane in enumerate(self.planes):
                        if plane['health'] <= 0:
                            continue
                        try:
                            # Determine smoke intensity based on health
                            if plane['health'] == 30:
                                num_particles, particle_size = 0, 0  # No smoke
                            elif plane['health'] < 27 and plane['health'] >= 17:
                                num_particles, particle_size = 1, 6  # Light smoke
                            elif plane['health'] < 17 and plane['health'] >= 10:
                                num_particles, particle_size = 2, 12  # Medium smoke
                            elif plane['health'] < 9:  # health == 0 (just before hiding)
                                num_particles, particle_size = 3, 18  # Heavy smoke
                            
                            for _ in range(num_particles):
                                # Spawn at plane's rear (opposite direction)
                                spawn_x = plane['pos_x'] + self.plane_size.width() // 2 - (self.plane_size.width() // 5 * plane['direction'])
                                spawn_y = plane['pos_y'] + self.plane_size.height() // 2
                                particle = {
                                    'label': QLabel(self),
                                    'pos_x': spawn_x,
                                    'pos_y': spawn_y,
                                    'vx': 0.1 * plane['direction'],  # Drift opposite plane direction
                                    'vy': 0,  # Slight upward drift
                                    'size': particle_size,
                                    'opacity': 0.8,  # Start semi-transparent
                                    'lifetime': 60,  # ~1 second at 60 FPS
                                    'frame': 0
                                }
                                particle['base_pixmap'] = self.create_smoke_particle_image(particle_size, particle['opacity'])
                                particle['label'].setPixmap(particle['base_pixmap'])
                                particle['label'].resize(particle['base_pixmap'].size())
                                particle['label'].show()
                                self.smoke_particles.append(particle)
                                print(f"Plane {i} spawned smoke at ({spawn_x:.1f}, {spawn_y:.1f}), size={particle_size}, health={plane['health']}")
                        except Exception as e:
                            print(f"Error spawning smoke particle: {e}")
  
                # Update projectiles
                projectiles_to_remove = []
                for projectile in self.projectiles:
                    try:
                        projectile['pos_x'] += projectile['vx']
                        projectile['pos_y'] += projectile['vy']
                        
                        # Pulse size between 15 and 25 pixels
                        projectile['frame'] += 1
                        scale = 15 + 10 #* (0.5 + 0.5 * math.sin(projectile['frame'] / 10))
                        # Rotate bullet to match initial angle
                        transform = QTransform()
                        transform.translate(self.projectile_base_size * 1.5 / 2, self.projectile_base_size * 1.5 / 2)  # Center of padded pixmap
                        transform.rotate(projectile['angle'])  # Stored angle in degrees
                        transform.translate(-self.projectile_base_size * 1.5 / 2, -self.projectile_base_size * 1.5 / 2)
                        rotated_pixmap = projectile['base_pixmap'].transformed(transform, Qt.SmoothTransformation)
                        # Scale the rotated pixmap
                        scaled_pixmap = rotated_pixmap.scaled(int(scale), int(scale), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                        
                        projectile['label'].setPixmap(scaled_pixmap)
                        projectile['label'].resize(scaled_pixmap.size())
                        projectile['label'].move(QPoint(int(projectile['pos_x'] - scale / 2), int(projectile['pos_y'] - scale / 2)))
                        
                        # Check if bullet traveled enough for collision
                        travel_dist = math.sqrt((projectile['pos_x'] - projectile['spawn_x'])**2 + (projectile['pos_y'] - projectile['spawn_y'])**2)
                        if travel_dist > 50:
                            for j, plane in enumerate(self.planes):
                                if plane['health'] <= 0 or j == projectile['shooter_index']:
                                    continue
                                plane_rect = plane['label'].geometry()
                                proj_rect = projectile['label'].geometry()
                                if plane_rect.intersects(proj_rect):
                                    plane['health'] -= 1
                                    print(f"Hit! Plane {j} health: {plane['health']}, bullet at ({projectile['pos_x']:.1f}, {projectile['pos_y']:.1f}), travel: {travel_dist:.1f}")
                                    projectiles_to_remove.append(projectile)
                                    break
                        
                        if (projectile['pos_x'] < -10 or projectile['pos_x'] > self.screen_width or
                            projectile['pos_y'] < -10 or projectile['pos_y'] > self.screen_height):
                            projectiles_to_remove.append(projectile)
                        else:
                            pass
                            #print(f"Bullet at ({projectile['pos_x']:.1f}, {projectile['pos_y']:.1f}), travel: {travel_dist:.1f}, angle: {projectile['angle']:.1f}")
                    except Exception as e:
                        print(f"Error updating projectile: {e}")
                        projectiles_to_remove.append(projectile)
                        
                        if (projectile['pos_x'] < -10 or projectile['pos_x'] > self.screen_width or
                            projectile['pos_y'] < -10 or projectile['pos_y'] > self.screen_height):
                            projectiles_to_remove.append(projectile)
                        else:
                            print(f"Bullet at ({projectile['pos_x']:.1f}, {projectile['pos_y']:.1f}), travel: {travel_dist:.1f}")
                    except Exception as e:
                        print(f"Error updating projectile: {e}")
                        projectiles_to_remove.append(projectile)
                
                # Remove projectiles
                for projectile in projectiles_to_remove:
                    if projectile in self.projectiles:
                        projectile['label'].hide()
                        self.projectiles.remove(projectile)
                
                # Update smoke particles
                smoke_to_remove = []
                for particle in self.smoke_particles:
                    try:
                        particle['frame'] += 1
                        particle['pos_x'] += particle['vx']
                        particle['pos_y'] += particle['vy']
                        # Fade out
                        particle['opacity'] -= 0.8 / particle['lifetime']
                        if particle['opacity'] <= 0 or particle['frame'] >= particle['lifetime']:
                            smoke_to_remove.append(particle)
                            continue
                        # Update pixmap with new opacity
                        particle['base_pixmap'] = self.create_smoke_particle_image(particle['size'], particle['opacity'])
                        particle['label'].setPixmap(particle['base_pixmap'])
                        particle['label'].resize(particle['base_pixmap'].size())
                        particle['label'].move(QPoint(int(particle['pos_x'] - particle['size'] / 2), int(particle['pos_y'] - particle['size'] / 2)))
                    except Exception as e:
                        print(f"Error updating smoke particle: {e}")
                        smoke_to_remove.append(particle)

                # Remove expired smoke particles
                for particle in smoke_to_remove:
                    if particle in self.smoke_particles:
                        particle['label'].hide()
                        self.smoke_particles.remove(particle)

                # Check for winner
                alive_planes = [p for p in self.planes if p['health'] > 0]
                if len(alive_planes) <= 1:
                    self.game_active = False
                    self.winner = alive_planes[0] if alive_planes else None
                    print(f"Game over. Winner: {'Plane 0' if self.winner == self.planes[0] else 'Plane 1' if self.winner else 'None' and exit(0)}")

            else:
                # Winner phase
                if self.winner:
                    self.winner_exit_counter += 1
                    if self.winner_exit_counter < self.winner_exit_duration:
                        self.winner['pos_x'] += self.winner['base_speed']
                    else:
                        self.winner['pos_x'] += self.winner['base_speed'] * 2
                    if self.winner['pos_x'] > self.screen_width:
                        self.winner['label'].hide()
                        self.timer.stop()
                        print("Winner exited")
                        exit(0)
                        return
                
                    dx = self.winner['pos_x'] - self.winner['prev_pos_x']
                    dy = 0
                    angle = math.degrees(math.atan2(dy, dx)) if dx != 0 else 0
                    transform = QTransform()
                    transform.translate(self.plane_size.width() / 2, self.plane_size.height() / 2)
                    transform.rotate(angle)
                    transform.translate(-self.plane_size.width() / 2, -self.plane_size.height() / 2)
                    rotated_pixmap = self.winner['pixmap'].transformed(transform, Qt.SmoothTransformation)
                    self.winner['label'].setPixmap(rotated_pixmap)
                    screen_x = int(self.winner['pos_x'])
                    screen_y = int(self.winner['pos_y'])
                    self.winner['label'].move(QPoint(screen_x, screen_y))
        
            self.update()
        except Exception as e:
            print(f"Error in update_position: {e}")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = PlaneAnimation()
    sys.exit(app.exec_())