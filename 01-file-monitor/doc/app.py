#!/usr/bin/env python3
import markdown
from flask import Flask

app = Flask(__name__)

@app.route('/')
def convert_to_html():
    with open('DOC.md') as f:
        return markdown.markdown(f.read())

if __name__ == '__main__':
    app.run(port=9000)