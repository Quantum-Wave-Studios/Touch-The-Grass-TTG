import pygame
import sys
import json
import os
from .settings import SCREEN_SIZE, CENTER, MIN_SCALE, MAX_SCALE
from .paths import CUSTOM_FONT_PATH
from .assets import resource_path


income = 0
def run_loop(screen, clock, assets):
    """Ana oyun döngüsü. Ekranda animasyon ve para sayacını günceller..."""

    # Oyun verilerini yükleme
    game_data = load_game_data()
    money = game_data.get('money', 0)
    multiplier = game_data.get('multiplier', 1)
    auto_income = game_data.get('auto_income', 0.0)
    total_clicks = game_data.get('total_clicks', 0)
    afk_upgrade_cost = game_data.get('afk_upgrade_cost', 15)
    multiplier_upgrade_cost = game_data.get('multiplier_upgrade_cost', 10)
    highest_money = game_data.get('highest_money', 0)
    current_grass_index = game_data.get('current_grass_index', 0)

    # Assets dictionary'den gerekli görselleri ve fontu al
    grass_img_original = assets['grass_img']
    custom_font = assets['custom_font']
    font_path = resource_path(CUSTOM_FONT_PATH)
    small_font = pygame.font.Font(font_path, 18)  # Daha küçük fontlar kullan
    extra_small_font = pygame.font.Font(font_path, 14)  # Extra küçük font
    medium_font = pygame.font.Font(font_path, 22)  # Orta boyut

    # Farklı çim görselleri
    grass_images = [grass_img_original]  # İlk görsel varsayılan
    grass_costs = [0, 1000, 5000, 20000]  # Farklı çim görsellerinin fiyatları
    grass_names = ["Normal Grass", "Golden Grass", "Rainbow Grass", "Diamond Grass"]
    
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
                    min(255, int(green_value * 0.3))   # Mavi bileşeni azalt
                )
                golden_grass.set_at((x, y), new_color)
    grass_images.append(golden_grass)
    
    # Gökkuşağı ve Elmas çimler için
    for i in range(2, 4):
        img = grass_img_original.copy()
        if i == 2:  # Gökkuşağı çim (turkuaz tonu)
            img = colorize(img, (64, 224, 208))
        else:  # Elmas çim (açık mavi tonu)
            img = colorize(img, (135, 206, 250))
        grass_images.append(img)

    # Aktif çim görselini ayarla
    if current_grass_index < len(grass_images):
        active_grass_img = grass_images[current_grass_index]
    else:
        active_grass_img = grass_images[0]
        current_grass_index = 0

    # sesleri yükle ve çal
    #pygame.mixer.music.load('Main\assets\sounds\back.mp3')
    #pygame.mixer.music.play(-1)  # Sonsuz döngüde çal
    pygame.mixer.music.set_volume(0.02896705)  # Ses seviyesini ayarla (0.0 - 1.0)
    click_effect = pygame.mixer.Sound(resource_path("assets/sounds/click.mp3"))
    buy_effect = pygame.mixer.Sound(resource_path("assets/sounds/buy.mp3"))

    # Başlangıç ayarları
    scale_factor = 1.0          # Orijinal boyutta başla
    rotation_angle = 0          # Başlangıç dönüş açısı
    rotation_direction = 1      # Dönüş yönü (1: saat yönü, -1: ters yön)
    scale_direction = 1         # Ölçek yönü (1: büyüt, -1: küçült)

    # Resmin konumunu belirle
    grass_rect = active_grass_img.get_rect()
    grass_rect.center = CENTER

    # Buton ayarları
    afk_button_rect = pygame.Rect(0, 0, 0, 0)  # Başlangıçta boş, sonra güncellenecek
    multiplier_button_rect = pygame.Rect(0, 0, 0, 0)  # Başlangıçta boş, sonra güncellenecek
    save_button_rect = pygame.Rect(0, 0, 0, 0)  # Başlangıçta boş, sonra güncellenecek
    stats_button_rect = pygame.Rect(0, 0, 0, 0)  # Başlangıçta boş, sonra güncellenecek
    shop_button_rect = pygame.Rect(0, 0, 0, 0)  # Başlangıçta boş, sonra güncellenecek
    
    # Renk tanımları - Pixel art tarzı için daha canlı renkler
    BACKGROUND_COLOR = (20, 38, 24)
    TEXT_COLOR = (240, 240, 240)  # Daha parlak beyaz
    BUTTON_BORDER_COLOR = (255, 255, 255)
    AFK_BUTTON_COLOR = (30, 144, 255)  # Mavi
    MULTIPLIER_BUTTON_COLOR = (50, 205, 50)  # Yeşil
    SAVE_BUTTON_COLOR = (255, 165, 0)  # Turuncu
    STATS_BUTTON_COLOR = (138, 43, 226)  # Mor
    SHOP_BUTTON_COLOR = (255, 105, 180)  # Pembe
    MONEY_COLOR = (255, 215, 0)  # Altın rengi
    STATS_COLOR = (200, 200, 200)  # Gri
    
    # Panel ayarları - Daha geniş panel
    stats_panel_rect = pygame.Rect(10, 10, 280, 200)

    
    # Wipe Save butonu ayarları
    wipe_button_rect = pygame.Rect(0, 0, 80, 30)  # Küçük buton
    wipe_button_rect.bottomright = (SCREEN_SIZE[0] - 10, SCREEN_SIZE[1] - 10)  # Sağ alt köşe
    
    # İstatistik ekranı ve mağaza ekranı görünürlüğü
    show_stats = False
    show_shop = False
    
    running = True
    while running:
        dt = clock.tick(60) / 1000.0  # Geçen süre (saniye)
        # Otomatik gelir eklemesi
        money += auto_income * dt
        
        # En yüksek para miktarını güncelle
        if money > highest_money:
            highest_money = money

        screen.fill(BACKGROUND_COLOR)
        
        # İstatistik paneli çizimi - Pixel art tarzı için daha belirgin kenarlar
        pygame.draw.rect(screen, (40, 58, 44), stats_panel_rect, border_radius=3)
        pygame.draw.rect(screen, (80, 98, 84), stats_panel_rect, 2, border_radius=3)
        
        # AFK Gelir butonu çizimi
        afk_button_text = medium_font.render(f"AFK Income +0.5 (${int(afk_upgrade_cost)})", True, TEXT_COLOR)
        padding = 10  # Daha az padding
        afk_text_rect = afk_button_text.get_rect()
        button_width = afk_text_rect.width + 2 * padding
        button_height = afk_text_rect.height + 2 * padding
        afk_button_rect = pygame.Rect(0, 0, button_width, button_height)
        afk_button_rect.topright = (SCREEN_SIZE[0] - 20, 20)
        afk_text_rect.center = afk_button_rect.center
        
        # Buton arka planı ve kenarları - Pixel art tarzı için daha keskin kenarlar
        pygame.draw.rect(screen, AFK_BUTTON_COLOR, afk_button_rect, border_radius=3)
        pygame.draw.rect(screen, BUTTON_BORDER_COLOR, afk_button_rect, 2, border_radius=3)
        screen.blit(afk_button_text, afk_text_rect)
        
        # Çarpan butonu çizimi
        multiplier_button_text = medium_font.render(f"Click Power x{multiplier+1} (${int(multiplier_upgrade_cost)})", True, TEXT_COLOR)
        multiplier_text_rect = multiplier_button_text.get_rect()
        button_width = multiplier_text_rect.width + 2 * padding
        button_height = multiplier_text_rect.height + 2 * padding
        multiplier_button_rect = pygame.Rect(0, 0, button_width, button_height)
        multiplier_button_rect.topright = (SCREEN_SIZE[0] - 20, afk_button_rect.bottom + 10)  # Daha az boşluk
        multiplier_text_rect.center = multiplier_button_rect.center
        
        # Buton arka planı ve kenarları
        pygame.draw.rect(screen, MULTIPLIER_BUTTON_COLOR, multiplier_button_rect, border_radius=3)
        pygame.draw.rect(screen, BUTTON_BORDER_COLOR, multiplier_button_rect, 2, border_radius=3)
        screen.blit(multiplier_button_text, multiplier_text_rect)
        
        # Kaydet butonu çizimi
        save_button_text = medium_font.render("Save Game", True, TEXT_COLOR)
        save_text_rect = save_button_text.get_rect()
        button_width = save_text_rect.width + 2 * padding
        button_height = save_text_rect.height + 2 * padding
        save_button_rect = pygame.Rect(0, 0, button_width, button_height)
        save_button_rect.topright = (SCREEN_SIZE[0] - 20, multiplier_button_rect.bottom + 10)  # Daha az boşluk
        save_text_rect.center = save_button_rect.center
        
        # Buton arka planı ve kenarları
        pygame.draw.rect(screen, SAVE_BUTTON_COLOR, save_button_rect, border_radius=3)
        pygame.draw.rect(screen, BUTTON_BORDER_COLOR, save_button_rect, 2, border_radius=3)
        screen.blit(save_button_text, save_text_rect)
        
        # İstatistik butonu çizimi
        stats_button_text = medium_font.render("Statistics", True, TEXT_COLOR)
        stats_text_rect = stats_button_text.get_rect()
        button_width = stats_text_rect.width + 2 * padding
        button_height = stats_text_rect.height + 2 * padding
        stats_button_rect = pygame.Rect(0, 0, button_width, button_height)
        stats_button_rect.topright = (SCREEN_SIZE[0] - 20, save_button_rect.bottom + 10)  # Daha az boşluk
        stats_text_rect.center = stats_button_rect.center
        
        # Buton arka planı ve kenarları
        pygame.draw.rect(screen, STATS_BUTTON_COLOR, stats_button_rect, border_radius=3)
        pygame.draw.rect(screen, BUTTON_BORDER_COLOR, stats_button_rect, 2, border_radius=3)
        screen.blit(stats_button_text, stats_text_rect)
        
        # Mağaza butonu çizimi
        shop_button_text = medium_font.render("Grass Shop", True, TEXT_COLOR)
        shop_text_rect = shop_button_text.get_rect()
        button_width = shop_text_rect.width + 2 * padding
        button_height = shop_text_rect.height + 2 * padding
        shop_button_rect = pygame.Rect(0, 0, button_width, button_height)
        shop_button_rect.topright = (SCREEN_SIZE[0] - 20, stats_button_rect.bottom + 10)  # Daha az boşluk
        shop_text_rect.center = shop_button_rect.center
        
        # Buton arka planı ve kenarları
        pygame.draw.rect(screen, SHOP_BUTTON_COLOR, shop_button_rect, border_radius=3)
        pygame.draw.rect(screen, BUTTON_BORDER_COLOR, shop_button_rect, 2, border_radius=3)
        screen.blit(shop_button_text, shop_text_rect)
        
        # Wipe Save butonu çizimi
        wipe_button_text = extra_small_font.render("Wipe Save", True, TEXT_COLOR)
        wipe_text_rect = wipe_button_text.get_rect()
        wipe_text_rect.center = wipe_button_rect.center

        # Wipe Save buton arka planı ve kenarları
        pygame.draw.rect(screen, (200, 0, 0), wipe_button_rect, border_radius=3)  # Kırmızı renk
        pygame.draw.rect(screen, BUTTON_BORDER_COLOR, wipe_button_rect, 2, border_radius=3)
        screen.blit(wipe_button_text, wipe_text_rect)
        
        # Ölçek faktörünü güncelle
        scale_factor += scale_direction * 0.0034  
        if scale_factor >= MAX_SCALE or scale_factor <= MIN_SCALE:
            scale_direction *= -1
        
        # Dönüş açısını güncelle
        rotation_angle += rotation_direction * 0.054
        if abs(rotation_angle) >= 5:
            rotation_direction *= -1
        
        # Resmi yeniden ölçekle ve döndür
        current_width = int(active_grass_img.get_width() * scale_factor)
        current_height = int(active_grass_img.get_height() * scale_factor)
        scaled_img = pygame.transform.scale(active_grass_img, (current_width, current_height))
        rotated_img = pygame.transform.rotate(scaled_img, rotation_angle)
        grass_rect = rotated_img.get_rect(center=grass_rect.center)
        
        # === İMLEÇ KONTROLÜ ===
        mouse_pos = pygame.mouse.get_pos()
        if (afk_button_rect.collidepoint(mouse_pos) or 
            multiplier_button_rect.collidepoint(mouse_pos) or 
            save_button_rect.collidepoint(mouse_pos) or 
            stats_button_rect.collidepoint(mouse_pos) or 
            shop_button_rect.collidepoint(mouse_pos) or 
            wipe_button_rect.collidepoint(mouse_pos) or 
            grass_rect.collidepoint(mouse_pos)):
            pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND)   # El işareti
        else:
            pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)  # Normal ok

        # Resmi ekrana çiz
        screen.blit(rotated_img, grass_rect.topleft)

        # Kullanıcı girişlerini kontrol et
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                # Çıkış yapmadan önce oyunu kaydet
                save_game_data({
                    'money': money,
                    'multiplier': multiplier,
                    'auto_income': auto_income,
                    'total_clicks': total_clicks,
                    'afk_upgrade_cost': afk_upgrade_cost,
                    'multiplier_upgrade_cost': multiplier_upgrade_cost,
                    'highest_money': highest_money,
                    'current_grass_index': current_grass_index
                })
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
                elif save_button_rect.collidepoint(event.pos):
                    pygame.mixer.Sound.set_volume(click_effect, 0.0896705)
                    click_effect.play()
                    # Oyun verilerini kaydet
                    save_game_data({
                        'money': money,
                        'multiplier': multiplier,
                        'auto_income': auto_income,
                        'total_clicks': total_clicks,
                        'afk_upgrade_cost': afk_upgrade_cost,
                        'multiplier_upgrade_cost': multiplier_upgrade_cost,
                        'highest_money': highest_money,
                        'current_grass_index': current_grass_index
                    })
                    # Kaydetme onayı göster
                    save_text = small_font.render("Game Saved!", True, (255, 255, 255))
                    screen.blit(save_text, (SCREEN_SIZE[0] // 2 - save_text.get_width() // 2, 10))
                    pygame.display.flip()
                    pygame.time.wait(500)  # 0.5 saniye bekle
                elif stats_button_rect.collidepoint(event.pos):
                    pygame.mixer.Sound.set_volume(click_effect, 0.0896705)
                    click_effect.play()
                    show_stats = not show_stats  # İstatistik ekranını aç/kapat
                    show_shop = False  # Mağaza ekranını kapat
                elif shop_button_rect.collidepoint(event.pos):
                    pygame.mixer.Sound.set_volume(click_effect, 0.0896705)
                    click_effect.play()
                    show_shop = not show_shop  # Mağaza ekranını aç/kapat
                    show_stats = False  # İstatistik ekranını kapat
                elif grass_rect.collidepoint(event.pos):
                    pygame.mixer.Sound.set_volume(click_effect, 0.0896705)
                    click_effect.play()
                    money += 1 * multiplier
                    total_clicks += 1
                elif wipe_button_rect.collidepoint(event.pos):
                    pygame.mixer.Sound.set_volume(click_effect, 0.0896705)
                    click_effect.play()
                    if os.path.exists(os.path.join(os.getenv('LOCALAPPDATA'), "TouchTheGrass", "save_data.json")):
                        os.remove(os.path.join(os.getenv('LOCALAPPDATA'), "TouchTheGrass", "save_data.json"))
                        # Oyunu sıfırla
                        money = 0
                        multiplier = 1
                        auto_income = 0.0
                        total_clicks = 0
                        afk_upgrade_cost = 15
                        multiplier_upgrade_cost = 10
                        highest_money = 0
                        current_grass_index = 0
                        active_grass_img = grass_images[current_grass_index]

        # Para değerini ve diğer bilgileri ekrana yazdır - Yazıların birbirinin içine girmesini önle
        money_text = custom_font.render("$" + str(int(money)), True, MONEY_COLOR)
        money_label = small_font.render("Money:", True, TEXT_COLOR)
        
        income_value = small_font.render(str(round(auto_income, 1)) + " $/s", True, MONEY_COLOR)
        income_label = small_font.render("AFK Income:", True, TEXT_COLOR)
        
        multiplier_value = small_font.render("x" + str(multiplier), True, MULTIPLIER_BUTTON_COLOR)
        multiplier_label = small_font.render("Click Power:", True, TEXT_COLOR)
        
        clicks_value = small_font.render(str(total_clicks), True, STATS_COLOR)
        clicks_label = small_font.render("Total Clicks:", True, TEXT_COLOR)
        
        # İstatistik paneline bilgileri yerleştir - Daha iyi hizalama
        screen.blit(money_label, (stats_panel_rect.x + 15, stats_panel_rect.y + 15))
        screen.blit(money_text, (stats_panel_rect.x + 15, stats_panel_rect.y + 40))
        
        screen.blit(income_label, (stats_panel_rect.x + 15, stats_panel_rect.y + 80))
        screen.blit(income_value, (stats_panel_rect.x + 150, stats_panel_rect.y + 80))  # Daha fazla boşluk
        
        screen.blit(multiplier_label, (stats_panel_rect.x + 15, stats_panel_rect.y + 110))
        screen.blit(multiplier_value, (stats_panel_rect.x + 150, stats_panel_rect.y + 110))  # Daha fazla boşluk
        
        screen.blit(clicks_label, (stats_panel_rect.x + 15, stats_panel_rect.y + 140))
        screen.blit(clicks_value, (stats_panel_rect.x + 150, stats_panel_rect.y + 140))  # Daha fazla boşluk

        # İstatistik ekranını göster - Pixel art tarzı için daha keskin kenarlar
        if show_stats:
            stats_surface = pygame.Surface((500, 400))
            stats_surface.fill((30, 48, 34))
            stats_rect = stats_surface.get_rect(center=(SCREEN_SIZE[0] // 2, SCREEN_SIZE[1] // 2))
            
            # İstatistik başlığı
            title_text = custom_font.render("Game Statistics", True, TEXT_COLOR)
            stats_surface.blit(title_text, (stats_surface.get_width() // 2 - title_text.get_width() // 2, 20))
            
            # İstatistik bilgileri - Daha iyi hizalama
            y_pos = 80
            line_height = 40
            
            stats_list = [
                ("Total Clicks", str(total_clicks)),
                ("Highest Money", "$" + str(int(highest_money))),
                ("Current Money", "$" + str(int(money))),
                ("Click Power", "x" + str(multiplier)),
                ("AFK Income", str(round(auto_income, 1)) + " $/s"),
                ("AFK Upgrade Cost", "$" + str(int(afk_upgrade_cost))),
                ("Multiplier Upgrade Cost", "$" + str(int(multiplier_upgrade_cost)))
            ]
            
            for label, value in stats_list:
                label_text = small_font.render(label + ":", True, TEXT_COLOR)
                value_text = small_font.render(value, True, MONEY_COLOR)
                stats_surface.blit(label_text, (50, y_pos))
                stats_surface.blit(value_text, (300, y_pos))
                y_pos += line_height
            
            # Kapat butonu - Pixel art tarzı için daha keskin kenarlar
            close_text = small_font.render("Close", True, TEXT_COLOR)
            close_rect = pygame.Rect(stats_surface.get_width() // 2 - 50, stats_surface.get_height() - 50, 100, 40)
            pygame.draw.rect(stats_surface, (200, 50, 50), close_rect, border_radius=3)
            pygame.draw.rect(stats_surface, BUTTON_BORDER_COLOR, close_rect, 2, border_radius=3)
            stats_surface.blit(close_text, (close_rect.centerx - close_text.get_width() // 2, close_rect.centery - close_text.get_height() // 2))
            
            # İstatistik ekranını ana ekrana çiz
            screen.blit(stats_surface, stats_rect.topleft)
            
            # Kapat butonuna tıklama kontrolü
            if event.type == pygame.MOUSEBUTTONDOWN:
                if stats_rect.collidepoint(event.pos):
                    # Kapat butonunun konumunu ana ekrana göre ayarla
                    adjusted_close_rect = close_rect.copy()
                    adjusted_close_rect.x += stats_rect.x
                    adjusted_close_rect.y += stats_rect.y
                    
                    if adjusted_close_rect.collidepoint(event.pos):
                        show_stats = False
                        pygame.mixer.Sound.set_volume(click_effect, 0.0896705)
                        click_effect.play()
        
        # Mağaza ekranını göster - Pixel art tarzı için daha keskin kenarlar
        if show_shop:
            shop_surface = pygame.Surface((500, 400))
            shop_surface.fill((30, 48, 34))
            shop_rect = shop_surface.get_rect(center=(SCREEN_SIZE[0] // 2, SCREEN_SIZE[1] // 2))
            
            # Mağaza başlığı
            title_text = custom_font.render("Grass Shop", True, TEXT_COLOR)
            shop_surface.blit(title_text, (shop_surface.get_width() // 2 - title_text.get_width() // 2, 20))
            
            # Çim seçenekleri - Daha iyi hizalama
            y_pos = 80
            item_height = 70
            
            for i, (name, cost) in enumerate(zip(grass_names, grass_costs)):
                # Çim öğesi arka planı - Pixel art tarzı için daha keskin kenarlar
                item_rect = pygame.Rect(50, y_pos, 400, item_height)
                if current_grass_index == i:
                    # Aktif çim için farklı renk
                    pygame.draw.rect(shop_surface, (50, 100, 50), item_rect, border_radius=3)
                else:
                    pygame.draw.rect(shop_surface, (40, 70, 40), item_rect, border_radius=3)
                pygame.draw.rect(shop_surface, (60, 90, 60), item_rect, 2, border_radius=3)
                
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
                button_rect = pygame.Rect(item_rect.right - 100, item_rect.centery - 20, 80, 40)
                pygame.draw.rect(shop_surface, button_color, button_rect, border_radius=3)
                pygame.draw.rect(shop_surface, BUTTON_BORDER_COLOR, button_rect, 2, border_radius=3)
                shop_surface.blit(button_text_render, (button_rect.centerx - button_text_render.get_width() // 2, button_rect.centery - button_text_render.get_height() // 2))
                
                # Buton tıklama kontrolü
                if event.type == pygame.MOUSEBUTTONDOWN and shop_rect.collidepoint(event.pos):
                    # Butonun konumunu ana ekrana göre ayarla
                    adjusted_button_rect = button_rect.copy()
                    adjusted_button_rect.x += shop_rect.x
                    adjusted_button_rect.y += shop_rect.y
                    
                    if adjusted_button_rect.collidepoint(event.pos):
                        if current_grass_index != i and current_grass_index >= i:
                            # Zaten sahip olunan çimi seç
                            current_grass_index = i
                            active_grass_img = grass_images[current_grass_index]
                            pygame.mixer.Sound.set_volume(click_effect, 0.0896705)
                            click_effect.play()
                        elif i > 0 and current_grass_index < i and money >= cost:
                            # Yeni çim satın al
                            money -= cost
                            current_grass_index = i
                            active_grass_img = grass_images[current_grass_index]
                            pygame.mixer.Sound.set_volume(buy_effect, 0.0896705)
                            buy_effect.play()
                
                y_pos += item_height + 10
            
            # Kapat butonu - Pixel art tarzı için daha keskin kenarlar
            close_text = small_font.render("Close", True, TEXT_COLOR)
            close_rect = pygame.Rect(shop_surface.get_width() // 2 - 50, shop_surface.get_height() - 50, 100, 40)
            pygame.draw.rect(shop_surface, (200, 50, 50), close_rect, border_radius=3)
            pygame.draw.rect(shop_surface, BUTTON_BORDER_COLOR, close_rect, 2, border_radius=3)
            shop_surface.blit(close_text, (close_rect.centerx - close_text.get_width() // 2, close_rect.centery - close_text.get_height() // 2))
            
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
                        pygame.mixer.Sound.set_volume(click_effect, 0.0896705)
                        click_effect.play()

        pygame.display.flip()

    pygame.quit()
    sys.exit()


def save_game_data(data):
    """Oyun verilerini JSON formatında kaydeder."""
    try:
        # Windows'da AppData\Local altında bir klasör oluştur
        app_data = os.path.join(os.getenv('LOCALAPPDATA'), "TouchTheGrass")
        # Klasör yoksa oluştur
        if not os.path.exists(app_data):
            os.makedirs(app_data)
        save_path = os.path.join(app_data, "save_data.json")
        with open(save_path, 'w') as f:
            json.dump(data, f)
        return True
    except Exception as e:
        print(f"Kaydetme hatası: {e}")
        return False


def load_game_data():
    """Kaydedilmiş oyun verilerini yükler, yoksa boş bir sözlük döndürür."""
    try:
        app_data = os.path.join(os.getenv('LOCALAPPDATA'), "TouchTheGrass")
        save_path = os.path.join(app_data, "save_data.json")
        if os.path.exists(save_path):
            with open(save_path, 'r') as f:
                return json.load(f)
    except Exception as e:
        print(f"Yükleme hatası: {e}")
    return {}  # Varsayılan boş veri


def colorize(image, color):
    """Bir görselin rengini değiştirir."""
    colorized = image.copy()
    colorized.fill(color, special_flags=pygame.BLEND_RGBA_MULT)
    return colorized
