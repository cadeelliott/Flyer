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
        self.shoot_interval = 2

        self.show_hud = False
        self.hud_labels = []
        self.init_hud()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_position)
        self.timer.start(16)
        
        self.show()
        self.raise_()
        print("--- Initialization Complete. Window Shown. ---")

    def load_plane_pixmap(self, fighter_name):
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            image_path = os.path.join(script_dir, f"{fighter_name}.png")
            if os.path.exists(image_path):
                pixmap = QPixmap(image_path)
                if not pixmap.isNull():
                    # Standardize size before padding
                    pixmap = pixmap.scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    padding = 20
                    padded = QPixmap(pixmap.width() + 2 * padding, pixmap.height() + 2 * padding)
                    padded.fill(Qt.transparent)
                    painter = QPainter(padded); painter.drawPixmap(padding, padding, pixmap); painter.end()
                    return padded
        except Exception as e: print(f"Error loading plane image {fighter_name}: {e}")
        return self.create_fallback_image(Qt.red)

    def init_planes(self):
        self.planes = [
            {'label': QLabel(self), 'base_pixmap': self.plane1_pixmap, 'pixmap': self.plane1_pixmap.copy(), 'pos_x': 0, 'pos_y': self.screen_height//3, 'y_target': self.screen_height//3, 'speed': 3, 'base_speed': 3, 'change_y_counter': 0, 'prev_pos_x': 0, 'prev_pos_y': self.screen_height//3, 'health': 30, 'direction': 1, 'vy': 0, 'angle': 0, 'flare_cooldown': 0, 'flares_left': 2, 'missiles_left': 4, 'missile_fire_cooldown': 0, 'is_deploying_flares': False, 'flare_deployment_counter': 0, 'damage_points': [], 'state': 'maneuvering', 'speed_multiplier': 1.0, 'evade_timer': 0, 'maneuver_timer': 0, 'disengage_timer': 0, 'disengage_cooldown': 0, 'current_maneuver': 'lag_pursuit', 'actual_vx': 3, 'afterburner_fuel': 100, 'max_afterburner_fuel': 100},
            {'label': QLabel(self), 'base_pixmap': self.plane2_pixmap, 'pixmap': self.plane2_pixmap.copy(), 'pos_x': self.screen_width - self.plane_size.width(), 'pos_y': self.screen_height*2//3, 'y_target': self.screen_height*2//3, 'speed': -3, 'base_speed': 3, 'change_y_counter': 0, 'prev_pos_x': self.screen_width - self.plane_size.width(), 'prev_pos_y': self.screen_height*2//3, 'health': 30, 'direction': -1, 'vy': 0, 'angle': 0, 'flare_cooldown': 0, 'flares_left': 2, 'missiles_left': 4, 'missile_fire_cooldown': 0, 'is_deploying_flares': False, 'flare_deployment_counter': 0, 'damage_points': [], 'state': 'maneuvering', 'speed_multiplier': 1.0, 'evade_timer': 0, 'maneuver_timer': 0, 'disengage_timer': 0, 'disengage_cooldown': 0, 'current_maneuver': 'lag_pursuit', 'actual_vx': -3, 'afterburner_fuel': 100, 'max_afterburner_fuel': 100}
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

    def init_hud(self):
        # HUD for Plane 1 (Left)
        self.hud_left = QLabel(self)
        self.hud_left.setGeometry(10, 10, 250, 120)
        self.hud_left.setStyleSheet("color: white; background-color: rgba(0, 0, 0, 100); border-radius: 5px; padding: 5px; font-family: 'Lucida Console', Monaco, monospace;")
        self.hud_left.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.hud_left.setVisible(self.show_hud)
        self.hud_labels.append(self.hud_left)

        # HUD for Plane 2 (Right)
        self.hud_right = QLabel(self)
        self.hud_right.setGeometry(self.screen_width - 260, 10, 250, 120)
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
        fuel_bar1 = "█" * int(plane1.get('afterburner_fuel', 0) / 10) + " " * (10 - int(plane1.get('afterburner_fuel', 0) / 10))
        hud1_text = (
            f"<b>Left Wing</b><br>"
            f"Health: [{health_bar1}]<br>"
            f"Missiles: {plane1.get('missiles_left', 0)}<br>"
            f"Flares: {plane1.get('flares_left', 0)}<br>"
            f"Fuel:   [{fuel_bar1}]<br>"
            f"State: <i>{plane1.get('state', 'N/A').replace('_', ' ').title()}</i>"
        )
        self.hud_left.setText(hud1_text)

        # HUD for Plane 2 (Right)
        plane2 = self.planes[1]
        health_bar2 = "█" * int(plane2['health'] / 3) + " " * (10 - int(plane2['health'] / 3))
        fuel_bar2 = "█" * int(plane2.get('afterburner_fuel', 0) / 10) + " " * (10 - int(plane2.get('afterburner_fuel', 0) / 10))
        hud2_text = (
            f"<div align='right'><b>Right Wing</b><br>"
            f"[{health_bar2}] :Health<br>"
            f"{plane2.get('missiles_left', 0)} :Missiles<br>"
            f"{plane2.get('flares_left', 0)} :Flares<br>"
            f"[{fuel_bar2}] :Fuel<br>"
            f"<i>{plane2.get('state', 'N/A').replace('_', ' ').title()}</i> :State</div>"
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
                
                damaged_pixmap = self.winner['base_pixmap'].copy()
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
        for plane in self.planes:
            if plane['flare_cooldown'] > 0: plane['flare_cooldown'] -= 1
            if plane['is_deploying_flares'] and plane['flare_deployment_counter'] > 0 and plane['flare_deployment_counter'] % 2 == 0:
                flare = {'label': QLabel(self), 'pos_x': plane['pos_x'] + self.plane_size.width()/2, 'pos_y': plane['pos_y'] + self.plane_size.height()/2, 'vx': random.uniform(-2, 2) - plane['direction']*2, 'vy': random.uniform(-2, 2), 'size': 15, 'opacity': 1.0, 'lifetime': 90, 'frame': 0}
                flare['label'].setPixmap(self.create_particle_pixmap(flare['size'], flare['opacity'], QColor(255, 255, 0))); flare['label'].resize(flare['label'].pixmap().size()); flare['label'].show(); self.flares.append(flare)
            if plane['is_deploying_flares']: plane['flare_deployment_counter'] -= 1
            if plane['flare_deployment_counter'] <= 0: plane['is_deploying_flares'] = False

    def fire_projectiles(self):
        for i, plane in enumerate(self.planes):
            if plane['health'] <= 0: continue
            target = self.planes[1 - i]
            if target['health'] > 0:
                # --- Calculate Intercept Point ---
                projectile_speed = 8.0
                
                target_vx = target['pos_x'] - target['prev_pos_x']
                target_vy = target['pos_y'] - target['prev_pos_y']

                dx_initial = target['pos_x'] - plane['pos_x']
                dy_initial = target['pos_y'] - plane['pos_y']
                dist_initial = math.sqrt(dx_initial**2 + dy_initial**2)

                if dist_initial == 0: continue

                time_to_hit = dist_initial / projectile_speed

                predicted_x = target['pos_x'] + target_vx * time_to_hit
                predicted_y = target['pos_y'] + target_vy * time_to_hit

                dx = predicted_x - plane['pos_x']
                dy = predicted_y - plane['pos_y']
                dist = math.sqrt(dx**2 + dy**2)
                # --- End Intercept Calculation ---

                # Define engagement envelope for guns
                if not (50 < dist < 600):
                    continue

                target_angle = math.degrees(math.atan2(dy, dx))
                angle_diff = abs((target_angle - plane['angle'] + 180) % 360 - 180)
                if angle_diff > 10: # Widen angle slightly for leading shots
                    continue

                if dist > 1:
                    dx, dy = dx/dist, dy/dist
                    spawn_x, spawn_y = plane['pos_x'] + self.plane_size.width()/2, plane['pos_y'] + self.plane_size.height()/2
                    proj = {'label': QLabel(self), 'base_pixmap': self.projectile_pixmap, 'pos_x': spawn_x, 'pos_y': spawn_y, 'vx': dx*projectile_speed, 'vy': dy*projectile_speed, 'frame': 0, 'shooter_index': i, 'angle': math.degrees(math.atan2(dy, dx))}
                    proj['label'].setPixmap(proj['base_pixmap']); proj['label'].resize(proj['base_pixmap'].size()); proj['label'].show(); self.projectiles.append(proj)

    def try_fire_missile(self, plane, target):
        if plane.get('missiles_left', 0) <= 0 or plane.get('missile_fire_cooldown', 0) > 0:
            return False

        dx, dy = target['pos_x'] - plane['pos_x'], target['pos_y'] - plane['pos_y']
        dist = math.sqrt(dx**2 + dy**2)
        angle_to_target = math.degrees(math.atan2(dy, dx))
        angle_diff = abs((angle_to_target - plane['angle'] + 180) % 360 - 180)

        # Check missile engagement envelope (min range and angle)
        if angle_diff < 20 and dist > 200:
            plane['missiles_left'] -= 1
            plane['missile_fire_cooldown'] = 120 # 2 second cooldown between missile launches

            spawn_x, spawn_y = plane['pos_x'] + self.plane_size.width()/2, plane['pos_y'] + self.plane_size.height()/2
            if dist > 1: dx, dy = dx/dist, dy/dist
            missile = {'label': QLabel(self), 'base_pixmap': self.missile_pixmap, 'pos_x': spawn_x, 'pos_y': spawn_y, 'vx': dx*self.missile_speed, 'vy': dy*self.missile_speed, 'angle': math.degrees(math.atan2(dy, dx)), 'shooter_index': self.planes.index(plane), 'target_index': self.planes.index(target), 'frame': 0, 'target_flare': None, 'target_missile': None}
            missile['label'].setPixmap(missile['base_pixmap']); missile['label'].resize(missile['base_pixmap'].size()); missile['label'].show(); self.missiles.append(missile)
            return True
        return False

    def handle_missile_threats(self, plane, plane_idx):
        # Checks for and reacts to immediate missile threats.
        # Returns True if a threat was handled, False otherwise.
        for missile in self.missiles:
            if missile['target_index'] == plane_idx and not missile.get('target_flare'):
                if math.sqrt((missile['pos_x'] - plane['pos_x'])**2 + (missile['pos_y'] - plane['pos_y'])**2) < 450:
                    # Evade missile by moving perpendicular to its path, with some randomness
                    plane['y_target'] = plane['pos_y'] + (300 if missile['vy'] < 0 else -300) + random.uniform(-50, 50)
                    plane['speed_multiplier'] = 1.6 # Use afterburner to dodge
                    return True
        return False

    def is_projectile_threat(self, plane, plane_idx):
        for proj in self.projectiles:
            if proj['shooter_index'] == plane_idx:
                continue

            proj_dx = proj['pos_x'] - plane['pos_x']
            
            # Only check for collision if projectile is somewhat relevant.
            if abs(proj_dx) > 500 or abs(proj['pos_y'] - plane['pos_y']) > 300:
                continue

            # Predictive check using relative velocity
            relative_vx = proj['vx'] - plane['actual_vx']
            if relative_vx == 0: continue
            
            time_to_impact = proj_dx / relative_vx
            
            if 0 < time_to_impact < 50: # Generous 50-frame window
                future_proj_y = proj['pos_y'] + proj['vy'] * time_to_impact
                future_plane_y = plane['pos_y'] + plane['vy'] * time_to_impact
                
                if abs(future_proj_y - future_plane_y) < 75: # Wider collision box
                    # Store the threat for the state machine to use
                    plane['projectile_threat'] = proj 
                    return True
        
        plane['projectile_threat'] = None
        return False

    def get_plane_state(self, plane, target):
        # If we are currently disengaging, check the timer.
        if plane.get('state') == 'disengaging':
            if plane.get('disengage_timer', 0) > 0:
                return 'disengaging' # Continue disengaging
            else:
                # Timer is up, force re-engagement and start cooldown
                plane['disengage_cooldown'] = 480 # 8 second cooldown
                return 'maneuvering'

        # If health is low and not on cooldown, start disengaging
        if plane['health'] < 10 and plane.get('disengage_cooldown', 0) <= 0 and plane.get('state') != 'attacking':
             return 'start_disengage'
        
        dist = math.sqrt((target['pos_x'] - plane['pos_x'])**2 + (target['pos_y'] - plane['pos_y'])**2)
        
        # Is target on my tail?
        angle_to_me = math.degrees(math.atan2(plane['pos_y'] - target['pos_y'], plane['pos_x'] - target['pos_x']))
        target_angle_diff = abs((angle_to_me - target['angle'] + 180) % 360 - 180)
        is_target_behind_me = (plane['pos_x'] - target['pos_x']) * plane['direction'] > 0

        # Am I on target's tail?
        angle_to_target = math.degrees(math.atan2(target['pos_y'] - plane['pos_y'], target['pos_x'] - plane['pos_x']))
        my_angle_diff = abs((angle_to_target - plane['angle'] + 180) % 360 - 180)
        am_i_behind_target = (target['pos_x'] - plane['pos_x']) * target['direction'] > 0

        if is_target_behind_me and dist < 400 and target_angle_diff < 45:
            return 'evading_plane'

        if am_i_behind_target and dist < 600 and my_angle_diff < 45:
            return 'attacking'

        return 'maneuvering'

    def update_planes(self):
        for i, plane in enumerate(self.planes):
            if plane['health'] <= 0: continue

            if plane.get('missile_fire_cooldown', 0) > 0:
                plane['missile_fire_cooldown'] -= 1
            if plane.get('disengage_timer', 0) > 0:
                plane['disengage_timer'] -= 1
            if plane.get('disengage_cooldown', 0) > 0:
                plane['disengage_cooldown'] -= 1

            # --- Wall Collision Override ---
            margin = 20 
            if (plane['pos_x'] > self.screen_width - self.plane_size.width() - margin and plane['direction'] == 1):
                plane['direction'] = -1
                plane['speed'] = plane['base_speed'] * plane['direction']
                plane['maneuver_timer'] = 0
            elif (plane['pos_x'] < margin and plane['direction'] == -1):
                plane['direction'] = 1
                plane['speed'] = plane['base_speed'] * plane['direction']
                plane['maneuver_timer'] = 0

            target = self.planes[1 - i]
            
            current_multiplier = plane.get('speed_multiplier', 1.0)
            plane['speed_multiplier'] = current_multiplier + (1.0 - current_multiplier) * 0.05

            # --- Threat Evasion Logic ---
            threat_handled = False
            
            is_dodging_projectile = self.is_projectile_threat(plane, i)
            if is_dodging_projectile:
                plane['state'] = 'evading_projectile'
                plane['evade_timer'] = 20
            
            if plane.get('evade_timer', 0) > 0 and plane.get('state') == 'evading_projectile':
                plane['evade_timer'] -= 1
                threatening_proj = plane.get('projectile_threat')
                if threatening_proj:
                    relative_vy = threatening_proj['vy'] - plane['vy']
                    plane['y_target'] = plane['pos_y'] + (300 if relative_vy > 0 else -300)
                plane['speed_multiplier'] = 1.8
                threat_handled = True
            
            if not threat_handled:
                threat_handled = self.handle_missile_threats(plane, i)

            # --- Main AI State Machine ---
            if not threat_handled and target['health'] > 0:
                state = self.get_plane_state(plane, target)
                
                if state == 'start_disengage':
                    plane['disengage_timer'] = random.randint(120, 240)
                    state = 'disengaging'

                plane['state'] = state

                if state == 'disengaging':
                    plane['speed_multiplier'] = 2.0
                    corner_x = 0 if target['pos_x'] > self.screen_width / 2 else self.screen_width
                    corner_y = 0 if target['pos_y'] > self.screen_height / 2 else self.screen_height
                    
                    target_dx = corner_x - plane['pos_x']
                    
                    if target_dx > 0: plane['direction'] = 1
                    else: plane['direction'] = -1
                    plane['speed'] = plane['base_speed'] * plane['direction']
                    
                    plane['y_target'] = corner_y

                elif state == 'evading_plane':
                    if plane['evade_timer'] <= 0:
                        plane['evade_decision'] = random.choice(['break_burn_up', 'break_burn_down', 'break_cut_up', 'break_cut_down', 'jink', 'high_g_reversal'])
                        plane['evade_timer'] = random.randint(60, 90)
                        if plane['evade_decision'] == 'high_g_reversal':
                            plane['evade_timer'] = 75 # Fixed time for this maneuver
                        
                        if plane['flare_cooldown'] == 0 and plane['flares_left'] > 0 and random.random() < 0.4:
                            plane['flares_left'] -= 1
                            plane['is_deploying_flares'] = True
                            plane['flare_deployment_counter'] = 16
                            plane['flare_cooldown'] = 180

                    plane['evade_timer'] -= 1
                    decision = plane.get('evade_decision', 'jink')

                    if decision == 'high_g_reversal':
                        plane['speed_multiplier'] = 0.3 # Drastically cut speed
                        # Start a sharp climb or dive away from the attacker
                        if plane['evade_timer'] == 74: # First frame of maneuver
                            plane['y_target'] = plane['pos_y'] + (500 if target['pos_y'] > plane['pos_y'] else -500)
                        
                        # At the apex of the turn, reverse direction
                        if plane['evade_timer'] == 45:
                            plane['direction'] *= -1
                            plane['speed'] = plane['base_speed'] * plane['direction']
                    elif 'burn' in decision: plane['speed_multiplier'] = 1.8
                    elif 'cut' in decision: plane['speed_multiplier'] = 0.5

                    if 'up' in decision: plane['y_target'] = plane['pos_y'] - 400
                    elif 'down' in decision: plane['y_target'] = plane['pos_y'] + 400
                    
                    if decision == 'jink':
                        if plane['evade_timer'] % 15 == 0:
                             plane['y_target'] = plane['pos_y'] + random.uniform(-200, 200)

                elif state == 'attacking':
                    self.try_fire_missile(plane, target)
                    plane['y_target'] = target['pos_y'] + random.uniform(-20, 20)
                    dist = math.sqrt((target['pos_x'] - plane['pos_x'])**2 + (target['pos_y'] - plane['pos_y'])**2)
                    
                    follow_dist = plane.get('follow_dist', 250)
                    if random.random() < 0.02:
                        plane['follow_dist'] = random.uniform(200, 300)

                    if dist > follow_dist + 50: plane['speed_multiplier'] = 1.4
                    elif dist < follow_dist - 50: plane['speed_multiplier'] = 0.8
                    else: plane['speed_multiplier'] = 1.1

                elif state == 'maneuvering':
                    dist = math.sqrt((target['pos_x'] - plane['pos_x'])**2 + (target['pos_y'] - plane['pos_y'])**2)
                    if dist > 600:
                        self.try_fire_missile(plane, target)

                    plane['maneuver_timer'] = plane.get('maneuver_timer', 0) - 1
                    if plane['maneuver_timer'] <= 0:
                        plane['arc_direction'] = None # Reset arc direction
                        plane['current_maneuver'] = random.choice(['lag_pursuit', 'lag_pursuit', 'low_yo_yo', 'high_yo_yo', 'extend_and_run', 'wide_arc'])
                        plane['maneuver_timer'] = random.randint(120, 240) # Longer maneuvers
                        plane['maneuver_rand_val'] = random.uniform(250, 400)

                    maneuver = plane.get('current_maneuver', 'lag_pursuit')
                    rand_val = plane.get('maneuver_rand_val', 300)

                    if maneuver == 'lag_pursuit':
                        # --- Lag Pursuit Logic ---
                        # Aim for a control point behind the target to get a good attack angle.
                        control_point_x = target['pos_x'] - (target['direction'] * rand_val)
                        control_point_y = target['pos_y']
                        plane['y_target'] = control_point_y

                        dist_to_control_point = abs(plane['pos_x'] - control_point_x)
                        is_facing_control_point = (control_point_x - plane['pos_x']) * plane['direction'] > 0

                        if not is_facing_control_point and dist_to_control_point > 150:
                            # If we are facing the wrong way and are far, we must turn.
                            plane['speed_multiplier'] = 1.9 
                            plane['direction'] *= -1
                            plane['speed'] = plane['base_speed'] * plane['direction']
                            plane['maneuver_timer'] = 45 # Commit to the turn
                        else:
                            # Facing the right way, or close enough not to matter.
                            if dist_to_control_point > 100:
                                plane['speed_multiplier'] = 1.8 # Burn to catch up
                            else:
                                plane['speed_multiplier'] = 1.2 # Pace the target
                    
                    elif maneuver == 'high_yo_yo':
                        plane['y_target'] = target['pos_y'] - rand_val
                        plane['speed_multiplier'] = 0.8

                    elif maneuver == 'low_yo_yo':
                        plane['y_target'] = target['pos_y'] + rand_val
                        plane['speed_multiplier'] = 1.9

                    elif maneuver == 'extend_and_run':
                        # Fly straight towards the screen edge plane is facing
                        plane['y_target'] = plane['pos_y'] # Maintain altitude
                        plane['speed_multiplier'] = 1.9 # Full afterburner
                        # Let wall collision logic handle the turn

                    elif maneuver == 'wide_arc':
                        # Fly in a large arc across the screen
                        if plane.get('arc_direction') is None:
                            plane['arc_direction'] = 'up' if plane['pos_y'] > self.screen_height / 2 else 'down'
                        
                        if plane['arc_direction'] == 'up':
                            plane['y_target'] = 50 # Target near top of screen
                        else:
                            plane['y_target'] = self.screen_height - 150 # Target near bottom
                        
                        plane['speed_multiplier'] = 1.3 # Steady speed for a smooth arc
            
            # --- Afterburner and Fuel Management ---
            if plane['speed_multiplier'] > 1.0:
                if plane.get('afterburner_fuel', 0) > 0:
                    plane['afterburner_fuel'] -= 1.5  # Fuel consumption rate
                else:
                    plane['speed_multiplier'] = 1.0 # Out of fuel
            else:
                if plane.get('afterburner_fuel', 100) < plane.get('max_afterburner_fuel', 100):
                    plane['afterburner_fuel'] += 0.3  # Fuel regeneration rate
            
            # --- Physics and Position Update ---
            health_percentage = max(0, plane['health']/30)
            damage_modifier = 0.6 + (0.4 * health_percentage)
            
            target_vx = plane['speed'] * damage_modifier * plane['speed_multiplier']
            current_vx = plane.get('actual_vx', target_vx)
            turn_factor = 0.05 
            plane['actual_vx'] = current_vx + (target_vx - current_vx) * turn_factor
            
            plane['prev_pos_x'], plane['prev_pos_y'] = plane['pos_x'], plane['pos_y']
            plane['pos_x'] += plane['actual_vx']
            
            vertical_acceleration = 0.15; max_vertical_speed = 5
            if plane['y_target'] > plane['pos_y']: plane['vy'] += vertical_acceleration
            else: plane['vy'] -= vertical_acceleration
            plane['vy'] = max(-max_vertical_speed, min(plane['vy'], max_vertical_speed)); plane['vy'] *= 0.95
            plane['pos_y'] += plane['vy']
            
            plane['pos_x'] = max(0, min(plane['pos_x'], self.screen_width - self.plane_size.width()))
            plane['pos_y'] = max(0, min(plane['pos_y'], self.screen_height - self.plane_size.height()))
            
            # --- Angle and Drawing Update ---
            dx = plane['actual_vx']
            dy = plane['pos_y'] - plane['prev_pos_y']
            plane['angle'] = math.degrees(math.atan2(dy, dx)) if dx or dy else (0 if plane['direction'] == 1 else 180)
            
            damaged_pixmap = plane['base_pixmap'].copy()
            if plane['damage_points']:
                painter = QPainter(damaged_pixmap); painter.setCompositionMode(QPainter.CompositionMode_Clear)
                painter.setBrush(Qt.transparent); painter.setPen(Qt.NoPen)
                for point in plane['damage_points']: painter.drawEllipse(point, 3, 3)
                painter.end()
            transform = QTransform().translate(self.plane_size.width()/2, self.plane_size.height()/2).rotate(plane['angle']).translate(-self.plane_size.width()/2, -self.plane_size.height()/2)
            plane['label'].setPixmap(damaged_pixmap.transformed(transform, Qt.SmoothTransformation)); plane['label'].move(QPoint(int(plane['pos_x']), int(plane['pos_y'])))
            
            # --- Smoke Trail Update ---
            if plane['health'] < 9: num, size = 3, 12
            elif plane['health'] < 17: num, size = 2, 8
            elif plane['health'] < 27: num, size = 1, 5
            else: num = 0
            if num > 0:
                center_x, center_y = self.plane_size.width()/2, self.plane_size.height()/2
                angle_rad = math.radians(plane['angle'])
                for k in range(num):
                    y_offset = (k - (num - 1)/2) * 10; relative_x = -30
                    rotated_relative_x = relative_x * math.cos(angle_rad) - y_offset * math.sin(angle_rad)
                    rotated_relative_y = relative_x * math.sin(angle_rad) + y_offset * math.cos(angle_rad)
                    spawn_x = center_x + plane['pos_x'] + rotated_relative_x; spawn_y = center_y + plane['pos_y'] + rotated_relative_y
                    smoke_vx = (plane['pos_x'] - plane['prev_pos_x']) * -0.2 + random.uniform(-0.2, 0.2)
                    smoke_vy = (plane['pos_y'] - plane['prev_pos_y']) * -0.2 + random.uniform(-0.2, 0.2)
                    smoke = {'label': QLabel(self), 'pos_x': spawn_x, 'pos_y': spawn_y, 'vx': smoke_vx, 'vy': smoke_vy, 'size': size, 'opacity': 0.8, 'lifetime': 60, 'frame': 0, 'type': 'smoke'}
                    smoke['label'].setPixmap(self.create_particle_pixmap(size, 0.8, QColor(100,100,100))); smoke['label'].resize(smoke['label'].pixmap().size()); smoke['label'].show(); self.smoke_particles.append(smoke)
            
            # --- Smoke Trail Update ---
            if plane['health'] < 9: num, size = 3, 12
            elif plane['health'] < 17: num, size = 2, 8
            elif plane['health'] < 27: num, size = 1, 5
            else: num = 0
            if num > 0:
                center_x, center_y = self.plane_size.width()/2, self.plane_size.height()/2
                angle_rad = math.radians(plane['angle'])
                for k in range(num):
                    y_offset = (k - (num - 1)/2) * 10; relative_x = -30
                    rotated_relative_x = relative_x * math.cos(angle_rad) - y_offset * math.sin(angle_rad)
                    rotated_relative_y = relative_x * math.sin(angle_rad) + y_offset * math.cos(angle_rad)
                    spawn_x = center_x + plane['pos_x'] + rotated_relative_x; spawn_y = center_y + plane['pos_y'] + rotated_relative_y
                    smoke_vx = (plane['pos_x'] - plane['prev_pos_x']) * -0.2 + random.uniform(-0.2, 0.2)
                    smoke_vy = (plane['pos_y'] - plane['prev_pos_y']) * -0.2 + random.uniform(-0.2, 0.2)
                    smoke = {'label': QLabel(self), 'pos_x': spawn_x, 'pos_y': spawn_y, 'vx': smoke_vx, 'vy': smoke_vy, 'size': size, 'opacity': 0.8, 'lifetime': 60, 'frame': 0, 'type': 'smoke'}
                    smoke['label'].setPixmap(self.create_particle_pixmap(size, 0.8, QColor(100,100,100))); smoke['label'].resize(smoke['label'].pixmap().size()); smoke['label'].show(); self.smoke_particles.append(smoke)

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

    def init_hud(self):
        # HUD for Plane 1 (Left)
        self.hud_left = QLabel(self)
        self.hud_left.setGeometry(10, 10, 250, 120)
        self.hud_left.setStyleSheet("color: white; background-color: rgba(0, 0, 0, 100); border-radius: 5px; padding: 5px; font-family: 'Lucida Console', Monaco, monospace;")
        self.hud_left.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.hud_left.setVisible(self.show_hud)
        self.hud_labels.append(self.hud_left)

        # HUD for Plane 2 (Right)
        self.hud_right = QLabel(self)
        self.hud_right.setGeometry(self.screen_width - 260, 10, 250, 120)
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
        fuel_bar1 = "█" * int(plane1.get('afterburner_fuel', 0) / 10) + " " * (10 - int(plane1.get('afterburner_fuel', 0) / 10))
        hud1_text = (
            f"<b>Left Wing</b><br>"
            f"Health: [{health_bar1}]<br>"
            f"Missiles: {plane1.get('missiles_left', 0)}<br>"
            f"Flares: {plane1.get('flares_left', 0)}<br>"
            f"Fuel:   [{fuel_bar1}]<br>"
            f"State: <i>{plane1.get('state', 'N/A').replace('_', ' ').title()}</i>"
        )
        self.hud_left.setText(hud1_text)

        # HUD for Plane 2 (Right)
        plane2 = self.planes[1]
        health_bar2 = "█" * int(plane2['health'] / 3) + " " * (10 - int(plane2['health'] / 3))
        fuel_bar2 = "█" * int(plane2.get('afterburner_fuel', 0) / 10) + " " * (10 - int(plane2.get('afterburner_fuel', 0) / 10))
        hud2_text = (
            f"<div align='right'><b>Right Wing</b><br>"
            f"[{health_bar2}] :Health<br>"
            f"{plane2.get('missiles_left', 0)} :Missiles<br>"
            f"{plane2.get('flares_left', 0)} :Flares<br>"
            f"[{fuel_bar2}] :Fuel<br>"
            f"<i>{plane2.get('state', 'N/A').replace('_', ' ').title()}</i> :State</div>"
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
                
                damaged_pixmap = self.winner['base_pixmap'].copy()
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
        for plane in self.planes:
            if plane['flare_cooldown'] > 0: plane['flare_cooldown'] -= 1
            if plane['is_deploying_flares'] and plane['flare_deployment_counter'] > 0 and plane['flare_deployment_counter'] % 2 == 0:
                flare = {'label': QLabel(self), 'pos_x': plane['pos_x'] + self.plane_size.width()/2, 'pos_y': plane['pos_y'] + self.plane_size.height()/2, 'vx': random.uniform(-2, 2) - plane['direction']*2, 'vy': random.uniform(-2, 2), 'size': 15, 'opacity': 1.0, 'lifetime': 90, 'frame': 0}
                flare['label'].setPixmap(self.create_particle_pixmap(flare['size'], flare['opacity'], QColor(255, 255, 0))); flare['label'].resize(flare['label'].pixmap().size()); flare['label'].show(); self.flares.append(flare)
            if plane['is_deploying_flares']: plane['flare_deployment_counter'] -= 1
            if plane['flare_deployment_counter'] <= 0: plane['is_deploying_flares'] = False

    def fire_projectiles(self):
        for i, plane in enumerate(self.planes):
            if plane['health'] <= 0: continue
            target = self.planes[1 - i]
            if target['health'] > 0:
                # --- Calculate Intercept Point ---
                projectile_speed = 8.0
                
                target_vx = target['pos_x'] - target['prev_pos_x']
                target_vy = target['pos_y'] - target['prev_pos_y']

                dx_initial = target['pos_x'] - plane['pos_x']
                dy_initial = target['pos_y'] - plane['pos_y']
                dist_initial = math.sqrt(dx_initial**2 + dy_initial**2)

                if dist_initial == 0: continue

                time_to_hit = dist_initial / projectile_speed

                predicted_x = target['pos_x'] + target_vx * time_to_hit
                predicted_y = target['pos_y'] + target_vy * time_to_hit

                dx = predicted_x - plane['pos_x']
                dy = predicted_y - plane['pos_y']
                dist = math.sqrt(dx**2 + dy**2)
                # --- End Intercept Calculation ---

                # Define engagement envelope for guns
                if not (50 < dist < 600):
                    continue

                target_angle = math.degrees(math.atan2(dy, dx))
                angle_diff = abs((target_angle - plane['angle'] + 180) % 360 - 180)
                if angle_diff > 10: # Widen angle slightly for leading shots
                    continue

                if dist > 1:
                    dx, dy = dx/dist, dy/dist
                    spawn_x, spawn_y = plane['pos_x'] + self.plane_size.width()/2, plane['pos_y'] + self.plane_size.height()/2
                    proj = {'label': QLabel(self), 'base_pixmap': self.projectile_pixmap, 'pos_x': spawn_x, 'pos_y': spawn_y, 'vx': dx*projectile_speed, 'vy': dy*projectile_speed, 'frame': 0, 'shooter_index': i, 'angle': math.degrees(math.atan2(dy, dx))}
                    proj['label'].setPixmap(proj['base_pixmap']); proj['label'].resize(proj['base_pixmap'].size()); proj['label'].show(); self.projectiles.append(proj)

    def try_fire_missile(self, plane, target):
        if plane.get('missiles_left', 0) <= 0 or plane.get('missile_fire_cooldown', 0) > 0:
            return False

        dx, dy = target['pos_x'] - plane['pos_x'], target['pos_y'] - plane['pos_y']
        dist = math.sqrt(dx**2 + dy**2)
        angle_to_target = math.degrees(math.atan2(dy, dx))
        angle_diff = abs((angle_to_target - plane['angle'] + 180) % 360 - 180)

        # Check missile engagement envelope (min range and angle)
        if angle_diff < 20 and dist > 200:
            plane['missiles_left'] -= 1
            plane['missile_fire_cooldown'] = 120 # 2 second cooldown between missile launches

            spawn_x, spawn_y = plane['pos_x'] + self.plane_size.width()/2, plane['pos_y'] + self.plane_size.height()/2
            if dist > 1: dx, dy = dx/dist, dy/dist
            missile = {'label': QLabel(self), 'base_pixmap': self.missile_pixmap, 'pos_x': spawn_x, 'pos_y': spawn_y, 'vx': dx*self.missile_speed, 'vy': dy*self.missile_speed, 'angle': math.degrees(math.atan2(dy, dx)), 'shooter_index': self.planes.index(plane), 'target_index': self.planes.index(target), 'frame': 0, 'target_flare': None, 'target_missile': None}
            missile['label'].setPixmap(missile['base_pixmap']); missile['label'].resize(missile['base_pixmap'].size()); missile['label'].show(); self.missiles.append(missile)
            return True
        return False

    def handle_missile_threats(self, plane, plane_idx):
        # Checks for and reacts to immediate missile threats.
        # Returns True if a threat was handled, False otherwise.
        for missile in self.missiles:
            if missile['target_index'] == plane_idx and not missile.get('target_flare'):
                if math.sqrt((missile['pos_x'] - plane['pos_x'])**2 + (missile['pos_y'] - plane['pos_y'])**2) < 450:
                    # Evade missile by moving perpendicular to its path, with some randomness
                    plane['y_target'] = plane['pos_y'] + (300 if missile['vy'] < 0 else -300) + random.uniform(-50, 50)
                    plane['speed_multiplier'] = 1.6 # Use afterburner to dodge
                    return True
        return False

    def is_projectile_threat(self, plane, plane_idx):
        for proj in self.projectiles:
            if proj['shooter_index'] == plane_idx:
                continue

            proj_dx = proj['pos_x'] - plane['pos_x']
            
            # Only check for collision if projectile is somewhat relevant.
            if abs(proj_dx) > 500 or abs(proj['pos_y'] - plane['pos_y']) > 300:
                continue

            # Predictive check using relative velocity
            relative_vx = proj['vx'] - plane['actual_vx']
            if relative_vx == 0: continue
            
            time_to_impact = proj_dx / relative_vx
            
            if 0 < time_to_impact < 50: # Generous 50-frame window
                future_proj_y = proj['pos_y'] + proj['vy'] * time_to_impact
                future_plane_y = plane['pos_y'] + plane['vy'] * time_to_impact
                
                if abs(future_proj_y - future_plane_y) < 75: # Wider collision box
                    # Store the threat for the state machine to use
                    plane['projectile_threat'] = proj 
                    return True
        
        plane['projectile_threat'] = None
        return False

    def get_plane_state(self, plane, target):
        # If we are currently disengaging, check the timer.
        if plane.get('state') == 'disengaging':
            if plane.get('disengage_timer', 0) > 0:
                return 'disengaging' # Continue disengaging
            else:
                # Timer is up, force re-engagement and start cooldown
                plane['disengage_cooldown'] = 480 # 8 second cooldown
                return 'maneuvering'

        # If health is low and not on cooldown, start disengaging
        if plane['health'] < 10 and plane.get('disengage_cooldown', 0) <= 0 and plane.get('state') != 'attacking':
             return 'start_disengage'
        
        dist = math.sqrt((target['pos_x'] - plane['pos_x'])**2 + (target['pos_y'] - plane['pos_y'])**2)
        
        # Is target on my tail?
        angle_to_me = math.degrees(math.atan2(plane['pos_y'] - target['pos_y'], plane['pos_x'] - target['pos_x']))
        target_angle_diff = abs((angle_to_me - target['angle'] + 180) % 360 - 180)
        is_target_behind_me = (plane['pos_x'] - target['pos_x']) * plane['direction'] > 0

        # Am I on target's tail?
        angle_to_target = math.degrees(math.atan2(target['pos_y'] - plane['pos_y'], target['pos_x'] - plane['pos_x']))
        my_angle_diff = abs((angle_to_target - plane['angle'] + 180) % 360 - 180)
        am_i_behind_target = (target['pos_x'] - plane['pos_x']) * target['direction'] > 0

        if is_target_behind_me and dist < 400 and target_angle_diff < 45:
            return 'evading_plane'

        if am_i_behind_target and dist < 600 and my_angle_diff < 45:
            return 'attacking'

        return 'maneuvering'

    def update_planes(self):
        for i, plane in enumerate(self.planes):
            if plane['health'] <= 0: continue

            if plane.get('missile_fire_cooldown', 0) > 0:
                plane['missile_fire_cooldown'] -= 1
            if plane.get('disengage_timer', 0) > 0:
                plane['disengage_timer'] -= 1
            if plane.get('disengage_cooldown', 0) > 0:
                plane['disengage_cooldown'] -= 1

            # --- Wall Collision Override ---
            margin = 20 
            if (plane['pos_x'] > self.screen_width - self.plane_size.width() - margin and plane['direction'] == 1):
                plane['direction'] = -1
                plane['speed'] = plane['base_speed'] * plane['direction']
                plane['maneuver_timer'] = 0
            elif (plane['pos_x'] < margin and plane['direction'] == -1):
                plane['direction'] = 1
                plane['speed'] = plane['base_speed'] * plane['direction']
                plane['maneuver_timer'] = 0

            target = self.planes[1 - i]
            
            current_multiplier = plane.get('speed_multiplier', 1.0)
            plane['speed_multiplier'] = current_multiplier + (1.0 - current_multiplier) * 0.05

            # --- Threat Evasion Logic ---
            threat_handled = False
            
            is_dodging_projectile = self.is_projectile_threat(plane, i)
            if is_dodging_projectile:
                plane['state'] = 'evading_projectile'
                plane['evade_timer'] = 20
            
            if plane.get('evade_timer', 0) > 0 and plane.get('state') == 'evading_projectile':
                plane['evade_timer'] -= 1
                threatening_proj = plane.get('projectile_threat')
                if threatening_proj:
                    relative_vy = threatening_proj['vy'] - plane['vy']
                    plane['y_target'] = plane['pos_y'] + (300 if relative_vy > 0 else -300)
                plane['speed_multiplier'] = 1.8
                threat_handled = True
            
            if not threat_handled:
                threat_handled = self.handle_missile_threats(plane, i)

            # --- Main AI State Machine ---
            if not threat_handled and target['health'] > 0:
                state = self.get_plane_state(plane, target)
                
                if state == 'start_disengage':
                    plane['disengage_timer'] = random.randint(120, 240)
                    state = 'disengaging'

                plane['state'] = state

                if state == 'disengaging':
                    plane['speed_multiplier'] = 2.0
                    corner_x = 0 if target['pos_x'] > self.screen_width / 2 else self.screen_width
                    corner_y = 0 if target['pos_y'] > self.screen_height / 2 else self.screen_height
                    
                    target_dx = corner_x - plane['pos_x']
                    
                    if target_dx > 0: plane['direction'] = 1
                    else: plane['direction'] = -1
                    plane['speed'] = plane['base_speed'] * plane['direction']
                    
                    plane['y_target'] = corner_y

                elif state == 'evading_plane':
                    if plane['evade_timer'] <= 0:
                        plane['evade_decision'] = random.choice(['break_burn_up', 'break_burn_down', 'break_cut_up', 'break_cut_down', 'jink', 'high_g_reversal'])
                        plane['evade_timer'] = random.randint(60, 90)
                        if plane['evade_decision'] == 'high_g_reversal':
                            plane['evade_timer'] = 75 # Fixed time for this maneuver
                        
                        if plane['flare_cooldown'] == 0 and plane['flares_left'] > 0 and random.random() < 0.4:
                            plane['flares_left'] -= 1
                            plane['is_deploying_flares'] = True
                            plane['flare_deployment_counter'] = 16
                            plane['flare_cooldown'] = 180

                    plane['evade_timer'] -= 1
                    decision = plane.get('evade_decision', 'jink')

                    if decision == 'high_g_reversal':
                        plane['speed_multiplier'] = 0.3 # Drastically cut speed
                        # Start a sharp climb or dive away from the attacker
                        if plane['evade_timer'] == 74: # First frame of maneuver
                            plane['y_target'] = plane['pos_y'] + (500 if target['pos_y'] > plane['pos_y'] else -500)
                        
                        # At the apex of the turn, reverse direction
                        if plane['evade_timer'] == 45:
                            plane['direction'] *= -1
                            plane['speed'] = plane['base_speed'] * plane['direction']
                    elif 'burn' in decision: plane['speed_multiplier'] = 1.8
                    elif 'cut' in decision: plane['speed_multiplier'] = 0.5

                    if 'up' in decision: plane['y_target'] = plane['pos_y'] - 400
                    elif 'down' in decision: plane['y_target'] = plane['pos_y'] + 400
                    
                    if decision == 'jink':
                        if plane['evade_timer'] % 15 == 0:
                             plane['y_target'] = plane['pos_y'] + random.uniform(-200, 200)

                elif state == 'attacking':
                    self.try_fire_missile(plane, target)
                    plane['y_target'] = target['pos_y'] + random.uniform(-20, 20)
                    dist = math.sqrt((target['pos_x'] - plane['pos_x'])**2 + (target['pos_y'] - plane['pos_y'])**2)
                    
                    follow_dist = plane.get('follow_dist', 250)
                    if random.random() < 0.02:
                        plane['follow_dist'] = random.uniform(200, 300)

                    if dist > follow_dist + 50: plane['speed_multiplier'] = 1.4
                    elif dist < follow_dist - 50: plane['speed_multiplier'] = 0.8
                    else: plane['speed_multiplier'] = 1.1

                elif state == 'maneuvering':
                    dist = math.sqrt((target['pos_x'] - plane['pos_x'])**2 + (target['pos_y'] - plane['pos_y'])**2)
                    if dist > 600:
                        self.try_fire_missile(plane, target)

                    plane['maneuver_timer'] = plane.get('maneuver_timer', 0) - 1
                    if plane['maneuver_timer'] <= 0:
                        plane['arc_direction'] = None # Reset arc direction
                        plane['current_maneuver'] = random.choice(['lag_pursuit', 'lag_pursuit', 'low_yo_yo', 'high_yo_yo', 'extend_and_run', 'wide_arc'])
                        plane['maneuver_timer'] = random.randint(120, 240) # Longer maneuvers
                        plane['maneuver_rand_val'] = random.uniform(250, 400)

                    maneuver = plane.get('current_maneuver', 'lag_pursuit')
                    rand_val = plane.get('maneuver_rand_val', 300)

                    if maneuver == 'lag_pursuit':
                        # --- Lag Pursuit Logic ---
                        # Aim for a control point behind the target to get a good attack angle.
                        control_point_x = target['pos_x'] - (target['direction'] * rand_val)
                        control_point_y = target['pos_y']
                        plane['y_target'] = control_point_y

                        dist_to_control_point = abs(plane['pos_x'] - control_point_x)
                        is_facing_control_point = (control_point_x - plane['pos_x']) * plane['direction'] > 0

                        if not is_facing_control_point and dist_to_control_point > 150:
                            # If we are facing the wrong way and are far, we must turn.
                            plane['speed_multiplier'] = 1.9 
                            plane['direction'] *= -1
                            plane['speed'] = plane['base_speed'] * plane['direction']
                            plane['maneuver_timer'] = 45 # Commit to the turn
                        else:
                            # Facing the right way, or close enough not to matter.
                            if dist_to_control_point > 100:
                                plane['speed_multiplier'] = 1.8 # Burn to catch up
                            else:
                                plane['speed_multiplier'] = 1.2 # Pace the target
                    
                    elif maneuver == 'high_yo_yo':
                        plane['y_target'] = target['pos_y'] - rand_val
                        plane['speed_multiplier'] = 0.8

                    elif maneuver == 'low_yo_yo':
                        plane['y_target'] = target['pos_y'] + rand_val
                        plane['speed_multiplier'] = 1.9

                    elif maneuver == 'extend_and_run':
                        # Fly straight towards the screen edge plane is facing
                        plane['y_target'] = plane['pos_y'] # Maintain altitude
                        plane['speed_multiplier'] = 1.9 # Full afterburner
                        # Let wall collision logic handle the turn

                    elif maneuver == 'wide_arc':
                        # Fly in a large arc across the screen
                        if plane.get('arc_direction') is None:
                            plane['arc_direction'] = 'up' if plane['pos_y'] > self.screen_height / 2 else 'down'
                        
                        if plane['arc_direction'] == 'up':
                            plane['y_target'] = 50 # Target near top of screen
                        else:
                            plane['y_target'] = self.screen_height - 150 # Target near bottom
                        
                        plane['speed_multiplier'] = 1.3 # Steady speed for a smooth arc
            
            # --- Afterburner and Fuel Management ---
            if plane['speed_multiplier'] > 1.0:
                if plane.get('afterburner_fuel', 0) > 0:
                    plane['afterburner_fuel'] -= 1.5  # Fuel consumption rate
                else:
                    plane['speed_multiplier'] = 1.0 # Out of fuel
            else:
                if plane.get('afterburner_fuel', 100) < plane.get('max_afterburner_fuel', 100):
                    plane['afterburner_fuel'] += 0.3  # Fuel regeneration rate
            
            # --- Physics and Position Update ---
            health_percentage = max(0, plane['health']/30)
            damage_modifier = 0.6 + (0.4 * health_percentage)
            
            target_vx = plane['speed'] * damage_modifier * plane['speed_multiplier']
            current_vx = plane.get('actual_vx', target_vx)
            turn_factor = 0.05 
            plane['actual_vx'] = current_vx + (target_vx - current_vx) * turn_factor
            
            plane['prev_pos_x'], plane['prev_pos_y'] = plane['pos_x'], plane['pos_y']
            plane['pos_x'] += plane['actual_vx']
            
            vertical_acceleration = 0.15; max_vertical_speed = 5
            if plane['y_target'] > plane['pos_y']: plane['vy'] += vertical_acceleration
            else: plane['vy'] -= vertical_acceleration
            plane['vy'] = max(-max_vertical_speed, min(plane['vy'], max_vertical_speed)); plane['vy'] *= 0.95
            plane['pos_y'] += plane['vy']
            
            plane['pos_x'] = max(0, min(plane['pos_x'], self.screen_width - self.plane_size.width()))
            plane['pos_y'] = max(0, min(plane['pos_y'], self.screen_height - self.plane_size.height()))
            
            # --- Angle and Drawing Update ---
            dx = plane['actual_vx']
            dy = plane['pos_y'] - plane['prev_pos_y']
            plane['angle'] = math.degrees(math.atan2(dy, dx)) if dx or dy else (0 if plane['direction'] == 1 else 180)
            
            damaged_pixmap = plane['base_pixmap'].copy()
            if plane['damage_points']:
                painter = QPainter(damaged_pixmap); painter.setCompositionMode(QPainter.CompositionMode_Clear)
                painter.setBrush(Qt.transparent); painter.setPen(Qt.NoPen)
                for point in plane['damage_points']: painter.drawEllipse(point, 3, 3)
                painter.end()
            transform = QTransform().translate(self.plane_size.width()/2, self.plane_size.height()/2).rotate(plane['angle']).translate(-self.plane_size.width()/2, -self.plane_size.height()/2)
            plane['label'].setPixmap(damaged_pixmap.transformed(transform, Qt.SmoothTransformation)); plane['label'].move(QPoint(int(plane['pos_x']), int(plane['pos_y'])))
            
            # --- Smoke Trail Update ---
            if plane['health'] < 9: num, size = 3, 12
            elif plane['health'] < 17: num, size = 2, 8
            elif plane['health'] < 27: num, size = 1, 5
            else: num = 0
            if num > 0:
                center_x, center_y = self.plane_size.width()/2, self.plane_size.height()/2
                angle_rad = math.radians(plane['angle'])
                for k in range(num):
                    y_offset = (k - (num - 1)/2) * 10; relative_x = -30
                    rotated_relative_x = relative_x * math.cos(angle_rad) - y_offset * math.sin(angle_rad)
                    rotated_relative_y = relative_x * math.sin(angle_rad) + y_offset * math.cos(angle_rad)
                    spawn_x = center_x + plane['pos_x'] + rotated_relative_x; spawn_y = center_y + plane['pos_y'] + rotated_relative_y
                    smoke_vx = (plane['pos_x'] - plane['prev_pos_x']) * -0.2 + random.uniform(-0.2, 0.2)
                    smoke_vy = (plane['pos_y'] - plane['prev_pos_y']) * -0.2 + random.uniform(-0.2, 0.2)
                    smoke = {'label': QLabel(self), 'pos_x': spawn_x, 'pos_y': spawn_y, 'vx': smoke_vx, 'vy': smoke_vy, 'size': size, 'opacity': 0.8, 'lifetime': 60, 'frame': 0, 'type': 'smoke'}
                    smoke['label'].setPixmap(self.create_particle_pixmap(size, 0.8, QColor(100,100,100))); smoke['label'].resize(smoke['label'].pixmap().size()); smoke['label'].show(); self.smoke_particles.append(smoke)
            
            # --- Smoke Trail Update ---
            if plane['health'] < 9: num, size = 3, 12
            elif plane['health'] < 17: num, size = 2, 8
            elif plane['health'] < 27: num, size = 1, 5
            else: num = 0
            if num > 0:
                center_x, center_y = self.plane_size.width()/2, self.plane_size.height()/2
                angle_rad = math.radians(plane['angle'])
                for k in range(num):
                    y_offset = (k - (num - 1)/2) * 10; relative_x = -30
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
            if self.game_active and math.sqrt((tx - missile['pos_x'])**2 + (ty - missile['pos_y'])**2) < 400 and target_plane['flare_cooldown'] == 0 and target_plane['flares_left'] > 0 and random.random() < 0.5:
                target_plane['flares_left'] -= 1
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