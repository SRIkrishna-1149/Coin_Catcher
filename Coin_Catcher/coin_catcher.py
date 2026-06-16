import pickle
from pathlib import Path

import pygame

BASE_DIR = Path(__file__).resolve().parent
IMG_DIR = BASE_DIR / "img"

BASE_WIDTH = 700
BASE_HEIGHT = 700
FPS = 60
TILE_SIZE = 35

PLAYER_WIDTH = 30
PLAYER_HEIGHT = 60
PLAYER_CROUCH_HEIGHT = 42
PLAYER_SPEED = 3
JUMP_STRENGTH = -15
GRAVITY = 1
MAX_FALL_SPEED = 10

WINDOW_SAFE_SCALE = 0.88
MIN_WINDOW_SIZE = 350

WHITE = (255, 255, 255)
BLUE = (0, 0, 255)
LETTERBOX_COLOUR = (10, 12, 18)

AUDIO_ENABLED = False


class SilentSound:
    def play(self, *args, **kwargs):
        return None

    def set_volume(self, *args, **kwargs):
        return None


def asset_path(filename):
    return IMG_DIR / filename


def load_image(filename, use_alpha=True):
    image_path = asset_path(filename)
    if not image_path.exists():
        raise SystemExit(f"Missing required image asset: {image_path}")

    try:
        image = pygame.image.load(str(image_path))
    except pygame.error as exc:
        raise SystemExit(f"Could not load image asset '{image_path}': {exc}") from exc

    try:
        return image.convert_alpha() if use_alpha else image.convert()
    except pygame.error:
        return image


def load_sound(filename, volume=0.5):
    if not AUDIO_ENABLED:
        return SilentSound()

    sound_path = asset_path(filename)
    if not sound_path.exists():
        print(f"Warning: missing sound asset, continuing without it: {sound_path}")
        return SilentSound()

    try:
        sound = pygame.mixer.Sound(str(sound_path))
        sound.set_volume(volume)
        return sound
    except pygame.error as exc:
        print(
            f"Warning: could not load sound '{sound_path}', "
            f"continuing without it: {exc}"
        )
        return SilentSound()


def start_music(filename):
    if not AUDIO_ENABLED:
        return

    music_path = asset_path(filename)
    if not music_path.exists():
        print(f"Warning: missing music asset, continuing without it: {music_path}")
        return

    try:
        pygame.mixer.music.load(str(music_path))
        pygame.mixer.music.play(-1, 0.0, 5000)
    except pygame.error as exc:
        print(
            f"Warning: could not play music '{music_path}', "
            f"continuing without it: {exc}"
        )


def init_audio():
    global AUDIO_ENABLED

    try:
        if not pygame.mixer.get_init():
            pygame.mixer.init()
        AUDIO_ENABLED = True
    except pygame.error as exc:
        AUDIO_ENABLED = False
        print(f"Warning: audio is disabled because the mixer could not start: {exc}")


def load_level_data(level):
    level_path = BASE_DIR / f"level{level}_data"
    if not level_path.exists():
        raise SystemExit(f"Missing required level data file: {level_path}")

    try:
        with level_path.open("rb") as pickle_in:
            return pickle.load(pickle_in)
    except (pickle.PickleError, EOFError, OSError) as exc:
        raise SystemExit(f"Could not load level data '{level_path}': {exc}") from exc


def get_initial_window_size():
    display_info = pygame.display.Info()
    monitor_width = display_info.current_w or BASE_WIDTH
    monitor_height = display_info.current_h or BASE_HEIGHT
    safe_size = int(min(monitor_width, monitor_height) * WINDOW_SAFE_SCALE)

    if safe_size <= 0:
        safe_size = BASE_WIDTH
    if safe_size < MIN_WINDOW_SIZE:
        return safe_size, safe_size
    return safe_size, safe_size


def get_scaled_view(window_size):
    window_width = max(1, window_size[0])
    window_height = max(1, window_size[1])
    scale = min(window_width / BASE_WIDTH, window_height / BASE_HEIGHT)
    scaled_width = max(1, int(BASE_WIDTH * scale))
    scaled_height = max(1, int(BASE_HEIGHT * scale))
    offset_x = (window_width - scaled_width) // 2
    offset_y = (window_height - scaled_height) // 2
    return scale, (scaled_width, scaled_height), (offset_x, offset_y)


def window_to_virtual(mouse_pos, view):
    scale, scaled_size, offset = view
    scaled_width, scaled_height = scaled_size
    offset_x, offset_y = offset
    mouse_x, mouse_y = mouse_pos

    if (
        mouse_x < offset_x
        or mouse_y < offset_y
        or mouse_x >= offset_x + scaled_width
        or mouse_y >= offset_y + scaled_height
    ):
        return None

    virtual_x = int((mouse_x - offset_x) / scale)
    virtual_y = int((mouse_y - offset_y) / scale)
    return virtual_x, virtual_y


def handle_resize(event):
    width = max(1, event.w)
    height = max(1, event.h)
    return pygame.display.set_mode((width, height), pygame.RESIZABLE)


def present_virtual_surface(virtual_surface, display_surface, view):
    _, scaled_size, offset = view
    display_surface.fill(LETTERBOX_COLOUR)
    scaled_surface = pygame.transform.smoothscale(virtual_surface, scaled_size)
    display_surface.blit(scaled_surface, offset)
    pygame.display.update()


def draw_text(surface, text, font, text_col, x, y):
    img = font.render(text, True, text_col)
    surface.blit(img, (x, y))


def draw_centered_text(surface, text, font, text_col, center_x, y):
    img = font.render(text, True, text_col)
    rect = img.get_rect()
    rect.centerx = center_x
    rect.y = y
    surface.blit(img, rect)


def create_sprite_groups():
    return {
        "blob": pygame.sprite.Group(),
        "platform": pygame.sprite.Group(),
        "lava": pygame.sprite.Group(),
        "coin": pygame.sprite.Group(),
        "exit": pygame.sprite.Group(),
    }


def reset_level(level, player, groups):
    player.reset(100, BASE_HEIGHT - 130)
    for group in groups.values():
        group.empty()

    world = World(load_level_data(level), groups)

    score_coin = Coin(TILE_SIZE // 2, TILE_SIZE // 2)
    groups["coin"].add(score_coin)
    return world


class Button:
    def __init__(self, x, y, image):
        self.image = image
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y
        self.clicked = False

    def draw(self, surface, mouse_pos, mouse_pressed):
        action = False

        if mouse_pos is not None and self.rect.collidepoint(mouse_pos):
            if mouse_pressed[0] and not self.clicked:
                action = True
                self.clicked = True

        if not mouse_pressed[0]:
            self.clicked = False

        surface.blit(self.image, self.rect)
        return action


class Player:
    def __init__(self, x, y):
        self.reset(x, y)

    def reset(self, x, y):
        self.images_right = []
        self.images_left = []
        self.index = 0
        self.counter = 0

        for num in range(1, 5):
            img_right = load_image(f"guy{num}.png")
            img_right = pygame.transform.scale(img_right, (PLAYER_WIDTH, PLAYER_HEIGHT))
            img_left = pygame.transform.flip(img_right, True, False)
            self.images_right.append(img_right)
            self.images_left.append(img_left)

        self.crouch_images_right, self.crouch_images_left = self.load_crouch_images()
        self.dead_image = pygame.transform.scale(
            load_image("ghost.png"), (PLAYER_WIDTH, PLAYER_HEIGHT)
        )

        self.image = self.images_right[self.index]
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y
        self.sync_dimensions()

        self.vel_y = 0
        self.jump_key_down = False
        self.direction = 1
        self.in_air = True
        self.crouching = False

    def load_crouch_images(self):
        crouch_candidates = (
            "guy_crouch.png",
            "guy_down.png",
            "guy_duck.png",
            "crouch.png",
            "duck.png",
        )

        for filename in crouch_candidates:
            if asset_path(filename).exists():
                img_right = load_image(filename)
                img_right = pygame.transform.scale(
                    img_right, (PLAYER_WIDTH, PLAYER_CROUCH_HEIGHT)
                )
                img_left = pygame.transform.flip(img_right, True, False)
                return [img_right], [img_left]

        crouch_right = pygame.transform.smoothscale(
            self.images_right[0], (PLAYER_WIDTH, PLAYER_CROUCH_HEIGHT)
        )
        crouch_left = pygame.transform.flip(crouch_right, True, False)
        return [crouch_right], [crouch_left]

    def sync_dimensions(self):
        self.width = self.rect.width
        self.height = self.rect.height

    def set_image(self, image):
        old_centerx = self.rect.centerx
        old_bottom = self.rect.bottom

        self.image = image
        if self.rect.size != image.get_size():
            self.rect = self.image.get_rect()
            self.rect.centerx = old_centerx
            self.rect.bottom = old_bottom
            self.sync_dimensions()

    def current_standing_image(self):
        return self.images_right[0] if self.direction == 1 else self.images_left[0]

    def current_crouch_image(self):
        return (
            self.crouch_images_right[0]
            if self.direction == 1
            else self.crouch_images_left[0]
        )

    def apply_idle_image(self):
        if self.crouching:
            self.set_image(self.current_crouch_image())
        else:
            self.set_image(self.current_standing_image())

    def can_stand(self, world, platform_group):
        standing_rect = self.current_standing_image().get_rect()
        standing_rect.centerx = self.rect.centerx
        standing_rect.bottom = self.rect.bottom

        for tile in world.tile_list:
            if tile[1].colliderect(standing_rect):
                return False

        for platform in platform_group:
            if platform.rect.colliderect(standing_rect):
                return False

        return True

    def set_crouching(self, crouching, world=None, platform_group=None):
        if self.crouching == crouching:
            self.apply_idle_image()
            return

        if not crouching and world is not None and platform_group is not None:
            if not self.can_stand(world, platform_group):
                return

        self.crouching = crouching
        self.index = 0
        self.counter = 0
        self.apply_idle_image()

    def try_jump(self, jump_sound):
        if self.in_air:
            return False

        self.set_crouching(False)
        self.vel_y = JUMP_STRENGTH
        self.in_air = True
        jump_sound.play()
        return True

    def handle_input(self, world, groups, sounds):
        dx = 0
        key = pygame.key.get_pressed()
        jump_pressed = key[pygame.K_SPACE] or key[pygame.K_UP]
        down_pressed = key[pygame.K_DOWN]
        moving = False

        jump_started = False
        if jump_pressed and not self.jump_key_down:
            jump_started = self.try_jump(sounds["jump"])
        self.jump_key_down = jump_pressed

        if jump_started:
            self.set_crouching(False)
        elif down_pressed and not self.in_air:
            self.set_crouching(True)
        elif not down_pressed:
            self.set_crouching(False, world, groups["platform"])

        if key[pygame.K_LEFT]:
            dx -= PLAYER_SPEED
            self.counter += 1
            self.direction = -1
            moving = True

        if key[pygame.K_RIGHT]:
            dx += PLAYER_SPEED
            self.counter += 1
            self.direction = 1
            moving = True

        self.update_animation(moving)
        return dx

    def update_animation(self, moving):
        walk_cooldown = 5

        if self.crouching:
            self.apply_idle_image()
            return

        if not moving:
            self.counter = 0
            self.index = 0
            self.apply_idle_image()
            return

        if self.counter > walk_cooldown:
            self.counter = 0
            self.index += 1
            if self.index >= len(self.images_right):
                self.index = 0

        if self.direction == 1:
            self.set_image(self.images_right[self.index])
        else:
            self.set_image(self.images_left[self.index])

    def apply_gravity(self):
        self.vel_y += GRAVITY
        if self.vel_y > MAX_FALL_SPEED:
            self.vel_y = MAX_FALL_SPEED
        return self.vel_y

    def check_world_collision(self, world, dx, dy):
        self.in_air = True

        for tile in world.tile_list:
            if tile[1].colliderect(
                self.rect.x + dx, self.rect.y, self.width, self.height
            ):
                dx = 0

            if tile[1].colliderect(
                self.rect.x, self.rect.y + dy, self.width, self.height
            ):
                if self.vel_y < 0:
                    dy = tile[1].bottom - self.rect.top
                    self.vel_y = 0
                elif self.vel_y >= 0:
                    dy = tile[1].top - self.rect.bottom
                    self.vel_y = 0
                    self.in_air = False

        return dx, dy

    def check_platform_collision(self, platform_group, dx, dy):
        col_thresh = 20

        for platform in platform_group:
            if platform.rect.colliderect(
                self.rect.x + dx, self.rect.y, self.width, self.height
            ):
                dx = 0

            if platform.rect.colliderect(
                self.rect.x, self.rect.y + dy, self.width, self.height
            ):
                if abs((self.rect.top + dy) - platform.rect.bottom) < col_thresh:
                    self.vel_y = 0
                    dy = platform.rect.bottom - self.rect.top
                elif abs((self.rect.bottom + dy) - platform.rect.top) < col_thresh:
                    self.rect.bottom = platform.rect.top - 1
                    self.in_air = False
                    dy = 0

                if platform.move_x != 0:
                    self.rect.x += platform.move_direction

        return dx, dy

    def update(self, game_over, world, groups, sounds, surface):
        dx = 0
        dy = 0

        if game_over == 0:
            dx = self.handle_input(world, groups, sounds)
            dy = self.apply_gravity()
            dx, dy = self.check_world_collision(world, dx, dy)
            dx, dy = self.check_platform_collision(groups["platform"], dx, dy)

            self.rect.x += dx
            self.rect.y += dy

            if self.in_air and self.crouching:
                self.set_crouching(False)

            if pygame.sprite.spritecollide(self, groups["blob"], False):
                game_over = -1
                sounds["game_over"].play()

            if pygame.sprite.spritecollide(self, groups["lava"], False):
                game_over = -1
                sounds["game_over"].play()

            if pygame.sprite.spritecollide(self, groups["exit"], False):
                game_over = 1

        elif game_over == -1:
            self.set_image(self.dead_image)
            if self.rect.y > 200:
                self.rect.y -= 5

        surface.blit(self.image, self.rect)
        return game_over


class World:
    def __init__(self, data, groups):
        self.tile_list = []

        dirt_img = load_image("dirt.png")
        grass_img = load_image("grass.png")

        row_count = 0
        for row in data:
            col_count = 0
            for tile in row:
                x = col_count * TILE_SIZE
                y = row_count * TILE_SIZE

                if tile == 1:
                    img = pygame.transform.scale(dirt_img, (TILE_SIZE, TILE_SIZE))
                    img_rect = img.get_rect()
                    img_rect.x = x
                    img_rect.y = y
                    self.tile_list.append((img, img_rect))
                if tile == 2:
                    img = pygame.transform.scale(grass_img, (TILE_SIZE, TILE_SIZE))
                    img_rect = img.get_rect()
                    img_rect.x = x
                    img_rect.y = y
                    self.tile_list.append((img, img_rect))
                if tile == 3:
                    blob = Enemy(x, y + 5)
                    groups["blob"].add(blob)
                if tile == 4:
                    platform = Platform(x, y, 1, 0)
                    groups["platform"].add(platform)
                if tile == 5:
                    platform = Platform(x, y, 0, 1)
                    groups["platform"].add(platform)
                if tile == 6:
                    lava = Lava(x, y + (TILE_SIZE // 2))
                    groups["lava"].add(lava)
                if tile == 7:
                    coin = Coin(x + (TILE_SIZE // 2), y + (TILE_SIZE // 2))
                    groups["coin"].add(coin)
                if tile == 8:
                    exit_sprite = Exit(x, y - (TILE_SIZE // 2))
                    groups["exit"].add(exit_sprite)
                col_count += 1
            row_count += 1

    def draw(self, surface):
        for tile in self.tile_list:
            surface.blit(tile[0], tile[1])


class Enemy(pygame.sprite.Sprite):
    def __init__(self, x, y):
        pygame.sprite.Sprite.__init__(self)
        self.image = load_image("blob.png")
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y
        self.move_direction = 1
        self.move_counter = 0

    def update(self):
        self.rect.x += self.move_direction
        self.move_counter += 1
        if abs(self.move_counter) > 35:
            self.move_direction *= -1
            self.move_counter *= -1


class Platform(pygame.sprite.Sprite):
    def __init__(self, x, y, move_x, move_y):
        pygame.sprite.Sprite.__init__(self)
        img = load_image("platform.png")
        self.image = pygame.transform.scale(img, (TILE_SIZE, TILE_SIZE // 2))
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y
        self.move_counter = 0
        self.move_direction = 1
        self.move_x = move_x
        self.move_y = move_y

    def update(self):
        self.rect.x += self.move_direction * self.move_x
        self.rect.y += self.move_direction * self.move_y
        self.move_counter += 1
        if abs(self.move_counter) > 50:
            self.move_direction *= -1
            self.move_counter *= -1


class Lava(pygame.sprite.Sprite):
    def __init__(self, x, y):
        pygame.sprite.Sprite.__init__(self)
        img = load_image("lava.png")
        self.image = pygame.transform.scale(img, (TILE_SIZE, TILE_SIZE // 2))
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y


class Coin(pygame.sprite.Sprite):
    def __init__(self, x, y):
        pygame.sprite.Sprite.__init__(self)
        img = load_image("coin.png")
        self.image = pygame.transform.scale(img, (TILE_SIZE // 2, TILE_SIZE // 2))
        self.rect = self.image.get_rect()
        self.rect.center = (x, y)


class Exit(pygame.sprite.Sprite):
    def __init__(self, x, y):
        pygame.sprite.Sprite.__init__(self)
        img = load_image("exit.png")
        self.image = pygame.transform.scale(img, (TILE_SIZE, int(TILE_SIZE * 1.5)))
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y


def main():
    pygame.mixer.pre_init(44100, -16, 2, 512)
    pygame.init()
    init_audio()

    clock = pygame.time.Clock()
    display_surface = pygame.display.set_mode(
        get_initial_window_size(), pygame.RESIZABLE
    )
    pygame.display.set_caption("Coin Catcher!!")
    virtual_surface = pygame.Surface((BASE_WIDTH, BASE_HEIGHT)).convert()

    font = pygame.font.SysFont("Bauhaus 93", 70)
    font_score = pygame.font.SysFont("Bauhaus 93", 30)

    sun_img = load_image("sun.png")
    bg_img = pygame.transform.scale(
        load_image("sky.png", use_alpha=False), (BASE_WIDTH, BASE_HEIGHT)
    )
    restart_img = load_image("restart_btn.png")
    start_img = load_image("start_btn.png")
    exit_img = load_image("exit_btn.png")

    start_music("music.wav")
    sounds = {
        "coin": load_sound("coin.wav"),
        "jump": load_sound("jump.wav"),
        "game_over": load_sound("game_over.wav"),
    }

    game_over = 0
    main_menu = True
    level = 1
    max_levels = 7
    score = 0

    groups = create_sprite_groups()
    player = Player(50, BASE_HEIGHT - 110)
    world = World(load_level_data(level), groups)

    score_coin = Coin(TILE_SIZE // 2, TILE_SIZE // 2)
    groups["coin"].add(score_coin)

    restart_button = Button(BASE_WIDTH // 2 - 50, BASE_HEIGHT // 2 + 100, restart_img)
    start_button = Button(BASE_WIDTH // 2 - 350, BASE_HEIGHT // 2, start_img)
    exit_button = Button(BASE_WIDTH // 2 + 100, BASE_HEIGHT // 2, exit_img)

    run = True
    while run:
        clock.tick(FPS)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run = False
            elif event.type == pygame.VIDEORESIZE:
                display_surface = handle_resize(event)

        view = get_scaled_view(display_surface.get_size())
        virtual_mouse_pos = window_to_virtual(pygame.mouse.get_pos(), view)
        mouse_pressed = pygame.mouse.get_pressed()

        virtual_surface.blit(bg_img, (0, 0))
        virtual_surface.blit(sun_img, (100, 100))

        if main_menu:
            if exit_button.draw(virtual_surface, virtual_mouse_pos, mouse_pressed):
                run = False
            if start_button.draw(virtual_surface, virtual_mouse_pos, mouse_pressed):
                main_menu = False
        else:
            world.draw(virtual_surface)

            if game_over == 0:
                groups["blob"].update()
                groups["platform"].update()

                if pygame.sprite.spritecollide(player, groups["coin"], True):
                    score += 1
                    sounds["coin"].play()

                draw_text(
                    virtual_surface,
                    "X " + str(score),
                    font_score,
                    WHITE,
                    TILE_SIZE - 10,
                    10,
                )

            groups["blob"].draw(virtual_surface)
            groups["platform"].draw(virtual_surface)
            groups["lava"].draw(virtual_surface)
            groups["coin"].draw(virtual_surface)
            groups["exit"].draw(virtual_surface)

            game_over = player.update(game_over, world, groups, sounds, virtual_surface)

            if game_over == -1:
                draw_centered_text(
                    virtual_surface,
                    "GAME OVER!",
                    font,
                    BLUE,
                    BASE_WIDTH // 2,
                    BASE_HEIGHT // 2,
                )
                if restart_button.draw(
                    virtual_surface, virtual_mouse_pos, mouse_pressed
                ):
                    world = reset_level(level, player, groups)
                    game_over = 0
                    score = 0

            if game_over == 1:
                if level < max_levels:
                    level += 1
                    world = reset_level(level, player, groups)
                    game_over = 0
                else:
                    draw_centered_text(
                        virtual_surface,
                        "YOU WIN!",
                        font,
                        BLUE,
                        BASE_WIDTH // 2,
                        BASE_HEIGHT // 2,
                    )
                    if restart_button.draw(
                        virtual_surface, virtual_mouse_pos, mouse_pressed
                    ):
                        level = 1
                        world = reset_level(level, player, groups)
                        game_over = 0
                        score = 0

        present_virtual_surface(virtual_surface, display_surface, view)

    pygame.quit()


if __name__ == "__main__":
    main()
