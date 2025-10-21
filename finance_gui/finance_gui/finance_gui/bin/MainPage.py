from bin.view import *   # 菜单栏对应的各个子页面
from tkinter import ttk
"""修改开始"""
import tkinter as tk
import ttkbootstrap as tb
from ttkbootstrap.constants import *
from bin.StatisticsFrame import StatisticsFrame
import sys
import os

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 现有的导入语句
from bin.view import *   # 菜单栏对应的各个子页面

# 添加统计模块的导入
try:
    from bin.StatisticsFrame import StatisticsFrame
except ImportError as e:
    print(f"导入统计模块失败: {e}")
    # 如果导入失败，创建一个空的占位符类
    class StatisticsFrame(tb.Frame):
        def __init__(self, parent):
            super().__init__(parent)
            label = tb.Label(self, text="统计模块加载失败，请检查StatisticsFrame.py文件")
            label.pack(pady=20)
"""修改结束"""

class MainPage(object):
    def __init__(self, master=None):
        self.win = master  # 定义内部变量root
        # self.win.protocol('WM_DELETE_WINDOW', self.closeWindow)  # 绑定窗口关闭事件，防止计时器正在工作导致数据丢失

        # 设置窗口大小
        winWidth = 1000
        winHeight = 800
        # 获取屏幕分辨率
        screenWidth = self.win.winfo_screenwidth()
        screenHeight = self.win.winfo_screenheight()

        x = int((screenWidth - winWidth) / 2)
        y = int((screenHeight - winHeight) / 2)

        # 设置窗口初始位置在屏幕居中
        self.win.geometry("%sx%s+%s+%s" % (winWidth, winHeight, x, y))
        self.page = None  # 用于标记功能界面
        self.createPage()
        """修改开始"""
        # 在创建其他标签页的代码后面添加
        #self.add_statistics_tab()
        self.statistics_frame = StatisticsFrame(self.notebook)
        self.notebook.add(self.statistics_frame, text="统计图表")
        """修改结束"""

    def createPage(self):
        # 设置主框架标签页
        # Tab Control introduced here --------------------------------------
        tabControl = tb.Notebook(self.win, bootstyle="solar") 
        self.notebook = tabControl # Create Tab Control
  # 主页
        tab1 = tb.Frame(tabControl)  # Create a tab
        tabControl.add(tab1, text='  主页  ')  # Add the tab

        tab2 = tb.Frame(tabControl)  # Add a second tab
        tabControl.add(tab2, text='  支出  ')  # Make second tab visible

        tab3 = tb.Frame(tabControl)  # Add a third tab
        tabControl.add(tab3, text='  收入  ')  # Make second tab visible

        tab_budget = tb.Frame(tabControl)
        tabControl.add(tab_budget, text='  预算  ')

        tab4 = tb.Frame(tabControl)
        tabControl.add(tab4, text='  借入  ')

        tab5 = tb.Frame(tabControl)
        tabControl.add(tab5, text='  借出  ')

        tab6 = tb.Frame(tabControl)
        tabControl.add(tab6, text='  还款  ')

        tab7 = tb.Frame(tabControl)
        tabControl.add(tab7, text='  记录  ')

        tab8 = tb.Frame(tabControl)
        tabControl.add(tab8, text='  备份与恢复  ')


        tabControl.pack(expand=YES, fill=BOTH, padx=10, pady=10)  # Pack to make visible
        # ~ Tab Control introduced here -----------------------------------------

        # ========= 主页布局 =========
        # 第0行：信息汇总区（左：IndexFrame，右：预算容器）
        # 第1行：两个饼图（支出 / 收入）
        try:
            tab1.rowconfigure(0, weight=1)   # 信息汇总区域可扩展
            tab1.rowconfigure(1, weight=0)   # 饼图行不纵向扩展
            tab1.columnconfigure(0, weight=1)
        except Exception:
            pass

        # 信息汇总容器（两列）
        summary_pair = tb.Frame(tab1)
        summary_pair.grid(row=0, column=0, sticky="nsew", padx=10, pady=(10, 0))
        # 左右列等权重，确保右侧预算不会被压缩；同时为预算列设定一个最小宽度
        try:
            summary_pair.columnconfigure(0, weight=1)
            summary_pair.columnconfigure(1, weight=1, minsize=420)
            summary_pair.rowconfigure(0, weight=1)
        except Exception:
            pass

        # 左侧：信息汇总（IndexFrame）
        self.monty1 = IndexFrame(summary_pair)
        self.monty1.grid(column=0, row=0, padx=8, pady=4, sticky="nsew")

        # 右侧：预算专用容器（外层 LabelFrame，内层 host 承载 BudgetFrame）
        home_budget_group = tb.LabelFrame(summary_pair, text="预算")
        home_budget_group.grid(column=1, row=0, padx=8, pady=4, sticky="nsew")
        # 让容器内部可扩展
        try:
            home_budget_group.columnconfigure(0, weight=1)
            home_budget_group.rowconfigure(0, weight=1)
        except Exception:
            pass
        # host：真正承载 BudgetFrame 的容器
        self.home_budget_host = tb.Frame(home_budget_group)
        self.home_budget_host.grid(row=0, column=0, sticky="nsew", padx=6, pady=6)

        # 在 host 中创建 BudgetFrame。注意：BudgetFrame 内部会创建 self.root 并自己 grid()，
        # 因此此处不要再对 self.home_budget_panel 调用 grid()，以免双重布局。
        self.home_budget_panel = BudgetFrame(self.home_budget_host)
        # 尝试让 BudgetFrame 的内部 root 充满 host，避免被压缩
        try:
            self.home_budget_panel.root.grid_configure(sticky="nsew")
        except Exception:
            pass

        # ========= 分类占比（支出 / 收入） =========
        charts_group = tb.LabelFrame(tab1, text="本月分类占比（支出 / 收入）")
        charts_group.grid(row=1, column=0, sticky="ew", padx=10, pady=10)
        charts_group.columnconfigure(0, weight=1)

        # 工具栏（右侧刷新按钮）
        toolbar = tb.Frame(charts_group)
        toolbar.grid(row=0, column=0, sticky="ew", padx=6, pady=(6, 0))
        toolbar.columnconfigure(0, weight=1)

        def _home_refresh():
            try:
                from datetime import datetime
                now = datetime.now()
                # 刷新支出
                self.statistics_frame.render_pie_chart_in_parent(self.home_pie_frame, now.year, now.month)
                # 刷新收入
                if hasattr(self, "home_income_pie_frame"):
                    self.statistics_frame.render_income_pie_chart_in_parent(self.home_income_pie_frame, now.year, now.month)
                # 刷新主页预算栏
                try:
                    self.home_budget_panel.show_infos()
                except Exception:
                    pass
            except Exception as _e:
                for frm in (getattr(self, "home_pie_frame", None), getattr(self, "home_income_pie_frame", None)):
                    if frm:
                        try:
                            for w in frm.winfo_children():
                                w.destroy()
                        except Exception:
                            pass
                        tb.Label(frm, text=f"刷新失败：{_e}").pack(padx=10, pady=10, anchor="w")

        self.refresh_home_pie = _home_refresh
        btn_refresh = tb.Button(toolbar, text="刷新", command=self.refresh_home_pie,bootstyle="success")
        btn_refresh.grid(row=0, column=1, padx=0, pady=0, sticky="e")

        # 两个饼图并排
        pair = tb.Frame(charts_group)
        pair.grid(row=1, column=0, sticky="ew", padx=6, pady=6)
        pair.columnconfigure(0, weight=1)
        pair.columnconfigure(1, weight=1)

        # 左：支出
        left_group = tb.LabelFrame(pair, text="支出分类占比")
        left_group.grid(row=0, column=0, sticky="w", padx=(0, 6))
        self.home_pie_frame = tb.Frame(left_group, width=340, height=340)
        self.home_pie_frame.grid(row=0, column=0, sticky="w", padx=6, pady=6)
        self.home_pie_frame.grid_propagate(False)

        # 右：收入
        right_group = tb.LabelFrame(pair, text="收入分类占比")
        right_group.grid(row=0, column=1, sticky="w", padx=(6, 0))
        self.home_income_pie_frame = tb.Frame(right_group, width=340, height=340)
        self.home_income_pie_frame.grid(row=0, column=0, sticky="w", padx=6, pady=6)
        self.home_income_pie_frame.grid_propagate(False)

        # 确保已创建 statistics_frame 实例（在统计页使用的同一个实例）
        try:
            _ = self.statistics_frame
        except AttributeError:
            hidden_tab = tb.Frame(self.notebook)
            self.statistics_frame = StatisticsFrame(hidden_tab)  # 不加入到 notebook

        # 初始渲染（支出 + 收入）
        try:
            from datetime import datetime
            now = datetime.now()
            self.statistics_frame.render_pie_chart_in_parent(self.home_pie_frame, now.year, now.month)
            self.statistics_frame.render_income_pie_chart_in_parent(self.home_income_pie_frame, now.year, now.month)
        except Exception as e:
            for frm in (self.home_pie_frame, self.home_income_pie_frame):
                try:
                    tb.Label(frm, text=f"渲染分类占比图失败：{e}").grid(row=0, column=0, padx=10, pady=10, sticky="w")
                except Exception:
                    pass

        # ========= 其它标签页 =========
        self.monty2 = PaymentFrame(tab2)
        self.monty2.grid(column=0, row=0, padx=8, pady=4)

        self.monty3 = IncomeFrame(tab3)
        self.monty3.grid(column=0, row=0, padx=8, pady=4)
        # 预算页
        self.monty_budget = BudgetFrame(tab_budget)
        self.monty_budget.grid(column=0, row=0, padx=8, pady=4)

        self.monty4 = BorrowFrame(tab4)
        self.monty4.grid(column=0, row=0, padx=8, pady=4)

        self.monty5 = LendFrame(tab5)
        self.monty5.grid(column=0, row=0, padx=8, pady=4)

        self.monty6 = RepaymentFrame(tab6)
        self.monty6.grid(column=0, row=0, padx=8, pady=4)

        self.monty7 = NoteFrame(tab7)
        self.monty7.grid(column=0, row=0, padx=8, pady=4)

        monty8 = BackupFrame(tab8)
        monty8.grid(column=0, row=0, padx=8, pady=4)

        # 绑定标签栏 鼠标左键事件 用于每次点击 主页标签都能得到最新的汇总信息
        tabControl.bind("<Button-1>", self.reshow_infos) 
        #self.notebook.bind("<Button-1>", self.reshow_infos) # 调用方法获取最新汇总信息

    # 绑定事件：当有支出/收入变化时刷新预算显示
        try:
            self.win.bind('<<PaymentsChanged>>', self.reshow_infos)
            self.win.bind('<<IncomesChanged>>', self.reshow_infos)
        except Exception:
            pass

    def reshow_infos(self, event=None):
        # 刷新显示各个页面最新信息
        try:
            self.monty1.show_infos()
        except Exception:
            pass
        try:
            self.monty2.showAll()
        except Exception:
            pass
        try:
            self.monty3.showAll()
        except Exception:
            pass
        # 主页预算栏
        try:
            self.home_budget_panel.show_infos()
        except Exception:
            pass
        # 预算标签页（保留）
        try:
            self.monty_budget.show_infos()
        except Exception:
            pass
        try:
            self.monty4.showAll()
        except Exception:
            pass
        try:
            self.monty5.showAll()
        except Exception:
            pass
        try:
            self.monty6.showAll()
        except Exception:
            pass
        try:
            self.monty7.showAll()
        except Exception:
            pass
  

    
'''修改开始'''
def add_statistics_tab(self):

        """添加统计图表标签页"""
        print("开始添加统计标签页...")
        print(f"Notebook状态: {self.notebook}")
        print(f"Notebook类型: {type(self.notebook)}")
    
              # 检查notebook的方法和属性
        print(f"Notebook方法: {[method for method in dir(self.notebook) if not method.startswith('_')]}")
              # 创建统计标签页的框架
        tab9 = tb.Frame(self.notebook)
        self.notebook.add(tab9, text='  统计图表  ')
            
            # 在标签页中创建统计框架
        self.statistics_frame = StatisticsFrame(tab9)
        self.statistics_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
            
            
    

