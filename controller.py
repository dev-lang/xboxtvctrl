"""
Xbox Controller -> Mouse
Pensado para usarse en la PC host de Sunshine (Windows), controlando
desde la TV con Moonlight y un joystick Xbox, para jugar títulos que
solo soportan mouse (ej: Sort Works: Nuts & Order).

Requisitos (correr en la PC con Windows, NO en el cliente Moonlight):
    pip install XInput-Python pywin32

Uso:
    python controller_mouse.py

Controles:
    Stick izquierdo -> mueve el cursor
    RT o botón A    -> click izquierdo (mantené para drag & drop)
    LT o botón B    -> click derecho
    Stick derecho   -> scroll vertical
    LB / RB         -> baja / sube sensibilidad (ajuste fino)
    Cruceta         -> mueve el cursor pixel a pixel (para encastrar con precisión)
    Start           -> pausa / reanuda el control de mouse
    Ctrl+C          -> salir
"""

import sys
import time

try:
    import XInput
except ImportError:
    print("Falta la librería XInput. Instalá con: pip install XInput-Python")
    sys.exit(1)

try:
    import win32api
    import win32con
except ImportError:
    print("Falta pywin32. Instalá con: pip install pywin32")
    sys.exit(1)

# ---------- Config ----------
DEADZONE = 0.18
BASE_SENSITIVITY = 35.0     # píxeles por frame con el stick a fondo (antes 18)
CURVE_EXPONENT = 1.8        # >1 = movimientos chicos más precisos, a fondo más rápido
POLL_HZ = 125
SCROLL_DEADZONE = 0.30
SCROLL_SENSITIVITY = 3
FINE_STEP = 1                    # píxeles por paso con la cruceta
DPAD_MOVE_EVERY_N_FRAMES = 4      # más alto = movimiento más lento/fino, más bajo = más rápido
# -----------------------------

screen_w = win32api.GetSystemMetrics(0)
screen_h = win32api.GetSystemMetrics(1)


def apply_deadzone(value, dz):
    if abs(value) < dz:
        return 0.0
    sign = 1 if value > 0 else -1
    return sign * (abs(value) - dz) / (1 - dz)


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


class ControllerMouse:
    def __init__(self):
        self.sensitivity = BASE_SENSITIVITY
        self.left_down = False
        self.right_down = False
        self.paused = False
        self.start_was_pressed = False
        self.dpad_frame_counter = 0

    def run(self):
        print(f"Listo. Resolución detectada: {screen_w}x{screen_h}. Ctrl+C para salir.")
        period = 1.0 / POLL_HZ
        while True:
            if not XInput.get_connected()[0]:
                print("Esperando control en el puerto 0...", end="\r")
                time.sleep(0.5)
                continue
            self.tick()
            time.sleep(period)

    def tick(self):
        state = XInput.get_state(0)
        stick_l, stick_r = XInput.get_thumb_values(state)
        trig_l, trig_r = XInput.get_trigger_values(state)
        buttons = XInput.get_button_values(state)

        # Pausa con Start
        if buttons['START'] and not self.start_was_pressed:
            self.paused = not self.paused
            print(f"\n{'Pausado' if self.paused else 'Activo'}")
        self.start_was_pressed = buttons['START']

        if self.paused:
            return

        # Sensibilidad con bumpers
        if buttons['LEFT_SHOULDER']:
            self.sensitivity = clamp(self.sensitivity - 0.3, 4, 80)
        if buttons['RIGHT_SHOULDER']:
            self.sensitivity = clamp(self.sensitivity + 0.3, 4, 80)

        # Movimiento del cursor con stick izquierdo
        rx, ry = stick_l
        rx = apply_deadzone(rx, DEADZONE)
        ry = apply_deadzone(ry, DEADZONE)
        if rx or ry:
            # Curva no lineal: conserva el signo, exagera la magnitud
            rx_c = (abs(rx) ** CURVE_EXPONENT) * (1 if rx >= 0 else -1)
            ry_c = (abs(ry) ** CURVE_EXPONENT) * (1 if ry >= 0 else -1)
            dx = rx_c * self.sensitivity
            dy = -ry_c * self.sensitivity  # arriba del stick = arriba en pantalla
            cx, cy = win32api.GetCursorPos()
            nx = clamp(cx + dx, 0, screen_w - 1)
            ny = clamp(cy + dy, 0, screen_h - 1)
            win32api.SetCursorPos((int(nx), int(ny)))

        # Movimiento fino del cursor con la cruceta (pixel a pixel, para precisión)
        self.dpad_frame_counter += 1
        if self.dpad_frame_counter >= DPAD_MOVE_EVERY_N_FRAMES:
            self.dpad_frame_counter = 0
            fdx = fdy = 0
            if buttons['DPAD_LEFT']:
                fdx -= FINE_STEP
            if buttons['DPAD_RIGHT']:
                fdx += FINE_STEP
            if buttons['DPAD_UP']:
                fdy -= FINE_STEP
            if buttons['DPAD_DOWN']:
                fdy += FINE_STEP
            if fdx or fdy:
                cx, cy = win32api.GetCursorPos()
                nx = clamp(cx + fdx, 0, screen_w - 1)
                ny = clamp(cy + fdy, 0, screen_h - 1)
                win32api.SetCursorPos((int(nx), int(ny)))

        # Click izquierdo: A o RT (sirve para drag & drop manteniendo apretado)
        left_should = buttons['A'] or trig_r > 0.5
        if left_should and not self.left_down:
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            self.left_down = True
        elif not left_should and self.left_down:
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
            self.left_down = False

        # Click derecho: B o LT
        right_should = buttons['B'] or trig_l > 0.5
        if right_should and not self.right_down:
            win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, 0)
            self.right_down = True
        elif not right_should and self.right_down:
            win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)
            self.right_down = False

        # Scroll con stick derecho
        lx, ly = stick_r
        ly = apply_deadzone(ly, SCROLL_DEADZONE)
        if ly:
            win32api.mouse_event(
                win32con.MOUSEEVENTF_WHEEL, 0, 0,
                int(ly * 120 * SCROLL_SENSITIVITY / 10), 0
            )


if __name__ == "__main__":
    ControllerMouse().run()
