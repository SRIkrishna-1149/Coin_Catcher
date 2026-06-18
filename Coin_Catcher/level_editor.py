import pickle
from pathlib import Path

import pygame

BASE_DIR = Path(__file__).resolve().parent
IMG_DIR = BASE_DIR / "img"

BASE_TILE_SIZE = 35
BASE_COLS = 20
BASE_GRID_SIZE = BASE_TILE_SIZE * BASE_COLS
BASE_MARGIN = 70
BASE_WIDTH = BASE_GRID_SIZE
BASE_HEIGHT = BASE_GRID_SIZE + BASE_MARGIN

FPS = 60
MAX_TILE_VALUE = 8
WINDOW_SAFE_SCALE = 0.88
MIN_WINDOW_WIDTH = 350
MIN_WINDOW_HEIGHT = 385

WHITE = (255, 255, 255)
GREEN = (144, 201, 120)
YELLOW = (255, 235, 130)
LETTERBOX_COLOUR = (10, 12, 18)


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


def level_file_path(level):
    return BASE_DIR / f"level{level}_data"


def create_empty_world():
    world_data = [[0 for _ in range(BASE_COLS)] for _ in range(BASE_COLS)]

    for tile in range(BASE_COLS):
        world_data[BASE_COLS - 1][tile] = 2
        world_data[0][tile] = 1
        world_data[tile][0] = 1
        world_data[tile][BASE_COLS - 1] = 1

    return world_data


def is_valid_world_data(data):
    if not isinstance(data, list) or len(data) != BASE_COLS:
        return False
    return all(isinstance(row, list) and len(row) == BASE_COLS for row in data)


def save_level_data(level, world_data):
    save_path = level_file_path(level)

    try:
        with save_path.open("wb") as file:
            pickle.dump(world_data, file)
        return "Level saved successfully"
    except OSError as exc:
        print(f"Could not save level file '{save_path}': {exc}")
        return "Could not save level data"


def load_level_data(level):
    load_path = level_file_path(level)
    if not load_path.exists():
        return None, "No saved data for this level"

    try:
        with load_path.open("rb") as file:
            loaded_data = pickle.load(file)
    except (pickle.PickleError, EOFError, OSError, AttributeError, ValueError) as exc:
        print(f"Could not load level file '{load_path}': {exc}")
        return None, "Could not load level data"

    if not is_valid_world_data(loaded_data):
        return None, "Saved level data is invalid"

    return loaded_data, "Level loaded successfully"


def get_initial_window_size():
    display_info = pygame.display.Info()
    monitor_width = display_info.current_w or BASE_WIDTH
    monitor_height = display_info.current_h or BASE_HEIGHT
    safe_width = max(1, int(monitor_width * WINDOW_SAFE_SCALE))
    safe_height = max(1, int(monitor_height * WINDOW_SAFE_SCALE))
    scale = min(safe_width / BASE_WIDTH, safe_height / BASE_HEIGHT)

    if scale <= 0:
        return BASE_WIDTH, BASE_HEIGHT

    return max(1, int(BASE_WIDTH * scale)), max(1, int(BASE_HEIGHT * scale))


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
    width = max(MIN_WINDOW_WIDTH, event.w)
    height = max(MIN_WINDOW_HEIGHT, event.h)
    return pygame.display.set_mode((width, height), pygame.RESIZABLE)


def present_editor_surface(editor_surface, display_surface, view):
    _, scaled_size, offset = view
    display_surface.fill(LETTERBOX_COLOUR)
    scaled_surface = pygame.transform.smoothscale(editor_surface, scaled_size)
    display_surface.blit(scaled_surface, offset)
    pygame.display.update()


def draw_text(surface, text, font, text_col, x, y):
    img = font.render(text, True, text_col)
    surface.blit(img, (x, y))


def load_editor_images():
    return {
        "sun": pygame.transform.scale(
            load_image("sun.png"), (BASE_TILE_SIZE, BASE_TILE_SIZE)
        ),
        "bg": pygame.transform.scale(
            load_image("sky.png", use_alpha=False), (BASE_WIDTH, BASE_GRID_SIZE)
        ),
        "dirt": pygame.transform.scale(
            load_image("dirt.png"), (BASE_TILE_SIZE, BASE_TILE_SIZE)
        ),
        "grass": pygame.transform.scale(
            load_image("grass.png"), (BASE_TILE_SIZE, BASE_TILE_SIZE)
        ),
        "blob": pygame.transform.scale(
            load_image("blob.png"), (BASE_TILE_SIZE, int(BASE_TILE_SIZE * 0.75))
        ),
        "platform_x": pygame.transform.scale(
            load_image("platform_x.png"), (BASE_TILE_SIZE, BASE_TILE_SIZE // 2)
        ),
        "platform_y": pygame.transform.scale(
            load_image("platform_y.png"), (BASE_TILE_SIZE, BASE_TILE_SIZE // 2)
        ),
        "lava": pygame.transform.scale(
            load_image("lava.png"), (BASE_TILE_SIZE, BASE_TILE_SIZE // 2)
        ),
        "coin": pygame.transform.scale(
            load_image("coin.png"), (BASE_TILE_SIZE // 2, BASE_TILE_SIZE // 2)
        ),
        "exit": pygame.transform.scale(
            load_image("exit.png"), (BASE_TILE_SIZE, int(BASE_TILE_SIZE * 1.5))
        ),
        "save": load_image("save_btn.png"),
        "load": load_image("load_btn.png"),
    }


def draw_grid(surface):
    for c in range(BASE_COLS + 1):
        pygame.draw.line(
            surface,
            WHITE,
            (c * BASE_TILE_SIZE, 0),
            (c * BASE_TILE_SIZE, BASE_GRID_SIZE),
        )
        pygame.draw.line(
            surface,
            WHITE,
            (0, c * BASE_TILE_SIZE),
            (BASE_WIDTH, c * BASE_TILE_SIZE),
        )


def draw_world(surface, world_data, images):
    for row in range(BASE_COLS):
        for col in range(BASE_COLS):
            tile = world_data[row][col]
            x = col * BASE_TILE_SIZE
            y = row * BASE_TILE_SIZE

            if tile == 1:
                surface.blit(images["dirt"], (x, y))
            elif tile == 2:
                surface.blit(images["grass"], (x, y))
            elif tile == 3:
                surface.blit(images["blob"], (x, y + (BASE_TILE_SIZE // 4)))
            elif tile == 4:
                surface.blit(images["platform_x"], (x, y))
            elif tile == 5:
                surface.blit(images["platform_y"], (x, y))
            elif tile == 6:
                surface.blit(images["lava"], (x, y + (BASE_TILE_SIZE // 2)))
            elif tile == 7:
                surface.blit(
                    images["coin"],
                    (x + (BASE_TILE_SIZE // 4), y + (BASE_TILE_SIZE // 4)),
                )
            elif tile == 8:
                surface.blit(images["exit"], (x, y - (BASE_TILE_SIZE // 2)))


def edit_tile_at_pos(world_data, virtual_pos, mouse_button):
    if virtual_pos is None:
        return False

    mouse_x, mouse_y = virtual_pos
    if not (0 <= mouse_x < BASE_GRID_SIZE and 0 <= mouse_y < BASE_GRID_SIZE):
        return False

    col = mouse_x // BASE_TILE_SIZE
    row = mouse_y // BASE_TILE_SIZE

    if mouse_button == 1:
        world_data[row][col] = (world_data[row][col] + 1) % (MAX_TILE_VALUE + 1)
        return True

    if mouse_button == 3:
        world_data[row][col] = (world_data[row][col] - 1) % (MAX_TILE_VALUE + 1)
        return True

    return False


class Button:
    def __init__(self, x, y, image):
        self.image = image
        self.rect = self.image.get_rect()
        self.rect.topleft = (x, y)
        self.clicked = False

    def update(self, mouse_pos, mouse_pressed):
        action = False

        if mouse_pos is not None and self.rect.collidepoint(mouse_pos):
            if mouse_pressed[0] and not self.clicked:
                action = True
                self.clicked = True

        if not mouse_pressed[0]:
            self.clicked = False

        return action

    def draw(self, surface):
        surface.blit(self.image, self.rect)


def main():
    pygame.init()

    clock = pygame.time.Clock()
    display_surface = pygame.display.set_mode(
        get_initial_window_size(), pygame.RESIZABLE
    )
    pygame.display.set_caption("Level Editor")
    editor_surface = pygame.Surface((BASE_WIDTH, BASE_HEIGHT)).convert()
    view = get_scaled_view(display_surface.get_size())

    font = pygame.font.SysFont("Futura", 24)
    status_font = pygame.font.SysFont("Futura", 18)
    images = load_editor_images()

    world_data = create_empty_world()
    clicked = False
    level = 1
    status_message = "Ready"

    save_button = Button(BASE_WIDTH - 190, BASE_GRID_SIZE + 14, images["save"])
    load_button = Button(BASE_WIDTH - 100, BASE_GRID_SIZE + 14, images["load"])

    run = True
    while run:
        clock.tick(FPS)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run = False
            elif event.type == pygame.VIDEORESIZE:
                display_surface = handle_resize(event)
                view = get_scaled_view(display_surface.get_size())
            elif event.type == pygame.MOUSEBUTTONDOWN and not clicked:
                clicked = True
                virtual_pos = window_to_virtual(event.pos, view)
                edit_tile_at_pos(world_data, virtual_pos, event.button)
            elif event.type == pygame.MOUSEBUTTONUP:
                clicked = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    level += 1
                    status_message = f"Editing level {level}"
                elif event.key == pygame.K_DOWN:
                    if level > 1:
                        level -= 1
                        status_message = f"Editing level {level}"
                    else:
                        status_message = "Level cannot go below 1"

        virtual_mouse_pos = window_to_virtual(pygame.mouse.get_pos(), view)
        mouse_pressed = pygame.mouse.get_pressed()

        if save_button.update(virtual_mouse_pos, mouse_pressed):
            status_message = save_level_data(level, world_data)

        if load_button.update(virtual_mouse_pos, mouse_pressed):
            loaded_data, status_message = load_level_data(level)
            if loaded_data is not None:
                world_data = loaded_data

        editor_surface.fill(GREEN)
        editor_surface.blit(images["bg"], (0, 0))
        editor_surface.blit(images["sun"], (BASE_TILE_SIZE * 2, BASE_TILE_SIZE * 2))

        draw_world(editor_surface, world_data, images)
        draw_grid(editor_surface)

        save_button.draw(editor_surface)
        load_button.draw(editor_surface)

        draw_text(
            editor_surface,
            f"Level: {level}",
            font,
            WHITE,
            BASE_TILE_SIZE,
            BASE_GRID_SIZE + 5,
        )
        draw_text(
            editor_surface,
            "Press UP or DOWN to change level",
            font,
            WHITE,
            BASE_TILE_SIZE,
            BASE_GRID_SIZE + 28,
        )
        draw_text(
            editor_surface,
            status_message,
            status_font,
            YELLOW,
            BASE_TILE_SIZE,
            BASE_GRID_SIZE + 52,
        )

        present_editor_surface(editor_surface, display_surface, view)

    pygame.quit()


if __name__ == "__main__":
    main()
