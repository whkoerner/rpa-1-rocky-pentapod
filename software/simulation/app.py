"""Pygame front end for RPA-1 Simulation v0.1."""

from __future__ import annotations

import json
import math
from pathlib import Path

import pygame

from .logger import CsvRunLogger
from .model import ContactState, RobotMode, SimRobot


HERE = Path(__file__).resolve().parent
CONFIG_PATH = HERE / "config" / "robot.json"
LOG_DIR = HERE / "logs"


def load_config() -> dict:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def limb_points(robot: SimRobot, limb_index: int, center: tuple[int, int]) -> tuple[tuple[int, int], ...]:
    display = robot.config["display"]
    limb = robot.limbs[limb_index]
    base_deg = -90.0 + limb_index * (360.0 / len(robot.limbs))
    joint_1 = limb.actuators[0].position_deg
    joint_2 = limb.actuators[1].position_deg

    a1 = math.radians(base_deg + joint_1)
    a2 = math.radians(base_deg + joint_1 + joint_2)
    body_r = float(display["body_radius_px"])
    seg1 = float(display["segment_1_px"])
    seg2 = float(display["segment_2_px"])

    shoulder = (
        int(center[0] + math.cos(a1) * body_r),
        int(center[1] + math.sin(a1) * body_r),
    )
    elbow = (
        int(shoulder[0] + math.cos(a1) * seg1),
        int(shoulder[1] + math.sin(a1) * seg1),
    )
    foot = (
        int(elbow[0] + math.cos(a2) * seg2),
        int(elbow[1] + math.sin(a2) * seg2),
    )
    return shoulder, elbow, foot


def draw(screen: pygame.Surface, font: pygame.font.Font, robot: SimRobot, csp_mode: bool, csp_buffer: str) -> None:
    screen.fill((245, 245, 245))
    width, height = screen.get_size()
    center = (width // 2, height // 2)

    pygame.draw.circle(screen, (60, 60, 60), center, int(robot.config["display"]["body_radius_px"]), 3)

    contact_colors = {
        ContactState.UNKNOWN: (120, 120, 120),
        ContactState.CONTACT: (30, 140, 60),
        ContactState.FREE: (190, 90, 40),
    }

    for limb in robot.limbs:
        shoulder, elbow, foot = limb_points(robot, limb.index, center)
        pygame.draw.line(screen, (40, 80, 130), shoulder, elbow, 6)
        pygame.draw.line(screen, (40, 80, 130), elbow, foot, 6)
        pygame.draw.circle(screen, (30, 30, 30), shoulder, 6)
        pygame.draw.circle(screen, (30, 30, 30), elbow, 6)
        pygame.draw.circle(screen, contact_colors[limb.contact], foot, 9)

        label = font.render(str(limb.index + 1), True, (20, 20, 20))
        screen.blit(label, (foot[0] + 10, foot[1] - 10))

    status = [
        f"Mode: {robot.mode.value}",
        f"Fault: {robot.fault or '-'}",
        f"Gait: {'ON' if robot.gait_active else 'OFF'}  limb={robot.gait_limb_index + 1} phase={robot.gait_phase}",
        f"Last CSP-1: {robot.last_csp_intent or '-'} {robot.last_csp_text}",
        "Keys: A=arm  SPACE=start/stop gait  E=E-stop  R=reset",
        "1-5=cycle contact UNKNOWN -> CONTACT -> FREE  C=enter CSP-1 line  ESC=quit/cancel",
    ]

    y = 12
    for line in status:
        surface = font.render(line, True, (20, 20, 20))
        screen.blit(surface, (12, y))
        y += 24

    if csp_mode:
        prompt = font.render("CSP-1> " + csp_buffer, True, (80, 20, 120))
        screen.blit(prompt, (12, height - 38))


def run() -> None:
    config = load_config()
    robot = SimRobot(config)
    fixed_step_s = float(config["fixed_step_s"])

    pygame.init()
    screen = pygame.display.set_mode(
        (int(config["display"]["width_px"]), int(config["display"]["height_px"]))
    )
    pygame.display.set_caption("RPA-1 Simulation v0.1")
    font = pygame.font.Font(None, 24)
    clock = pygame.time.Clock()

    logger = CsvRunLogger(LOG_DIR)
    running = True
    accumulator = 0.0
    sim_time_s = 0.0
    csp_mode = False
    csp_buffer = ""

    digit_keys = {
        pygame.K_1: 0,
        pygame.K_2: 1,
        pygame.K_3: 2,
        pygame.K_4: 3,
        pygame.K_5: 4,
    }

    try:
        while running:
            elapsed_s = min(clock.tick(60) / 1000.0, 0.25)
            accumulator += elapsed_s

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    continue
                if event.type != pygame.KEYDOWN:
                    continue

                if csp_mode:
                    if event.key == pygame.K_ESCAPE:
                        csp_mode = False
                        csp_buffer = ""
                    elif event.key == pygame.K_RETURN:
                        robot.handle_csp(csp_buffer + "\n")
                        csp_mode = False
                        csp_buffer = ""
                    elif event.key == pygame.K_BACKSPACE:
                        csp_buffer = csp_buffer[:-1]
                    elif event.unicode and event.unicode.isprintable():
                        csp_buffer += event.unicode
                    continue

                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_a:
                    robot.arm()
                elif event.key == pygame.K_e:
                    robot.emergency_stop()
                elif event.key == pygame.K_r:
                    robot.reset()
                elif event.key == pygame.K_SPACE:
                    if robot.gait_active:
                        robot.stop_gait()
                    else:
                        robot.start_gait()
                elif event.key == pygame.K_c:
                    csp_mode = True
                    csp_buffer = ""
                elif event.key in digit_keys:
                    robot.toggle_contact(digit_keys[event.key])

            while accumulator >= fixed_step_s:
                robot.update(fixed_step_s)
                sim_time_s += fixed_step_s
                logger.record(robot, sim_time_s)
                accumulator -= fixed_step_s

            draw(screen, font, robot, csp_mode, csp_buffer)
            pygame.display.flip()
    finally:
        logger.close()
        pygame.quit()


if __name__ == "__main__":
    run()
