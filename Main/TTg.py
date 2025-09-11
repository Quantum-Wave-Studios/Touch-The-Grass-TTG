import pygame
import os

# Define base directory paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
GRASS_IMG_PATH = os.path.join(BASE_DIR, "grass.png")
GRASS1_IMG_PATH = os.path.join(BASE_DIR, "grass1.png")
FONTS_DIR = os.path.join(os.path.dirname(BASE_DIR), "fonts")
CUSTOM_FONT_PATH = os.path.join(FONTS_DIR, "PixelifySans-Regular.ttf")

# Initialize pygame
pygame.init()
screen = pygame.display.set_mode((800, 600))
clock = pygame.time.Clock()

money = 0
multipier = 1

# Load images using organized paths
# Örnek olarak grass1 görüntüsünü kullanıyoruz
grass_img_original = pygame.image.load(GRASS1_IMG_PATH).convert_alpha()
# Ölçeklendirme örneği
original_width = grass_img_original.get_width()
original_height = grass_img_original.get_height()
grass_img_original = pygame.transform.scale(grass_img_original, (int(original_width / 2.4), int(original_height / 2.4)))

# Load custom font if needed
custom_font = pygame.font.Font(CUSTOM_FONT_PATH, 36)  # 36 yazı boyutu

# Başlangıç boyutu ve dönüş açısı
scale_factor = 1.0  # Ölçek faktörü (1.0 = orijinal boyut)
rotation_angle = 0  # Resmin başlangıç dönüş açısı
rotation_direction = 1  # Dönüş yönü (1: saat yönü, -1: ters yön)
# Ölçekleme yönü (1: büyüt, -1: küçült)
scale_direction = 1
# Ölçekleme limiti
max_scale = 1.2  # %120
min_scale = 0.9  # %90 (daha az küçültme)

grass_rect = grass_img_original.get_rect()
grass_rect.center = (400, 300)  # Ekranın ortası

running = True
while running:
    screen.fill((0, 0, 0))  # Ekranı temizle

    # Ölçek faktörünü güncelle
    scale_factor += scale_direction * 0.0034  # Daha yavaş büyüt/küçült (%1)

    # Ölçek sınırlarını kontrol et
    if scale_factor >= max_scale or scale_factor <= min_scale:
        scale_direction *= -1  # Yönü tersine çevir

    # Dönüş açısını güncelle
    rotation_angle += rotation_direction * 0.054  # Daha yavaş dönüş
    if abs(rotation_angle) >= 5:  # Maksimum sağa/sola dönüş açısı
        rotation_direction *= -1  # Dönüş yönünü tersine çevir

    # Yeni boyutlara göre resmi yeniden ölçekle ve döndür
    current_width = int(grass_img_original.get_width() * scale_factor)
    current_height = int(grass_img_original.get_height() * scale_factor)
    scaled_img = pygame.transform.scale(grass_img_original, (current_width, current_height))
    rotated_img = pygame.transform.rotate(scaled_img, rotation_angle)
    grass_rect = rotated_img.get_rect(center=grass_rect.center)

    screen.blit(rotated_img, grass_rect.topleft)


    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.MOUSEBUTTONDOWN:  # Fare tıklama olayı
            if grass_rect.collidepoint(event.pos):  # Tıklama resim üzerinde mi?
                money += 1 * multipier  # Para kazanma
                #print(money)

    # Her frame'in sonunda:
    money_text = custom_font.render("Money: " + str(money), True, (255, 255, 255))
    screen.blit(money_text, (10, 10))

    clock.tick(60)
    pygame.display.flip(),
    

pygame.quit()
exit()
