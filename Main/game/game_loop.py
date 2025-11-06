import pygame
import sys
import json
import os
import random
import time
import math
from .settings import SCREEN_SIZE, CENTER, MIN_SCALE, MAX_SCALE
from .paths import CUSTOM_FONT_PATH, CLICK_SOUND_PATH, BACK_SOUND_PATH
from .assets import resource_path


income = 0


# Safe audio helpers to avoid crashes on systems without a working audio backend
def _safe_set_volume(sound_obj, vol):
    try:
        if sound_obj is not None:
            pygame.mixer.Sound.set_volume(sound_obj, vol)
    except Exception:
        pass


def _safe_play(sound_obj):
    try:
        if sound_obj is not None:
            sound_obj.play()
    except Exception:
        pass


def _safe_music_pause():
    try:
        pygame.mixer.music.pause()
    except Exception:
        pass


def _safe_music_unpause():
    try:
        pygame.mixer.music.unpause()
    except Exception:
        pass

# Monkey-patch pygame.mixer.Sound.set_volume to be safe (ignore None / backend errors)
try:
    _orig_set_volume = pygame.mixer.Sound.set_volume
    def _wrapped_set_volume(sound_obj, vol):
        try:
            if sound_obj is not None:
                _orig_set_volume(sound_obj, vol)
        except Exception:
            pass
    pygame.mixer.Sound.set_volume = _wrapped_set_volume
except Exception:
    # if pygame or mixer not initialized, ignore
    pass

# Particle system global config and pool
MAX_PARTICLES = 700
_particle_pool = []  # list of recycled particle dicts


# ensure draw_particles cache exists at module import-time
def _ensure_particle_cache():
    if not hasattr(draw_particles, "cache"):
        draw_particles.cache = {}


def spawn_particles(particles_list, position, color, count=16):
    """Append simple particle dicts to particles_list."""
    # enforce a global particle cap to avoid storms
    allowed = max(0, MAX_PARTICLES - len(particles_list))
    to_spawn = min(count, allowed)
    for i in range(to_spawn):
        # reuse particle dicts from pool when available
        if _particle_pool:
            p = _particle_pool.pop()
        else:
            p = {}
        angle = random.uniform(0, math.tau if hasattr(math, "tau") else 2 * math.pi)
        speed = random.uniform(60, 220)
        vx = math.cos(angle) * speed
        vy = math.sin(angle) * speed
        lifetime = random.uniform(0.5, 1.2)
        radius = random.randint(2, 5)
        p.update(
            {
                "pos": [float(position[0]), float(position[1])],
                "vel": [vx, vy],
                "life": lifetime,
                "max_life": lifetime,
                "color": color,
                "r": radius,
            }
        )
        particles_list.append(p)


def update_particles(particles_list, dt):
    # simple physics: velocity, gravity, life decay
    g = 300.0
    i = 0
    while i < len(particles_list):
        p = particles_list[i]
        p["vel"][1] += g * dt
        p["pos"][0] += p["vel"][0] * dt
        p["pos"][1] += p["vel"][1] * dt
        p["life"] -= dt
        if p["life"] <= 0:
            # recycle into pool
            dead = particles_list.pop(i)
            # clear big list items to avoid holding refs
            dead.clear()
            _particle_pool.append(dead)
        else:
            i += 1


def draw_particles(surface, particles_list):
    # ensure cache exists
    _ensure_particle_cache()
    cache = draw_particles.cache
    for p in particles_list:
        life_ratio = max(0.0, min(1.0, p["life"] / (p.get("max_life", 1.0) or 1.0)))
        alpha = int(255 * life_ratio)
        # soften size over life for nicer fade
        r = max(1, int(p["r"] * (0.6 + 0.4 * life_ratio)))
        color = p["color"]
        # key: (r, r,g,b)
        color_key = (r, color[0], color[1], color[2])

        if color_key not in cache:
            surf = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            # draw circle with the target color directly (no per-blit tinting)
            pygame.draw.circle(surf, (color[0], color[1], color[2], 255), (r, r), r)
            cache[color_key] = surf

        base = cache[color_key]
        # create a lightweight copy to set alpha without expensive blit tinting
        draw_surf = base.copy()
        draw_surf.set_alpha(alpha)
        surface.blit(draw_surf, (int(p["pos"][0] - r), int(p["pos"][1] - r)))


# create a cached background gradient to avoid per-frame fill calls
def _get_bg_gradient(size):
    if not hasattr(_get_bg_gradient, "cache"):
        _get_bg_gradient.cache = {}
    key = tuple(size)
    if key in _get_bg_gradient.cache:
        return _get_bg_gradient.cache[key]
    surf = pygame.Surface(size)
    # vertical gradient from darker to lighter
    top = (12, 28, 18)
    bottom = (40, 70, 48)
    for y in range(size[1]):
        t = y / max(1, size[1] - 1)
        col = (
            int(top[0] * (1 - t) + bottom[0] * t),
            int(top[1] * (1 - t) + bottom[1] * t),
            int(top[2] * (1 - t) + bottom[2] * t),
        )
        pygame.draw.line(surf, col, (0, y), (size[0], y))
    _get_bg_gradient.cache[key] = surf
    return surf


def smooth_damp(
    current, target, current_velocity, smooth_time, dt, max_speed=float("inf")
):
    """SmoothDamp like Unity. Returns (new_position, new_velocity).

    smooth_time: roughly the time it takes to reach the target — larger = smoother/slower.
    """
    # Based on typical SmoothDamp implementation
    if smooth_time < 1e-4:
        return target, 0.0

    omega = 2.0 / smooth_time
    x = omega * dt
    exp = 1.0 / (1.0 + x + 0.48 * x * x + 0.235 * x * x * x)

    change = current - target
    original_to = target

    # clamp max speed
    max_change = max_speed * smooth_time
    if change > max_change:
        change = max_change
    elif change < -max_change:
        change = -max_change

    target = current - change
    temp = (current_velocity + omega * change) * dt
    new_velocity = (current_velocity - omega * temp) * exp
    new_position = target + (change + temp) * exp

    # prevent overshooting
    if (original_to - current) * (new_position - original_to) > 0:
        new_position = original_to
        new_velocity = 0.0

    return new_position, new_velocity


# legacy draw_button removed; use enhanced draw_button below

# global button states for hover/press animations
button_states = {}


def draw_button(
    surface,
    rect,
    bg_color,
    border_color,
    text,
    font,
    dt,
    effect_name=None,
    text_color=(255, 255, 255),
):
    """Draw button with hover glow and press animation.

    effect_name: unique key for this button to retain animation state across frames
    dt: delta time for anim updates
    """
    # Initialize or fetch state. We'll use a spring-damper model for natural shake
    if effect_name:
        state = button_states.setdefault(
            effect_name,
            {
                "hover_val": 0.0,  # smoothed hover value
                "hover_vel": 0.0,
                "press": 0.0,  # press impulse (legacy)
                "press_impulse": 0.0,
                "scale": 1.0,
                "scale_vel": 0.0,
                "vel": 0.0,  # current horizontal velocity of shake
                "pos": 0.0,  # current horizontal offset
            },
        )
    else:
        state = {
            "hover_val": 0.0,
            "hover_vel": 0.0,
            "press": 0.0,
            "press_impulse": 0.0,
            "scale": 1.0,
            "scale_vel": 0.0,
            "vel": 0.0,
            "pos": 0.0,
        }

    mouse_over = rect.collidepoint(pygame.mouse.get_pos())
    target = 1.0 if mouse_over else 0.0
    # smooth approach to hover using SmoothDamp for frame-rate independent smoothing
    hover_cur = state.get("hover_val", 0.0)
    hover_vel = state.get("hover_vel", 0.0)
    hover_smooth_time = 0.06  # smaller = snappier, larger = smoother
    new_hover, new_hover_vel = smooth_damp(
        hover_cur, target, hover_vel, hover_smooth_time, dt, max_speed=20.0
    )
    state["hover_val"] = new_hover
    state["hover_vel"] = new_hover_vel

    # Apply press decay
    state["press"] = max(0.0, state.get("press", 0.0) - dt * 3.0)

    # Use SmoothDamp for very smooth motion. position follows the smoothed hover value
    desired_offset = 8.0 * state.get("hover_val", 0.0)  # pixels target
    # slightly snappier position smoothing for responsive feel
    smooth_time = 0.055
    cur = state.get("pos", 0.0)
    cur_vel = state.get("vel", 0.0)
    new_pos, new_vel = smooth_damp(
        cur, desired_offset, cur_vel, smooth_time, dt, max_speed=1500.0
    )
    state["pos"] = new_pos
    state["vel"] = new_vel

    # press scale: small squash when pressed
    press_scale = 1.0 - 0.045 * state["press"]

    # Draw scaled rect at its shaken position; do not draw twice (avoid ghosting)
    w, h = rect.width, rect.height
    sw, sh = int(w * press_scale), int(h * press_scale)
    sx = rect.centerx - sw // 2 + int(round(state["pos"]))
    sy = rect.centery - sh // 2
    draw_rect = pygame.Rect(sx, sy, sw, sh)

    # Render base button once at base size and cache it. Minor per-frame scaling
    # (for press animation) will not bust the cache.
    base_w, base_h = rect.width, rect.height
    if not hasattr(draw_button, "button_cache"):
        draw_button.button_cache = {}
    cache_key = (text, id(font), base_w, base_h, bg_color, border_color, text_color)
    base_surf = draw_button.button_cache.get(cache_key)
    if base_surf is None:
        base_surf = pygame.Surface((base_w, base_h), pygame.SRCALPHA)
        pygame.draw.rect(
            base_surf, bg_color, pygame.Rect(0, 0, base_w, base_h), border_radius=6
        )
        pygame.draw.rect(
            base_surf,
            border_color,
            pygame.Rect(0, 0, base_w, base_h),
            2,
            border_radius=6,
        )
        text_surf = font.render(text, True, text_color)
        txt_rect = text_surf.get_rect(center=(base_w // 2, base_h // 2))
        base_surf.blit(text_surf, txt_rect)
        draw_button.button_cache[cache_key] = base_surf

    # Handle press animation as a target scale using SmoothDamp for smoothness
    # press impulse decays quickly
    press_impulse = state.get("press_impulse", 0.0)
    # If previous code set numeric 'press', map it to impulse (backcompat)
    if state.get("press", 0.0) > 0 and press_impulse <= 0:
        press_impulse = state.get("press", 0.0)
    # decay impulse
    press_impulse = max(0.0, press_impulse - dt * 6.0)
    state["press_impulse"] = press_impulse

    target_scale = 1.0 - 0.06 * press_impulse
    cur_scale = state.get("scale", 1.0)
    cur_scale_vel = state.get("scale_vel", 0.0)
    new_scale, new_scale_vel = smooth_damp(
        cur_scale, target_scale, cur_scale_vel, 0.08, dt, max_speed=8.0
    )
    state["scale"] = new_scale
    state["scale_vel"] = new_scale_vel

    # Compute final drawn size from smoothed scale
    sw, sh = max(1, int(base_w * new_scale)), max(1, int(base_h * new_scale))

    # scale the base surface for current frame. Use smoothscale for quality
    if sw == base_w and sh == base_h:
        btn_surf = base_surf
    else:
        try:
            btn_surf = pygame.transform.smoothscale(base_surf, (sw, sh))
        except Exception:
            btn_surf = pygame.transform.scale(base_surf, (sw, sh))

    surface.blit(btn_surf, draw_rect.topleft)

    # compute text_rect for callers (centered on the drawn button)
    text_rect = btn_surf.get_rect(center=draw_rect.center)

    if effect_name:
        button_states[effect_name] = state

    return text_rect


def safe_load_sound(path, default_volume=0.08):
    try:
        s = pygame.mixer.Sound(resource_path(path))
        _safe_set_volume(s, default_volume)
        return s
    except Exception:
        # Return a dummy sound object with a no-op play() to avoid checks everywhere
        class _DummySound:
            def play(self, *a, **k):
                return None

        return _DummySound()


def run_loop(screen, clock, assets):
    """Ana oyun döngüsü. Ekranda animasyon ve para sayacını günceller."""

    random_weather_change = random.randint(1, 3)
    weather_multiplier = 1.0
    # Try to initialize music; on headless/Linux/Wine installs this may fail.
    music_enabled = True
    try:
        try:
            pygame.mixer.music.load(resource_path(BACK_SOUND_PATH))
            pygame.mixer.music.play(-1)  # Sonsuz döngüde çal
            pygame.mixer.music.set_volume(0.01596705)  # Ses seviyesini ayarla (0.0 - 1.0)
        except Exception:
            # Ignore music backend errors on platforms like Wine/Linux headless
            pass
    except Exception:
        music_enabled = False
    panel_open = False
    panel_scale = 0
    panel_speed = 0.1
    sound_on_image = pygame.image.load(
        resource_path("Assets/images/musicOn.png")
    ).convert_alpha()
    sound_off_image = pygame.image.load(
        resource_path("Assets/images/musicOff.png")
    ).convert_alpha()
    sound_on_image = pygame.transform.scale(sound_on_image, (30, 30))
    sound_off_image = pygame.transform.scale(sound_off_image, (30, 30))
    current_sound_state = "on"
    sound_image = sound_on_image

    # Oyun verilerini yükleme
    game_data = load_game_data()
    money = game_data.get("money", 0)
    multiplier = game_data.get("multiplier", 1)
    auto_income = game_data.get("auto_income", 0.0)
    total_clicks = game_data.get("total_clicks", 0)
    afk_upgrade_cost = game_data.get("afk_upgrade_cost", 150)
    multiplier_upgrade_cost = game_data.get("multiplier_upgrade_cost", 150)
    highest_money = game_data.get("highest_money", 0)
    current_grass_index = game_data.get("current_grass_index", 0)
    weather_index = game_data.get("weather_index", 0)

    # Assets dictionary'den gerekli görselleri ve fontu al
    grass_img_original = assets["grass_img"]
    custom_font = assets["custom_font"]
    font_path = resource_path(CUSTOM_FONT_PATH)
    small_font = pygame.font.Font(font_path, 18)  # Daha küçük fontlar kullan
    extra_small_font = pygame.font.Font(font_path, 14)  # Extra küçük font
    medium_font = pygame.font.Font(font_path, 22)  # Orta boyut

    # Farklı çim görselleri
    grass_images = [grass_img_original]  # İlk görsel varsayılan
    grass_costs = [
        0,
        10000,
        50000,
        200000,
        300000,
        500000,
    ]  # Farklı çim görsellerinin fiyatları
    grass_names = [
        "Normal Grass",
        "Golden Grass",
        "Frozen Grass",
        "Diamond Grass",
        "Mystic Grass",
        "Blackhole Grass",
    ]  # Çim isimleri

    # Altın çim oluştur
    golden_grass = grass_img_original.copy()
    for x in range(golden_grass.get_width()):
        for y in range(golden_grass.get_height()):
            color = golden_grass.get_at((x, y))
            if color.a != 0:  # Sadece görünür pikselleri işle
                # Yeşil değerleri altın tonlarına dönüştür
                green_value = color.g
                new_color = pygame.Color(
                    min(255, int(green_value * 1.2)),  # Kırmızı bileşeni artır
                    min(255, int(green_value * 0.9)),  # Yeşil bileşeni biraz azalt
                    min(255, int(green_value * 0.3)),  # Mavi bileşeni azalt
                )
                golden_grass.set_at((x, y), new_color)
    grass_images.append(golden_grass)

    # Gökkuşağı çim oluştur
    rainbow_grass = grass_img_original.copy()
    for x in range(rainbow_grass.get_width()):
        for y in range(rainbow_grass.get_height()):
            color = rainbow_grass.get_at((x, y))
            if color.a != 0:  # Sadece görünür pikselleri işle
                # Yeşil değerleri gökkuşağı tonlarına dönüştür
                green_value = color.g
                new_color = pygame.Color(
                    min(255, int(green_value * 0.3)),  # Kırmızı bileşeni artır
                    min(255, int(green_value * 1.1)),  # Yeşil bileşeni biraz azalt
                    min(255, int(green_value * 5)),  # Mavi bileşeni azalt
                )
                rainbow_grass.set_at((x, y), new_color)
    grass_images.append(rainbow_grass)

    # Elmas çim oluştur
    diamond_grass = grass_img_original.copy()
    for x in range(diamond_grass.get_width()):
        for y in range(diamond_grass.get_height()):
            color = diamond_grass.get_at((x, y))
            if color.a != 0:  # Sadece görünür pikselleri işle
                # Yeşil değerleri elmas tonlarına dönüştür
                green_value = color.g
                new_color = pygame.Color(
                    min(255, int(green_value * 0.1)),  # Kırmızı bileşeni artır
                    min(255, int(green_value * 1)),  # Yeşil bileşeni biraz azalt
                    min(255, int(green_value * 1.8)),  # Mavi bileşeni azalt
                )
                diamond_grass.set_at((x, y), new_color)
    grass_images.append(diamond_grass)

    # Gizemli çim oluştur
    # Mystic Grass oluştur
    mystic_grass = grass_img_original.copy()
    for x in range(mystic_grass.get_width()):
        for y in range(mystic_grass.get_height()):
            color = mystic_grass.get_at((x, y))
            if color.a != 0:  # Sadece görünür pikselleri işle
                # Yeşil değerleri gizemli tonlara dönüştür
                green_value = color.g
                new_color = pygame.Color(
                    min(255, int(green_value * 0.5)),  # Kırmızı bileşeni azalt
                    min(255, int(green_value * 0.2)),  # Yeşil bileşeni azalt
                    min(255, int(green_value * 1.5)),  # Mavi bileşeni artır
                )
                mystic_grass.set_at((x, y), new_color)
    grass_images.append(mystic_grass)

    # Blackhole Grass oluştur
    blackhole_grass = grass_img_original.copy()
    for x in range(blackhole_grass.get_width()):
        for y in range(blackhole_grass.get_height()):
            color = blackhole_grass.get_at((x, y))
            if color.a != 0:  # Sadece görünür pikselleri işle
                # Yeşil değerleri siyah delik tonlarına dönüştür
                green_value = color.g
                new_color = pygame.Color(
                    min(255, int(green_value * 0.1)),  # Kırmızı bileşeni azalt
                    min(255, int(green_value * 0.1)),  # Yeşil bileşeni azalt
                    min(255, int(green_value * 0.1)),  # Mavi bileşeni azalt
                )
                blackhole_grass.set_at((x, y), new_color)
    grass_images.append(blackhole_grass)

    # Aktif çim görselini ayarla
    if current_grass_index < len(grass_images):
        active_grass_img = grass_images[current_grass_index]
    else:
        active_grass_img = grass_images[0]
        current_grass_index = 0

    # sesleri yükle ve çal
    try:
        pygame.mixer.music.load(resource_path(BACK_SOUND_PATH))
        pygame.mixer.music.play(-1)  # Sonsuz döngüde çal
        pygame.mixer.music.set_volume(0.01596705)  # Ses seviyesini ayarla (0.0 - 1.0)
    except Exception:
        pass
    # use configured CLICK_SOUND_PATH constant when available
    click_effect = safe_load_sound(CLICK_SOUND_PATH) or safe_load_sound(
        "assets/sounds/click.mp3"
    )
    weather_change_effect = safe_load_sound("assets/sounds/change.mp3")
    buy_effect = safe_load_sound("assets/sounds/buy.mp3")

    weather_index = 0  # Hava durumu indeksi
    weather_timer = 0  # Hava durumu zamanlayıcısı

    # Başlangıç ayarları
    scale_factor = 1.0  # Orijinal boyutta başla
    rotation_angle = 0  # Başlangıç dönüş açısı
    rotation_direction = 1  # Dönüş yönü (1: saat yönü, -1: ters yön)
    scale_direction = 1  # Ölçek yönü (1: büyüt, -1: küçült)

    # Resmin konumunu belirle
    grass_rect = active_grass_img.get_rect()
    grass_rect.center = CENTER

    # Buton ayarları
    afk_button_rect = pygame.Rect(0, 0, 0, 0)  # Başlangıçta boş, sonra güncellenecek
    multiplier_button_rect = pygame.Rect(
        0, 0, 0, 0
    )  # Başlangıçta boş, sonra güncellenecek
    save_button_rect = pygame.Rect(0, 0, 0, 0)  # Başlangıçta boş, sonra güncellenecek
    stats_button_rect = pygame.Rect(0, 0, 0, 0)  # Başlangıçta boş, sonra güncellenecek
    shop_button_rect = pygame.Rect(0, 0, 0, 0)  # Başlangıçta boş, sonra güncellenecek

    # Renk tanımları - Pixel art tarzı için daha canlı renkler
    BACKGROUND_COLOR = (20, 38, 24)
    TEXT_COLOR = (240, 240, 240)  # Daha parlak beyaz
    BUTTON_BORDER_COLOR = (255, 255, 255)
    AFK_BUTTON_COLOR = (30, 144, 255)  # Mavi
    MULTIPLIER_BUTTON_COLOR = (14, 176, 14)  # Yeşil
    SAVE_BUTTON_COLOR = (255, 165, 0)  # Turuncu
    STATS_BUTTON_COLOR = (138, 43, 226)  # Mor
    SHOP_BUTTON_COLOR = (255, 105, 180)  # Pembe
    MONEY_COLOR = (255, 215, 0)  # Altın rengi
    STATS_COLOR = (200, 200, 200)  # Gri

    # Panel ayarları - Daha geniş panel
    stats_panel_rect = pygame.Rect(10, 10, 235, 182)

    CURRENT_BG = 0

    weather_panel_rect = pygame.Rect(10, 360, 180, 70)

    # Wipe Save butonu ayarları
    wipe_button_rect = pygame.Rect(0, 0, 80, 30)  # Küçük buton
    wipe_button_rect.bottomright = (
        SCREEN_SIZE[0] - 10,
        SCREEN_SIZE[1] - 10,
    )  # Sağ alt köşe

    # İstatistik ekranı ve mağaza ekranı görünürlüğü
    show_stats = False
    show_shop = False
    # non-blocking save message timer (seconds)
    save_msg_timer = 0.0
    save_msg_text = None

    running = True
    particles = []
    anim_time = 0.0
    while running:
        # Try to run up to 144 FPS for high-refresh displays. Use busy loop when available.
        try:
            ms = clock.tick_busy_loop(144)
        except Exception:
            ms = clock.tick(144)
        dt = ms / 1000.0
        # clamp dt to avoid huge steps
        if dt > 0.1:
            dt = 0.1
        anim_time += dt
        # Otomatik gelir eklemesi
        money += auto_income * dt
        # Update particle physics before rendering so visuals reflect current state
        update_particles(particles, dt)

        # En yüksek para miktarını güncelley
        if money > highest_money:
            highest_money = money

        # draw cached gradient background for nicer visuals
        bg = _get_bg_gradient(SCREEN_SIZE)
        screen.blit(bg, (0, 0))

        # İstatistik paneli çizimi - Pixel art tarzı için daha belirgin kenarlar
        pygame.draw.rect(screen, (40, 58, 44), stats_panel_rect, border_radius=3)
        pygame.draw.rect(screen, (80, 98, 84), stats_panel_rect, 2, border_radius=3)

        ez = SCREEN_SIZE[0] - 132, 558, 35, 35

        pygame.draw.rect(screen, (20, 38, 24), ez, border_radius=3)

        screen.blit(sound_image, (SCREEN_SIZE[0] - 130, 560))

        pygame.draw.rect(screen, (35, 58, 23), weather_panel_rect, border_radius=3)
        pygame.draw.rect(screen, (84, 98, 84), weather_panel_rect, 2, border_radius=3)

        # AFK Gelir butonu çizimi
        padding = 8  # Daha az padding
        afk_text = f"AFK Income +0.5 (${int(afk_upgrade_cost)})"
        afk_button_text_rect = (
            small_font.get_rect(afk_text) if hasattr(small_font, "get_rect") else None
        )
        afk_text_surf = small_font.render(afk_text, True, TEXT_COLOR)
        afk_text_rect = afk_text_surf.get_rect()
        button_width = afk_text_rect.width + 2 * padding
        button_height = afk_text_rect.height + 2 * padding
        afk_button_rect = pygame.Rect(0, 0, button_width, button_height)
        afk_button_rect.topright = (SCREEN_SIZE[0] - 20, 20)

        deneme_text_surf = extra_small_font.render("Test", True, TEXT_COLOR)
        deneme_text_rect = deneme_text_surf.get_rect()
        button_width = deneme_text_rect.width + 2 * padding
        button_height = deneme_text_rect.height + 2 * padding
        deneme_button_rect = pygame.Rect(0, 0, button_width, button_height)
        deneme_button_rect.topright = (
            SCREEN_SIZE[0] - 20,
            wipe_button_rect.top - 38,
        )  # Daha az boşluk
        deneme_text_rect.center = deneme_button_rect.center

        multiplier_text = (
            f"Click Power x{multiplier + 0.5} (${int(multiplier_upgrade_cost)})"
        )
        multiplier_text_surf = small_font.render(multiplier_text, True, TEXT_COLOR)
        multiplier_text_rect = multiplier_text_surf.get_rect()
        button_width = multiplier_text_rect.width + 2 * padding
        button_height = multiplier_text_rect.height + 2 * padding
        multiplier_button_rect = pygame.Rect(0, 0, button_width, button_height)
        multiplier_button_rect.topright = (
            SCREEN_SIZE[0] - 20,
            afk_button_rect.bottom + 8,
        )  # Daha az boşluk
        multiplier_text_rect.center = multiplier_button_rect.center

        save_text = "Save Game"
        save_text_surf = small_font.render(save_text, True, TEXT_COLOR)
        save_text_rect = save_text_surf.get_rect()
        button_width = save_text_rect.width + 2 * padding
        button_height = save_text_rect.height + 2 * padding
        save_button_rect = pygame.Rect(0, 0, button_width, button_height)
        save_button_rect.topright = (
            SCREEN_SIZE[0] - 20,
            multiplier_button_rect.bottom + 8,
        )  # Daha az boşluk
        save_text_rect.center = save_button_rect.center

        stats_text = "Statistics"
        stats_text_surf = small_font.render(stats_text, True, TEXT_COLOR)
        stats_text_rect = stats_text_surf.get_rect()
        button_width = stats_text_rect.width + 2 * padding
        button_height = stats_text_rect.height + 2 * padding
        stats_button_rect = pygame.Rect(0, 0, button_width, button_height)
        stats_button_rect.topright = (
            SCREEN_SIZE[0] - 20,
            save_button_rect.bottom + 8,
        )  # Daha az boşluk
        stats_text_rect.center = stats_button_rect.center

        weather_timer += dt
        if weather_timer >= 50:  # 50 sn bekle
            _safe_set_volume(weather_change_effect, 0.0696705)
            weather_change_effect.play()
            weather_timer = 0
            random_weather_change = random.randint(0, 7)
            if (
                random_weather_change == 3
                or random_weather_change == 4
                or random_weather_change == 5
            ):
                weather_index = 1
                weather_multiplier = 1.3
            elif random_weather_change == 6 or random_weather_change == 7:
                weather_index = 2
                weather_multiplier = 1.5

            elif random_weather_change == 8:
                weather_index = 3
                weather_multiplier = 1.90

            elif (
                random_weather_change == 0
                or random_weather_change == 1
                or random_weather_change == 2
            ):
                weather_index = 0
                weather_multiplier = 1.0

        shop_text = "Grass Shop"
        shop_text_surf = small_font.render(shop_text, True, TEXT_COLOR)
        shop_text_rect = shop_text_surf.get_rect()
        button_width = shop_text_rect.width + 2 * padding
        button_height = shop_text_rect.height + 2 * padding
        shop_button_rect = pygame.Rect(0, 0, button_width, button_height)
        shop_button_rect.topright = (
            SCREEN_SIZE[0] - 20,
            stats_button_rect.bottom + 8,
        )  # Daha az boşluk
        shop_text_rect.center = shop_button_rect.center

        # Draw AFK button
        draw_button(
            screen,
            afk_button_rect,
            AFK_BUTTON_COLOR,
            BUTTON_BORDER_COLOR,
            afk_text,
            small_font,
            dt,
            effect_name="afk",
        )

        # Çarpan butonu çizimi
        draw_button(
            screen,
            multiplier_button_rect,
            MULTIPLIER_BUTTON_COLOR,
            BUTTON_BORDER_COLOR,
            multiplier_text,
            small_font,
            dt,
            effect_name="mult",
        )

        # Kaydet butonu çizimi
        draw_button(
            screen,
            save_button_rect,
            SAVE_BUTTON_COLOR,
            BUTTON_BORDER_COLOR,
            save_text,
            small_font,
            dt,
            effect_name="save",
        )

        # İstatistik butonu çizimi
        draw_button(
            screen,
            stats_button_rect,
            STATS_BUTTON_COLOR,
            BUTTON_BORDER_COLOR,
            stats_text,
            small_font,
            dt,
            effect_name="stats",
        )

        # Mağaza butonu çizimi
        draw_button(
            screen,
            shop_button_rect,
            SHOP_BUTTON_COLOR,
            BUTTON_BORDER_COLOR,
            shop_text,
            small_font,
            dt,
            effect_name="shop",
        )

        weather_surface = pygame.Surface((100, 30))

        # Wipe Save butonu çizimi
        wipe_button_text = extra_small_font.render("Wipe Save", True, TEXT_COLOR)
        wipe_text_rect = wipe_button_text.get_rect()
        wipe_text_rect.center = wipe_button_rect.center

        draw_button(
            screen,
            wipe_button_rect,
            (200, 0, 0),
            BUTTON_BORDER_COLOR,
            "Wipe Save",
            extra_small_font,
            dt,
            effect_name="wipe",
        )

        # Smooth scale/rotation using sine for smoother motion
        # amplitude based on configured MIN/MAX
        mid_scale = (MIN_SCALE + MAX_SCALE) / 2.0
        amp = (MAX_SCALE - MIN_SCALE) / 2.0
        scale_factor = mid_scale + amp * math.sin(anim_time * 1.6)

        # rotation oscillates between -5 and +5 degrees smoothly (faster)
        rotation_angle = 5.0 * math.sin(anim_time * 1.8)

        # Grass parallax/bob for subtle motion
        bob = math.sin(anim_time * 1.2) * 6.0  # +/- pixels
        # Resmi yeniden ölçekle ve döndür
        current_width = int(active_grass_img.get_width() * scale_factor)
        current_height = int(active_grass_img.get_height() * scale_factor)
        scaled_img = pygame.transform.scale(
            active_grass_img, (current_width, current_height)
        )
        rotated_img = pygame.transform.rotate(scaled_img, rotation_angle)
        grass_rect = rotated_img.get_rect(center=(CENTER[0], CENTER[1] + int(bob)))

        sound_button = sound_image.get_rect(topleft=(SCREEN_SIZE[0] - 130, 560))
        # sound button rect

        # === İMLEÇ KONTROLÜ ===
        mouse_pos = pygame.mouse.get_pos()
        if (
            afk_button_rect.collidepoint(mouse_pos)
            or multiplier_button_rect.collidepoint(mouse_pos)
            or save_button_rect.collidepoint(mouse_pos)
            or stats_button_rect.collidepoint(mouse_pos)
            or shop_button_rect.collidepoint(mouse_pos)
            or wipe_button_rect.collidepoint(mouse_pos)
            or grass_rect.collidepoint(mouse_pos)
            or sound_button.collidepoint(mouse_pos)
        ):
            pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND)  # El işareti
        else:
            pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)  # Normal ok

        # Resmi ekrana çiz
        screen.blit(rotated_img, grass_rect.topleft)
        # draw sound icon
        screen.blit(sound_image, (SCREEN_SIZE[0] - 130, 560))

        # draw particles behind UI
        draw_particles(screen, particles)

        # draw save message if any
        if save_msg_timer > 0:
            save_msg_surf = small_font.render(
                save_msg_text or "Game Saved!", True, (255, 255, 255)
            )
            screen.blit(
                save_msg_surf,
                (SCREEN_SIZE[0] // 2 - save_msg_surf.get_width() // 2, 10),
            )

        # Kullanıcı girişlerini kontrol et
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                # Çıkış yapmadan önce oyunu kaydet
                save_game_data(
                    {
                        "money": money,
                        "multiplier": multiplier,
                        "auto_income": auto_income,
                        "total_clicks": total_clicks,
                        "afk_upgrade_cost": afk_upgrade_cost,
                        "multiplier_upgrade_cost": multiplier_upgrade_cost,
                        "highest_money": highest_money,
                        "current_grass_index": current_grass_index,
                        "weather_index": weather_index,
                    }
                )
                running = False
            if event.type == pygame.MOUSEBUTTONDOWN:
                if afk_button_rect.collidepoint(event.pos):
                    if money >= afk_upgrade_cost:
                        if current_sound_state == "on":
                            if buy_effect:
                                try:
                                    _safe_set_volume(buy_effect, 0.0896705)
                                    buy_effect.play()
                                except Exception:
                                    pass
                        # press animation + particles
                        button_states.setdefault("afk", {"hover": 0.0, "press": 0.0})[
                            "press"
                        ] = 1.0
                        spawn_particles(
                            particles, afk_button_rect.center, (60, 144, 255), count=14
                        )
                        money -= afk_upgrade_cost
                        if current_grass_index == 0:
                            auto_income += 0.5 * multiplier
                            afk_upgrade_cost *= 1.82
                        elif current_grass_index >= 1:
                            auto_income += 0.5 * multiplier * current_grass_index * 1.5
                            afk_upgrade_cost *= 1.2

                elif sound_button.collidepoint(event.pos):
                    if current_sound_state == "on":
                        # Müziği duraklat
                        try:
                            pygame.mixer.music.pause()
                        except Exception:
                            pass
                        # Tüm efekt seslerini kapat
                        if click_effect:
                            try:
                                _safe_set_volume(click_effect, 0)
                            except Exception:
                                pass
                        if weather_change_effect:
                            try:
                                _safe_set_volume(weather_change_effect, 0)
                            except Exception:
                                pass
                        if buy_effect:
                            try:
                                _safe_set_volume(buy_effect, 0)
                            except Exception:
                                pass
                        current_sound_state = "off"
                        sound_image = sound_off_image
                        screen.blit(sound_image, (SCREEN_SIZE[0] - 130, 560))

                    else:
                        # Müziği devam ettir
                        try:
                            pygame.mixer.music.unpause()
                        except Exception:
                            pass
                        # Tüm efekt seslerini aç
                        if click_effect:
                            try:
                                _safe_set_volume(click_effect, 0.0896705)
                            except Exception:
                                pass
                        if weather_change_effect:
                            try:
                                _safe_set_volume(weather_change_effect, 0.0696705)
                            except Exception:
                                pass
                        if buy_effect:
                            try:
                                _safe_set_volume(buy_effect, 0.0896705)
                            except Exception:
                                pass
                        current_sound_state = "on"
                        sound_image = sound_on_image
                        screen.blit(sound_image, (SCREEN_SIZE[0] - 130, 560))

                # end sound/multiplier/save handling

                elif multiplier_button_rect.collidepoint(event.pos):
                    if money >= multiplier_upgrade_cost:
                        if current_sound_state == "on":
                            if buy_effect:
                                try:
                                    _safe_set_volume(buy_effect, 0.0896705)
                                    buy_effect.play()
                                except Exception:
                                    pass
                        # press animation + particles
                        button_states.setdefault("mult", {"hover": 0.0, "press": 0.0})[
                            "press"
                        ] = 1.0
                        spawn_particles(
                            particles,
                            multiplier_button_rect.center,
                            (14, 176, 14),
                            count=14,
                        )
                        money -= multiplier_upgrade_cost
                        multiplier += 0.5
                        multiplier_upgrade_cost *= 1.2
                        multiplier_value = small_font.render(
                            "x " + str(multiplier), True, MULTIPLIER_BUTTON_COLOR
                        )
                        # Update stats_list to reflect new multiplier
                        stats_list = [
                            ("Total Clicks", str(total_clicks)),
                            ("Highest Money", "$" + str(int(highest_money))),
                            ("Current Money", "$" + str(int(money))),
                            ("Click Power", "x " + str(multiplier)),
                            ("AFK Income", str(round(auto_income, 1)) + " $/s"),
                            ("AFK Upgrade Cost", "$" + str(int(afk_upgrade_cost))),
                            (
                                "Multiplier Upgrade Cost",
                                "$" + str(int(multiplier_upgrade_cost)),
                            ),
                        ]
                elif save_button_rect.collidepoint(event.pos):
                    if current_sound_state == "on":
                        if click_effect:
                            try:
                                _safe_set_volume(click_effect, 0.0896705)
                            except Exception:
                                pass
                        click_effect.play()
                    # visual feedback
                    button_states.setdefault("save", {"hover": 0.0, "press": 0.0})[
                        "press"
                    ] = 1.0
                    spawn_particles(
                        particles, save_button_rect.center, (255, 165, 0), count=16
                    )
                    # Oyun verilerini kaydet
                    save_game_data(
                        {
                            "money": money,
                            "multiplier": multiplier,
                            "auto_income": auto_income,
                            "total_clicks": total_clicks,
                            "afk_upgrade_cost": afk_upgrade_cost,
                            "multiplier_upgrade_cost": multiplier_upgrade_cost,
                            "highest_money": highest_money,
                            "current_grass_index": current_grass_index,
                            "weather_index": weather_index,
                        }
                    )
                    # Non-blocking save confirmation
                    save_msg_timer = 0.9
                    save_msg_text = "Game Saved!"
                elif stats_button_rect.collidepoint(event.pos):
                    if current_sound_state == "on":
                        _safe_set_volume(click_effect, 0.0896705)
                        click_effect.play()
                    # visual feedback
                    button_states.setdefault("stats", {"hover": 0.0, "press": 0.0})[
                        "press"
                    ] = 1.0
                    spawn_particles(
                        particles, stats_button_rect.center, (138, 43, 226), count=12
                    )
                    show_stats = not show_stats  # İstatistik ekranını aç/kapat
                    show_shop = False  # Mağaza ekranını kapat
                elif shop_button_rect.collidepoint(event.pos):
                    if current_sound_state == "on":
                        _safe_set_volume(click_effect, 0.0896705)
                        click_effect.play()
                    # visual feedback
                    button_states.setdefault("shop", {"hover": 0.0, "press": 0.0})[
                        "press"
                    ] = 1.0
                    spawn_particles(
                        particles, shop_button_rect.center, (255, 105, 180), count=18
                    )
                    show_shop = not show_shop  # Mağaza ekranını aç/kapat
                    show_stats = False  # İstatistik ekranını kapat
                elif grass_rect.collidepoint(event.pos):
                    if current_sound_state == "on":
                        _safe_set_volume(click_effect, 0.0896705)
                        click_effect.play()
                    if current_grass_index == 0:
                        money += 1 * multiplier * weather_multiplier
                        total_clicks += 1
                        # spawn particles at click position (center of grass)
                        spawn_particles(
                            particles, grass_rect.center, (255, 240, 160), count=18
                        )
                    elif current_grass_index >= 1:
                        money += (
                            1
                            * multiplier
                            * current_grass_index
                            * 1.5
                            * weather_multiplier
                        )
                        total_clicks += 1
                        spawn_particles(
                            particles, grass_rect.center, (220, 255, 200), count=22
                        )
                elif wipe_button_rect.collidepoint(event.pos):
                    if current_sound_state == "on":
                        _safe_set_volume(click_effect, 0.0896705)
                        click_effect.play()
                    # visual feedback
                    button_states.setdefault("wipe", {"hover": 0.0, "press": 0.0})[
                        "press"
                    ] = 1.0
                    spawn_particles(
                        particles, wipe_button_rect.center, (200, 50, 50), count=20
                    )
                    save_dir = get_save_dir()
                    save_path = os.path.join(save_dir, "save_data.json")
                    if os.path.exists(save_path):
                        try:
                            os.remove(save_path)
                        except Exception:
                            # If remove fails, attempt ignore and continue
                            pass
                        # Oyunu sıfırla
                        money = 0
                        multiplier = 1
                        auto_income = 0.0
                        total_clicks = 0
                        afk_upgrade_cost = 200
                        multiplier_upgrade_cost = 150
                        highest_money = 0
                        current_grass_index = 0
                        active_grass_img = grass_images[current_grass_index]

        # Para değerini ve diğer bilgileri ekrana yazdır - Yazıların birbirinin içine girmesini önle
        money_text = custom_font.render("$" + str(int(money)), True, MONEY_COLOR)
        money_label = small_font.render("Money:", True, TEXT_COLOR)

        income_value = small_font.render(
            f"{auto_income * weather_multiplier:.2f} $/s", True, MONEY_COLOR
        )
        income_label = small_font.render("AFK Income:", True, TEXT_COLOR)

        multiplier_value = small_font.render(
            "x " + str(multiplier * weather_multiplier), True, MULTIPLIER_BUTTON_COLOR
        )
        multiplier_label = small_font.render("Click Power:", True, TEXT_COLOR)

        clicks_value = small_font.render(str(total_clicks), True, STATS_COLOR)
        clicks_label = small_font.render("Total Clicks:", True, TEXT_COLOR)

        # İstatistik paneline bilgileri yerleştir - Daha iyi hizalama
        screen.blit(money_label, (stats_panel_rect.x + 15, stats_panel_rect.y + 15))
        screen.blit(money_text, (stats_panel_rect.x + 15, stats_panel_rect.y + 40))

        screen.blit(income_label, (stats_panel_rect.x + 15, stats_panel_rect.y + 80))
        screen.blit(
            income_value, (stats_panel_rect.x + 150, stats_panel_rect.y + 80)
        )  # Daha fazla boşluk

        screen.blit(
            multiplier_label, (stats_panel_rect.x + 15, stats_panel_rect.y + 110)
        )
        screen.blit(
            multiplier_value, (stats_panel_rect.x + 150, stats_panel_rect.y + 110)
        )  # Daha fazla boşluk

        screen.blit(clicks_label, (stats_panel_rect.x + 15, stats_panel_rect.y + 140))
        screen.blit(
            clicks_value, (stats_panel_rect.x + 150, stats_panel_rect.y + 140)
        )  # Daha fazla boşluk

        # Hava durumu değişikliği - Her 50 saniyede bir değiştir

        # Hava Paneli

        if weather_index == 0:
            weather_text = small_font.render("Weather: Normal", True, MONEY_COLOR)
            timer_text = small_font.render(
                "Next Change: " + str(round(50 - weather_timer, 1)) + "s",
                True,
                TEXT_COLOR,
            )
        if weather_index == 1:
            weather_text = small_font.render("Weather: Sunny", True, MONEY_COLOR)
            timer_text = small_font.render(
                "Next Change: " + str(round(50 - weather_timer, 1)) + "s",
                True,
                TEXT_COLOR,
            )
        elif weather_index == 2:
            weather_text = small_font.render("Weather: Rainy", True, MONEY_COLOR)
            timer_text = small_font.render(
                "Next Change: " + str(round(50 - weather_timer, 1)) + "s",
                True,
                TEXT_COLOR,
            )
        elif weather_index == 3:
            weather_text = small_font.render("Weather: Stormy", True, MONEY_COLOR)
            timer_text = small_font.render(
                "Next Change: " + str(round(50 - weather_timer, 1)) + "s",
                True,
                TEXT_COLOR,
            )

        screen.blit(weather_text, (weather_panel_rect.x + 15, weather_panel_rect.y + 9))
        screen.blit(timer_text, (weather_panel_rect.x + 6, weather_panel_rect.y + 43))

        # İstatistik ekranını göster - Pixel art tarzı için daha keskin kenarlar
        if show_stats:
            stats_surface = pygame.Surface((500, 400))
            stats_surface.fill((30, 48, 34))
            stats_rect = stats_surface.get_rect(
                center=(SCREEN_SIZE[0] // 2, SCREEN_SIZE[1] // 2)
            )
            pygame.draw.rect(
                stats_surface, (40, 58, 44), stats_surface.get_rect(), border_radius=3
            )
            pygame.draw.rect(
                stats_surface,
                (80, 98, 84),
                stats_surface.get_rect(),
                2,
                border_radius=3,
            )

            # İstatistik başlığı
            title_text = custom_font.render("Game Statistics", True, TEXT_COLOR)
            stats_surface.blit(
                title_text,
                (stats_surface.get_width() // 2 - title_text.get_width() // 2, 20),
            )

            # İstatistik bilgileri - Daha iyi hizalama
            y_pos = 80
            line_height = 40

            stats_list = [
                ("Total Clicks", str(total_clicks)),
                ("Highest Money", "$" + str(int(highest_money))),
                ("Current Money", "$" + str(int(money))),
                ("Click Power", "x" + str(float(multiplier))),
                ("AFK Income", str(round(auto_income, 1)) + " $/s"),
                ("AFK Upgrade Cost", "$" + str(int(afk_upgrade_cost))),
                ("Multiplier Upgrade Cost", "$" + str(int(multiplier_upgrade_cost))),
            ]

            for label, value in stats_list:
                label_text = small_font.render(label + ":", True, TEXT_COLOR)
                value_text = small_font.render(value, True, MONEY_COLOR)
                stats_surface.blit(label_text, (50, y_pos))
                stats_surface.blit(value_text, (300, y_pos))
                y_pos += line_height

            # Kapat butonu - Pixel art tarzı için daha keskin kenarlar
            close_text = small_font.render("Close", True, TEXT_COLOR)
            close_rect = pygame.Rect(
                stats_surface.get_width() // 2 - 50,
                stats_surface.get_height() - 50,
                100,
                40,
            )
            pygame.draw.rect(stats_surface, (200, 50, 50), close_rect, border_radius=3)
            pygame.draw.rect(
                stats_surface, BUTTON_BORDER_COLOR, close_rect, 2, border_radius=3
            )
            stats_surface.blit(
                close_text,
                (
                    close_rect.centerx - close_text.get_width() // 2,
                    close_rect.centery - close_text.get_height() // 2,
                ),
            )

            # İstatistik ekranını ana ekrana çiz
            screen.blit(stats_surface, stats_rect.topleft)

            # Kapat butonuna tıklama kontrolü
            if event.type == pygame.MOUSEBUTTONDOWN:
                if stats_rect.collidepoint(event.pos):
                    # Kapat butonunun konumunu ana ekrana göre ayarla.
                    adjusted_close_rect = close_rect.copy()
                    adjusted_close_rect.x += stats_rect.x
                    adjusted_close_rect.y += stats_rect.y

                    if adjusted_close_rect.collidepoint(event.pos):
                        show_stats = False
                        _safe_set_volume(click_effect, 0.0896705)
                        click_effect.play()

        # Mağaza ekranını göster - Pixel art tarzı için daha keskin kenarlar.
        if show_shop:
            shop_surface = pygame.Surface((500, 605))
            shop_surface.fill((30, 48, 34))
            shop_rect = shop_surface.get_rect(
                center=(SCREEN_SIZE[0] // 2, SCREEN_SIZE[1] // 2)
            )
            pygame.draw.rect(
                shop_surface, (40, 58, 44), shop_surface.get_rect(), border_radius=3
            )
            pygame.draw.rect(
                shop_surface, (80, 98, 84), shop_surface.get_rect(), 2, border_radius=3
            )

            # Mağaza başlığı
            title_text = custom_font.render("Grass Shop", True, TEXT_COLOR)
            shop_surface.blit(
                title_text,
                (shop_surface.get_width() // 2 - title_text.get_width() // 2, 20),
            )

            # Çim seçenekleri - Daha iyi hizalama
            y_pos = 80
            item_height = 70

            for i, (name, cost) in enumerate(zip(grass_names, grass_costs)):
                # Çim öğesi arka planı - Pixel art tarzı için daha keskin kenarlar
                item_rect = pygame.Rect(50, y_pos, 400, item_height)
                if current_grass_index == i:
                    # Aktif çim için farklı renk
                    pygame.draw.rect(
                        shop_surface, (50, 100, 50), item_rect, border_radius=3
                    )
                else:
                    pygame.draw.rect(
                        shop_surface, (40, 70, 40), item_rect, border_radius=3
                    )
                pygame.draw.rect(
                    shop_surface, (60, 90, 60), item_rect, 2, border_radius=3
                )

                # Çim adı ve fiyatı
                name_text = small_font.render(name, True, TEXT_COLOR)
                shop_surface.blit(name_text, (item_rect.x + 15, item_rect.y + 10))

                if i == 0 or current_grass_index >= i:
                    status_text = small_font.render("Owned", True, (50, 205, 50))
                else:
                    status_text = small_font.render(f"Cost: ${cost}", True, MONEY_COLOR)
                shop_surface.blit(status_text, (item_rect.x + 15, item_rect.y + 40))

                # Satın alma/seçme butonu - Pixel art tarzı için daha keskin kenarlar
                if current_grass_index != i and current_grass_index >= i:
                    button_text = "Select"
                    button_color = (50, 150, 255)
                elif i > 0 and current_grass_index < i:
                    button_text = "Buy"
                    button_color = (50, 205, 50) if money >= cost else (150, 150, 150)
                else:
                    button_text = "Selected"
                    button_color = (150, 150, 150)

                button_text_render = small_font.render(button_text, True, TEXT_COLOR)
                button_rect = pygame.Rect(
                    item_rect.right - 100, item_rect.centery - 20, 80, 40
                )
                pygame.draw.rect(
                    shop_surface, button_color, button_rect, border_radius=3
                )
                pygame.draw.rect(
                    shop_surface, BUTTON_BORDER_COLOR, button_rect, 2, border_radius=3
                )
                shop_surface.blit(
                    button_text_render,
                    (
                        button_rect.centerx - button_text_render.get_width() // 2,
                        button_rect.centery - button_text_render.get_height() // 2,
                    ),
                )

                # Buton tıklama kontrolü
                if event.type == pygame.MOUSEBUTTONDOWN and shop_rect.collidepoint(
                    event.pos
                ):
                    # Butonun konumunu ana ekrana göre ayarla
                    adjusted_button_rect = button_rect.copy()
                    adjusted_button_rect.x += shop_rect.x
                    adjusted_button_rect.y += shop_rect.y

                    if adjusted_button_rect.collidepoint(event.pos):
                        if current_grass_index != i and current_grass_index >= i:
                            # Zaten sahip olunan çimi seç
                            current_grass_index = i
                            active_grass_img = grass_images[current_grass_index]
                            _safe_set_volume(click_effect, 0.0896705)
                            click_effect.play()
                        elif i > 0 and current_grass_index < i and money >= cost:
                            # Yeni çim satın al
                            money -= cost
                            current_grass_index = i
                            active_grass_img = grass_images[current_grass_index]
                            _safe_set_volume(buy_effect, 0.0896705)
                            buy_effect.play()

                y_pos += item_height + 10

            # Kapat butonu - Pixel art tarzı için daha keskin kenarlar
            close_text = small_font.render("Close", True, TEXT_COLOR)
            close_rect = pygame.Rect(
                shop_surface.get_width() // 2 - 50,
                shop_surface.get_height() - 50,
                100,
                40,
            )
            pygame.draw.rect(shop_surface, (200, 50, 50), close_rect, border_radius=3)
            pygame.draw.rect(
                shop_surface, BUTTON_BORDER_COLOR, close_rect, 2, border_radius=3
            )
            shop_surface.blit(
                close_text,
                (
                    close_rect.centerx - close_text.get_width() // 2,
                    close_rect.centery - close_text.get_height() // 2,
                ),
            )

            # Mağaza ekranını ana ekrana çiz
            screen.blit(shop_surface, shop_rect.topleft)

            # Kapat butonuna tıklama kontrolü
            if event.type == pygame.MOUSEBUTTONDOWN:
                if shop_rect.collidepoint(event.pos):
                    # Kapat butonunun konumunu ana ekrana göre ayarla
                    adjusted_close_rect = close_rect.copy()
                    adjusted_close_rect.x += shop_rect.x
                    adjusted_close_rect.y += shop_rect.y

                    if adjusted_close_rect.collidepoint(event.pos):
                        show_shop = False
                        _safe_set_volume(click_effect, 0.0896705)
                        click_effect.play()

        pygame.display.flip()

        # decrement save message timer
        if save_msg_timer > 0:
            save_msg_timer = max(0.0, save_msg_timer - dt)

    pygame.quit()
    sys.exit()


def save_game_data(data):
    """Oyun verilerini JSON formatında kaydeder."""
    try:
        # Cross-platform application data directory
        app_data = get_save_dir()
        # Ensure directory exists
        os.makedirs(app_data, exist_ok=True)
        save_path = os.path.join(app_data, "save_data.json")
        # Write atomically: write to temp file then rename
        tmp_path = save_path + ".tmp"
        # Dump pretty (multi-line, indented) JSON for readability
        pretty = json.dumps(data, indent=2, ensure_ascii=False)
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(pretty)
        os.replace(tmp_path, save_path)
        return True
    except Exception as e:
        print(f"Kaydetme hatası: {e}")
        return False


def get_save_dir():
    """Return a cross-platform directory for storing app data for TouchTheGrass.

    Windows: %LOCALAPPDATA%/TouchTheGrass
    macOS: ~/Library/Application Support/TouchTheGrass
    Linux: $XDG_DATA_HOME/TouchTheGrass or ~/.local/share/TouchTheGrass
    """
    # Prefer explicit environment variable for Windows
    local_appdata = os.getenv("LOCALAPPDATA")
    if local_appdata:
        return os.path.join(local_appdata, "TouchTheGrass")

    # macOS
    if sys.platform == "darwin":
        return os.path.join(
            os.path.expanduser("~"), "Library", "Application Support", "TouchTheGrass"
        )

    # Linux and other Unixes
    xdg = os.getenv("XDG_DATA_HOME")
    if xdg:
        return os.path.join(xdg, "TouchTheGrass")

    return os.path.join(os.path.expanduser("~"), ".local", "share", "TouchTheGrass")


def load_game_data():
    """Kaydedilmiş oyun verilerini yükler, yoksa boş bir sözlük döndürür."""
    try:
        app_data = get_save_dir()
        save_path = os.path.join(app_data, "save_data.json")
        if os.path.exists(save_path):
            with open(save_path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        print(f"Yükleme hatası: {e}")
    return {}  # Varsayılan boş veri


def colorize(image, color):
    """Bir görselin rengini değiştirir."""
    colorized = image.copy()
    colorized.fill(color, special_flags=pygame.BLEND_RGBA_MULT)
    return colorized
