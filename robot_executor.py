import sys
import os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLabel, QSpinBox, QComboBox, QGridLayout, QGroupBox,
                             QMessageBox, QSplitter, QTextEdit, QApplication,
                             QPlainTextEdit, QScrollArea, QFrame, QSizePolicy)
from PyQt6.QtGui import QPainter, QColor, QPen, QFont, QBrush, QPixmap, QIcon, QTextCursor, QSyntaxHighlighter, \
    QTextCharFormat
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QSize, QPoint, QRegularExpression
from enum import Enum


class Direction(Enum):
    UP = 0
    RIGHT = 1
    DOWN = 2
    LEFT = 3


class CellType(Enum):
    EMPTY = 0
    WALL = 1
    MARKED = 2
    ROBOT = 3


class RobotSyntaxHighlighter(QSyntaxHighlighter):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.highlighting_rules = []

        # Ключевые слова
        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor("#FF79C6"))
        keyword_format.setFontWeight(QFont.Weight.Bold)
        keywords = ["нц", "кц", "пока", "если", "то", "иначе", "все", "выбор", "при", "и", "или", "не", "для", "от",
                    "до", "шаг"]
        for word in keywords:
            pattern = QRegularExpression(r"\b" + word + r"\b")
            self.highlighting_rules.append((pattern, keyword_format))

        # Команды робота
        command_format = QTextCharFormat()
        command_format.setForeground(QColor("#50FA7B"))
        command_format.setFontWeight(QFont.Weight.Bold)
        commands = ["вверх", "вниз", "влево", "вправо", "закрасить", "свободно", "слева", "справа", "сверху", "снизу"]
        for word in commands:
            pattern = QRegularExpression(r"\b" + word + r"\b")
            self.highlighting_rules.append((pattern, command_format))

        # Условия
        condition_format = QTextCharFormat()
        condition_format.setForeground(QColor("#8BE9FD"))
        conditions = ["стена", "краска", "не_stena", "не_краска"]
        for word in conditions:
            pattern = QRegularExpression(r"\b" + word + r"\b")
            self.highlighting_rules.append((pattern, condition_format))

        # Числа
        number_format = QTextCharFormat()
        number_format.setForeground(QColor("#BD93F9"))
        pattern = QRegularExpression(r"\b\d+\b")
        self.highlighting_rules.append((pattern, number_format))

        # Комментарии
        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor("#6272A4"))
        pattern = QRegularExpression(r"\|[^\n]*")
        self.highlighting_rules.append((pattern, comment_format))

    def highlightBlock(self, text):
        for pattern, format in self.highlighting_rules:
            match_iterator = pattern.globalMatch(text)
            while match_iterator.hasNext():
                match = match_iterator.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), format)


class RobotExecutor(QWidget):
    execution_finished = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.grid_size = 15
        self.cell_size = 30
        self.robot_pos = QPoint(0, 0)
        self.robot_direction = Direction.RIGHT
        self.grid = [[CellType.EMPTY for _ in range(self.grid_size)] for _ in range(self.grid_size)]
        self.is_running = False
        self.current_command_index = 0
        self.commands = []
        self.speed = 500
        self.timer = QTimer()
        self.timer.timeout.connect(self.execute_next_command)
        self.variables = {}  # Для хранения переменных циклов

        self.init_ui()

    def init_ui(self):
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # Левая панель - поле и управление
        left_panel = QVBoxLayout()
        left_panel.setSpacing(10)

        # Панель управления полем
        control_panel = QHBoxLayout()

        self.clear_btn = QPushButton("Очистить поле")
        self.clear_btn.clicked.connect(self.clear_grid)
        control_panel.addWidget(self.clear_btn)

        self.add_walls_btn = QPushButton("Режим стен")
        self.add_walls_btn.setCheckable(True)
        self.add_walls_btn.clicked.connect(self.toggle_wall_mode)
        control_panel.addWidget(self.add_walls_btn)

        control_panel.addStretch()

        size_label = QLabel("Размер:")
        control_panel.addWidget(size_label)

        self.size_spin = QSpinBox()
        self.size_spin.setRange(5, 30)
        self.size_spin.setValue(self.grid_size)
        self.size_spin.valueChanged.connect(self.resize_grid)
        control_panel.addWidget(self.size_spin)

        left_panel.addLayout(control_panel)

        # Поле для рисования
        self.grid_widget = GridWidget(self)
        self.grid_widget.setMinimumSize(500, 500)
        left_panel.addWidget(self.grid_widget)

        left_widget = QWidget()
        left_widget.setLayout(left_panel)
        main_layout.addWidget(left_widget)

        # Правая панель - программирование и информация
        right_panel = QVBoxLayout()
        right_panel.setSpacing(10)

        # Группа программирования - УВЕЛИЧЕНА
        program_group = QGroupBox("Программирование Робота")
        program_layout = QVBoxLayout()
        program_layout.setSpacing(8)

        # Редактор кода - УВЕЛИЧЕН
        self.code_editor = QPlainTextEdit()
        self.code_editor.setPlaceholderText("""нц пока справа свободно
  вправо
  закрасить
  если справа стена то
    вниз
  все
кц""")
        self.code_editor.setMinimumHeight(300)  # Увеличенная высота
        self.code_editor.setStyleSheet("""
            QPlainTextEdit {
                font-family: "Courier New";
                font-size: 12px;
                background-color: #282a36;
                color: #f8f8f2;
                border: 2px solid #44475a;
                border-radius: 5px;
                padding: 8px;
            }
        """)

        # Подсветка синтаксиса
        self.highlighter = RobotSyntaxHighlighter(self.code_editor.document())

        program_layout.addWidget(self.code_editor)

        # Кнопки управления выполнением
        exec_buttons_layout = QHBoxLayout()
        exec_buttons_layout.setSpacing(5)

        self.run_btn = QPushButton("Запуск")
        self.run_btn.setStyleSheet("""
            QPushButton {
                background-color: #50fa7b;
                color: #282a36;
                font-weight: bold;
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #69ff94;
            }
            QPushButton:disabled {
                background-color: #6272a4;
                color: #f8f8f2;
            }
        """)
        self.run_btn.clicked.connect(self.start_execution)
        exec_buttons_layout.addWidget(self.run_btn)

        self.step_btn = QPushButton("Шаг")
        self.step_btn.setStyleSheet("""
            QPushButton {
                background-color: #8be9fd;
                color: #282a36;
                font-weight: bold;
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #a4f2ff;
            }
        """)
        self.step_btn.clicked.connect(self.execute_step)
        exec_buttons_layout.addWidget(self.step_btn)

        self.stop_btn = QPushButton("Стоп")
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #ff5555;
                color: #282a36;
                font-weight: bold;
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #ff6e6e;
            }
            QPushButton:disabled {
                background-color: #6272a4;
                color: #f8f8f2;
            }
        """)
        self.stop_btn.clicked.connect(self.stop_execution)
        exec_buttons_layout.addWidget(self.stop_btn)

        program_layout.addLayout(exec_buttons_layout)

        # Настройки скорости
        speed_layout = QHBoxLayout()
        speed_layout.addWidget(QLabel("Скорость:"))

        self.speed_combo = QComboBox()
        self.speed_combo.addItems(["Очень медленно", "Медленно", "Нормально", "Быстро", "Очень быстро"])
        self.speed_combo.setCurrentIndex(2)
        self.speed_combo.currentIndexChanged.connect(self.change_speed)
        self.speed_combo.setStyleSheet("""
            QComboBox {
                background-color: #44475a;
                color: #f8f8f2;
                border: 1px solid #6272a4;
                border-radius: 3px;
                padding: 5px;
                min-width: 120px;
            }
        """)
        speed_layout.addWidget(self.speed_combo)
        speed_layout.addStretch()

        program_layout.addLayout(speed_layout)

        program_group.setLayout(program_layout)
        program_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 14px;
                color: #f8f8f2;
                border: 2px solid #44475a;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        right_panel.addWidget(program_group)

        # Группа подсказок - УВЕЛИЧЕНА
        help_group = QGroupBox("Подсказка: Команды Робота")
        help_layout = QVBoxLayout()

        help_text = QTextEdit()
        help_text.setReadOnly(True)
        help_text.setMinimumHeight(250)  # Увеличенная высота
        help_text.setStyleSheet("""
            QTextEdit {
                background-color: #282a36;
                color: #f8f8f2;
                border: 1px solid #44475a;
                border-radius: 5px;
                font-size: 11px;
                padding: 8px;
            }
        """)
        help_text.setHtml("""
        <h3 style="color: #ff79c6; margin-top: 0;">Основные команды:</h3>
        <ul style="margin: 0; padding-left: 15px;">
        <li><b style="color: #50fa7b;">вверх</b> - переместить робота вверх</li>
        <li><b style="color: #50fa7b;">вниз</b> - переместить робота вниз</li>
        <li><b style="color: #50fa7b;">влево</b> - переместить робота влево</li>
        <li><b style="color: #50fa7b;">вправо</b> - переместить робота вправо</li>
        <li><b style="color: #50fa7b;">закрасить</b> - закрасить текущую клетку</li>
        </ul>

        <h3 style="color: #ff79c6;">Условия:</h3>
        <ul style="margin: 0; padding-left: 15px;">
        <li><b style="color: #8be9fd;">справа свободно</b> - справа нет стены</li>
        <li><b style="color: #8be9fd;">справа стена</b> - справа есть стена</li>
        <li><b style="color: #8be9fd;">слева свободно</b> - слева нет стены</li>
        <li><b style="color: #8be9fd;">слева стена</b> - слева есть стена</li>
        <li><b style="color: #8be9fd;">сверху свободно</b> - сверху нет стены</li>
        <li><b style="color: #8be9fd;">сверху стена</b> - сверху есть стена</li>
        <li><b style="color: #8be9fd;">снизу свободно</b> - снизу нет стены</li>
        <li><b style="color: #8be9fd;">снизу стена</b> - снизу есть стена</li>
        </ul>

        <h3 style="color: #ff79c6;">Циклы:</h3>
        <ul style="margin: 0; padding-left: 15px;">
        <li><b>нц пока условие</b><br>...<br><b>кц</b> - цикл с предусловием</li>
        <li><b>нц</b><br>...<br><b>кц при условие</b> - цикл с постусловием</li>
        <li><b>нц для i от 1 до 5</b><br>...<br><b>кц</b> - цикл со счетчиком</li>
        </ul>

        <h3 style="color: #ff79c6;">Условия:</h3>
        <ul style="margin: 0; padding-left: 15px;">
        <li><b>если условие то</b><br>...<br><b>все</b> - простое условие</li>
        <li><b>если условие то</b><br>...<br><b>иначе</b><br>...<br><b>все</b> - условие с иначе</li>
        </ul>
        """)
        help_layout.addWidget(help_text)

        help_group.setLayout(help_layout)
        help_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 14px;
                color: #f8f8f2;
                border: 2px solid #44475a;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        right_panel.addWidget(help_group)

        # Группа информации - УВЕЛИЧЕНА
        info_group = QGroupBox("Информация")
        info_layout = QVBoxLayout()

        self.info_text = QTextEdit()
        self.info_text.setReadOnly(True)
        self.info_text.setMinimumHeight(120)  # Увеличенная высота
        self.info_text.setStyleSheet("""
            QTextEdit {
                background-color: #282a36;
                color: #f8f8f2;
                border: 1px solid #44475a;
                border-radius: 5px;
                font-family: "Courier New";
                font-size: 12px;
                padding: 8px;
            }
        """)
        info_layout.addWidget(self.info_text)

        info_group.setLayout(info_layout)
        info_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 14px;
                color: #f8f8f2;
                border: 2px solid #44475a;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        right_panel.addWidget(info_group)

        right_widget = QWidget()
        right_widget.setLayout(right_panel)
        right_widget.setMinimumWidth(450)  # Увеличенная минимальная ширина
        right_widget.setMaximumWidth(500)
        main_layout.addWidget(right_widget)

        self.setLayout(main_layout)
        self.update_info()

    def toggle_wall_mode(self):
        self.grid_widget.wall_mode = self.add_walls_btn.isChecked()

    def clear_grid(self):
        self.grid = [[CellType.EMPTY for _ in range(self.grid_size)] for _ in range(self.grid_size)]
        self.robot_pos = QPoint(0, 0)
        self.robot_direction = Direction.RIGHT
        self.variables = {}
        self.grid_widget.update()
        self.update_info()

    def resize_grid(self, new_size):
        self.grid_size = new_size
        self.grid = [[CellType.EMPTY for _ in range(self.grid_size)] for _ in range(self.grid_size)]
        if self.robot_pos.x() >= self.grid_size or self.robot_pos.y() >= self.grid_size:
            self.robot_pos = QPoint(0, 0)
        self.grid_widget.update()

    def parse_program(self, code):
        """Парсит текст программы в список команд с поддержкой всех циклов и условий"""
        # Сохраняем оригинальные строки с отступами
        original_lines = code.split('\n')
        lines = []

        # Обрабатываем каждую строку, сохраняя информацию об отступах
        for line in original_lines:
            stripped_line = line.strip()
            # Пропускаем пустые строки и комментарии
            if not stripped_line or stripped_line.startswith('|'):
                continue

            # Сохраняем информацию об отступах в самой строке
            indent_level = len(line) - len(line.lstrip())
            lines.append({
                'text': stripped_line,
                'indent': indent_level,
                'original': line
            })

        commands = []
        i = 0

        while i < len(lines):
            line_info = lines[i]
            line = line_info['text']
            indent = line_info['indent']

            # Простые команды движения
            if line == 'вверх':
                commands.append('up')
            elif line == 'вниз':
                commands.append('down')
            elif line == 'влево':
                commands.append('left')
            elif line == 'вправо':
                commands.append('right')
            elif line == 'закрасить':
                commands.append('mark')

            # Цикл с предусловием "нц пока ... кц"
            elif line.startswith('нц пока'):
                condition_text = line.replace('нц пока', '').strip()
                condition = self.parse_condition(condition_text)

                # Ищем конец цикла по отступам
                end_index = self.find_matching_kc_by_indent(lines, i, indent)
                if end_index == -1:
                    raise Exception("Не найден конец цикла 'кц'")

                # Извлекаем тело цикла (строки с большим отступом)
                body_lines = []
                for j in range(i + 1, end_index):
                    if lines[j]['indent'] > indent:  # Только строки с большим отступом
                        body_lines.append(lines[j]['text'])

                body_commands = self.parse_body_commands(body_lines)

                commands.append({
                    'type': 'while',
                    'condition': condition,
                    'body': body_commands,
                    'current_body_index': 0
                })

                i = end_index

            # Цикл с постусловием "нц ... кц при ..."
            elif line == 'нц':
                # Ищем соответствующий "кц при" по отступам
                end_index = self.find_matching_kc_pri_by_indent(lines, i, indent)
                if end_index == -1:
                    raise Exception("Не найден конец цикла 'кц при'")

                condition_text = lines[end_index]['text'].replace('кц при', '').strip()
                condition = self.parse_condition(condition_text)

                # Извлекаем тело цикла
                body_lines = []
                for j in range(i + 1, end_index):
                    if lines[j]['indent'] > indent:
                        body_lines.append(lines[j]['text'])

                body_commands = self.parse_body_commands(body_lines)

                commands.append({
                    'type': 'do_while',
                    'condition': condition,
                    'body': body_commands,
                    'current_body_index': 0,
                    'first_execution': True
                })

                i = end_index

            # Цикл со счетчиком "нц для ... от ... до ..."
            elif line.startswith('нц для'):
                # Парсим параметры цикла
                parts = line.split()
                if len(parts) < 6 or parts[1] != 'для' or parts[3] != 'от' or parts[5] != 'до':
                    raise Exception("Неверный формат цикла для. Пример: 'нц для i от 1 до 5'")

                var_name = parts[2]
                start_val = int(parts[4])
                end_val = int(parts[6])

                # Опциональный шаг
                step = 1
                if len(parts) > 7 and parts[7] == 'шаг':
                    step = int(parts[8])

                # Ищем конец цикла по отступам
                end_index = self.find_matching_kc_by_indent(lines, i, indent)
                if end_index == -1:
                    raise Exception("Не найден конец цикла 'кц'")

                # Извлекаем тело цикла
                body_lines = []
                for j in range(i + 1, end_index):
                    if lines[j]['indent'] > indent:
                        body_lines.append(lines[j]['text'])

                body_commands = self.parse_body_commands(body_lines)

                commands.append({
                    'type': 'for',
                    'var_name': var_name,
                    'start': start_val,
                    'end': end_val,
                    'step': step,
                    'current': start_val,
                    'body': body_commands,
                    'current_body_index': 0
                })

                i = end_index

            # Условие "если ... то ..."
            elif line.startswith('если'):
                # Ищем "все" по отступам
                all_index = self.find_matching_all_by_indent(lines, i, indent)
                if all_index == -1:
                    raise Exception("Не найден конец условия 'все'")

                # Проверяем есть ли "иначе"
                else_index = -1
                for j in range(i + 1, all_index):
                    if lines[j]['text'] == 'иначе' and lines[j]['indent'] == indent:
                        else_index = j
                        break

                # Парсим условие
                condition_text = line.replace('если', '').replace('то', '').strip()
                condition = self.parse_condition(condition_text)

                # Парсим тело then
                then_end = else_index if else_index != -1 else all_index
                then_lines = []
                for j in range(i + 1, then_end):
                    if lines[j]['indent'] > indent:
                        then_lines.append(lines[j]['text'])
                then_commands = self.parse_body_commands(then_lines)

                # Парсим тело else (если есть)
                else_commands = []
                if else_index != -1:
                    else_lines = []
                    for j in range(else_index + 1, all_index):
                        if lines[j]['indent'] > indent:
                            else_lines.append(lines[j]['text'])
                    else_commands = self.parse_body_commands(else_lines)

                commands.append({
                    'type': 'if',
                    'condition': condition,
                    'then_body': then_commands,
                    'else_body': else_commands,
                    'current_then_index': 0,
                    'current_else_index': 0,
                    'executed': False
                })

                i = all_index

            i += 1

        return commands

    def find_matching_kc_by_indent(self, lines, start_index, base_indent):
        """Находит соответствующий 'кц' для цикла по отступам"""
        for i in range(start_index + 1, len(lines)):
            if lines[i]['indent'] == base_indent and lines[i]['text'] == 'кц':
                return i
        return -1

    def find_matching_kc_pri_by_indent(self, lines, start_index, base_indent):
        """Находит соответствующий 'кц при' для цикла с постусловием по отступам"""
        for i in range(start_index + 1, len(lines)):
            if (lines[i]['indent'] == base_indent and
                    (lines[i]['text'].startswith('кц при') or lines[i]['text'] == 'кц')):
                return i
        return -1

    def find_matching_all_by_indent(self, lines, start_index, base_indent):
        """Находит соответствующий 'все' для условия по отступам"""
        for i in range(start_index + 1, len(lines)):
            if lines[i]['indent'] == base_indent and lines[i]['text'] == 'все':
                return i
        return -1

    def parse_body_commands(self, lines):
        """Парсит тело циклов и условий"""
        commands = []
        i = 0

        while i < len(lines):
            line = lines[i]

            if line == 'вверх':
                commands.append('up')
            elif line == 'вниз':
                commands.append('down')
            elif line == 'влево':
                commands.append('left')
            elif line == 'вправо':
                commands.append('right')
            elif line == 'закрасить':
                commands.append('mark')
            # Обработка вложенных конструкций будет происходить в основном парсере
            i += 1

        return commands

    def parse_condition(self, condition_text):
        """Парсит условие"""
        condition_text = condition_text.strip()

        conditions_map = {
            'справа свободно': 'right_free',
            'справа стена': 'right_wall',
            'слева свободно': 'left_free',
            'слева стена': 'left_wall',
            'сверху свободно': 'top_free',
            'сверху стена': 'top_wall',
            'снизу свободно': 'bottom_free',
            'снизу стена': 'bottom_wall'
        }

        return conditions_map.get(condition_text, condition_text)

    def check_condition(self, condition):
        """Проверяет условие"""
        x, y = self.robot_pos.x(), self.robot_pos.y()

        conditions_map = {
            'right_free': x + 1 < self.grid_size and self.grid[y][x + 1] != CellType.WALL,
            'right_wall': x + 1 >= self.grid_size or self.grid[y][x + 1] == CellType.WALL,
            'left_free': x - 1 >= 0 and self.grid[y][x - 1] != CellType.WALL,
            'left_wall': x - 1 < 0 or self.grid[y][x - 1] == CellType.WALL,
            'top_free': y - 1 >= 0 and self.grid[y - 1][x] != CellType.WALL,
            'top_wall': y - 1 < 0 or self.grid[y - 1][x] == CellType.WALL,
            'bottom_free': y + 1 < self.grid_size and self.grid[y + 1][x] != CellType.WALL,
            'bottom_wall': y + 1 >= self.grid_size or self.grid[y + 1][x] == CellType.WALL
        }

        return conditions_map.get(condition, False)

    def start_execution(self):
        code = self.code_editor.toPlainText().strip()
        if not code:
            QMessageBox.warning(self, "Предупреждение", "Введите программу для выполнения!")
            return

        try:
            self.commands = self.parse_program(code)
            if not self.commands:
                QMessageBox.warning(self, "Предупреждение", "Не удалось распознать команды!")
                return

            self.is_running = True
            self.current_command_index = 0
            self.run_btn.setEnabled(False)
            self.step_btn.setEnabled(False)
            self.timer.start(self.speed)

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка в программе: {str(e)}")

    def stop_execution(self):
        self.is_running = False
        self.timer.stop()
        self.run_btn.setEnabled(True)
        self.step_btn.setEnabled(True)

    def execute_step(self):
        if self.current_command_index < len(self.commands):
            self.execute_command(self.commands[self.current_command_index])
        else:
            self.stop_execution()

    def execute_next_command(self):
        if self.current_command_index >= len(self.commands):
            self.stop_execution()
            self.execution_finished.emit()
            return

        self.execute_command(self.commands[self.current_command_index])

    def execute_command(self, command):
        try:
            if isinstance(command, dict):
                if command['type'] == 'while':
                    self.execute_while_loop(command)
                elif command['type'] == 'do_while':
                    self.execute_do_while_loop(command)
                elif command['type'] == 'for':
                    self.execute_for_loop(command)
                elif command['type'] == 'if':
                    self.execute_if_statement(command)
            else:
                # Простые команды
                self.execute_simple_command(command)
                self.current_command_index += 1

            self.grid_widget.update()
            self.update_info()

        except Exception as e:
            self.stop_execution()
            QMessageBox.critical(self, "Ошибка", f"Ошибка выполнения: {str(e)}")

    def execute_if_statement(self, if_command):
        """Выполняет условие если...то...иначе...все"""
        if not if_command['executed']:
            # Первое выполнение - проверяем условие
            if self.check_condition(if_command['condition']):
                # Условие истинно - выполняем then_body
                if_command['branch'] = 'then'
            else:
                # Условие ложно - выполняем else_body (если есть)
                if_command['branch'] = 'else' if if_command['else_body'] else None

            if_command['executed'] = True

        # Выполняем команды из выбранной ветки
        if if_command['branch'] == 'then':
            if if_command['current_then_index'] < len(if_command['then_body']):
                body_command = if_command['then_body'][if_command['current_then_index']]
                if isinstance(body_command, dict) and body_command['type'] == 'if':
                    self.execute_if_statement(body_command)
                else:
                    self.execute_simple_command(body_command)
                if_command['current_then_index'] += 1
            else:
                # Завершили выполнение then ветки
                if_command['current_then_index'] = 0
                if_command['executed'] = False
                self.current_command_index += 1

        elif if_command['branch'] == 'else':
            if if_command['current_else_index'] < len(if_command['else_body']):
                body_command = if_command['else_body'][if_command['current_else_index']]
                if isinstance(body_command, dict) and body_command['type'] == 'if':
                    self.execute_if_statement(body_command)
                else:
                    self.execute_simple_command(body_command)
                if_command['current_else_index'] += 1
            else:
                # Завершили выполнение else ветки
                if_command['current_else_index'] = 0
                if_command['executed'] = False
                self.current_command_index += 1

        else:
            # Нет else ветки - просто завершаем
            if_command['executed'] = False
            self.current_command_index += 1

    def execute_simple_command(self, command):
        """Выполняет простую команду"""
        if command == 'up':
            self.move_robot('up')
        elif command == 'down':
            self.move_robot('down')
        elif command == 'left':
            self.move_robot('left')
        elif command == 'right':
            self.move_robot('right')
        elif command == 'mark':
            self.mark_cell()

    def execute_while_loop(self, loop_command):
        """Цикл с предусловием - проверяет условие ДО выполнения тела"""
        if self.check_condition(loop_command['condition']):
            # Условие истинно - выполняем тело
            if loop_command['current_body_index'] < len(loop_command['body']):
                body_command = loop_command['body'][loop_command['current_body_index']]
                self.execute_simple_command(body_command)
                loop_command['current_body_index'] += 1
            else:
                # Конец тела - сбрасываем индекс для следующей итерации
                loop_command['current_body_index'] = 0
        else:
            # Условие ложно - завершаем цикл
            loop_command['current_body_index'] = 0
            self.current_command_index += 1

    def execute_do_while_loop(self, loop_command):
        """Цикл с постусловием - выполняет тело ХОТЯ БЫ ОДИН РАЗ, затем проверяет условие"""
        if loop_command['first_execution'] or self.check_condition(loop_command['condition']):
            # Первое выполнение или условие истинно - выполняем тело
            loop_command['first_execution'] = False

            if loop_command['current_body_index'] < len(loop_command['body']):
                body_command = loop_command['body'][loop_command['current_body_index']]
                if isinstance(body_command, dict) and body_command['type'] == 'if':
                    self.execute_if_statement(body_command)
                else:
                    self.execute_simple_command(body_command)
                loop_command['current_body_index'] += 1
            else:
                # Конец тела - сбрасываем индекс и проверяем условие
                loop_command['current_body_index'] = 0
        else:
            # Условие ложно - завершаем цикл
            loop_command['current_body_index'] = 0
            loop_command['first_execution'] = True
            self.current_command_index += 1

    def execute_for_loop(self, loop_command):
        """Цикл со счетчиком"""
        if loop_command['current'] <= loop_command['end']:
            # Выполняем текущую команду из тела
            if loop_command['current_body_index'] < len(loop_command['body']):
                body_command = loop_command['body'][loop_command['current_body_index']]
                if isinstance(body_command, dict) and body_command['type'] == 'if':
                    self.execute_if_statement(body_command)
                else:
                    self.execute_simple_command(body_command)
                loop_command['current_body_index'] += 1
            else:
                # Конец тела - увеличиваем счетчик и сбрасываем индекс тела
                loop_command['current'] += loop_command['step']
                loop_command['current_body_index'] = 0
        else:
            # Цикл завершен
            self.current_command_index += 1

    def move_robot(self, direction):
        new_pos = QPoint(self.robot_pos)

        if direction == 'up':
            new_pos.setY(self.robot_pos.y() - 1)
            self.robot_direction = Direction.UP
        elif direction == 'right':
            new_pos.setX(self.robot_pos.x() + 1)
            self.robot_direction = Direction.RIGHT
        elif direction == 'down':
            new_pos.setY(self.robot_pos.y() + 1)
            self.robot_direction = Direction.DOWN
        elif direction == 'left':
            new_pos.setX(self.robot_pos.x() - 1)
            self.robot_direction = Direction.LEFT

        # Проверка границ и стен
        if (0 <= new_pos.x() < self.grid_size and
                0 <= new_pos.y() < self.grid_size and
                self.grid[new_pos.y()][new_pos.x()] != CellType.WALL):
            self.robot_pos = new_pos
        else:
            raise Exception(f"Робот не может двигаться {direction} - там стена или граница!")

    def mark_cell(self):
        if self.grid[self.robot_pos.y()][self.robot_pos.x()] == CellType.EMPTY:
            self.grid[self.robot_pos.y()][self.robot_pos.x()] = CellType.MARKED

    def change_speed(self, index):
        speeds = [1000, 500, 250, 100, 50]
        self.speed = speeds[index]
        if self.timer.isActive():
            self.timer.setInterval(self.speed)

    def update_info(self):
        direction_names = {
            Direction.UP: "Вверх",
            Direction.RIGHT: "Вправо",
            Direction.DOWN: "Вниз",
            Direction.LEFT: "Влево"
        }

        info = f"Позиция: ({self.robot_pos.x()}, {self.robot_pos.y()})\n"
        info += f"Направление: {direction_names[self.robot_direction]}\n"
        info += f"Команд в программе: {len(self.commands)}\n"

        if self.current_command_index < len(self.commands):
            current_command = self.commands[self.current_command_index]
            if isinstance(current_command, dict):
                info += f"Текущая команда: {current_command['type']}\n"
            else:
                info += f"Текущая команда: {current_command}\n"
        else:
            info += "Текущая команда: Завершено\n"

        self.info_text.setPlainText(info)


class GridWidget(QWidget):
    def __init__(self, executor):
        super().__init__()
        self.executor = executor
        self.wall_mode = False
        self.setMinimumSize(500, 500)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            cell_size = min(self.width() // self.executor.grid_size,
                            self.height() // self.executor.grid_size)
            x = event.pos().x() // cell_size
            y = event.pos().y() // cell_size

            if 0 <= x < self.executor.grid_size and 0 <= y < self.executor.grid_size:
                if self.wall_mode:
                    # Переключаем стену
                    if self.executor.grid[y][x] == CellType.EMPTY:
                        self.executor.grid[y][x] = CellType.WALL
                    elif self.executor.grid[y][x] == CellType.WALL:
                        self.executor.grid[y][x] = CellType.EMPTY
                else:
                    # Перемещаем робота
                    if self.executor.grid[y][x] != CellType.WALL:
                        self.executor.robot_pos = QPoint(x, y)

                self.update()
                self.executor.update_info()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        cell_size = min(self.width() // self.executor.grid_size,
                        self.height() // self.executor.grid_size)

        # Рисуем сетку
        painter.setPen(QPen(QColor("#44475a"), 1))
        for i in range(self.executor.grid_size + 1):
            # Вертикальные линии
            painter.drawLine(i * cell_size, 0, i * cell_size, self.executor.grid_size * cell_size)
            # Горизонтальные линии
            painter.drawLine(0, i * cell_size, self.executor.grid_size * cell_size, i * cell_size)

        # Рисуем клетки
        for y in range(self.executor.grid_size):
            for x in range(self.executor.grid_size):
                rect = (x * cell_size, y * cell_size, cell_size, cell_size)

                if self.executor.grid[y][x] == CellType.WALL:
                    painter.fillRect(*rect, QColor("#ff5555"))  # Красный для стен
                elif self.executor.grid[y][x] == CellType.MARKED:
                    painter.fillRect(*rect, QColor("#50fa7b"))  # Зеленый для закрашенных
                else:
                    painter.fillRect(*rect, QColor("#282a36"))  # Темный для пустых

        # Рисуем робота
        robot_x = self.executor.robot_pos.x() * cell_size
        robot_y = self.executor.robot_pos.y() * cell_size

        # Тело робота
        painter.setBrush(QBrush(QColor("#bd93f9")))  # Фиолетовый
        painter.drawEllipse(robot_x + 5, robot_y + 5, cell_size - 10, cell_size - 10)

        # Направление робота
        painter.setPen(QPen(QColor("#f8f8f2"), 3))
        center_x = robot_x + cell_size // 2
        center_y = robot_y + cell_size // 2

        if self.executor.robot_direction == Direction.UP:
            painter.drawLine(center_x, center_y, center_x, robot_y + 5)
        elif self.executor.robot_direction == Direction.RIGHT:
            painter.drawLine(center_x, center_y, robot_x + cell_size - 5, center_y)
        elif self.executor.robot_direction == Direction.DOWN:
            painter.drawLine(center_x, center_y, center_x, robot_y + cell_size - 5)
        elif self.executor.robot_direction == Direction.LEFT:
            painter.drawLine(center_x, center_y, robot_x + 5, center_y)


# Вкладка для исполнителя робота
class RobotExecutorTab(QWidget):
    def __init__(self):
        super().__init__()
        self.executor = RobotExecutor()
        layout = QVBoxLayout()
        layout.addWidget(self.executor)
        self.setLayout(layout)