from lib.browser import Browser
from lib.layoutparser import LayoutParser
import code
import json
import base64


def write_image(base64_enc, file_name):
    with open(file_name, 'wb') as f:
        f.write(base64.b64decode(base64_enc))


def write_json(data, file_name):
    with open(file_name, 'w') as f:
        f.write(json.dumps(data, indent=4, sort_keys=True))


def main():
    browser = Browser()
    with browser.new_page() as tab:
        data = tab.collect_data("https://news.ycombinator.com/")
        layout_parser = LayoutParser(data["snapshot"], data["tree"], data["screenshot"])
        layout_parser.build_rtree_index()
        layout_parser.build_dom_index()
        write_json(layout_parser.dom_index, "dom-build.json")
        # write_image(layout_parser.screenshot["data"], "page.png")
        layout_parser.plot_img()

        # code.interact(local=dict(globals(), **locals()))


if __name__ == "__main__":
    main()
