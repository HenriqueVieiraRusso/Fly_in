"""Pygame display of the simulation."""
import os

os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

import pygame  # noqa: E402

from source.frames import Frame, FrameBuilder, Point  # noqa: E402
from source.graph import Graph  # noqa: E402


WIDTH, HEIGHT, MARGIN, HUD = 1000, 700, 80, 60
BACKGROUND = (20, 22, 28)
TEXT = (230, 230, 230)
LINK = (110, 115, 130)
MOVE_FRACTION = 0.7


class PygameRenderer:
    """Animated view of the network and the drones.

    Controls: SPACE pause, LEFT/RIGHT step, UP/DOWN speed, ESC quit.
    """

    def __init__(self, graph: Graph, lines: list[str]) -> None:
        """Prepare frames and the coordinate transform."""
        self.graph = graph
        self.frames: list[Frame] = FrameBuilder(graph).build(lines)
        xs = [z.x for z in graph.zones.values()]
        ys = [z.y for z in graph.zones.values()]
        self.min_x, self.min_y = min(xs), min(ys)
        span_x = max(max(xs) - self.min_x, 1)
        span_y = max(max(ys) - self.min_y, 1)
        self.scale = min(
            (WIDTH - 2 * MARGIN) / span_x,
            (HEIGHT - HUD - 2 * MARGIN) / span_y,
        )
        self.labels: dict[str, str] = {}
        number = 1
        for zone in graph.zones.values():
            if zone.is_start:
                self.labels[zone.name] = "start hub"
            elif zone.is_end:
                self.labels[zone.name] = "end hub"
            else:
                self.labels[zone.name] = f"hub {number}"
                number += 1

    @staticmethod
    def color_of(name: str | None, default: tuple[int, int, int]
                 ) -> tuple[int, int, int]:
        """Return an RGB tuple for a color name, or `default`."""
        if not name:
            return default
        try:
            c = pygame.Color(name)
        except ValueError:
            return default
        return (c.r, c.g, c.b)

    def to_screen(self, p: Point) -> tuple[int, int]:
        """Map-space coordinates to pixels."""
        return (
            int(MARGIN + (p[0] - self.min_x) * self.scale),
            int(HUD + MARGIN + (p[1] - self.min_y) * self.scale),
        )

    def draw_map(self, screen: pygame.Surface,
                 font: pygame.font.Font) -> None:
        """Draw connections, then zones."""
        for conn in self.graph.connections:
            a = self.graph.zones[conn.zone_a]
            b = self.graph.zones[conn.zone_b]
            pygame.draw.line(
                screen, LINK,
                self.to_screen((a.x, a.y)), self.to_screen((b.x, b.y)),
                2 + 2 * (conn.max_link_capacity - 1),
            )
        for z in self.graph.zones.values():
            pos = self.to_screen((z.x, z.y))
            col = self.color_of(z.color, (150, 150, 150))
            pygame.draw.circle(screen, col, pos, 22)
            if z.zone_type.value == "restricted":
                pygame.draw.circle(screen, (255, 80, 80), pos, 26, 3)
            elif z.zone_type.value == "priority":
                pygame.draw.circle(screen, (255, 215, 0), pos, 26, 3)
            elif z.is_blocked:
                pygame.draw.line(screen, (0, 0, 0),
                                 (pos[0] - 15, pos[1] - 15),
                                 (pos[0] + 15, pos[1] + 15), 4)
                pygame.draw.line(screen, (0, 0, 0),
                                 (pos[0] + 15, pos[1] - 15),
                                 (pos[0] - 15, pos[1] + 15), 4)
            label = font.render(self.labels[z.name], True, TEXT)
            screen.blit(label, (pos[0] - label.get_width() // 2,
                                pos[1] + 30))

    def draw_drones(self, screen: pygame.Surface, font: pygame.font.Font,
                    index: int, progress: float) -> None:
        """Draw drones, interpolated between two frames."""
        cur = self.frames[index]
        nxt = self.frames[min(index + 1, len(self.frames) - 1)]
        slots: dict[tuple[int, int], int] = {}
        for drone, a in cur.items():
            b = nxt[drone]
            p = (a[0] + (b[0] - a[0]) * progress,
                 a[1] + (b[1] - a[1]) * progress)
            sx, sy = self.to_screen(p)
            n = slots.get((sx // 10, sy // 10), 0)
            slots[(sx // 10, sy // 10)] = n + 1
            sx += (n % 4) * 14 - 21
            sy += (n // 4) * 14 - 14
            pygame.draw.circle(screen, (255, 255, 255), (sx, sy), 8)
            pygame.draw.circle(screen, (30, 30, 30), (sx, sy), 8, 1)
            tag = font.render(drone[1:], True, (0, 0, 0))
            screen.blit(tag, (sx - tag.get_width() // 2,
                              sy - tag.get_height() // 2))

    def run(self) -> None:
        """Open the window and play the simulation."""
        pygame.init()
        screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Fly-in")
        font = pygame.font.SysFont(None, 20)
        big = pygame.font.SysFont(None, 28)
        clock = pygame.time.Clock()

        last = len(self.frames) - 1
        position = 0.0          # frame index as a float
        speed = 1.5             # turns per second
        paused = False
        running = True
        while running:
            dt = clock.tick(60) / 1000
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_SPACE:
                        paused = not paused
                    elif event.key == pygame.K_RIGHT:
                        position = min(float(int(position) + 1), last)
                        paused = True
                    elif event.key == pygame.K_LEFT:
                        position = max(float(int(position) - 1), 0.0)
                        paused = True
                    elif event.key == pygame.K_UP:
                        speed = min(speed * 1.5, 12.0)
                    elif event.key == pygame.K_DOWN:
                        speed = max(speed / 1.5, 0.2)
            if not paused:
                position = min(position + speed * dt, float(last))

            index = int(position)
            screen.fill(BACKGROUND)
            self.draw_map(screen, font)
            progress = min((position - index) / MOVE_FRACTION, 1.0)
            self.draw_drones(screen, font, index, progress)
            hud = big.render(
                f"Turn {index}/{last}   speed x{speed:.1f}"
                f"{'   [paused]' if paused else ''}", True, TEXT)
            screen.blit(hud, (20, 18))
            pygame.display.flip()
        pygame.quit()
