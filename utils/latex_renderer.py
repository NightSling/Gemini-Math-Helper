import logging
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import QUrl
from pathlib import Path
import json
import re

logger = logging.getLogger(__name__)

class LaTeXRenderer(QWebEngineView):
    def __init__(self, parent=None):
        super().__init__(parent)
        logger.info("Initializing enhanced LaTeX renderer")
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
                }
                #content {
                    font-size: 1.2em;
                    white-space: pre-wrap;
                    font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
                    line-height: 1.6;
                    color: #333333;
                }
                .math-error {
                    color: #d32f2f;
                    background: #ffebee;
                    padding: 12px;
                    border-radius: 6px;
                    margin: 8px 0;
                    border: 1px solid #ffcdd2;
                }
                .math-block {
                    display: block;
                    margin: 1em 0;
                }
                .text-content {
                    display: inline;
                }
                /* Custom styles for specific mathematical elements */
                .mjx-boxed {
                    border: 2px solid #2196F3;
                    border-radius: 4px;
                    padding: 2px 6px;
                }
                .mjx-box {
                    padding: 2px;
                }
            </style>
            <script>
                window.MathJax = {
                    tex: {
                        inlineMath: [['$', '$'], ['\\\\(', '\\\\)']],
                        displayMath: [['$$', '$$'], ['\\\\[', '\\\\]']],
                        packages: ['base', 'ams', 'noerrors', 'noundefined', 'bbox', 'cancel', 'color'],
                        macros: {
                            R: '{\\\\mathbb{R}}',
                            N: '{\\\\mathbb{N}}',
                            Z: '{\\\\mathbb{Z}}',
                            Q: '{\\\\mathbb{Q}}',
                            C: '{\\\\mathbb{C}}'
                        },
                        environments: {
                            aligned: ['\\\\begin{aligned}', '\\\\end{aligned}'],
                            gather: ['\\\\begin{gather}', '\\\\end{gather}'],
                            cases: ['\\\\begin{cases}', '\\\\end{cases}']
                        },
                        processEscapes: true,
                        processEnvironments: true,
                        processRefs: true
                    },
                    options: {
                        enableMenu: false,
                        safeOptions: {
                            allow: {
                                URLs: false,
                                classes: true,
                                cssIDs: false,
                                styles: true
                            }
                        }
                    },
                    loader: {
                        load: ['[tex]/color', '[tex]/cancel', '[tex]/bbox']
                    },
                    startup: {
                        typeset: false,
                        ready: () => {
                            MathJax.startup.defaultReady();
                            MathJax.startup.promise.then(() => {
                                console.log('MathJax initial setup completed');
                            });
                        }
                    },
                    messageStyle: 'none'
                };
            </script>
        </head>
        <body>
            <div id="content"></div>
            <script>
                function renderContent(content) {
                    const element = document.getElementById('content');
                    try {
                        // Split content into lines and process each line
                        const lines = content.split('\\n');
                        const processedLines = lines.map(line => {
                            // If line is empty, just return a line break
                            if (!line.trim()) {
                                return '\\n';
                            }

                            // Check if the line contains display math
                            if (line.trim().startsWith('$$') || line.trim().startsWith('\\\\[')) {
                                return `<div class="math-block">${line}</div>`;
                            }

                            // Regular line (may contain inline math)
                            return `<span class="text-content">${line}</span>`;
                        });

                        // Join lines and remove any double line breaks
                        element.innerHTML = processedLines.join('\\n')
                            .replace(/\\n\\n+/g, '\\n\\n')
                            .replace(/^\\n+|\\n+$/g, '');

                        MathJax.typesetPromise([element]).then(() => {
                            console.log('Typeset completed successfully');
                            // Adjust the container size after rendering
                            window.setTimeout(() => {
                                const height = document.body.scrollHeight;
                                if (window.QWebChannel && window.QWebChannel.objects.callback) {
                                    window.QWebChannel.objects.callback.adjustHeight(height);
                                }
                            }, 100);
                        }).catch((err) => {
                            console.error('MathJax error:', err);
                            element.innerHTML = `
                                <div class="math-error">
                                    <strong>Math Input Error:</strong><br>
                                    Please check your mathematical expressions.<br>
                                    Details: ${err.message}
                                </div>`;
                        });
                    } catch (err) {
                        console.error('Rendering error:', err);
                        element.innerHTML = `
                            <div class="math-error">
                                <strong>Rendering Error:</strong><br>
                                ${err.message}
                            </div>`;
                    }
                }
            </script>
        </body>
        </html>
        '''
        self.setHtml(html)

    def _validate_latex(self, text):
        """Enhanced validation for LaTeX input."""
        if not text:
            return False, "Empty input"
        
        # Check for balanced delimiters
        delimiters = {
            '$': {'count': 0, 'pairs': True},
            '\\(': {'count': 0, 'pairs': False, 'match': '\\)'},
            '\\[': {'count': 0, 'pairs': False, 'match': '\\]'},
            '\\begin{': {'count': 0, 'pairs': False, 'match': '\\end{'}
        }
        
        # Track environment names for matching begin/end
        environments = []
        
        # Process text character by character
        i = 0
        while i < len(text):
            # Check for escaped characters
            if text[i] == '\\' and i + 1 < len(text):
                if text[i+1] in ['$', '{', '}']:
                    i += 2
                    continue
            
            # Check for environment declarations
            if text[i:].startswith('\\begin{'):
                delimiters['\\begin{']['count'] += 1
                env_end = text.find('}', i)
                if env_end != -1:
                    env_name = text[i+7:env_end]
                    environments.append(env_name)
                i = env_end + 1 if env_end != -1 else i + 1
                continue
                
            if text[i:].startswith('\\end{'):
                delimiters['\\end{']['count'] += 1
                env_end = text.find('}', i)
                if env_end != -1:
                    env_name = text[i+5:env_end]
                    if not environments or environments[-1] != env_name:
                        return False, f"Mismatched environment: {env_name}"
                    environments.pop()
                i = env_end + 1 if env_end != -1 else i + 1
                continue
            
            # Check for other delimiters
            for delim in ['$', '\\(', '\\[']:
                if text[i:].startswith(delim):
                    delimiters[delim]['count'] += 1
                    i += len(delim)
                    break
            else:
                i += 1
        
        # Validate delimiter counts
        for delim, info in delimiters.items():
            if info['pairs']:
                if info['count'] % 2 != 0:
                    return False, f"Unmatched {delim} delimiter"
            else:
                match_delim = info['match']
                if match_delim and text.count(delim) != text.count(match_delim):
                    return False, f"Unmatched {delim} and {match_delim} delimiters"
        
        # Check for unclosed environments
        if environments:
            return False, f"Unclosed environment: {environments[-1]}"
        
        return True, None

    def render_latex(self, text):
        """Render mixed LaTeX and text content with enhanced validation."""
        if not isinstance(text, str):
            logger.error(f"Invalid input type: {type(text)}")
            return

        valid, error = self._validate_latex(text)
        if not valid:
            logger.error(f"LaTeX validation error: {error}")
            error_msg = f'<div class="math-error"><strong>Math Input Error:</strong><br>{error}</div>'
            self.page().runJavaScript(f'renderContent(`{error_msg}`)')
            return

        logger.info(f"Rendering mixed content: {text}")
        
        # Escape backticks and properly escape backslashes for JavaScript
        text = text.replace('`', '\\`').replace('\\', '\\\\')
        
        # Use template literals instead of JSON for better handling of special characters
        js = f'renderContent(`{text}`)'
        self.page().runJavaScript(js)
        logger.debug("Mixed content rendering requested")