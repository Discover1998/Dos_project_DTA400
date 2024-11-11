import simpy, random, pygame
import matplotlib.pyplot as plt

# Simulation Parameters
REQUEST_PROCESSING_TIME = 1
NORMAL_REQUEST_RATE = 2
DOS_REQUEST_RATE = 0.05
SERVER_CAPACITY = 10
SIMULATION_TIME = 300
DOS_ATTACK_START = 150

# Tracking Server Metrics
cpu_load_over_time = []
dropped_packets_over_time = []

# Visualization Setup
SCREEN_WIDTH, SCREEN_HEIGHT = 1200, 800
FPS = 60
WHITE, GREEN, RED, BLUE, YELLOW, BLACK, GRAY = (255, 255, 255), (0, 255, 0), (255, 0, 0), (0, 0, 255), (255, 255, 0), (0, 0, 0), (128, 128, 128)

class Server:
    def __init__(self, env, capacity):
        self.env = env
        self.capacity = capacity
        self.queue = simpy.Resource(env, capacity)
        self.cpu_load = 0
        self.dropped_packets = 0

    def handle_request(self, request_type, sprite):
        with self.queue.request() as req:
            if len(self.queue.users) >= self.capacity:
                self.dropped_packets += 1
                if request_type == 'normal':
                    sprite.icon_type = 'dropped'
                return
            yield req
            yield self.env.timeout(REQUEST_PROCESSING_TIME)
            self.cpu_load = min(100, (len(self.queue.users) / self.capacity) * 100)

    def get_stats(self):
        return self.cpu_load, self.dropped_packets

class ClientSprite(pygame.sprite.Sprite):
    def __init__(self, x, y, icon_type, server):
        super().__init__()
        self.icon_type = icon_type
        self.server = server
        self.rect = pygame.Rect(x, y, 40, 40)

    def update(self):
        target_x, target_y = SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2
        self.rect.x += (target_x - self.rect.x) * 0.02
        self.rect.y += (target_y - self.rect.y) * 0.02

    def draw(self, screen):
        if self.icon_type == 'user':
            pygame.draw.circle(screen, BLUE, self.rect.center, 12)
        elif self.icon_type == 'attacker':
            pygame.draw.rect(screen, YELLOW, self.rect) 
            pygame.draw.rect(screen, BLACK, self.rect, 1)
        elif self.icon_type == 'dropped':
            pygame.draw.line(screen, RED, self.rect.topleft, self.rect.bottomright, 5)
            pygame.draw.line(screen, RED, self.rect.topright, self.rect.bottomleft, 5)

class ThreatActor:
    def __init__(self):
        self.x = SCREEN_WIDTH - 75
        self.y = SCREEN_HEIGHT // 2 - 40

    def draw(self, screen, font):
        pygame.draw.polygon(screen, BLACK, [(self.x - 30, self.y), (self.x + 30, self.y), (self.x, self.y - 20)])
        pygame.draw.circle(screen, BLACK, (self.x, self.y + 20), 20)
        pygame.draw.polygon(screen, BLACK, [(self.x - 30, self.y + 40), (self.x + 30, self.y + 40), (self.x + 20, self.y + 80), (self.x - 20, self.y + 80)], 3)
        pygame.draw.rect(screen, BLACK, (self.x - 5, self.y + 40, 10, 20))
        pygame.draw.polygon(screen, BLACK, [(self.x - 10, self.y + 60), (self.x + 10, self.y + 60), (self.x, self.y + 80)])
        screen.blit(font.render('Hacker', True, BLACK), (self.x - 40, self.y + 85))

def draw_server_icon(screen, rect, color):
    pygame.draw.ellipse(screen, color, pygame.Rect(rect.x, rect.y, rect.width, rect.height // 4))
    pygame.draw.rect(screen, color, pygame.Rect(rect.x, rect.y + rect.height // 8, rect.width, rect.height * 3 // 4))
    pygame.draw.ellipse(screen, color, pygame.Rect(rect.x, rect.y + (rect.height * 3 // 4), rect.width, rect.height // 4))
    pygame.draw.ellipse(screen, BLACK, pygame.Rect(rect.x, rect.y, rect.width, rect.height // 4), 2)
    pygame.draw.ellipse(screen, BLACK, pygame.Rect(rect.x, rect.y + (rect.height * 3 // 4), rect.width, rect.height // 4), 2)
    pygame.draw.line(screen, BLACK, (rect.x, rect.y + rect.height // 8), (rect.x, rect.y + rect.height * 7 // 8), 2)
    pygame.draw.line(screen, BLACK, (rect.right, rect.y + rect.height // 8), (rect.right, rect.y + rect.height * 7 // 8), 2)

def normal_client(env, server, all_sprites):
    while True:
        yield env.timeout(random.expovariate(1.0 / NORMAL_REQUEST_RATE))
        client = ClientSprite(random.randint(0, SCREEN_WIDTH), random.randint(0, SCREEN_HEIGHT), 'user', server)
        all_sprites.add(client)
        env.process(server.handle_request('normal', client))

def dos_attacker(env, server, all_sprites):
    while True:
        yield env.timeout(DOS_REQUEST_RATE)
        attacker = ClientSprite(SCREEN_WIDTH - 85, SCREEN_HEIGHT // 2, 'attacker', server)
        all_sprites.add(attacker)
        env.process(server.handle_request('attack', attacker))

def monitor_server(env, server):
    while True:
        cpu_load, dropped_packets = server.get_stats()
        cpu_load_over_time.append((env.now, cpu_load))
        dropped_packets_over_time.append((env.now, dropped_packets))
        yield env.timeout(1)

def pygame_visualization(server, env):
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    clock = pygame.time.Clock()
    
    font = pygame.font.SysFont('Times New Roman', 28)
    server_status_font = pygame.font.SysFont('Times New Roman', 30, bold=True)
    server_sprite = pygame.Rect(SCREEN_WIDTH // 2 - 50, SCREEN_HEIGHT // 2 - 50, 100, 150)
    all_sprites = pygame.sprite.Group()
    threat_actor = ThreatActor()

    for _ in range(3):
        env.process(normal_client(env, server, all_sprites))

    running, attack_started = True, False
    while running and env.now < SIMULATION_TIME:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        all_sprites.update()
        screen.fill(WHITE)
        for sprite in all_sprites:
            sprite.draw(screen)

        threat_actor.draw(screen, font)
        cpu_load = server.cpu_load
        server_color = GRAY if cpu_load >= 80 else GREEN
        draw_server_icon(screen, server_sprite, server_color)

        server_status_text = server_status_font.render("Under Attack" if attack_started else "Normal Status", True, BLACK)
        screen.blit(server_status_text, (SCREEN_WIDTH // 2 - 90, SCREEN_HEIGHT // 2 + 100))

        pygame.display.flip()
        clock.tick(FPS)
        env.run(until=env.now + 1)

        if env.now >= DOS_ATTACK_START and not attack_started:
            attack_started = True
            env.process(dos_attacker(env, server, all_sprites))

    pygame.quit()

env = simpy.Environment()
server = Server(env, SERVER_CAPACITY)
env.process(monitor_server(env, server))
pygame_visualization(server, env)

if cpu_load_over_time:
    times, cpu_loads = zip(*cpu_load_over_time)
    plt.figure(figsize=(10, 5))
    plt.plot(times, cpu_loads, label='CPU Load (%)')
    plt.axvline(x=DOS_ATTACK_START, color='red', linestyle='--', label='DoS Attack Start')
    plt.xlabel('Time (s)', fontname='Times New Roman', fontsize=20)
    plt.ylabel('CPU Load (%)', fontname='Times New Roman', fontsize=20)
    plt.title('Server CPU Load Over Time', fontname='Times New Roman', fontsize=22)
    plt.legend(prop={'size': 14})
    plt.grid(True)
    plt.show()

if dropped_packets_over_time:
    times, dropped_packets = zip(*dropped_packets_over_time)
    plt.figure(figsize=(10, 5))
    plt.plot(times, dropped_packets, label='Dropped Packets')
    plt.axvline(x=DOS_ATTACK_START, color='red', linestyle='--', label='DoS Attack Start')
    plt.xlabel('Time (s)', fontname='Times New Roman', fontsize=20)
    plt.ylabel('Dropped Packets', fontname='Times New Roman', fontsize=20)
    plt.title('Dropped Packets Over Time', fontname='Times New Roman', fontsize=22)
    plt.legend(prop={'size': 14})
    plt.grid(True)
    plt.show()
