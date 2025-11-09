from PySide6.QtWidgets import QApplication, QMainWindow, QLineEdit, QVBoxLayout, QWidget
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtCore import QUrl
from urllib.parse import urlparse
import sys, spacy, re, difflib, json
import google.generativeai as genai
import threading

nlp = spacy.load("en_core_web_sm")
genai.configure(api_key="your-api-key")
model = genai.GenerativeModel("gemini-2.5-flash")

with open("commands.json") as f:
    commands = json.load(f)["commands"]

class Fjord(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Fjord Browser v0.1")
        self.resize(1200, 800)

        self.browser = QWebEngineView()
        self.browser.setUrl(QUrl("https://maniksharma.xyz/SupremeBrowser"))

        self.command_bar = QLineEdit()
        self.command_bar.setPlaceholderText("Type > to talk to Intern (say hello!) or enter a URL...")
        self.command_bar.returnPressed.connect(self.handle_command)

        layout = QVBoxLayout()
        layout.addWidget(self.command_bar)
        layout.addWidget(self.browser)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def handle_command(self):
        text = self.command_bar.text().strip()

        # If user didn’t include a scheme, assume https://
        if not text.startswith(("http://", "https://")):
            if "." in text and " " not in text:
                text = "https://" + text

        if self.is_valid_url(text):
            self.browser.setUrl(QUrl(text))
        elif text.startswith(">"):
            cmd = text[1:].strip()  # remove '>'
            action, value = self.intern(cmd)
            self.execute_action(action, value)
            return
        else:
            self.browser.setUrl(QUrl(f"https://duckduckgo.com/?q={text}"))

    def execute_action(self, action, value):
        if action == "open_url":
            self.browser.setUrl(QUrl(value))
        elif action == "search_web":
            self.browser.setUrl(QUrl(f"https://duckduckgo.com/?q={value}"))
        elif action == "respond":
            self.browser.setHtml(f"<h2 style='font-family:sans-serif;'>{value}</h2>")
        elif action == "commands":
            self.browser.setHtml("<table><tr><td><strong>Settings</strong></td><td>Opens Intern Settings</td></tr><tr><td><strong>Open</strong></td><td>Opens a URL for you</td></tr><tr><td><strong>Search</strong></td><td>Searches something for you</td></tr><tr><td><strong>Summarize</strong></td><td>Summarizes the webpage</td></tr><tr><td><strong>Hello</strong></td><td>Gives a brief description about Intern</td></tr><tr><td><strong>Commands</strong></td><td>Shows this page</td></tr></table>")
        elif action == "summarize_page":
            def store_html(html):
                clean = re.sub(r"<(script|style).*?>.*?</\1>", "", html, flags=re.DOTALL)
                clean = re.sub(r"<[^>]+>", " ", clean)
                clean = re.sub(r"\s+", " ", clean).strip()

                prompt = f"Summarize this webpage content clearly and concisely, use html tags instead of md in bolding and other stuff:\n\n{clean[:10000]}"  # limit input length
                print("Prompt Asked!")

                response = model.generate_content(prompt)
                print(response.text)
                self.browser.setHtml(f"<h2>Summary</h2><p>{response.text}</p>")

            threading.Thread(target=store_html, daemon=True).start()
            
            self.browser.page().toHtml(store_html)
        elif action == "unknown":
            self.browser.setHtml("<p>🤔 I didn’t understand that.</p>")

    # --- Intern function ---
    def intern(self, cmd):
        cmd = self.normalize_repeats(cmd.lower().strip())
        doc = nlp(cmd)

        lemmas = [t.lemma_ for t in doc]
        text = " ".join(lemmas)

        # --- Greeting detection ---
        greetings = ["hi", "hello", "yo"]
        if any(self.is_similar(lemma, greetings) for lemma in lemmas):
            return ("respond", "Hey there 👋 I’m Intern. You can ask 'commands' to see what I can do!")

        # --- Commands page ---
        command_words = ["command", "commands", "list", "show"]
        if any(self.is_similar(lemma, command_words) for lemma in lemmas):
            return ("commands", None)

        # --- Open URLs ---
        if "open" in lemmas:
            joined_cmd = " ".join(lemmas).replace("-", " ")
            key = self.is_similar(joined_cmd, list(commands.keys()))
            if key:
                return ("open_url", commands[key])

        # --- Search ---
        if "search" in lemmas:
            query = cmd.replace("search", "").strip()
            return ("search_web", query)

        # --- Summarize / Explain ---
        if "summarize" in lemmas or "explain" in lemmas:
            return ("summarize_page", None)

        # Fallback
        return ("unknown", None)
    
    def normalize_repeats(self, text):
        """Replace repeated letters (2+) with a single letter: heeeeello -> helo"""
        return re.sub(r'(.)\1{1,}', r'\1', text)

    def is_similar(self, word, candidates, cutoff=0.7):
        """Return True if word is similar to any candidate (fuzzy match)"""
        matches = difflib.get_close_matches(word, candidates, n=1, cutoff=cutoff)
        return matches[0] if matches else None


    def is_valid_url(self, text):
            try:
                result = urlparse(text)
                return all([result.scheme, result.netloc])
            except ValueError:
                return False



app = QApplication(sys.argv)
window = Fjord()
window.show()
sys.exit(app.exec())
