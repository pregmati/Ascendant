import pygame, json, copy, random

from Packages.Extern import SoundPlayer
from Packages import Settings, Sprite, Enemy, Player, Water

class Particle():
    def __init__(self, position, velocity, color):
        self.position = position
        self.velocity = velocity
        self.color = color
    def update_position(self, delta):
        self.position += self.velocity * delta
    def render(self, surface, offset, delta=None):
        if not delta == None:
            self.update_position(delta)
        surface.set_at([int(self.position.x+offset.x), int(self.position.y+offset.y)], self.color)
        return [pygame.Rect(int(self.position.x+offset.x)-2, int(self.position.y+offset.y)-2, 5, 5)]

class Level():
    def __init__(self, should_load=True, level_num=0, save_num=0, position=pygame.Vector2(0,0), player_base=Player.Player(), water_base=Water.Water(), enemy_base=Enemy.Enemy(), flying_enemy_base=Enemy.FlyingEnemy()):
        self.position = position

        self.sprites_infront = []
        self.sprites_behind = []
        self.level_num = level_num
        self.save_level = 0

        self.player_base = player_base
        self.water_base = water_base
        self.enemy_base = enemy_base
        self.flying_enemy_base = flying_enemy_base

        self.colliders, self.damage_colliders, self.hitable_colliders, self.transitions, self.waters, self.water_colliders, self.enemies = [],[],[],[],[],[],[]
        self.player = player_base.copy()
        self.particles = []
        self.colors = [pygame.Color(33, 48, 34), pygame.Color(30,30,30), pygame.Color(69, 61, 51), pygame.Color(199,199,199)]
        self.level_size = [0,0]


        self.level_filename = f"{Settings.SRC_DIRECTORY}Levels/Level{self.level_num}/level.json"
        self.entities_filename = f"{Settings.SRC_DIRECTORY}Levels/Level{self.level_num}/entities.json"
        
        if should_load:
            self.load_level(level_num)
                
    def get_colliders(self):
        return self.colliders

    def get_damage_colliders(self):
        return self.damage_colliders
    
    def get_hitable_colliders(self):
        return self.hitable_colliders
    
    def get_save_colliders(self):
        return self.save_colliders
    
    def get_water_colliders(self):
        return self.water_colliders

    def render_colliders(self, delta, surface, offset):
        for collider in self.colliders:
            collider.move_ip(offset)
            pygame.draw.rect(surface, (255,0,0), collider)
            collider.move_ip(-offset)
        for collider in self.hitable_colliders:
            collider.move_ip(offset)
            pygame.draw.rect(surface, (100,0,100), collider)
            collider.move_ip(-offset)
        for collider in self.damage_colliders:
            collider.move_ip(offset)
            pygame.draw.rect(surface, (200,0,100), collider)
            collider.move_ip(-offset)
        for collider in self.water_colliders:
            collider.move_ip(offset)
            pygame.draw.rect(surface, (100,150,200), collider)
            collider.move_ip(-offset)
        for collider in [a["collider"] for a in self.transitions]:
            collider.move_ip(offset)
            pygame.draw.rect(surface, (100,0,200), collider)
            collider.move_ip(-offset)

    def render_infront(self, delta, surface, offset=pygame.Vector2(0,0)):
        dirty_rects = []

        # Handle particles
        if random.randint(0, 20) == 0:
            self.particles += [Particle(
                pygame.Vector2(0, random.randint(0, self.level_size[1])),
                pygame.Vector2(random.uniform(20, 100),random.uniform(-2, 2)),
                random.choice(self.colors),
            )]
        i=0
        while i < len(self.particles):
            if self.particles[i].position.x > self.level_size[0]:
                del self.particles[i]
            else:
                dirty_rects += self.particles[i].render(surface, offset, delta)
                i+=1

        for sprite in self.waters:
            dirty_rects += sprite.render_infront(delta, surface, self.position + offset)
        for sprite in self.sprites_infront:
            render_position = self.position + pygame.Vector2(offset.x*sprite["parallax"].x, offset.y*sprite["parallax"].y)
            sprite["sprite"].render(surface, render_position)

        return dirty_rects

    def render_behind(self, delta, surface, offset=pygame.Vector2(0,0)):
        for sprite in self.waters:
            sprite.render_behind(delta, surface, self.position + offset)
        for sprite in self.sprites_behind:
            render_position = self.position + pygame.Vector2(offset.x*sprite["parallax"].x, offset.y*sprite["parallax"].y)
            sprite["sprite"].render(surface, render_position)
    
    def load_save(self, save_num):
        self.selected_save = save_num
        save_filename = Settings.SAVE_FILETEMPLATE.substitute(num=str(save_num))
        try:
            with open(save_filename) as json_file:
                json_data = json.load(json_file)
            self.load_level(level_num=json_data["save_level"])
            self.save_level = json_data["save_level"]
            self.player.play_animation("unsit")
        except Exception as e:
            if Settings.DEBUG:
                print(f"Failed to load save {save_filename}, error: ", e)
            try:
                with open(save_filename, 'w') as file:
                    json.dump(Settings.DEFAULT_SAVE, file)
            except Exception as e:
                if Settings.DEBUG:
                    print(f"Failed to write save {save_filename}, error: ", e)
            self.load_level()
        
    def save_game(self):
        save_filename = Settings.SAVE_FILETEMPLATE.substitute(num=str(Settings.SELECTED_SAVE))
        save_data = Settings.DEFAULT_SAVE
        save_data["save_level"] = self.save_level
        try:
            with open(save_filename, 'w') as file:
                json.dump(Settings.DEFAULT_SAVE, file)
        except Exception as e:
            if Settings.DEBUG:
                print(f"Failed to write save {save_filename}, error: ", e)

    def load_level(self, level_num=0, transition=None):
        self.level_num=level_num
        self.level_filename = f"{Settings.SRC_DIRECTORY}Levels/Level{self.level_num}/level.json"

        with open(self.level_filename) as json_file:
            level_json_data = json.load(json_file)
        
        sorted_layers = sorted(level_json_data["layers"], key = lambda x: x["depth"])
        self.sprites_behind, self.sprites_infront = [],[]
        for image_layer in sorted_layers:
            if image_layer["depth"] <= 0:
                self.sprites_behind.append({
                    "sprite": Sprite.ImageSprite( image_filename=f"{Settings.SRC_DIRECTORY}Levels/Level{self.level_num}/{image_layer['filename']}"),
                    "depth": image_layer["depth"],
                    "parallax": pygame.Vector2(image_layer["parallaxX"],image_layer["parallaxY"])   
                })
            else:
                self.sprites_infront.append({
                    "sprite": Sprite.ImageSprite( image_filename=f"{Settings.SRC_DIRECTORY}Levels/Level{self.level_num}/{image_layer['filename']}"),
                    "depth": image_layer["depth"],
                    "parallax": pygame.Vector2(image_layer["parallaxX"],image_layer["parallaxY"])   
                })
        self.level_size = [self.sprites_behind[0]["sprite"].image.get_width(), self.sprites_behind[0]["sprite"].image.get_height()]
            
        self.entities_filename = f"{Settings.SRC_DIRECTORY}Levels/Level{self.level_num}/{level_json_data['entities']['filename']}"
        with open(self.entities_filename) as json_file:
            json_data = json.load(json_file)

        self.colliders = []
        if "collisions" in json_data:
            for collider in json_data["collisions"]:
                self.colliders.append(pygame.Rect(collider["x"], collider["y"], collider["width"], collider["height"]))
        elif Settings.DEBUG:
            print(f"No collisions entity layer found in {self.entities_filename}")
        
        self.damage_colliders = []
        if "damage_colliders" in json_data:
            for collider in json_data["damage_colliders"]:
                self.damage_colliders.append(pygame.Rect(collider["x"], collider["y"], collider["width"], collider["height"]))
        elif Settings.DEBUG:
            print(f"No damage_colliders entity layer found in {self.entities_filename}")

        self.hitable_colliders = []
        if "hitable_colliders" in json_data:
            for collider in json_data["hitable_colliders"]:
                self.hitable_colliders.append(pygame.Rect(collider["x"], collider["y"], collider["width"], collider["height"]))
        elif Settings.DEBUG:
            print(f"No hitable_colliders entity layer found in {self.entities_filename}")

        self.save_colliders = []
        if "save_game" in json_data:
            for collider in json_data["save_game"]:
                self.save_colliders.append(pygame.Rect(collider["x"], collider["y"], collider["width"], collider["height"]))
        elif Settings.DEBUG:
            print(f"No save_games entity layer found in {self.entities_filename}")
        
        self.transitions = []
        try:
            for bounds, info in zip(json_data["level_transition"], level_json_data["level_transition"]):
                self.transitions.append({
                    "collider":pygame.Rect(bounds["x"], bounds["y"], bounds["width"], bounds["height"]),
                    "to_level":info["to_level"],
                    "to_transition":info["to_transition"],
                    "direction":["N", "E", "S", "W"][info["direction"]]
                })
        except:
            if Settings.DEBUG:
                print(f"Failed to load transition entities {self.entities_filename}, and {self.level_filename}")

        self.waters = []
        self.water_colliders = []
        if "water" in json_data:
            for water in json_data["water"]:
                self.waters.append(self.water_base.copy())
                self.waters[-1].tile_from_rect(pygame.Rect(water["x"], water["y"], water["width"], water["height"]))
                self.water_colliders.append(pygame.Rect(water["x"], water["y"], water["width"], water["height"]))
        elif Settings.DEBUG:
            print(f"No water entity layer found in {self.entities_filename}")

        self.reset_level()

        # Configure level settings
        Settings.camera.contraints_max = pygame.Vector2(
            self.sprites_behind[0]["sprite"].image.get_rect().width,
            self.sprites_behind[0]["sprite"].image.get_rect().height,
        )

        # Handle transition
        if not transition == None:
            transition_rect = self.transitions[transition["to_transition"]]["collider"]
            direction = self.transitions[transition["to_transition"]]["direction"]

            self.player.transition_frames = self.player.transition_max_frames

            if direction == "N":
                self.player.velocity.y = -self.player.gravity.y/4
                self.player.position = pygame.Vector2(
                    transition_rect.left + transition_rect.width*0.5 - self.player.collider_size.x*0.5,
                    transition_rect.top,
                ) - self.player.collider_offset
            elif direction == "S":
                self.player.velocity.y = self.player.gravity.y/4
                self.player.position = pygame.Vector2(
                    transition_rect.left + transition_rect.width*0.5,
                    transition_rect.top,
                ) - self.player.collider_offset
            elif direction == "E":
                self.player.transition_frames = self.player.transition_max_frames
                self.player.velocity.x = self.player.walk_speed
                self.player.position = pygame.Vector2(
                    transition_rect.left + transition_rect.width,
                    transition_rect.top + transition_rect.height*0.5,
                ) - self.player.collider_offset
                self.player.play_animation("walk", loop=True)
            elif direction == "W":
                self.player.transition_frames = self.player.transition_max_frames
                self.player.velocity.x = -self.player.walk_speed
                self.player.position = pygame.Vector2(
                    transition_rect.left,
                    transition_rect.top + transition_rect.height - self.player.collider_size.y,
                ) - self.player.collider_offset
                self.player.play_animation("walk", loop=True)
                self.player.flipX = True

        Settings.camera.set_position(self.player.position, Settings.surface)
    
    def reset_level(self):
        with open(self.entities_filename) as json_file:
            json_data = json.load(json_file)

        if "player" in json_data:
            old_player_hearts = self.player.hearts
            old_player_key_state = self.player.key_state

            player_info = json_data["player"][0]
            self.player = self.player_base.copy()
            self.player.position = pygame.Vector2(
                player_info["x"] - self.player.collider_offset.x,
                player_info["y"] - self.player.collider_offset.x,
            )
            self.player.hearts = old_player_hearts
            self.player.key_state = old_player_key_state
        elif Settings.DEBUG:
            print(f"No players entity layer found in {self.entities_filename}")

        self.enemies = []
        if "enemies" in json_data:
            for enemy in json_data["enemies"]:
                self.enemies.append(self.enemy_base.copy())
                self.enemies[-1].position = pygame.Vector2(
                    enemy["x"] - self.enemy_base.collider_offset.x,
                    enemy["y"] - self.enemy_base.collider_offset.y,
                )
        elif Settings.DEBUG:
            print(f"No enemies entity layer found in {self.entities_filename}")

        if "flying_enemies" in json_data:
            for enemy in json_data["flying_enemies"]:
                self.enemies.append(self.flying_enemy_base.copy())
                self.enemies[-1].position = pygame.Vector2(
                    enemy["x"] - self.flying_enemy_base.collider_offset.x,
                    enemy["y"] - self.flying_enemy_base.collider_offset.y,
                )
                self.enemies[-1].og_position = copy.copy(self.enemies[-1].position)
        elif Settings.DEBUG:
            print(f"No flying_enemies entity layer found in {self.entities_filename}")