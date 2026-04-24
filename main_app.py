from datetime import datetime, timedelta
import sys, os, json, threading, time
import pandas as pd
from PySide6.QtWidgets import *
from PySide6.QtCore import QEvent, QSize, Qt, QAbstractTableModel, QTimer
from PySide6.QtGui import QAction, QColor
from PySide6.QtWidgets import QWidgetAction
from PySide6.QtWidgets import QInputDialog
from license_system import validate_license
from PySide6.QtWidgets import QStyledItemDelegate
from PySide6.QtCore import QRect
from PySide6.QtWidgets import QStyleOptionButton, QStyle
from PySide6.QtGui import QPalette
from PySide6.QtGui import QTextDocument
from PySide6.QtPrintSupport import QPrinter, QPrintDialog
from PySide6.QtGui import QPainter


CONFIG_FILE = "config.json"
PRESET_FILE = "presets.json"

DISPLAY_COLUMNS = [
    "Tray Code", "Current Rack Grp", "Pl No",
     "Route Type",
    "Routetype", "Order Type"
]

def get_shift_now():
    now = datetime.now()

    if now.hour < 7:
        now = now - timedelta(days=1)

    return now.time()
# =========================
# LICENSE CHECK
# =========================
def background_check():
    while True:
        ok, _, _ = validate_license()
        if not ok:
            os._exit(1)
        time.sleep(15)

class RightCheckDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        style = option.widget.style()

        # Base item
        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        opt.features &= ~QStyleOptionViewItem.HasCheckIndicator

        # leave space for checkbox
        opt.rect = option.rect.adjusted(0, 0, -50, 0)

        style.drawControl(QStyle.CE_ItemViewItem, opt, painter)

        # Hover effect
        if option.state & QStyle.State_MouseOver:
            painter.save()
            painter.setBrush(QColor(255, 255, 255, 20))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(option.rect.adjusted(2, 2, -2, -2), 8, 8)
            painter.restore()

        checked = index.data(Qt.CheckStateRole) == Qt.Checked

        # Selected background
        if checked:
            painter.save()
            painter.setBrush(QColor("#238636"))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(option.rect.adjusted(2, 2, -2, -2), 8, 8)
            painter.restore()


        # 🔥 CUSTOM CHECKBOX (MANUAL DRAW — BEST CONTROL)
        rect = option.rect
        cb_rect = QRect(rect.right() - 40, rect.top() + 8, 22, 22)

        painter.save()

        # Box
        painter.setPen(QColor("#8b949e"))
        painter.setBrush(QColor("#30363d") if not checked else QColor("#3fb950"))
        painter.drawRoundedRect(cb_rect, 4, 4)

        # Tick
        if checked:
            painter.setPen(QColor("#ffffff"))
            painter.drawText(cb_rect, Qt.AlignCenter, "✔")

        painter.restore()

    def editorEvent(self, event, model, option, index):
        if event.type() == QEvent.MouseButtonRelease:
            rect = option.rect
            cb_rect = QRect(rect.right() - 40, rect.top() + 8, 22, 22)

            if cb_rect.contains(event.pos()):
                current = index.data(Qt.CheckStateRole)
                new_state = Qt.Unchecked if current == Qt.Checked else Qt.Checked

                model.setData(index, new_state, Qt.CheckStateRole)
                option.widget.viewport().update()
                return True

        return super().editorEvent(event, model, option, index)

# =========================
# TABLE MODEL
# =========================
class PandasModel(QAbstractTableModel):
    def __init__(self, df):
        super().__init__()
        self.df = df
        

    def rowCount(self, parent=None):
        return len(self.df)

    def columnCount(self, parent=None):
        return len(self.df.columns)

    def data(self, index, role):
        if role == Qt.DisplayRole:
            return str(self.df.iloc[index.row(), index.column()])

    def headerData(self, col, orientation, role):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self.df.columns[col]

# =========================
# MULTISELECT DROPDOWN
# =========================
class MultiSelectCombo(QPushButton):
    def __init__(self, parent, key):
        super().__init__("All")
        self.parent_widget = parent
        self.key = key

        self.menu = QMenu(self)
        self.setMenu(self.menu)

        self.actions = []

    def populate(self, values, selected):
        self.menu.clear()
        self.actions = []

        # 🔍 Search box
        search_action = QWidgetAction(self.menu)
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search...")
        self.search_box.textChanged.connect(self.filter_items)
        search_action.setDefaultWidget(self.search_box)
        self.menu.addAction(search_action)

        # ✔ Select All
        select_all = QAction("Select All", self)
        select_all.triggered.connect(self.select_all)
        self.menu.addAction(select_all)

        # ❌ Clear All
        clear_all = QAction("Clear All", self)
        clear_all.triggered.connect(self.clear_all)
        self.menu.addAction(clear_all)

        self.menu.addSeparator()

        for v in sorted([str(v) for v in values]):
            act = QAction(v, self)
            act.setCheckable(True)
            act.setChecked(v in selected)
            act.toggled.connect(self.update_selection)
            self.menu.addAction(act)
            self.actions.append(act)

        self.update_text()

    def filter_items(self, text):
        text = text.lower()
        for act in self.actions:
            act.setVisible(text in act.text().lower())

    def select_all(self):
        for a in self.actions:
            a.setChecked(True)

    def clear_all(self):
        for a in self.actions:
            a.setChecked(False)

    def update_selection(self):
        selected = [a.text() for a in self.actions if a.isChecked()]
        self.parent_widget.filters[self.key] = selected
        self.update_text()
        self.parent_widget.apply_filters()

    def update_text(self):
        selected = [a.text() for a in self.actions if a.isChecked()]
        if not selected:
            self.setText("All")
        elif len(selected) <= 2:
            self.setText(", ".join(selected))
        else:
            self.setText(f"{selected[0]}, {selected[1]} (+{len(selected)-2})")

# =========================
# PROCESS DATA
# =========================
def process_df(df):
    df.columns = df.iloc[0]
    df = df[1:].reset_index(drop=True)
    df.columns = df.columns.astype(str).str.strip()

    def find(k):
        return [c for c in df.columns if k in c.lower()]

    rack = find("rack")
    tray = find("tray")
    route = find("route")

    if rack:
        df.rename(columns={rack[0]: "Current Rack Grp"}, inplace=True)
    if tray:
        df.rename(columns={tray[0]: "Tray Code"}, inplace=True)
    if len(route) >= 1:
        df.rename(columns={route[0]: "Route Type"}, inplace=True)
    if len(route) >= 2:
        df.rename(columns={route[1]: "Routetype"}, inplace=True)

    if "Tray Code" in df.columns:
        df = df.drop_duplicates(subset=["Tray Code"])

    df = df[df["Current Rack Grp"].notna()]
    df = df[df["Current Rack Grp"] != ""]

    return df

# =========================
# MAIN APP
# =========================
class App(QMainWindow):
    def __init__(self):
        super().__init__()
        from PySide6.QtGui import QFont
        self.setFont(QFont("Segoe UI", 11))
        self.setWindowTitle("Tray Filter App")
        self.resize(1500, 850)

        self.config = self.load_json(CONFIG_FILE)
        self.presets = self.load_json(PRESET_FILE)

        self.filters = {
            "order_type": [],
            "route_type": [],
            "slot": [],
            "order_class": []
        }

        # ✅ CREATE FILTER WIDGETS HERE (FIX)
        self.order = MultiSelectCombo(self, "order_type")
        self.route = MultiSelectCombo(self, "route_type")
        self.slot = MultiSelectCombo(self, "slot")
        self.cls = MultiSelectCombo(self, "order_class")

        self.df = None
        self.filtered_df = None

        self.dark = True
        self.apply_dark()

        self.init_ui()
        self.load_files()
        self.update_license_status()
        self.license_timer = QTimer()
        self.license_timer.timeout.connect(self.update_license_status)
        self.license_timer.start(60000)

        # AUTO REFRESH
        self.timer = QTimer()
        self.timer.timeout.connect(self.auto_refresh)
        self.timer.start(5000)

    # =========================
    # UI
    # =========================
    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)

        # ===== SIDEBAR =====
        side = QVBoxLayout()
        side.setSpacing(10)

        # FILE SELECT
        self.file_box = QComboBox()
        self.file_box.currentIndexChanged.connect(self.load_file)

        self.theme_btn = QPushButton("Toggle Theme")
        self.theme_btn.clicked.connect(self.toggle_theme)

        file_group = QGroupBox("File")
        file_layout = QVBoxLayout()
        file_layout.addWidget(self.file_box)

        # 🔥 SETTINGS BUTTON (small)
        settings_layout = QHBoxLayout()
        
        self.theme_btn = QPushButton("🌙")
        self.theme_btn.setFixedWidth(40)
        self.theme_btn.clicked.connect(self.toggle_theme)
        
        self.settings_btn = QPushButton("📂")
        self.settings_btn.setFixedWidth(40)
        self.settings_btn.clicked.connect(self.change_folder)
        
        settings_layout.addWidget(self.theme_btn)
        settings_layout.addWidget(self.settings_btn)
        
        file_layout.addLayout(settings_layout)
        file_group.setLayout(file_layout)
        side.addWidget(file_group)

        # FILTERS
        filter_group = QGroupBox("Filters")
        filter_layout = QVBoxLayout()

        filter_layout.addWidget(QLabel("Order Type"))
        filter_layout.addWidget(self.order)

        filter_layout.addWidget(QLabel("Route Type"))
        filter_layout.addWidget(self.route)

        filter_layout.addWidget(QLabel("Slot"))
        filter_layout.addWidget(self.slot)

        filter_layout.addWidget(QLabel("Order Class"))
        filter_layout.addWidget(self.cls)

        filter_group.setLayout(filter_layout)
        side.addWidget(filter_group)

        # PRESETS
        preset_group = QGroupBox("Presets")
        preset_layout = QVBoxLayout()

        self.preset_box = QComboBox()
        self.preset_box.addItems([""] + list(self.presets.keys()))

        btn_load = QPushButton("Load")
        btn_save = QPushButton("Save")

        btn_load.clicked.connect(self.load_preset)
        btn_save.clicked.connect(self.save_preset)

        preset_layout.addWidget(self.preset_box)
        preset_layout.addWidget(btn_load)
        preset_layout.addWidget(btn_save)

        preset_group.setLayout(preset_layout)
        side.addWidget(preset_group)

        side.addStretch()

        layout.addLayout(side, 1)

        # ===== RIGHT PANEL =====
        right = QVBoxLayout()

        # =========================
        # 📊 METRICS BAR
        # =========================
        metrics_layout = QHBoxLayout()

        self.total_label = QLabel("Total: 0")
        self.filtered_label = QLabel("Filtered: 0")
        self.rack_count_label = QLabel("Racks: 0")

        self.total_label.setStyleSheet("color:#58a6ff; font-weight:bold;")
        self.filtered_label.setStyleSheet("color:#3fb950; font-weight:bold;")
        self.rack_count_label.setStyleSheet("color:#f2cc60; font-weight:bold;")

        metrics_layout.addWidget(self.total_label)
        metrics_layout.addWidget(self.filtered_label)
        metrics_layout.addWidget(self.rack_count_label)

        right.addLayout(metrics_layout)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Search Tray Code")
        self.search.textChanged.connect(self.apply_filters)
        right.addWidget(self.search)

        self.remove_st = QCheckBox("Remove ST trays")
        self.remove_st.setChecked(True)
        self.remove_st.stateChanged.connect(self.apply_filters)
        right.addWidget(self.remove_st)

        self.active_rack_label = QLabel("All Racks")
        self.active_rack_label.setStyleSheet("color:#58a6ff; font-weight:bold;")
        right.addWidget(self.active_rack_label)

        right.addWidget(QLabel("Rack Summary"))
        rack_btn_layout = QHBoxLayout()

        btn_all = QPushButton("Select All")
        btn_none = QPushButton("Clear")
        btn_print = QPushButton("🖨")   # small icon button
        btn_print.setFixedWidth(40)

        btn_all.clicked.connect(self.select_all_racks)
        btn_none.clicked.connect(self.clear_all_racks)
        btn_print.clicked.connect(self.print_selected_racks_pdf)

        rack_btn_layout.addWidget(btn_all)
        rack_btn_layout.addWidget(btn_none)
        rack_btn_layout.addWidget(btn_print)

        right.addLayout(rack_btn_layout)
        self.rack_list = QListWidget()
        self.rack_list.setSelectionMode(QAbstractItemView.MultiSelection)
        self.rack_list.itemChanged.connect(self.filter_rack)
        right.addWidget(self.rack_list)

        self.rack_list.setItemDelegate(RightCheckDelegate())

        self.table = QTableView()
        self.table.setSortingEnabled(True)
        right.addWidget(self.table)

        btn_layout = QHBoxLayout()

        btn_export = QPushButton("Export View")
        btn_export.clicked.connect(self.export_view)

        btn_rack = QPushButton("Rack-wise Export")
        btn_rack.clicked.connect(self.export_rack)

        btn_notify = QPushButton("Send to Telegram")
        btn_notify.clicked.connect(self.rack_notify_telegram)

        btn_auto = QPushButton("Run All Presets")
        btn_auto.clicked.connect(self.run_all_presets)

        btn_layout.addWidget(btn_notify)
        btn_layout.addWidget(btn_export)
        btn_layout.addWidget(btn_rack)
        btn_layout.addWidget(btn_auto)

        right.addLayout(btn_layout)

        btn_layout.addWidget(btn_export)
        btn_layout.addWidget(btn_rack)
        right.addLayout(btn_layout)

        layout.addLayout(right, 3)
        self.rack_list.setSpacing(6)
        self.rack_list.setUniformItemSizes(True)

        # =========================
        # 🔐 LICENSE STATUS
        # =========================
        self.license_label = QLabel("License: Checking...")
        self.license_label.setStyleSheet("color:#58a6ff; font-weight:bold;")
        right.addWidget(self.license_label)


    # =========================
    # THEMES
    # =========================
    def apply_dark(self):
        self.setStyleSheet("""
        QWidget {
            background: #0d1117;
            color: #e6edf3;
            font-size: 14px;
            font-family: Segoe UI;
        }

        QGroupBox {
            font-size: 15px;
            font-weight: bold;
            border: 1px solid #30363d;
            border-radius: 8px;
            margin-top: 10px;
        }

        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px;
        }

        QPushButton {
            background-color: #21262d;
            border: 1px solid #30363d;
            padding: 6px 10px;
            border-radius: 6px;
        }

        QPushButton:hover {
            background-color: #30363d;
        }

        QLineEdit {
            background: #161b22;
            border: 1px solid #30363d;
            padding: 6px;
            border-radius: 6px;
        }

        QListWidget {
            border: none;
            outline: none;
        }

        /* 🔥 CARD STYLE ITEMS */
        QListWidget::item {
            background: #161b22;
            margin: 4px;
            padding: 10px;
            border-radius: 8px;
        }

        QListWidget::item:hover {
            background: #1f2937;
        }

        QListWidget::item:selected {
            background: #238636;
        }

        /* 🔥 BIGGER CHECKBOX */
        QCheckBox::indicator {
            width: 20px;
            height: 20px;
        }

        QCheckBox::indicator:unchecked {
            border: 2px solid #8b949e;
            background: #0d1117;
        }

        QCheckBox::indicator:checked {
            background: #3fb950;
            border: 2px solid #3fb950;
        }

        QTableView {
            background: #0d1117;
            gridline-color: #30363d;
        }
        """)

    def rack_notify_telegram(self):
        if self.filtered_df is None:
            return
    
        import requests
        import re
    
        BOT_TOKEN = "8663778811:AAEqvTZYh8Lx6PocVh6zEVCEtF9I59VGdIo"
        CHAT_ID = "-5117824741"
    
        selected_racks = []
    
        for i in range(self.rack_list.count()):
            item = self.rack_list.item(i)
            if item.data(Qt.CheckStateRole) == Qt.Checked:
                rack = item.text().split(" (")[0]
                selected_racks.append(rack)
    
        if not selected_racks:
            QMessageBox.warning(self, "No Selection", "Select at least one rack")
            return

    # 🔥 SORT
        def rack_sort_key(x):
            nums = re.findall(r'\d+', str(x))
            return int(nums[0]) if nums else 0

        selected_racks = sorted(selected_racks, key=rack_sort_key)

    # 🔥 BUILD MESSAGE (CLEAN FORMAT)
        lines = []
        for rack in selected_racks:
            df = self.filtered_df[
                self.filtered_df["Current Rack Grp"] == rack
            ]

            trays = df["Tray Code"].drop_duplicates().astype(str).tolist()

            if trays:
                line = f"{rack}  " + "  ".join(trays)
                lines.append(line)

        message = "\n".join(lines)

        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

        try:
            requests.post(url, data={
                "chat_id": CHAT_ID,
                "text": message
            })
            QMessageBox.information(self, "Sent", "Message sent to Telegram group")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def apply_light(self):
        self.setStyleSheet("QWidget { background:#f5f5f5; color:#111; }")

    def toggle_theme(self):
        if self.dark:
            self.apply_light()
        else:
            self.apply_dark()
        self.dark = not self.dark

    # =========================
    # FILTERS
    # =========================
    def apply_filters(self):
        if self.df is None:
            return

        self.active_rack_label.setText("All Racks")

        df = self.df.copy()

        if self.filters["order_type"]:
            df = df[df["Order Type"].isin(self.filters["order_type"])]
        if self.filters["route_type"]:
            df = df[df["Route Type"].isin(self.filters["route_type"])]
        if self.filters["slot"]:
            df = df[df["Routetype"].isin(self.filters["slot"])]
        if self.filters["order_class"]:
            df = df[df["Order Class"].isin(self.filters["order_class"])]

        if self.search.text():
            df = df[df["Tray Code"].astype(str).str.contains(self.search.text(), case=False, na=False)]

        if self.remove_st.isChecked():
            df = df[df["Tray Code"].notna() & (df["Tray Code"] != "")]

        df = df[[c for c in DISPLAY_COLUMNS if c in df.columns]]

        if "Tray Code" in df.columns:
            df = df.drop_duplicates(subset=["Tray Code"])

        self.filtered_df = df
        self.table.setModel(PandasModel(df))
        self.update_rack(df)
        self.update_metrics(df)

    def update_rack(self, df):
        grp = df.groupby("Current Rack Grp").size().sort_values(ascending=False)

        self.rack_list.blockSignals(True)
        self.rack_list.clear()

        for k, v in grp.items():
            item = QListWidgetItem(f"{k} ({v})")
            item.setData(Qt.CheckStateRole, Qt.Unchecked)

            # Bigger row height (card feel)
            item.setSizeHint(QSize(0, 40))

            self.rack_list.addItem(item)

        self.rack_list.blockSignals(False)

    def filter_rack(self):
        checked_racks = []

        for i in range(self.rack_list.count()):
            item = self.rack_list.item(i)
            if item.data(Qt.CheckStateRole) == Qt.Checked:
                rack = item.text().split(" (")[0]
                checked_racks.append(rack)

        if not checked_racks:
            self.table.setModel(PandasModel(self.filtered_df))
            self.active_rack_label.setText("All Racks")
            return

        df = self.filtered_df[
            self.filtered_df["Current Rack Grp"].isin(checked_racks)
        ]

        self.active_rack_label.setText(
            f"Active Racks: {', '.join(checked_racks[:3])}" +
            (f" (+{len(checked_racks)-3})" if len(checked_racks) > 3 else "")
        )

        self.table.setModel(PandasModel(df))

    # =========================
    # EXPORT
    # =========================
    def export_view(self):
        from datetime import datetime

        count = len(self.filtered_df)
        default_name = f"filtered_{count}_rows_{datetime.now().strftime('%Y-%m-%d_%H-%M')}.xlsx"

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save",
            default_name,   # 🔥 auto filename here
            "Excel (*.xlsx)"
        )

        if not path:
            return

        df = self.filtered_df.copy()

        if "Tray Code" in df.columns:
            df = df.drop_duplicates(subset=["Tray Code"])

        df.to_excel(path, index=False)

    def export_rack(self):
        default_name = f"rack_report_{datetime.now().strftime('%Y-%m-%d_%H-%M')}.xlsx"
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save",
            default_name,   # 🔥 auto filename
            "Excel (*.xlsx)"
        )

        if not path:
            return

        import re

        def rack_sort_key(x):
            nums = re.findall(r'\d+', str(x))
            return int(nums[0]) if nums else 0

        racks = sorted(
            self.filtered_df["Current Rack Grp"].dropna().unique(),
            key=rack_sort_key
        )

        data = []

        for r in racks:
            trays = self.filtered_df[
                self.filtered_df["Current Rack Grp"] == r
            ]["Tray Code"].drop_duplicates().astype(str).tolist()

            if trays:
                row = {"Rack": r}

                # 🔥 Spread trays across columns
                for i, tray in enumerate(trays, start=1):
                    row[f"Tray{i}"] = tray

                data.append(row)

        final_df = pd.DataFrame(data)

        # 🔥 Fill missing cells (important for clean Excel)
        final_df = final_df.fillna("")

        final_df.to_excel(path, index=False)

    def select_all_racks(self):
        self.rack_list.blockSignals(True)
        for i in range(self.rack_list.count()):
            item = self.rack_list.item(i)
            item.setData(Qt.CheckStateRole, Qt.Checked)
        self.rack_list.blockSignals(False)
        self.filter_rack()
    
    
    def clear_all_racks(self):
        self.rack_list.blockSignals(True)
        for i in range(self.rack_list.count()):
            item = self.rack_list.item(i)
            item.setData(Qt.CheckStateRole, Qt.Unchecked)
        self.rack_list.blockSignals(False)
        self.filter_rack()

    def print_selected_racks(self):
        if self.filtered_df is None:
            return

        selected_racks = []

        for i in range(self.rack_list.count()):
            item = self.rack_list.item(i)
            if item.data(Qt.CheckStateRole) == Qt.Checked:
                rack = item.text().split(" (")[0]
                selected_racks.append(rack)

        if not selected_racks:
            QMessageBox.warning(self, "No Selection", "Select at least one rack")
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "Save Print File", "", "Excel (*.xlsx)"
        )

        if not path:
            return

        with pd.ExcelWriter(path, engine="openpyxl") as writer:
            for rack in selected_racks:
                df = self.filtered_df[
                    self.filtered_df["Current Rack Grp"] == rack
                ]

                if "Tray Code" in df.columns:
                    df = df.drop_duplicates(subset=["Tray Code"])

                df.to_excel(writer, sheet_name=str(rack)[:30], index=False)

        QMessageBox.information(self, "Done", "Rack print file created")

    def print_selected_racks_pdf(self):
        if self.filtered_df is None:
            return

        import getpass
        from datetime import datetime

        selected_racks = []

        for i in range(self.rack_list.count()):
            item = self.rack_list.item(i)
            if item.data(Qt.CheckStateRole) == Qt.Checked:
                rack = item.text().split(" (")[0]
                selected_racks.append(rack)

        if not selected_racks:
            QMessageBox.warning(self, "No Selection", "Select at least one rack")
            return

        username = getpass.getuser()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 🔥 BUILD HTML
        html = f"""
        <html>
        <head>
        <style>
            body {{ font-family: Segoe UI; font-size: 9pt; margin: 5px; }}

            h1 {{ color: #58a6ff; margin-bottom: 5px; }}
            h2 {{ color: #238636; margin: 2px 0; font-size: 10pt; }}

            .meta {{
                margin-bottom: 5px;
                font-size: 8pt;
                color: #555;
            }}

            table {{
                border-collapse: collapse;
                width: 100%;
                margin-bottom: 5px;
            }}

            td {{
                padding: 3px;
                border: 1px solid #ccc;
                font-size: 8pt;
            }}

            .b2b {{ background-color: #e3f2fd; }}
            .b2c {{ background-color: #fff3cd; }}
        </style>
        </head>
        <body>


        <h5>Rack Report</h5>

        <div class="meta">
            Generated by: {username} <br>
            Generated on: {timestamp} <br>
            Total Racks: {len(selected_racks)}
        </div>
        """

        for rack in selected_racks:
            df = self.filtered_df[
                self.filtered_df["Current Rack Grp"] == rack
            ]

            # 🔥 LIMIT TO REQUIRED COLUMNS ONLY
            df = df[[c for c in DISPLAY_COLUMNS if c in df.columns]]

            if "Tray Code" in df.columns:
                df = df.drop_duplicates(subset=["Tray Code"])

            html += f"<h6>Rack: {rack}</h6>"
            html += "<table>"

            # Rows with conditional coloring
            for _, row in df.iterrows():
                order_type = str(row.get("Order Type", "")).upper()

                row_class = ""
                if "B2B" in order_type:
                    row_class = "b2b"
                elif "B2C" in order_type:
                    row_class = "b2c"

                html += f"<tr class='{row_class}'>"

                for val in row:
                    html += f"<td>{str(val)}</td>"

                html += "</tr>"

            html += "</table>"

        html += "</body></html>"

        # 🔥 CREATE DOCUMENT
        doc = QTextDocument()
        doc.setHtml(html)

        # 🔥 AUTO PDF SAVE
        printer = QPrinter(QPrinter.HighResolution)
        printer.setOutputFormat(QPrinter.PdfFormat)
        printer.setOutputFileName("rack_report.pdf")

        doc.print_(printer)

        # 🔥 OPEN PRINT DIALOG (OPTIONAL)
        dialog = QPrintDialog(printer, self)
        if dialog.exec() == QPrintDialog.Accepted:
            doc.print_(printer)

        QMessageBox.information(self, "Done", "PDF created + print ready")

    def change_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Data Folder")

        if not folder:
            return

        # Save to config
        self.config["data_folder"] = folder
        self.save_json(CONFIG_FILE, self.config)

        # Reload files immediately
        self.load_files()

    # =========================
    # FILES
    # =========================
    def load_files(self):
        folder = self.config.get("data_folder")

        if not folder or not os.path.exists(folder):
            folder = QFileDialog.getExistingDirectory(self, "Select Folder")
            if not folder:
                return

            self.config["data_folder"] = folder
            self.save_json(CONFIG_FILE, self.config)

        self.folder = folder

        files = [
    f for f in os.listdir(folder)
    if f.lower().endswith(".xlsx") and "tray_status" in f.lower()
]
        files.sort(key=lambda x: os.path.getmtime(os.path.join(folder, x)), reverse=True)

        self.file_box.clear()
        self.file_box.addItems(files)

        if files:
            self.file_box.setCurrentIndex(0)

    def load_file(self):
        file = self.file_box.currentText()
        path = os.path.join(self.folder, file)

        df = pd.read_excel(path, header=2)
        df = process_df(df)

        self.df = df
        self.populate_filters()
        self.apply_filters()

    def update_metrics(self, df):
        total = len(self.df) if self.df is not None else 0
        filtered = len(df)
        racks = df["Current Rack Grp"].nunique() if "Current Rack Grp" in df.columns else 0

        self.total_label.setText(f"Total: {total}")
        self.filtered_label.setText(f"Filtered: {filtered}")
        self.rack_count_label.setText(f"Racks: {racks}")

    def update_license_status(self):
        ok, msg, lic = validate_license()
    
        if not ok:
            self.license_label.setText(f"License: ❌ {msg}")
            self.license_label.setStyleSheet("color:red; font-weight:bold;")
            return
    
        expiry = lic.get("expires", "N/A").split("T")[0]
    
        try:
            days_left = (datetime.fromisoformat(lic["expires"]) - datetime.now()).days
        except:
            days_left = 0
    
        if days_left <= 3:
            color = "#ff4d4d"
        elif days_left <= 10:
            color = "#f2cc60"
        else:
            color = "#3fb950"
    
        self.license_label.setStyleSheet(f"color:{color}; font-weight:bold;")
        self.license_label.setText(
            f"License: ✅ Active | Expires: {expiry} ({days_left} days)"
        )

    def auto_refresh(self):
        if not hasattr(self, "folder"):
            return

        files = [
            f for f in os.listdir(self.folder)
            if f.lower().endswith(".xlsx") and "tray_status" in f.lower()
        ]

        if not files:
            return

        files.sort(key=lambda x: os.path.getmtime(os.path.join(self.folder, x)), reverse=True)
        latest = files[0]

        # ?? ALWAYS reload latest file
        self.file_box.setCurrentText(latest)
        self.load_file()

    def populate_filters(self):
        self.order.populate(self.df["Order Type"].dropna().unique(), self.filters["order_type"])
        self.route.populate(self.df["Route Type"].dropna().unique(), self.filters["route_type"])
        self.slot.populate(self.df["Routetype"].dropna().unique(), self.filters["slot"])
        self.cls.populate(self.df["Order Class"].dropna().unique(), self.filters["order_class"])

    # =========================
    # PRESETS
    # =========================
    def save_preset(self):
        name, ok = QInputDialog.getText(self, "Preset", "Preset Name")
        if not ok or not name:
            return

        # 🔥 GET FROM TIME
        from_time, ok1 = QInputDialog.getText(
            self, "From Time", "Enter From Time (HH:MM:SS)", text="00:00:00"
        )
        if not ok1:
            return

        # 🔥 GET TO TIME
        to_time, ok2 = QInputDialog.getText(
            self, "To Time", "Enter To Time (HH:MM:SS)", text="23:59:59"
        )
        if not ok2:
            return

        preset_data = self.filters.copy()
        preset_data["from_time"] = from_time
        preset_data["to_time"] = to_time

        self.presets[name] = preset_data
        self.save_json(PRESET_FILE, self.presets)

        if self.preset_box.findText(name) == -1:
            self.preset_box.addItem(name)

    def load_preset(self):
        name = self.preset_box.currentText()
        if name in self.presets:
            p = self.presets[name]

            self.filters["order_type"] = p.get("order_type") or p.get("order", [])
            self.filters["route_type"] = p.get("route_type") or p.get("route", [])
            self.filters["slot"] = p.get("slot", [])
            self.filters["order_class"] = p.get("order_class") or p.get("class", [])

            self.populate_filters()
            self.apply_filters()

    def run_all_presets(self):
        import time

        print("🚀 Running all presets...")

        now = get_shift_now()
        print("🕒 Shift Time:", now)

        for name, preset in self.presets.items():
            print(f"👉 Checking preset: {name}")

            from_time = preset.get("from_time", "00:00:00")
            to_time = preset.get("to_time", "23:59:59")

            ft = datetime.strptime(from_time, "%H:%M:%S").time()
            tt = datetime.strptime(to_time, "%H:%M:%S").time()

            # 🔥 TIME FILTER
            if ft <= tt:
                valid = ft <= now <= tt
            else:
                valid = now >= ft or now <= tt

            if not valid:
                print(f"⏭ Skipping {name} (outside time range)")
                continue
                

            print(f"✅ Running preset: {name}")

            # APPLY FILTERS
            self.filters["order_type"] = preset.get("order_type", [])
            self.filters["route_type"] = preset.get("route_type", [])
            self.filters["slot"] = preset.get("slot", [])
            self.filters["order_class"] = preset.get("order_class", [])

            self.populate_filters()
            self.apply_filters()

            QApplication.processEvents()
            time.sleep(1)

            # ❌ SKIP EMPTY
            if self.filtered_df is None or self.filtered_df.empty:
                print(f"⚠️ No data for {name}, skipping")
                continue

            # 📩 SEND
            self.send_preset_to_telegram(name, preset)

            time.sleep(2)

        print("✅ All presets done")

    def send_preset_to_telegram(self, preset_name, preset):
        import requests

        BOT_TOKEN = "8663778811:AAEqvTZYh8Lx6PocVh6zEVCEtF9I59VGdIo"
        CHAT_ID = "-5117824741"

        slot = ", ".join(self.filters.get("slot", [])) or "All"
        order_type = ", ".join(self.filters.get("order_type", [])) or "All"
        route_type = ", ".join(self.filters.get("route_type", [])) or "All"

        from_time = preset.get("from_time", "00:00:00")
        to_time = preset.get("to_time", "23:59:59")

        # 🔥 HEADER
        lines = [
            f"📦 {preset_name}",
            f"🕒 {from_time} → {to_time}",
            f"📍 Slot: {slot}",
            f"📦 Order: {order_type}",
            f"🚚 Route: {route_type}",
            ""
        ]

        racks = self.filtered_df.groupby("Current Rack Grp")

        for rack, df in racks:
            trays = df["Tray Code"].drop_duplicates().astype(str).tolist()
            if trays:
                lines.append(f"{rack}  " + "  ".join(trays))

        message = "\n".join(lines)

        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            data={"chat_id": CHAT_ID, "text": message}
        )

    # =========================
    # JSON
    # =========================
    def load_json(self, p):
        return json.load(open(p)) if os.path.exists(p) else {}

    def save_json(self, p, d):
        json.dump(d, open(p, "w"), indent=4)

# =========================
# START
# =========================
if __name__ == "__main__":
    ok, msg, _ = validate_license()
    if not ok:
        app = QApplication(sys.argv)
        QMessageBox.critical(None, "License Error", msg)
        sys.exit()

    QTimer.singleShot(5000, lambda: threading.Thread(target=background_check, daemon=True).start())

    app = QApplication(sys.argv)
    win = App()
    win.show()
    sys.exit(app.exec())