import pygame

pygame.init()
screen = pygame.display.set_mode((800, 600))

money = 0
multipier = 1


grass_img = pygame.image.load("grass1.png").convert_alpha()
grass_img = pygame.transform.scale(grass_img, (grass_img.get_width()//3, grass_img.get_height()//3))  # Resmi ölçeklendir

grass_rect = grass_img.get_rect()
grass_rect.center = (400, 300)  # Ekranın ortası



clock = pygame.time.Clock()



running = True
while running:
    screen.fill((0, 0, 0))  # Ekranı temizle

    screen.blit(grass_img, grass_rect.topleft)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.MOUSEBUTTONDOWN:  # Fare tıklama olayı
            if grass_rect.collidepoint(event.pos):  # Tıklama resim üzerinde mi?
                money += 1 * multipier  # Para kazanma
                print(money)

    clock.tick(60)
    pygame.display.flip()

pygame.quit()
exit()
pygame.quit()
