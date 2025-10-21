import os
import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
from datetime import datetime, timedelta
import calendar
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import matplotlib.dates as mdates
from matplotlib import font_manager as fm
from matplotlib.backend_bases import MouseButton
import math
import ttkbootstrap as tb
from ttkbootstrap.constants import *


class StatisticsFrame(tb.Frame):
    """统计模块框架"""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        # 使用更可靠的路径计算方法
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)
        self.db_path = os.path.join(project_root, "db", "finance.db")

        
        print(f"数据库路径: {self.db_path}")
        print(f"数据库文件存在: {os.path.exists(self.db_path)}")
        
        # 设置中文字体支持
        plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False
        

        
        # 用于鼠标交互的属性
        self.current_fig = None
        self.current_canvas = None
        self.current_category_names = []
        
        self.create_widgets()
        
    def create_widgets(self):
        """创建界面组件"""
        # 主框架
        main_frame = tb.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 控制面板
        control_frame = tb.LabelFrame(main_frame, text="统计选项")
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 年份选择
        tb.Label(control_frame, text="选择年份:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.year_var = tk.StringVar(value=str(datetime.now().year))
        year_combo = tb.Combobox(control_frame, textvariable=self.year_var, width=10)
        year_combo['values'] = [str(y) for y in range(2020, datetime.now().year + 1)]
        year_combo.grid(row=0, column=1, padx=5, pady=5)
        
        # 月份选择
        tb.Label(control_frame, text="选择月份:").grid(row=0, column=2, padx=5, pady=5, sticky=tk.W)
        self.month_var = tk.StringVar(value=str(datetime.now().month))
        month_combo = tb.Combobox(control_frame, textvariable=self.month_var, width=10)
        month_combo['values'] = [str(m) for m in range(1, 13)]
        month_combo.grid(row=0, column=3, padx=5, pady=5)
        
        # 按钮
        tb.Button(control_frame, text="生成月度支出饼图", 
                  command=self.generate_pie_chart).grid(row=0, column=4, padx=5, pady=5)
        tb.Button(control_frame, text="生成年度支出饼图", 
                  command=self.generate_yearly_pie_chart).grid(row=0, column=5, padx=5, pady=5)
        # 新增：月度柱状图与年度柱状图
        tb.Button(control_frame, text="生成月度支出柱状图", 
                  command=self.generate_monthly_bar_chart).grid(row=1, column=4, padx=5, pady=5)
        tb.Button(control_frame, text="生成年度支出柱状图", 
                  command=self.generate_bar_chart).grid(row=1, column=5, padx=5, pady=5)
        
        # 状态显示
        self.status_label = tb.Label(control_frame, text="")
        self.status_label.grid(row=0, column=6, padx=10, pady=5)
        
        # 图表显示区域
        self.chart_frame = tb.Frame(main_frame)
        self.chart_frame.pack(fill=tb.BOTH, expand=True)

    def get_db_connection(self):
        """获取数据库连接"""
        try:
            # 检查数据库文件是否存在
            if not os.path.exists(self.db_path):
                messagebox.showerror("数据库错误", f"数据库文件不存在: {self.db_path}")
                return None
                
            conn = sqlite3.connect(self.db_path)
            return conn
        except sqlite3.Error as e:
            messagebox.showerror("数据库错误", f"无法连接数据库: {e}")
            return None

    def get_table_structure(self, table_name):
        """获取表结构信息"""
        conn = self.get_db_connection()
        if not conn:
            return None
            
        try:
            cursor = conn.cursor()
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            return columns
        except sqlite3.Error as e:
            print(f"获取表结构错误: {e}")
            return None
        finally:
            conn.close()

    def get_monthly_expenses_by_category(self, year, month):
        """获取指定月份按分类的支出数据（父子分类合并为标签：父——子）"""
        conn = self.get_db_connection()
        if not conn:
            return None
        try:
            # 该月范围
            _, last_day = calendar.monthrange(year, month)
            start_date = f"{year}-{month:02d}-01"
            end_date = f"{year}-{month:02d}-{last_day:02d}"
            cursor = conn.cursor()
            # 父子分类合并标签
            query = """
                SELECT 
                    CASE 
                        WHEN pc_c.title IS NOT NULL AND pc_c.title <> '' THEN pc_p.title || '——' || pc_c.title
                        ELSE COALESCE(pc_p.title, '未分类')
                    END AS category_label,
                    SUM(p.money) AS total_amount
                FROM payments p
                LEFT JOIN pay_categorys pc_p ON p.category_pid = pc_p.id
                LEFT JOIN pay_categorys pc_c ON p.category_cid = pc_c.id
                WHERE p.note_date BETWEEN ? AND ? 
                AND p.is_delete = 0
                GROUP BY category_label
                ORDER BY total_amount DESC
            """
            cursor.execute(query, (start_date, end_date))
            results = cursor.fetchall()
            return results
        except sqlite3.Error as e:
            messagebox.showerror("查询错误", f"查询数据时出错: {e}")
            return None
        finally:
            conn.close()
    
    def get_category_details(self, year, month, category_name):
        """获取指定分类的详细支出记录（支持父——子标签）"""
        conn = self.get_db_connection()
        if not conn:
            return None
        try:
            _, last_day = calendar.monthrange(year, month)
            start_date = f"{year}-{month:02d}-01"
            end_date = f"{year}-{month:02d}-{last_day:02d}"
            cursor = conn.cursor()
            if category_name == '未分类':
                query = """
                    SELECT id, note_date, title, remark, money, create_time 
                    FROM payments 
                    WHERE note_date BETWEEN ? AND ? 
                    AND is_delete = 0
                    AND (category_pid IS NULL OR category_pid = 0)
                    ORDER BY note_date DESC
                """
                cursor.execute(query, (start_date, end_date))
            else:
                parts = category_name.split('——')
                if len(parts) == 2:
                    parent_title, child_title = parts[0], parts[1]
                    query = """
                        SELECT p.id, p.note_date, p.title, p.remark, p.money, p.create_time 
                        FROM payments p
                        LEFT JOIN pay_categorys pc_p ON p.category_pid = pc_p.id
                        LEFT JOIN pay_categorys pc_c ON p.category_cid = pc_c.id
                        WHERE p.note_date BETWEEN ? AND ? 
                        AND p.is_delete = 0
                        AND pc_p.title = ? AND pc_c.title = ?
                        ORDER BY p.note_date DESC
                    """
                    cursor.execute(query, (start_date, end_date, parent_title, child_title))
                else:
                    parent_title = parts[0]
                    query = """
                        SELECT p.id, p.note_date, p.title, p.remark, p.money, p.create_time 
                        FROM payments p
                        LEFT JOIN pay_categorys pc_p ON p.category_pid = pc_p.id
                        LEFT JOIN pay_categorys pc_c ON p.category_cid = pc_c.id
                        WHERE p.note_date BETWEEN ? AND ? 
                        AND p.is_delete = 0
                        AND pc_p.title = ? AND pc_c.id IS NULL
                        ORDER BY p.note_date DESC
                    """
                    cursor.execute(query, (start_date, end_date, parent_title))
            results = cursor.fetchall()
            return results
        except sqlite3.Error as e:
            print(f"获取分类详情错误: {e}")
            return None
        finally:
            conn.close()
    
    def get_monthly_expenses_by_category_for_year(self, year, month):
        """获取指定月份按分类的支出数据（年度堆叠图：父——子标签）"""
        conn = self.get_db_connection()
        if not conn:
            return None
        try:
            _, last_day = calendar.monthrange(year, month)
            start_date = f"{year}-{month:02d}-01"
            end_date = f"{year}-{month:02d}-{last_day:02d}"
            cursor = conn.cursor()
            query = """
                SELECT 
                    CASE 
                        WHEN pc_c.title IS NOT NULL AND pc_c.title <> '' THEN pc_p.title || '——' || pc_c.title
                        ELSE COALESCE(pc_p.title, '未分类')
                    END AS category_label,
                    SUM(p.money) AS total_amount
                FROM payments p
                LEFT JOIN pay_categorys pc_p ON p.category_pid = pc_p.id
                LEFT JOIN pay_categorys pc_c ON p.category_cid = pc_c.id
                WHERE p.note_date BETWEEN ? AND ? 
                AND p.is_delete = 0
                GROUP BY category_label
                ORDER BY total_amount DESC
            """
            cursor.execute(query, (start_date, end_date))
            results = cursor.fetchall()
            return results
        except sqlite3.Error as e:
            print(f"获取月度分类支出错误: {e}")
            return None
        finally:
            conn.close()
    
    def get_all_categories_for_year(self, year):
        """获取指定年份所有出现过的分类"""
        categories = set()
        
        for month in range(1, 13):
            data = self.get_monthly_expenses_by_category_for_year(year, month)
            if data:
                for category, _ in data:
                    categories.add(category)
        
        return sorted(list(categories))
    
    def get_monthly_category_expenses(self, year, categories):
        """获取每月各分类的支出数据"""
        monthly_data = {}
        
        for month in range(1, 13):
            month_data = {cat: 0 for cat in categories}
            data = self.get_monthly_expenses_by_category_for_year(year, month)
            
            if data:
                for category, amount in data:
                    if category in month_data:
                        month_data[category] = amount
            
            monthly_data[month] = month_data
        
        return monthly_data
    
    def get_monthly_category_details(self, year, month, category):
        """获取指定月份指定分类的详细支出记录（支持父——子标签）"""
        conn = self.get_db_connection()
        if not conn:
            return None
        try:
            _, last_day = calendar.monthrange(year, month)
            start_date = f"{year}-{month:02d}-01"
            end_date = f"{year}-{month:02d}-{last_day:02d}"
            cursor = conn.cursor()
            if category == '未分类':
                query = """
                    SELECT id, note_date, title, remark, money, create_time 
                    FROM payments 
                    WHERE note_date BETWEEN ? AND ? 
                    AND is_delete = 0
                    AND (category_pid IS NULL OR category_pid = 0)
                    ORDER BY note_date DESC
                """
                cursor.execute(query, (start_date, end_date))
            else:
                parts = category.split('——')
                if len(parts) == 2:
                    parent_title, child_title = parts[0], parts[1]
                    query = """
                        SELECT p.id, p.note_date, p.title, p.remark, p.money, p.create_time 
                        FROM payments p
                        LEFT JOIN pay_categorys pc_p ON p.category_pid = pc_p.id
                        LEFT JOIN pay_categorys pc_c ON p.category_cid = pc_c.id
                        WHERE p.note_date BETWEEN ? AND ? 
                        AND p.is_delete = 0
                        AND pc_p.title = ? AND pc_c.title = ?
                        ORDER BY p.note_date DESC
                    """
                    cursor.execute(query, (start_date, end_date, parent_title, child_title))
                else:
                    parent_title = parts[0]
                    query = """
                        SELECT p.id, p.note_date, p.title, p.remark, p.money, p.create_time 
                        FROM payments p
                        LEFT JOIN pay_categorys pc_p ON p.category_pid = pc_p.id
                        LEFT JOIN pay_categorys pc_c ON p.category_cid = pc_c.id
                        WHERE p.note_date BETWEEN ? AND ? 
                        AND p.is_delete = 0
                        AND pc_p.title = ? AND pc_c.id IS NULL
                        ORDER BY p.note_date DESC
                    """
                    cursor.execute(query, (start_date, end_date, parent_title))
            return cursor.fetchall()
        except sqlite3.Error as e:
            print(f"获取月度分类详情错误: {e}")
            return None
        finally:
            conn.close()
    
    def on_bar_hover(self, event, bars, categories, year, tooltip, monthly_data):
        """堆叠柱状图的鼠标悬停事件（优化版本：优先使用contains方法，确保支出柱正常显示信息）"""
        if event.inaxes is None or event.xdata is None or event.ydata is None:
            # 不做任何操作，让其他事件处理器有机会处理
            return

        # 首先检查是否悬停在支出柱的x坐标范围内（考虑向左偏移0.2）
        # 支出柱的x范围：[month_index - 0.2 - 0.2, month_index - 0.2 + 0.2] = [month_index - 0.4, month_index]
        month_index = int(round(event.xdata + 0.2)) - 1  # 计算月份索引(0-11)
        if month_index < 0 or month_index > 11:
            # 不在支出柱范围内，不做任何操作
            return
        
        # 计算月份和支出柱中心位置
        month = month_index + 1
        bar_center = month_index - 0.2  # 支出柱中心位置
        
        # 检查x坐标是否在支出柱范围内
        if not (bar_center - 0.2 <= event.xdata <= bar_center + 0.2):
            # 不在支出柱范围内，不做任何操作
            return

        # 优化的矩形contains检测：直接遍历所有支出柱矩形
        hit_found = False
        for i, bar_group in enumerate(bars):
            for rect in bar_group:
                # 检查矩形是否包含鼠标位置
                contains, _ = rect.contains(event)
                if contains:
                    # 找到命中的矩形
                    hit_found = True
                    hit_category = categories[i]
                    hit_top = rect.get_y() + rect.get_height()
                    amount = monthly_data.get(month, {}).get(hit_category, 0)
                    
                    # 获取详细信息
                    details = self.get_monthly_category_details(year, month, hit_category) or []
                    tooltip_text = f"{month}月 {hit_category} 支出\n总计: {amount:.2f}元\n"
                    if details:
                        max_display = 5
                        for record in details[:max_display]:
                            note_date = record[1]
                            title = record[2]
                            money = record[4]
                            parts = note_date.split('-')
                            short_date = f"{parts[1]}月{parts[2]}日" if len(parts) >= 3 else note_date
                            tooltip_text += f"{short_date} {title} {money}元\n"
                        if len(details) > max_display:
                            tooltip_text += f"...等{len(details)}条记录"
                    else:
                        tooltip_text += "暂无明细记录"
                    
                    # 设置并显示tooltip
                    tooltip.set_text(tooltip_text)
                    tooltip.xy = (bar_center, hit_top)  # 提示框位置在柱子中心顶部
                    tooltip.set_visible(True)
                    
                    # 更改鼠标指针
                    if self.current_canvas:
                        self.current_canvas.get_tk_widget().config(cursor="hand2")
                        self.current_canvas.draw_idle()
                    
                    return  # 找到命中后立即返回，避免后续处理

        # 如果没有找到命中的矩形，隐藏tooltip并重置鼠标指针
        if not hit_found:
            tooltip.set_visible(False)
            if self.current_canvas:
                self.current_canvas.get_tk_widget().config(cursor="arrow")
                self.current_canvas.draw_idle()

    def get_monthly_income_total(self, year, month):
        """获取指定月份收入总额"""
        conn = self.get_db_connection()
        if not conn:
            return 0
        try:
            _, last_day = calendar.monthrange(year, month)
            start_date = f"{year}-{month:02d}-01"
            end_date = f"{year}-{month:02d}-{last_day:02d}"
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT COALESCE(SUM(money), 0) FROM incomes
                WHERE note_date BETWEEN ? AND ? AND is_delete = 0
                """,
                (start_date, end_date),
            )
            result = cursor.fetchone()
            return result[0] if result and result[0] is not None else 0
        except sqlite3.Error as e:
            print(f"获取月收入总额错误: {e}")
            return 0
        finally:
            conn.close()

    def get_monthly_expense_total(self, year, month):
        """获取指定月份支出总额"""
        conn = self.get_db_connection()
        if not conn:
            return 0
        try:
            _, last_day = calendar.monthrange(year, month)
            start_date = f"{year}-{month:02d}-01"
            end_date = f"{year}-{month:02d}-{last_day:02d}"
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT COALESCE(SUM(money), 0) FROM payments
                WHERE note_date BETWEEN ? AND ? AND is_delete = 0
                """,
                (start_date, end_date),
            )
            result = cursor.fetchone()
            return result[0] if result and result[0] is not None else 0
        except sqlite3.Error as e:
            print(f"获取月支出总额错误: {e}")
            return 0
        finally:
            conn.close()

    def get_monthly_income_details(self, year, month):
        """获取指定月份收入详细记录"""
        conn = self.get_db_connection()
        if not conn:
            return []
        try:
            _, last_day = calendar.monthrange(year, month)
            start_date = f"{year}-{month:02d}-01"
            end_date = f"{year}-{month:02d}-{last_day:02d}"
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, note_date, title, remark, money, create_time
                FROM incomes
                WHERE note_date BETWEEN ? AND ? AND is_delete = 0
                ORDER BY note_date DESC
                """,
                (start_date, end_date),
            )
            return cursor.fetchall()
        except sqlite3.Error as e:
            print(f"获取收入明细错误: {e}")
            return []
        finally:
            conn.close()
            
    def get_monthly_expense_details(self, year, month):
        """获取指定月份支出详细记录"""
        conn = self.get_db_connection()
        if not conn:
            return []
        try:
            _, last_day = calendar.monthrange(year, month)
            start_date = f"{year}-{month:02d}-01"
            end_date = f"{year}-{month:02d}-{last_day:02d}"
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, note_date, title, remark, money, create_time
                FROM payments
                WHERE note_date BETWEEN ? AND ? AND is_delete = 0
                ORDER BY note_date DESC
                """,
                (start_date, end_date),
            )
            return cursor.fetchall()
        except sqlite3.Error as e:
            print(f"获取支出明细错误: {e}")
            return []
        finally:
            conn.close()

    def get_yearly_income_totals(self, year):
        """获取指定年份各月收入总额列表（长度12）"""
        totals = []
        for month in range(1, 13):
            totals.append(self.get_monthly_income_total(year, month))
        return totals

    def generate_monthly_bar_chart(self):
        """生成月度支出/收入柱状图（堆叠显示：总支出和总收入两根柱子）"""
        try:
            year = int(self.year_var.get())
            month = int(self.month_var.get())
            self.status_label.config(text=f"查询{year}年{month}月数据...")
        except ValueError:
            messagebox.showerror("输入错误", "请输入有效的年份和月份")
            return
        
        # 获取支出分类数据
        expense_categories_data = self.get_monthly_expenses_by_category(year, month)
        if expense_categories_data is None:
            messagebox.showerror("查询错误", "数据查询失败")
            self.status_label.config(text="查询失败")
            return
        
        # 获取收入分类数据（假设收入也有分类，这里先使用月度收入明细数据）
        income_details = self.get_monthly_income_details(year, month)
        # 按项目标题分组收入数据（简化处理，实际可能需要专门的收入分类表）
        income_by_category = {}
        for record in income_details:
            title = record[2]
            money = record[4]
            if title in income_by_category:
                income_by_category[title] += money
            else:
                income_by_category[title] = money
        
        # 准备堆叠柱状图数据
        expense_categories = [item[0] for item in expense_categories_data]
        expense_amounts = [item[1] for item in expense_categories_data]
        
        income_categories = list(income_by_category.keys())
        income_amounts = list(income_by_category.values())
        
        # 计算总额
        expense_total = self.get_monthly_expense_total(year, month)
        income_total = self.get_monthly_income_total(year, month)
        
        # 清理图表区域
        for widget in self.chart_frame.winfo_children():
            widget.destroy()
        
        # 创建图表
        fig = Figure(figsize=(4, 4), dpi=100)
        ax = fig.add_subplot(111)
        self.current_fig = fig
        
        # 设置柱子宽度（适当减小）
        bar_width = 0.4
        
        # 支出堆叠柱状图
        expense_bottom = 0
        expense_bars = []
        expense_colors = plt.cm.tab20c.colors[:len(expense_categories)]
        for i, (category, amount) in enumerate(zip(expense_categories, expense_amounts)):
            bar = ax.bar(0, amount, bottom=expense_bottom, width=bar_width, 
                        color=expense_colors[i], label=category, zorder=2)
            expense_bars.append(bar)
            expense_bottom += amount
        
        # 收入堆叠柱状图
        income_bottom = 0
        income_bars = []
        income_colors = plt.cm.tab20b.colors[:len(income_categories)]
        for i, (category, amount) in enumerate(zip(income_categories, income_amounts)):
            bar = ax.bar(1, amount, bottom=income_bottom, width=bar_width, 
                        color=income_colors[i], label=category, zorder=2)
            income_bars.append(bar)
            income_bottom += amount
        
        # 设置坐标轴
        ax.set_xticks([0, 1])
        ax.set_xticklabels(['总支出', '总收入'])
        ax.set_xlabel('收支类型')
        ax.set_ylabel('金额 (元)')
        ax.set_title(f'{year}年{month}月收支堆叠柱状图\n（悬停查看各领域明细）')
        
        # 添加网格
        ax.grid(axis='y', alpha=0.3, zorder=1)
        
        # 添加总额标签
        ax.text(0, expense_total, f"{expense_total:.0f}", ha="center", va="bottom", fontsize=9, color="tab:red")
        ax.text(1, income_total, f"{income_total:.0f}", ha="center", va="bottom", fontsize=9, color="tab:green")
        
        # 调整布局
        fig.tight_layout()
        
        # 创建画布
        canvas = FigureCanvasTkAgg(fig, self.chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tb.BOTH, expand=False)
        self.current_canvas = canvas
        
        # 创建悬停提示
        tooltip = ax.annotate('', xy=(0, 0), xytext=(0, 0),
                              bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="gray", alpha=0.9),
                              arrowprops=dict(arrowstyle="->"), va="bottom", ha="left")
        tooltip.set_visible(False)
        
        # 保存数据用于悬停事件
        self.current_expense_data = {"categories": expense_categories, "bars": expense_bars, "year": year, "month": month}
        self.current_income_data = {"categories": income_categories, "bars": income_bars, "year": year, "month": month}
        
        # 绑定悬停事件
        canvas.mpl_connect('motion_notify_event', lambda e: self.on_stacked_bar_hover(e, tooltip))
        
        self.status_label.config(text=f"已生成{year}年{month}月收支堆叠柱状图")
    
    def on_stacked_bar_hover(self, event, tooltip):
        """堆叠柱状图悬停事件处理，显示各领域款项细则"""
        if event.inaxes is None:
            tooltip.set_visible(False)
            if self.current_canvas:
                self.current_canvas.get_tk_widget().config(cursor="arrow")
                self.current_canvas.draw_idle()
            return
        
        # 检查是否悬停在支出堆叠柱上
        expense_data = getattr(self, 'current_expense_data', None)
        if expense_data:
            expense_bars = expense_data['bars']
            expense_categories = expense_data['categories']
            year = expense_data['year']
            month = expense_data['month']
            
            for i, bar_group in enumerate(expense_bars):
                for rect in bar_group:
                    contains, _ = rect.contains(event)
                    if contains:
                        category = expense_categories[i]
                        details = self.get_monthly_category_details(year, month, category)
                        amount = sum([item[1] for item in self.get_monthly_expenses_by_category(year, month) if item[0] == category])
                        
                        tooltip_text = f"{category} - 支出\n总计: {amount:.2f}元\n"
                        if details:
                            max_display = 5
                            for record in details[:max_display]:
                                note_date = record[1]
                                title = record[2]
                                money = record[4]
                                parts = note_date.split('-')
                                short_date = f"{parts[1]}月{parts[2]}日" if len(parts) >= 3 else note_date
                                tooltip_text += f"{short_date} {title} {money}元\n"
                            if len(details) > max_display:
                                tooltip_text += f"...等{len(details)}条记录"
                        else:
                            tooltip_text += "暂无详细记录"
                        
                        tooltip.set_text(tooltip_text)
                        
                        # 设置tooltip的锚点位置（鼠标位置）
                        tooltip.xy = (event.xdata, event.ydata)
                        
                        # 计算合适的提示框位置，确保在图表区域内显示
                        # 获取当前axes的坐标范围
                        xlim = event.inaxes.get_xlim()
                        ylim = event.inaxes.get_ylim()
                        
                        # 计算文本框理想位置（相对于锚点的偏移）
                        # 默认显示在右侧上方
                        x_offset = 10
                        y_offset = 10
                        
                        # 如果鼠标靠近右侧，提示框显示在左侧
                        if event.xdata > xlim[0] + (xlim[1] - xlim[0]) * 0.7:
                            x_offset = -200  # 左侧显示，留出足够空间
                        
                        # 如果鼠标靠近顶部，提示框显示在下方
                        if event.ydata > ylim[0] + (ylim[1] - ylim[0]) * 0.75:
                            y_offset = -150  # 向下显示，留出足够空间
                        
                        # 设置提示框相对于锚点的位置
                        tooltip.xytext = (x_offset, y_offset)
                        
                        # 设置文本框的bbox参数以确保美观
                        tooltip.set_bbox(dict(boxstyle="round,pad=0.3", fc="white", ec="gray", alpha=0.9))
                        
                        tooltip.set_visible(True)
                        if self.current_canvas:
                            self.current_canvas.get_tk_widget().config(cursor="hand2")
                            self.current_canvas.draw_idle()
                        return
        
        # 检查是否悬停在收入堆叠柱上
        income_data = getattr(self, 'current_income_data', None)
        if income_data:
            income_bars = income_data['bars']
            income_categories = income_data['categories']
            year = income_data['year']
            month = income_data['month']
            
            for i, bar_group in enumerate(income_bars):
                for rect in bar_group:
                    contains, _ = rect.contains(event)
                    if contains:
                        category = income_categories[i]
                        # 获取该收入类别的详细记录
                        income_details = [record for record in self.get_monthly_income_details(year, month) if record[2] == category]
                        amount = sum([record[4] for record in income_details])
                        
                        tooltip_text = f"{category} - 收入\n总计: {amount:.2f}元\n"
                        if income_details:
                            max_display = 5
                            for record in income_details[:max_display]:
                                note_date = record[1]
                                title = record[2]
                                money = record[4]
                                parts = note_date.split('-')
                                short_date = f"{parts[1]}月{parts[2]}日" if len(parts) >= 3 else note_date
                                tooltip_text += f"{short_date} {title} {money}元\n"
                            if len(income_details) > max_display:
                                tooltip_text += f"...等{len(income_details)}条记录"
                        else:
                            tooltip_text += "暂无详细记录"
                        
                        tooltip.set_text(tooltip_text)
                        
                        # 设置tooltip的锚点位置（鼠标位置）
                        tooltip.xy = (event.xdata, event.ydata)
                        
                        # 计算合适的提示框位置，确保在图表区域内显示
                        # 获取当前axes的坐标范围
                        xlim = event.inaxes.get_xlim()
                        ylim = event.inaxes.get_ylim()
                        
                        # 计算文本框理想位置（相对于锚点的偏移）
                        # 默认显示在右侧上方
                        x_offset = 10
                        y_offset = 10
                        
                        # 如果鼠标靠近右侧，提示框显示在左侧
                        if event.xdata > xlim[0] + (xlim[1] - xlim[0]) * 0.7:
                            x_offset = -200  # 左侧显示，留出足够空间
                        
                        # 如果鼠标靠近顶部，提示框显示在下方
                        if event.ydata > ylim[0] + (ylim[1] - ylim[0]) * 0.75:
                            y_offset = -150  # 向下显示，留出足够空间
                        
                        # 设置提示框相对于锚点的位置
                        tooltip.xytext = (x_offset, y_offset)
                        
                        # 设置文本框的bbox参数以确保美观
                        tooltip.set_bbox(dict(boxstyle="round,pad=0.3", fc="white", ec="gray", alpha=0.9))
                        
                        tooltip.set_visible(True)
                        if self.current_canvas:
                            self.current_canvas.get_tk_widget().config(cursor="hand2")
                            self.current_canvas.draw_idle()
                        return
        
        # 不在任何柱子上
        tooltip.set_visible(False)
        if self.current_canvas:
            self.current_canvas.get_tk_widget().config(cursor="arrow")
            self.current_canvas.draw_idle()

    def on_monthly_bar_hover(self, event, bars, categories, year, month, tooltip):
        """月度柱状图悬停，显示分类部分明细或收入明细与净收入"""
        if event.inaxes is None:
            tooltip.set_visible(False)
            if self.current_canvas:
                self.current_canvas.get_tk_widget().config(cursor="arrow")
                self.current_canvas.draw_idle()
            return
        for idx, rect in enumerate(bars.patches):
            contains, _ = rect.contains(event)
            if contains:
                category = categories[idx]
                if category == "总收入":
                    income_details = self.get_monthly_income_details(year, month)
                    income_total = self.get_monthly_income_total(year, month)
                    expense_total = self.get_monthly_expense_total(year, month)
                    net_income = income_total - expense_total
                    text = f"{year}年{month}月 总收入\n总计: {income_total:.2f}元\n净收入: {net_income:.2f}元\n"
                    if income_details:
                        max_display = 5
                        for record in income_details[:max_display]:
                            note_date = record[1]
                            title = record[2]
                            money = record[4]
                            date_parts = note_date.split('-')
                            short_date = f"{date_parts[1]}月{date_parts[2]}日" if len(date_parts) >= 3 else note_date
                            text += f"{short_date} {title} {money}元\n"
                        if len(income_details) > max_display:
                            text += f"...等{len(income_details)}条记录"
                    else:
                        text += "暂无收入记录"
                elif category == "总支出":
                    expense_details = self.get_monthly_expense_details(year, month)
                    expense_total = self.get_monthly_expense_total(year, month)
                    text = f"{year}年{month}月 总支出\n总计: {expense_total:.2f}元\n"
                    if expense_details:
                        max_display = 5
                        for record in expense_details[:max_display]:
                            note_date = record[1]
                            title = record[2]
                            money = record[4]
                            date_parts = note_date.split('-')
                            short_date = f"{date_parts[1]}月{date_parts[2]}日" if len(date_parts) >= 3 else note_date
                            text += f"{short_date} {title} {money}元\n"
                        if len(expense_details) > max_display:
                            text += f"...等{len(expense_details)}条记录"
                    else:
                        text += "暂无支出记录"
                else:
                    details = self.get_monthly_category_details(year, month, category)
                    text = f"{category}\n"
                    if details:
                        max_display = 5
                        for record in details[:max_display]:
                            note_date = record[1]
                            title = record[2]
                            money = record[4]
                            date_parts = note_date.split('-')
                            short_date = f"{date_parts[1]}月{date_parts[2]}日" if len(date_parts) >= 3 else note_date
                            text += f"{short_date} {title} {money}元\n"
                        if len(details) > max_display:
                            text += f"...等{len(details)}条记录"
                    else:
                        text += "暂无详细记录"
                tooltip.set_text(text)
                tooltip.xy = (event.xdata, event.ydata)
                tooltip.set_visible(True)
                if self.current_canvas:
                    self.current_canvas.get_tk_widget().config(cursor="hand2")
                    self.current_canvas.draw_idle()
                break
        else:
            # 不在收入柱上方时不干扰已有提示框状态
            if self.current_canvas:
                self.current_canvas.draw_idle()

    def get_yearly_category_details(self, year, category):
        """获取指定年份指定分类的详细支出记录（支持父——子标签）"""
        conn = self.get_db_connection()
        if not conn:
            return None
        try:
            start_date = f"{year}-01-01"
            end_date = f"{year}-12-31"
            cursor = conn.cursor()
            if category == '未分类':
                query = """
                    SELECT id, note_date, title, remark, money, create_time 
                    FROM payments 
                    WHERE note_date BETWEEN ? AND ? 
                    AND is_delete = 0
                    AND (category_pid IS NULL OR category_pid = 0)
                    ORDER BY note_date DESC
                """
                cursor.execute(query, (start_date, end_date))
            else:
                parts = category.split('——')
                if len(parts) == 2:
                    parent_title, child_title = parts[0], parts[1]
                    query = """
                        SELECT p.id, p.note_date, p.title, p.remark, p.money, p.create_time 
                        FROM payments p
                        LEFT JOIN pay_categorys pc_p ON p.category_pid = pc_p.id
                        LEFT JOIN pay_categorys pc_c ON p.category_cid = pc_c.id
                        WHERE p.note_date BETWEEN ? AND ? 
                        AND p.is_delete = 0
                        AND pc_p.title = ? AND pc_c.title = ?
                        ORDER BY p.note_date DESC
                    """
                    cursor.execute(query, (start_date, end_date, parent_title, child_title))
                else:
                    parent_title = parts[0]
                    query = """
                        SELECT p.id, p.note_date, p.title, p.remark, p.money, p.create_time 
                        FROM payments p
                        LEFT JOIN pay_categorys pc_p ON p.category_pid = pc_p.id
                        LEFT JOIN pay_categorys pc_c ON p.category_cid = pc_c.id
                        WHERE p.note_date BETWEEN ? AND ? 
                        AND p.is_delete = 0
                        AND pc_p.title = ? AND pc_c.id IS NULL
                        ORDER BY p.note_date DESC
                    """
                    cursor.execute(query, (start_date, end_date, parent_title))
            return cursor.fetchall()
        except sqlite3.Error as e:
            print(f"获取年度分类细则错误: {e}")
            return None
        finally:
            conn.close()
    
    def on_yearly_income_bar_hover(self, event, income_bars, year, tooltip, monthly_data):
        """年度柱状图收入柱悬停，显示收入详情与净收入"""
        if event.inaxes is None:
            tooltip.set_visible(False)
            if self.current_canvas:
                self.current_canvas.get_tk_widget().config(cursor="arrow")
                self.current_canvas.draw_idle()
            return
        for rect in income_bars.patches:
            contains, _ = rect.contains(event)
            if contains:
                # x 位置带有偏移，round 后可得到月份索引
                month_index = int(round(rect.get_x()))
                month = month_index + 1
                income_total = self.get_monthly_income_total(year, month)
                # 从已计算的月度分类支出数据中汇总当月支出总额
                expense_total = sum(monthly_data.get(month, {}).values()) if monthly_data else 0
                net_income = income_total - expense_total
                details = self.get_monthly_income_details(year, month)
                text = f"{year}年{month}月 总收入\n总计: {income_total:.2f}元\n净收入: {net_income:.2f}元\n"
                if details:
                    max_display = 5
                    for record in details[:max_display]:
                        note_date = record[1]
                        title = record[2]
                        money = record[4]
                        parts = note_date.split('-')
                        short_date = f"{parts[1]}月{parts[2]}日" if len(parts) >= 3 else note_date
                        text += f"{short_date} {title} {money}元\n"
                    if len(details) > max_display:
                        text += f"...等{len(details)}条记录"
                else:
                    text += "暂无收入记录"
                tooltip.set_text(text)
                tooltip.xy = (event.xdata, event.ydata)
                tooltip.set_visible(True)
                if self.current_canvas:
                    self.current_canvas.get_tk_widget().config(cursor="hand2")
                    self.current_canvas.draw_idle()
                break
        else:
            tooltip.set_visible(False)
            if self.current_canvas:
                self.current_canvas.get_tk_widget().config(cursor="arrow")
                self.current_canvas.draw_idle()

    def generate_bar_chart(self):
        """生成年度支出柱状图（每月收入支出各1根堆叠柱，共24根）"""
        try:
            year = int(self.year_var.get())
            self.status_label.config(text=f"查询{year}年数据...")
        except ValueError:
            messagebox.showerror("输入错误", "请输入有效的年份")
            return
        
        # 清理图表区域
        for widget in self.chart_frame.winfo_children():
            widget.destroy()
        
        # 创建图表
        fig = Figure(figsize=(4, 4), dpi=100)
        ax = fig.add_subplot(111)
        self.current_fig = fig
        
        # 准备数据结构
        monthly_expense_data = {}
        monthly_income_data = {}
        all_expense_categories = set()
        all_income_categories = set()
        
        # 获取12个月的数据
        for month in range(1, 13):
            # 获取该月支出分类数据
            expense_categories_data = self.get_monthly_expenses_by_category(year, month)
            if expense_categories_data:
                monthly_expense_data[month] = {}
                for category, amount in expense_categories_data:
                    monthly_expense_data[month][category] = amount
                    all_expense_categories.add(category)
            else:
                monthly_expense_data[month] = {}
            
            # 获取该月收入明细数据并按标题分类
            income_details = self.get_monthly_income_details(year, month)
            if income_details:
                monthly_income_data[month] = {}
                for record in income_details:
                    title = record[2]
                    money = record[4]
                    if title in monthly_income_data[month]:
                        monthly_income_data[month][title] += money
                    else:
                        monthly_income_data[month][title] = money
                    all_income_categories.add(title)
            else:
                monthly_income_data[month] = {}
        
        # 转换为列表便于处理
        all_expense_categories = list(all_expense_categories)
        all_income_categories = list(all_income_categories)
        
        # 设置颜色
        expense_colors = plt.cm.tab20c.colors[:len(all_expense_categories)]
        income_colors = plt.cm.tab20b.colors[:len(all_income_categories)]
        
        # 绘制每个月的收支柱子（每月两个柱子）
        month_positions = []
        expense_bars_by_month = {}
        income_bars_by_month = {}
        
        # 计算柱子位置（每月两个柱子，间距适当调整）
        for month in range(1, 13):
            base_pos = month - 1
            expense_pos = base_pos - 0.2  # 支出柱靠左
            income_pos = base_pos + 0.2   # 收入柱靠右
            
            # 绘制支出堆叠柱
            expense_bottom = 0
            expense_bars_by_month[month] = []
            for i, category in enumerate(all_expense_categories):
                amount = monthly_expense_data[month].get(category, 0)
                if amount > 0:  # 只绘制有金额的部分
                    bar = ax.bar(expense_pos, amount, bottom=expense_bottom, width=0.35,
                                color=expense_colors[i], label=category if month == 1 else "", zorder=2)
                    expense_bars_by_month[month].append((category, bar))
                    expense_bottom += amount
            
            # 绘制收入堆叠柱
            income_bottom = 0
            income_bars_by_month[month] = []
            for i, category in enumerate(all_income_categories):
                amount = monthly_income_data[month].get(category, 0)
                if amount > 0:  # 只绘制有金额的部分
                    bar = ax.bar(income_pos, amount, bottom=income_bottom, width=0.35,
                                color=income_colors[i], label=category if month == 1 else "", zorder=2)
                    income_bars_by_month[month].append((category, bar))
                    income_bottom += amount
            
            # 添加总额标签
            if expense_bottom > 0:
                ax.text(expense_pos, expense_bottom, f"{expense_bottom:.0f}",
                        ha="center", va="bottom", fontsize=8, color="tab:red")
            if income_bottom > 0:
                ax.text(income_pos, income_bottom, f"{income_bottom:.0f}",
                        ha="center", va="bottom", fontsize=8, color="tab:green")
        
        # 设置坐标轴
        ax.set_xticks(range(12))
        ax.set_xticklabels([f"{m}月" for m in range(1, 13)])
        ax.set_xlabel('月份')
        ax.set_ylabel('金额 (元)')
        ax.set_title(f'{year}年各月收支柱状图\n（每月左侧为支出，右侧为收入，悬停查看明细）')
        
        # 添加网格
        ax.grid(axis='y', alpha=0.3, zorder=1)
        
        # 添加图例（只显示唯一的图例项）
        handles, labels = ax.get_legend_handles_labels()
        by_label = dict(zip(labels, handles))
        # 只显示前10个分类，避免图例过长
        if len(by_label) > 10:
            limited_by_label = {k: by_label[k] for k in list(by_label.keys())[:10]}
            ax.legend(limited_by_label.values(), limited_by_label.keys(), loc='upper right', ncol=2, fontsize=7)
            ax.text(0.5, -0.15, "注：仅显示前10个分类", ha='center', transform=ax.transAxes, fontsize=7, style='italic')
        else:
            ax.legend(by_label.values(), by_label.keys(), loc='upper right', ncol=2, fontsize=7)
        
        # 调整布局
        fig.tight_layout(rect=[0, 0, 1, 0.95])  # 留出底部空间
        
        # 创建画布
        canvas = FigureCanvasTkAgg(fig, self.chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tb.BOTH, expand=False)
        self.current_canvas = canvas
        
        # 创建悬停提示
        tooltip = ax.annotate('', xy=(0, 0), xytext=(10, 10),
                              bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="gray", alpha=0.9),
                              arrowprops=dict(arrowstyle="->"), va="bottom", ha="left")
        tooltip.set_visible(False)
        
        # 保存数据用于悬停事件
        self.yearly_chart_data = {
            'year': year,
            'expense_data': monthly_expense_data,
            'income_data': monthly_income_data,
            'expense_bars': expense_bars_by_month,
            'income_bars': income_bars_by_month
        }
        
        # 绑定悬停事件
        canvas.mpl_connect('motion_notify_event', lambda e: self.on_yearly_stacked_bar_hover(e, tooltip))
        
        self.status_label.config(text=f"已生成{year}年各月收支柱状图")
        
    def on_yearly_stacked_bar_hover(self, event, tooltip):
        """年度堆叠柱状图悬停事件处理，显示各月各类别的收支明细"""
        if event.inaxes is None:
            tooltip.set_visible(False)
            if self.current_canvas:
                self.current_canvas.get_tk_widget().config(cursor="arrow")
                self.current_canvas.draw_idle()
            return
        
        # 获取图表数据
        chart_data = getattr(self, 'yearly_chart_data', None)
        if not chart_data:
            return
        
        year = chart_data['year']
        expense_bars = chart_data['expense_bars']
        income_bars = chart_data['income_bars']
        
        # 检查是否悬停在支出柱子上
        for month, category_bars in expense_bars.items():
            for category, bar in category_bars:
                for rect in bar:
                    contains, _ = rect.contains(event)
                    if contains:
                        # 获取该月该分类的详细记录
                        details = self.get_monthly_category_details(year, month, category)
                        amount = sum([item[1] for item in self.get_monthly_expenses_by_category(year, month) if item[0] == category])
                        
                        tooltip_text = f"{year}年{month}月 - {category}\n总计: {amount:.2f}元\n"
                        if details:
                            max_display = 5
                            for record in details[:max_display]:
                                note_date = record[1]
                                title = record[2]
                                money = record[4]
                                parts = note_date.split('-')
                                short_date = f"{parts[1]}月{parts[2]}日" if len(parts) >= 3 else note_date
                                tooltip_text += f"{short_date} {title} {money}元\n"
                            if len(details) > max_display:
                                tooltip_text += f"...等{len(details)}条记录"
                        else:
                            tooltip_text += "暂无详细记录"
                        
                        tooltip.set_text(tooltip_text)
                        tooltip.xy = (event.xdata, event.ydata)
                        tooltip.set_visible(True)
                        if self.current_canvas:
                            self.current_canvas.get_tk_widget().config(cursor="hand2")
                            self.current_canvas.draw_idle()
                        return
        
        # 检查是否悬停在收入柱子上
        for month, category_bars in income_bars.items():
            for category, bar in category_bars:
                for rect in bar:
                    contains, _ = rect.contains(event)
                    if contains:
                        # 获取该月该收入类别的详细记录
                        income_details = [record for record in self.get_monthly_income_details(year, month) if record[2] == category]
                        amount = sum([record[4] for record in income_details])
                        
                        tooltip_text = f"{year}年{month}月 - {category}\n总计: {amount:.2f}元\n"
                        if income_details:
                            max_display = 5
                            for record in income_details[:max_display]:
                                note_date = record[1]
                                title = record[2]
                                money = record[4]
                                parts = note_date.split('-')
                                short_date = f"{parts[1]}月{parts[2]}日" if len(parts) >= 3 else note_date
                                tooltip_text += f"{short_date} {title} {money}元\n"
                            if len(income_details) > max_display:
                                tooltip_text += f"...等{len(income_details)}条记录"
                        else:
                            tooltip_text += "暂无详细记录"
                        
                        tooltip.set_text(tooltip_text)
                        tooltip.xy = (event.xdata, event.ydata)
                        tooltip.set_visible(True)
                        if self.current_canvas:
                            self.current_canvas.get_tk_widget().config(cursor="hand2")
                            self.current_canvas.draw_idle()
                        return
        
        # 不在任何柱子上
        tooltip.set_visible(False)
        if self.current_canvas:
            self.current_canvas.get_tk_widget().config(cursor="arrow")
            self.current_canvas.draw_idle()


    def generate_yearly_pie_chart(self):
        """生成年度支出饼图（按父——子分类）"""
        try:
            year = int(self.year_var.get())
            self.status_label.config(text=f"查询{year}年数据...")
        except ValueError:
            messagebox.showerror("输入错误", "请输入有效的年份")
            return
        if not self.test_database_connection():
            messagebox.showerror("数据库错误", "无法连接数据库或没有数据")
            return
        data = self.get_yearly_expenses_by_category(year)
        if data is None:
            messagebox.showerror("查询错误", "数据查询失败")
            self.status_label.config(text="查询失败")
            return
        if not data:
            messagebox.showinfo("无数据", f"{year}年没有支出数据")
            self.status_label.config(text="没有找到数据")
            return
        self.current_category_names = [item[0] for item in data]
        amounts = [item[1] for item in data]
        for widget in self.chart_frame.winfo_children():
            widget.destroy()
        fig = Figure(figsize=(4, 4), dpi=100)
        ax = fig.add_subplot(111)
        self.current_fig = fig
        # 计算百分比，为内部标签做准备
        total_amount = sum(amounts) if amounts else 0
        # 定义显示在内部的标签和不显示的标签
        labels = []
        autopct_list = []
        self.visible_labels = []  # 用于记录哪些标签显示在内部
        
        # 角度阈值，用于判断是否足够宽以显示文本（大约10度为最小宽度）
        MIN_ANGLE_WIDTH = 10.0
        
        # 准备标签和百分比显示
        for i, (category, amount) in enumerate(zip(self.current_category_names, amounts)):
            # 计算该部分的角度范围
            angle_width = (amount / total_amount) * 360 if total_amount > 0 else 0
            
            # 如果角度宽度足够大，显示分类名和百分比
            if angle_width >= MIN_ANGLE_WIDTH:
                labels.append(category)
                autopct_list.append('%.1f%%' % (amount / total_amount * 100 if total_amount > 0 else 0))
                self.visible_labels.append(True)
            else:
                # 对于过窄的部分，不在内部显示标签，在悬停时显示
                labels.append("")  # 空标签
                autopct_list.append("")  # 空百分比
                self.visible_labels.append(False)
        
        # 绘制饼图，将标签放在内部
        wedges, texts, autotexts = ax.pie(
            amounts,
            labels=labels,
            autopct=lambda p: autopct_list[next(i for i, v in enumerate(autopct_list) if v == f'{p:.1f}%')] if f'{p:.1f}%' in autopct_list else '',
            startangle=90,
            wedgeprops={'edgecolor': 'w', 'linewidth': 1},
            textprops={'fontsize': 10, 'ha': 'center', 'va': 'center'},
            labeldistance=0.7  # 标签位置在饼图内部
        )
        
        # 调整自动百分比文本的样式
        for autotext in autotexts:
            autotext.set_fontsize(8)
            autotext.set_color('white')
            # 确保百分比文本在深色背景下也清晰可见
            autotext.set_bbox(dict(boxstyle="round,pad=0.2", fc="black", ec="none", alpha=0.3))
        
        # 为没有内部标签的部分，确保悬停时能正常显示信息
        self.narrow_segments = [i for i, visible in enumerate(self.visible_labels) if not visible]
        ax.set_title(f"{year}年支出分类占比\n（悬停查看明细，点击打开详情）", fontsize=16)
        tooltip = ax.annotate('', xy=(0.5, 0.5), xytext=(0.5, 0.5),
                               bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="gray", alpha=0.9),
                               arrowprops=dict(arrowstyle="->"), va="center", ha="center")
        tooltip.set_visible(False)
        canvas = FigureCanvasTkAgg(fig, self.chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tb.BOTH, expand=False)
        self.current_canvas = canvas
        canvas.mpl_connect('motion_notify_event', lambda event: self.on_pie_hover_yearly(event, wedges, tooltip, year))
        canvas.mpl_connect('button_press_event', lambda event: self.on_pie_click_yearly(event, wedges, year))
        self.status_label.config(text=f"已生成{year}年支出饼图")

    def generate_pie_chart(self):
        """生成月度支出饼图（按父——子分类，含悬停与弹窗）"""
        try:
            year = int(self.year_var.get())
            month = int(self.month_var.get())
            self.status_label.config(text=f"查询{year}年{month}月数据...")
        except ValueError:
            messagebox.showerror("输入错误", "请输入有效的年份和月份")
            return

        if not self.test_database_connection():
            messagebox.showerror("数据库错误", "无法连接数据库或没有数据")
            return

        data = self.get_monthly_expenses_by_category(year, month)
        if data is None:
            messagebox.showerror("查询错误", "数据查询失败")
            self.status_label.config(text="查询失败")
            return
        if not data:
            messagebox.showinfo("无数据", f"{year}年{month}月没有支出数据")
            self.status_label.config(text="没有找到数据")
            return

        self.current_category_names = [item[0] for item in data]
        amounts = [item[1] for item in data]

        for widget in self.chart_frame.winfo_children():
            widget.destroy()
        
        # ✨ 等待 Tkinter 布局稳定
        self.chart_frame.update_idletasks()

        # ✅ 获取当前 chart_frame 的真实像素宽高
        frame_width = self.chart_frame.winfo_width()
        frame_height = self.chart_frame.winfo_height()

        # 若窗口尚未显示，可能仍为 1，此时给一个默认值
        if frame_width < 100 or frame_height < 100:
            frame_width, frame_height = 800, 600

        # 根据 frame 大小动态计算合适的 figsize
        fig_w = frame_width / 100     # DPI=100 时换算英寸
        fig_h = frame_height / 100


        fig = Figure(figsize=(4,4), dpi=100)
        ax = fig.add_subplot()
        self.current_fig = fig

        total_amount = sum(amounts) if amounts else 0
        labels = []
        autopct_list = []
        self.visible_labels = []
        MIN_ANGLE_WIDTH = 10.0

        for i, (category, amount) in enumerate(zip(self.current_category_names, amounts)):
            angle_width = (amount / total_amount) * 360 if total_amount > 0 else 0
            if angle_width >= MIN_ANGLE_WIDTH:
                labels.append(category)
                autopct_list.append('%.1f%%' % (amount / total_amount * 100 if total_amount > 0 else 0))
                self.visible_labels.append(True)
            else:
                labels.append("")
                autopct_list.append("")
                self.visible_labels.append(False)

        wedges, texts, autotexts = ax.pie(
            amounts,
            labels=labels,
            autopct=lambda p: autopct_list[next((i for i, v in enumerate(autopct_list) if v == f'{p:.1f}%'), None)] if f'{p:.1f}%' in autopct_list else '',
            startangle=90,
            wedgeprops={'edgecolor': 'w', 'linewidth': 1},
            textprops={'fontsize': 10, 'ha': 'center', 'va': 'center'},
            labeldistance=0.7
        )

        for autotext in autotexts:
            autotext.set_fontsize(8)
            autotext.set_color('white')
            autotext.set_bbox(dict(boxstyle="round,pad=0.2", fc="black", ec="none", alpha=0.3))

        self.narrow_segments = [i for i, visible in enumerate(self.visible_labels) if not visible]
        ax.set_title(f"{year}年{month}月支出分类占比\n（悬停查看明细，点击打开详情）", fontsize=16)

        tooltip = ax.annotate('', xy=(0.5, 0.5), xytext=(0.5, 0.5),
                               bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="gray", alpha=0.9),
                               arrowprops=dict(arrowstyle="->"), va="center", ha="center")
        tooltip.set_visible(False)

        canvas = FigureCanvasTkAgg(fig, self.chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tb.BOTH, expand=False)
        self.chart_frame.update_idletasks()
        self.current_canvas = canvas

        # 绑定悬停与点击事件（和年度版一致）
        canvas.mpl_connect('motion_notify_event', lambda event: self.on_pie_hover_monthly(event, wedges, tooltip, year, month))
        canvas.mpl_connect('button_press_event', lambda event: self.on_pie_click_monthly(event, wedges, year, month))

        self.status_label.config(text=f"已生成{year}年{month}月支出饼图")

    def on_pie_hover_monthly(self, event, wedges, tooltip, year, month):
        """月度饼图悬停显示分类名与账目摘要（与年度版一致）"""
        if event.inaxes is None:
            tooltip.set_visible(False)
            if self.current_canvas:
                self.current_canvas.draw_idle()
                self.current_canvas.get_tk_widget().config(cursor="arrow")
            return

        for i, wedge in enumerate(wedges):
            if wedge.contains_point((event.x, event.y)):
                category = self.current_category_names[i]
                details = self.get_monthly_category_details(year, month, category)
                tooltip_text = f"{category}\n"

                if details:
                    max_display = 5
                    for record in details[:max_display]:
                        note_date = record[1]
                        title = record[2]
                        money = record[4]
                        parts = note_date.split('-')
                        short_date = f"{parts[1]}月{parts[2]}日" if len(parts) >= 3 else note_date
                        tooltip_text += f"{short_date} {title} {money}元\n"
                    if len(details) > max_display:
                        tooltip_text += f"...等{len(details)}条记录"
                else:
                    tooltip_text += "暂无详细记录"

                tooltip.set_text(tooltip_text)
                tooltip.xy = (event.xdata, event.ydata)
                tooltip.set_visible(True)

                if self.current_canvas:
                    self.current_canvas.get_tk_widget().config(cursor="hand2")
                    self.current_canvas.draw_idle()
                return

        tooltip.set_visible(False)
        if self.current_canvas:
            self.current_canvas.get_tk_widget().config(cursor="arrow")
            self.current_canvas.draw_idle()

    def on_pie_click_monthly(self, event, wedges, year, month):
        """点击月度饼图打开分类详细账目弹窗"""
        if event.inaxes is None or event.button != MouseButton.LEFT:
            return
        for i, wedge in enumerate(wedges):
            if wedge.contains_point((event.x, event.y)):
                category = self.current_category_names[i]
                self.show_monthly_category_details(year, month, category)
                break

    def show_monthly_category_details(self, year, month, category_name):
        """弹窗显示月度分类账目详情"""
        details = self.get_monthly_category_details(year, month, category_name)
        window_title = f"{year}年{month}月 - {category_name} - 账目详情"
        if not details:
            messagebox.showinfo("无明细", f"{window_title}\n暂无记录")
            return

        detail_window = tk.Toplevel(self.parent)
        detail_window.title(window_title)
        detail_window.geometry("780x520")

        tb.Label(detail_window, text=window_title, font=("Microsoft YaHei", 12, "bold")).pack(pady=8)
        columns = ("id", "date", "title", "remark", "money")
        tree = tb.Treeview(detail_window, columns=columns, show='headings')
        tree.heading("id", text="ID")
        tree.heading("date", text="日期")
        tree.heading("title", text="项目")
        tree.heading("remark", text="备注")
        tree.heading("money", text="金额")
        tree.column("id", width=60)
        tree.column("date", width=120)
        tree.column("title", width=180)
        tree.column("remark", width=220)
        tree.column("money", width=80, anchor="e")

        for record in details:
            tree.insert('', 'end', values=(record[0], record[1], record[2], record[3], record[4]))

        tree.pack(fill='both', expand=True, padx=10, pady=10)

        button_frame = tb.Frame(detail_window)
        button_frame.pack(fill="x", padx=10, pady=10, anchor="center")
        tb.Button(button_frame, text="关闭", command=detail_window.destroy).pack(pady=5)





    def on_pie_hover(self, event, wedges, tooltip, year, month):
        """月度饼图悬停，显示分类名和部分明细"""
        if event.inaxes is None:
            tooltip.set_visible(False)
            if self.current_canvas:
                self.current_canvas.draw_idle()
                self.current_canvas.get_tk_widget().config(cursor="arrow")
            return
        for i, wedge in enumerate(wedges):
            if wedge.contains_point((event.x, event.y)):
                category = self.current_category_names[i]
                details = self.get_monthly_category_details(year, month, category)
                tooltip_text = f"{category}\n"
                if details:
                    max_display = 5
                    for record in details[:max_display]:
                        note_date = record[1]
                        title = record[2]
                        money = record[4]
                        parts = note_date.split('-')
                        short_date = f"{parts[1]}月{parts[2]}日" if len(parts) >= 3 else note_date
                        tooltip_text += f"{short_date} {title} {money}元\n"
                    if len(details) > max_display:
                        tooltip_text += f"...等{len(details)}条记录"
                else:
                    tooltip_text += "暂无详细记录"
                tooltip.set_text(tooltip_text)
                tooltip.xy = (event.xdata, event.ydata)
                tooltip.set_visible(True)
                if self.current_canvas:
                    self.current_canvas.get_tk_widget().config(cursor="hand2")
                    self.current_canvas.draw_idle()
                return
        tooltip.set_visible(False)
        if self.current_canvas:
            self.current_canvas.get_tk_widget().config(cursor="arrow")
            self.current_canvas.draw_idle()

    def on_pie_hover_yearly(self, event, wedges, tooltip, year):
        """年度饼图悬停，显示分类名和部分明细"""
        if event.inaxes is None:
            tooltip.set_visible(False)
            if self.current_canvas:
                self.current_canvas.draw_idle()
                self.current_canvas.get_tk_widget().config(cursor="arrow")
            return
        for i, wedge in enumerate(wedges):
            if wedge.contains_point((event.x, event.y)):
                category = self.current_category_names[i]
                details = self.get_yearly_category_details(year, category)
                
                # 检查是否为过窄部分（没有内部标签的部分）
                is_narrow = hasattr(self, 'narrow_segments') and i in self.narrow_segments
                
                # 对于过窄部分，确保分类名称显示在详细信息的第一行
                tooltip_text = f"{category}\n"
                
                if details:
                    max_display = 5
                    for record in details[:max_display]:
                        note_date = record[1]
                        title = record[2]
                        money = record[4]
                        date_parts = note_date.split('-')
                        short_date = f"{date_parts[1]}月{date_parts[2]}日" if len(date_parts) >= 3 else note_date
                        tooltip_text += f"{short_date} {title} {money}元\n"
                    if len(details) > max_display:
                        tooltip_text += f"...等{len(details)}条记录"
                else:
                    tooltip_text += "暂无详细记录"
                
                tooltip.set_text(tooltip_text)
                tooltip.xy = (event.xdata, event.ydata)
                tooltip.set_visible(True)
                if self.current_canvas:
                    self.current_canvas.get_tk_widget().config(cursor="hand2")
                    self.current_canvas.draw_idle()
                return
        tooltip.set_visible(False)
        if self.current_canvas:
            self.current_canvas.get_tk_widget().config(cursor="arrow")
            self.current_canvas.draw_idle()

    def on_pie_click_yearly(self, event, wedges, year):
        """年度饼图点击查看详细账目"""
        if event.inaxes is None or event.button != MouseButton.LEFT:
            return
        for i, wedge in enumerate(wedges):
            if wedge.contains_point((event.x, event.y)):
                category = self.current_category_names[i]
                self.show_yearly_category_details(year, category)
                break

    def show_yearly_category_details(self, year, category_name):
        """弹窗展示某年份某分类的账目细则"""
        details = self.get_yearly_category_details(year, category_name)
        window_title = f"{year}年 - {category_name} - 账目详情"
        if not details:
            messagebox.showinfo("无明细", f"{window_title}\n暂无记录")
            return
        detail_window = tk.Toplevel(self.parent)
        detail_window.title(window_title)
        detail_window.geometry("780x520")
        tb.Label(detail_window, text=window_title, font=("Microsoft YaHei", 12, "bold")).pack(pady=8)
        columns = ("id", "date", "title", "remark", "money")
        tree = tb.Treeview(detail_window, columns=columns, show='headings')
        tree.heading("id", text="ID")
        tree.heading("date", text="日期")
        tree.heading("title", text="项目")
        tree.heading("remark", text="备注")
        tree.heading("money", text="金额")
        tree.column("id", width=60)
        tree.column("date", width=120)
        tree.column("title", width=180)
        tree.column("remark", width=220)
        tree.column("money", width=80, anchor="e")
        for record in details:
            tree.insert('', 'end', values=(record[0], record[1], record[2], record[3], record[4]))
        tree.pack(fill='both', expand=True, padx=10, pady=10)
        button_frame = tb.Frame(detail_window)
        button_frame.pack(fill="x", padx=10, pady=10, anchor="center")
        tb.Button(button_frame, text="关闭", command=detail_window.destroy).pack(pady=5)


###主页部分

    def show_category_details(self, year, month, category_name):
        """显示指定分类的详细支出记录"""
        # 获取详细记录
        details = self.get_category_details(year, month, category_name)
        
        if not details:
            messagebox.showinfo("无数据", f"{category_name}分类下暂无详细记录")
            return
        
        # 创建新窗口显示详情
        detail_window = tk.Toplevel(self.parent)
        detail_window.title(f"{year}年{month}月 - {category_name}分类详细账目")
        detail_window.geometry("800x500")
        
        # 创建Treeview控件显示详细记录
        columns = ("id", "日期", "标题", "备注", "金额", "创建时间")
        tree = tb.Treeview(detail_window, columns=columns, show="headings")
        
        # 设置列宽和标题
        tree.column("id", width=50, anchor="center")
        tree.column("日期", width=100, anchor="center")
        tree.column("标题", width=200, anchor="w")
        tree.column("备注", width=250, anchor="w")
        tree.column("金额", width=100, anchor="e")
        tree.column("创建时间", width=200, anchor="center")
        
        for col in columns:
            tree.heading(col, text=col)
        
        # 添加数据行
        total_amount = 0
        for row in details:
            tree.insert("", "end", values=row)
            total_amount += row[4]  # 金额在第5个位置（索引4）
        
        # 添加滚动条
        scrollbar = tb.Scrollbar(detail_window, orient="vertical", command=tree.yview)
        tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        tree.pack(fill="both", expand=True, padx=10, pady=10)
        
        # 添加总计信息
        total_frame = tb.Frame(detail_window)
        total_frame.pack(fill="x", padx=10, pady=10, anchor="e")
        tb.Label(total_frame, text=f"总计: {total_amount:.2f} 元", font=("SimHei", 12, "bold")).pack()
        
        # 添加关闭按钮
        button_frame = tb.Frame(detail_window)
        button_frame.pack(fill="x", padx=10, pady=10, anchor="center")
        tb.Button(button_frame, text="关闭", command=detail_window.destroy).pack(pady=5)


    def get_monthly_incomes_by_category(self, year, month):
        """获取指定月份按分类的收入数据"""
        conn = self.get_db_connection()
        if not conn:
            return None
        try:
            _, last_day = calendar.monthrange(year, month)
            start_date = f"{year}-{month:02d}-01"
            end_date = f"{year}-{month:02d}-{last_day:02d}"
            cursor = conn.cursor()

            # 检查字段
            cursor.execute("SELECT * FROM incomes LIMIT 1")
            column_names = [d[0] for d in cursor.description]

            if 'category_pid' in column_names:
                query = """                    SELECT 
                        COALESCE(ic.title, '未分类') as category_name,
                        SUM(p.money) as total_amount
                    FROM incomes p
                    LEFT JOIN income_categorys ic ON p.category_pid = ic.id
                    WHERE p.note_date BETWEEN ? AND ?
                    AND p.is_delete = 0
                    GROUP BY COALESCE(ic.title, '未分类')
                    ORDER BY total_amount DESC
                """
            else:
                query = """                    SELECT '收入' as category_name, SUM(p.money) as total_amount
                    FROM incomes p
                    WHERE p.note_date BETWEEN ? AND ?
                    AND p.is_delete = 0
                    ORDER BY total_amount DESC
                """

            cursor.execute(query, (start_date, end_date))
            results = cursor.fetchall()
            return results
        except sqlite3.Error as e:
            print(f"查询收入分类出错: {e}")
            return None
        finally:
            conn.close()

    def get_income_category_details(self, year, month, category_name):
        """获取指定分类的详细收入记录"""
        conn = self.get_db_connection()
        if not conn:
            return None
        try:
            _, last_day = calendar.monthrange(year, month)
            start_date = f"{year}-{month:02d}-01"
            end_date = f"{year}-{month:02d}-{last_day:02d}"
            cursor = conn.cursor()

            # 若 incomes 表有 category_pid，则按分类筛选
            cursor.execute("SELECT * FROM incomes LIMIT 1")
            column_names = [d[0] for d in cursor.description]

            if 'category_pid' in column_names:
                query = """                    SELECT 
                        p.id, p.note_date, p.title, p.remark, p.money,
                        a.title as account, s.title as seller,
                        ic_p.title as category_p, ic_c.title as category_c,
                        m.title as member
                    FROM incomes p
                    LEFT JOIN accounts a ON p.account_id = a.id
                    LEFT JOIN sellers s ON p.seller_id = s.id
                    LEFT JOIN income_categorys ic_p ON p.category_pid = ic_p.id
                    LEFT JOIN income_categorys ic_c ON p.category_cid = ic_c.id
                    LEFT JOIN members m ON p.member_id = m.id
                    WHERE p.note_date BETWEEN ? AND ?
                    AND p.is_delete = 0
                    AND ic_p.title = ?
                    ORDER BY p.note_date DESC
                """
                cursor.execute(query, (start_date, end_date, category_name))
            else:
                query = """                    SELECT p.id, p.note_date, p.title, p.remark, p.money,
                           a.title as account, s.title as seller,
                           '' as category_p, '' as category_c,
                           m.title as member
                    FROM incomes p
                    LEFT JOIN accounts a ON p.account_id = a.id
                    LEFT JOIN sellers s ON p.seller_id = s.id
                    LEFT JOIN members m ON p.member_id = m.id
                    WHERE p.note_date BETWEEN ? AND ?
                    AND p.is_delete = 0
                    ORDER BY p.note_date DESC
                """
                cursor.execute(query, (start_date, end_date))

            return cursor.fetchall()
        except sqlite3.Error as e:
            print(f"获取收入分类详情错误: {e}")
            return None
        finally:
            conn.close()

    def get_yearly_expenses_by_category(self, year):
        """获取指定年份按分类的支出数据（父——子标签）"""
        conn = self.get_db_connection()
        if not conn:
            return None
        try:
            start_date = f"{year}-01-01"
            end_date = f"{year}-12-31"
            cursor = conn.cursor()
            query = """
                SELECT 
                    CASE 
                        WHEN pc_c.title IS NOT NULL AND pc_c.title <> '' THEN pc_p.title || '——' || pc_c.title
                        ELSE COALESCE(pc_p.title, '未分类')
                    END AS category_label,
                    SUM(p.money) AS total_amount
                FROM payments p
                LEFT JOIN pay_categorys pc_p ON p.category_pid = pc_p.id
                LEFT JOIN pay_categorys pc_c ON p.category_cid = pc_c.id
                WHERE p.note_date BETWEEN ? AND ? 
                AND p.is_delete = 0
                GROUP BY category_label
                ORDER BY total_amount DESC
            """
            cursor.execute(query, (start_date, end_date))
            return cursor.fetchall()
        except sqlite3.Error as e:
            print(f"获取年度分类支出错误: {e}")
            return None
        finally:
            conn.close()

    def render_income_pie_chart_in_parent(self, parent, year=None, month=None):
        # 主页收入分类占比饼图（与支出一致的交互）
        try:
            from matplotlib.figure import Figure
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
            import tkinter as tk
            from datetime import datetime
        except Exception as e:
            messagebox.showerror("依赖缺失", f"无法加载绘图依赖: {e}")
            return None

        # 默认年月
        if year is None or month is None:
            now = datetime.now()
            year = now.year if year is None else int(year)
            month = now.month if month is None else int(month)

        # 查询收入数据
        data = self.get_monthly_incomes_by_category(year, month)

        # 清空父容器
        for w in parent.winfo_children():
            try:
                w.destroy()
            except Exception:
                pass

        if not data:
            lbl = tb.Label(parent, text=f"{year}年{month}月暂无收入数据", anchor="center")
            lbl.pack(fill=tb.BOTH, expand=True, padx=10, pady=10)
            return None

        category_names = [row[0] for row in data]
        amounts = [row[1] for row in data]

        # 绘图（保持与支出相同风格/尺寸）
        fig = Figure(figsize=(3.2, 3.2), dpi=100)
        ax = fig.add_subplot(111)
        total = sum(amounts)
        def autopct_fmt(pct):
            val = pct * total / 100.0
            return f"{pct:.1f}%\n{val:.0f}"

        wedges, texts, autotexts = ax.pie(
            amounts,
            labels=category_names,
            autopct=autopct_fmt,
            startangle=90,
            pctdistance=0.75,
            textprops=dict(color="black", fontsize=9),
            wedgeprops=dict(width=0.45)
        )
        ax.set_title(f"{year}年{month}月收入分类占比", fontsize=12)
        ax.axis("equal")
        fig.tight_layout()

        # 鼠标悬停提示（使用通用处理函数，避免与其他图相互影响）
        tooltip = ax.annotate('', xy=(0.5, 0.5), xytext=(0.5, 0.5),
                              bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="gray", alpha=0.85),
                              arrowprops=dict(arrowstyle="->"), va="center", ha="center", fontsize=9)
        tooltip.set_visible(False)

        canvas = FigureCanvasTkAgg(fig, parent)
        canvas.draw()
        widget = canvas.get_tk_widget()
        widget.pack(padx=2, pady=2)

        # 只做悬停提示（需求未要求点击弹窗）
        canvas.mpl_connect('motion_notify_event',
            lambda e, names=category_names: self._on_hover_generic(e, wedges, tooltip, year, month, names, self.get_income_category_details))

        return canvas


    def render_pie_chart_in_parent(self, parent, year=None, month=None):
            # 在任意父容器中渲染“支出分类占比”饼图，用于主页固定展示。
            # 不依赖本类内部的 self.chart_frame / self.year_var / self.month_var 等控件。
            try:
                from matplotlib.figure import Figure
                from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
                import tkinter as tk
                from datetime import datetime
            except Exception as e:
                messagebox.showerror("依赖缺失", f"无法加载绘图依赖: {e}")
                return None

            # 默认显示当前年月
            if year is None or month is None:
                now = datetime.now()
                year = now.year if year is None else int(year)
                month = now.month if month is None else int(month)

            # 查询数据
            data = self.get_monthly_expenses_by_category(year, month)
            # 清空父容器原有内容
            for w in parent.winfo_children():
                try:
                    w.destroy()
                except Exception:
                    pass

            if not data:
                # 无数据时显示占位提示
                lbl = tb.Label(parent, text=f"{year}年{month}月暂无支出数据", anchor="center")
                lbl.pack(fill=tb.BOTH, expand=True, padx=10, pady=10)
                return None

            # 准备数据
            category_names = [row[0] for row in data]
            amounts = [row[1] for row in data]
            self.current_category_names = category_names

            # 创建并绘制饼图
            fig = Figure(figsize=(3.2, 3.2), dpi=100)
            ax = fig.add_subplot(111)
            total = sum(amounts)
            def autopct_fmt(pct):
                val = pct * total / 100.0
                return f"{pct:.1f}%\n{val:.0f}"

            wedges, texts, autotexts = ax.pie(
                amounts,
                labels=category_names,
                autopct=autopct_fmt,
                startangle=90,
                pctdistance=0.75,
                textprops=dict(color="black", fontsize=9),
                wedgeprops=dict(width=0.45)  # 环形更清爽
            )
            ax.set_title(f"{year}年{month}月支出分类占比", fontsize=12)
            ax.axis("equal")



            # 创建鼠标悬停提示框（与统计页一致的样式/内容）
            tooltip = ax.annotate('', xy=(0.5, 0.5), xytext=(0.5, 0.5),
                                bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="gray", alpha=0.85),
                                arrowprops=dict(arrowstyle="->"), va="center", ha="center", fontsize=9)
            tooltip.set_visible(False)

            # 连接事件：鼠标移动显示详情，点击打开分类明细
            if hasattr(self, "current_canvas") and self.current_canvas:
                try:
                    self.current_canvas.mpl_disconnect(self._home_hover_cid)
                except Exception:
                    pass
                try:
                    self.current_canvas.mpl_disconnect(self._home_click_cid)
                except Exception:
                    pass

            self.current_canvas = FigureCanvasTkAgg(fig, parent)
            self.current_canvas.draw()
            widget = self.current_canvas.get_tk_widget()
            # 保持 pack 与同一父容器一致
            widget.pack(padx=2, pady=2)

            self._home_hover_cid = self.current_canvas.mpl_connect('motion_notify_event',
                lambda e: self.on_hover(e, wedges, tooltip, year, month))
            self._home_click_cid = self.current_canvas.mpl_connect('button_press_event',
                lambda e: self.on_click(e, wedges, year, month))
            ## HOME_PIE_HOVER_WIRED

    def _on_hover_generic(self, event, wedges, tooltip, year, month, category_names, detail_fetcher):
        """通用的鼠标悬停事件：传入分类名列表与详情查询函数，避免不同图表相互干扰"""
        try:
            canvas = getattr(event, 'canvas', None)
        except Exception:
            canvas = None

        if event.inaxes is None:
            tooltip.set_visible(False)
            if canvas:
                try:
                    canvas.get_tk_widget().config(cursor="arrow")
                    canvas.draw_idle()
                except Exception:
                    pass
            return

        # 命中检测
        for i, wedge in enumerate(wedges):
            try:
                contains = wedge.contains_point((event.x, event.y))
            except Exception:
                contains = False
            if contains:
                category = category_names[i] if i < len(category_names) else "未知分类"
                details = None
                try:
                    details = detail_fetcher(year, month, category)
                except Exception as _e:
                    details = None

                tooltip_text = f"{category}\n"
                if details:
                    max_display = 5
                    for record in details[:max_display]:
                        note_date = record[1]
                        title = record[2]
                        money = record[4]
                        # 显示月日
                        parts = str(note_date).split('-')
                        if len(parts) >= 3:
                            short_date = f"{parts[1]}月{parts[2]}日"
                        else:
                            short_date = str(note_date)
                        tooltip_text += f"{short_date} {title} {money}元\n"
                    if len(details) > max_display:
                        tooltip_text += f"...等{len(details)}条记录"
                else:
                    tooltip_text += "暂无详细记录"

                tooltip.set_text(tooltip_text)
                tooltip.xy = (event.xdata, event.ydata)
                tooltip.set_visible(True)
                if canvas:
                    try:
                        canvas.get_tk_widget().config(cursor="hand2")
                        canvas.draw_idle()
                    except Exception:
                        pass
                return

        tooltip.set_visible(False)
        if canvas:
            try:
                canvas.get_tk_widget().config(cursor="arrow")
                canvas.draw_idle()
            except Exception:
                pass


    def on_hover(self, event, wedges, tooltip, year, month):
        """鼠标悬停事件处理函数 - 显示分类名称和详细支出记录"""
        if event.inaxes is None:
            tooltip.set_visible(False)
            if self.current_canvas:
                self.current_canvas.draw_idle()
                self.current_canvas.get_tk_widget().config(cursor="arrow")
            return
        
        # 检测鼠标是否在某个扇形区域内
        for i, wedge in enumerate(wedges):
            if wedge.contains_point((event.x, event.y)):
                category = self.current_category_names[i]
                
                # 获取该分类的详细支出记录
                details = self.get_category_details(year, month, category)
                
                # 构建提示框内容
                tooltip_text = f"{category}\n"
                if details:
                    # 最多显示前5条记录，避免提示框过长
                    max_display = 5
                    for j, record in enumerate(details[:max_display]):
                        note_date = record[1]  # 日期
                        title = record[2]  # 标题
                        money = record[4]  # 金额
                        # 格式化日期显示（只显示月日）
                        date_parts = note_date.split('-')
                        if len(date_parts) >= 3:
                            short_date = f"{date_parts[1]}月{date_parts[2]}日"
                        else:
                            short_date = note_date
                        tooltip_text += f"{short_date} {title} {money}元\n"
                    
                    # 如果记录超过5条，显示省略提示
                    if len(details) > max_display:
                        tooltip_text += f"...等{len(details)}条记录"
                else:
                    tooltip_text += "暂无详细记录"
                
                # 更新提示框内容
                tooltip.set_text(tooltip_text)
                tooltip.xy = (event.xdata, event.ydata)
                tooltip.set_visible(True)
                # 更改光标样式为手型
                if self.current_canvas:
                    self.current_canvas.get_tk_widget().config(cursor="hand2")
                    self.current_canvas.draw_idle()
                return
        
        # 鼠标不在任何扇形区域内
        tooltip.set_visible(False)
        if self.current_canvas:
            self.current_canvas.get_tk_widget().config(cursor="arrow")
            self.current_canvas.draw_idle()
    
    def on_click(self, event, wedges, year, month):
        """鼠标点击事件处理函数"""
        if event.inaxes is None or event.button != MouseButton.LEFT:
            return
        
        # 检测鼠标点击的扇形区域
        for i, wedge in enumerate(wedges):
            if wedge.contains_point((event.x, event.y)):
                category = self.current_category_names[i]
                # 显示该分类的详细支出记录
                self.show_category_details(year, month, category)
                break


    def test_database_connection(self):
        """测试数据库连接和数据"""
        print("=== 开始数据库测试 ===")
        print(f"数据库路径: {self.db_path}")
        print(f"文件存在: {os.path.exists(self.db_path)}")
        conn = self.get_db_connection()
        if not conn:
            return False
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM payments WHERE is_delete = 0")
            count = cursor.fetchone()[0]
            print(f"payments表记录数: {count}")
            return True
        except sqlite3.Error as e:
            print(f"测试查询错误: {e}")
            return False
        finally:
            conn.close()


    

    

    

