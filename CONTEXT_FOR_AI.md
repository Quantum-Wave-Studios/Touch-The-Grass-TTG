# Touch The Grass (TTG) – Project Context for AI

## Project Overview

**Touch The Grass** is a Python/Pygame clicker game where players click on grass to earn money, unlock grass variants, and purchase upgrades (AFK income, click multiplier). The project has been enhanced with advanced particle effects, cross-platform save/load, audio hardening, and interactive special collectibles.

**Repository**: https://github.com/MrTarik2112/Touch-The-Grass-TTG  
**Owner/Developer**: MrTarik2112  
**Engine**: Python 3.8+ with Pygame (pygame-ce)  
**Platform**: Windows (executable), Linux/macOS (from source)

---

## Current Feature Set

### Gameplay

- **Main mechanic**: Click central grass sprite to earn money.
- **Multiplier system**: Upgrade click power via `multiplier` stat (scales money per click).
- **AFK income**: Passive money generation (scales with multiplier and grass variant).
- **Weather system**: Every 50 seconds, weather randomizes (Normal/Sunny/Rainy/Stormy) and applies a multiplier (1.0–1.9×) to income and click damage.
- **Grass variants**: 6 grass types (unlockable via shop: Normal, Golden, Frozen, Diamond, Mystic, Blackhole), each with higher base stats and costs; owned variants can be switched.
- **Special collectibles**: Watercan items spawn probabilistically (0.10/sec), appear briefly (10–20s), and can be clicked for bonus money (800–3500). They have:
  - Vertical bobbing animation
  - Horizontal sway (left-right)
  - Subtle rotation (tilt)
  - Clickable radius that scales with sprite size
  - Particle burst, floating damage numbers, and sound feedback on collection
- **Combo system**: Consecutive grass clicks within 1.5 seconds build a combo multiplier (1.5×–5.0× based on combo count); displayed with animated combo meter, timer bar, and particle effects. Higher combos trigger stronger screen shake.
- **Achievement system**: 20+ achievements tracking milestones (clicks, money, combos, upgrades, grass purchases, special collections, daily streaks) with monetary rewards. Achievements display with slide-in popups and notifications.
- **Prestige system** (structure ready): Reset progress to earn grass seeds and gain permanent multiplier bonuses (10% per prestige level).
- **Power-up system** (structure ready): Timed bonuses (click boost, AFK boost) with visual indicators and countdown timers.
- **Daily rewards**: Login streak tracking with escalating rewards ($100 × streak^1.5); displays popup on login showing streak count and reward amount.
- **Floating damage numbers**: Visual feedback showing money earned on each click/collection with physics-based animation (rise, gravity, fade-out) and color coding (yellow for clicks, gold for specials).

### UI & UX

- **Stats panel** (left): Money, AFK income, click power, total clicks, upgrade costs, prestige level, grass seeds
- **Weather panel** (left): Current weather, time until next change
- **Combo meter** (center-top): Displays current combo count and timeout bar; visual feedback for consecutive collects
- **Achievement popup** (center): Displays unlocked achievements with name, description, and reward amount
- **Daily reward banner** (center): Shows login streak and reward amount earned
- **Control buttons** (right): AFK Upgrade, Multiplier Upgrade, Save, Stats, Shop, Prestige, Settings, Wipe Save
- **Sound toggle** (top-right): Enable/disable audio (music and all effects)
- **FPS counter** (top-left, optional): Shows current frame rate (configurable in settings)
- **Notification system**: Toast-style messages for game events (auto-save, achievement unlocks, etc.)
- **Floating damage numbers**: Money earned per click displayed as rising numbers near click position
- **Power-up indicator** (top-center): Shows active power-ups with countdown timers
- **Tooltip system**: Hover-based hints for buttons and UI elements
- **Modal overlays**: Statistics, Grass Shop, Prestige Menu, Settings screens (centered, with close buttons)
- **Text color coding**: Gold/yellow for money, white for labels, colored text for button states, green for achievements

### Particle System

- **Pooled particles** (max 700 simultaneous) for performance.
- **Emission modes**:
  - Side emission (20%): horizontal burst, tiny, short-lived
  - Pop-up (45%): rise then fall, moderate size, gentle lateral spread
  - Fall-first (35%): gravity-dominant from spawn
- **Physics**: Per-particle velocity, drag, wind, gravitational lift window, side acceleration, oscillation.
- **Color interpolation**: Particles fade from `shade_start` to `shade_end` over lifetime.
- **Special cases**:
  - Green particles (grass-colored) sometimes spawn green-toned variants or tiny vivid flecks.
  - Yellow particles occasionally shift toward green tones.
- **Size scaling**: Particles are ~36% larger than base to remain visible at distance.
- **Visual effects**: Cached drawing (rounded RGB, alpha variants) to minimize Surface allocations.

### Save/Load System

- **Cross-platform**: Uses `get_save_dir()` to write to OS-appropriate directories (Windows: AppData, Linux: ~/.local/share).
- **Format**: JSON with human-readable indentation.
- **Atomic writes**: Temp file + `os.replace()` to prevent corruption.
- **Auto-save**: Automatic save every 30 seconds during gameplay; manual save via "Save Game" button.
- **Data**: money, multiplier, auto_income, total_clicks, upgrade costs, highest_money, grass variant, weather_index, combo stats, achievements, prestige_level, grass_seeds, login streak, daily login date, power-up states, settings.

### Audio

- **Safe initialization**: Attempts normal mixer init; falls back to SDL dummy driver if unavailable (Linux/Wine/headless).
- **MIXER_AVAILABLE flag**: Set in game_loop so callers can skip audio operations if mixer failed.
- **Safe wrappers**: `_safe_set_volume()`, `_safe_play()`, `_safe_music_pause()`, `_safe_music_unpause()`.
- **Sounds**:
  - `click.mp3`: Grass click feedback
  - `back.mp3`: Music (looped)
  - `buy_effect`: Generic success/upgrade sound
  - `weather_change_effect`: Transition between weather states

---

## Code Architecture

### File Structure

```
Main/game/
├── __main__.py              # Entry point, calls game.py
├── __init__.py              # Package marker
├── game.py                  # Bootstrap: pygame init, mixer safe-init, asset load, run_loop call
├── game_loop.py             # Main loop (~2400 lines): render, input, particles, specials, UI
├── assets.py                # Asset loading (images, fonts); resource_path() for PyInstaller compat
├── paths.py                 # Relative asset paths (case-sensitive for Linux)
├── settings.py              # Constants: SCREEN_SIZE=(800,600), MIN/MAX_SCALE, etc.
├── runtime_hook.py          # PyInstaller data-file collection hints (unused in current build)
├── line_counter.go          # Utility to count project lines (not part of game)

Assets/
├── fonts/
│   └── PixelifySans-Regular.ttf
├── images/
│   ├── grass1.png           # Main grass sprite
│   ├── watercan.png         # Special collectible sprite
│   ├── icon.ico             # Window icon
│   └── (additional variants if any)
└── sounds/
    ├── click.mp3
    └── back.mp3
```

### Key Functions & Classes

#### `game_loop.py`

- **`spawn_particles(p_list, position, color, count=12)`**: Spawn pooled pixel particles with varied physics.
- **`update_particles(p_list, dt)`**: Update particle positions, velocities, lifetimes; recycle dead ones to pool.
- **`draw_particles(surface, p_list)`**: Render particles with alpha/color caching; apply oscillation offset.
- **`draw_button(screen, rect, bg_color, border_color, text, font, dt, effect_name=None)`**: Draw interactive button with:
  - SmoothDamp hover/press animations
  - Cached shadow and base surfaces
  - Mouse cursor updates (hand on hover)
- **`run_loop(screen, clock, assets)`**: Main game loop (144 FPS target, dt clamped to 0.1s):
  - Update particle physics, combo timer, notifications, damage numbers, screen shake
  - Check mouse input and button collisions
  - Render UI, stats panel, shop, weather, grass sprite (with scale/rotation animation)
  - Manage special collectible spawning, drawing, click collection
  - Check and unlock achievements
  - Auto-save every 30 seconds
  - Decay and remove expired specials
  - Save game on quit
  - Render particles, damage numbers, combo meter, achievement popups last (foreground)

**New Helper Functions (Session 5: Game Enhancements):**

- **`add_notification(notifications, text, color, duration)`**: Queue a notification message with color and display duration.
- **`update_notifications(notifications, dt)`**: Update notification timers and remove expired ones.
- **`draw_notifications(surface, notifications, font)`**: Render notification stack in top-right corner with fade effects.
- **`spawn_damage_number(damage_numbers, pos, value, color)`**: Create a floating damage number at position with physics.
- **`update_damage_numbers(damage_numbers, dt)`**: Update damage number physics (velocity, gravity, lifetime).
- **`draw_damage_numbers(surface, damage_numbers, font)`**: Render floating damage numbers with alpha fade.
- **`update_screen_shake(screen_offset, shake_intensity, shake_duration, dt)`**: Update camera shake effect.
- **`trigger_screen_shake(intensity, duration)`**: Start a screen shake with given intensity and duration.
- **`check_achievement(achievements, achievement_defs, ach_id, achievement_queue, notifications, money_ref)`**: Check and unlock achievement, return reward amount.
- **`draw_achievement_popup(surface, achievement_data, timer, font, small_font)`**: Render achievement unlock popup with slide-in animation.
- **`get_combo_multiplier(combo_count)`**: Calculate combo multiplier (1.0× to 5.0×) based on combo count.
- **`draw_combo_meter(surface, combo_count, combo_timer, combo_timeout, font, pos)`**: Render animated combo counter and timer bar.
- **`draw_tooltip(surface, rect, text, font)`**: Draw hover tooltip near given rect (currently structure ready).
- **`calculate_prestige_gain(money, total_clicks)`**: Calculate grass seeds earned from prestiging.

#### `assets.py`

- **`resource_path(relative_path)`**: Resolve asset paths relative to `Main/` directory:
  - Check for PyInstaller `_MEIPASS` temp folder (executables)
  - Fall back to dev directory structure
  - Print debug logs for troubleshooting
- **`load_assets()`**: Load and cache all images, fonts, and special collectible sprite:
  - `grass_img`: Main grass (scaled to 41% of original size)
  - `custom_font`: 36pt Pixelify Sans for text rendering
  - `icon`: Window icon
  - `watercan`: Special collectible image (loaded from `Assets/images/watercan.png`)

#### `game.py`

- Safe mixer initialization with fallback to dummy driver.
- Pygame init, window setup, icon assignment.
- Asset load and main loop invocation.

#### `paths.py`

- Path constants for all assets (case-sensitive `Assets` folder for Linux compatibility).

#### `settings.py`

- Screen dimensions, scale ranges, animation constants.

---

## Special Collectibles (Watercan) – Detailed Behavior

### Spawning

- **Trigger**: Per-frame probabilistic check: `if random.random() < 0.06 * dt` (average 1 every ~16.7 seconds).
- **Position**: Random (x, y) within screen bounds with margins (120–680 pixels horizontally, 120–380 vertically).
- **Life**: Random 10–20 seconds; decrements each frame, object removed when life ≤ 0.
- **Value**: Random 800–3500 money reward on click.
- **Sprite**: Loaded from `assets["watercan"]`, scaled to max 64×64 pixels, with click radius adjusted to match sprite size.

### Animation

Each special has three simultaneous animated motions:

1. **Vertical bob**: `sin(anim_time * speed + phase) * amplitude` (4–10 pixel range, 0.8–1.8× speed).
2. **Horizontal sway**: `sin(anim_time * speed + phase) * amplitude` (6–18 pixel range, 0.6–1.6× speed).
3. **Rotation**: Sprite rotates ±6–20° smoothly back-and-forth (0.8–1.6× speed).

### Interaction

- **Click detection**: Distance-based (`r ≤ click_radius`); accounts for current bob and sway offsets.
- **Collection**: On click:
  - Money += special["value"]
  - Spawn 20 golden particles at special position (255, 215, 80 color)
  - Play `buy_effect` sound (if MIXER_AVAILABLE)
  - Remove special from list immediately
- **Expiration**: Special is drawn but not collected if life > 0; removed after life ≤ 0.

---

## New Systems & Features (Latest Session)

### Combo System

- **Mechanic**: Each special collectible clicked within 1.5 seconds of the previous one increases combo count.
- **Multiplier**: Combo applies a bonus multiplier (1.0× base + 0.1× per combo level) to special rewards.
- **Display**: Combo meter shows current count and remaining time until timeout; color changes at milestones (orange → green → red).
- **Achievement integration**: Combo milestones (10×, 25×, 50×) trigger achievements with rewards.
- **Save/load**: Combo state persists across sessions.

### Achievement System

- **20+ achievements** covering:
  - Click milestones (100, 1000, 10000 clicks)
  - Money milestones ($1k, $10k, $100k, $1M)
  - Combo milestones (10×, 25×, 50×)
  - Upgrade milestones (first AFK, first multiplier, buy grass variants)
  - Prestige (first rebirth)
  - Daily login streaks (7 days)
  - Special collectible collection (1, 10 collected)
  - Power-up collection
- **Display**: Pop-up overlay when achievement is unlocked, showing name, description, and reward.
- **Rewards**: Money bonus (10–50,000 depending on achievement).
- **Tracking**: Saved in JSON; prevents duplicate rewards.

### Prestige System

- **Purpose**: Reset progress to earn permanent bonuses; enables long-term progression goal.
- **Mechanics**:
  - Player clicks "Prestige" button (available when high money threshold reached, e.g., $100k)
  - Resets: money, multiplier, auto_income, total_clicks, current_grass_index
  - Rewards: Grass Seeds (calculated from total money earned: `seeds = int(sqrt(money) / 10)`)
  - Permanent bonus: +10% multiplier per prestige level (applied to all future calculations)
- **Menu**: Prestige Modal shows projected seeds earned and confirmation button.
- **Data**: prestige_level and grass_seeds tracked in save file.

### Power-up System

- **Spawn**: Random power-ups spawn every 45–90 seconds when active_powerups list < max.
- **Types** (examples):
  - 2× Income (30 seconds): AFK income doubled
  - 5× Click Power (20 seconds): Click multiplier × 5
  - Money Rain (15 seconds): +$1000 per second
  - Instant Wealth (10 seconds): +$50k once
- **Display**: Icon + timer on top of screen; notification when activated.
- **Collection**: Power-ups must be clicked before expiry; auto-removed when timer reaches zero.
- **Visual feedback**: Glowing sprite, countdown timer, particle effects on collection.

### Daily Reward System

- **Trigger**: On game start, check if today's login already claimed.
- **Streak tracking**: Consecutive daily logins increase reward multiplier.
  - Day 1: $100 + bonus 10% of daily wealth
  - Day 7: $5000 + bonus 70% of daily wealth
- **Display**: Modal showing streak count and reward amount; auto-closes after 3 seconds or on click.
- **Reset**: Streak resets if login skipped for a day.
- **Data**: Saved as `last_login_date` and `login_streak` in JSON.

### Floating Damage Numbers

- **Spawn**: Each grass click generates a floating number showing money earned at click position.
- **Physics**: Numbers rise upward with fade-out over ~1 second.
- **Color coding**:
  - Yellow (normal clicks)
  - Gold (special collects)
  - Green (power-up bonus)
  - Red (prestige milestone)
- **Display**: Rendered above particles but below UI.

### Screen Shake

- **Trigger**: Major events (milestone achievements, prestige, special collect, big wins).
- **Effect**: Camera offset (±pixels) applied to all screen-space drawing; intensity decays over duration.
- **Configurable**: Intensity and duration parameters; can be disabled in settings.
- **Performance**: Minimal overhead; only active when triggered.

### Notification System

- **Display**: Toast-style messages appearing at bottom-center, fading after duration.
- **Types**: Auto-save confirmations, achievement unlocks, power-up alerts, milestone messages.
- **Color/icon**: Different colors for different notification types.
- **Stacking**: Multiple notifications queue and display sequentially.

### Tooltip System

- **Mechanic**: Hover over UI elements (buttons, stats labels) to see helpful hint text.
- **Delay**: Shows after 0.5 second hover to avoid visual clutter.
- **Positioning**: Appears above/below element depending on screen space.
- **Content**: Button descriptions, stat explanations, upgrade tips.

### Settings Menu

- **Options**:
  - Screen Shake: Enable/disable camera shake effects
  - Show FPS: Toggle frame rate display
  - Particle Density: Slider to adjust particle count (0.5× – 2.0×)
  - Master Volume: Audio volume slider (0–100%)
- **Persistence**: Settings saved in JSON under `settings` key.
- **UI**: Modal menu with sliders and checkboxes; apply/reset buttons.

### Auto-save System

- **Interval**: Saves game every 30 seconds during active gameplay.
- **Manual save**: Player can also save via "Save Game" button anytime.
- **Indicator**: Brief flash/notification when auto-save completes.
- **Safety**: Uses same atomic write as manual save; no risk of corruption.

## Performance Optimizations

1. **Particle pooling**: Reuse particle dicts instead of allocating new ones; clear on reuse.
2. **Alpha/color caching**: Particles grouped by `(size, rounded_RGB)` key; alpha variants cached to avoid per-particle Surface.copy().
3. **Draw caching**: Button backgrounds and shadows cached; invalidated on hover/press state change.
4. **Background gradient**: Cached per-frame (simple color fill; real gradient would use stored Surface).
5. **Font rendering**: Text surfaces rendered once per value change, reused across frames (e.g., multiplier_value).
6. **Clock tick strategy**: Use `clock.tick_busy_loop(144)` for high-refresh displays; fall back to `clock.tick(144)` on error.
7. **dt clamping**: Frame deltas capped at 0.1s to prevent huge time jumps (useful for debugger breakpoints).
8. **Damage number/notification culling**: Only active items drawn; expired items removed from lists.
9. **Achievement bulk-checking**: Check achievements only on relevant actions (click, money update, upgrades) rather than every frame.
10. **Power-up effect batching**: Apply multiple power-ups' effects in single pass to reduce per-frame overhead.

---

## Known Issues & Limitations

1. **Large watercan images**: If `watercan.png` is very large (>512×512 px), the size cap (64 px max) may make it barely visible. Recommend providing a ~80–128 px sprite.
2. **Audio fallback**: On some Wine/Docker setups, even dummy driver init may fail; code gracefully handles `MIXER_AVAILABLE = False`.
3. **Save path on very old Windows**: `get_save_dir()` uses `os.path.expandvars()` which may not work on legacy systems; untested on Windows XP or earlier.
4. **Particle count**: 700 max is a soft limit; spawning more than 700 in one frame will skip particles to stay under cap.
5. **Stats/Shop modal overlap**: Multiple modal overlays (stats + shop) cannot be open simultaneously by design.

---

## Recent Changes & Development Notes

### Session 1: Cross-Platform & Audio Hardening

- **Linux save errors**: Implemented `get_save_dir()` (cross-platform AppData/local share) and atomic JSON writes.
- **Audio crashes**: Guarded mixer init with fallback to SDL dummy driver; added MIXER_AVAILABLE flag and safe wrappers.

### Session 2: Particle System & Visual Polish

- **Particles**: Implemented pooling, three emission modes, per-particle physics (drag, wind, gravity lift window, oscillation).
- **Color interpolation**: Particles fade from shade_start to shade_end; special handling for green and yellow tones.
- **Draw caching**: Reduced allocations via alpha/color grouping.
- **Button animations**: Added SmoothDamp smoothing for hover/press effects and cached shadows.

### Session 3: Special Collectibles

- **Watercan spawn**: Probabilistic (0.06/sec) rather than timer-based; spawns at random screen position.
- **Click interaction**: Distance-based hit detection; awards money, triggers particle burst and sound.
- **Animation**: Added vertical bob, horizontal sway, and subtle rotation for lively appearance.

### Session 4: Animation Enhancements

- **Sway & rotation**: Each special gets unique sway speed, amplitude, phase, and rotation parameters (randomized per spawn).
- **Realistic movement**: Combines three simultaneous motions for organic, playful feel.
- **Click accuracy**: Hit detection updated to account for animation offsets (bob + sway).

### Session 5: Advanced Gameplay Systems (Current)

- **Combo system**: Special collectible chain mechanic with bonus multiplier and achievement tracking.
- **Achievement system**: 20+ achievements with rewards, tracking all major game milestones.
- **Prestige system**: Progress reset mechanic granting permanent bonuses and long-term goals.
- **Power-up system**: Timed random bonuses (income, click power, instant wealth) with visual indicators.
- **Daily rewards**: Login streak tracking with escalating daily bonuses.
- **Floating damage numbers**: Visual feedback for money earned on clicks.
- **Screen shake**: Camera effect triggered by major events.
- **Notification system**: Toast messages for important game events.
- **Tooltip system**: Hover hints for UI elements and buttons.
- **Settings menu**: In-game customization (screen shake, FPS display, particle density, volume).
- **Auto-save system**: Game saves automatically every 30 seconds; manual save anytime via button.

### Session 6: MASSIVE Game Enhancement (Latest)

- **Critical Hit System**: 5% base critical hit chance with 5x damage multiplier. Critical hits trigger special particle effects, screen shake, and red damage numbers. Skill tree upgrades increase crit chance and multiplier.
- **Skill Tree System**: 12 skills across 4 branches (Click Power, AFK Income, Luck, Combo). Skills purchased with Skill Points (SP) earned from boss defeats. Each skill has multiple levels with increasing costs.
- **Boss Battle System**: Bosses spawn every 5 minutes with 60-second time limit. 5 boss types (Grass Golem, Stone Giant, Crystal Titan, Shadow Beast, Golden Dragon) with scaling HP and rewards. Defeating bosses grants money and Skill Points.
- **Mini-Games System**: 3 mini-games accessible via "Mini-Games" button:
  - Click Frenzy: Click grass as fast as possible for 10 seconds
  - Target Practice: Click disappearing targets for points
  - Golden Rush: Catch falling gold coins
- **Lucky Wheel**: Daily free spin for prizes (money bonuses, multipliers, skill points, power-ups). 8 prize segments with varying rewards.
- **Offline Progress**: Earn AFK income while game is closed (up to 8 hours, 50% efficiency). "Welcome Back" popup shows offline earnings.
- **Seasonal Events**: Automatic bonuses based on current month:
  - December: Winter Wonderland (1.5x multiplier)
  - October: Spooky Season (1.3x multiplier)
  - April: Spring Bloom (1.2x multiplier)
  - July/August: Summer Heat (1.4x multiplier)
- **50+ New Achievements**: Tiered achievements (bronze/silver/gold/platinum/diamond) for:
  - Click milestones (100k, 1M clicks)
  - Money milestones ($10M, $100M)
  - Combo records (100x, 200x)
  - Critical hit counts
  - Boss defeats
  - Mini-game scores
  - Skill purchases
  - Wheel spins
  - Prestige levels
  - Playtime milestones
- **Enhanced Statistics**: Tracking total playtime, all-time clicks, highest combo ever, bosses defeated, critical hits, and more.
- **Enhanced Power-ups**: 6 power-up types including Rainbow Mode (rainbow particle colors) and Critical Boost (+20% crit chance).
- **UI Enhancements**: New buttons for Mini-Games, Skills (with SP count), Wheel (with free spins), and Prestige (appears when money >= $100k).

---

## Next Possible Enhancements

1. ~~**Skill trees**: Tech tree for unlocking new abilities and permanent upgrades.~~ ✅ DONE
2. ~~**Mini-games**: Bonus rounds for extra rewards.~~ ✅ DONE
3. ~~**Seasonal events**: Limited-time challenges, themed power-ups, holiday multipliers.~~ ✅ DONE
4. **Leaderboard/statistics**: High-score tracking (local JSON or cloud API); compare stats with friends.
5. **Grass cosmetics**: Custom skins, animated grass variants, particle color customization.
6. **Sound improvements**: Dynamic audio (pitch-shifting based on multiplier, combo audio effects).
7. **Mobile port**: Touch-based controls for Android/iOS; responsive UI scaling.
8. **Clan/multiplayer**: Shared progress, cooperative bonuses, leaderboards.
9. **Mod support**: Allow custom power-ups, grass types, sounds via JSON configs.
10. **Analytics/telemetry**: Track playtime, progression speed, feature usage (opt-in).

---

## How to Extend or Debug

### Adding a New Button

1. Define button rect in `run_loop()` near other button rects.
2. Call `draw_button()` with desired color, text, font, and effect name.
3. Add event handler in `pygame.MOUSEBUTTONDOWN` section.
4. Spawn particles at button center for visual feedback.

### Adding a New Particle Color/Type

1. Call `spawn_particles(particles, position, color, count=N)` with desired RGB tuple and count.
2. Particles will auto-allocate from pool or create new dicts.
3. Customize emission mode by modifying `spawn_particles()` logic.

### Debugging Asset Loading

- Check console output from `resource_path()` for resolved paths.
- Ensure asset files exist in `Main/Assets/` with correct casing.
- Verify `pygame.image.load()` does not raise exceptions.

### Adjusting Particle Physics

- Modify `spawn_particles()` velocity ranges, drag, wind, and oscillation parameters.
- Tweak `update_particles()` gravity, lift window, and decay logic.
- Adjust `draw_particles()` color interpolation and alpha caching thresholds.

### Tuning Special Collectible Spawn

- Change `SPAWN_CHANCE_PER_SECOND` constant in `run_loop()` for spawn frequency.
- Adjust `max_dim` (currently 64) in special spawn logic to change visual size cap.
- Modify life range `random.uniform(10.0, 20.0)` to make specials appear longer/shorter.
- Tweak `osc_amp`, `sway_amp`, `rot_amp` ranges for more/less animation movement.

---

## Build & Deployment

### Running from Source

```bash
cd c:/Users/tarik/Documents/PY/Touch-The-Grass-TTG
.venv/Scripts/activate
python Main/game/__main__.py
```

### Building Executable (PyInstaller)

```bash
pip install pyinstaller
python build_exe.py
# or manually:
pyinstaller TouchTheGrass.spec
```

### Distribution

- Single-file exe: Easier to distribute; slower startup.
- Directory exe: Faster startup; requires folder of DLLs/assets.

---

## Contact & Contribution

- **GitHub**: https://github.com/MrTarik2112/Touch-The-Grass-TTG
- **Developer**: MrTarik2112
- **License**: (Check repo for license file; assuming MIT or similar)

---

## Glossary

- **dt**: Delta time (seconds elapsed since last frame).
- **anim_time**: Accumulated animation time used for sinusoidal effects.
- **MIXER_AVAILABLE**: Boolean flag indicating if audio system initialized successfully.
- **Pooling**: Reusing object dicts instead of creating new ones; improves GC and cache locality.
- **SmoothDamp**: Gradual approach to target value (used for button press/hover animations).
- **Special**: Short for "special collectible" (watercan item).
- **Bob**: Vertical oscillating motion.
- **Sway**: Horizontal oscillating motion.

---

**Document generated**: 2025-12-08  
**Last modified by**: Development AI Assistant  
**Status**: Ready for handoff to another AI or team member
