import logging
from PyQt6.QtWebEngineWidgets import QWebEngineView

logger = logging.getLogger(__name__)

class LaTeXRenderer(QWebEngineView):
    def __init__(self, parent=None):
        super().__init__(parent)
        logger.info("Initializing LaTeX renderer")
        self._load_mathjax_template()

    def _load_mathjax_template(self):
        html = '''
        <!DOCTYPE html>
        <html>
        <head>
            <script src="https://polyfill.io/v3/polyfill.min.js?features=es6"></script>
            <script id="MathJax-script" async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
            <style>
                body {
                    margin: 0;
                    padding: 20px;
                    background-color: #ffffff;
                    font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
                    color: #333333;
                    line-height: 1.6;
                }
                #content {
                    font-size: 1.2em;
                    white-space: pre-wrap;
                }
            </style>
            <script>
                window.MathJax = {
                    tex: {
                        inlineMath: [['$', '$'], ['\\(', '\\)']],
                        displayMath: [['$$', '$$'], ['\\[', '\\]']],
                        packages: ['base', 'ams', 'bbox', 'cancel', 'color'],
                    },
                    loader: { load: ['[tex]/color', '[tex]/cancel', '[tex]/bbox', '[tex]/ams'] },
                    startup: {
                        typeset: false,
                        ready: () => {
                            MathJax.startup.defaultReady();
                        }
                    }
                };
                window.renderContent = function(content) {
                    let contentElement = document.getElementById('content');
                    contentElement.innerHTML = content.replace(/\\n/g, '<br>');
                    MathJax.typesetPromise([contentElement]);
                };
            </script>
        </head>
        <body>
            <h2>LaTeX Renderer</h2>
            <div id="content"></div>
        </body>
        </html>
        '''
        self.setHtml(html)

    def render_latex(self, text):
        logger.info("Rendering LaTeX countent")
        text = text.replace('`', '\\`').replace('\\', '\\\\')
        self.loadFinished.connect(lambda: self.page().runJavaScript("console.log('Page fully loaded.');"))
        self.page().runJavaScript(f'window.renderContent(`{text}`)')