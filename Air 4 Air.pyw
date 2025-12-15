import sys
import os
import random
import math
from PyQt5.QtWidgets import QApplication, QLabel, QWidget
from PyQt5.QtCore import Qt, QTimer, QPoint
from PyQt5.QtGui import QPixmap, QImage, QPainter, QTransform, QColor, QPen, QPainterPath

class PlaneAnimation(QWidget):
    def __init__(self):
        super().__init__()
        print("--- Initializing PlaneAnimation ---")

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        
        screen = QApplication.primaryScreen().geometry()
        self.screen_width = screen.width()
        self.screen_height = screen.height()
        self.resize(self.screen_width, self.screen_height)
        self.setGeometry(0, 0, self.screen_width, self.screen_height)
        
        self.plane_pixmap = self.load_plane_pixmap()
        self.plane_size = self.plane_pixmap.size()
        self.projectile_pixmap = self.create_projectile_image()
        self.missile_pixmap = self.create_missile_image()

        self.planes, self.projectiles, self.missiles, self.smoke_particles, self.explosions, self.flares = [], [], [], [], [], []
        
        self.init_planes()
        
        self.missile_speed = 8
        self.missile_turn_rate = 0.05
        self.missile_base_size = 25

        self.game_active = True
        self.winner = None
        self.winner_exit_counter = 0
        self.winner_exit_duration = 180
        
        self.shoot_counter = 0
        self.fire_missile_counter = 0
        self.shoot_interval = 2
        self.fire_missile_interval = 180

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_position)
        self.timer.start(16)
        
        self.show()
        self.raise_()
        print("--- Initialization Complete. Window Shown. ---")

    def load_plane_pixmap(self):
        try:
            fighterChoice = random.choice(["F-22", "F-35"])
            script_dir = os.path.dirname(os.path.abspath(__file__))
            image_path = os.path.join(script_dir, f"{fighterChoice}.png")
            if os.path.exists(image_path):
                pixmap = QPixmap(image_path)
                if not pixmap.isNull():
                    padding = 20
                    padded = QPixmap(pixmap.width() + 2 * padding, pixmap.height() + 2 * padding)
                    padded.fill(Qt.transparent)
                    painter = QPainter(padded); painter.drawPixmap(padding, padding, pixmap); painter.end()
                    return padded
        except Exception as e: print(f"Error loading plane image: {e}")
        return self.create_fallback_image(Qt.red)

    def init_planes(self):
        self.planes = [
            {'label': QLabel(self), 'pixmap': self.plane_pixmap.copy(), 'pos_x': 0, 'pos_y': self.screen_height//3, 'y_target': self.screen_height//3, 'speed': 5, 'base_speed': 5, 'change_y_counter': 0, 'prev_pos_x': 0, 'prev_pos_y': self.screen_height//3, 'health': 30, 'direction': 1, 'vy': 0, 'angle': 0, 'flare_cooldown': 0, 'flares_left': 8, 'is_deploying_flares': False, 'flare_deployment_counter': 0, 'damage_points': []},
            {'label': QLabel(self), 'pixmap': self.plane_pixmap.copy(), 'pos_x': self.screen_width - self.plane_size.width(), 'pos_y': self.screen_height*2//3, 'y_target': self.screen_height*2//3, 'speed': -5, 'base_speed': 5, 'change_y_counter': 0, 'prev_pos_x': self.screen_width - self.plane_size.width(), 'prev_pos_y': self.screen_height*2//3, 'health': 30, 'direction': -1, 'vy': 0, 'angle': 0, 'flare_cooldown': 0, 'flares_left': 8, 'is_deploying_flares': False, 'flare_deployment_counter': 0, 'damage_points': []}
        ]
        for plane in self.planes:
            plane['label'].setPixmap(plane['pixmap']); plane['label'].resize(self.plane_size); plane['label'].show()

    def create_fallback_image(self, color):
        size = 70; image = QImage(size, size, QImage.Format_ARGB32); image.fill(Qt.transparent)
        painter = QPainter(image); painter.setBrush(color); painter.setPen(Qt.black)
        center = size//2; points = [QPoint(center + 20, center), QPoint(center - 20, center - 15), QPoint(center - 20, center + 15)]
        painter.drawPolygon(points); painter.end()
        return QPixmap.fromImage(image)

    def create_projectile_image(self):
        size = 20; image = QImage(size, size, QImage.Format_ARGB32); image.fill(Qt.transparent)
        painter = QPainter(image); painter.setBrush(QColor(255, 215, 0)); painter.setPen(QPen(Qt.black, 2))
        painter.drawRoundedRect((size - 10)//2, (size - 5)//2, 10, 5, 2, 2); painter.end()
        return QPixmap.fromImage(image)

    def create_missile_image(self):
        size = 25; image = QImage(size, size, QImage.Format_ARGB32); image.fill(Qt.transparent)
        painter = QPainter(image)
        body_width, body_height = size*0.2, size*0.8; body_x, body_y = (size - body_width)/2, (size - body_height)/2
        painter.setBrush(QColor(200, 200, 200)); painter.setPen(QPen(Qt.black, 1))
        painter.drawRect(int(body_x), int(body_y), int(body_width), int(body_height))
        nose_path = QPainterPath(); nose_path.moveTo(body_x, body_y); nose_path.lineTo(body_x + body_width, body_y); nose_path.lineTo(body_x + body_width/2, body_y - size*0.2); nose_path.closeSubpath()
        painter.setBrush(QColor(255, 0, 0)); painter.drawPath(nose_path)
        fin_width, fin_height = size*0.2, size*0.25; fin_y = body_y + body_height - fin_height
        painter.drawRect(int(body_x - fin_width), int(fin_y), int(fin_width), int(fin_height)); painter.drawRect(int(body_x + body_width), int(fin_y), int(fin_width), int(fin_height))
        painter.end()
        return QPixmap.fromImage(image)

    def create_particle_pixmap(self, size, opacity, color, is_flare_smoke=False):
        image = QImage(int(size), int(size), QImage.Format_ARGB32); image.fill(Qt.transparent)
        painter = QPainter(image)
        final_color = QColor(color); final_color.setAlpha(int(opacity * (150 if is_flare_smoke else 255)))
        painter.setBrush(final_color); painter.setPen(Qt.NoPen)
        painter.drawEllipse(0, 0, int(size) - 1, int(size) - 1); painter.end()
        return QPixmap.fromImage(image)

    def create_plane_explosion(self, plane):
        for _ in range(15):
            color = random.choice([QColor(255, 165, 0), QColor(255, 69, 0), QColor(255, 140, 0)])
            self.explosions.append({'label': QLabel(self), 'pos_x': plane['pos_x'] + self.plane_size.width()/2 + random.uniform(-30, 30), 'pos_y': plane['pos_y'] + self.plane_size.height()/2 + random.uniform(-30, 30), 'size': 20, 'max_size': random.uniform(100, 160), 'opacity': 1.0, 'frame': 0, 'lifetime': random.uniform(40, 70), 'color': color})
            self.explosions[-1]['label'].setPixmap(self.create_particle_pixmap(20, 1.0, color)); self.explosions[-1]['label'].resize(self.explosions[-1]['label'].pixmap().size()); self.explosions[-1]['label'].show()

    def create_explosion(self, x, y):
        self.explosions.append({'label': QLabel(self), 'pos_x': x, 'pos_y': y, 'size': 20, 'max_size': 80, 'opacity': 1.0, 'frame': 0, 'lifetime': 25, 'color': QColor(255, 165, 0)})
        self.explosions[-1]['label'].setPixmap(self.create_particle_pixmap(20, 1.0, QColor(255, 165, 0))); self.explosions[-1]['label'].resize(self.explosions[-1]['label'].pixmap().size()); self.explosions[-1]['label'].show()

    def update_position(self):
        try:
            if self.game_active: self.update_active_game_logic()
            else: self.update_winner_phase()
            self.update_projectiles(); self.update_missiles(); self.update_effects()
            if self.game_active: self.check_game_over()
            for plane in self.planes:
                if plane['health'] > 0: plane['label'].raise_()
            self.update()
            if not self.game_active and not self.winner and not self.projectiles and not self.missiles and not self.smoke_particles and not self.explosions and not self.flares:
                self.close()
        except Exception as e: print(f"!!! FATAL ERROR in update_position: {e}"); self.timer.stop()

    def update_active_game_logic(self):
        self.handle_plane_actions(); self.update_planes()

    def update_winner_phase(self):
        if self.winner:
            self.winner_exit_counter += 1
            if self.winner_exit_counter > self.winner_exit_duration and self.winner['pos_x'] > self.screen_width: self.winner['label'].hide(); self.winner = None
            else:
                self.winner['pos_x'] += self.winner['base_speed'] * 2; self.winner['prev_pos_x'] = self.winner['pos_x'] - self.winner['base_speed'] * 2
                dx = self.winner['pos_x'] - self.winner['prev_pos_x']
                self.winner['angle'] = math.degrees(math.atan2(0, dx)) if dx != 0 else 0
                transform = QTransform().translate(self.plane_size.width()/2, self.plane_size.height()/2).rotate(self.winner['angle']).translate(-self.plane_size.width()/2, -self.plane_size.height()/2)
                
                damaged_pixmap = self.plane_pixmap.copy()
                if self.winner['damage_points']:
                    painter = QPainter(damaged_pixmap); painter.setCompositionMode(QPainter.CompositionMode_Clear)
                    painter.setBrush(Qt.transparent); painter.setPen(Qt.NoPen)
                    for point in self.winner['damage_points']: painter.drawEllipse(point, 3, 3)
                    painter.end()
                
                self.winner['label'].setPixmap(damaged_pixmap.transformed(transform, Qt.SmoothTransformation)); self.winner['label'].move(QPoint(int(self.winner['pos_x']), int(self.winner['pos_y'])))
                
                if self.winner['health'] < 9: num, size = 3, 12
                elif self.winner['health'] < 17: num, size = 2, 8
                elif self.winner['health'] < 27: num, size = 1, 5
                else: num = 0
                if num > 0:
                    center_x, center_y = self.plane_size.width()/2, self.plane_size.height()/2
                    angle_rad = math.radians(self.winner['angle'])
                    for i in range(num):
                        y_offset = (i - (num - 1)/2) * 10; relative_x = -30
                        rotated_relative_x = relative_x * math.cos(angle_rad) - y_offset * math.sin(angle_rad)
                        rotated_relative_y = relative_x * math.sin(angle_rad) + y_offset * math.cos(angle_rad)
                        spawn_x = center_x + self.winner['pos_x'] + rotated_relative_x; spawn_y = center_y + self.winner['pos_y'] + rotated_relative_y
                        smoke_vx = (self.winner['pos_x'] - self.winner['prev_pos_x']) * -0.2 + random.uniform(-0.2, 0.2)
                        smoke_vy = (self.winner['pos_y'] - self.winner['prev_pos_y']) * -0.2 + random.uniform(-0.2, 0.2)
                        smoke = {'label': QLabel(self), 'pos_x': spawn_x, 'pos_y': spawn_y, 'vx': smoke_vx, 'vy': smoke_vy, 'size': size, 'opacity': 0.8, 'lifetime': 60, 'frame': 0, 'type': 'smoke'}
                        smoke['label'].setPixmap(self.create_particle_pixmap(size, 0.8, QColor(100,100,100))); smoke['label'].resize(smoke['label'].pixmap().size()); smoke['label'].show(); self.smoke_particles.append(smoke)

    def check_game_over(self):
        if len([p for p in self.planes if p['health'] > 0]) <= 1:
            self.game_active = False
            self.winner = next((p for p in self.planes if p['health'] > 0), None)
            print(f"--- Game Over. Winner: {'Plane ' + str(self.planes.index(self.winner)) if self.winner else 'Mutual destruction.'} ---")

    def handle_plane_actions(self):
        self.shoot_counter += 1
        if self.shoot_counter >= self.shoot_interval: self.shoot_counter = 0; self.fire_projectiles()
        self.fire_missile_counter += 1
        if self.fire_missile_counter >= self.fire_missile_interval: self.fire_missile_counter = 0; self.fire_missiles()
        for plane in self.planes:
            if plane['flare_cooldown'] > 0: plane['flare_cooldown'] -= 1
            if plane['is_deploying_flares'] and plane['flare_deployment_counter'] > 0 and plane['flare_deployment_counter'] % 2 == 0:
                plane['flares_left'] -= 1
                flare = {'label': QLabel(self), 'pos_x': plane['pos_x'] + self.plane_size.width()/2, 'pos_y': plane['pos_y'] + self.plane_size.height()/2, 'vx': random.uniform(-2, 2) - plane['direction']*2, 'vy': random.uniform(-2, 2), 'size': 15, 'opacity': 1.0, 'lifetime': 90, 'frame': 0}
                flare['label'].setPixmap(self.create_particle_pixmap(flare['size'], flare['opacity'], QColor(255, 255, 0))); flare['label'].resize(flare['label'].pixmap().size()); flare['label'].show(); self.flares.append(flare)
            if plane['is_deploying_flares']: plane['flare_deployment_counter'] -= 1
            if plane['flare_deployment_counter'] <= 0: plane['is_deploying_flares'] = False

    def fire_projectiles(self):
        for i, plane in enumerate(self.planes):
            if plane['health'] <= 0: continue
            target = self.planes[1 - i]
            if target['health'] > 0:
                dx, dy = target['pos_x'] - plane['pos_x'], target['pos_y'] - plane['pos_y']
                target_angle = math.degrees(math.atan2(dy, dx))
                angle_diff = abs((target_angle - plane['angle'] + 180) % 360 - 180)
                if angle_diff > 5: continue
                if (dist := math.sqrt(dx**2 + dy**2)) > 1:
                    dx, dy = dx/dist, dy/dist
                    spawn_x, spawn_y = plane['pos_x'] + self.plane_size.width()/2, plane['pos_y'] + self.plane_size.height()/2
                    proj = {'label': QLabel(self), 'base_pixmap': self.projectile_pixmap, 'pos_x': spawn_x, 'pos_y': spawn_y, 'vx': dx*9, 'vy': dy*9, 'frame': 0, 'shooter_index': i, 'angle': math.degrees(math.atan2(dy, dx))}
                    proj['label'].setPixmap(proj['base_pixmap']); proj['label'].resize(proj['base_pixmap'].size()); proj['label'].show(); self.projectiles.append(proj)

    def fire_missiles(self):
        for i, plane in enumerate(self.planes):
            if plane['health'] <= 0: continue
            target = self.planes[1 - i]
            if target['health'] > 0:
                dx, dy = target['pos_x'] - plane['pos_x'], target['pos_y'] - plane['pos_y']
                if (dist := math.sqrt(dx**2 + dy**2)) > 400 and abs((math.degrees(math.atan2(dy, dx)) - plane['angle'] + 180) % 360 - 180) < 30:
                    spawn_x, spawn_y = plane['pos_x'] + self.plane_size.width()/2, plane['pos_y'] + self.plane_size.height()/2
                    if dist > 1: dx, dy = dx/dist, dy/dist
                    missile = {'label': QLabel(self), 'base_pixmap': self.missile_pixmap, 'pos_x': spawn_x, 'pos_y': spawn_y, 'vx': dx*self.missile_speed, 'vy': dy*self.missile_speed, 'angle': math.degrees(math.atan2(dy, dx)), 'shooter_index': i, 'target_index': 1-i, 'frame': 0, 'target_flare': None, 'target_missile': None}
                    missile['label'].setPixmap(missile['base_pixmap']); missile['label'].resize(missile['base_pixmap'].size()); missile['label'].show(); self.missiles.append(missile)

    def update_planes(self):
        for i, plane in enumerate(self.planes):
            if plane['health'] <= 0: continue
            threat_detected = False
            for missile in self.missiles:
                if missile['target_index'] == i and not missile.get('target_flare') and not missile.get('target_missile') and math.sqrt((missile['pos_x'] - plane['pos_x'])**2 + (missile['pos_y'] - plane['pos_y'])**2) < 350:
                    threat_detected = True; plane['y_target'] = plane['pos_y'] - 200 if missile['pos_y'] > plane['pos_y'] else plane['pos_y'] + 200; break
            if not threat_detected:
                for proj in self.projectiles:
                    if proj['shooter_index'] != i and abs(plane['pos_y'] - proj['pos_y']) < 50 and math.sqrt((proj['pos_x'] - plane['pos_x'])**2 + (proj['pos_y'] - plane['pos_y'])**2) < 250:
                        threat_detected = True; plane['y_target'] = plane['pos_y'] + (150 if proj['vy'] < 0 else -150); break
            if not threat_detected:
                plane['change_y_counter'] += 1
                if plane['change_y_counter'] >= 120: plane['y_target'] = random.randint(self.screen_height//4, self.screen_height*3//4); plane['change_y_counter'] = 0
            if (plane['pos_x'] >= self.screen_width - self.plane_size.width() and plane['direction'] == 1) or (plane['pos_x'] <= 0 and plane['direction'] == -1):
                plane['direction'] *= -1; plane['speed'] = plane['base_speed'] * plane['direction']
                if plane['pos_y'] < self.screen_height/2: plane['y_target'] = random.randint(self.screen_height//2, self.screen_height*3//4)
                else: plane['y_target'] = random.randint(self.screen_height//4, self.screen_height//2)
            
            health_percentage = max(0, plane['health']/30); damage_modifier = 0.4 + (0.6 * health_percentage); effective_speed = plane['speed'] * damage_modifier
            plane['prev_pos_x'], plane['prev_pos_y'] = plane['pos_x'], plane['pos_y']; plane['pos_x'] += effective_speed
            
            vertical_acceleration = 0.1; max_vertical_speed = 4
            if plane['y_target'] > plane['pos_y']: plane['vy'] += vertical_acceleration
            else: plane['vy'] -= vertical_acceleration
            plane['vy'] = max(-max_vertical_speed, min(plane['vy'], max_vertical_speed)); plane['vy'] *= 0.97; plane['pos_y'] += plane['vy']
            plane['pos_x'] = max(0, min(plane['pos_x'], self.screen_width - self.plane_size.width())); plane['pos_y'] = max(0, min(plane['pos_y'], self.screen_height - self.plane_size.height()))
            
            dx, dy = plane['pos_x'] - plane['prev_pos_x'], plane['pos_y'] - plane['prev_pos_y']
            plane['angle'] = math.degrees(math.atan2(dy, dx)) if dx or dy else (0 if plane['direction'] == 1 else 180)
            
            damaged_pixmap = self.plane_pixmap.copy()
            if plane['damage_points']:
                painter = QPainter(damaged_pixmap); painter.setCompositionMode(QPainter.CompositionMode_Clear)
                painter.setBrush(Qt.transparent); painter.setPen(Qt.NoPen)
                for point in plane['damage_points']: painter.drawEllipse(point, 3, 3)
                painter.end()
            transform = QTransform().translate(self.plane_size.width()/2, self.plane_size.height()/2).rotate(plane['angle']).translate(-self.plane_size.width()/2, -self.plane_size.height()/2)
            plane['label'].setPixmap(damaged_pixmap.transformed(transform, Qt.SmoothTransformation)); plane['label'].move(QPoint(int(plane['pos_x']), int(plane['pos_y'])))
            
            if plane['health'] < 9: num, size = 3, 12
            elif plane['health'] < 17: num, size = 2, 8
            elif plane['health'] < 27: num, size = 1, 5
            else: num = 0
            if num > 0:
                center_x, center_y = self.plane_size.width()/2, self.plane_size.height()/2
                angle_rad = math.radians(plane['angle'])
                for i in range(num):
                    y_offset = (i - (num - 1)/2) * 10; relative_x = -30
                    rotated_relative_x = relative_x * math.cos(angle_rad) - y_offset * math.sin(angle_rad)
                    rotated_relative_y = relative_x * math.sin(angle_rad) + y_offset * math.cos(angle_rad)
                    spawn_x = center_x + plane['pos_x'] + rotated_relative_x; spawn_y = center_y + plane['pos_y'] + rotated_relative_y
                    smoke_vx = (plane['pos_x'] - plane['prev_pos_x']) * -0.2 + random.uniform(-0.2, 0.2)
                    smoke_vy = (plane['pos_y'] - plane['prev_pos_y']) * -0.2 + random.uniform(-0.2, 0.2)
                    smoke = {'label': QLabel(self), 'pos_x': spawn_x, 'pos_y': spawn_y, 'vx': smoke_vx, 'vy': smoke_vy, 'size': size, 'opacity': 0.8, 'lifetime': 60, 'frame': 0, 'type': 'smoke'}
                    smoke['label'].setPixmap(self.create_particle_pixmap(size, 0.8, QColor(100,100,100))); smoke['label'].resize(smoke['label'].pixmap().size()); smoke['label'].show(); self.smoke_particles.append(smoke)

    def update_projectiles(self):
        to_remove = []
        for p in self.projectiles:
            p['pos_x'] += p['vx']; p['pos_y'] += p['vy']; p['frame'] += 1
            transform = QTransform().translate(20/2, 20/2).rotate(p['angle']).translate(-20/2, -20/2)
            p['label'].setPixmap(p['base_pixmap'].transformed(transform, Qt.SmoothTransformation)); p['label'].move(QPoint(int(p['pos_x'] - p['base_pixmap'].width()/2), int(p['pos_y'] - p['base_pixmap'].height()/2)))
            if self.game_active:
                for j, plane in enumerate(self.planes):
                    if plane['health'] > 0 and j != p['shooter_index'] and p['label'].geometry().intersects(plane['label'].geometry()):
                        plane['health'] -= 1; to_remove.append(p)
                        for _ in range(3): plane['damage_points'].append(QPoint(random.randint(20, self.plane_size.width() - 20) + random.randint(-5, 5), random.randint(20, self.plane_size.height() - 20) + random.randint(-5, 5)))
                        if plane['health'] <= 0: self.create_plane_explosion(plane); plane['label'].hide()
                        break
            if not (-10 < p['pos_x'] < self.screen_width and -10 < p['pos_y'] < self.screen_height): to_remove.append(p)
        for p in to_remove:
            if p in self.projectiles: p['label'].hide(); self.projectiles.remove(p)

    def update_missiles(self):
        to_remove = []
        for m in self.missiles:
            if m in to_remove: continue
            target_x, target_y = self.get_missile_target_pos(m)
            desired_vx, desired_vy = m['vx'], m['vy']
            if target_x:
                dx, dy = target_x - m['pos_x'], target_y - m['pos_y']
                if (dist := math.sqrt(dx**2 + dy**2)) > 1: desired_vx, desired_vy = (dx/dist)*self.missile_speed, (dy/dist)*self.missile_speed
            m['vx'] += (desired_vx - m['vx'])*self.missile_turn_rate; m['vy'] += (desired_vy - m['vy'])*self.missile_turn_rate
            if (speed := math.sqrt(m['vx']**2 + m['vy']**2)) > 0: m['vx'], m['vy'] = (m['vx']/speed)*self.missile_speed, (m['vy']/speed)*self.missile_speed
            m['pos_x'] += m['vx']; m['pos_y'] += m['vy']; m['angle'] = math.degrees(math.atan2(m['vy'], m['vx'])); m['frame'] += 1
            if m['frame'] % 2 == 0:
                for _ in range(3):
                    smoke = {'label': QLabel(self), 'pos_x': m['pos_x']+random.uniform(-2,2), 'pos_y': m['pos_y']+random.uniform(-2,2), 'vx': -m['vx']*0.1, 'vy': -m['vy']*0.1, 'size': 4, 'opacity': 0.7, 'lifetime': 30, 'frame': 0, 'type': 'smoke'}
                    smoke['label'].setPixmap(self.create_particle_pixmap(4, 0.7, QColor(100,100,100))); smoke['label'].resize(smoke['label'].pixmap().size()); smoke['label'].show(); self.smoke_particles.append(smoke)
            transform = QTransform().translate(self.missile_base_size/2, self.missile_base_size/2).rotate(m['angle']+90).translate(-self.missile_base_size/2, -self.missile_base_size/2)
            m['label'].setPixmap(m['base_pixmap'].transformed(transform, Qt.SmoothTransformation)); m['label'].move(QPoint(int(m['pos_x'] - m['base_pixmap'].width()/2), int(m['pos_y'] - m['base_pixmap'].height()/2)))
            collided = self.check_missile_collision(m)
            if collided: to_remove.extend(c for c in collided if c not in to_remove)
            if not (-50 < m['pos_x'] < self.screen_width+50 and -50 < m['pos_y'] < self.screen_height+50) or m['frame'] > 270:
                if m not in to_remove: to_remove.append(m)
        for m in to_remove:
            if m in self.missiles: self.create_explosion(m['pos_x'], m['pos_y']); m['label'].hide(); self.missiles.remove(m)

    def get_missile_target_pos(self, missile):
        if (tm := missile.get('target_missile')) and tm in self.missiles: return tm['pos_x'], tm['pos_y']
        if (tf := missile.get('target_flare')) and tf in self.flares: return tf['pos_x'], tf['pos_y']
        if not tf:
            for other in self.missiles:
                if missile != other and missile['shooter_index'] != other['shooter_index'] and math.sqrt((other['pos_x'] - missile['pos_x'])**2 + (other['pos_y'] - missile['pos_y'])**2) < 100 and random.random() < 0.1:
                    missile['target_missile'] = other; break
            if not missile.get('target_missile'):
                for flare in self.flares:
                    if math.sqrt((flare['pos_x'] - missile['pos_x'])**2 + (flare['pos_y'] - missile['pos_y'])**2) < 150 and random.random() < 0.6:
                        missile['target_flare'] = flare; break
        target_plane = self.planes[missile['target_index']]
        if target_plane['health'] > 0:
            tx, ty = target_plane['pos_x'] + self.plane_size.width()/2, target_plane['pos_y'] + self.plane_size.height()/2
            if self.game_active and math.sqrt((tx - missile['pos_x'])**2 + (ty - missile['pos_y'])**2) < 200 and target_plane['flare_cooldown'] == 0 and target_plane['flares_left'] > 0 and random.random() < 0.5:
                target_plane['is_deploying_flares'], target_plane['flare_deployment_counter'], target_plane['flare_cooldown'] = True, 16, 180
            return tx, ty
        return 0, 0

    def check_missile_collision(self, missile):
        destroyed = []
        if (tm := missile.get('target_missile')) and tm in self.missiles and missile['label'].geometry().intersects(tm['label'].geometry()):
            print("Missile-on-missile impact!"); destroyed.extend([missile, tm])
        elif self.game_active and not missile.get('target_flare'):
            target_plane = self.planes[missile['target_index']]
            if target_plane['health'] > 0 and missile['label'].geometry().intersects(target_plane['label'].geometry()):
                target_plane['health'] -= 5; destroyed.append(missile)
                if target_plane['health'] <= 0: self.create_plane_explosion(target_plane); target_plane['label'].hide()
        return destroyed

    def update_effects(self):
        for group in [self.smoke_particles, self.flares, self.explosions]:
            to_remove = []
            for item in group:
                item['frame'] += 1
                if item['frame'] >= item['lifetime']: to_remove.append(item); continue
                item['opacity'] = 1.0 - (item['frame'] / item['lifetime'])
                if group == self.smoke_particles:
                    item['pos_x'] += item['vx']; item['pos_y'] += item['vy']
                    color = QColor(80, 80, 80); is_flare_smoke = False
                    if item.get('type') == 'flare_smoke': color, is_flare_smoke = QColor(255, 255, 0), True
                    else:
                        progress = item['frame'] / item['lifetime']
                        if progress < 0.15: color = QColor(255, int(165 * (1 - (progress/0.15)) + 255 * (progress/0.15)), 0)
                        elif progress < 0.5:
                            stage_progress = (progress - 0.15) / 0.35
                            color = QColor(int(255 * (1 - stage_progress) + 80 * stage_progress), int(255 * (1 - stage_progress) + 80 * stage_progress), int(0 * (1 - stage_progress) + 80 * stage_progress))
                    item['label'].setPixmap(self.create_particle_pixmap(item['size'], item['opacity'], color, is_flare_smoke))
                elif group == self.flares:
                    item['pos_x'] += item['vx']; item['pos_y'] += item['vy']
                    if item['frame'] % 3 == 0:
                        smoke = {'label': QLabel(self), 'pos_x': item['pos_x'], 'pos_y': item['pos_y'], 'vx': random.uniform(-0.5,0.5), 'vy': random.uniform(-0.5,0.5), 'size': 10, 'opacity': 0.8, 'lifetime': 40, 'frame': 0, 'type': 'flare_smoke'}
                        smoke['label'].setPixmap(self.create_particle_pixmap(10, 0.8, QColor(255,255,0), True)); smoke['label'].resize(smoke['label'].pixmap().size()); smoke['label'].show(); self.smoke_particles.append(smoke)
                    item['label'].setPixmap(self.create_particle_pixmap(item['size'], item['opacity'], QColor(255,255,0)))
                elif group == self.explosions:
                    item['size'] = 20 + (item['max_size'] - 20) * (item['frame']/item['lifetime'])
                    item['label'].setPixmap(self.create_particle_pixmap(item['size'], item['opacity'], item.get('color', QColor(255,165,0))))
                item['label'].resize(item['label'].pixmap().size()); item['label'].move(QPoint(int(item['pos_x'] - item['size']/2), int(item['pos_y'] - item['size']/2)))
            for item in to_remove:
                if item in group: item['label'].hide(); group.remove(item)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = PlaneAnimation()
    sys.exit(app.exec_())