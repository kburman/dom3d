import code
import time

import pychrome
from urllib.parse import urlparse


class Browser:
    def __init__(self):
        self.browser = pychrome.Browser(url="http://127.0.0.1:9222")

    def new_page(self):
        return BrowserTab(self.browser, self.browser.new_tab())


class BrowserTab:
    def __init__(self, browser, tab):
        assert browser is not None
        assert tab is not None
        self.browser = browser
        self.tab = tab
    
    def __enter__(self):
        self.start()
        return self
    
    def __exit__(self, type1, value, traceback):
        self.close()
    
    def set_window_size(self, width, height):
        # {'windowId': 8, 'bounds': {'left': 0, 'top': 0, 'width': 800, 'height': 600, 'windowState': 'normal'}}
        res = self.tab.call_method("Browser.getWindowForTarget", targetId=self.tab.id)
        res['bounds']['width'] = width
        res['bounds']['height'] = height
        self.tab.call_method("Browser.setWindowBounds", windowId=res['windowId'], bounds=res['bounds'])

    def start(self):
        assert self.tab.start()
        self.tab.call_method("DOMSnapshot.enable")
        self.tab.call_method("DOM.enable")
        self.tab.call_method("Page.enable")
        # https://gs.statcounter.com/screen-resolution-stats/desktop/worldwide
        self.set_window_size(1366, 768)

    def stop(self):
        assert self.tab.stop()

    def load_url(self, url):
        o = urlparse(url)
        self.tab.call_method("Page.navigate", url=o.geturl(), _timeout=5)

    def wait(self, timeout):
        self.tab.wait(timeout)

    def collect_dom_snapshot(self):
        return self.tab.call_method("DOMSnapshot.captureSnapshot", computedStyles=[],
                                    includePaintOrder=True, includeDOMRects=True)

    def collect_dom_tree(self):
        return self.tab.call_method("DOM.getDocument", depth=-1)

    def collect_dom_screenshot(self):
        layout_metrics = self.tab.call_method("Page.getLayoutMetrics")
        viewport = layout_metrics["contentSize"].copy()
        viewport["scale"] = 1
        print(layout_metrics)
        self.set_window_size(viewport["width"], viewport["height"])
        return self.tab.call_method("Page.captureScreenshot", format="png", clip=viewport)

    def collect_data(self, url):
        self.load_url(url)
        self.wait(3)
        return {
            "snapshot": self.collect_dom_snapshot(),
            "screenshot": self.collect_dom_screenshot(),
            "tree": self.collect_dom_tree()
        }
    
    def close(self):
        self.stop()
        self.browser.close_tab(self.tab)

