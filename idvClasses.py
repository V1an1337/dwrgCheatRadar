import pymem

DEBUG = False
def Print(*args, **kwargs):
    if DEBUG:
        print(*args, **kwargs)

def resolve_pointer(pm, base_address, offsets):
    addr = base_address
    try:
        for offset in offsets[:-1]:
            addr = pm.read_ulonglong(addr + offset)
        return addr + offsets[-1]
    except pymem.exception.MemoryReadError as e:
        #print(f"[错误] 无法读取地址：{hex(base_address)}, {[hex(i) for i in offsets]}, {hex(addr)}, {e}")
        return False


class Survivor:
    PLAYER_POST_OFFSET = [0x40, 0x50]
    NAME_OFFSETS = [0x170, 0x0, 0xB8, 0x28, 0x8, 0x0]
    SURVIVOR_MAP = {
        "h55_survivor_w_bdz": "空军", "h55_survivor_m_qiutu": "囚徒",
        "h55_survivor_m_yxz": "佣兵", "h55_survivor_w_jyz": "盲女",
        "h55_survivor_w_xiangshuishi": "调香师", "h55_survivor_m_shoumu": "守墓人",
        "dm65_survivor_w_yiyaoshi": "医生", "h55_survivor_m_yc": "邮差",
        "h55_survivor_m_zbs": "先知", "h55_survivor_w_cp": "心理学家",
        "h55_survivor_m_ldz": "魔术师", "h55_survivor_m_rls": "入殓师",
        "h55_survivor_m_it": "律师", "h55_survivor_m_qd": "慈善家",
        "h55_survivor_m_ydy": "前锋", "h55_survivor_w_hlz": "园丁",
        "h55_survivor_m_xcz": "冒险家", "h55_survivor_w_fxt": "机械师",
        "h55_survivor_w_jisi": "祭司", "h55_survivor_m_niuzai": "牛仔",
        "h55_survivor_w_wht": "舞女", "h55_survivor_m_kantan": "勘探员",
        "h55_survivor_w_zhoushu": "咒术师", "h55_survivor_m_yeren": "野人",
        "h55_survivor_m_zaji": "杂技演员", "h55_survivor_m_dafu": "大副",
        "h55_survivor_w_tiaojiu": "调酒师", "h55_survivor_w_kunchong": "昆虫学者",
        "h55_survivor_m_artist": "画家", "h55_survivor_m_jiqiu": "击球手",
        "h55_survivor_w_shangren": "玩具商", "h55_survivor_m_cp": "病患",
        "h55_survivor_m_bzt": "小说家", "dm65_survivor_girl": "小女孩",
        "h55_survivor_m_spjk": "哭泣小丑", "h55_survivor_m_niexi": "教授",
        "h55_survivor_w_gd": "古董商", "h55_survivor_m_yinyue": "作曲家",
        "h55_survivor_w_deluosi": "记者", "h55_survivor_m_fxj": "飞行家",
        "h55_survivor_w_ll": "啦啦队员", "h55_survivor_m_muou": "木偶师",
        "h55_survivor_m_xf": "火灾调查员", "h55_survivor_w_fl": "法罗女士",
        "h55_survivor_m_dxzh": "骑士", "h55_survivor_w_qx": "气象学家",
        "dm65_survivor_m_bo": "幸运儿"
    }
    def __init__(self, pm: pymem.Pymem, base_address, offset: list, index=""):
        self.pm = pm
        self.base_address = base_address
        self.x_offsets = offset + self.PLAYER_POST_OFFSET
        self.name_offsets = offset + self.NAME_OFFSETS
        self.index = index

        self.x, self.y, self.z = 10000, 10000, 10000
        self.name = ""
        self.valid = True

        self.x_addr = resolve_pointer(pm, self.base_address, self.x_offsets)
        #print(self.x_addr)
        if not self.x_addr:
            #print(f"Survivor {index} 无法解析地址")
            self.valid = False
            return
        self.y_addr = self.x_addr + 0x4
        self.z_addr = self.x_addr + 0x8
        Print(f"Survivor {index} 解析地址成功 {[hex(i) for i in self.x_offsets]} -> {hex(self.x_addr)}！")

        self.name_addr = resolve_pointer(pm, self.base_address, self.name_offsets)
        Print(f"Survivor {index} 解析名称成功 {[hex(i) for i in self.name_offsets]} -> {hex(self.name_addr)}！")

        try:
            self.update()
        except Exception as e:
            Print(f"Survivor {index} 读取信息失败：{e}")
            self.valid = False
            return

    def update(self):
        self.x = self.pm.read_float(self.x_addr)
        self.y = self.pm.read_float(self.y_addr)
        self.z = self.pm.read_float(self.z_addr)

        self.name = self.pm.read_string(self.name_addr, byte=100, encoding="utf-8")
        self.name = self.get_survivor_type(self.name) + f"({self.index})"
        Print(f"Survivor {self.name} 更新坐标：{self.x}, {self.y}, {self.z}")

    def get_survivor_type(self, name):
        for key, value in self.SURVIVOR_MAP.items():
            if key in name:
                if "qiutu" in name and "box" in name:
                    return "unknown"
                return value
        return "unknown"


class Camera:
    CAMERA_POST_OFFSET = [0x40, 0x18, 0xB8, 0xD18, 0x20, 0x20, 0x50]
    def __init__(self, pm, base_address, offset:list, name=""):
        self.pm = pm
        self.base_address = base_address
        self.x_offsets = offset + self.CAMERA_POST_OFFSET
        self.name = name
        self.x, self.y, self.z = 10000, 10000, 10000
        self.direction_x, self.direction_z = 0, 0
        self.valid = True

        self.x_addr = resolve_pointer(pm, self.base_address, self.x_offsets)
        if not self.x_addr:
            Print(f"Camera {name} 无法解析地址")
            self.valid = False
            return
        self.y_addr = self.x_addr + 0x4
        self.z_addr = self.x_addr + 0x8
        self.direction_x_addr = self.x_addr + 0x18
        self.direction_z_addr = self.x_addr + 0x20
        Print(f"Camera {name} 解析地址成功！{[hex(i) for i in offset]} -> {hex(self.x_addr)}")
        #print(f"camera {name} x_addr: {hex(self.x_addr)}")

        self.update()

    def update(self):
        self.x = self.pm.read_float(self.x_addr)
        self.y = self.pm.read_float(self.y_addr)
        self.z = self.pm.read_float(self.z_addr)
        self.direction_x = self.pm.read_float(self.direction_x_addr)  # 范围1~-1
        self.direction_z = self.pm.read_float(self.direction_z_addr)  # 范围1~-1
        # print(f"Camera {self.name} 更新坐标：{self.x}, {self.y}, {self.z}")