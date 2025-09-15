import pygame
import sys
from .settings import SCREEN_SIZE, CENTER, MIN_SCALE, MAX_SCALE
import os


income = 0
def run_loop(screen, clock, assets):
    """Ana oyun döngüsü. Ekranda animasyon ve para sayacını günceller."""

    money = 0
    multiplier = 1

    # Assets dictionary'den gerekli görselleri ve fontu al
    grass_img_original = assets['grass_img']
    custom_font = assets['custom_font']
    # Daha küçük font boyutu için yeni fontlar oluştur
    medium_font = pygame.font.Font(pygame.font.match_font('arial'), 24)
    small_font = pygame.font.Font(pygame.font.match_font('arial'), 20)

    # sesleri yükle ve çal
    pygame.mixer.music.load('Main/assets/sounds/back.mp3')
    pygame.mixer.music.play(-1)  # Sonsuz döngüde çal
    pygame.mixer.music.set_volume(0.02896705)  # Ses seviyesini ayarla (0.0 - 1.0)
    click_effect = pygame.mixer.Sound("Main/assets/sounds/click.mp3")
    buy_effect = pygame.mixer.Sound("Main/assets/sounds/buy.mp3")

    # Yükseltme bilgileri
    afk_upgrade_cost = 15        # AFK gelir yükseltme başlangıç fiyatı
    multiplier_upgrade_cost = 10  # Çarpan yükseltme başlangıç fiyatı
    auto_income = 0.0            # Otomatik gelir (saniyede artan miktar)

    # Başlangıç ayarları
    scale_factor = 1.0          # Orijinal boyutta başla
    rotation_angle = 0          # Başlangıç dönüş açısı
    rotation_direction = 1      # Dönüş yönü (1: saat yönü, -1: ters yön)
    scale_direction = 1         # Ölçek yönü (1: büyüt, -1: küçült)

    # Resmin konumunu belirle
    grass_rect = grass_img_original.get_rect()
    grass_rect.center = CENTER

    # Buton ayarları
    afk_button_rect = pygame.Rect(0, 0, 0, 0)  # Başlangıçta boş, sonra güncellenecek
    multiplier_button_rect = pygame.Rect(0, 0, 0, 0)  # Başlangıçta boş, sonra güncellenecek

    # İstatistikler
    total_clicks = 0
    
    # Renk tanımları
    BACKGROUND_COLOR = (20, 38, 24)
    TEXT_COLOR = (255, 255, 255)
    BUTTON_BORDER_COLOR = (255, 255, 255)
    AFK_BUTTON_COLOR = (30, 144, 255)  # Mavi
    MULTIPLIER_BUTTON_COLOR = (50, 205, 50)  # Yeşil
    MONEY_COLOR = (255, 215, 0)  # Altın rengi
    STATS_COLOR = (200, 200, 200)  # Gri
    
    # Panel ayarları
    stats_panel_rect = pygame.Rect(10, 10, 250, 180)
    
    running = True
    while running:
        dt = clock.tick(60) / 1000.0  # Geçen süre (saniye)
        # Otomatik gelir eklemesi
        money += auto_income * dt

        screen.fill(BACKGROUND_COLOR)
        
        # İstatistik paneli çizimi
        pygame.draw.rect(screen, (40, 58, 44), stats_panel_rect, border_radius=5)
        pygame.draw.rect(screen, (60, 78, 64), stats_panel_rect, 2, border_radius=5)
        
        # AFK Gelir butonu çizimi
        afk_button_text = medium_font.render(f"AFK Income +0.5 (${int(afk_upgrade_cost)})", True, TEXT_COLOR)
        padding = 12
        afk_text_rect = afk_button_text.get_rect()
        button_width = afk_text_rect.width + 2 * padding
        button_height = afk_text_rect.height + 2 * padding
        afk_button_rect = pygame.Rect(0, 0, button_width, button_height)
        afk_button_rect.topright = (SCREEN_SIZE[0] - 20, 20)
        afk_text_rect.center = afk_button_rect.center
        
        # Buton arka planı ve kenarları
        pygame.draw.rect(screen, AFK_BUTTON_COLOR, afk_button_rect, border_radius=5)
        pygame.draw.rect(screen, BUTTON_BORDER_COLOR, afk_button_rect, 2, border_radius=5)
        screen.blit(afk_button_text, afk_text_rect)
        
        # Çarpan butonu çizimi
        multiplier_button_text = medium_font.render(f"Click Power x{multiplier+1} (${int(multiplier_upgrade_cost)})", True, TEXT_COLOR)
        multiplier_text_rect = multiplier_button_text.get_rect()
        button_width = multiplier_text_rect.width + 2 * padding
        button_height = multiplier_text_rect.height + 2 * padding
        multiplier_button_rect = pygame.Rect(0, 0, button_width, button_height)
        multiplier_button_rect.topright = (SCREEN_SIZE[0] - 20, afk_button_rect.bottom + 15)
        multiplier_text_rect.center = multiplier_button_rect.center
        
        # Buton arka planı ve kenarları
        pygame.draw.rect(screen, MULTIPLIER_BUTTON_COLOR, multiplier_button_rect, border_radius=5)
        pygame.draw.rect(screen, BUTTON_BORDER_COLOR, multiplier_button_rect, 2, border_radius=5)
        screen.blit(multiplier_button_text, multiplier_text_rect)
        
        # Ölçek faktörünü güncelle
        scale_factor += scale_direction * 0.0034  
        if scale_factor >= MAX_SCALE or scale_factor <= MIN_SCALE:
            scale_direction *= -1
        
        # Dönüş açısını güncelle
        rotation_angle += rotation_direction * 0.054
        if abs(rotation_angle) >= 5:
            rotation_direction *= -1
        
        # Resmi yeniden ölçekle ve döndür
        current_width = int(grass_img_original.get_width() * scale_factor)
        current_height = int(grass_img_original.get_height() * scale_factor)
        scaled_img = pygame.transform.scale(grass_img_original, (current_width, current_height))
        rotated_img = pygame.transform.rotate(scaled_img, rotation_angle)
        grass_rect = rotated_img.get_rect(center=grass_rect.center)
        
        # === İMLEÇ KONTROLÜ ===
        mouse_pos = pygame.mouse.get_pos()
        if afk_button_rect.collidepoint(mouse_pos) or multiplier_button_rect.collidepoint(mouse_pos) or grass_rect.collidepoint(mouse_pos):
            pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND)   # El işareti
        else:
            pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)  # Normal ok

        # Resmi ekrana çiz
        screen.blit(rotated_img, grass_rect.topleft)

        # Kullanıcı girişlerini kontrol et
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.MOUSEBUTTONDOWN:
                if afk_button_rect.collidepoint(event.pos):
                    pygame.mixer.Sound.set_volume(buy_effect, 0.0896705)
                    if money >= afk_upgrade_cost:
                        buy_effect.play()
                        money -= afk_upgrade_cost
                        auto_income += 0.5
                        afk_upgrade_cost *= 1.25
                elif multiplier_button_rect.collidepoint(event.pos):
                    pygame.mixer.Sound.set_volume(buy_effect, 0.0896705)
                    if money >= multiplier_upgrade_cost:
                        buy_effect.play()
                        money -= multiplier_upgrade_cost
                        multiplier += 1
                        multiplier_upgrade_cost *= 1.5
                elif grass_rect.collidepoint(event.pos):
                    pygame.mixer.Sound.set_volume(click_effect, 0.0896705)
                    click_effect.play()
                    money += 1 * multiplier
                    total_clicks += 1

        # Para değerini ve diğer bilgileri ekrana yazdır
        money_text = custom_font.render("$" + str(int(money)), True, MONEY_COLOR)
        money_label = small_font.render("Money:", True, TEXT_COLOR)
        
        income_value = small_font.render(str(round(auto_income, 1)) + " $/s", True, MONEY_COLOR)
        income_label = small_font.render("AFK Income:", True, TEXT_COLOR)
        
        multiplier_value = small_font.render("x" + str(multiplier), True, MULTIPLIER_BUTTON_COLOR)
        multiplier_label = small_font.render("Click Power:", True, TEXT_COLOR)
        
        clicks_value = small_font.render(str(total_clicks), True, STATS_COLOR)
        clicks_label = small_font.render("Total Clicks:", True, TEXT_COLOR)
        
        # İstatistik paneline bilgileri yerleştir
        screen.blit(money_label, (stats_panel_rect.x + 15, stats_panel_rect.y + 15))
        screen.blit(money_text, (stats_panel_rect.x + 15, stats_panel_rect.y + 40))
        
        screen.blit(income_label, (stats_panel_rect.x + 15, stats_panel_rect.y + 80))
        screen.blit(income_value, (stats_panel_rect.x + 130, stats_panel_rect.y + 80))
        
        screen.blit(multiplier_label, (stats_panel_rect.x + 15, stats_panel_rect.y + 110))
        screen.blit(multiplier_value, (stats_panel_rect.x + 130, stats_panel_rect.y + 110))
        
        screen.blit(clicks_label, (stats_panel_rect.x + 15, stats_panel_rect.y + 140))
        screen.blit(clicks_value, (stats_panel_rect.x + 130, stats_panel_rect.y + 140))

        pygame.display.flip()

    pygame.quit()
    sys.exit()
