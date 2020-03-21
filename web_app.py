from flask import Flask, render_template, url_for
import base64

from lib.browser import Browser
from lib.layoutparser import LayoutParser

app = Flask(__name__)


def write_image(base64_enc, file_name):
    with open(file_name, 'wb') as f:
        f.write(base64.b64decode(base64_enc))


@app.route('/')
def index():
    browser = Browser()
    report = None
    with browser.new_page() as tab:
        print("Loading page")
        data = tab.collect_data("https://timesofindia.indiatimes.com/")
        layout_parser = LayoutParser(data["snapshot"], data["tree"], data["screenshot"])
        print("Building rtree")
        layout_parser.build_rtree_index()
        print("Building dom tree")
        layout_parser.build_dom_index()
        write_image(layout_parser.screenshot["data"], "page.png")
        print("Creating report")
        report = layout_parser.create_report1()
    return render_template("index.html", report=report)


if __name__ == "__main__":
    app.run(debug=True)
