import os
import tkinter as tk
from tkinter import tb, messagebox
import sqlite3
from datetime import datetime, timedelta
import calendar
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import matplotlib.dates as mdates
from matplotlib import font_manager as fm
from matplotlib.backend_bases import MouseButton
import ttkbootstrap as tb
from ttkbootstrap.constants import *

class StatisticsFram_main(tb.Frame):
    """统计模块框架"""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        # 使用更可靠的路径计算方法
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)
        self.db_path = os.path.join(project_root, "db", "finance.db")
        self.conf_path = os.path.join(project_root, "conf")
        self.budget_file = os.path.join(self.conf_path, "budget.json")
        
        print(f"数据库路径: {self.db_path}")
        print(f"数据库文件存在: {os.path.exists(self.db_path)}")
        
        # 设置中文字体支持
        plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False
        
        # 初始化预算数据
        self.monthly_budgets = {}
        self.load_budgets()
        
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
        tb.Button(control_frame, text="生成支出饼图", 
                  command=self.generate_pie_chart).grid(row=0, column=4, padx=5, pady=5)
        tb.Button(control_frame, text="生成年度对比图", 
                  command=self.generate_bar_chart).grid(row=0, column=5, padx=5, pady=5)
        
        # 状态显示
        self.status_label = tb.Label(control_frame, text="")
        self.status_label.grid(row=0, column=6, padx=10, pady=5)
        
        # 预算设置面板
        budget_frame = tb.LabelFrame(main_frame, text="预算设置")
        budget_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 预算年份选择
        tb.Label(budget_frame, text="预算年份:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.budget_year_var = tk.StringVar(value=str(datetime.now().year))
        budget_year_combo = tb.Combobox(budget_frame, textvariable=self.budget_year_var, width=10)
        budget_year_combo['values'] = [str(y) for y in range(2020, datetime.now().year + 2)]
        budget_year_combo.grid(row=0, column=1, padx=5, pady=5)
        
        # 预算金额输入（适用于所有月份）
        tb.Label(budget_frame, text="月度预算:").grid(row=0, column=2, padx=5, pady=5, sticky=tk.W)
        self.budget_amount_var = tk.StringVar(value="1500")
        budget_entry = tb.Entry(budget_frame, textvariable=self.budget_amount_var, width=15)
        budget_entry.grid(row=0, column=3, padx=5, pady=5)
        tb.Label(budget_frame, text="元").grid(row=0, column=4, padx=0, pady=5, sticky=tk.W)
        
        # 按钮区域
        button_frame = tb.Frame(budget_frame)
        button_frame.grid(row=0, column=5, padx=5, pady=5)
        
        # 保存统一预算按钮
        tb.Button(button_frame, text="保存统一预算", command=self.save_budget).pack(side="left", padx=5)
        
        # 单独设置每月预算按钮
        tb.Button(button_frame, text="单独设置每月预算", command=self.open_monthly_budget_window).pack(side="left", padx=5)
        
        # 预算说明标签
        self.budget_status_label = tb.Label(budget_frame, text="点击保存预算后将应用到图表展示中")
        self.budget_status_label.grid(row=0, column=6, padx=10, pady=5, sticky=tk.W)
        
        # 图表显示区域
        self.chart_frame = tb.Frame(main_frame)
        self.chart_frame.pack(fill=tk.BOTH, expand=True)

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
        """获取指定月份按分类的支出数据 - 完全修正版"""
        conn = self.get_db_connection()
        if not conn:
            return None
            
        try:
            # 获取月份的第一天和最后一天
            _, last_day = calendar.monthrange(year, month)
            start_date = f"{year}-{month:02d}-01"
            end_date = f"{year}-{month:02d}-{last_day:02d}"
            
            # 调试：检查payments表结构
            payments_structure = self.get_table_structure("payments")
            print("payments表结构:", payments_structure)
            
            # 调试：检查pay_categorys表结构
            category_structure = self.get_table_structure("pay_categorys")
            print("pay_categorys表结构:", category_structure)
            
            cursor = conn.cursor()
            
            # 方法1：直接查询分类名称（如果payments表中有分类名称字段）
            # 先尝试简单的查询，看看表中有哪些字段
            test_query = "SELECT * FROM payments LIMIT 1"
            cursor.execute(test_query)
            sample_row = cursor.fetchone()
            column_names = [description[0] for description in cursor.description]
            print("payments表字段名:", column_names)
            print("样本数据:", sample_row)
            
            # 根据实际表结构构建查询
            # 如果payments表中有category_pid字段，我们通过连接pay_categorys表获取分类名称
            if 'category_pid' in column_names:
                query = """
                    SELECT 
                        COALESCE(pc.title, '未分类') as category_name, 
                        SUM(p.money) as total_amount
                    FROM payments p
                    LEFT JOIN pay_categorys pc ON p.category_pid = pc.id
                    WHERE p.note_date BETWEEN ? AND ? 
                    AND p.is_delete = 0
                    GROUP BY COALESCE(pc.title, '未分类')
                    ORDER BY total_amount DESC
                """
            else:
                # 如果表中没有分类字段，使用固定分类
                query = """
                    SELECT 
                        '支出' as category_name, 
                        SUM(p.money) as total_amount
                    FROM payments p
                    WHERE p.note_date BETWEEN ? AND ? 
                    AND p.is_delete = 0
                    ORDER BY total_amount DESC
                """
            
            print(f"执行查询: {query}")
            print(f"参数: {start_date}, {end_date}")
            
            cursor.execute(query, (start_date, end_date))
            results = cursor.fetchall()
            
            print(f"查询结果: {results}")
            
            return results
        except sqlite3.Error as e:
            messagebox.showerror("查询错误", f"查询数据时出错: {e}")
            print(f"SQL错误详情: {e}")
            return None
        finally:
            conn.close()
    
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

    def get_category_details(self, year, month, category_name):
        """获取指定分类的详细支出记录"""
        conn = self.get_db_connection()
        if not conn:
            return None
            
        try:
            # 获取月份的第一天和最后一天
            _, last_day = calendar.monthrange(year, month)
            start_date = f"{year}-{month:02d}-01"
            end_date = f"{year}-{month:02d}-{last_day:02d}"
            
            cursor = conn.cursor()
            
            # 根据分类名称查询详细记录
            if category_name == '未分类':
                # 查询未分类的记录
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
                # 查询指定分类的记录
                query = """
                    SELECT p.id, p.note_date, p.title, p.remark, p.money, p.create_time 
                    FROM payments p
                    LEFT JOIN pay_categorys pc ON p.category_pid = pc.id
                    WHERE p.note_date BETWEEN ? AND ? 
                    AND p.is_delete = 0
                    AND pc.title = ?
                    ORDER BY p.note_date DESC
                """
                cursor.execute(query, (start_date, end_date, category_name))
            
            results = cursor.fetchall()
            return results
        except sqlite3.Error as e:
            print(f"获取分类详情错误: {e}")
            return None
        finally:
            conn.close()
    
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

    def get_yearly_expenses(self, year):
        """获取指定年份每月支出总额 - 安全版本"""
        conn = self.get_db_connection()
        if not conn:
            return {}  # 返回空字典而不是None
            
        try:
            # 查询每月支出总额
            cursor = conn.cursor()
            query = """
                SELECT 
                    strftime('%m', note_date) as month, 
                    SUM(money) as total_amount
                FROM payments 
                WHERE strftime('%Y', note_date) = ?
                AND is_delete = 0
                GROUP BY month
                ORDER BY month
            """
            
            cursor.execute(query, (str(year),))
            results = cursor.fetchall()
            
            print(f"年度支出查询结果: {results}")
            
            # 转换为字典形式
            monthly_expenses = {}
            for month, amount in results:
                try:
                    monthly_expenses[int(month)] = amount
                except (ValueError, TypeError):
                    continue
            
            # 填充所有月份（如果没有数据的月份设为0）
            full_year_data = {}
            for month in range(1, 13):
                full_year_data[month] = monthly_expenses.get(month, 0)
                
            return full_year_data
        except sqlite3.Error as e:
            messagebox.showerror("查询错误", f"查询数据时出错: {e}")
            return {}  # 返回空字典而不是None
        finally:
            conn.close()

    def load_budgets(self):
        """从文件加载预算数据"""
        try:
            if os.path.exists(self.budget_file):
                import json
                with open(self.budget_file, 'r', encoding='utf-8') as f:
                    self.monthly_budgets = json.load(f)
                print(f"已加载预算数据: {self.monthly_budgets}")
        except Exception as e:
            print(f"加载预算数据失败: {e}")
            self.monthly_budgets = {}
    
    def save_budgets(self):
        """保存预算数据到文件"""
        try:
            # 确保配置目录存在
            if not os.path.exists(self.conf_path):
                os.makedirs(self.conf_path)
                
            import json
            with open(self.budget_file, 'w', encoding='utf-8') as f:
                json.dump(self.monthly_budgets, f, ensure_ascii=False, indent=2)
            print(f"已保存预算数据: {self.monthly_budgets}")
        except Exception as e:
            print(f"保存预算数据失败: {e}")
            messagebox.showerror("错误", f"保存预算失败: {e}")
    
    def save_budget(self):
        """保存用户设置的预算"""
        try:
            year = self.budget_year_var.get()
            amount = float(self.budget_amount_var.get())
            
            if amount <= 0:
                messagebox.showerror("输入错误", "预算金额必须大于0")
                return
            
            # 存储该年份的预算
            if year not in self.monthly_budgets:
                self.monthly_budgets[year] = {}
            
            # 设置所有月份的预算
            for month in range(1, 13):
                self.monthly_budgets[year][str(month)] = amount
            
            # 保存到文件
            self.save_budgets()
            
            # 更新状态标签
            self.budget_status_label.config(text=f"已保存{year}年的月度预算: {amount}元")
            messagebox.showinfo("成功", f"已成功保存{year}年的月度预算")
            
        except ValueError:
            messagebox.showerror("输入错误", "请输入有效的数字")
        except Exception as e:
            messagebox.showerror("错误", f"保存失败: {str(e)}")
            
    def open_monthly_budget_window(self):
        """打开月度预算单独调整窗口"""
        try:
            year = int(self.budget_year_var.get())
            current_budgets = self.get_monthly_budget(year)
            
            # 创建新窗口
            budget_window = tk.Toplevel(self.parent)
            budget_window.title(f"设置{year}年每月预算")
            budget_window.geometry("400x500")
            budget_window.resizable(False, False)
            
            # 创建滚动区域
            canvas = tk.Canvas(budget_window)
            scrollbar = tb.Scrollbar(budget_window, orient="vertical", command=canvas.yview)
            scrollable_frame = tb.Frame(canvas)
            
            scrollable_frame.bind(
                "<Configure>",
                lambda e: canvas.configure(
                    scrollregion=canvas.bbox("all")
                )
            )
            
            canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
            canvas.configure(yscrollcommand=scrollbar.set)
            
            canvas.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")
            
            # 存储月度预算输入框的引用
            month_entries = []
            
            # 创建每个月的预算输入
            for month in range(1, 13):
                frame = tb.Frame(scrollable_frame)
                frame.pack(fill="x", padx=20, pady=8)
                
                tb.Label(frame, text=f"{month}月预算:", width=10).pack(side="left")
                
                var = tk.StringVar(value=f"{current_budgets[month]:.2f}")
                entry = tb.Entry(frame, textvariable=var, width=15)
                entry.pack(side="left", padx=5)
                
                tb.Label(frame, text="元").pack(side="left")
                
                month_entries.append((str(month), var))
            
            # 保存按钮
            def save_monthly_budgets():
                try:
                    year_str = str(year)
                    if year_str not in self.monthly_budgets:
                        self.monthly_budgets[year_str] = {}
                    
                    for month_str, var in month_entries:
                        amount = float(var.get())
                        if amount <= 0:
                            messagebox.showerror("输入错误", f"{month_str}月预算必须大于0")
                            return
                        self.monthly_budgets[year_str][month_str] = amount
                    
                    # 保存到文件
                    self.save_budgets()
                    messagebox.showinfo("成功", f"已成功保存{year}年的月度预算")
                    budget_window.destroy()
                    
                except ValueError:
                    messagebox.showerror("输入错误", "请确保所有输入都是有效的数字")
            
            # 添加保存和取消按钮
            button_frame = tb.Frame(budget_window)
            button_frame.pack(fill="x", padx=20, pady=15)
            
            tb.Button(button_frame, text="取消", command=budget_window.destroy).pack(side="right", padx=10)
            tb.Button(button_frame, text="保存", command=save_monthly_budgets).pack(side="right", padx=10)
            
        except ValueError:
            messagebox.showerror("错误", "请先选择有效的年份")
    
    
    def get_monthly_expense_sum(self, year, month):
        """返回指定年月的支出总额（payments.money 之和，is_delete=0）"""
        conn = self.get_db_connection()
        if not conn:
            return 0.0
        try:
            import calendar
            _, last_day = calendar.monthrange(int(year), int(month))
            start_date = f"{int(year)}-{int(month):02d}-01"
            end_date = f"{int(year)}-{int(month):02d}-{last_day:02d}"
            cur = conn.cursor()
            cur.execute("""                SELECT COALESCE(SUM(money), 0) 
                FROM payments 
                WHERE note_date BETWEEN ? AND ? AND is_delete=0
            """, (start_date, end_date))
            val = cur.fetchone()[0] or 0.0
            try:
                return float(val)
            except Exception:
                return 0.0
        except Exception as e:
            print(f"get_monthly_expense_sum error: {e}")
            return 0.0
        finally:
            conn.close()

    def get_budget_for(self, year, month, default=1500.0):
        """获取指定年月的预算数值（若无则返回默认值）"""
        year_str = str(int(year))
        month_str = str(int(month))
        try:
            return float(self.monthly_budgets.get(year_str, {}).get(month_str, default))
        except Exception:
            return float(default)

    def set_budget_for(self, year, month, amount):
        """设置并保存指定年月的预算数值"""
        try:
            year_str = str(int(year))
            month_str = str(int(month))
            if year_str not in self.monthly_budgets:
                self.monthly_budgets[year_str] = {}
            self.monthly_budgets[year_str][month_str] = float(amount)
            self.save_budgets()
            return True
        except Exception as e:
            print(f"set_budget_for error: {e}")
            return False
    def get_monthly_budget(self, year):
        """获取每月预算数据"""
        year_str = str(year)
        
        # 如果有保存的预算数据，使用保存的数据
        if year_str in self.monthly_budgets:
            budget_dict = {}
            for month in range(1, 13):
                month_str = str(month)
                if month_str in self.monthly_budgets[year_str]:
                    budget_dict[month] = self.monthly_budgets[year_str][month_str]
                else:
                    budget_dict[month] = 1500  # 默认预算
            return budget_dict
        
        # 如果没有保存的预算，使用默认值
        return {month: 1500 for month in range(1, 13)}  # 默认预算

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
            
            # 测试查询payments表
            cursor.execute("SELECT COUNT(*) FROM payments WHERE is_delete = 0")
            count = cursor.fetchone()[0]
            print(f"payments表记录数: {count}")
            
            # 显示表结构
            cursor.execute("PRAGMA table_info(payments)")
            table_info = cursor.fetchall()
            print("payments表结构:")
            for column in table_info:
                print(f"  {column}")
            
            # 显示前几条记录
            if count > 0:
                cursor.execute("SELECT * FROM payments WHERE is_delete = 0 LIMIT 3")
                sample_data = cursor.fetchall()
                print("样本数据:")
                for row in sample_data:
                    print(f"  {row}")
            
            return count > 0
        except sqlite3.Error as e:
            print(f"测试查询错误: {e}")
            return False
        finally:
            conn.close()

    def generate_pie_chart(self):
        """生成支出分类饼图，支持鼠标悬停显示详细账目"""
        try:
            year = int(self.year_var.get())
            month = int(self.month_var.get())
            self.status_label.config(text=f"查询{year}年{month}月数据...")
        except ValueError:
            messagebox.showerror("输入错误", "请输入有效的年份和月份")
            return
        
        # 先测试数据库连接
        if not self.test_database_connection():
            messagebox.showerror("数据库错误", "无法连接数据库或没有数据")
            return
            
        data = self.get_monthly_expenses_by_category(year, month)
        
        # 安全检查数据
        if data is None:
            messagebox.showerror("查询错误", "数据查询失败")
            self.status_label.config(text="查询失败")
            return
            
        if not data:
            messagebox.showinfo("无数据", f"{year}年{month}月没有支出数据")
            self.status_label.config(text="没有找到数据")
            return
            
        # 准备饼图数据
        self.current_category_names = [item[0] for item in data]
        amounts = [item[1] for item in data]
        
        # 清除现有图表
        for widget in self.chart_frame.winfo_children():
            widget.destroy()
            
        # 创建图表
        fig = Figure(figsize=(8, 6), dpi=100)
        ax = fig.add_subplot(111)
        self.current_fig = fig
        
        # 绘制饼图
        wedges, texts, autotexts = ax.pie(
            amounts, 
            labels=self.current_category_names, 
            autopct='%1.1f%%',
            startangle=90,
            wedgeprops={'edgecolor': 'w', 'linewidth': 1}
        )
        
        # 设置标题
        ax.set_title(f"{year}年{month}月支出分类占比\n（点击饼图各部分查看详细账目）", fontsize=16)
        
        # 确保百分比文本清晰可读
        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_fontsize(10)
            
        # 创建鼠标悬停提示框
        tooltip = ax.annotate('', xy=(0.5, 0.5), xytext=(0.5, 0.5),
                           bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="gray", alpha=0.8),
                           arrowprops=dict(arrowstyle="->"), va="center", ha="center")
        tooltip.set_visible(False)
        
        # 在Tkinter中显示图表
        canvas = FigureCanvasTkAgg(fig, self.chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        self.current_canvas = canvas
        
        # 绑定鼠标事件
        canvas.mpl_connect('motion_notify_event', lambda event: self.on_hover(event, wedges, tooltip, year, month))
        canvas.mpl_connect('button_press_event', lambda event: self.on_click(event, wedges, year, month))
        
        self.status_label.config(text=f"已生成{year}年{month}月支出饼图（点击查看明细）")
    
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
            lbl.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
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
            lbl.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
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
    def get_monthly_expenses_by_category_for_year(self, year, month):
            """获取指定月份按分类的支出数据（用于年度堆叠图）"""
            conn = self.get_db_connection()
            if not conn:
                return None
            
            try:
                # 获取月份的第一天和最后一天
                _, last_day = calendar.monthrange(year, month)
                start_date = f"{year}-{month:02d}-01"
                end_date = f"{year}-{month:02d}-{last_day:02d}"
            
                cursor = conn.cursor()
            
                # 查询按分类的支出
                query = """
                    SELECT 
                        COALESCE(pc.title, '未分类') as category_name, 
                        SUM(p.money) as total_amount
                    FROM payments p
                    LEFT JOIN pay_categorys pc ON p.category_pid = pc.id
                    WHERE p.note_date BETWEEN ? AND ? 
                    AND p.is_delete = 0
                    GROUP BY COALESCE(pc.title, '未分类')
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
            """获取指定月份指定分类的详细支出记录"""
            conn = self.get_db_connection()
            if not conn:
                return None
            
            try:
                # 获取月份的第一天和最后一天
                _, last_day = calendar.monthrange(year, month)
                start_date = f"{year}-{month:02d}-01"
                end_date = f"{year}-{month:02d}-{last_day:02d}"
            
                cursor = conn.cursor()
            
                # 查询指定月份和分类的详细记录
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
                    query = """
                        SELECT p.id, p.note_date, p.title, p.remark, p.money, p.create_time 
                        FROM payments p
                        LEFT JOIN pay_categorys pc ON p.category_pid = pc.id
                        WHERE p.note_date BETWEEN ? AND ? 
                        AND p.is_delete = 0
                        AND pc.title = ?
                        ORDER BY p.note_date DESC
                    """
                    cursor.execute(query, (start_date, end_date, category))
            
                results = cursor.fetchall()
                return results
            except sqlite3.Error as e:
                print(f"获取月度分类详情错误: {e}")
                return None
            finally:
                conn.close()
    
    def on_bar_hover(self, event, bars, categories, year, tooltip, monthly_data):
            """堆叠柱状图的鼠标悬停事件处理函数，支持预算柱状图交互"""
            if event.inaxes is None:
                tooltip.set_visible(False)
                if self.current_canvas:
                    self.current_canvas.draw_idle()
                    self.current_canvas.get_tk_widget().config(cursor="arrow")
                return
        
            # 首先检查是否悬停在预算柱状图上
            # 查找红色的柱状图（预算）
            budget_bar_found = False
            for artist in event.inaxes.patches:
                # 预算柱状图颜色为红色，位置在右侧
                if hasattr(artist, 'get_fc') and str(artist.get_fc()) == 'red' and artist.contains_point((event.x, event.y)):
                    # 计算预算柱状图对应的月份
                    bar_x = artist.get_x()
                    # 由于我们是并排显示，预算柱状图的x位置在右侧，需要特殊计算月份索引
                    month_idx = int(round(bar_x + artist.get_width()/2))
                    month = month_idx + 1  # 月份从1开始
                
                    if 1 <= month <= 12:
                        # 获取该月预算
                        budget_value = self.get_monthly_budget(year).get(month, 0)
                    
                        # 构建提示框内容
                        tooltip_text = f"{month}月预算\n金额: {budget_value:.2f}元"
                    
                        # 更新提示框
                        tooltip.set_text(tooltip_text)
                        tooltip.xy = (event.xdata, event.ydata)
                        tooltip.set_visible(True)
                    
                        # 更改光标样式
                        if self.current_canvas:
                            self.current_canvas.get_tk_widget().config(cursor="hand2")
                            self.current_canvas.draw_idle()
                        budget_bar_found = True
                        break
        
            if budget_bar_found:
                return
        
            # 获取鼠标位置对应的月份
            # 实际支出柱状图在左侧，需要调整月份计算
            x_pos = int(round(event.xdata))
            month = x_pos + 1  # 月份从1开始
        
            # 检查是否在有效月份范围内
            if month < 1 or month > 12:
                tooltip.set_visible(False)
                if self.current_canvas:
                    self.current_canvas.draw_idle()
                    self.current_canvas.get_tk_widget().config(cursor="arrow")
                return
        
            # 遍历所有堆叠层，找到鼠标悬停的层（实际支出部分）
            for i, bar_group in enumerate(bars):
                for j, rect in enumerate(bar_group):
                    if j == x_pos and rect.contains_point((event.x, event.y)):
                        category = categories[i]
                        # 确保month在monthly_data中
                        if month in monthly_data and category in monthly_data[month]:
                            amount = monthly_data[month][category]
                        
                            # 获取该分类该月份的详细记录
                            details = self.get_monthly_category_details(year, month, category)
                        
                            # 构建提示框内容
                            tooltip_text = f"{month}月 {category} 支出\n总计: {amount:.2f}元\n"
                            if details:
                                # 最多显示前5条记录
                                max_display = 5
                                for record in details[:max_display]:
                                    note_date = record[1]
                                    title = record[2]
                                    money = record[4]
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
                        
                            # 更新提示框
                            tooltip.set_text(tooltip_text)
                            tooltip.xy = (event.xdata, event.ydata)
                            tooltip.set_visible(True)
                        
                            # 更改光标样式
                            if self.current_canvas:
                                self.current_canvas.get_tk_widget().config(cursor="hand2")
                                self.current_canvas.draw_idle()
                            return
        
            # 鼠标不在任何柱状图上
            tooltip.set_visible(False)
            if self.current_canvas:
                self.current_canvas.draw_idle()
                self.current_canvas.get_tk_widget().config(cursor="arrow")
    
    def generate_bar_chart(self):
            """生成年度预算与实际支出对比柱状图（实际支出使用堆叠柱状图）"""
            try:
                year = int(self.year_var.get())
                self.status_label.config(text=f"查询{year}年数据...")
            except ValueError:
                messagebox.showerror("输入错误", "请输入有效的年份")
                return
            
            # 先测试数据库连接
            if not self.test_database_connection():
                messagebox.showerror("数据库错误", "无法连接数据库或没有数据")
                return
        
            # 获取预算数据
            budget_data = self.get_monthly_budget(year)
        
            # 获取所有分类
            categories = self.get_all_categories_for_year(year)
            if not categories:
                messagebox.showinfo("无数据", f"{year}年没有支出数据")
                self.status_label.config(text="没有找到数据")
                return
        
            # 获取每月各分类的支出数据
            monthly_data = self.get_monthly_category_expenses(year, categories)
        
            # 清除现有图表
            for widget in self.chart_frame.winfo_children():
                widget.destroy()
            
            # 创建图表
            fig = Figure(figsize=(10, 6), dpi=100)
            ax = fig.add_subplot(111)
            self.current_fig = fig
        
            # 准备数据
            months = list(range(1, 13))
            month_names = [f'{m}月' for m in months]
            budget_values = [budget_data.get(m, 0) for m in months]
        
            # 设置柱状图位置和宽度
            x = range(len(months))
            width = 0.6
        
            # 为不同分类生成不同颜色
            colors = plt.cm.tab10.colors[:len(categories)]
        
            # 设置柱状图位置和宽度（并排显示）
            bar_width = width / 2  # 将宽度分为两部分，一部分给实际支出，一部分给预算
        
            # 绘制堆叠柱状图（实际支出）
            bottom = [0] * len(months)
            bars = []
        
            # 实际支出柱状图的x位置：左半部分
            actual_x_pos = [pos - bar_width/2 for pos in x]
        
            for i, category in enumerate(categories):
                # 获取该分类各月的支出
                category_values = [monthly_data[month][category] for month in months]
                # 绘制堆叠层
                bar = ax.bar(actual_x_pos, category_values, bar_width, 
                            bottom=bottom, label=category, color=colors[i])
                bars.append(bar)
                # 更新下一层的起始位置
                bottom = [bottom[j] + category_values[j] for j in range(len(months))]
        
            # 绘制预算柱状图（预算柱状图位置：右半部分）
            budget_x_pos = [pos + bar_width/2 for pos in x]
            budget_bars = ax.bar(budget_x_pos, budget_values, bar_width, 
                                label='预算', color='red')
        
            # 添加数值标签（实际支出总和）
            for i, total in enumerate(bottom):
                if total > 0:
                    ax.text(actual_x_pos[i], total + 10, f'{total:.0f}', 
                            ha='center', va='bottom', fontsize=8)
                
            # 添加预算柱状图数值标签
            for i, budget in enumerate(budget_values):
                if budget > 0:
                    ax.text(budget_x_pos[i], budget + 10, f'{budget:.0f}', 
                            ha='center', va='bottom', fontsize=8, color='red')
        
            # 设置图表属性
            ax.set_xlabel('月份')
            ax.set_ylabel('金额 (元)')
            ax.set_title(f'{year}年每月支出分类堆叠图与预算对比\n（鼠标悬停查看详细支出）')
            ax.set_xticks(x)
            ax.set_xticklabels(month_names)
            ax.legend(loc='upper left', bbox_to_anchor=(1, 1))  # 图例放在右侧
        
            # 调整布局以容纳右侧图例
            fig.tight_layout()
            fig.subplots_adjust(right=0.75)
        
            # 创建鼠标悬停提示框
            tooltip = ax.annotate('', xy=(0.5, 0.5), xytext=(0.5, 0.5),
                               bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="gray", alpha=0.9),
                               arrowprops=dict(arrowstyle="->"), va="center", ha="center")
            tooltip.set_visible(False)
        
            # 在Tkinter中显示图表
            canvas = FigureCanvasTkAgg(fig, self.chart_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
            self.current_canvas = canvas
        
            # 绑定鼠标事件
            canvas.mpl_connect('motion_notify_event', 
                              lambda event: self.on_bar_hover(event, bars, categories, year, tooltip, monthly_data))
        
            self.status_label.config(text=f"已生成{year}年支出分类堆叠图")