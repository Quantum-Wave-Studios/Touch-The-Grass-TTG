import os
import sys
import json
import random
import math
import pygame

from .assets import resource_path
from .paths import BACK_SOUND_PATH, CLICK_SOUND_PATH, CUSTOM_FONT_PATH
from .settings import SCREEN_SIZE, CENTER, MIN_SCALE, MAX_SCALE

# Simple particle system (pooled) to support pixel-art particles.
MAX_PARTICLES = 700
_particle_pool = []


def spawn_particles(p_list, position, color, count=12):
    """Spawn simple square (pixel) particles at position.

    p_list: the active particles list (modified in place)
    position: (x,y) tuple
    color: (r,g,b)
    """
    for _ in range(count):
        if len(p_list) >= MAX_PARTICLES:
            break
        if _particle_pool:
            p = _particle_pool.pop()
            # ensure no leftover keys from previous use
            p.clear()
        else:
            p = {}

        # Determine emission style: side (horizontal), pop-up (rise then fall), or fall-first
        r = random.random()
        if r < 0.20:
            # side emission: go directly left or right with strong horizontal velocity
            dir_sign = random.choice((-1, 1))
            vx = dir_sign * random.uniform(160.0, 320.0)
            vy = random.uniform(-30.0, 30.0)
            life = random.uniform(0.6, 1.1)
            # make side particles tiny
            size = random.randint(1, 2)
            float_time = 0.0
            # keep pushing outward a bit
            side_acc = dir_sign * random.uniform(40.0, 120.0)
        elif r < 0.65:
            # pop-up particles: milder upward velocity, stronger lateral spread
            vx = random.uniform(-160.0, 160.0)
            vy = -random.uniform(70.0, 160.0)  # negative = upward on screen
            life = random.uniform(0.7, 1.3)
            # slightly larger but still small
            size = random.randint(1, 3)
            float_time = random.uniform(0.08, 0.22)  # reduced gravity window
            side_acc = random.uniform(-120.0, 120.0)
        else:
            # drifting/fall-first particles
            vx = random.uniform(-100.0, 100.0)
            vy = random.uniform(40.0, 160.0)  # positive = downward
            life = random.uniform(0.5, 1.0)
            size = random.randint(1, 3)
            float_time = 0.0
            side_acc = random.uniform(-40.0, 40.0)

        # create per-particle shade start/end for subtle tonal interpolation
        def _clamp(v):
            return max(0, min(255, int(v)))

        # small brighten/darken factors
        b_factor = random.uniform(1.02, 1.22)
        d_factor = random.uniform(0.45, 0.92)
        shade_start = [
            _clamp(color[0] * b_factor),
            _clamp(color[1] * b_factor),
            _clamp(color[2] * b_factor),
        ]
        shade_end = [
            _clamp(color[0] * d_factor),
            _clamp(color[1] * d_factor),
            _clamp(color[2] * d_factor),
        ]

        # add tiny per-channel jitter so not all particles have identical tones
        for ci in range(3):
            shade_start[ci] = _clamp(shade_start[ci] + random.randint(-8, 8))
            shade_end[ci] = _clamp(shade_end[ci] + random.randint(-12, 12))
        shade_start = tuple(shade_start)
        shade_end = tuple(shade_end)

        # Increase particle size by 36% (user request)
        size = max(1, int(round(size * 1.36)))

        # Physics tuning: per-particle drag, wind, and small oscillation for natural motion
        drag = random.uniform(0.6, 2.2)  # higher = slows quicker
        wind = random.uniform(-28.0, 28.0)
        osc_amp = random.uniform(0.0, 2.4)
        osc_freq = random.uniform(1.2, 6.0)

        # Add angular jitter to spread directions so particles don't all go identical
        try:
            ang = math.atan2(vy, vx)
        except Exception:
            ang = 0.0
        ang += random.uniform(math.radians(-35.0), math.radians(35.0))
        speed = math.hypot(vx, vy) * random.uniform(0.78, 1.18)
        vx = math.cos(ang) * speed
        vy = math.sin(ang) * speed

        # If the source color looks like grass (green-dominant), add subtle green tone variations
        is_grass = color[1] > color[0] and color[1] > color[2] and color[1] >= 60
        if is_grass and random.random() < 0.35:
            # create green-leaning shades
            g_base = max(80, color[1])
            gs = (
                _clamp(int(g_base * random.uniform(0.18, 0.55))),
                _clamp(int(g_base * random.uniform(0.85, 1.15))),
                _clamp(int(g_base * random.uniform(0.08, 0.45))),
            )
            ge = (
                _clamp(int(g_base * random.uniform(0.35, 0.78))),
                _clamp(int(g_base * random.uniform(0.42, 0.95))),
                _clamp(int(g_base * random.uniform(0.05, 0.28))),
            )
            shade_start = gs
            shade_end = ge

            # occasionally spawn a tiny vivid green fleck in addition
            if random.random() < 0.12:
                fleck = {}
                fleck["pos"] = [float(position[0]), float(position[1])]
                fleck["vel"] = [random.uniform(-80, 80), random.uniform(-60, 20)]
                fleck["life"] = random.uniform(0.45, 0.9)
                fleck["max_life"] = fleck["life"]
                fleck["color"] = (180, 255, 120)
                fleck["shade_start"] = (200, 255, 140)
                fleck["shade_end"] = (100, 160, 80)
                fleck["size"] = 1
                fleck["age"] = 0.0
                fleck["float_time"] = 0.0
                fleck["side_acc"] = random.uniform(-20, 20)
                fleck["drag"] = random.uniform(0.8, 2.2)
                fleck["wind"] = random.uniform(-10, 10)
                fleck["osc_amp"] = random.uniform(0.0, 1.2)
                fleck["osc_freq"] = random.uniform(2.0, 6.0)
                p_list.append(fleck)

        # If the source color looks yellow-ish, occasionally bias tones slightly green
        is_yellow = (
            color[0] >= 160 and color[1] >= 140 and color[2] <= 140
        ) or (color[0] > color[1] and color[1] > color[2] and color[1] >= 120)
        if is_yellow and random.random() < 0.30:
            # nudge toward greener yellows (subtle)
            gs = (
                _clamp(color[0] * random.uniform(0.92, 1.03)),
                _clamp(color[1] * random.uniform(1.06, 1.28)),
                _clamp(color[2] * random.uniform(0.45, 0.85)),
            )
            ge = (
                _clamp(color[0] * random.uniform(0.72, 0.95)),
                _clamp(color[1] * random.uniform(0.88, 1.02)),
                _clamp(color[2] * random.uniform(0.20, 0.55)),
            )
            # apply small per-channel jitter too
            gs = tuple(_clamp(c + random.randint(-6, 6)) for c in gs)
            ge = tuple(_clamp(c + random.randint(-10, 10)) for c in ge)
            shade_start = gs
            shade_end = ge

        p.update({
            "pos": [float(position[0]), float(position[1])],
            "vel": [vx, vy],
            "life": life,
            "max_life": life,
            # keep original color for reference
            "color": color,
            "shade_start": shade_start,
            "shade_end": shade_end,
            "size": size,
            "age": 0.0,
            "float_time": float_time,
            "side_acc": side_acc,
            "drag": drag,
            "wind": wind,
            "osc_amp": osc_amp,
            "osc_freq": osc_freq,
        })
        p_list.append(p)


# Audio helpers to safely call mixer functions even when mixer is unavailable
def _safe_set_volume(sound_obj, vol):
    try:
        if getattr(globals().get("game_loop", None), "MIXER_AVAILABLE", True) and sound_obj is not None:
            sound_obj.set_volume(vol)
    except Exception:
        pass


def _safe_play(sound_obj):
    try:
        if getattr(globals().get("game_loop", None), "MIXER_AVAILABLE", True) and sound_obj is not None:
            sound_obj.play()
    except Exception:
        pass


def _safe_music_pause():
    try:
        if getattr(globals().get("game_loop", None), "MIXER_AVAILABLE", True):
            pygame.mixer.music.pause()
    except Exception:
        pass


def _safe_music_unpause():
    try:
        if getattr(globals().get("game_loop", None), "MIXER_AVAILABLE", True):
            pygame.mixer.music.unpause()
    except Exception:
        pass


def update_particles(p_list, dt):
    """Simple Euler integration and pooling for expired particles.

    Particles have an 'age' and optional 'float_time' during which gravity is reduced
    so pop-up particles rise a bit then are pulled down by normal gravity.
    """
    g = 400.0
    i = 0
    while i < len(p_list):
        p = p_list[i]
        # age
        p["age"] = p.get("age", 0.0) + dt


        # improved physics:
        # - apply a gentle upward lift during float_time for pop particles
        # - otherwise apply normal gravity
        if p.get("age", 0.0) < p.get("float_time", 0.0):
            # gentle lift to accentuate a short pop
            p["vel"][1] += -g * 0.45 * dt
        else:
            p["vel"][1] += g * dt

        # apply sideways acceleration (initial push)
        p["vel"][0] += p.get("side_acc", 0.0) * dt

        # apply persistent wind
        p["vel"][0] += p.get("wind", 0.0) * dt

        # apply drag (velocity decay). Use per-particle drag; clamp multiplier to >=0
        drag = p.get("drag", 1.0)
        vd = max(0.0, 1.0 - drag * dt)
        p["vel"][0] *= vd
        # vertical drag is smaller
        p["vel"][1] *= max(0.0, 1.0 - (drag * 0.35) * dt)

        # integrate
        p["pos"][0] += p["vel"][0] * dt
        p["pos"][1] += p["vel"][1] * dt

        # small oscillation around x based on osc_amp/freq (for drawing jitter)
        # we don't modify pos permanently; draw offset will be computed in draw
        # store age-based phase if needed (no-op here, age is used by draw)

        p["life"] -= dt
        if p["life"] <= 0:
            # recycle
            p.clear()
            _particle_pool.append(p)
            p_list.pop(i)
        else:
            i += 1


def draw_particles(surface, p_list):
    """Draw particles as pixel squares using a small surface cache."""
    # cache structure: { (size,color): {"base": Surface, "alpha": {alpha_int: Surface}} }
    if not hasattr(draw_particles, "cache"):
        draw_particles.cache = {}
    cache = draw_particles.cache
    for p in p_list:
        r = p.get("size", 3)
        # interpolate color between shade_start -> shade_end based on life progression
        max_life = max(1e-6, p.get("max_life", 1.0))
        life = max(0.0, p.get("life", 0.0))
        progress = 1.0 - (life / max_life)  # 0 = birth, 1 = death

        ss = p.get("shade_start", p.get("color", (255, 255, 255)))
        se = p.get("shade_end", p.get("color", (255, 255, 255)))
        # linear interpolation
        cur_col = (
            int(ss[0] + (se[0] - ss[0]) * progress),
            int(ss[1] + (se[1] - ss[1]) * progress),
            int(ss[2] + (se[2] - ss[2]) * progress),
        )

        # round color channels to reduce cache variety (keeps memory bounded)
        rounded_col = (
            max(0, min(255, int(round(cur_col[0] / 8.0) * 8))),
            max(0, min(255, int(round(cur_col[1] / 8.0) * 8))),
            max(0, min(255, int(round(cur_col[2] / 8.0) * 8))),
        )

        # alpha based on remaining life (0..255)
        alpha = int(255 * max(0.0, life / max_life))
        alpha = max(0, min(255, alpha))

        color_key = (r, rounded_col)
        entry = cache.get(color_key)
        if entry is None:
            base = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            base.fill((rounded_col[0], rounded_col[1], rounded_col[2], 255))
            entry = {"base": base, "alpha": {}}
            cache[color_key] = entry

        alpha_map = entry["alpha"]
        draw_surf = alpha_map.get(alpha)
        if draw_surf is None:
            # create and cache this alpha variant
            draw_surf = entry["base"].copy()
            draw_surf.set_alpha(alpha)
            alpha_map[alpha] = draw_surf

        # add a small oscillation offset for natural fluttering
        osc_amp = p.get("osc_amp", 0.0)
        osc_freq = p.get("osc_freq", 0.0)
        if osc_amp and osc_freq:
            try:
                offset_x = math.sin(p.get("age", 0.0) * osc_freq) * osc_amp
            except Exception:
                offset_x = 0.0
        else:
            offset_x = 0.0

        blit_x = int(round(p["pos"][0] - r + offset_x))
        blit_y = int(round(p["pos"][1] - r))
        surface.blit(draw_surf, (blit_x, blit_y))


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
    val = draw_button.button_cache.get(cache_key)
    if val is None:
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

        # create a soft drop shadow surface (cached alongside base)
        shadow = pygame.Surface((base_w + 8, base_h + 8), pygame.SRCALPHA)
        for i, a in enumerate((48, 32, 20, 12)):
            pygame.draw.rect(
                shadow,
                (0, 0, 0, a),
                pygame.Rect(i, i, base_w + 8 - i * 2, base_h + 8 - i * 2),
                border_radius=8,
            )

        draw_button.button_cache[cache_key] = (base_surf, shadow)
    else:
        if isinstance(val, tuple):
            base_surf, shadow = val
        else:
            base_surf = val
            shadow = None
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

    # draw shadow (if cached) beneath the button
    shadow_surf = None
    if shadow is not None:
        try:
            shadow_surf = pygame.transform.smoothscale(shadow, (sw + 8, sh + 8))
        except Exception:
            try:
                shadow_surf = pygame.transform.scale(shadow, (sw + 8, sh + 8))
            except Exception:
                shadow_surf = None
    if shadow_surf is not None:
        shadow_rect = shadow_surf.get_rect(center=draw_rect.center)
        shadow_rect.x += 3
        shadow_rect.y += 4
        surface.blit(shadow_surf, shadow_rect.topleft)

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
            if getattr(globals().get("game_loop", None), "MIXER_AVAILABLE", True):
                pygame.mixer.music.load(resource_path(BACK_SOUND_PATH))
                pygame.mixer.music.play(-1)  # Sonsuz döngüde çal
                pygame.mixer.music.set_volume(
                    0.01596705
                )  # Ses seviyesini ayarla (0.0 - 1.0)
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
        if getattr(globals().get("game_loop", None), "MIXER_AVAILABLE", True):
            pygame.mixer.music.load(resource_path(BACK_SOUND_PATH))
            pygame.mixer.music.play(-1)  # Sonsuz döngüde çal
            pygame.mixer.music.set_volume(
                0.01596705
            )  # Ses seviyesini ayarla (0.0 - 1.0)
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
    # Special collectibles (golden cookie like)
    specials = []
    # probabilistic spawn: chance per second to spawn a special
    SPAWN_CHANCE_PER_SECOND = 0.10
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
            _safe_play(weather_change_effect)
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

        # Draw and update specials (behind UI but above grass)
        # Use vertical bobbing, horizontal sway and subtle rotation for livelier visuals
        now_specials = []
        for s in specials:
            # vertical bobbing
            v_amp = s.get("osc_amp", 0.0)
            v_speed = s.get("osc_speed", 1.0)
            v_phase = s.get("osc_phase", 0.0)
            bob = math.sin(anim_time * v_speed + v_phase) * v_amp
            # horizontal sway
            sway_amp = s.get("sway_amp", 0.0)
            sway_speed = s.get("sway_speed", 1.0)
            sway_phase = s.get("sway_phase", 0.0)
            sway = math.sin(anim_time * sway_speed + sway_phase) * sway_amp
            # rotation (degrees) that oscillates left-right
            rot_amp = s.get("rot_amp", 0.0)
            rot_speed = s.get("rot_speed", 1.0)
            rot_phase = s.get("rot_phase", 0.0)
            angle = math.sin(anim_time * rot_speed + rot_phase) * rot_amp

            surf = s.get("surf")
            cx = int(s["pos"][0] + sway)
            cy = int(s["pos"][1] + bob)
            if surf:
                # rotate the sprite around its center
                rotated = pygame.transform.rotate(surf, angle)
                rect = rotated.get_rect(center=(cx, cy))
                screen.blit(rotated, rect.topleft)
            else:
                # fallback: draw a small gold circle whose radius reflects click area
                pygame.draw.circle(
                    screen, (240, 200, 64), (cx, cy), max(6, s.get("click_radius", 10))
                )
            if s.get("life", 0.0) > 0:
                now_specials.append(s)
        specials = now_specials

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
                # Check specials first (click to collect)
                # iterate copy because we may modify list
                for si, s in list(enumerate(specials)):
                    # account for bobbing and sway when checking click hit
                    v_amp = s.get("osc_amp", 0.0)
                    v_speed = s.get("osc_speed", 1.0)
                    v_phase = s.get("osc_phase", 0.0)
                    bob = math.sin(anim_time * v_speed + v_phase) * v_amp
                    sway_amp = s.get("sway_amp", 0.0)
                    sway_speed = s.get("sway_speed", 1.0)
                    sway_phase = s.get("sway_phase", 0.0)
                    sway = math.sin(anim_time * sway_speed + sway_phase) * sway_amp
                    sx = s.get("pos", (0, 0))[0] + sway
                    sy = s.get("pos", (0, 0))[1] + bob
                    r = s.get("click_radius", 14)
                    if (event.pos[0] - sx) ** 2 + (event.pos[1] - sy) ** 2 <= r * r:
                        # collect
                        val = s.get("value", 1000)
                        money += val
                        # spawn particles and sound feedback
                        spawn_particles(particles, (sx, sy), (255, 215, 80), count=20)
                        try:
                            _safe_play(buy_effect)
                        except Exception:
                            pass
                        # remove special
                        try:
                            specials.pop(si)
                        except Exception:
                            pass
                        # stop further click handling for this event
                        break
                if afk_button_rect.collidepoint(event.pos):
                    if money >= afk_upgrade_cost:
                        if current_sound_state == "on":
                            if buy_effect:
                                try:
                                    _safe_set_volume(buy_effect, 0.0896705)
                                    _safe_play(buy_effect)
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
                            _safe_music_pause()
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
                            _safe_music_unpause()
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
                                    _safe_play(buy_effect)
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
                        _safe_play(click_effect)
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
                        _safe_play(click_effect)
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
                        _safe_play(click_effect)
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
                        _safe_play(click_effect)
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
                        _safe_play(click_effect)
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
                        _safe_play(click_effect)

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
                            _safe_play(click_effect)
                        elif i > 0 and current_grass_index < i and money >= cost:
                            # Yeni çim satın al
                            money -= cost
                            current_grass_index = i
                            active_grass_img = grass_images[current_grass_index]
                            _safe_set_volume(buy_effect, 0.0896705)
                            _safe_play(buy_effect)

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
                        _safe_play(click_effect)

        pygame.display.flip()

        # decrement save message timer
        if save_msg_timer > 0:
            save_msg_timer = max(0.0, save_msg_timer - dt)

        # spawn/update specials (probabilistic per-second chance)
        if random.random() < SPAWN_CHANCE_PER_SECOND * dt:
            # spawn a special at a random position near the grass area
            gx = random.randint(120, SCREEN_SIZE[0] - 120)
            gy = random.randint(120, SCREEN_SIZE[1] - 220)
            # try to use asset if loaded
            gsurf = assets.get("watercan") if assets else None
            special = {
                "pos": [float(gx), float(gy)],
                "life": random.uniform(10.0, 20.0),
                "value": random.randint(800, 3500),
                # default, may be adjusted after surf scaling
                "click_radius": 18,
                "surf": None,
            }
            if gsurf:
                # cap visual size so it doesn't dominate the screen
                max_dim = 64
                gw, gh = gsurf.get_width(), gsurf.get_height()
                scale = min(0.8, max_dim / max(gw, gh)) if max(gw, gh) > 0 else 0.8
                new_w = max(8, int(gw * scale))
                new_h = max(8, int(gh * scale))
                special["surf"] = pygame.transform.smoothscale(gsurf, (new_w, new_h))
                # adjust click radius to match sprite size
                special["click_radius"] = max(18, int(max(new_w, new_h) / 2) + 4)
            # add bobbing/oscillation params for animation
            special["osc_amp"] = random.uniform(4.0, 10.0)
            special["osc_speed"] = random.uniform(0.8, 1.8)
            special["osc_phase"] = random.uniform(0.0, math.pi * 2)
            # horizontal sway parameters (left-right motion)
            special["sway_amp"] = random.uniform(6.0, 18.0)
            special["sway_speed"] = random.uniform(0.6, 1.6)
            special["sway_phase"] = random.uniform(0.0, math.pi * 2)
            # subtle rotation left-right
            special["rot_amp"] = random.uniform(6.0, 20.0)  # degrees
            special["rot_speed"] = random.uniform(0.8, 1.6)
            special["rot_phase"] = random.uniform(0.0, math.pi * 2)
            specials.append(special)

        # decay life for specials
        for s in list(specials):
            s["life"] -= dt
            if s["life"] <= 0:
                try:
                    specials.remove(s)
                except Exception:
                    pass

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
