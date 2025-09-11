import pygame
import sys
from .settings import SCREEN_SIZE, CENTER, MIN_SCALE, MAX_SCALE


def run_loop(screen, clock, assets):
    """Ana oyun döngüsü. Ekranda animasyon ve para sayacını günceller."""

    money = 0
    multipier = 1
    
    # Assets dictionary'den gerekli görselleri ve fontu al
    grass_img_original = assets['grass_img']
    custom_font = assets['custom_font']
    
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
        # Ekranı temizle (siyah arka plan)
        screen.fill((0, 0, 0))
        
        # Ölçek faktörünü güncelle
        scale_factor += scale_direction * 0.0034  # Kademeli artış/azalış
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
        
        # Resmi ekrana çiz
        screen.blit(rotated_img, grass_rect.topleft)

        # Kullanıcı girişlerini kontrol et
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.MOUSEBUTTONDOWN:  # Fare tıklaması
                if grass_rect.collidepoint(event.pos):  # Tıklama resim üzerindeyse
                    money += 1 * multipier

        # Para değerini ekrana yazdır
        money_text = custom_font.render("Money: " + str(money), True, (255, 255, 255))
        screen.blit(money_text, (10, 10))
        
        # Ekranı güncelle
        clock.tick(60)
        pygame.display.flip()

    pygame.quit()
    sys.exit()
