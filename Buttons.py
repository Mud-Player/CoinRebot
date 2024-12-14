from PySide6.QtCore import QSize
from PySide6.QtWidgets import QWidget, QPushButton, QHBoxLayout, QButtonGroup


class ToggleButtons(QWidget):
    def __init__(self, name1, name2):
        super().__init__()
        # 创建按钮
        self.button1 = QPushButton(name1, self)
        self.button2 = QPushButton(name2, self)
        self.button1.setCheckable(True)
        self.button2.setCheckable(True)
        self.button1.setChecked(True)

        button_group = QButtonGroup(self)
        button_group.setExclusive(True)
        button_group.addButton(self.button1)
        button_group.addButton(self.button2)

        # 设置默认选中状态（Button 1 高亮）
        self.highlight_button(self.button1)
        self.dim_button(self.button2)

        # 布局
        layout = QHBoxLayout()
        layout.addWidget(self.button1)
        layout.addWidget(self.button2)
        self.setLayout(layout)

        self.setFixedSize(QSize(210, 60))

        # 连接按钮点击事件
        self.button1.clicked.connect(lambda: self.on_button_clicked(self.button1, self.button2))
        self.button2.clicked.connect(lambda: self.on_button_clicked(self.button2, self.button1))

    def button1_isChecked(self):
        return self.button1.isChecked()

    def button2_isChecked(self):
        return self.button2.isChecked()

    def on_button_clicked(self, clicked_button, other_button):
        """点击按钮时切换高亮和变暗状态"""
        self.highlight_button(clicked_button)
        self.dim_button(other_button)

    def highlight_button(self, button):
        """高亮按钮，使用样式表改变外观"""
        button.setStyleSheet("background-color: #01bc8d; font-weight: bold; color: white;"
                             "border: 1px solid #01bc8d; border-radius: 10px; padding: 10px 20px 10px 20px")


    def dim_button(self, button):
        """使按钮变暗，使用样式表改变外观"""
        button.setStyleSheet("background-color: #f4f5f7; color: #641517;"
                             "border: 1px solid #f4f5f7; border-radius: 10px; padding: 10px 20px 10px 20px")