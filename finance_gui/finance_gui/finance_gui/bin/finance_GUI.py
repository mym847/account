
import os
import sys
from pathlib import Path
import ttkbootstrap as tb
base_dir = Path(__file__).resolve().parent.parent
DATA_FILE = base_dir / 'data' / 'example.txt'  # 使用斜杠/拼接路径，更直观
sys.path.append(base_dir)
base_dir1 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(base_dir1)
#from bin.MainPage import *
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)  # 获取项目根目录


# 将项目根目录添加到Python路径
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 现在尝试导入
try:
    from bin.MainPage import *
    print("✓ 成功导入 MainPage")
except ImportError as e:
    print(f"导入失败: {e}")

"""修改开始"""
"""修改开始"""


# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
bin_dir = os.path.join(project_root, "bin")

if project_root not in sys.path:

    sys.path.insert(0, project_root)
if bin_dir not in sys.path:
    sys.path.insert(0, bin_dir)

# 尝试导入StatisticsFrame
from bin.StatisticsFrame import StatisticsFrame
"""修改结束"""
"""修改结束"""
"测试用途"
# 原有导入
from bin.view import *


# 创建带主题的主窗口
root = tb.Window(themename="solar")  # 可选主题：darkly, flatly, cyborg, minty, solar, etc.
root.title('Finance for College Students')
# root.iconbitmap(default='icon.ico')  # 如果有图标可放开

MainPage(root)
root.mainloop()



    