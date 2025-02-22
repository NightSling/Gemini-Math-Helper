import cv2
import numpy as np
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget,
    QProgressBar
)
from PyQt6.QtCore import Qt, QMimeData
from PyQt6.QtGui import (
    QDragEnterEvent, QDropEvent, QImage, QPixmap, 
    QKeySequence, QShortcut
)
from PIL import ImageGrab, Image
import os
import tempfile
from .image import enhance_text
from .gemini import GeminiSolver
from .latex_renderer import LaTeXRenderer
import logging

logger = logging.getLogger(__name__)

class LoadingOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setVisible(False)
        
        # Make the overlay catch all mouse events
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Add a processing label
        self.label = QLabel("Processing image...")
        self.label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 14px;
                font-weight: bold;
                margin-bottom: 10px;
            }
        """)
        layout.addWidget(self.label)
        
        # Enhanced progress bar
        self.spinner = QProgressBar()
        self.spinner.setRange(0, 0)  # Makes it an infinite spinner
        self.spinner.setFixedSize(200, 20)
        layout.addWidget(self.spinner)
        
        # Improved styling
        self.setStyleSheet("""
            LoadingOverlay {
                background-color: rgba(0, 0, 0, 180);
            }
            QProgressBar {
                border: 2px solid #4CAF50;
                border-radius: 5px;
                text-align: center;
                background-color: #FFFFFF;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                width: 10px;
                margin: 0.5px;
            }
        """)

class ImageProcessor(QMainWindow):
    def __init__(self, solver: GeminiSolver):
        super().__init__()
        logger.info("Initializing ImageProcessor")
        self._solver = solver
        self.loading_overlay = None
        self._is_processing = False
        self.init_ui()
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

    def init_ui(self):
        self.setWindowTitle("Image Text Enhancer")
        self.setGeometry(100, 100, 400, 500)  # Smaller, calculator-like size
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.WindowStaysOnTopHint)  # Make window floating
        self.setAcceptDrops(True)

        # Add keyboard shortcut
        shortcut = QShortcut(QKeySequence.StandardKey.Paste, self)
        shortcut.activated.connect(self.handle_paste)
        logger.info("Registered Ctrl+V shortcut")

        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Create drop label with minimal height
        self.drop_label = QLabel("Drop image or Ctrl+V")
        self.drop_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.drop_label.setStyleSheet("""
            QLabel {
                background-color: #f0f0f0;
                padding: 5px;
                border-bottom: 1px solid #ddd;
            }
        """)
        self.drop_label.setMaximumHeight(30)
        layout.addWidget(self.drop_label)

        # Create LaTeX display with stretch
        self.latex_display = LaTeXRenderer()
        layout.addWidget(self.latex_display, stretch=1)

        # Create loading overlay
        self.loading_overlay = LoadingOverlay(central_widget)
        self.loading_overlay.resize(self.size())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.loading_overlay:
            self.loading_overlay.resize(self.size())

    def dragEnterEvent(self, event: QDragEnterEvent):
        if self._is_processing:
            event.ignore()
            return
            
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        if self._is_processing:
            event.ignore()
            return
            
        files = [url.toLocalFile() for url in event.mimeData().urls()]
        for file_path in files:
            if file_path.lower().endswith(('.png', '.jpg', '.jpeg')):
                img = cv2.imread(file_path)
                self.process_image(img)
                break

    def handle_paste(self):
        """Separate method to handle paste operations with processing check"""
        if not self._is_processing:
            self.process_clipboard()

    def keyPressEvent(self, event):
        if self._is_processing:
            event.ignore()
            return
            
        logger.debug(f"Key press detected - Key: {event.key()}, Modifiers: {event.modifiers()}")
        
        is_ctrl_v = (
            (event.key() == Qt.Key.Key_V and event.modifiers() == Qt.KeyboardModifier.ControlModifier) or
            (event.key() == Qt.Key.Key_V and event.modifiers() & Qt.KeyboardModifier.ControlModifier) or
            (event.matches(QKeySequence.StandardKey.Paste))
        )
        
        if is_ctrl_v:
            logger.info("Ctrl+V detected, attempting to process clipboard")
            self.handle_paste()
            event.accept()
        else:
            super().keyPressEvent(event)

    def _pil_to_cv2(self, pil_image):
        """Convert PIL image to CV2 format."""
        numpy_image = np.array(pil_image)
        if len(numpy_image.shape) == 3:
            cv2_image = cv2.cvtColor(numpy_image, cv2.COLOR_RGB2BGR)
        else:
            cv2_image = numpy_image
        return cv2_image

    def process_clipboard(self):
        try:
            logger.info("Processing clipboard content")
            clipboard = QApplication.clipboard()
            mime_data = clipboard.mimeData()

            if mime_data.hasImage():
                logger.info("Found image data in clipboard")
                q_image = clipboard.image()
                if not q_image.isNull():
                    logger.info(f"Successfully loaded QImage from clipboard: {q_image.width()}x{q_image.height()}")
                    
                    ptr = q_image.constBits()
                    ptr.setsize(q_image.width() * q_image.height() * 4)
                    arr = np.frombuffer(ptr, np.uint8).reshape(q_image.height(), q_image.width(), 4)
                    img = Image.fromarray(arr)
                    
                    logger.info("Successfully converted QImage to PIL Image")
                    cv2_img = self._pil_to_cv2(img)
                    logger.info("Successfully converted PIL Image to CV2 format")
                    self.process_image(cv2_img)
                    return

            logger.info("Attempting to grab image using PIL ImageGrab")
            clipboard_img = ImageGrab.grabclipboard()
            if clipboard_img:
                if isinstance(clipboard_img, list):
                    logger.info(f"Found file paths in clipboard: {clipboard_img}")
                    for file_path in clipboard_img:
                        if file_path.lower().endswith(('.png', '.jpg', '.jpeg')):
                            logger.info(f"Loading image from file: {file_path}")
                            cv2_img = cv2.imread(file_path)
                            self.process_image(cv2_img)
                            return
                else:
                    logger.info("Successfully grabbed PIL Image from clipboard")
                    cv2_img = self._pil_to_cv2(clipboard_img)
                    logger.info("Successfully converted PIL Image to CV2 format")
                    self.process_image(cv2_img)
                    return
            
            logger.warning("No valid image found in clipboard")
            
        except Exception as e:
            logger.error(f"Error processing clipboard: {str(e)}", exc_info=True)

    def process_image(self, img):
        if self._is_processing:
            logger.warning("Already processing an image, ignoring new request")
            return
            
        try:
            logger.info("Processing new image")
            self._is_processing = True
            self.loading_overlay.setVisible(True)
            QApplication.processEvents()  # Ensure the overlay is shown

            enhanced_img = enhance_text(img)
            temp_dir = tempfile.gettempdir()
            temp_path = os.path.join(temp_dir, 'enhanced_image.png')
            
            cv2.imwrite(temp_path, enhanced_img)
            logger.info("Image enhanced and saved to temporary file")
            latex_result = self._solver.solve(temp_path)
            logger.info("Received LaTeX result from Gemini")
            self.latex_display.render_latex(latex_result)
            
        except Exception as e:
            logger.error(f"Error processing image: {e}")
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
                logger.debug("Temporary file removed")
            self._is_processing = False
            self.loading_overlay.setVisible(False)
            QApplication.processEvents()  # Ensure the overlay is hidden

    def closeEvent(self, event):
        logger.info("Window closing, shutting down application")
        QApplication.quit()
        event.accept()