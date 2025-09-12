import pygame
import sys
from .settings import SCREEN_SIZE, CENTER, MIN_SCALE, MAX_SCALE
import os

income = 0
def run_loop(screen, clock, assets):
    """Ana oyun döngüsü. Ekranda animasyon ve para sayacını günceller."""

    money = 0
    multipier = 1

    # Assets dictionary'den gerekli görselleri ve fontu al
    grass_img_original = assets['grass_img']
    custom_font = assets['custom_font']

    # Buton ayarları (sağ üst köşe)
    button_rect = pygame.Rect(SCREEN_SIZE[0] - 220, 20, 200, 50)

    # sesleri yükle ve çal
    pygame.mixer.music.load('Main/assets/sounds/back.mp3')
    pygame.mixer.music.play(-1)  # Sonsuz döngüde çal
    pygame.mixer.music.set_volume(0.02896705)  # Ses seviyesini ayarla (0.0 - 1.0)
    click_effect = pygame.mixer.Sound("Main/assets/sounds/click.mp3")
    buy_effect = pygame.mixer.Sound("Main/assets/sounds/buy.mp3")


    # AFK Income upgrade bilgileri
    upgrade_cost = 15        # Başlangıç fiyatı
    auto_income = 0.0        # Otomatik gelir (saniyede artan miktar)

    # Başlangıç ayarları
    scale_factor = 1.0          # Orijinal boyutta başla
    rotation_angle = 0          # Başlangıç dönüş açısı
    rotation_direction = 1      # Dönüş yönü (1: saat yönü, -1: ters yön)
    scale_direction = 1         # Ölçek yönü (1: büyüt, -1: küçült)

    # Resmin konumunu belirle
    grass_rect = grass_img_original.get_rect()
    grass_rect.center = CENTER

    running = True
    while running:
        dt = clock.tick(60) / 1000.0  # Geçen süre (saniye)
        # Otomatik gelir eklemesi
        money += auto_income * dt

        screen.fill((20, 38, 24))
        
        # Buton çizimi: pixel art stili, metin boyutuna göre dinamik boyutlandırma
        button_text = custom_font.render(f"AFK Money (${int(upgrade_cost)})", False, (255, 255, 255))
        padding = 10
        text_rect = button_text.get_rect()
        button_rect = pygame.Rect(0, 0, text_rect.width + 2 * padding, text_rect.height + 2 * padding)
        button_rect.topright = (SCREEN_SIZE[0] - 20, 20)
        text_rect.center = button_rect.center
        pygame.draw.rect(screen, (30, 144, 255), button_rect, border_radius=0)
        pygame.draw.rect(screen, (255, 255, 255), button_rect, 2, border_radius=0)
        screen.blit(button_text, text_rect)
        
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
        # === İMLEÇ KONTROLÜ ===
        mouse_pos = pygame.mouse.get_pos()
        if button_rect.collidepoint(mouse_pos) or grass_rect.collidepoint(mouse_pos):
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
                if button_rect.collidepoint(event.pos):
                    pygame.mixer.Sound.set_volume(buy_effect, 0.0896705)
                    if money >= upgrade_cost:
                        buy_effect.play()
                        money -= upgrade_cost
                        auto_income += 0.5
                        upgrade_cost *= 1.25
                elif grass_rect.collidepoint(event.pos):
                    pygame.mixer.Sound.set_volume(click_effect, 0.0896705)
                    click_effect.play()
                    money += 1 * multipier

        # Para değerini ekrana yazdır
        money_text = custom_font.render("Money: " + str(int(money)), True, (255, 255, 255))
        income_text = custom_font.render("AFK Income: " + str(round(auto_income, 1)) + " $/s", True, (255, 255, 255))
        screen.blit(income_text, (10, 50))
        screen.blit(money_text, (10, 10))

        pygame.display.flip()

    pygame.quit()
    sys.exit()
