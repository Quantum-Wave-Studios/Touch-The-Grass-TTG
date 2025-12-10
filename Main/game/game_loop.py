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
        is_yellow = (color[0] >= 160 and color[1] >= 140 and color[2] <= 140) or (
            color[0] > color[1] and color[1] > color[2] and color[1] >= 120
        )
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

        p.update(
            {
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
            }
        )
        p_list.append(p)


# Audio helpers to safely call mixer functions even when mixer is unavailable
def _safe_set_volume(sound_obj, vol):
    try:
        if (
            getattr(globals().get("game_loop", None), "MIXER_AVAILABLE", True)
            and sound_obj is not None
        ):
            sound_obj.set_volume(vol)
    except Exception:
        pass


def _safe_play(sound_obj):
    try:
        if (
            getattr(globals().get("game_loop", None), "MIXER_AVAILABLE", True)
            and sound_obj is not None
        ):
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
    # vertical gradient from darker to lighter - Mystic Nature Theme
    # vertical gradient from darker to lighter - Mystic Nature Theme (Deep Forest)
    top = (15, 25, 20)
    bottom = (30, 45, 35)
    for y in range(size[1]):
        t = y / max(1, size[1] - 1)
        col = (
            int(top[0] * (1 - t) + bottom[0] * t),
            int(top[1] * (1 - t) + bottom[1] * t),
            int(top[2] * (1 - t) + bottom[2] * t),
        )
        pygame.draw.line(surf, col, (0, y), (size[0], y))

    # Simple Vignette (darken corners) - REMOVED per user request
    # try:
    #     # Create a radial gradient approximation using a large texture scaled up
    #     vig_tex = pygame.Surface((100, 100), pygame.SRCALPHA)
    #     vig_tex.fill((0, 0, 0, 150))  # Dark corners
    #     # Clear center circle
    #     pygame.draw.circle(vig_tex, (0, 0, 0, 0), (50, 50), 45)
    #     # Scale to screen size to create soft blur effect
    #     vig_scaled = pygame.transform.smoothscale(vig_tex, size)
    #     surf.blit(vig_scaled, (0, 0))
    # except Exception:
    #     pass

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
        # Outline restored (1px) per user request
        pygame.draw.rect(
            base_surf,
            border_color,
            pygame.Rect(0, 0, base_w, base_h),
            1,
            border_radius=6,
        )
        text_surf = font.render(text, True, text_color)
        txt_rect = text_surf.get_rect(center=(base_w // 2, base_h // 2))
        base_surf.blit(text_surf, txt_rect)

        draw_button.button_cache[cache_key] = base_surf
    else:
        if isinstance(val, tuple):
            # Legacy support if cache has tuple
            base_surf, _ = val
        else:
            base_surf = val
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


def draw_panel(
    surface,
    rect,
    border_color=(100, 150, 120),
    bg_color=(30, 40, 35, 230),
    draw_shadow=True,
):
    """Draws a unified panel background with border and shadow."""
    # Shadow
    if draw_shadow:
        shadow_rect = rect.copy()
        shadow_rect.x += 4
        shadow_rect.y += 4
        s = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        pygame.draw.rect(s, (0, 0, 0, 80), s.get_rect(), border_radius=8)
        surface.blit(s, (shadow_rect.x, shadow_rect.y))

    # Background
    bg = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    pygame.draw.rect(bg, bg_color, bg.get_rect(), border_radius=8)
    surface.blit(bg, rect.topleft)

    # Border
    pygame.draw.rect(surface, border_color, rect, 2, border_radius=8)


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

    # NEW: Combo system
    combo_count = game_data.get("combo_count", 0)
    max_combo = game_data.get("max_combo", 0)
    combo_timer = 0.0
    combo_display_timer = 0.0
    COMBO_TIMEOUT = 0.47  # EXTREME MODE: Very fast clicking required!

    # NEW: Achievement system
    achievements = game_data.get("achievements", {})
    # Initialize achievements if not present
    achievement_defs = {
        "minigame_first": {"name": "Gamer", "desc": "Play a mini-game", "reward": 500},
        "minigame_master": {
            "name": "Pro Gamer",
            "desc": "Score 100+ in a mini-game",
            "reward": 2500,
        },
        "skill_first": {"name": "Learner", "desc": "Unlock a skill", "reward": 1000},
        "skill_10": {"name": "Skilled", "desc": "Unlock 10 skills", "reward": 10000},
        "skill_max": {"name": "Master", "desc": "Max out a skill", "reward": 5000},
        "wheel_first": {"name": "Lucky Spin", "desc": "Spin the wheel", "reward": 200},
        "wheel_jackpot": {
            "name": "Jackpot",
            "desc": "Hit the jackpot on wheel",
            "reward": 10000,
        },
        "first_click": {
            "name": "First Touch",
            "desc": "Click grass once",
            "reward": 10,
        },
        "click_100": {
            "name": "Getting Started",
            "desc": "Click 100 times",
            "reward": 100,
        },
        "click_1000": {
            "name": "Dedicated Clicker",
            "desc": "Click 1000 times",
            "reward": 500,
        },
        "click_10000": {
            "name": "Click Master",
            "desc": "Click 10000 times",
            "reward": 5000,
        },
        "money_1k": {"name": "First Thousand", "desc": "Earn $1,000", "reward": 50},
        "money_10k": {"name": "Big Earner", "desc": "Earn $10,000", "reward": 500},
        "money_100k": {"name": "Wealthy", "desc": "Earn $100,000", "reward": 5000},
        "money_1m": {"name": "Millionaire", "desc": "Earn $1,000,000", "reward": 50000},
        "combo_10": {"name": "Combo Starter", "desc": "Reach 10x combo", "reward": 200},
        "combo_25": {"name": "Combo Expert", "desc": "Reach 25x combo", "reward": 1000},
        "combo_50": {"name": "Combo Master", "desc": "Reach 50x combo", "reward": 5000},
        "upgrade_afk": {
            "name": "Passive Income",
            "desc": "Buy first AFK upgrade",
            "reward": 100,
        },
        "upgrade_mult": {
            "name": "Power Up",
            "desc": "Buy first multiplier upgrade",
            "reward": 100,
        },
        "buy_grass": {
            "name": "New Grass",
            "desc": "Buy a new grass type",
            "reward": 500,
        },
        "all_grass": {
            "name": "Grass Collector",
            "desc": "Own all grass types",
            "reward": 10000,
        },
        "special_collect": {
            "name": "Lucky Find",
            "desc": "Collect a special item",
            "reward": 200,
        },
        "special_10": {
            "name": "Collector",
            "desc": "Collect 10 special items",
            "reward": 2000,
        },
        "prestige_1": {
            "name": "Rebirth",
            "desc": "Prestige for the first time",
            "reward": 0,
        },
        "daily_7": {
            "name": "Week Warrior",
            "desc": "Login 7 days in a row",
            "reward": 5000,
        },
        "powerup_collect": {
            "name": "Power Player",
            "desc": "Collect a power-up",
            "reward": 300,
        },
    }

    # === PROGRAMMATIC ACHIEVEMENT GENERATION (120+ Achievements) ===
    # Click milestones: 1k, 5k, 10k, 50k, 100k, ... 1B
    click_milestones = [
        1000,
        5000,
        10000,
        50000,
        100000,
        500000,
        1000000,
        5000000,
        10000000,
        50000000,
        100000000,
        500000000,
        1000000000,
    ]
    for i, milestone in enumerate(click_milestones):
        achievement_defs[f"clicks_{milestone}"] = {
            "name": f"Click Master {i+1}",
            "desc": f"Click {milestone:,} times",
            "reward": milestone // 10,
        }

    # Money milestones: 1k, 10k, ... 1T
    money_milestones = [
        1000,
        10000,
        100000,
        1000000,
        10000000,
        100000000,
        1000000000,
        10000000000,
        100000000000,
        1000000000000,
    ]
    for i, milestone in enumerate(money_milestones):
        achievement_defs[f"money_prog_{milestone}"] = {
            "name": f"Tycoon {i+1}",
            "desc": f"Earn ${milestone:,}",
            "reward": milestone // 20,
        }

    # Playtime: 1m, 5m, 10m, 30m, 1h, 5h, 10h, 24h, 100h
    time_milestones = [60, 300, 600, 1800, 3600, 18000, 36000, 86400, 360000]
    for i, seconds in enumerate(time_milestones):
        hours = seconds / 3600
        achievement_defs[f"time_{seconds}"] = {
            "name": f"Dedicated {i+1}",
            "desc": f"Play for {hours:.1f} hours",
            "reward": 1000 * (i + 1),
        }

    # Boss kills: 1, 5, 10, 25, 50, 100
    boss_milestones = [1, 5, 10, 25, 50, 100]
    for i, count in enumerate(boss_milestones):
        achievement_defs[f"boss_kill_{count}"] = {
            "name": f"Boss Slayer {i+1}",
            "desc": f"Defeat {count} bosses",
            "reward": 5000 * (i + 1),
        }

    # Combo: 10, 20, 50, 100, 250, 500
    combo_milestones = [10, 20, 50, 100, 250, 500]
    for i, count in enumerate(combo_milestones):
        achievement_defs[f"combo_prog_{count}"] = {
            "name": f"Combo King {i+1}",
            "desc": f"Reach {count}x combo",
            "reward": 200 * count,
        }

    for ach_id, ach_data in achievement_defs.items():
        if ach_id not in achievements:
            achievements[ach_id] = {"unlocked": False, "progress": 0}

    achievement_queue = []  # Achievements to display
    achievement_display_timer = 0.0
    special_collected_count = game_data.get("special_collected_count", 0)

    # NEW: Prestige system
    prestige_level = game_data.get("prestige_level", 0)
    grass_seeds = game_data.get("grass_seeds", 0)
    prestige_multiplier = 1.0 + (prestige_level * 0.1)  # 10% per prestige
    show_prestige_menu = False

    # NEW: Power-up system
    active_powerups = []
    powerup_spawn_timer = 0.0
    POWERUP_SPAWN_INTERVAL = random.uniform(45, 90)  # Random spawn time

    # NEW: Daily rewards
    import datetime

    last_login_str = game_data.get("last_login_date", None)
    login_streak = game_data.get("login_streak", 0)
    today = datetime.date.today().isoformat()
    show_daily_reward = False
    daily_reward_amount = 0

    # Check daily reward
    if last_login_str:
        last_login = datetime.date.fromisoformat(last_login_str)
        today_date = datetime.date.today()
        days_diff = (today_date - last_login).days
        if days_diff == 1:
            login_streak += 1
        elif days_diff > 1:
            login_streak = 1
        # If same day, don't change streak
        if days_diff >= 1:
            show_daily_reward = True
            daily_reward_amount = 100 * (login_streak**1.5)
            money += daily_reward_amount
    else:
        login_streak = 1
        show_daily_reward = True
        daily_reward_amount = 100
        money += daily_reward_amount

    daily_reward_timer = 3.0 if show_daily_reward else 0.0

    # NEW: Floating damage numbers
    damage_numbers = []

    # NEW: Screen shake
    screen_shake_intensity = 0.0
    screen_shake_duration = 0.0
    screen_offset = [0, 0]

    # NEW: Notification system
    notifications = []  # {text, color, timer, y_offset}

    # NEW: Tooltips
    current_tooltip = None
    tooltip_timer = 0.0

    # NEW: Settings
    settings = game_data.get(
        "settings",
        {
            "screen_shake": True,
            "show_fps": False,
            "particle_density": 1.0,
            "master_volume": 1.0,
        },
    )
    show_settings = False

    # NEW: Auto-save
    autosave_timer = 0.0
    AUTOSAVE_INTERVAL = 30.0
    save_indicator_timer = 0.0

    # ============================================================
    # MASSIVE GAME ENHANCEMENT SYSTEMS
    # ============================================================

    # === CRITICAL HIT SYSTEM ===
    critical_hit_chance = game_data.get("critical_hit_chance", 0.05)  # 5% base chance
    critical_hit_multiplier = game_data.get("critical_hit_multiplier", 5.0)  # 5x damage
    last_critical = False
    critical_hit_count = game_data.get("critical_hit_count", 0)

    # === OFFLINE PROGRESS ===
    last_play_time_str = game_data.get("last_play_time", None)
    show_offline_progress = False
    offline_earnings = 0
    if last_play_time_str and auto_income > 0:
        try:
            last_play_time = datetime.datetime.fromisoformat(last_play_time_str)
            now = datetime.datetime.now()
            offline_seconds = (now - last_play_time).total_seconds()
            # Max 8 hours offline earnings, 50% efficiency
            max_offline_seconds = 8 * 60 * 60
            offline_seconds = min(offline_seconds, max_offline_seconds)
            if offline_seconds > 60:  # At least 1 minute away
                offline_earnings = (
                    auto_income * offline_seconds * 0.5 * prestige_multiplier
                )
                money += offline_earnings
                show_offline_progress = True
        except Exception:
            pass
    offline_progress_timer = 4.0 if show_offline_progress else 0.0

    # === MINI-GAMES SYSTEM ===
    show_minigame_menu = False
    current_minigame = None
    minigame_active = False
    minigame_timer = 0.0
    minigame_score = 0
    minigame_targets = []  # For target practice
    minigame_click_count = 0  # For click frenzy
    minigame_result = None  # Store result after game ends
    minigame_result_timer = 0.0

    # Mini-game cooldowns (can play once every 5 minutes per game)
    minigame_cooldowns = game_data.get(
        "minigame_cooldowns",
        {"click_frenzy": 0, "target_practice": 0, "golden_rush": 0},
    )
    MINIGAME_COOLDOWN = 300  # 5 minutes in seconds

    # Mini-game high scores
    minigame_high_scores = game_data.get(
        "minigame_high_scores",
        {"click_frenzy": 0, "target_practice": 0, "golden_rush": 0},
    )

    # === SKILL TREE SYSTEM ===
    show_skill_tree = False
    skill_points = game_data.get("skill_points", 0)
    skills = game_data.get(
        "skills",
        {
            # Click Power Branch
            "click_power_1": {
                "level": 0,
                "max": 10,
                "cost": 1,
                "effect": 0.1,
                "name": "Strong Fingers",
                "desc": "+10% click power per level",
            },
            "click_power_2": {
                "level": 0,
                "max": 5,
                "cost": 3,
                "effect": 0.25,
                "name": "Iron Grip",
                "desc": "+25% click power per level",
                "req": "click_power_1",
            },
            "click_power_3": {
                "level": 0,
                "max": 3,
                "cost": 10,
                "effect": 0.5,
                "name": "Diamond Touch",
                "desc": "+50% click power per level",
                "req": "click_power_2",
            },
            # AFK Branch
            "afk_power_1": {
                "level": 0,
                "max": 10,
                "cost": 1,
                "effect": 0.15,
                "name": "Patience",
                "desc": "+15% AFK income per level",
            },
            "afk_power_2": {
                "level": 0,
                "max": 5,
                "cost": 3,
                "effect": 0.3,
                "name": "Meditation",
                "desc": "+30% AFK income per level",
                "req": "afk_power_1",
            },
            "afk_power_3": {
                "level": 0,
                "max": 3,
                "cost": 10,
                "effect": 0.5,
                "name": "Zen Master",
                "desc": "+50% AFK income per level",
                "req": "afk_power_2",
            },
            # Luck Branch
            "luck_1": {
                "level": 0,
                "max": 10,
                "cost": 2,
                "effect": 0.02,
                "name": "Lucky",
                "desc": "+2% critical chance per level",
            },
            "luck_2": {
                "level": 0,
                "max": 5,
                "cost": 5,
                "effect": 0.5,
                "name": "Fortune",
                "desc": "+0.5x critical multiplier per level",
                "req": "luck_1",
            },
            "luck_3": {
                "level": 0,
                "max": 3,
                "cost": 15,
                "effect": 0.1,
                "name": "Golden Touch",
                "desc": "+10% special spawn rate per level",
                "req": "luck_2",
            },
            # Combo Branch
            "combo_1": {
                "level": 0,
                "max": 10,
                "cost": 2,
                "effect": 0.05,
                "name": "Quick Hands",
                "desc": "+0.05s combo timeout per level",
            },
            "combo_2": {
                "level": 0,
                "max": 5,
                "cost": 5,
                "effect": 0.1,
                "name": "Combo King",
                "desc": "+10% combo multiplier per level",
                "req": "combo_1",
            },
        },
    )

    # Calculate skill bonuses
    def calculate_skill_bonus(skill_id, skills_dict):
        skill = skills_dict.get(skill_id, {})
        return skill.get("level", 0) * skill.get("effect", 0)

    # === BOSS BATTLE SYSTEM ===
    show_boss = False
    boss_active = False
    boss_hp = 0
    boss_max_hp = 0
    boss_timer = 0.0
    boss_spawn_timer = game_data.get("boss_spawn_timer", 300.0)  # 5 minutes
    BOSS_SPAWN_INTERVAL = 300.0  # 5 minutes
    boss_level = game_data.get("boss_level", 1)
    boss_defeated_count = game_data.get("boss_defeated_count", 0)
    boss_animation_timer = 0.0
    boss_hit_flash = 0.0

    # Boss types with different stats
    boss_types = [
        {
            "name": "Grass Golem",
            "hp_mult": 1.0,
            "reward_mult": 1.0,
            "color": (100, 180, 100),
        },
        {
            "name": "Stone Giant",
            "hp_mult": 1.5,
            "reward_mult": 1.3,
            "color": (150, 150, 150),
        },
        {
            "name": "Crystal Titan",
            "hp_mult": 2.0,
            "reward_mult": 1.6,
            "color": (100, 200, 255),
        },
        {
            "name": "Shadow Beast",
            "hp_mult": 2.5,
            "reward_mult": 2.0,
            "color": (80, 50, 100),
        },
        {
            "name": "Golden Dragon",
            "hp_mult": 3.0,
            "reward_mult": 3.0,
            "color": (255, 200, 50),
        },
    ]
    current_boss_type = None

    # === LUCKY WHEEL SYSTEM ===
    show_lucky_wheel = False
    wheel_spinning = False
    wheel_angle = 0.0
    wheel_target_angle = 0.0
    wheel_speed = 0.0
    wheel_result = None
    wheel_result_timer = 0.0
    free_spins_today = game_data.get("free_spins_today", 1)
    last_spin_date = game_data.get("last_spin_date", None)

    # Reset free spins if new day
    if last_spin_date != today:
        free_spins_today = 1

    wheel_prizes = [
        {
            "name": "2x Money",
            "type": "money_mult",
            "value": 2,
            "color": (100, 200, 100),
        },
        {"name": "+$1000", "type": "money", "value": 1000, "color": (255, 215, 0)},
        {
            "name": "5x Money",
            "type": "money_mult",
            "value": 5,
            "color": (100, 255, 100),
        },
        {"name": "+$5000", "type": "money", "value": 5000, "color": (255, 200, 50)},
        {
            "name": "10x Money",
            "type": "money_mult",
            "value": 10,
            "color": (50, 255, 50),
        },
        {"name": "+$10000", "type": "money", "value": 10000, "color": (255, 150, 50)},
        {
            "name": "Skill Point",
            "type": "skill_point",
            "value": 1,
            "color": (150, 100, 255),
        },
        {
            "name": "Double AFK 5min",
            "type": "powerup",
            "value": 300,
            "color": (100, 150, 255),
        },
    ]

    # === SEASONAL EVENTS (DISABLED per user request) ===
    # current_month = datetime.date.today().month
    seasonal_event = None
    seasonal_multiplier = 1.0
    seasonal_colors = None

    # === ENHANCED VISUAL EFFECTS ===
    rainbow_mode = False
    rainbow_timer = 0.0
    trail_particles = []
    explosion_particles = []
    weather_particles = []
    glow_intensity = 0.0

    # === STATISTICS TRACKING ===
    stats_data = game_data.get(
        "stats",
        {
            "total_playtime": 0.0,
            "total_money_earned": 0,
            "total_clicks_all_time": 0,
            "highest_single_click": 0,
            "highest_combo_ever": 0,
            "bosses_defeated": 0,
            "minigames_played": 0,
            "skills_purchased": 0,
            "wheels_spun": 0,
            "critical_hits": 0,
        },
    )
    session_start_time = datetime.datetime.now()

    # === ENHANCED ACHIEVEMENTS (50+ total) ===
    enhanced_achievement_defs = {
        # Click milestones (tiered)
        "click_100k": {
            "name": "Click Legend",
            "desc": "Click 100,000 times",
            "reward": 25000,
            "tier": "gold",
        },
        "click_1m": {
            "name": "Click God",
            "desc": "Click 1,000,000 times",
            "reward": 500000,
            "tier": "platinum",
        },
        # Money milestones
        "money_10m": {
            "name": "Multi-Millionaire",
            "desc": "Earn $10,000,000",
            "reward": 500000,
            "tier": "platinum",
        },
        "money_100m": {
            "name": "Billionaire",
            "desc": "Earn $100,000,000",
            "reward": 5000000,
            "tier": "diamond",
        },
        # Combo achievements
        "combo_100": {
            "name": "Combo Legend",
            "desc": "Reach 100x combo",
            "reward": 25000,
            "tier": "gold",
        },
        "combo_200": {
            "name": "Combo God",
            "desc": "Reach 200x combo",
            "reward": 100000,
            "tier": "platinum",
        },
        # Critical hit achievements
        "crit_first": {
            "name": "Critical Start",
            "desc": "Get first critical hit",
            "reward": 100,
            "tier": "bronze",
        },
        "crit_100": {
            "name": "Critical Expert",
            "desc": "Get 100 critical hits",
            "reward": 5000,
            "tier": "silver",
        },
        "crit_1000": {
            "name": "Critical Master",
            "desc": "Get 1000 critical hits",
            "reward": 50000,
            "tier": "gold",
        },
        # Boss achievements
        "boss_first": {
            "name": "Boss Slayer",
            "desc": "Defeat first boss",
            "reward": 5000,
            "tier": "silver",
        },
        "boss_10": {
            "name": "Boss Hunter",
            "desc": "Defeat 10 bosses",
            "reward": 25000,
            "tier": "gold",
        },
        "boss_50": {
            "name": "Boss Destroyer",
            "desc": "Defeat 50 bosses",
            "reward": 100000,
            "tier": "platinum",
        },
        # Mini-game achievements
        "minigame_first": {
            "name": "Game On",
            "desc": "Play first mini-game",
            "reward": 500,
            "tier": "bronze",
        },
        "minigame_master": {
            "name": "Mini Master",
            "desc": "Score 100+ in any mini-game",
            "reward": 10000,
            "tier": "gold",
        },
        # Skill tree achievements
        "skill_first": {
            "name": "Learner",
            "desc": "Unlock first skill",
            "reward": 500,
            "tier": "bronze",
        },
        "skill_10": {
            "name": "Skilled",
            "desc": "Unlock 10 skills",
            "reward": 5000,
            "tier": "silver",
        },
        "skill_max": {
            "name": "Master of All",
            "desc": "Max out a skill branch",
            "reward": 50000,
            "tier": "gold",
        },
        # Wheel achievements
        "wheel_first": {
            "name": "Lucky Spinner",
            "desc": "Spin the wheel",
            "reward": 200,
            "tier": "bronze",
        },
        "wheel_jackpot": {
            "name": "Jackpot!",
            "desc": "Win 10x on wheel",
            "reward": 25000,
            "tier": "gold",
        },
        # Prestige achievements
        "prestige_5": {
            "name": "Transcendent",
            "desc": "Reach prestige 5",
            "reward": 50000,
            "tier": "gold",
        },
        "prestige_10": {
            "name": "Eternal",
            "desc": "Reach prestige 10",
            "reward": 250000,
            "tier": "platinum",
        },
        # Time achievements
        "playtime_1h": {
            "name": "Dedicated",
            "desc": "Play for 1 hour total",
            "reward": 1000,
            "tier": "bronze",
        },
        "playtime_10h": {
            "name": "Committed",
            "desc": "Play for 10 hours total",
            "reward": 25000,
            "tier": "gold",
        },
        # Login achievements
        "daily_30": {
            "name": "Monthly Warrior",
            "desc": "Login 30 days in a row",
            "reward": 50000,
            "tier": "gold",
        },
        # Secret achievements
        "secret_1": {
            "name": "???",
            "desc": "Secret achievement",
            "reward": 10000,
            "tier": "secret",
        },
        "secret_2": {
            "name": "???",
            "desc": "Secret achievement",
            "reward": 50000,
            "tier": "secret",
        },
    }

    # Merge enhanced achievements into main dict
    for ach_id, ach_data in enhanced_achievement_defs.items():
        if ach_id not in achievement_defs:
            achievement_defs[ach_id] = ach_data
        if ach_id not in achievements:
            achievements[ach_id] = {"unlocked": False, "progress": 0}

    # === POWER-UP DEFINITIONS ===
    powerup_types = [
        {
            "name": "2x Click Power",
            "type": "click_boost",
            "multiplier": 2.0,
            "duration": 30,
            "color": (255, 100, 100),
        },
        {
            "name": "5x Click Power",
            "type": "click_boost",
            "multiplier": 5.0,
            "duration": 15,
            "color": (255, 50, 50),
        },
        {
            "name": "2x AFK Income",
            "type": "afk_boost",
            "multiplier": 2.0,
            "duration": 60,
            "color": (100, 100, 255),
        },
        {
            "name": "Money Rain",
            "type": "money_rain",
            "multiplier": 100,
            "duration": 20,
            "color": (255, 215, 0),
        },
        {
            "name": "Rainbow Mode",
            "type": "rainbow",
            "multiplier": 1,
            "duration": 30,
            "color": (255, 100, 255),
        },
        {
            "name": "Critical Boost",
            "type": "crit_boost",
            "multiplier": 0.2,
            "duration": 45,
            "color": (255, 200, 100),
        },
    ]

    # === PRESTIGE BUTTON ===
    show_prestige_confirm = False
    prestige_button_rect = pygame.Rect(0, 0, 100, 30)

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
    # Removed Mini-Games, Skills, Wheel buttons definition
    # minigame_button_rect = ...
    # skills_button_rect = ...
    # wheel_button_rect = ...

    # Renk tanımları - Pixel art tarzı için daha canlı renkler
    # Renk tanımları - Mystic Nature Theme
    BACKGROUND_COLOR = (20, 30, 25)  # Deep Forest Green
    TEXT_COLOR = (240, 255, 245)  # Off-white
    BUTTON_BORDER_COLOR = (100, 150, 120)

    # Modern Palette
    AFK_BUTTON_COLOR = (45, 120, 180)  # Muted Blue
    MULTIPLIER_BUTTON_COLOR = (60, 160, 60)  # Forest Green
    SAVE_BUTTON_COLOR = (200, 140, 40)  # Amber
    STATS_BUTTON_COLOR = (120, 60, 180)  # Deep Purple
    SHOP_BUTTON_COLOR = (200, 80, 120)  # Rose

    MONEY_COLOR = (255, 215, 0)  # Gold
    STATS_COLOR = (180, 200, 190)  # Sage Grey
    PANEL_BG_COLOR = (20, 25, 30, 230)  # Clean Dark Slate

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

        # NEW: Update combo timer
        if combo_count > 0:
            combo_timer -= dt
            if combo_timer <= 0:
                # Combo broken
                if combo_count > 5:
                    add_notification(
                        notifications,
                        f"Combo broken! Max: {combo_count}x",
                        (255, 100, 100),
                    )
                combo_count = 0
                combo_timer = 0.0

        # NEW: Update notifications
        update_notifications(notifications, dt)

        # NEW: Update damage numbers
        update_damage_numbers(damage_numbers, dt)

        # NEW: Update screen shake
        screen_shake_duration = update_screen_shake(
            screen_offset, screen_shake_intensity, screen_shake_duration, dt
        )

        # NEW: Update achievement display
        if achievement_queue and achievement_display_timer <= 0:
            achievement_display_timer = 3.0  # Show for 3 seconds
        if achievement_display_timer > 0:
            achievement_display_timer -= dt
            if achievement_display_timer <= 0 and achievement_queue:
                achievement_queue.pop(0)
                if achievement_queue:
                    achievement_display_timer = 3.0

        # NEW: Update daily reward display
        if daily_reward_timer > 0:
            daily_reward_timer -= dt

        # NEW: Update power-ups
        for powerup in active_powerups[:]:
            powerup["duration"] -= dt
            if powerup["duration"] <= 0:
                active_powerups.remove(powerup)
                add_notification(
                    notifications, f"{powerup['name']} expired!", (200, 200, 200)
                )

        # NEW: Auto-save system
        autosave_timer += dt
        if autosave_timer >= AUTOSAVE_INTERVAL:
            autosave_timer = 0.0
            save_indicator_timer = 1.0
            # Save game
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
                    "combo_count": 0,  # Don't save active combo
                    "max_combo": max_combo,
                    "achievements": achievements,
                    "prestige_level": prestige_level,
                    "grass_seeds": grass_seeds,
                    "special_collected_count": special_collected_count,
                    "last_login_date": today,
                    "login_streak": login_streak,
                    "settings": settings,
                    # NEW: Enhanced game data
                    "critical_hit_count": critical_hit_count,
                    "skill_points": skill_points,
                    "skills": skills,
                    "boss_level": boss_level,
                    "boss_spawn_timer": boss_spawn_timer,
                    "boss_defeated_count": boss_defeated_count,
                    "minigame_cooldowns": minigame_cooldowns,
                    "minigame_high_scores": minigame_high_scores,
                    "free_spins_today": free_spins_today,
                    "last_spin_date": last_spin_date,
                    "stats": stats_data,
                    "last_play_time": datetime.datetime.now().isoformat(),
                }
            )

        if save_indicator_timer > 0:
            save_indicator_timer -= dt

        # Otomatik gelir eklemesi
        afk_mult = 1.0
        afk_skill_bonus = (
            1.0
            + calculate_skill_bonus("afk_power_1", skills)
            + calculate_skill_bonus("afk_power_2", skills)
            + calculate_skill_bonus("afk_power_3", skills)
        )
        for powerup in active_powerups:
            if powerup["type"] == "afk_boost":
                afk_mult = powerup["multiplier"]
            if powerup["type"] == "money_rain":
                money += powerup["multiplier"] * dt  # Money rain effect
        money += (
            auto_income
            * dt
            * afk_mult
            * prestige_multiplier
            * seasonal_multiplier
            * afk_skill_bonus
        )

        # === BOSS SPAWN TIMER ===
        if not boss_active and not minigame_active:
            boss_spawn_timer -= dt
            if boss_spawn_timer <= 0:
                # Spawn boss!
                boss_active = True
                boss_spawn_timer = BOSS_SPAWN_INTERVAL
                boss_timer = 60.0  # 60 seconds to defeat boss
                current_boss_type = boss_types[min(boss_level - 1, len(boss_types) - 1)]
                boss_max_hp = int(1000 * boss_level * current_boss_type["hp_mult"])
                boss_hp = boss_max_hp
                boss_animation_timer = 0.0
                add_notification(
                    notifications,
                    f"BOSS: {current_boss_type['name']} appeared!",
                    (255, 50, 50),
                )
                if settings.get("screen_shake", True):
                    screen_shake_intensity, screen_shake_duration = (
                        trigger_screen_shake(15, 0.5)
                    )

        # === UPDATE BOSS ===
        if boss_active:
            boss_timer -= dt
            boss_animation_timer += dt
            if boss_hit_flash > 0:
                boss_hit_flash -= dt * 3

            if boss_timer <= 0:
                # Boss escaped
                boss_active = False
                add_notification(notifications, f"Boss escaped!", (255, 150, 50))
                boss_spawn_timer = BOSS_SPAWN_INTERVAL

        # === UPDATE RAINBOW MODE ===
        rainbow_mode = False
        for powerup in active_powerups:
            if powerup["type"] == "rainbow":
                rainbow_mode = True
                rainbow_timer += dt

        # === UPDATE MINIGAME COOLDOWNS ===
        for game_name in minigame_cooldowns:
            if minigame_cooldowns[game_name] > 0:
                minigame_cooldowns[game_name] -= dt

        # === UPDATE MINIGAME ===
        if minigame_active and current_minigame:
            minigame_timer -= dt

            if current_minigame == "target_practice":
                # Spawn random targets
                if len(minigame_targets) < 5 and random.random() < 2 * dt:
                    target = {
                        "x": random.randint(150, SCREEN_SIZE[0] - 150),
                        "y": random.randint(150, SCREEN_SIZE[1] - 150),
                        "radius": random.randint(15, 35),
                        "life": random.uniform(1.5, 3.0),
                        "color": (
                            random.randint(100, 255),
                            random.randint(100, 255),
                            random.randint(50, 150),
                        ),
                    }
                    minigame_targets.append(target)

                # Update targets
                for target in minigame_targets[:]:
                    target["life"] -= dt
                    if target["life"] <= 0:
                        minigame_targets.remove(target)

            elif current_minigame == "golden_rush":
                # Spawn falling gold coins
                if len(minigame_targets) < 8 and random.random() < 3 * dt:
                    coin = {
                        "x": random.randint(100, SCREEN_SIZE[0] - 100),
                        "y": -20,
                        "vy": random.uniform(100, 200),
                        "radius": 15,
                        "value": random.randint(1, 5),
                    }
                    minigame_targets.append(coin)

                # Update coins
                for coin in minigame_targets[:]:
                    coin["y"] += coin["vy"] * dt
                    if coin["y"] > SCREEN_SIZE[1] + 20:
                        minigame_targets.remove(coin)

            # Check if minigame ended
            if minigame_timer <= 0:
                minigame_active = False
                minigame_result = {"game": current_minigame, "score": minigame_score}
                minigame_result_timer = 3.0

                # Calculate reward
                reward = minigame_score * 50 * (1 + prestige_level * 0.1)
                money += reward

                # Check high score
                if minigame_score > minigame_high_scores.get(current_minigame, 0):
                    minigame_high_scores[current_minigame] = minigame_score
                    add_notification(
                        notifications,
                        f"NEW HIGH SCORE: {minigame_score}!",
                        (255, 215, 0),
                    )

                # Check achievements
                stats_data["minigames_played"] = (
                    stats_data.get("minigames_played", 0) + 1
                )
                if stats_data["minigames_played"] == 1 and not achievements.get(
                    "minigame_first", {}
                ).get("unlocked", False):
                    reward_ach = check_achievement(
                        achievements,
                        achievement_defs,
                        "minigame_first",
                        achievement_queue,
                        notifications,
                        money,
                    )
                    money += reward_ach
                if minigame_score >= 100 and not achievements.get(
                    "minigame_master", {}
                ).get("unlocked", False):
                    reward_ach = check_achievement(
                        achievements,
                        achievement_defs,
                        "minigame_master",
                        achievement_queue,
                        notifications,
                        money,
                    )
                    money += reward_ach

                add_notification(
                    notifications, f"Mini-game over! +${int(reward)}", (100, 255, 100)
                )
                current_minigame = None
                minigame_targets = []

        # === UPDATE MINIGAME RESULT DISPLAY ===
        if minigame_result_timer > 0:
            minigame_result_timer -= dt
            if minigame_result_timer <= 0:
                minigame_result = None

        # === UPDATE LUCKY WHEEL ===
        if wheel_spinning:
            wheel_speed *= 0.98  # Slow down
            wheel_angle += wheel_speed * dt
            if wheel_speed < 5:
                wheel_spinning = False
                # Determine prize
                prize_index = int((wheel_angle % 360) / (360 / len(wheel_prizes)))
                wheel_result = wheel_prizes[prize_index]
                wheel_result_timer = 3.0

                # Apply prize
                if wheel_result["type"] == "money":
                    money += wheel_result["value"]
                elif wheel_result["type"] == "money_mult":
                    bonus = money * (wheel_result["value"] - 1)
                    money += bonus
                    if wheel_result["value"] == 10 and not achievements.get(
                        "wheel_jackpot", {}
                    ).get("unlocked", False):
                        reward_ach = check_achievement(
                            achievements,
                            achievement_defs,
                            "wheel_jackpot",
                            achievement_queue,
                            notifications,
                            money,
                        )
                        money += reward_ach
                elif wheel_result["type"] == "skill_point":
                    skill_points += wheel_result["value"]
                elif wheel_result["type"] == "powerup":
                    active_powerups.append(
                        {
                            "name": "2x AFK",
                            "type": "afk_boost",
                            "multiplier": 2.0,
                            "duration": wheel_result["value"],
                        }
                    )

                stats_data["wheels_spun"] = stats_data.get("wheels_spun", 0) + 1
                add_notification(
                    notifications,
                    f"You won: {wheel_result['name']}!",
                    wheel_result["color"],
                )

        if wheel_result_timer > 0:
            wheel_result_timer -= dt
            if wheel_result_timer <= 0:
                wheel_result = None

        # === UPDATE OFFLINE PROGRESS DISPLAY ===
        if offline_progress_timer > 0:
            offline_progress_timer -= dt

        # === UPDATE STATISTICS ===
        stats_data["total_playtime"] = stats_data.get("total_playtime", 0) + dt

        # Check playtime achievements
        if stats_data["total_playtime"] >= 3600 and not achievements.get(
            "playtime_1h", {}
        ).get("unlocked", False):
            reward = check_achievement(
                achievements,
                achievement_defs,
                "playtime_1h",
                achievement_queue,
                notifications,
                money,
            )
            money += reward
        if stats_data["total_playtime"] >= 36000 and not achievements.get(
            "playtime_10h", {}
        ).get("unlocked", False):
            reward = check_achievement(
                achievements,
                achievement_defs,
                "playtime_10h",
                achievement_queue,
                notifications,
                money,
            )
            money += reward

        # Update particle physics before rendering so visuals reflect current state
        update_particles(particles, dt)

        # En yüksek para miktarını güncelley
        if money > highest_money:
            highest_money = money

        # NEW: Check money achievements
        if money >= 1000 and not achievements.get("money_1k", {}).get(
            "unlocked", False
        ):
            reward = check_achievement(
                achievements,
                achievement_defs,
                "money_1k",
                achievement_queue,
                notifications,
                money,
            )
            money += reward
        if money >= 10000 and not achievements.get("money_10k", {}).get(
            "unlocked", False
        ):
            reward = check_achievement(
                achievements,
                achievement_defs,
                "money_10k",
                achievement_queue,
                notifications,
                money,
            )
            money += reward
        if money >= 100000 and not achievements.get("money_100k", {}).get(
            "unlocked", False
        ):
            reward = check_achievement(
                achievements,
                achievement_defs,
                "money_100k",
                achievement_queue,
                notifications,
                money,
            )
            money += reward
        if money >= 1000000 and not achievements.get("money_1m", {}).get(
            "unlocked", False
        ):
            reward = check_achievement(
                achievements,
                achievement_defs,
                "money_1m",
                achievement_queue,
                notifications,
                money,
            )
            money += reward

        # draw cached gradient background for nicer visuals
        # Use a slightly larger size to prevent black edges during screen shake
        bg_width = SCREEN_SIZE[0] + 60
        bg_height = SCREEN_SIZE[1] + 60
        bg = _get_bg_gradient((bg_width, bg_height))

        # Center the background relative to the screen, then apply shake offset
        bg_x = -30 + int(screen_offset[0])
        bg_y = -30 + int(screen_offset[1])
        screen.blit(bg, (bg_x, bg_y))

        # İstatistik paneli çizimi - Enhanced
        draw_panel(
            screen,
            stats_panel_rect,
            border_color=(80, 100, 90),
            bg_color=(30, 45, 35, 200),
            draw_shadow=False,
        )

        screen.blit(sound_image, (SCREEN_SIZE[0] - 130, 560))

        # Weather Panel
        draw_panel(
            screen,
            weather_panel_rect,
            border_color=(80, 100, 90),
            bg_color=(35, 50, 40, 200),
            draw_shadow=False,
        )

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

        # === NEW BUTTONS FOR ENHANCED SYSTEMS ===

        # Skill Tree button
        skills_text = f"Skills ({skill_points} SP)"
        skills_text_surf = small_font.render(skills_text, True, TEXT_COLOR)
        skills_text_rect = skills_text_surf.get_rect()
        button_width = skills_text_rect.width + 2 * padding
        button_height = skills_text_rect.height + 2 * padding
        skills_button_rect = pygame.Rect(0, 0, button_width, button_height)
        skills_button_rect.topright = (
            SCREEN_SIZE[0] - 20,
            shop_button_rect.bottom + 8,
        )

        draw_button(
            screen,
            skills_button_rect,
            (120, 80, 200),  # Mystic Purple
            BUTTON_BORDER_COLOR,
            skills_text,
            small_font,
            dt,
            effect_name="skills",
        )

        # Prestige button (if can prestige - money >= 100k)
        if money >= 100000:
            prestige_text = "PRESTIGE"
            prestige_text_surf = extra_small_font.render(
                prestige_text, True, TEXT_COLOR
            )
            prestige_text_rect = prestige_text_surf.get_rect()
            prestige_button_rect = pygame.Rect(0, 0, 80, 25)
            prestige_button_rect.bottomleft = (10, SCREEN_SIZE[1] - 45)

            draw_button(
                screen,
                prestige_button_rect,
                (210, 180, 60),  # Gold
                BUTTON_BORDER_COLOR,
                prestige_text,
                extra_small_font,
                dt,
                effect_name="prestige",
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

        # NEW: Draw damage numbers
        draw_damage_numbers(screen, damage_numbers, small_font)

        # NEW: Draw combo meter (above grass)
        if combo_count > 0:
            draw_combo_meter(
                screen,
                combo_count,
                combo_timer,
                COMBO_TIMEOUT,
                medium_font,
                (SCREEN_SIZE[0] // 2, 100),
            )

        # NEW: Draw notifications (DISABLED - too small and cluttering)
        # draw_notifications(screen, notifications, extra_small_font)

        # NEW: Draw achievement popup
        if achievement_queue and achievement_display_timer > 0:
            draw_achievement_popup(
                screen,
                achievement_queue[0],
                achievement_display_timer,
                medium_font,
                small_font,
            )

        # NEW: Draw daily reward popup (smaller, at top)
        if daily_reward_timer > 0:
            alpha = int(255 * min(1.0, daily_reward_timer / 0.5))
            reward_surf = pygame.Surface((300, 100), pygame.SRCALPHA)
            pygame.draw.rect(
                reward_surf,
                (40, 100, 40, alpha),
                reward_surf.get_rect(),
                border_radius=8,
            )
            pygame.draw.rect(
                reward_surf,
                (100, 255, 100, alpha),
                reward_surf.get_rect(),
                2,
                border_radius=8,
            )

            title = small_font.render("Daily Reward!", True, (255, 255, 100))
            title.set_alpha(alpha)
            streak_text = small_font.render(
                f"Streak: {login_streak} days", True, (255, 255, 255)
            )
            streak_text.set_alpha(alpha)
            reward_text = small_font.render(
                f"+${int(daily_reward_amount)}", True, (100, 255, 100)
            )
            reward_text.set_alpha(alpha)

            reward_surf.blit(title, (150 - title.get_width() // 2, 15))
            reward_surf.blit(streak_text, (150 - streak_text.get_width() // 2, 45))
            reward_surf.blit(reward_text, (150 - reward_text.get_width() // 2, 70))

            # Position at top-center instead of center
            screen.blit(reward_surf, (SCREEN_SIZE[0] // 2 - 150, 50))

        # NEW: Draw save indicator
        if save_indicator_timer > 0:
            alpha = int(255 * save_indicator_timer)
            save_text = extra_small_font.render("Auto-saved", True, (100, 255, 100))
            save_text.set_alpha(alpha)
            screen.blit(save_text, (10, SCREEN_SIZE[1] - 30))

        # NEW: Draw FPS counter (if enabled)
        if settings.get("show_fps", False):
            fps = int(clock.get_fps())
            fps_text = extra_small_font.render(f"FPS: {fps}", True, (255, 255, 255))
            screen.blit(fps_text, (SCREEN_SIZE[0] - 70, SCREEN_SIZE[1] - 25))

        # NEW: Draw active power-ups indicator
        if active_powerups:
            y_offset = 200
            for powerup in active_powerups:
                time_left = int(powerup["duration"])
                powerup_text = extra_small_font.render(
                    f"{powerup['name']}: {time_left}s", True, (255, 200, 100)
                )
                screen.blit(powerup_text, (10, y_offset))
                y_offset += 20

        # NEW: Draw prestige indicator (if prestiged)
        if prestige_level > 0:
            prestige_text = extra_small_font.render(
                f"Prestige: Lv{prestige_level} ({prestige_multiplier:.1f}x)",
                True,
                (255, 215, 0),
            )
            screen.blit(
                prestige_text, (stats_panel_rect.x + 15, stats_panel_rect.bottom + 10)
            )

        # === BOSS HP BAR ===
        if boss_active and current_boss_type:
            boss_bar_width = 400
            boss_bar_height = 30
            boss_bar_x = SCREEN_SIZE[0] // 2 - boss_bar_width // 2
            boss_bar_y = 20

            # Boss bar background
            pygame.draw.rect(
                screen,
                (50, 30, 30),
                (
                    boss_bar_x - 2,
                    boss_bar_y - 2,
                    boss_bar_width + 4,
                    boss_bar_height + 4,
                ),
                border_radius=5,
            )
            pygame.draw.rect(
                screen,
                (80, 40, 40),
                (boss_bar_x, boss_bar_y, boss_bar_width, boss_bar_height),
                border_radius=4,
            )

            # HP fill
            hp_ratio = max(0, boss_hp / boss_max_hp)
            hp_width = int(boss_bar_width * hp_ratio)
            hp_color = current_boss_type["color"]
            if boss_hit_flash > 0:
                hp_color = (255, 255, 255)  # Flash white when hit
            if hp_width > 0:
                pygame.draw.rect(
                    screen,
                    hp_color,
                    (boss_bar_x, boss_bar_y, hp_width, boss_bar_height),
                    border_radius=4,
                )

            # Boss name and timer
            boss_name_text = small_font.render(
                f"{current_boss_type['name']} Lv{boss_level}", True, (255, 255, 255)
            )
            screen.blit(boss_name_text, (boss_bar_x, boss_bar_y - 22))

            boss_timer_text = small_font.render(
                f"{int(boss_timer)}s",
                True,
                (255, 100, 100) if boss_timer < 15 else (255, 255, 255),
            )
            screen.blit(
                boss_timer_text, (boss_bar_x + boss_bar_width - 30, boss_bar_y - 22)
            )

            # HP text
            hp_text = extra_small_font.render(
                f"{max(0, boss_hp)}/{boss_max_hp}", True, (255, 255, 255)
            )
            screen.blit(
                hp_text,
                (
                    boss_bar_x + boss_bar_width // 2 - hp_text.get_width() // 2,
                    boss_bar_y + 6,
                ),
            )

        # === SEASONAL EVENT BANNER ===
        if seasonal_event:
            event_surf = pygame.Surface((180, 30), pygame.SRCALPHA)
            pygame.draw.rect(
                event_surf,
                (*seasonal_colors[0], 180),
                event_surf.get_rect(),
                border_radius=5,
            )
            pygame.draw.rect(
                event_surf,
                seasonal_colors[1],
                event_surf.get_rect(),
                2,
                border_radius=5,
            )

            event_text = extra_small_font.render(
                f"🎄 {seasonal_event} ({seasonal_multiplier}x)", True, (255, 255, 255)
            )
            event_surf.blit(event_text, (10, 6))
            screen.blit(event_surf, (SCREEN_SIZE[0] // 2 - 90, SCREEN_SIZE[1] - 35))

        # === OFFLINE PROGRESS POPUP ===
        if offline_progress_timer > 0 and offline_earnings > 0:
            alpha = int(255 * min(1.0, offline_progress_timer / 0.5))
            offline_surf = pygame.Surface((320, 120), pygame.SRCALPHA)
            pygame.draw.rect(
                offline_surf,
                (40, 60, 100, alpha),
                offline_surf.get_rect(),
                border_radius=10,
            )
            pygame.draw.rect(
                offline_surf,
                (100, 150, 255, alpha),
                offline_surf.get_rect(),
                3,
                border_radius=10,
            )

            offline_title = medium_font.render("Welcome Back!", True, (255, 255, 100))
            offline_title.set_alpha(alpha)
            offline_msg = small_font.render(
                "While you were away...", True, (200, 200, 255)
            )
            offline_msg.set_alpha(alpha)
            offline_amount = medium_font.render(
                f"+${int(offline_earnings)}", True, (100, 255, 100)
            )
            offline_amount.set_alpha(alpha)

            offline_surf.blit(offline_title, (160 - offline_title.get_width() // 2, 15))
            offline_surf.blit(offline_msg, (160 - offline_msg.get_width() // 2, 50))
            offline_surf.blit(
                offline_amount, (160 - offline_amount.get_width() // 2, 80)
            )

            screen.blit(
                offline_surf, (SCREEN_SIZE[0] // 2 - 160, SCREEN_SIZE[1] // 2 - 60)
            )

        # === MINIGAME OVERLAY ===
        if minigame_active and current_minigame:
            # Darken main game
            dark_overlay = pygame.Surface(SCREEN_SIZE, pygame.SRCALPHA)
            pygame.draw.rect(dark_overlay, (0, 0, 0, 100), dark_overlay.get_rect())
            screen.blit(dark_overlay, (0, 0))

            # Minigame header
            game_name = {
                "click_frenzy": "CLICK FRENZY!",
                "target_practice": "TARGET PRACTICE!",
                "golden_rush": "GOLDEN RUSH!",
            }
            header_text = medium_font.render(
                game_name.get(current_minigame, "MINI-GAME"), True, (255, 215, 0)
            )
            screen.blit(
                header_text, (SCREEN_SIZE[0] // 2 - header_text.get_width() // 2, 60)
            )

            # Timer and score
            timer_text = medium_font.render(
                f"Time: {int(minigame_timer)}s",
                True,
                (255, 100, 100) if minigame_timer < 5 else (255, 255, 255),
            )
            screen.blit(timer_text, (50, 100))

            score_text = medium_font.render(
                f"Score: {minigame_score}", True, (100, 255, 100)
            )
            screen.blit(score_text, (SCREEN_SIZE[0] - 150, 100))

            # Draw targets for target practice
            if current_minigame == "target_practice":
                for target in minigame_targets:
                    alpha = int(255 * min(1.0, target["life"] / 0.5))
                    pygame.draw.circle(
                        screen,
                        target["color"],
                        (int(target["x"]), int(target["y"])),
                        target["radius"],
                    )
                    pygame.draw.circle(
                        screen,
                        (255, 255, 255),
                        (int(target["x"]), int(target["y"])),
                        target["radius"],
                        2,
                    )

            # Draw coins for golden rush
            elif current_minigame == "golden_rush":
                for coin in minigame_targets:
                    pygame.draw.circle(
                        screen,
                        (255, 215, 0),
                        (int(coin["x"]), int(coin["y"])),
                        coin["radius"],
                    )
                    pygame.draw.circle(
                        screen,
                        (200, 170, 0),
                        (int(coin["x"]), int(coin["y"])),
                        coin["radius"],
                        2,
                    )
                    value_text = extra_small_font.render(
                        f"+{coin['value']}", True, (255, 255, 255)
                    )
                    screen.blit(value_text, (coin["x"] - 10, coin["y"] - 8))

            # Instructions
            if current_minigame == "click_frenzy":
                instr = extra_small_font.render(
                    "Click the grass as fast as you can!", True, (200, 200, 200)
                )
            elif current_minigame == "target_practice":
                instr = extra_small_font.render(
                    "Click the targets before they disappear!", True, (200, 200, 200)
                )
            else:
                instr = extra_small_font.render(
                    "Click the falling coins!", True, (200, 200, 200)
                )
            screen.blit(
                instr,
                (SCREEN_SIZE[0] // 2 - instr.get_width() // 2, SCREEN_SIZE[1] - 80),
            )

        # === MINIGAME RESULT DISPLAY ===
        if minigame_result and minigame_result_timer > 0:
            result_surf = pygame.Surface((300, 150), pygame.SRCALPHA)
            alpha = int(255 * min(1.0, minigame_result_timer / 0.5))
            pygame.draw.rect(
                result_surf,
                (30, 80, 30, alpha),
                result_surf.get_rect(),
                border_radius=10,
            )
            pygame.draw.rect(
                result_surf,
                (100, 255, 100, alpha),
                result_surf.get_rect(),
                3,
                border_radius=10,
            )

            result_title = medium_font.render("GAME OVER!", True, (255, 215, 0))
            result_title.set_alpha(alpha)
            score_result = medium_font.render(
                f"Score: {minigame_result['score']}", True, (255, 255, 255)
            )
            score_result.set_alpha(alpha)

            result_surf.blit(result_title, (150 - result_title.get_width() // 2, 30))
            result_surf.blit(score_result, (150 - score_result.get_width() // 2, 80))

            screen.blit(
                result_surf, (SCREEN_SIZE[0] // 2 - 150, SCREEN_SIZE[1] // 2 - 75)
            )

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
                # Çıkış yapmadan önce oyunu kaydet - TÜM VERİLERİ KAYDET
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
                        "max_combo": max_combo,
                        "achievements": achievements,
                        "prestige_level": prestige_level,
                        "grass_seeds": grass_seeds,
                        "special_collected_count": special_collected_count,
                        "last_login_date": today,
                        "login_streak": login_streak,
                        "settings": settings,
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
                        special_collected_count += 1

                        # NEW: Check special collection achievements
                        if special_collected_count == 1 and not achievements.get(
                            "special_collect", {}
                        ).get("unlocked", False):
                            reward = check_achievement(
                                achievements,
                                achievement_defs,
                                "special_collect",
                                achievement_queue,
                                notifications,
                                money,
                            )
                            money += reward
                        if special_collected_count >= 10 and not achievements.get(
                            "special_10", {}
                        ).get("unlocked", False):
                            reward = check_achievement(
                                achievements,
                                achievement_defs,
                                "special_10",
                                achievement_queue,
                                notifications,
                                money,
                            )
                            money += reward

                        # spawn particles and sound feedback
                        spawn_particles(particles, (sx, sy), (255, 215, 80), count=20)
                        spawn_damage_number(
                            damage_numbers, (sx, sy), val, (255, 215, 0)
                        )
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

                        # NEW: Check first AFK upgrade achievement
                        if auto_income == 0 and not achievements.get(
                            "upgrade_afk", {}
                        ).get("unlocked", False):
                            reward = check_achievement(
                                achievements,
                                achievement_defs,
                                "upgrade_afk",
                                achievement_queue,
                                notifications,
                                money,
                            )
                            money += reward

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

                        # NEW: Check first multiplier upgrade achievement
                        if multiplier == 1 and not achievements.get(
                            "upgrade_mult", {}
                        ).get("unlocked", False):
                            reward = check_achievement(
                                achievements,
                                achievement_defs,
                                "upgrade_mult",
                                achievement_queue,
                                notifications,
                                money,
                            )
                            money += reward

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
            if event.type == pygame.MOUSEBUTTONDOWN:
                # === OVERLAY HANDLING ===
                # Check active overlays first to prevent clicking through them
                if show_stats:
                    # Check Close button on Stats
                    # Recompute rects as in drawing code
                    stats_surface_rect = pygame.Rect(0, 0, 500, 400)
                    stats_surface_rect.center = (
                        SCREEN_SIZE[0] // 2,
                        SCREEN_SIZE[1] // 2,
                    )

                    close_rect = pygame.Rect(
                        stats_surface_rect.width // 2 - 50,
                        stats_surface_rect.height - 50,
                        100,
                        40,
                    )
                    # Adjust to screen coordinates
                    close_rect.x += stats_surface_rect.x
                    close_rect.y += stats_surface_rect.y

                    if close_rect.collidepoint(event.pos):
                        show_stats = False
                        _safe_set_volume(click_effect, 0.0896705)
                        _safe_play(click_effect)

                elif show_shop:
                    # Recompute Shop Rects
                    shop_surface_rect = pygame.Rect(0, 0, 500, 605)
                    shop_surface_rect.center = (
                        SCREEN_SIZE[0] // 2,
                        SCREEN_SIZE[1] // 2,
                    )

                    close_rect = pygame.Rect(
                        shop_surface_rect.width // 2 - 50,
                        shop_surface_rect.height - 50,
                        100,
                        40,
                    )
                    close_rect.x += shop_surface_rect.x
                    close_rect.y += shop_surface_rect.y

                    if close_rect.collidepoint(event.pos):
                        show_shop = False
                        _safe_set_volume(click_effect, 0.0896705)
                        _safe_play(click_effect)
                    else:
                        # Check Shop Items
                        y_pos = 80 + shop_surface_rect.y
                        item_height = 70
                        for i, (name, cost) in enumerate(zip(grass_names, grass_costs)):
                            # Calculate button rect in screen coordinates
                            # Item rect relative to shop surface is (50, y_pos_local, 400, item_height)
                            # Button is right aligned in item rect
                            item_x = shop_surface_rect.x + 50

                            # Button logic from drawing:
                            # button_rect = pygame.Rect(item_rect.right - 100, item_rect.centery - 20, 80, 40)
                            # item_rect.right = item_x + 400
                            # item_rect.centery = y_pos + item_height // 2

                            btn_x = (item_x + 400) - 100
                            btn_y = (y_pos + item_height // 2) - 20
                            button_rect = pygame.Rect(btn_x, btn_y, 80, 40)

                            if button_rect.collidepoint(event.pos):
                                if (
                                    current_grass_index != i
                                    and current_grass_index >= i
                                ):
                                    current_grass_index = i
                                    active_grass_img = grass_images[current_grass_index]
                                    _safe_set_volume(click_effect, 0.0896705)
                                    _safe_play(click_effect)
                                elif (
                                    i > 0 and current_grass_index < i and money >= cost
                                ):
                                    old_index = current_grass_index
                                    money -= cost
                                    current_grass_index = i
                                    active_grass_img = grass_images[current_grass_index]
                                    _safe_set_volume(buy_effect, 0.0896705)
                                    _safe_play(buy_effect)

                                    # Achievements
                                    if old_index == 0 and not achievements.get(
                                        "buy_grass", {}
                                    ).get("unlocked", False):
                                        reward = check_achievement(
                                            achievements,
                                            achievement_defs,
                                            "buy_grass",
                                            achievement_queue,
                                            notifications,
                                            money,
                                        )
                                        money += reward
                                    if current_grass_index >= len(
                                        grass_images
                                    ) - 1 and not achievements.get("all_grass", {}).get(
                                        "unlocked", False
                                    ):
                                        reward = check_achievement(
                                            achievements,
                                            achievement_defs,
                                            "all_grass",
                                            achievement_queue,
                                            notifications,
                                            money,
                                        )
                                        money += reward

                            y_pos += item_height + 10

                # REMOVED: Minigame Menu Logic
                # elif show_minigame_menu: ...

                elif show_skill_tree:
                    # Skill Tree Clicks
                    st_rect = pygame.Rect(0, 0, 500, 450)
                    st_rect.center = (SCREEN_SIZE[0] // 2, SCREEN_SIZE[1] // 2)

                    y_start = 80 + st_rect.y
                    x_start = 50 + st_rect.x

                    for i, (sid, sdata) in enumerate(skills.items()):
                        row = i // 2
                        col = i % 2
                        x = x_start + col * 220
                        y = y_start + row * 90
                        skill_rect = pygame.Rect(x, y, 200, 80)

                        if skill_rect.collidepoint(event.pos):
                            # Buy Skill Logic
                            if (
                                skill_points >= sdata["cost"]
                                and not sdata.get("unlocked", False)
                                and (
                                    not sdata.get("parent")
                                    or skills[sdata["parent"]].get("unlocked", False)
                                )
                            ):

                                skill_points -= sdata["cost"]
                                sdata["unlocked"] = True
                                _safe_play(buy_effect)
                                add_notification(
                                    notifications,
                                    f"Learned {sdata['name']}!",
                                    (50, 255, 50),
                                )

                                # Apply skill effect immediately
                                if sdata["type"] == "multiplier":
                                    multiplier += sdata["effect"]
                                # (Other types handled elsewhere)

                                # Skill Achievements
                                if not achievements.get("skill_first", {}).get(
                                    "unlocked", False
                                ):
                                    money += check_achievement(
                                        achievements,
                                        achievement_defs,
                                        "skill_first",
                                        achievement_queue,
                                        notifications,
                                        money,
                                    )

                    if not st_rect.collidepoint(event.pos):
                        show_skill_tree = False

                # REMOVED: Lucky Wheel Logic
                # elif show_lucky_wheel: ...

                # === MAIN MENU BUTTONS ===
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
                    # Oyun verilerini kaydet - TÜM VERİLERİ KAYDET
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
                            "max_combo": max_combo,
                            "achievements": achievements,
                            "prestige_level": prestige_level,
                            "grass_seeds": grass_seeds,
                            "special_collected_count": special_collected_count,
                            "last_login_date": today,
                            "login_streak": login_streak,
                            "settings": settings,
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

                # === NEW BUTTON HANDLERS ===

                # REMOVED: Minigame Button Handler
                # elif minigame_button_rect.collidepoint(event.pos): ...

                elif skills_button_rect.collidepoint(event.pos):
                    if current_sound_state == "on":
                        _safe_set_volume(click_effect, 0.0896705)
                        _safe_play(click_effect)
                    button_states.setdefault("skills", {"hover": 0.0, "press": 0.0})[
                        "press"
                    ] = 1.0
                    spawn_particles(
                        particles, skills_button_rect.center, (100, 50, 200), count=15
                    )
                    show_skill_tree = not show_skill_tree
                    show_minigame_menu = False
                    show_lucky_wheel = False

                # REMOVED: Wheel Button Handler
                # elif wheel_button_rect.collidepoint(event.pos): ...

                elif money >= 100000 and prestige_button_rect.collidepoint(event.pos):
                    # (Rest of prestige logic)
                    if current_sound_state == "on":
                        _safe_set_volume(click_effect, 0.0896705)
                        _safe_play(click_effect)
                    button_states.setdefault("prestige", {"hover": 0.0, "press": 0.0})[
                        "press"
                    ] = 1.0
                    spawn_particles(
                        particles, prestige_button_rect.center, (200, 150, 50), count=20
                    )

                    # Prestige!
                    prestige_level += 1
                    prestige_multiplier = 1.0 + (prestige_level * 0.1)
                    grass_seeds_earned = int(math.sqrt(money) / 10)
                    grass_seeds += grass_seeds_earned

                    # Reset progress
                    money = 0
                    multiplier = 1
                    auto_income = 0.0
                    total_clicks = 0
                    afk_upgrade_cost = 150
                    multiplier_upgrade_cost = 150
                    current_grass_index = 0
                    active_grass_img = grass_images[0]
                    combo_count = 0

                    if settings.get("screen_shake", True):
                        screen_shake_intensity, screen_shake_duration = (
                            trigger_screen_shake(25, 0.8)
                        )

                    spawn_particles(
                        particles,
                        (SCREEN_SIZE[0] // 2, SCREEN_SIZE[1] // 2),
                        (255, 215, 0),
                        count=100,
                    )
                    add_notification(
                        notifications,
                        f"PRESTIGE Lv{prestige_level}! +{grass_seeds_earned} Seeds!",
                        (255, 215, 0),
                    )

                    # Check prestige achievements
                    if prestige_level == 1 and not achievements.get(
                        "prestige_1", {}
                    ).get("unlocked", False):
                        check_achievement(
                            achievements,
                            achievement_defs,
                            "prestige_1",
                            achievement_queue,
                            notifications,
                            money,
                        )
                    if prestige_level >= 5 and not achievements.get(
                        "prestige_5", {}
                    ).get("unlocked", False):
                        reward = check_achievement(
                            achievements,
                            achievement_defs,
                            "prestige_5",
                            achievement_queue,
                            notifications,
                            money,
                        )
                        money += reward
                    if prestige_level >= 10 and not achievements.get(
                        "prestige_10", {}
                    ).get("unlocked", False):
                        reward = check_achievement(
                            achievements,
                            achievement_defs,
                            "prestige_10",
                            achievement_queue,
                            notifications,
                            money,
                        )
                        money += reward

                # === MINIGAME TARGET/COIN CLICKS ===
                elif minigame_active:
                    if current_minigame == "target_practice":
                        for target in minigame_targets[:]:
                            dist = math.sqrt(
                                (event.pos[0] - target["x"]) ** 2
                                + (event.pos[1] - target["y"]) ** 2
                            )
                            if dist <= target["radius"]:
                                minigame_targets.remove(target)
                                minigame_score += 1
                                spawn_particles(
                                    particles,
                                    (target["x"], target["y"]),
                                    target["color"],
                                    count=10,
                                )
                                if current_sound_state == "on":
                                    _safe_play(click_effect)
                                break

                    elif current_minigame == "golden_rush":
                        for coin in minigame_targets[:]:
                            dist = math.sqrt(
                                (event.pos[0] - coin["x"]) ** 2
                                + (event.pos[1] - coin["y"]) ** 2
                            )
                            if dist <= coin["radius"]:
                                minigame_targets.remove(coin)
                                minigame_score += coin["value"]
                                spawn_particles(
                                    particles,
                                    (coin["x"], coin["y"]),
                                    (255, 215, 0),
                                    count=8,
                                )
                                if current_sound_state == "on":
                                    _safe_play(click_effect)
                                break

                elif grass_rect.collidepoint(event.pos):
                    if current_sound_state == "on":
                        _safe_set_volume(click_effect, 0.0896705)
                        _safe_play(click_effect)

                    # Handle minigame clicks
                    if minigame_active and current_minigame == "click_frenzy":
                        minigame_click_count += 1
                        minigame_score = minigame_click_count
                        spawn_particles(
                            particles, grass_rect.center, (255, 200, 50), count=5
                        )
                        continue

                    # NEW: Combo system with skill bonus
                    combo_skill_bonus = calculate_skill_bonus("combo_1", skills)
                    combo_count += 1
                    combo_timer = (
                        COMBO_TIMEOUT + combo_skill_bonus
                    )  # Skill extends timeout
                    if combo_count > max_combo:
                        max_combo = combo_count
                        if max_combo > stats_data.get("highest_combo_ever", 0):
                            stats_data["highest_combo_ever"] = max_combo

                    combo_mult = get_combo_multiplier(combo_count)
                    combo_mult_bonus = 1.0 + calculate_skill_bonus("combo_2", skills)
                    combo_mult *= combo_mult_bonus

                    # NEW: Power-up multiplier
                    click_mult = 1.0
                    extra_crit_chance = 0.0
                    for powerup in active_powerups:
                        if powerup["type"] == "click_boost":
                            click_mult = powerup["multiplier"]
                        if powerup["type"] == "crit_boost":
                            extra_crit_chance = powerup["multiplier"]

                    # NEW: Skill tree click power bonus
                    click_skill_bonus = (
                        1.0
                        + calculate_skill_bonus("click_power_1", skills)
                        + calculate_skill_bonus("click_power_2", skills)
                        + calculate_skill_bonus("click_power_3", skills)
                    )

                    # NEW: Critical hit calculation with skill bonus
                    luck_skill_bonus = calculate_skill_bonus("luck_1", skills)
                    total_crit_chance = (
                        critical_hit_chance + luck_skill_bonus + extra_crit_chance
                    )

                    is_critical = random.random() < total_crit_chance
                    crit_mult_bonus = calculate_skill_bonus("luck_2", skills)
                    current_crit_mult = (
                        critical_hit_multiplier + crit_mult_bonus
                        if is_critical
                        else 1.0
                    )

                    # Calculate base money gain
                    if current_grass_index == 0:
                        # User Request: Biome 1 multiplier 1.1x
                        base_gain = 1.1 * multiplier * weather_multiplier
                    else:
                        base_gain = (
                            1
                            * multiplier
                            * current_grass_index
                            * 1.5
                            * weather_multiplier
                        )

                    # Apply all multipliers including critical, skill bonuses, and seasonal
                    total_gain = (
                        base_gain
                        * combo_mult
                        * click_mult
                        * prestige_multiplier
                        * click_skill_bonus
                        * current_crit_mult
                        * seasonal_multiplier
                    )

                    # Handle boss damage
                    if boss_active:
                        boss_hp -= int(total_gain * 10)  # Damage = 10x money gain
                        boss_hit_flash = 1.0
                        if settings.get("screen_shake", True):
                            # User Request: Screen shake intensity +45%
                            screen_shake_intensity, screen_shake_duration = (
                                trigger_screen_shake(4.35, 0.1)
                            )

                        if boss_hp <= 0:
                            # Boss defeated!
                            boss_active = False
                            boss_defeated_count += 1
                            stats_data["bosses_defeated"] = (
                                stats_data.get("bosses_defeated", 0) + 1
                            )

                            # Calculate boss reward
                            boss_reward = int(
                                5000
                                * boss_level
                                * current_boss_type["reward_mult"]
                                * prestige_multiplier
                            )
                            money += boss_reward
                            skill_points += boss_level  # Earn skill points from bosses!

                            spawn_particles(
                                particles,
                                grass_rect.center,
                                current_boss_type["color"],
                                count=50,
                            )
                            spawn_damage_number(
                                damage_numbers,
                                (SCREEN_SIZE[0] // 2, 200),
                                boss_reward,
                                (255, 100, 100),
                            )

                            add_notification(
                                notifications,
                                f"BOSS DEFEATED! +${boss_reward} +{boss_level} SP!",
                                (255, 215, 0),
                            )
                            if settings.get("screen_shake", True):
                                # User Request: Screen shake intensity +45%
                                screen_shake_intensity, screen_shake_duration = (
                                    trigger_screen_shake(29, 0.5)
                                )

                            boss_level += 1
                            boss_spawn_timer = BOSS_SPAWN_INTERVAL

                            # Check boss achievements
                            if boss_defeated_count == 1 and not achievements.get(
                                "boss_first", {}
                            ).get("unlocked", False):
                                reward = check_achievement(
                                    achievements,
                                    achievement_defs,
                                    "boss_first",
                                    achievement_queue,
                                    notifications,
                                    money,
                                )
                                money += reward
                            if boss_defeated_count >= 10 and not achievements.get(
                                "boss_10", {}
                            ).get("unlocked", False):
                                reward = check_achievement(
                                    achievements,
                                    achievement_defs,
                                    "boss_10",
                                    achievement_queue,
                                    notifications,
                                    money,
                                )
                                money += reward
                            if boss_defeated_count >= 50 and not achievements.get(
                                "boss_50", {}
                            ).get("unlocked", False):
                                reward = check_achievement(
                                    achievements,
                                    achievement_defs,
                                    "boss_50",
                                    achievement_queue,
                                    notifications,
                                    money,
                                )
                                money += reward

                    money += total_gain
                    total_clicks += 1
                    stats_data["total_clicks_all_time"] = (
                        stats_data.get("total_clicks_all_time", 0) + 1
                    )

                    # Track highest single click
                    if total_gain > stats_data.get("highest_single_click", 0):
                        stats_data["highest_single_click"] = total_gain

                    # NEW: Critical hit effects and achievements
                    if is_critical:
                        critical_hit_count += 1
                        stats_data["critical_hits"] = (
                            stats_data.get("critical_hits", 0) + 1
                        )

                        # Bigger particles for critical
                        if rainbow_mode:
                            crit_color = (
                                random.randint(100, 255),
                                random.randint(100, 255),
                                random.randint(100, 255),
                            )
                        else:
                            crit_color = (255, 50, 50)
                        spawn_particles(
                            particles, grass_rect.center, crit_color, count=30
                        )
                        spawn_damage_number(
                            damage_numbers, grass_rect.center, total_gain, (255, 50, 50)
                        )

                        if settings.get("screen_shake", True):
                            screen_shake_intensity, screen_shake_duration = (
                                trigger_screen_shake(8, 0.2)
                            )

                        # Check critical achievements
                        if critical_hit_count == 1 and not achievements.get(
                            "crit_first", {}
                        ).get("unlocked", False):
                            reward = check_achievement(
                                achievements,
                                achievement_defs,
                                "crit_first",
                                achievement_queue,
                                notifications,
                                money,
                            )
                            money += reward
                        if critical_hit_count >= 100 and not achievements.get(
                            "crit_100", {}
                        ).get("unlocked", False):
                            reward = check_achievement(
                                achievements,
                                achievement_defs,
                                "crit_100",
                                achievement_queue,
                                notifications,
                                money,
                            )
                            money += reward
                        if critical_hit_count >= 1000 and not achievements.get(
                            "crit_1000", {}
                        ).get("unlocked", False):
                            reward = check_achievement(
                                achievements,
                                achievement_defs,
                                "crit_1000",
                                achievement_queue,
                                notifications,
                                money,
                            )
                            money += reward
                    else:
                        # Normal damage number
                        if rainbow_mode:
                            dmg_color = (
                                random.randint(150, 255),
                                random.randint(150, 255),
                                random.randint(50, 255),
                            )
                        else:
                            dmg_color = (255, 255, 100)
                        spawn_damage_number(
                            damage_numbers, grass_rect.center, total_gain, dmg_color
                        )

                    # NEW: Screen shake (intensity based on combo and critical)
                    if settings.get("screen_shake", True) and not is_critical:
                        shake_intensity = min(10, 2 + combo_count * 0.2)
                        screen_shake_intensity, screen_shake_duration = (
                            trigger_screen_shake(shake_intensity, 0.15)
                        )

                    # spawn particles at click position (center of grass)
                    particle_count = min(30, 18 + int(combo_count * 0.5))
                    if current_grass_index == 0:
                        spawn_particles(
                            particles,
                            grass_rect.center,
                            (255, 240, 160),
                            count=particle_count,
                        )
                    else:
                        spawn_particles(
                            particles,
                            grass_rect.center,
                            (220, 255, 200),
                            count=particle_count,
                        )

                    # NEW: Check achievements
                    if total_clicks == 1 and not achievements.get(
                        "first_click", {}
                    ).get("unlocked", False):
                        reward = check_achievement(
                            achievements,
                            achievement_defs,
                            "first_click",
                            achievement_queue,
                            notifications,
                            money,
                        )
                        money += reward
                    if total_clicks >= 100 and not achievements.get(
                        "click_100", {}
                    ).get("unlocked", False):
                        reward = check_achievement(
                            achievements,
                            achievement_defs,
                            "click_100",
                            achievement_queue,
                            notifications,
                            money,
                        )
                        money += reward
                    if total_clicks >= 1000 and not achievements.get(
                        "click_1000", {}
                    ).get("unlocked", False):
                        reward = check_achievement(
                            achievements,
                            achievement_defs,
                            "click_1000",
                            achievement_queue,
                            notifications,
                            money,
                        )
                        money += reward
                    if total_clicks >= 10000 and not achievements.get(
                        "click_10000", {}
                    ).get("unlocked", False):
                        reward = check_achievement(
                            achievements,
                            achievement_defs,
                            "click_10000",
                            achievement_queue,
                            notifications,
                            money,
                        )
                        money += reward
                    if combo_count >= 10 and not achievements.get("combo_10", {}).get(
                        "unlocked", False
                    ):
                        reward = check_achievement(
                            achievements,
                            achievement_defs,
                            "combo_10",
                            achievement_queue,
                            notifications,
                            money,
                        )
                        money += reward
                    if combo_count >= 25 and not achievements.get("combo_25", {}).get(
                        "unlocked", False
                    ):
                        reward = check_achievement(
                            achievements,
                            achievement_defs,
                            "combo_25",
                            achievement_queue,
                            notifications,
                            money,
                        )
                        money += reward
                    if combo_count >= 50 and not achievements.get("combo_50", {}).get(
                        "unlocked", False
                    ):
                        reward = check_achievement(
                            achievements,
                            achievement_defs,
                            "combo_50",
                            achievement_queue,
                            notifications,
                            money,
                        )
                        money += reward
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
                        # Oyunu sıfırla - GLOBAL RESET
                        money = 0
                        multiplier = 1
                        auto_income = 0.0
                        total_clicks = 0
                        afk_upgrade_cost = 150
                        multiplier_upgrade_cost = 150
                        highest_money = 0
                        current_grass_index = 0
                        active_grass_img = grass_images[0]
                        weather_index = 0
                        combo_count = 0
                        max_combo = 0
                        achievements = {}
                        achievement_queue = []
                        prestige_level = 0
                        grass_seeds = 0
                        special_collected_count = 0
                        login_streak = 0
                        critical_hit_count = 0
                        skill_points = 0
                        # Reset skills (simple way: lock all)
                        for s_key in skills:
                            skills[s_key]["unlocked"] = False
                        boss_level = 1
                        boss_defeated_count = 0
                        stats_data = {}
                        minigame_high_scores = {
                            "click_frenzy": 0,
                            "target_practice": 0,
                            "golden_rush": 0,
                        }
                        minigame_cooldowns = {
                            "click_frenzy": 0,
                            "target_practice": 0,
                            "golden_rush": 0,
                        }

                        add_notification(
                            notifications, "Save Wiped! Restarting...", (255, 0, 0)
                        )

        # Stats Panel Background
        draw_panel(screen, stats_panel_rect, bg_color=PANEL_BG_COLOR)

        # Weather Panel Background
        if weather_index != 0:  # Only draw weather panel if weather is active/changed
            draw_panel(screen, weather_panel_rect, bg_color=PANEL_BG_COLOR)
        else:
            draw_panel(screen, weather_panel_rect, bg_color=PANEL_BG_COLOR)

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

        if show_minigame_menu:
            # Minigame Menu Overlay
            mg_surf = pygame.Surface((400, 300))
            mg_surf.fill((30, 48, 34))
            mg_rect = mg_surf.get_rect(
                center=(SCREEN_SIZE[0] // 2, SCREEN_SIZE[1] // 2)
            )
            pygame.draw.rect(mg_surf, (40, 58, 44), mg_surf.get_rect(), border_radius=5)
            pygame.draw.rect(
                mg_surf, (255, 140, 0), mg_surf.get_rect(), 3, border_radius=5
            )

            # Title
            title = medium_font.render("Select Minigame", True, (255, 140, 0))
            mg_surf.blit(title, (200 - title.get_width() // 2, 20))

            # Buttons (We define rects relative to surface for drawing, but need screen rects for events)
            # 1. Click Frenzy
            frenzy_btn = pygame.Rect(50, 70, 300, 50)
            pygame.draw.rect(
                mg_surf,
                (
                    (50, 30, 30)
                    if minigame_cooldowns["click_frenzy"] > 0
                    else (200, 50, 50)
                ),
                frenzy_btn,
                border_radius=5,
            )
            pygame.draw.rect(
                mg_surf, BUTTON_BORDER_COLOR, frenzy_btn, 2, border_radius=5
            )
            frenzy_txt = small_font.render("Click Frenzy", True, TEXT_COLOR)
            mg_surf.blit(
                frenzy_txt,
                (200 - frenzy_txt.get_width() // 2, 95 - frenzy_txt.get_height() // 2),
            )
            if minigame_cooldowns["click_frenzy"] > 0:
                cd_txt = extra_small_font.render(
                    f"{int(minigame_cooldowns['click_frenzy'])}s", True, (150, 150, 150)
                )
                mg_surf.blit(cd_txt, (320, 85))

            # 2. Target Practice
            target_btn = pygame.Rect(50, 140, 300, 50)
            pygame.draw.rect(
                mg_surf,
                (
                    (30, 30, 50)
                    if minigame_cooldowns["target_practice"] > 0
                    else (50, 100, 200)
                ),
                target_btn,
                border_radius=5,
            )
            pygame.draw.rect(
                mg_surf, BUTTON_BORDER_COLOR, target_btn, 2, border_radius=5
            )
            target_txt = small_font.render("Target Practice", True, TEXT_COLOR)
            mg_surf.blit(
                target_txt,
                (200 - target_txt.get_width() // 2, 165 - target_txt.get_height() // 2),
            )
            if minigame_cooldowns["target_practice"] > 0:
                cd_txt = extra_small_font.render(
                    f"{int(minigame_cooldowns['target_practice'])}s",
                    True,
                    (150, 150, 150),
                )
                mg_surf.blit(cd_txt, (320, 155))

            # 3. Golden Rush
            gold_btn = pygame.Rect(50, 210, 300, 50)
            pygame.draw.rect(
                mg_surf,
                (
                    (50, 50, 30)
                    if minigame_cooldowns["golden_rush"] > 0
                    else (200, 180, 50)
                ),
                gold_btn,
                border_radius=5,
            )
            pygame.draw.rect(mg_surf, BUTTON_BORDER_COLOR, gold_btn, 2, border_radius=5)
            gold_txt = small_font.render("Golden Rush", True, TEXT_COLOR)
            mg_surf.blit(
                gold_txt,
                (200 - gold_txt.get_width() // 2, 235 - gold_txt.get_height() // 2),
            )
            if minigame_cooldowns["golden_rush"] > 0:
                cd_txt = extra_small_font.render(
                    f"{int(minigame_cooldowns['golden_rush'])}s", True, (150, 150, 150)
                )
                mg_surf.blit(cd_txt, (320, 225))

            screen.blit(mg_surf, mg_rect.topleft)

        if show_skill_tree:
            # Skill Tree Overlay
            st_surf = pygame.Surface((500, 450))
            st_surf.fill((20, 20, 40))
            st_rect = st_surf.get_rect(
                center=(SCREEN_SIZE[0] // 2, SCREEN_SIZE[1] // 2)
            )
            pygame.draw.rect(
                st_surf, (100, 50, 200), st_surf.get_rect(), 3, border_radius=5
            )

            title = medium_font.render(
                f"Skill Tree (SP: {skill_points})", True, (200, 150, 255)
            )
            st_surf.blit(title, (250 - title.get_width() // 2, 20))

            # Draw skills in a grid
            y_start = 80
            x_start = 50
            for i, (sid, sdata) in enumerate(skills.items()):
                row = i // 2
                col = i % 2
                x = x_start + col * 220
                y = y_start + row * 90

                # Skill Box
                skill_rect = pygame.Rect(x, y, 200, 80)
                color = (50, 100, 50) if sdata.get("unlocked", False) else (80, 80, 80)
                if (
                    skill_points >= sdata["cost"]
                    and not sdata.get("unlocked", False)
                    and (
                        not sdata.get("parent")
                        or skills[sdata["parent"]].get("unlocked", False)
                    )
                ):
                    color = (50, 150, 50)  # Affordable

                pygame.draw.rect(st_surf, color, skill_rect, border_radius=5)
                pygame.draw.rect(
                    st_surf, (200, 200, 200), skill_rect, 1, border_radius=5
                )

                name_txt = extra_small_font.render(sdata["name"], True, (255, 255, 255))
                st_surf.blit(name_txt, (x + 5, y + 5))

                desc_txt = extra_small_font.render(
                    f"Cost: {sdata['cost']} SP", True, (255, 215, 0)
                )
                st_surf.blit(desc_txt, (x + 5, y + 25))

                status = "Owned" if sdata.get("unlocked", False) else "Locked"
                if not sdata.get("unlocked", False) and skill_points >= sdata["cost"]:
                    status = "Buy!"
                stat_txt = extra_small_font.render(status, True, (200, 200, 200))
                st_surf.blit(stat_txt, (x + 5, y + 45))

            screen.blit(st_surf, st_rect.topleft)

        # === WHEEL PHYSICS ===
        if wheel_spinning:
            wheel_angle += wheel_speed * dt
            wheel_speed -= 200 * dt  # Friction
            if wheel_speed <= 0:
                wheel_speed = 0
                wheel_spinning = False
                # Determine result based on angle
                # Determine result based on angle
                # 8 segments, 45 degrees each
                current_angle = wheel_angle % 360
                segment = int(current_angle // 45)

                # wheel_prizes is defined in init and has 8 items
                # The wheel rotates clockwise. Index 0 is at 0 degrees (Right).
                # Segment 0 is 0-45 degrees.
                # If the pointer is at 0 (Right), and we rotate, the indices pass by.
                # We need to map segment to index carefully.
                # Let's assume standard mapping: idx = (8 - segment) % 8
                idx = (8 - segment) % 8
                res = wheel_prizes[idx]
                wheel_result = res

                # Give Reward
                if res["type"] == "money" or res["type"] == "jackpot":
                    money += res["value"]
                elif res["type"] == "money_mult":
                    # For multiplier, maybe add money or temp buff?
                    # The definition says value 2, 5, 10.
                    # Let's give a big money bonus based on current stats
                    bonus = 1000 * res["value"] * multiplier
                    money += bonus
                elif res["type"] == "skill_point":
                    skill_points += res["value"]
                elif res["type"] == "powerup":
                    # Add a powerup
                    active_powerups.append(
                        {
                            "name": "Double AFK",
                            "type": "afk_boost",
                            "multiplier": 2.0,
                            "duration": res["value"],
                            "color": res["color"],
                        }
                    )

                add_notification(notifications, f"Won: {res['name']}", res["color"])
                _safe_play(buy_effect)

        if show_lucky_wheel:
            # Wheel Overlay
            wh_surf = pygame.Surface((400, 400))
            wh_surf.fill((20, 60, 40))
            wh_rect = wh_surf.get_rect(
                center=(SCREEN_SIZE[0] // 2, SCREEN_SIZE[1] // 2)
            )
            pygame.draw.rect(
                wh_surf, (50, 200, 100), wh_surf.get_rect(), 3, border_radius=10
            )

            title = medium_font.render("Lucky Wheel", True, (100, 255, 100))
            wh_surf.blit(title, (200 - title.get_width() // 2, 20))

            # Draw Wheel Circle
            center_x, center_y = 200, 220
            radius = 120
            pygame.draw.circle(
                wh_surf, (200, 200, 200), (center_x, center_y), radius + 5
            )

            # Segments (simplified visualization)
            for i in range(8):
                angle = i * (360 / 8) + wheel_angle
                rad_angle = math.radians(angle)
                end_x = center_x + radius * math.cos(rad_angle)
                end_y = center_y + radius * math.sin(rad_angle)
                pygame.draw.line(
                    wh_surf, (100, 100, 100), (center_x, center_y), (end_x, end_y), 2
                )

            # Spin Button
            spin_btn = pygame.Rect(140, 360, 120, 40)
            btn_color = (
                (255, 215, 0)
                if free_spins_today > 0 and not wheel_spinning
                else (100, 100, 100)
            )
            pygame.draw.rect(wh_surf, btn_color, spin_btn, border_radius=5)

            btn_txt = small_font.render(
                "SPIN!" if not wheel_spinning else "...", True, (0, 0, 0)
            )
            wh_surf.blit(
                btn_txt,
                (200 - btn_txt.get_width() // 2, 380 - btn_txt.get_height() // 2),
            )

            screen.blit(wh_surf, wh_rect.topleft)

            # User Request: Improved Spin Feedback
            if wheel_result:
                # Show result popup over the wheel
                res_surf = pygame.Surface((300, 100))
                res_surf.fill((50, 50, 50))
                pygame.draw.rect(
                    res_surf,
                    wheel_result["color"],
                    res_surf.get_rect(),
                    4,
                    border_radius=8,
                )

                res_title = medium_font.render("YOU WON!", True, (255, 255, 255))
                res_name = small_font.render(
                    wheel_result["name"], True, wheel_result["color"]
                )

                res_surf.blit(res_title, (150 - res_title.get_width() // 2, 20))
                res_surf.blit(res_name, (150 - res_name.get_width() // 2, 60))

                screen.blit(
                    res_surf, (SCREEN_SIZE[0] // 2 - 150, SCREEN_SIZE[1] // 2 - 50)
                )

        pygame.display.flip()

        # decrement save message timer
        if save_msg_timer > 0:
            save_msg_timer = max(0.0, save_msg_timer - dt)

        # spawn/update specials (probabilistic per-second chance)
        if random.random() < 0.013 * dt:
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


# NEW: Helper functions for enhanced gameplay


def add_notification(notifications, text, color=(255, 255, 255), duration=2.5):
    """Add a notification to the queue."""
    notifications.append(
        {"text": text, "color": color, "timer": duration, "y_offset": 0}
    )


def update_notifications(notifications, dt):
    """Update and remove expired notifications."""
    for notif in notifications[:]:
        notif["timer"] -= dt
        if notif["timer"] <= 0:
            notifications.remove(notif)


def draw_notifications(surface, notifications, font):
    """Draw all active notifications."""
    y_start = 10
    for i, notif in enumerate(notifications):
        alpha = min(255, int(notif["timer"] * 255)) if notif["timer"] < 1.0 else 255
        text_surf = font.render(notif["text"], True, notif["color"])
        text_surf.set_alpha(alpha)
        y_pos = y_start + (i * 22)  # Reduced spacing from 30 to 22
        surface.blit(
            text_surf, (surface.get_width() - text_surf.get_width() - 10, y_pos)
        )


def spawn_damage_number(damage_numbers, pos, value, color=(255, 255, 100)):
    """Spawn a floating damage number."""
    damage_numbers.append(
        {
            "pos": [float(pos[0]), float(pos[1])],
            "vel": [random.uniform(-20, 20), random.uniform(-80, -40)],
            "text": f"+${int(value)}",
            "color": color,
            "life": 1.2,
            "max_life": 1.2,
        }
    )


def update_damage_numbers(damage_numbers, dt):
    """Update floating damage numbers."""
    for dmg in damage_numbers[:]:
        dmg["pos"][0] += dmg["vel"][0] * dt
        dmg["pos"][1] += dmg["vel"][1] * dt
        dmg["vel"][1] += 120 * dt  # gravity
        dmg["life"] -= dt
        if dmg["life"] <= 0:
            damage_numbers.remove(dmg)


def draw_damage_numbers(surface, damage_numbers, font):
    """Draw floating damage numbers."""
    for dmg in damage_numbers:
        alpha = int(255 * (dmg["life"] / dmg["max_life"]))
        text_surf = font.render(dmg["text"], True, dmg["color"])
        text_surf.set_alpha(alpha)
        surface.blit(text_surf, (int(dmg["pos"][0]), int(dmg["pos"][1])))


def update_screen_shake(screen_offset, shake_intensity, shake_duration, dt):
    """Update screen shake effect."""
    if shake_duration > 0:
        shake_duration -= dt
        if shake_duration > 0:
            screen_offset[0] = random.uniform(-shake_intensity, shake_intensity)
            screen_offset[1] = random.uniform(-shake_intensity, shake_intensity)
        else:
            screen_offset[0] = 0
            screen_offset[1] = 0
    return shake_duration


def trigger_screen_shake(intensity, duration):
    """Trigger a screen shake effect."""
    return intensity, duration


def check_achievement(
    achievements, achievement_defs, ach_id, achievement_queue, notifications, money_ref
):
    """Check and unlock an achievement. Auto-initializes missing IDs."""
    # Ensure the achievement exists in the tracking dict
    if ach_id not in achievements:
        achievements[ach_id] = {"unlocked": False, "progress": 0}

    # If already unlocked, skip
    if achievements[ach_id].get("unlocked", False):
        return 0

    # Check if definition exists
    if ach_id not in achievement_defs:
        return 0  # No definition, can't unlock

    # Unlock!
    achievements[ach_id]["unlocked"] = True
    ach_data = achievement_defs[ach_id]
    achievement_queue.append(ach_data)
    add_notification(notifications, f"Achievement: {ach_data['name']}!", (255, 215, 0))
    return ach_data.get("reward", 0)


def draw_achievement_popup(surface, achievement_data, timer, font, small_font):
    """Draw achievement unlock popup."""
    if timer <= 0:
        return

    # Slide in from right
    progress = min(1.0, (3.0 - timer) / 0.5)  # 0.5s slide in
    fade_out = 1.0 if timer > 0.5 else (timer / 0.5)

    # Smaller size
    width = 280
    height = 70
    # Position at bottom-right corner
    x = surface.get_width() - width - 10
    y = surface.get_height() - height - 80  # Above wipe button

    # Slide animation from right
    x_offset = int((1.0 - progress) * width)

    # Draw panel
    panel_surf = pygame.Surface((width, height), pygame.SRCALPHA)
    alpha = int(255 * fade_out)
    pygame.draw.rect(
        panel_surf, (40, 40, 40, alpha), panel_surf.get_rect(), border_radius=8
    )
    pygame.draw.rect(
        panel_surf, (255, 215, 0, alpha), panel_surf.get_rect(), 2, border_radius=8
    )

    # Draw text - smaller and more compact
    title = small_font.render("Achievement!", True, (255, 215, 0))
    title.set_alpha(alpha)
    name = small_font.render(achievement_data["name"], True, (255, 255, 255))
    name.set_alpha(alpha)

    panel_surf.blit(title, (10, 8))
    panel_surf.blit(name, (10, 28))

    # Show reward if any
    if achievement_data.get("reward", 0) > 0:
        reward_text = small_font.render(
            f"+${achievement_data['reward']}", True, (100, 255, 100)
        )
        reward_text.set_alpha(alpha)
        panel_surf.blit(reward_text, (10, 48))

    surface.blit(panel_surf, (x + x_offset, y))


def get_combo_multiplier(combo_count):
    """Calculate combo multiplier based on combo count. (Nerfed for balance)"""
    if combo_count < 10:
        return 1.0
    elif combo_count < 25:
        return 1.05
    elif combo_count < 50:
        return 1.1
    elif combo_count < 100:
        return 1.15
    else:
        return 1.2


def draw_combo_meter(surface, combo_count, combo_timer, combo_timeout, font, pos):
    """Draw combo counter and timer bar."""
    if combo_count <= 0:
        return

    # Combo text
    combo_mult = get_combo_multiplier(combo_count)
    combo_text = font.render(
        f"{combo_count}x COMBO! ({combo_mult}x)", True, (255, 100, 100)
    )

    # Pulsing effect
    scale = 1.0 + 0.1 * math.sin(pygame.time.get_ticks() / 100)
    scaled_width = int(combo_text.get_width() * scale)
    scaled_height = int(combo_text.get_height() * scale)
    scaled_text = pygame.transform.scale(combo_text, (scaled_width, scaled_height))

    x = pos[0] - scaled_width // 2
    y = pos[1]
    surface.blit(scaled_text, (x, y))

    # Timer bar
    bar_width = 200
    bar_height = 10
    bar_x = pos[0] - bar_width // 2
    bar_y = y + scaled_height + 5

    # Background
    pygame.draw.rect(
        surface, (60, 60, 60), (bar_x, bar_y, bar_width, bar_height), border_radius=5
    )

    # Fill based on remaining time
    fill_width = int(bar_width * (combo_timer / combo_timeout))
    if fill_width > 0:
        color = (255, 100, 100) if combo_timer > combo_timeout * 0.3 else (255, 50, 50)
        pygame.draw.rect(
            surface, color, (bar_x, bar_y, fill_width, bar_height), border_radius=5
        )


def draw_tooltip(surface, rect, text, font):
    """Draw a tooltip near the given rect."""
    if not text:
        return

    lines = text.split("\n")
    line_height = 20
    padding = 10

    max_width = max(font.size(line)[0] for line in lines)
    tooltip_width = max_width + padding * 2
    tooltip_height = len(lines) * line_height + padding * 2

    # Position above the rect
    tooltip_x = rect.centerx - tooltip_width // 2
    tooltip_y = rect.top - tooltip_height - 10

    # Keep on screen
    tooltip_x = max(5, min(tooltip_x, surface.get_width() - tooltip_width - 5))
    tooltip_y = max(5, tooltip_y)

    # Draw background
    tooltip_surf = pygame.Surface((tooltip_width, tooltip_height), pygame.SRCALPHA)
    pygame.draw.rect(
        tooltip_surf, (30, 30, 30, 230), tooltip_surf.get_rect(), border_radius=5
    )
    pygame.draw.rect(
        tooltip_surf, (200, 200, 200, 230), tooltip_surf.get_rect(), 2, border_radius=5
    )

    # Draw text
    for i, line in enumerate(lines):
        text_surf = font.render(line, True, (255, 255, 255))
        tooltip_surf.blit(text_surf, (padding, padding + i * line_height))

    surface.blit(tooltip_surf, (tooltip_x, tooltip_y))


def calculate_prestige_gain(money, total_clicks):
    """Calculate how many grass seeds you'd get from prestiging."""
    # Formula: sqrt(money / 100000) + sqrt(total_clicks / 1000)
    money_seeds = math.sqrt(max(0, money / 100000))
    click_seeds = math.sqrt(max(0, total_clicks / 1000))
    return int(money_seeds + click_seeds)
