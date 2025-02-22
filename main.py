from dotenv import dotenv_values
from PyQt6.QtWidgets import QApplication
import sys
import logging
from utils import gemini, screentool

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('app.log')
    ]
)

logger = logging.getLogger(__name__)
config = dotenv_values(".env")

def main():
    logger.info("Starting application")
    # Initialize Qt Application
    app = QApplication(sys.argv)
    
    # Initialize the Gemini client
    gemini_client = gemini.GeminiSolver(config["GEMINI_API_KEY"])

    # Create and show window
    window = screentool.ImageProcessor(solver=gemini_client)
    window.show()
    
    # Start event loop
    sys.exit(app.exec())
    
if __name__ == "__main__":
    main()