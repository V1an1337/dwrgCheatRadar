import win32gui
import win32con
import win32api
import win32ui
import time
import math
import pymem
import pymem.process
import keyboard
import json
from idvClasses import *

with open("config.json", "r") as f:
    config = json.load(f)
CANVAS_SIZE = config["CANVAS_SIZE"]
SCALE = config["SCALE"]
scale = SCALE
SCALE2 = config["SCALE2"]
TRANSPARENCY = config["TRANSPARENCY"]
FPS = config["FPS"]
UPDATE_INTERVAL = float(1 / FPS)
FONT_HEIGHT = config["FONT_HEIGHT"]

VISIBLE = True
entities = {}

PROCESS_NAME = "dwrg.exe"
MODULE_NAME = "neox_engine.dll"

CAMERA_BASE_OFFSET = 0x0616D2C0
PLAYER_BASE_OFFSET = 0x0616D2C0

pm = None
base_address = None
camera = None
survivors = []


def resolve_pointer(pm, base_address, offsets):
    addr = base_address
    try:
        for offset in offsets[:-1]:
            addr = pm.read_ulonglong(addr + offset)
        return addr + offsets[-1]
    except pymem.exception.MemoryReadError:
        return False


def update_entities():
    global camera, survivors
    survivors = []

    camera_base = pm.read_ulonglong(base_address + CAMERA_BASE_OFFSET)
    player_base = pm.read_ulonglong(base_address + PLAYER_BASE_OFFSET)

    index = 1
    for offset in [-0x40, -0x30, -0x20, -0x10, 0x0, 0x10, 0x20, 0x30, 0x40]:
        survivor_offset = [offset]
        camera_offset = [offset]

        survivor = Survivor(pm, player_base, survivor_offset, index=index)
        if survivor.valid and 10 < abs(survivor.x) + abs(survivor.y) + abs(survivor.z) < 100000:
            survivors.append(survivor)
            camera_temp = Camera(pm, camera_base, camera_offset, name=f"c{index}")
            if camera_temp.valid:
                camera = camera_temp
                Print(f"Camera 设置为 {camera.name}")
            index += 1
    return True


def draw_entities(hdc):
    if not update_entities():
        return

    # 用 win32ui 包装 hdc
    dc = win32ui.CreateDCFromHandle(hdc)
    font = win32ui.CreateFont({
        "name": "Arial",
        "height": FONT_HEIGHT,
        "weight": 400
    })
    dc.SelectObject(font)

    if not camera:
        return

    center_x = camera.x
    center_z = camera.z
    angle = math.atan2(camera.direction_z, -camera.direction_x)

    # 中心箭头（朝上）
    win32gui.MoveToEx(hdc, CANVAS_SIZE // 2, CANVAS_SIZE // 2)
    win32gui.LineTo(hdc, CANVAS_SIZE // 2, CANVAS_SIZE // 2 - 30)

    ent_dict = {"cam": (camera.x, camera.z)}
    for s in survivors:
        ent_dict[s.name] = (s.x, s.z)

    for name, (x, z) in ent_dict.items():
        dx = x - center_x
        dz = z - center_z

        rel_x = dx * math.cos(angle) - dz * math.sin(angle)
        rel_z = dx * math.sin(angle) + dz * math.cos(angle)

        cx = CANVAS_SIZE // 2 - int(rel_x * scale)  # X轴反向
        cy = CANVAS_SIZE // 2 + int(rel_z * scale)

        if name == "cam":
            color = win32api.RGB(0, 0, 0)
            brush = win32gui.CreateSolidBrush(color)
            win32gui.FillRect(hdc, (cx - 3, cy - 3, cx + 3, cy + 3), brush)
            win32gui.DeleteObject(brush)
            continue

        # 检查实体是否超出边界
        out_of_fov = False
        if not (0 < cx < CANVAS_SIZE and 0 < cy < CANVAS_SIZE):
            out_of_fov = True
            # 计算箭头指向屏幕边缘
            if cx < 0:
                cx = 0
            elif cx > CANVAS_SIZE:
                cx = CANVAS_SIZE
            if cy < 0:
                cy = 0
            elif cy > CANVAS_SIZE:
                cy = CANVAS_SIZE

            dc.SetTextColor(win32api.RGB(0, 0, 255))  # 蓝色字
            dc.TextOut(cx + (10 if cx == 0 else -int(len(name) * FONT_HEIGHT * 0.6)), cy + (10 if cy == 0 else -20),
                       name)

            # 绘制箭头
            arrow_length = 30  # 箭头长度
            arrow_angle = math.atan2(cy - CANVAS_SIZE // 2, cx - CANVAS_SIZE // 2)
            arrow_end_x = cx - int(arrow_length * math.cos(arrow_angle))
            arrow_end_y = cy - int(arrow_length * math.sin(arrow_angle))

            win32gui.MoveToEx(hdc, cx, cy)
            win32gui.LineTo(hdc, arrow_end_x, arrow_end_y)

        color = win32api.RGB(255, 0, 0)
        brush = win32gui.CreateSolidBrush(color)
        win32gui.FillRect(hdc, (cx - 3, cy - 3, cx + 3, cy + 3), brush)
        win32gui.DeleteObject(brush)
        if name != "cam" and not out_of_fov:
            dc.SetTextColor(win32api.RGB(0, 0, 255))  # 蓝色字
            dc.TextOut(cx + 5, cy, name)

    dc.DeleteDC()  # 清理资源


# --- win32窗口模板修改版 ---

def wndProc(hwnd, msg, wParam, lParam):
    if msg == win32con.WM_PAINT:
        hdc, paintStruct = win32gui.BeginPaint(hwnd)
        draw_entities(hdc)
        win32gui.EndPaint(hwnd, paintStruct)
        return 0
    elif msg == win32con.WM_DESTROY:
        win32gui.PostQuitMessage(0)
        return 0
    else:
        return win32gui.DefWindowProc(hwnd, msg, wParam, lParam)


def main():
    global pm, base_address, scale, VISIBLE

    pm = pymem.Pymem(PROCESS_NAME)
    module = pymem.process.module_from_name(pm.process_handle, MODULE_NAME)
    base_address = module.lpBaseOfDll

    hInstance = win32api.GetModuleHandle()
    className = "MapOverlay"

    wndClass = win32gui.WNDCLASS()
    wndClass.style = win32con.CS_HREDRAW | win32con.CS_VREDRAW
    wndClass.lpfnWndProc = wndProc
    wndClass.hInstance = hInstance
    wndClass.hCursor = win32gui.LoadCursor(None, win32con.IDC_ARROW)
    wndClass.hbrBackground = win32con.COLOR_WINDOW
    wndClass.lpszClassName = className
    wndClassAtom = win32gui.RegisterClass(wndClass)

    hwnd = win32gui.CreateWindowEx(
        win32con.WS_EX_LAYERED | win32con.WS_EX_TOPMOST | win32con.WS_EX_TRANSPARENT,
        wndClassAtom,
        "地图Overlay",
        win32con.WS_POPUP,
        0, 0, CANVAS_SIZE, CANVAS_SIZE,
        None, None, hInstance, None
    )

    win32gui.SetLayeredWindowAttributes(hwnd, 0, int(255 * TRANSPARENCY), win32con.LWA_ALPHA)
    win32gui.ShowWindow(hwnd, win32con.SW_SHOW)

    # 初始化SCALE状态
    last_toggle_time = 0

    while True:
        if keyboard.is_pressed('insert'):
            if time.time() - last_toggle_time > 0.3:  # 防止切换过快
                VISIBLE = not VISIBLE
                if VISIBLE:
                    win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
                else:
                    win32gui.ShowWindow(hwnd, win32con.SW_HIDE)
                last_toggle_time = time.time()
        # 检查是否按下了F键（带去抖）
        if keyboard.is_pressed('f'):
            if time.time() - last_toggle_time > 0.3:  # 防止切换过快
                scale = SCALE2 if scale == SCALE else SCALE
                Print(f"SCALE 切换为：{scale}")
                last_toggle_time = time.time()
        win32gui.InvalidateRect(hwnd, None, True)
        win32gui.PumpWaitingMessages()
        time.sleep(UPDATE_INTERVAL)


if __name__ == "__main__":
    main()