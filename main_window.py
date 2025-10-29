import sys
import os
import traceback
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QTabWidget, QPlainTextEdit,
                             QMenuBar, QStatusBar, QMessageBox, QFileDialog,
                             QDockWidget, QTextEdit)
from PyQt6.QtGui import QAction, QFont, QColor, QPainter, QTextFormat
from PyQt6.QtCore import Qt, QRect, QSize


class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.code_editor = editor

    def sizeHint(self):
        return QSize(self.code_editor.line_number_area_width(), 0)

    def paintEvent(self, event):
        self.code_editor.line_number_area_paint_event(event)


class CodeEditor(QPlainTextEdit):
    def __init__(self):
        super().__init__()
        self.line_number_area = LineNumberArea(self)

        # Настройки редактора
        self.setFont(QFont("Consolas", 11))
        self.setTabStopDistance(20)  # Ширина табуляции

        # Связываем сигналы для обновления номеров строк
        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.cursorPositionChanged.connect(self.highlight_current_line)

        # Инициализируем ширину области номеров строк
        self.update_line_number_area_width(0)

        # Подсветка текущей строки
        self.highlight_current_line()

    def line_number_area_width(self):
        digits = 1
        max_num = max(1, self.blockCount())
        while max_num >= 10:
            max_num //= 10
            digits += 1
        space = 10 + self.fontMetrics().horizontalAdvance('9') * digits
        return space

    def update_line_number_area_width(self, _):
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def update_line_number_area(self, rect, dy):
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(0, rect.y(), self.line_number_area.width(), rect.height())

        if rect.contains(self.viewport().rect()):
            self.update_line_number_area_width(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.line_number_area.setGeometry(QRect(cr.left(), cr.top(),
                                                self.line_number_area_width(), cr.height()))

    def line_number_area_paint_event(self, event):
        painter = QPainter(self.line_number_area)
        painter.fillRect(event.rect(), QColor(240, 240, 240))  # Фон номеров строк

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
        bottom = top + self.blockBoundingGeometry(block).height()

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                painter.setPen(QColor(100, 100, 100))
                painter.drawText(0, int(top), self.line_number_area.width() - 5,
                                 self.fontMetrics().height(),
                                 Qt.AlignmentFlag.AlignRight, number)

            block = block.next()
            top = bottom
            bottom = top + self.blockBoundingGeometry(block).height()
            block_number += 1

    def highlight_current_line(self):
        extra_selections = []

        if not self.isReadOnly():
            selection = QTextEdit.ExtraSelection()
            line_color = QColor(235, 245, 255)  # Голубой фон для текущей строки
            selection.format.setBackground(line_color)
            selection.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            extra_selections.append(selection)

        self.setExtraSelections(extra_selections)


class OutputWindow(QTextEdit):
    def __init__(self):
        super().__init__()
        self.setReadOnly(True)
        self.setFont(QFont("Consolas", 10))

    def append_message(self, message, color=None):
        if color:
            self.setTextColor(color)
        else:
            self.setTextColor(QColor(0, 0, 0))  # Черный по умолчанию

        self.append(message)
        # Прокручиваем к последнему сообщению
        cursor = self.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.setTextCursor(cursor)


class ModernMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Cortex IDE")
        self.setGeometry(100, 100, 1200, 800)

        # Словарь для хранения путей к файлам
        self.file_paths = {}

        # Инициализация UI
        self.init_ui()

        # Создаем первую вкладку
        self.create_new_tab()

    def init_ui(self):
        """Инициализация пользовательского интерфейса"""
        # Центральный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Основной layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Создаем виджет вкладок
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.tabCloseRequested.connect(self.close_tab)
        main_layout.addWidget(self.tab_widget)

        # Создаем док-виджет для вывода
        self.create_output_dock()

        # Применяем светлую тему
        self.apply_light_theme()

        # Создаем меню
        self.create_menus()

        # Создаем строку состояния
        self.create_status_bar()

    def create_output_dock(self):
        """Создание док-виджета для вывода"""
        self.output_dock = QDockWidget("Вывод", self)
        self.output_dock.setAllowedAreas(Qt.DockWidgetArea.BottomDockWidgetArea |
                                         Qt.DockWidgetArea.RightDockWidgetArea)

        self.output_window = OutputWindow()
        self.output_dock.setWidget(self.output_window)

        # Устанавливаем начальный размер
        self.output_dock.setMinimumHeight(150)

        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.output_dock)

    def apply_light_theme(self):
        """Применение светлой темы"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #ffffff;
                color: #000000;
            }
            QTabWidget::pane {
                border: 1px solid #cccccc;
                background-color: #ffffff;
            }
            QTabBar::tab {
                background-color: #f0f0f0;
                color: #000000;
                padding: 8px 16px;
                border: 1px solid #cccccc;
                border-bottom: none;
            }
            QTabBar::tab:selected {
                background-color: #ffffff;
                border-bottom: 1px solid #ffffff;
            }
            QTabBar::tab:hover {
                background-color: #e8e8e8;
            }
            QMenuBar {
                background-color: #ffffff;
                color: #000000;
                border-bottom: 1px solid #cccccc;
            }
            QMenuBar::item {
                padding: 4px 8px;
            }
            QMenuBar::item:selected {
                background-color: #e8e8e8;
            }
            QMenu {
                background-color: #ffffff;
                color: #000000;
                border: 1px solid #cccccc;
            }
            QMenu::item {
                padding: 4px 16px;
            }
            QMenu::item:selected {
                background-color: #e8e8e8;
            }
            QStatusBar {
                background-color: #f5f5f5;
                color: #000000;
                border-top: 1px solid #cccccc;
            }
            QDockWidget {
                titlebar-close-icon: url(close.png);
                titlebar-normal-icon: url(float.png);
                color: #000000;
                font-weight: bold;
            }
            QDockWidget::title {
                background: #f0f0f0;
                padding: 6px;
                border: 1px solid #cccccc;
                border-bottom: none;
                text-align: center;
            }
        """)

    def create_menus(self):
        """Создание меню"""
        menubar = self.menuBar()

        # Меню Файл
        file_menu = menubar.addMenu("Файл")

        new_action = QAction("Новый", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self.create_new_tab)
        file_menu.addAction(new_action)

        open_action = QAction("Открыть", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.open_file)
        file_menu.addAction(open_action)

        save_action = QAction("Сохранить", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.save_file)
        file_menu.addAction(save_action)

        save_as_action = QAction("Сохранить как...", self)
        save_as_action.setShortcut("Ctrl+Shift+S")
        save_as_action.triggered.connect(self.save_file_as)
        file_menu.addAction(save_as_action)

        file_menu.addSeparator()

        # Меню Выполнение
        run_menu = menubar.addMenu("Выполнение")

        run_action = QAction("Запуск", self)
        run_action.setShortcut("F5")
        run_action.triggered.connect(self.run_code)
        run_menu.addAction(run_action)

        clear_output_action = QAction("Очистить вывод", self)
        clear_output_action.setShortcut("Ctrl+L")
        clear_output_action.triggered.connect(self.clear_output)
        run_menu.addAction(clear_output_action)

        file_menu.addSeparator()

        exit_action = QAction("Выход", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

    def create_status_bar(self):
        """Создание строки состояния"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Готово")

    def create_new_tab(self):
        """Создание новой вкладки редактора"""
        editor = CodeEditor()

        index = self.tab_widget.addTab(editor, "Новый файл")
        self.tab_widget.setCurrentIndex(index)
        self.file_paths[index] = None

    def close_tab(self, index):
        """Закрытие вкладки"""
        if self.tab_widget.widget(index).document().isModified():
            reply = QMessageBox.question(self, "Подтверждение",
                                         "Сохранить изменения перед закрытием?",
                                         QMessageBox.StandardButton.Yes |
                                         QMessageBox.StandardButton.No |
                                         QMessageBox.StandardButton.Cancel)

            if reply == QMessageBox.StandardButton.Yes:
                if not self.save_file(index):
                    return
            elif reply == QMessageBox.StandardButton.Cancel:
                return

        self.tab_widget.removeTab(index)
        # Обновляем индексы в file_paths
        self.file_paths = {self.tab_widget.indexOf(widget): path
                           for widget, path in [(self.tab_widget.widget(i), self.file_paths.get(i))
                                                for i in range(self.tab_widget.count())]}

    def open_file(self):
        """Открытие файла"""
        file_path, _ = QFileDialog.getOpenFileName(self, "Открыть файл", "", "Cortex Files (*.cortex);;All Files (*)")
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    content = file.read()

                editor = CodeEditor()
                editor.setPlainText(content)
                editor.document().setModified(False)

                file_name = os.path.basename(file_path)
                index = self.tab_widget.addTab(editor, file_name)
                self.tab_widget.setCurrentIndex(index)
                self.file_paths[index] = file_path

                self.status_bar.showMessage(f"Файл открыт: {file_path}")
                self.output_window.append_message(f"📂 Открыт файл: {file_path}")

            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось открыть файл: {str(e)}")

    def save_file(self, index=None):
        """Сохранение файла"""
        if index is None:
            index = self.tab_widget.currentIndex()

        if self.file_paths.get(index) is None:
            return self.save_file_as(index)
        else:
            file_path = self.file_paths[index]
            try:
                editor = self.tab_widget.widget(index)
                with open(file_path, 'w', encoding='utf-8') as file:
                    file.write(editor.toPlainText())

                editor.document().setModified(False)
                self.status_bar.showMessage(f"Файл сохранен: {file_path}")
                self.output_window.append_message(f"💾 Файл сохранен: {file_path}")
                return True

            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить файл: {str(e)}")
                return False

    def save_file_as(self, index=None):
        """Сохранение файла как"""
        if index is None:
            index = self.tab_widget.currentIndex()

        file_path, _ = QFileDialog.getSaveFileName(self, "Сохранить файл", "", "Cortex Files (*.cortex);;All Files (*)")
        if file_path:
            if not file_path.endswith('.cortex'):
                file_path += '.cortex'

            try:
                editor = self.tab_widget.widget(index)
                with open(file_path, 'w', encoding='utf-8') as file:
                    file.write(editor.toPlainText())

                self.file_paths[index] = file_path
                editor.document().setModified(False)
                file_name = os.path.basename(file_path)
                self.tab_widget.setTabText(index, file_name)

                self.status_bar.showMessage(f"Файл сохранен: {file_path}")
                self.output_window.append_message(f"💾 Файл сохранен как: {file_path}")
                return True

            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить файл: {str(e)}")
                return False
        return False

    def run_code(self):
        """Запуск кода Cortex"""
        editor = self.tab_widget.currentWidget()
        if editor:
            code = editor.toPlainText()
            self.output_window.append_message("🚀 Запуск программы Cortex...")

            if not code.strip():
                self.output_window.append_message("⚠️ Нет кода для выполнения")
                return

            try:
                # Добавляем путь для импорта модулей компилятора
                sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

                # Импортируем компоненты компилятора
                from cortex.compiler.lexer import Lexer
                from cortex.compiler.parser import Parser
                from cortex.compiler.interpreter import Interpreter

                # Лексический анализ
                self.output_window.append_message("🔍 Лексический анализ...")
                lexer = Lexer(code)
                tokens = lexer.tokenize()

                # Выводим токены для отладки
                self.output_window.append_message("📋 Токены:")
                for i, token in enumerate(tokens):
                    self.output_window.append_message(f"  {i}: {token.type} = '{token.value}'")

                # Синтаксический анализ
                self.output_window.append_message("🔍 Синтаксический анализ...")
                parser = Parser(tokens)
                ast = parser.parse()

                # Выводим AST для отладки
                self.output_window.append_message("📋 AST:")
                self.output_window.append_message(f"  Тип: {type(ast)}")
                if isinstance(ast, list):
                    self.output_window.append_message(f"  Количество statements: {len(ast)}")
                    for i, node in enumerate(ast):
                        self.output_window.append_message(f"    {i}: {node}")
                else:
                    self.output_window.append_message(f"  Значение: {ast}")

                # Интерпретация
                self.output_window.append_message("🔍 Интерпретация...")
                interpreter = Interpreter()
                result = interpreter.interpret(ast)

                # Вывод результатов
                output_text = interpreter.get_output()
                if output_text:
                    self.output_window.append_message("📤 Вывод программы:")
                    self.output_window.append_message(output_text)
                else:
                    self.output_window.append_message("ℹ️ Программа не вывела данных")

                if result is not None:
                    self.output_window.append_message(f"📤 Возвращаемое значение: {result}")

                self.output_window.append_message("✅ Выполнение завершено")

            except Exception as e:
                self.output_window.append_message(f"❌ Ошибка выполнения: {str(e)}")
                self.output_window.append_message(f"❌ Трассировка: {traceback.format_exc()}")

    def clear_output(self):
        """Очистка окна вывода"""
        self.output_window.clear()
        self.output_window.append_message("🧹 Вывод очищен")


def main():
    app = QApplication(sys.argv)
    window = ModernMainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()