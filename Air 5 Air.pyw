import sys
import os
import random
import math
from PyQt5.QtWidgets import QApplication, QLabel, QWidget
from PyQt5.QtCore import Qt, QTimer, QPoint, QRect
from PyQt5.QtGui import QPixmap, QImage, QPainter, QTransform, QColor, QPen, QPainterPath, QRadialGradient

class PlaneAnimation(QWidget):
    def __init__(self, geometry=None):
        super().__init__()
        print("--- Initializing PlaneAnimation ---")

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        
        if geometry:
            screen = geometry
        else:
            screen = QApplication.primaryScreen().geometry()
            
        self.screen_width = screen.width()
        self.screen_height = screen.height()
        self.resize(self.screen_width, self.screen_height)
        self.setGeometry(screen)
        
        # --- Fighter Selection ---
        factions = [
            ("F-22", "F-35"),    # US
            ("J-11", "J-20"),    # Chinese
            ("Su-47", "Su-57")   # Russian
        ]
        
        # Select two different factions
        faction1, faction2 = random.sample(factions, 2)
        
        # Pick one random fighter from each faction
        fighter1_name = random.choice(faction1)
        fighter2_name = random.choice(faction2)
        
        self.plane1_pixmap = self.load_plane_pixmap(fighter1_name)
        self.plane2_pixmap = self.load_plane_pixmap(fighter2_name)
        
        self.plane_size = self.plane1_pixmap.size() # Padded size, should be consistent
        self.projectile_pixmap = self.create_projectile_image()
        self.missile_pixmap = self.create_missile_image()

        # debug markers removed in production

        self.planes, self.projectiles, self.missiles, self.smoke_particles, self.explosions, self.flares = [], [], [], [], [], []
        
        self.init_planes()
        
        self.missile_speed = 8
        self.missile_turn_rate = 0.05
        self.missile_base_size = 25

        self.game_state = 'ACTIVE' # ACTIVE, ENDING
        self.winner = None
        
        self.shoot_counter = 0
        self.shoot_interval = 2

        # Stalemate detection
        self.stalemate_timer = 0
        self.last_known_health = {0: 30, 1: 30}
        self.STALEMATE_THRESHOLD = 120 # 2 seconds (120 frames / 60fps)

        # Global speed scale for planes (0.0-1.0); lower values slow all planes
        self.plane_speed_scale = 0.7

        self.show_hud = False
        self.hud_labels = []
        self.init_hud()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_position)
        self.timer.start(16)

        # Debug: measure visual centroid offsets (disabled)
        self.debug_measure_offsets = False
        # particle pixmap cache to avoid regenerating identical images each frame
        self.particle_cache = {}
        # rotated pixmap + offset cache
        self.rotated_cache = {}
        # simple caps
        self.max_smoke_particles = 300
        self.max_projectiles = 80
        self.max_missiles = 30
        
        self.show()
        self.raise_()
        print("--- Initialization Complete. Window Shown. ---")

    def _get_rotated_pixmap_and_offset(self, base_pixmap, angle_deg):
        # Quantize angle to reduce cache size and avoid per-frame heavy work
        quant = int(round(angle_deg / 5.0) * 5) % 360
        key = (id(base_pixmap), quant)
        if key in self.rotated_cache:
            return self.rotated_cache[key]

        w = base_pixmap.width()
        h = base_pixmap.height()
        transform = QTransform().translate(w/2, h/2).rotate(quant).translate(-w/2, -h/2)
        try:
            rotated = base_pixmap.transformed(transform, Qt.SmoothTransformation)
        except Exception:
            rotated = base_pixmap

        # Simple centering: align rotated bbox center to logical center
        off_x = (w - rotated.width()) / 2
        off_y = (h - rotated.height()) / 2

        self.rotated_cache[key] = (rotated, off_x, off_y)
        return self.rotated_cache[key]

    def create_projectile_image(self):
        size = 16
        image = QImage(size, size, QImage.Format_ARGB32)
        image.fill(Qt.transparent)
        painter = QPainter(image)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor(255, 215, 0))
        painter.setPen(QPen(Qt.black, 1))
        painter.drawRoundedRect((size - 8)//2, (size - 4)//2, 8, 4, 1, 1)
        painter.end()
        return QPixmap.fromImage(image)

    def create_fallback_image(self, color=Qt.red):
        size = 100
        pix = QPixmap(size, size)
        pix.fill(Qt.transparent)
        painter = QPainter(pix)
        painter.setRenderHint(QPainter.Antialiasing)
        bg = QColor(color) if not isinstance(color, QColor) else color
        painter.setBrush(bg)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(5, 5, size-10, size-10)
        painter.end()
        return pix

    def load_plane_pixmap(self, fighter_name):
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            image_path = os.path.join(script_dir, f"{fighter_name}.png")
            if os.path.exists(image_path):
                pixmap = QPixmap(image_path)
                if not pixmap.isNull():
                    pixmap = pixmap.scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    padding = 20
                    padded = QPixmap(pixmap.width() + 2 * padding, pixmap.height() + 2 * padding)
                    padded.fill(Qt.transparent)
                    painter = QPainter(padded); painter.drawPixmap(padding, padding, pixmap); painter.end()
                    return padded
        except Exception:
            pass
        return self.create_fallback_image(Qt.red)

    def init_planes(self):
        left_y = random.randint(self.screen_height//4, self.screen_height*3//4)
        right_y = random.randint(self.screen_height//4, self.screen_height*3//4)
        self.planes = [
            {'base_pixmap': self.plane1_pixmap, 'pixmap': self.plane1_pixmap.copy(), 'pos_x': 100, 'pos_y': left_y, 'vx': 5, 'vy': 0, 'angle': random.uniform(-20,20), 'target_angle': 0, 'speed': random.uniform(4.5,5.5), 'turn_rate': random.uniform(2.0,3.0), 'health': 30, 'damage_points': [], 'ammo': 60, 'max_ammo': 60, 'flare_cooldown': 0, 'flares_left': 2, 'missile_fire_cooldown': 0, 'missiles_left': 4, 'is_deploying_flares': False, 'flare_deployment_counter': 0, 'evade_timer': 0, 'state': 'chasing', 'visible': True, 'is_disintegrating': False, 'disintegration_timer': 0, 'angular_velocity': 0, 'turn_direction_lost': None},
            {'base_pixmap': self.plane2_pixmap, 'pixmap': self.plane2_pixmap.copy(), 'pos_x': self.screen_width - 100, 'pos_y': right_y, 'vx': -5, 'vy': 0, 'angle': 180 + random.uniform(-20,20), 'target_angle': 180, 'speed': random.uniform(4.5,5.5), 'turn_rate': random.uniform(2.0,3.0), 'health': 30, 'damage_points': [], 'ammo': 60, 'max_ammo': 60, 'flare_cooldown': 0, 'flares_left': 2, 'missile_fire_cooldown': 0, 'missiles_left': 4, 'is_deploying_flares': False, 'flare_deployment_counter': 0, 'evade_timer': 0, 'state': 'chasing', 'visible': True, 'is_disintegrating': False, 'disintegration_timer': 0, 'angular_velocity': 0, 'turn_direction_lost': None}
        ]

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

    def create_particle_pixmap(self, size, opacity, color, is_flare=False, is_flare_smoke=False):
        # Use a cache key to avoid regenerating identical particle images
        color_key = None
        if isinstance(color, QColor):
            color_key = (color.red(), color.green(), color.blue(), color.alpha())
        else:
            color_key = str(color)
        key = (int(size), round(float(opacity), 3), color_key, bool(is_flare), bool(is_flare_smoke))
        if key in self.particle_cache:
            return self.particle_cache[key]

        image = QImage(int(size), int(size), QImage.Format_ARGB32); image.fill(Qt.transparent)
        painter = QPainter(image)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)

        if is_flare:
            gradient = QRadialGradient(size/2, size/2, size/2)
            center_color = QColor(255, 255, 220)
            center_color.setAlphaF(opacity)
            gradient.setColorAt(0, center_color)

            mid_color = QColor(255, 200, 0)
            mid_color.setAlphaF(opacity * 0.8)
            gradient.setColorAt(0.6, mid_color)

            edge_color = QColor(255, 100, 0)
            edge_color.setAlphaF(opacity * 0.3)
            gradient.setColorAt(1, edge_color)

            painter.setBrush(gradient)
        else:
            final_color = QColor(color) if color is not None else QColor(100,100,100)
            final_color.setAlpha(int(opacity * (150 if is_flare_smoke else 255)))
            painter.setBrush(final_color);
        painter.drawEllipse(0, 0, int(size), int(size))
        painter.end()
        pm = QPixmap.fromImage(image)
        self.particle_cache[key] = pm
        return pm

    def create_plane_explosion(self, plane):
        # Instead of creating an explosion, start the disintegration process
        if not plane.get('is_disintegrating', False):
            try:
                plane['state'] = 'destroyed'
                plane['health'] = 0
                plane['is_disintegrating'] = True
                plane['disintegration_timer'] = 120 # 2 seconds at 60fps
                # Slow down the plane a bit, but keep momentum
                plane['vx'] *= 0.8
                plane['vy'] *= 0.8
                plane['angular_velocity'] = random.uniform(-1, 1)
            except Exception as e:
                print(f"Error starting disintegration: {e}")

    def create_explosion(self, x, y):
        self.explosions.append({'pos_x': x, 'pos_y': y, 'size': 20, 'max_size': 80, 'opacity': 1.0, 'frame': 0, 'lifetime': 25, 'color': QColor(255, 165, 0)})

    def create_small_explosion(self, x, y, size_range=(5, 20), lifetime=20, color=None):
        if color is None:
            color = random.choice([QColor(255, 165, 0), QColor(255, 255, 0), QColor(255, 100, 0)])
        self.explosions.append({'pos_x': x, 'pos_y': y, 'size': size_range[0], 'max_size': size_range[1], 'opacity': 1.0, 'frame': 0, 'lifetime': lifetime, 'color': color})

    def init_hud(self):
        # HUD for Plane 1 (Left)
        self.hud_left = QLabel(self)
        self.hud_left.setGeometry(10, 10, 250, 140)
        self.hud_left.setStyleSheet("color: white; background-color: rgba(0, 0, 0, 100); border-radius: 5px; padding: 5px; font-family: 'Lucida Console', Monaco, monospace;")
        self.hud_left.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.hud_left.setVisible(self.show_hud)
        self.hud_labels.append(self.hud_left)

        # HUD for Plane 2 (Right)
        self.hud_right = QLabel(self)
        self.hud_right.setGeometry(self.screen_width - 260, 10, 250, 140)
        self.hud_right.setStyleSheet("color: white; background-color: rgba(0, 0, 0, 100); border-radius: 5px; padding: 5px; font-family: 'Lucida Console', Monaco, monospace;")
        self.hud_right.setAlignment(Qt.AlignTop | Qt.AlignRight)
        self.hud_right.setVisible(self.show_hud)
        self.hud_labels.append(self.hud_right)

    def update_hud(self):
        if not self.show_hud:
            return

        # HUD for Plane 1 (Left)
        plane1 = self.planes[0]
        health_bar1 = "█" * int(plane1['health'] / 3) + " " * (10 - int(plane1['health'] / 3))
        hud1_text = (
            f"<b>Left Wing</b><br>"
            f"Health: [{health_bar1}]<br>"
            f"Ammo: {plane1.get('ammo', 0):03d}<br>"
            f"Missiles: {plane1.get('missiles_left', 0)} | Flares: {plane1.get('flares_left', 0)}"
        )
        self.hud_left.setText(hud1_text)

        # HUD for Plane 2 (Right)
        plane2 = self.planes[1]
        health_bar2 = "█" * int(plane2['health'] / 3) + " " * (10 - int(plane2['health'] / 3))
        # Align text to the right using HTML-like styling for the QLabel
        hud2_text = (
            f"<div align='right'><b>Right Wing</b><br>"
            f"Health: [{health_bar2}]<br>"
            f"Ammo: {plane2.get('ammo', 0):03d}<br>"
            f"Missiles: {plane2.get('missiles_left', 0)} | Flares: {plane2.get('flares_left', 0)}</div>"
        )
        self.hud_right.setText(hud2_text)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_H:
            self.show_hud = not self.show_hud
            for label in self.hud_labels:
                label.setVisible(self.show_hud)
        elif event.key() == Qt.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(event)

    def update_position(self):
        try:
            self.update_hud()

            if self.game_state == 'ACTIVE':
                self.update_active_game_logic()
                self.check_game_over()
            elif self.game_state == 'ENDING':
                self.update_end_phase()

            self.update_disintegration()

            # Update projectiles and effects regardless of game state
            self.update_projectiles()
            self.update_missiles()
            self.update_effects()

            # Schedule a single repaint for this frame (avoid multiple update() calls)
            # Drawing is handled in paintEvent which uses cached rotated pixmaps.
            self.update()

            # Condition to close the application
            if self.game_state == 'ENDING' and not self.projectiles and not self.missiles and all(not p.get('visible', True) for p in self.planes):
                self.close()

        except Exception as e:
            print(f"!!! FATAL ERROR in update_position: {e}")
            self.timer.stop()

    def update_active_game_logic(self):
        # --- "Bingo Ammo" Check ---
        p1, p2 = self.planes[0], self.planes[1]
        if p1['ammo'] <= 0 and p2['ammo'] <= 0 and self.game_state == 'ACTIVE':
            print("--- BINGO AMMO! Both planes returning to base. ---")
            self.game_state = 'ENDING'
            self.winner = None # It's a draw
            
            # Assign exit targets for both planes
            p1['exit_target_x'] = -200
            p1['exit_target_y'] = p1['pos_y']
            
            p2['exit_target_x'] = self.screen_width + 200
            p2['exit_target_y'] = p2['pos_y']
            return

        # --- Stalemate Detection ---
        dist = math.sqrt((p1['pos_x'] - p2['pos_x'])**2 + (p1['pos_y'] - p2['pos_y'])**2)
        
        # Check if health has changed
        health_changed = (p1['health'] != self.last_known_health[0] or 
                          p2['health'] != self.last_known_health[1])

        if dist < 150 and not health_changed:
            self.stalemate_timer += 1
        else:
            self.stalemate_timer = 0
            self.last_known_health[0] = p1['health']
            self.last_known_health[1] = p2['health']

        if self.stalemate_timer > self.STALEMATE_THRESHOLD:
            print("--- STALEMATE DETECTED! Disengaging... ---")
            self.stalemate_timer = 0
            margin = 150
            for p in self.planes:
                p['state'] = 'disengaging'
                p['disengage_timer'] = 120 # 2 seconds
            
            self.planes[0]['disengage_target_x'] = margin
            self.planes[0]['disengage_target_y'] = margin
            self.planes[1]['disengage_target_x'] = self.screen_width - margin
            self.planes[1]['disengage_target_y'] = self.screen_height - margin

        self.handle_plane_actions()
        self.update_planes()

    def update_end_phase(self):
        if self.winner:
            # If winner was destroyed by a stray shot, it's a draw
            if self.winner['health'] <= 0:
                print("--- Winner destroyed post-victory! It's a draw! ---")
                self.winner = None
                return

            # Smoothly turn winner to exit
            dx = self.winner['exit_target_x'] - self.winner['pos_x']
            dy = self.winner['exit_target_y'] - self.winner['pos_y']
            self.winner['target_angle'] = math.degrees(math.atan2(dy, dx))
            
            angle_diff = (self.winner['target_angle'] - self.winner['angle'] + 180) % 360 - 180
            turn_amount = max(-self.winner['turn_rate'], min(self.winner['turn_rate'], angle_diff))
            self.winner['angle'] += turn_amount
            self.winner['angle'] %= 360

            # Move at normal speed
            angle_rad = math.radians(self.winner['angle'])
            self.winner['vx'] = math.cos(angle_rad) * (self.winner['speed'] * self.plane_speed_scale)
            self.winner['vy'] = math.sin(angle_rad) * (self.winner['speed'] * self.plane_speed_scale)
            self.winner['pos_x'] += self.winner['vx']
            self.winner['pos_y'] += self.winner['vy']
            
            # --- Smoke Trail Update (copied from update_planes) ---
            num, size = 0, 0
            if self.winner['health'] < 9: num, size = 3, 12
            elif self.winner['health'] < 17: num, size = 2, 8
            elif self.winner['health'] < 27: num, size = 1, 5

            if num > 0:
                center_x, center_y = self.plane_size.width()/2, self.plane_size.height()/2
                angle_rad = math.radians(self.winner['angle'])
                for k in range(num):
                    # spawn smoke slightly behind the plane center so trail appears behind
                    local_x = -12
                    local_y = 0
                    rotated_relative_x = local_x * math.cos(angle_rad) - local_y * math.sin(angle_rad)
                    rotated_relative_y = local_x * math.sin(angle_rad) + local_y * math.cos(angle_rad)
                    spawn_x = center_x + self.winner['pos_x'] + rotated_relative_x
                    spawn_y = center_y + self.winner['pos_y'] + rotated_relative_y
                    smoke_vx = -self.winner['vx'] * 0.2 + random.uniform(-0.2, 0.2)
                    smoke_vy = -self.winner['vy'] * 0.2 + random.uniform(-0.2, 0.2)
                    smoke = {'pos_x': spawn_x, 'pos_y': spawn_y, 'vx': 0.0, 'vy': 0.0, 'drift_vx': smoke_vx, 'drift_vy': smoke_vy, 'drift_offset_x': 0.0, 'drift_offset_y': 0.0, 'size': size, 'opacity': 0.8, 'lifetime': 60, 'frame': 0, 'type': 'smoke', 'attached_to': self.planes.index(self.winner) if self.winner in self.planes else None, 'local_x': local_x, 'local_y': local_y, 'attached_time': 12}
                    self.smoke_particles.append(smoke)

            # Update label
            damaged_pixmap = self.winner['base_pixmap'].copy()
            if self.winner['damage_points']:
                painter = QPainter(damaged_pixmap)
                painter.setCompositionMode(QPainter.CompositionMode_Clear)
                painter.setBrush(Qt.transparent)
                painter.setPen(Qt.NoPen)
                for point in self.winner['damage_points']:
                    painter.drawEllipse(point, 2, 2)
                painter.end()

            self.winner['current_pixmap'] = damaged_pixmap

            # Check if winner has exited
            if not (-150 < self.winner['pos_x'] < self.screen_width + 150 and -150 < self.winner['pos_y'] < self.screen_height + 150):
                self.winner['visible'] = False
                self.winner = None
        else:
            # Stalemate or No Ammo case: both planes fly off
            for plane in self.planes:
                if not plane.get('visible', True):
                    continue

                if 'exit_target_x' not in plane:
                    plane['exit_target_x'] = -200 if plane['pos_x'] < self.screen_width / 2 else self.screen_width + 200
                    plane['exit_target_y'] = plane['pos_y']

                dx = plane['exit_target_x'] - plane['pos_x']
                dy = plane['exit_target_y'] - plane['pos_y']
                plane['target_angle'] = math.degrees(math.atan2(dy, dx))
                
                angle_diff = (plane['target_angle'] - plane['angle'] + 180) % 360 - 180
                turn_amount = max(-plane['turn_rate'], min(plane['turn_rate'], angle_diff))
                plane['angle'] += turn_amount
                plane['angle'] %= 360

                angle_rad = math.radians(plane['angle'])
                plane['vx'] = math.cos(angle_rad) * (plane['speed'] * self.plane_speed_scale)
                plane['vy'] = math.sin(angle_rad) * (plane['speed'] * self.plane_speed_scale)
                plane['pos_x'] += plane['vx']
                plane['pos_y'] += plane['vy']

                # Check if plane has exited
                if not (-150 < plane['pos_x'] < self.screen_width + 150 and -150 < plane['pos_y'] < self.screen_height + 150):
                    plane['visible'] = False

    def check_game_over(self):
        survivors = [p for p in self.planes if p.get('health', 0) > 0 and not p.get('is_disintegrating', False)]
        if len(survivors) <= 1 and self.game_state == 'ACTIVE':
            self.game_state = 'ENDING'
            self.winner = next((p for p in survivors), None)
            if self.winner:
                winner_index = self.planes.index(self.winner)
                print(f"--- Plane {winner_index} is the winner! ---")
                # pick an exit direction off the side it's closest to
                if self.winner['pos_x'] < self.screen_width / 2:
                    self.winner['exit_target_x'] = -200
                else:
                    self.winner['exit_target_x'] = self.screen_width + 200
                self.winner['exit_target_y'] = self.winner['pos_y']
                # orient nose toward exit immediately
                dx = self.winner['exit_target_x'] - self.winner['pos_x']
                dy = self.winner['exit_target_y'] - self.winner['pos_y']
                target_angle = math.degrees(math.atan2(dy, dx))
                self.winner['target_angle'] = target_angle
            else:
                print("--- Mutual destruction! ---")

    def handle_plane_actions(self):
        # Firing is only allowed during the active game state
        if self.game_state == 'ACTIVE':
            self.shoot_counter += 1
            if self.shoot_counter >= self.shoot_interval:
                self.shoot_counter = 0
                self.fire_projectiles()

        # Flare deployment can happen anytime
        for plane in self.planes:
            if plane['health'] <= 0: continue
            if plane['flare_cooldown'] > 0: plane['flare_cooldown'] -= 1
            if plane['is_deploying_flares'] and plane['flare_deployment_counter'] > 0 and plane['flare_deployment_counter'] % 2 == 0:
                direction = math.copysign(1, plane['vx']) if plane['vx'] != 0 else 1
                flare = {'pos_x': plane['pos_x'] + self.plane_size.width()/2, 'pos_y': plane['pos_y'] + self.plane_size.height()/2, 'vx': random.uniform(-2, 2) - direction*2, 'vy': random.uniform(-2, 2), 'size': 15, 'opacity': 1.0, 'lifetime': 90, 'frame': 0, 'type': 'flare'}
                self.flares.append(flare)
            if plane['is_deploying_flares']: plane['flare_deployment_counter'] -= 1
            if plane['flare_deployment_counter'] <= 0: plane['is_deploying_flares'] = False

    def fire_projectiles(self):
        for i, plane in enumerate(self.planes):
            if plane['health'] <= 0 or plane['ammo'] <= 0: continue
            target = self.planes[1 - i]
            if target['health'] > 0:
                cautiousness = 1.0 - (plane['ammo'] / plane['max_ammo'])
                required_angle_off = 8 - (cautiousness * 6) 

                projectile_speed = 12.0
                dx_initial, dy_initial = target['pos_x'] - plane['pos_x'], target['pos_y'] - plane['pos_y']
                dist_initial = math.sqrt(dx_initial**2 + dy_initial**2)
                if dist_initial == 0: continue

                time_to_hit = dist_initial / projectile_speed
                predicted_x = target['pos_x'] + target['vx'] * time_to_hit
                predicted_y = target['pos_y'] + target['vy'] * time_to_hit
                
                dx, dy = predicted_x - plane['pos_x'], predicted_y - plane['pos_y']
                dist_to_predicted = math.sqrt(dx**2 + dy**2)
                
                if not (100 < dist_initial < 700): continue

                if dist_to_predicted > 0:
                    vec_to_target = (dx/dist_to_predicted, dy/dist_to_predicted)
                    plane_heading_rad = math.radians(plane['angle'])
                    plane_heading_vec = (math.cos(plane_heading_rad), math.sin(plane_heading_rad))
                    angle_off = math.degrees(math.acos(max(-1, min(1, vec_to_target[0] * plane_heading_vec[0] + vec_to_target[1] * plane_heading_vec[1]))))
                    
                    if angle_off > required_angle_off: continue
                else:
                    continue

                plane['ammo'] -= 1
                fire_dx, fire_dy = dx/dist_to_predicted, dy/dist_to_predicted
                spawn_x, spawn_y = plane['pos_x'] + self.plane_size.width()/2, plane['pos_y'] + self.plane_size.height()/2
                proj = {'base_pixmap': self.projectile_pixmap, 'pos_x': spawn_x, 'pos_y': spawn_y, 'vx': fire_dx*projectile_speed, 'vy': fire_dy*projectile_speed, 'frame': 0, 'shooter_index': i, 'angle': math.degrees(math.atan2(fire_dy, fire_dx))}
                self.projectiles.append(proj)

    def try_fire_missile(self, plane, target):
        if plane.get('missiles_left', 0) <= 0 or plane.get('missile_fire_cooldown', 0) > 0: return False
        
        dx = target['pos_x'] - plane['pos_x']
        dy = target['pos_y'] - plane['pos_y']
        dist = math.sqrt(dx**2 + dy**2)
        
        vec_to_target = (dx/dist, dy/dist)
        plane_heading_rad = math.radians(plane['angle'])
        plane_heading_vec = (math.cos(plane_heading_rad), math.sin(plane_heading_rad))
        angle_off = math.degrees(math.acos(max(-1, min(1, vec_to_target[0] * plane_heading_vec[0] + vec_to_target[1] * plane_heading_vec[1]))))

        if 500 < dist < 2400 and angle_off < 15:
            plane['missiles_left'] -= 1
            plane['missile_fire_cooldown'] = 240 
            
            spawn_x, spawn_y = plane['pos_x'] + self.plane_size.width()/2, plane['pos_y'] + self.plane_size.height()/2
            missile = {'base_pixmap': self.missile_pixmap, 'pos_x': spawn_x, 'pos_y': spawn_y, 'vx': plane['vx'] + math.cos(plane_heading_rad) * 3, 'vy': plane['vy'] + math.sin(plane_heading_rad) * 3, 'angle': plane['angle'], 'shooter_index': self.planes.index(plane), 'target_index': self.planes.index(target), 'frame': 0, 'target_flare': None, 'target_missile': None}
            self.missiles.append(missile)
            return True
        return False

    def handle_missile_threats(self, plane, plane_idx):
        for missile in self.missiles:
            if missile['target_index'] == plane_idx and not missile.get('target_flare'):
                dist_to_missile = math.sqrt((missile['pos_x'] - plane['pos_x'])**2 + (missile['pos_y'] - plane['pos_y'])**2)
                if dist_to_missile < 450:
                    if dist_to_missile < 350 and plane['flare_cooldown'] == 0 and plane['flares_left'] > 0:
                        plane['flares_left'] -= 1
                        plane['is_deploying_flares'] = True
                        plane['flare_deployment_counter'] = 16
                        plane['flare_cooldown'] = 180
                    return True 
        return False

    def _update_plane_pixmap(self, plane):
        damaged_pixmap = plane['base_pixmap'].copy()
        if plane['damage_points']:
            painter = QPainter(damaged_pixmap)
            painter.setCompositionMode(QPainter.CompositionMode_Clear)
            painter.setBrush(Qt.transparent)
            painter.setPen(Qt.NoPen)
            for point in plane['damage_points']:
                painter.drawEllipse(point, 2, 2) # Reduced size
            painter.end()
        
        plane['current_pixmap'] = damaged_pixmap

    def update_disintegration(self):
        for plane in self.planes:
            if plane.get('is_disintegrating', False):
                plane['disintegration_timer'] -= 1
                if plane['disintegration_timer'] <= 0:
                    plane['visible'] = False
                    continue

                center_x = plane['pos_x'] + self.plane_size.width() / 2
                center_y = plane['pos_y'] + self.plane_size.height() / 2
                spawn_radius = 30

                # Add more damage points to simulate disintegration
                for _ in range(10): # More holes for a faster effect
                    plane['damage_points'].append(QPoint(random.randint(5, self.plane_size.width() - 5), random.randint(5, self.plane_size.height() - 5)))

                # Add heavy smoke
                for _ in range(5): # 5 particles per frame
                    smoke_x = center_x + random.uniform(-spawn_radius, spawn_radius)
                    smoke_y = center_y + random.uniform(-spawn_radius, spawn_radius)
                    smoke = {'pos_x': smoke_x, 
                             'pos_y': smoke_y, 
                             'vx': plane['vx'] * 0.1 + random.uniform(-0.5, 0.5), 
                             'vy': plane['vy'] * 0.1 + random.uniform(-0.5, 0.5), 
                             'size': random.uniform(8, 15), 
                             'opacity': 0.9, 
                             'lifetime': random.randint(80, 150), 
                             'frame': 0, 
                             'type': 'smoke'}
                    if len(self.smoke_particles) < self.max_smoke_particles:
                        self.smoke_particles.append(smoke)

                # Add random small explosions
                if random.random() < 0.4: # 40% chance
                    explosion_x = center_x + random.uniform(-spawn_radius, spawn_radius)
                    explosion_y = center_y + random.uniform(-spawn_radius, spawn_radius)
                    # Randomize explosion properties
                    size = random.choice([(5, 20), (10, 30), (3, 15)])
                    color = random.choice([QColor(255, 165, 0), QColor(255, 220, 0), QColor(255, 100, 100), QColor(255, 255, 255)])
                    self.create_small_explosion(explosion_x, explosion_y, size_range=size, color=color)

                # Update position with momentum
                plane['pos_x'] += plane['vx']
                plane['pos_y'] += plane['vy']
                plane['angle'] += plane.get('angular_velocity', 0)

                # Update the pixmap with new damage
                self._update_plane_pixmap(plane)

    def update_planes(self):
        # This function only updates active planes during the 'ACTIVE' game state
        if self.game_state != 'ACTIVE':
            return

        for i, plane in enumerate(self.planes):
            if plane.get('is_disintegrating', False):
                continue # Skip disintegrating planes

            if plane['health'] <= 0: continue

            if plane.get('state') == 'spinning':
                if plane.get('turn_damage_cooldown', 0) > 0:
                    plane['turn_damage_cooldown'] -= 1
                    plane['pos_x'] += plane['pre_hit_vx'] * 0.5 # Reduced speed
                    plane['pos_y'] += plane['pre_hit_vy'] * 0.5 # Reduced speed
                    plane['angle'] += 4 # Very Slow Spin
                    plane['angle'] %= 360
                else:
                    plane['state'] = 'chasing'
                    print(f"Plane {i} has stopped spinning.")
                continue

            target = self.planes[1 - i]
            
            if plane.get('disengage_timer', 0) > 0:
                plane['disengage_timer'] -= 1
                plane['state'] = 'disengaging'
            elif plane['state'] == 'disengaging':
                plane['state'] = 'chasing'

            if plane['missile_fire_cooldown'] > 0: plane['missile_fire_cooldown'] -= 1
            if plane['evade_timer'] > 0: plane['evade_timer'] -= 1

            plane_speed = plane['speed'] * self.plane_speed_scale

            if plane['state'] == 'disengaging':
                dx = plane['disengage_target_x'] - plane['pos_x']
                dy = plane['disengage_target_y'] - plane['pos_y']
                plane['target_angle'] = math.degrees(math.atan2(dy, dx))
                plane_speed = plane['speed'] * 1.8
            else:
                is_missile_threat = self.handle_missile_threats(plane, i)
                if is_missile_threat and plane['state'] != 'evading':
                    plane['state'] = 'evading'
                    plane['evade_timer'] = 90 
                elif plane['evade_timer'] <= 0 and plane['state'] == 'evading':
                    plane['state'] = 'chasing'

                if plane['state'] == 'evading':
                    plane['target_angle'] = plane['angle'] + 90 
                    plane_speed = plane['speed'] * 1.5 
                
                elif plane['state'] == 'chasing' and target['health'] > 0:
                    cautiousness = 1.0 - (plane['ammo'] / plane['max_ammo'])
                    dx = target['pos_x'] - plane['pos_x']
                    dy = target['pos_y'] - plane['pos_y']
                    dist = math.sqrt(dx**2 + dy**2) if math.sqrt(dx**2 + dy**2) > 0 else 0.1
                    
                    # Check if chaser is behind the target
                    target_heading_rad = math.radians(target['angle'])
                    target_heading_vec = (math.cos(target_heading_rad), math.sin(target_heading_rad))
                    
                    vec_to_chaser_x = plane['pos_x'] - target['pos_x']
                    vec_to_chaser_y = plane['pos_y'] - target['pos_y']
                    
                    if dist > 0:
                        norm_vec_to_chaser_x = vec_to_chaser_x / dist
                        norm_vec_to_chaser_y = vec_to_chaser_y / dist
                        dot_product = target_heading_vec[0] * norm_vec_to_chaser_x + target_heading_vec[1] * norm_vec_to_chaser_y
                    else:
                        dot_product = 0
                    
                    is_behind = dot_product < -0.7 # More strict check for being behind

                    lead_frames = dist / 15 
                    target_future_x = target['pos_x'] + target['vx'] * lead_frames
                    target_future_y = target['pos_y'] + target['vy'] * lead_frames
                    
                    target_future_x += random.uniform(-25, 25)
                    target_future_y += random.uniform(-25, 25)

                    lead_dx = target_future_x - plane['pos_x']
                    lead_dy = target_future_y - plane['pos_y']
                    
                    plane['target_angle'] = math.degrees(math.atan2(lead_dy, lead_dx))
                    
                    min_dist = 200 + (cautiousness * 200) 
                    if is_behind and dist < min_dist:
                        plane_speed = plane['speed'] * 0.6 # Slow down more if behind and close
                    elif dist < min_dist: 
                        plane_speed = plane['speed'] * 0.8
                    elif dist > 500: 
                        plane_speed = plane['speed'] * 1.2
                    
                    self.try_fire_missile(plane, target)

                else: 
                    plane_speed = plane['speed'] * 0.7

            angle_diff = (plane['target_angle'] - plane['angle'] + 180) % 360 - 180
            turn_amount = max(-plane['turn_rate'], min(plane['turn_rate'], angle_diff))
            
            plane['angle'] += turn_amount
            plane['angle'] %= 360

            margin = 100
            if (plane['pos_x'] < margin and plane['vx'] < 0) or \
                (plane['pos_x'] > self.screen_width - self.plane_size.width() - margin and plane['vx'] > 0) or \
                (plane['pos_y'] < margin and plane['vy'] < 0) or \
                (plane['pos_y'] > self.screen_height - self.plane_size.height() - margin and plane['vy'] > 0):
                
                center_x, center_y = self.screen_width / 2, self.screen_height / 2
                dx_center, dy_center = center_x - plane['pos_x'], center_y - plane['pos_y']
                plane['target_angle'] = math.degrees(math.atan2(dy_center, dx_center))

            health_percentage = max(0, plane['health'] / 30)
            damage_modifier = 0.7 + (0.3 * health_percentage)
            effective_speed = plane_speed * damage_modifier

            angle_rad = math.radians(plane['angle'])
            plane['vx'] = math.cos(angle_rad) * effective_speed
            plane['vy'] = math.sin(angle_rad) * effective_speed
            plane['pos_x'] += plane['vx']
            plane['pos_y'] += plane['vy']

            self._update_plane_pixmap(plane)

            # Prepare rotated pix for centroid computation
            transform = QTransform().translate(self.plane_size.width()/2, self.plane_size.height()/2).rotate(plane['angle']).translate(-self.plane_size.width()/2, -self.plane_size.height()/2)
            pix = plane['current_pixmap'].transformed(transform, Qt.SmoothTransformation)

            # Compute visual centroid of non-transparent pixels and offset the logical position so
            # the visual centroid stays locked to the plane's logical center.
            try:
                img = pix.toImage()
                w, h = img.width(), img.height()
                sx = sy = count = 0
                for yy in range(h):
                    for xx in range(w):
                        a = img.pixelColor(xx, yy).alpha()
                        if a > 16:
                            sx += xx; sy += yy; count += 1
                if count > 0:
                    cx = sx / count
                    cy = sy / count
                    # compute draw offsets so visual centroid matches logical center
                    draw_off_x = (self.plane_size.width() / 2) - cx
                    draw_off_y = (self.plane_size.height() / 2) - cy
                    plane['draw_offset_x'] = draw_off_x
                    plane['draw_offset_y'] = draw_off_y
                    if getattr(self, 'debug_measure_offsets', False):
                        # also print diagnostic info
                        logical_cx = plane['pos_x'] + (self.plane_size.width() / 2)
                        logical_cy = plane['pos_y'] + (self.plane_size.height() / 2)
                        visual_x = plane['pos_x'] + cx + plane.get('draw_offset_x', 0)
                        visual_y = plane['pos_y'] + cy + plane.get('draw_offset_y', 0)
                        dx = visual_x - logical_cx
                        dy = visual_y - logical_cy
                        dist = math.hypot(dx, dy)
                        print(f"Offset P{ i }: dx={dx:.1f}, dy={dy:.1f}, dist={dist:.1f}")
                else:
                    # keep logical top-left in pos_x/pos_y
                    pass
            except Exception:
                # already represented by plane['pos_x']/['pos_y']
                pass
            
            # Update debug markers: rotation center (green) and smoke-anchor center (blue)
            try:
                center_x = plane['pos_x'] + self.plane_size.width()/2
                center_y = plane['pos_y'] + self.plane_size.height()/2
                # rotation and smoke markers removed
            except Exception:
                pass
            num, size = 0, 0
            if plane['health'] < 9: num, size = 3, 12
            elif plane['health'] < 17: num, size = 2, 8
            elif plane['health'] < 27: num, size = 1, 5
            
            if num > 0:
                center_x, center_y = self.plane_size.width()/2, self.plane_size.height()/2
                angle_rad = math.radians(plane['angle'])
                for k in range(num):
                    # spawn smoke slightly behind the plane center so trail appears behind
                    local_x = -12
                    local_y = 0
                    # compute rotated spawn position for initial placement
                    rotated_relative_x = local_x * math.cos(angle_rad) - local_y * math.sin(angle_rad)
                    rotated_relative_y = local_x * math.sin(angle_rad) + local_y * math.cos(angle_rad)
                    spawn_x = center_x + plane['pos_x'] + rotated_relative_x
                    spawn_y = center_y + plane['pos_y'] + rotated_relative_y
                    smoke_vx = -plane['vx'] * 0.2 + random.uniform(-0.2, 0.2)
                    smoke_vy = -plane['vy'] * 0.2 + random.uniform(-0.2, 0.2)
                    smoke = {'pos_x': spawn_x, 'pos_y': spawn_y, 'vx': 0.0, 'vy': 0.0, 'drift_vx': smoke_vx, 'drift_vy': smoke_vy, 'drift_offset_x': 0.0, 'drift_offset_y': 0.0, 'size': size, 'opacity': 0.8, 'lifetime': 60, 'frame': 0, 'type': 'smoke', 'attached_to': i, 'local_x': local_x, 'local_y': local_y, 'attached_time': 12}
                    if len(self.smoke_particles) < self.max_smoke_particles:
                        self.smoke_particles.append(smoke)

    def update_projectiles(self):
        to_remove = []
        for p in self.projectiles:
            p['pos_x'] += p['vx']; p['pos_y'] += p['vy']; p['frame'] += 1

            # Collision check using bounding boxes (avoid QWidget geometry)
            pw = self.plane_size.width(); ph = self.plane_size.height()
            pw2 = p['base_pixmap'].width() if 'base_pixmap' in p else 8
            ph2 = p['base_pixmap'].height() if 'base_pixmap' in p else 8
            p_left = p['pos_x'] - pw2/2; p_right = p['pos_x'] + pw2/2
            p_top = p['pos_y'] - ph2/2; p_bottom = p['pos_y'] + ph2/2
            for j, plane in enumerate(self.planes):
                if plane['health'] <= 0 or j == p['shooter_index']: continue
                plane_left = plane['pos_x']; plane_top = plane['pos_y']
                plane_right = plane_left + pw; plane_bottom = plane_top + ph
                if (p_left < plane_right and p_right > plane_left and p_top < plane_bottom and p_bottom > plane_top):
                    plane['health'] -= 1
                    if random.random() < 0.1 and plane.get('turn_direction_lost') is None: # 10% chance
                        direction = random.choice(['left', 'right'])
                        plane['turn_direction_lost'] = direction
                        plane['turn_damage_cooldown'] = 240 # 4 seconds
                        print(f"Plane {j} has lost the ability to turn {direction} for 4 seconds!")
                    if p not in to_remove: to_remove.append(p)
                    for _ in range(3): plane['damage_points'].append(QPoint(random.randint(20, self.plane_size.width() - 20), random.randint(20, self.plane_size.height() - 20)))
                    if plane['health'] <= 0:
                        self.create_plane_explosion(plane)
                    break

            if not (-10 < p['pos_x'] < self.screen_width and -10 < p['pos_y'] < self.screen_height):
                if p not in to_remove:
                    to_remove.append(p)

        for p in to_remove:
            if p in self.projectiles:
                self.projectiles.remove(p)

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
                    smoke = {'pos_x': m['pos_x']+random.uniform(-2,2), 'pos_y': m['pos_y']+random.uniform(-2,2), 'vx': -m['vx']*0.1, 'vy': -m['vy']*0.1, 'size': 4, 'opacity': 0.7, 'lifetime': 30, 'frame': 0, 'type': 'smoke'}
                    self.smoke_particles.append(smoke)
            transform = QTransform().translate(self.missile_base_size/2, self.missile_base_size/2).rotate(m['angle']+90).translate(-self.missile_base_size/2, -self.missile_base_size/2)
            # missile drawing handled in paintEvent; no QLabel updates here
            
            collided = self.check_missile_collision(m)
            if collided:
                for c in collided:
                    if c not in to_remove:
                        to_remove.append(c)

            if not (-50 < m['pos_x'] < self.screen_width+50 and -50 < m['pos_y'] < self.screen_height+50) or m['frame'] > 270:
                if m not in to_remove:
                    to_remove.append(m)
        
        for m in to_remove:
            if m in self.missiles:
                self.create_explosion(m['pos_x'], m['pos_y'])
                self.missiles.remove(m)

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
            # Flares are only deployed automatically in an active game
            if self.game_state == 'ACTIVE' and math.sqrt((tx - missile['pos_x'])**2 + (ty - missile['pos_y'])**2) < 400 and target_plane['flare_cooldown'] == 0 and target_plane['flares_left'] > 0 and random.random() < 0.5:
                target_plane['flares_left'] -= 1
                target_plane['is_deploying_flares'], target_plane['flare_deployment_counter'], target_plane['flare_cooldown'] = True, 16, 180
            return tx, ty
        return 0, 0

    def check_missile_collision(self, missile):
        destroyed = []
        # missile-on-missile collision via bbox
        if (tm := missile.get('target_missile')) and tm in self.missiles:
            mw = missile['base_pixmap'].width(); mh = missile['base_pixmap'].height()
            tmw = tm['base_pixmap'].width(); tmh = tm['base_pixmap'].height()
            if (missile['pos_x'] - mw/2 < tm['pos_x'] + tmw/2 and missile['pos_x'] + mw/2 > tm['pos_x'] - tmw/2 and
                missile['pos_y'] - mh/2 < tm['pos_y'] + tmh/2 and missile['pos_y'] + mh/2 > tm['pos_y'] - tmh/2):
                print("Missile-on-missile impact!")
                destroyed.extend([missile, tm])
        elif not missile.get('target_flare'):
            target_plane = self.planes[missile['target_index']]
            if target_plane['health'] > 0:
                mw = missile['base_pixmap'].width(); mh = missile['base_pixmap'].height()
                plane_left = target_plane['pos_x']; plane_top = target_plane['pos_y']
                plane_right = plane_left + self.plane_size.width(); plane_bottom = plane_top + self.plane_size.height()
                if (missile['pos_x'] - mw/2 < plane_right and missile['pos_x'] + mw/2 > plane_left and
                    missile['pos_y'] - mh/2 < plane_bottom and missile['pos_y'] + mh/2 > plane_top):
                    target_plane['health'] -= 5
                    if random.random() < 0.5 and target_plane.get('state') != 'spinning': # 50% chance
                        target_plane['state'] = 'spinning'
                        target_plane['pre_hit_vx'] = target_plane['vx']
                        target_plane['pre_hit_vy'] = target_plane['vy']
                        target_plane['turn_damage_cooldown'] = 120 # 2 seconds
                        print(f"Plane {missile['target_index']} is spinning for 2 seconds due to missile hit!")
                    destroyed.append(missile)
                    if target_plane['health'] <= 0:
                        self.create_plane_explosion(target_plane)
        return destroyed

    def update_effects(self):
        for group in [self.smoke_particles, self.flares, self.explosions]:
            to_remove = []
            for item in group:
                item['frame'] += 1
                if item['frame'] >= item['lifetime']: to_remove.append(item); continue
                item['opacity'] = 1.0 - (item['frame'] / item['lifetime'])
                if group == self.smoke_particles:
                    # If particle is attached to a plane, compute anchored position using that plane's current angle
                    attached_idx = item.get('attached_to')
                    if attached_idx is not None and 0 <= attached_idx < len(self.planes):
                        plane = self.planes[attached_idx]
                        if plane.get('health', 0) > 0:
                            # If still within attached_time, anchor to a local offset on the plane
                            at = item.get('attached_time', 0)
                            center_x = plane['pos_x'] + self.plane_size.width()/2
                            center_y = plane['pos_y'] + self.plane_size.height()/2
                            angle_rad = math.radians(plane['angle'])
                            lx = item.get('local_x', 0)
                            ly = item.get('local_y', 0)
                            rotated_x = lx * math.cos(angle_rad) - ly * math.sin(angle_rad)
                            rotated_y = lx * math.sin(angle_rad) + ly * math.cos(angle_rad)
                            if at > 0:
                                item['attached_time'] = at - 1
                                # accumulate drift velocity into an offset so the smoke will trail
                                dvx = item.get('drift_vx', 0.0) + random.uniform(-0.01, 0.01)
                                dvy = item.get('drift_vy', 0.0) + random.uniform(-0.01, 0.01)
                                item['drift_vx'] = dvx
                                item['drift_vy'] = dvy
                                item['drift_offset_x'] = item.get('drift_offset_x', 0.0) + dvx
                                item['drift_offset_y'] = item.get('drift_offset_y', 0.0) + dvy
                                item['pos_x'] = center_x + rotated_x + item.get('drift_offset_x', 0.0)
                                item['pos_y'] = center_y + rotated_y + item.get('drift_offset_y', 0.0)
                            else:
                                # detach: give it a velocity based on accumulated drift so it moves away and forms a trail
                                item['attached_to'] = None
                                item['vx'] = item.get('drift_vx', 0.0) + plane.get('vx', 0.0) * 0.2 + random.uniform(-0.1, 0.1)
                                item['vy'] = item.get('drift_vy', 0.0) + plane.get('vy', 0.0) * 0.2 + random.uniform(-0.1, 0.1)
                                item['pos_x'] += item['vx']; item['pos_y'] += item['vy']
                        else:
                            # plane is dead - detach immediately and let particle drift
                            item['attached_to'] = None
                            item['vx'] = item.get('drift_vx', 0.0) + random.uniform(-0.1, 0.1)
                            item['vy'] = item.get('drift_vy', 0.0) + random.uniform(-0.1, 0.1)
                            item['pos_x'] += item['vx']; item['pos_y'] += item['vy']
                    else:
                        item['pos_x'] += item.get('vx', 0)
                        item['pos_y'] += item.get('vy', 0)

                    is_flare_smoke = False
                    if item.get('type') == 'debris':
                        color = item['color']
                        item['vy'] += 0.05 # Gravity
                    elif item.get('type') == 'flare_smoke':
                        color, is_flare_smoke = QColor(255, 255, 0), True
                    else:
                        color = QColor(80, 80, 80) # default smoke color
                        progress = item['frame'] / item['lifetime']
                        if progress < 0.15:
                            color = QColor(255, int(165 * (1 - (progress/0.15)) + 255 * (progress/0.15)), 0)
                        elif progress < 0.5:
                            stage_progress = (progress - 0.15) / 0.35
                            color = QColor(int(255 * (1 - stage_progress) + 80 * stage_progress), int(255 * (1 - stage_progress) + 80 * stage_progress), int(0 * (1 - stage_progress) + 80 * stage_progress))
                    
                    item['render_color'] = color

                elif group == self.flares:
                    item['pos_x'] += item['vx']; item['pos_y'] += item['vy']
                    if item['frame'] % 3 == 0:
                        smoke = {'pos_x': item['pos_x'], 'pos_y': item['pos_y'], 'vx': random.uniform(-0.5,0.5), 'vy': random.uniform(-0.5,0.5), 'size': 10, 'opacity': 0.8, 'lifetime': 40, 'frame': 0, 'type': 'flare_smoke'}
                        self.smoke_particles.append(smoke)
                    item['render_color'] = QColor(255,255,0)
                elif group == self.explosions:
                    item['size'] = 20 + (item['max_size'] - 20) * (item['frame']/item['lifetime'])
                    item['render_color'] = item.get('color', QColor(255,165,0))

            for item in to_remove:
                if item in group: group.remove(item)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        # Draw explosions first (behind)
        for item in list(self.explosions):
            size = item.get('size', 10)
            opacity = item.get('opacity', 1.0)
            color = item.get('render_color', item.get('color', QColor(255,165,0)))
            pm = self.create_particle_pixmap(size, opacity, color)
            painter.drawPixmap(int(item['pos_x'] - size/2), int(item['pos_y'] - size/2), pm)

        # Draw smoke and flare smoke
        for item in list(self.smoke_particles):
            size = item.get('size', 6)
            opacity = item.get('opacity', 1.0)
            color = item.get('render_color', QColor(100,100,100))
            is_flare_smoke = (item.get('type') == 'flare_smoke')
            pm = self.create_particle_pixmap(size, opacity, color, is_flare=is_flare_smoke, is_flare_smoke=is_flare_smoke)
            painter.drawPixmap(int(item['pos_x'] - size/2), int(item['pos_y'] - size/2), pm)

        # Draw flares (bright)
        for item in list(self.flares):
            size = item.get('size', 10)
            opacity = item.get('opacity', 1.0)
            color = item.get('render_color', QColor(255,255,0))
            pm = self.create_particle_pixmap(size, opacity, color, is_flare=True)
            painter.drawPixmap(int(item['pos_x'] - size/2), int(item['pos_y'] - size/2), pm)

        # Draw projectiles (bullets)
        for p in list(self.projectiles):
            pm = p.get('base_pixmap', self.projectile_pixmap)
            ang = p.get('angle', 0)
            if ang:
                transform = QTransform().translate(pm.width()/2, pm.height()/2).rotate(ang).translate(-pm.width()/2, -pm.height()/2)
                drawn = pm.transformed(transform, Qt.SmoothTransformation)
            else:
                drawn = pm
            painter.drawPixmap(int(p['pos_x'] - drawn.width()/2), int(p['pos_y'] - drawn.height()/2), drawn)

        # Draw missiles
        for m in list(self.missiles):
            pm = m.get('base_pixmap', self.missile_pixmap)
            ang = m.get('angle', 0) + 90
            transform = QTransform().translate(pm.width()/2, pm.height()/2).rotate(ang).translate(-pm.width()/2, -pm.height()/2)
            drawn = pm.transformed(transform, Qt.SmoothTransformation)
            painter.drawPixmap(int(m['pos_x'] - drawn.width()/2), int(m['pos_y'] - drawn.height()/2), drawn)

        # Draw planes on top using rotated-pixmap + centroid cache
        for idx, plane in enumerate(self.planes):
            if not plane.get('visible', True):
                continue
            base_pm = plane.get('current_pixmap', plane.get('base_pixmap'))
            if base_pm is None:
                continue
            # get cached rotated pixmap and draw offsets for a quantized angle
            rot_pm, off_x, off_y = self._get_rotated_pixmap_and_offset(base_pm, plane.get('angle', 0))
            draw_x = int(plane['pos_x'] + off_x)
            draw_y = int(plane['pos_y'] + off_y)
            painter.drawPixmap(draw_x, draw_y, rot_pm)

        painter.end()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    # Create a single window that spans all available screens
    all_screens_geometry = QRect()
    for screen in app.screens():
        all_screens_geometry = all_screens_geometry.united(screen.geometry())

    # If no screen geometry is found, fall back to the primary screen
    if all_screens_geometry.isNull():
        all_screens_geometry = app.primaryScreen().geometry()

    window = PlaneAnimation(all_screens_geometry)
    
    sys.exit(app.exec_())