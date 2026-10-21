import sys
import fitz  # PyMuPDF
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QLabel, QTreeWidget, QTreeWidgetItem, QScrollArea,
    QFileDialog, QSplitter
)
from PyQt6.QtGui import QImage, QPixmap, QKeySequence, QShortcut
from PyQt6.QtCore import Qt

# Import your chapter classification module
try:
    import chapter_classification
except ImportError:
    chapter_classification = None


class PDFReaderUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Python PDF Reader")
        self.resize(1100, 750)

        self.doc = None
        self.current_page = 0
        self.zoom_factor = 1.0  # Default zoom level (100%)

        self._init_ui()
        self._setup_shortcuts()

    def _init_ui(self):
        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.setCentralWidget(splitter)

        # 1. Left Sidebar - Chapter Navigation Tree
        self.toc_tree = QTreeWidget()
        self.toc_tree.setHeaderLabel("Table of Contents")
        self.toc_tree.itemClicked.connect(self._on_toc_item_clicked)
        splitter.addWidget(self.toc_tree)

        # 2. Right Container - Controls + Image Scroll Area
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)

        # Top Control Bar
        toolbar = QHBoxLayout()
        self.btn_open = QPushButton("Open PDF")
        self.btn_open.clicked.connect(self.open_file)

        self.btn_prev = QPushButton("◄ Prev")
        self.btn_prev.clicked.connect(self.prev_page)

        self.btn_next = QPushButton("Next ►")
        self.btn_next.clicked.connect(self.next_page)

        self.lbl_page = QLabel("Page: 0 / 0")

        # Zoom Controls
        self.btn_zoom_out = QPushButton("Zoom -")
        self.btn_zoom_out.clicked.connect(self.zoom_out)

        self.btn_zoom_in = QPushButton("Zoom +")
        self.btn_zoom_in.clicked.connect(self.zoom_in)

        self.btn_zoom_reset = QPushButton("100%")
        self.btn_zoom_reset.clicked.connect(self.zoom_reset)

        self.lbl_zoom = QLabel("100%")

        # Add widgets to Toolbar
        toolbar.addWidget(self.btn_open)
        toolbar.addWidget(self.btn_prev)
        toolbar.addWidget(self.btn_next)
        toolbar.addWidget(self.lbl_page)
        toolbar.addSpacing(20)
        toolbar.addWidget(self.btn_zoom_out)
        toolbar.addWidget(self.btn_zoom_in)
        toolbar.addWidget(self.btn_zoom_reset)
        toolbar.addWidget(self.lbl_zoom)
        toolbar.addStretch()

        right_layout.addLayout(toolbar)

        # Page Display Viewport
        self.scroll_area = QScrollArea()
        self.scroll_area.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.page_label = QLabel("No PDF Loaded")
        self.page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.scroll_area.setWidget(self.page_label)
        self.scroll_area.setWidgetResizable(True)

        # Intercept Wheel Events on the scroll area for Ctrl + Wheel zoom
        self.scroll_area.viewport().installEventFilter(self)

        right_layout.addWidget(self.scroll_area)
        splitter.addWidget(right_widget)

        splitter.setSizes([250, 850])

    def _setup_shortcuts(self):
        """Keyboard shortcuts for zooming"""
        QShortcut(QKeySequence.StandardKey.ZoomIn, self, self.zoom_in)
        QShortcut(QKeySequence("Ctrl+="), self, self.zoom_in)
        QShortcut(QKeySequence.StandardKey.ZoomOut, self, self.zoom_out)
        QShortcut(QKeySequence("Ctrl+0"), self, self.zoom_reset)

    def eventFilter(self, source, event):
        """Handle Ctrl + Mouse Wheel for zooming"""
        if source == self.scroll_area.viewport() and event.type() == event.Type.Wheel:
            if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                angle_delta = event.angleDelta().y()
                if angle_delta > 0:
                    self.zoom_in()
                elif angle_delta < 0:
                    self.zoom_out()
                return True
        return super().eventFilter(source, event)

    def open_file(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Open PDF File", "", "PDF Files (*.pdf)"
        )
        if not filepath:
            return

        self.doc = fitz.open(filepath)
        self.current_page = 0
        self.zoom_factor = 1.0
        self.populate_toc()
        self.render_current_page()

    def populate_toc(self):
        self.toc_tree.clear()
        if not self.doc:
            return

        toc = self.doc.get_toc()

        if not toc:
            # Fallback: Use chapter_classification module if TOC is missing
            if chapter_classification and hasattr(chapter_classification, "classify_document"):
                classified_toc = chapter_classification.classify_document(self.doc)
                self._build_tree_from_toc(classified_toc)
            else:
                QTreeWidgetItem(self.toc_tree, ["No TOC embedded"])
            return

        # Optional: Run titles through classification if module is available
        processed_toc = []
        for level, title, page in toc:
            category = ""
            if chapter_classification and hasattr(chapter_classification, "classify_title"):
                category = f" [{chapter_classification.classify_title(title)}]"
            processed_toc.append((level, f"{title}{category}", page))

        self._build_tree_from_toc(processed_toc)

    def _build_tree_from_toc(self, toc_items):
        node_stack = {0: self.toc_tree}
        for level, title, page in toc_items:
            parent = node_stack.get(level - 1, self.toc_tree)
            item = QTreeWidgetItem(parent, [f"{title} (p. {page})"])
            item.setData(0, Qt.ItemDataRole.UserRole, page - 1)
            node_stack[level] = item

        self.toc_tree.expandAll()

    def render_current_page(self):
        if not self.doc or self.current_page < 0 or self.current_page >= len(self.doc):
            return

        page = self.doc.load_page(self.current_page)
        
        # Base resolution scaled by zoom_factor
        base_dpi = 150
        scaled_dpi = int(base_dpi * self.zoom_factor)
        pix = page.get_pixmap(dpi=scaled_dpi)

        fmt = QImage.Format.Format_RGBA8888 if pix.alpha else QImage.Format.Format_RGB888
        qimg = QImage(pix.samples, pix.width, pix.height, pix.stride, fmt)
        pixmap = QPixmap.fromImage(qimg)

        self.page_label.setPixmap(pixmap)
        self.lbl_page.setText(f"Page: {self.current_page + 1} / {len(self.doc)}")
        self.lbl_zoom.setText(f"{int(self.zoom_factor * 100)}%")

    def zoom_in(self):
        if self.zoom_factor < 3.0:  # Upper bound 300%
            self.zoom_factor += 0.15
            self.render_current_page()

    def zoom_out(self):
        if self.zoom_factor > 0.3:  # Lower bound 30%
            self.zoom_factor -= 0.15
            self.render_current_page()

    def zoom_reset(self):
        self.zoom_factor = 1.0
        self.render_current_page()

    def prev_page(self):
        if self.doc and self.current_page > 0:
            self.current_page -= 1
            self.render_current_page()

    def next_page(self):
        if self.doc and self.current_page < len(self.doc) - 1:
            self.current_page += 1
            self.render_current_page()

    def _on_toc_item_clicked(self, item, column):
        page_num = item.data(0, Qt.ItemDataRole.UserRole)
        if page_num is not None:
            self.current_page = page_num
            self.render_current_page()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PDFReaderUI()
    window.show()
    sys.exit(app.exec())