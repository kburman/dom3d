import pychrome
from rtree import index
import base64
import json
import code

rtree = index.Index()
browser = pychrome.Browser(url="http://127.0.0.1:9222")


class Rectangle:
    # https://codereview.stackexchange.com/a/151327/118102
    def __init__(self, min_x=0, max_x=0, min_y=0, max_y=0):
        self.min_x = min_x
        self.max_x = max_x
        self.min_y = min_y
        self.max_y = max_y

    def is_intersect(self, other):
        if self.min_x > other.max_x or self.max_x < other.min_x:
            return False
        if self.min_y > other.max_y or self.max_y < other.min_y:
            return False
        return True

    def __and__(self, other):
        if not self.is_intersect(other):
            return Rectangle()
        min_x = max(self.min_x, other.min_x)
        max_x = min(self.max_x, other.max_x)
        min_y = max(self.min_y, other.min_y)
        max_y = min(self.max_y, other.max_y)
        return Rectangle(min_x, max_x, min_y, max_y)

    intersect = __and__

    def __or__(self, other):
        min_x = min(self.min_x, other.min_x)
        max_x = max(self.max_x, other.max_x)
        min_y = min(self.min_y, other.min_y)
        max_y = max(self.max_y, other.max_y)
        return Rectangle(min_x, max_x, min_y, max_y)

    union = __or__

    def __str__(self):
        return 'Rectangle({self.min_x},{self.max_x},{self.min_y},{self.max_y})'.format(self=self)

    @property
    def area(self):
        return (self.max_x - self.min_x) * (self.max_y - self.min_y)


def fix_window_size(chrome_tab):
    # {'windowId': 8, 'bounds': {'left': 0, 'top': 0, 'width': 800, 'height': 600, 'windowState': 'normal'}}
    res = chrome_tab.call_method("Browser.getWindowForTarget", targetId=chrome_tab.id)
    # https://gs.statcounter.com/screen-resolution-stats/desktop/worldwide
    res['bounds']['width'] = 1366
    res['bounds']['height'] = 768
    chrome_tab.call_method("Browser.setWindowBounds", windowId=res['windowId'], bounds=res['bounds'])


def write_image(base64_enc, file_name):
    with open(file_name, 'wb') as f:
        f.write(base64.b64decode(base64_enc))


def write_json(data, file_name):
    with open(file_name, 'w') as f:
        f.write(json.dumps(data, indent=4, sort_keys=True))


def _conv_for_rtree(x, y, w, h):
    # return [x, y + h, x + w, y]
    return [x, y, x + w, y + h]


def find_nodes(root_node, backend_ids):
    node_queue = [root_node]
    ans_nodes = []
    while len(node_queue) > 0:
        curr_node = node_queue.pop(0)
        if curr_node["backendNodeId"] in backend_ids:
            ans_nodes.append(curr_node)

        if 'children' in curr_node:
            node_queue.extend(curr_node['children'])
    return ans_nodes


def find_node(root_node, backend_id):
    node_queue = [root_node]
    while len(node_queue) > 0:
        curr_node = node_queue.pop(0)
        if curr_node["backendNodeId"] == backend_id:
            return curr_node

        if 'children' in curr_node:
            node_queue.extend(curr_node['children'])


def fix_order(backend_ids, dom_snapshot):
    def _get_paint_oder(backend_id):
        try:
            node_id = dom_snapshot["documents"][0]["nodes"]["backendNodeId"].index(backend_id)
            layout_index = dom_snapshot["documents"][0]["layout"]["nodeIndex"].index(node_id)
            return dom_snapshot["documents"][0]["layout"]["paintOrders"][layout_index]
        except ValueError:
            return 0

    return sorted(backend_ids, key=_get_paint_oder)


def dict_from_array(arr):
    d = {}
    if type(arr) is list:
        for i in range(len(arr)):
            if i % 2 == 0:
                d[arr[i]] = arr[i + 1]
    return d


def find_node_bounds(backend_id, dom_snapshot):
    try:
        node_index = dom_snapshot['documents'][0]['nodes']['backendNodeId'].index(backend_id)
        layout_index = dom_snapshot["documents"][0]["layout"]["nodeIndex"].index(node_index)
        return dom_snapshot["documents"][0]["layout"]["bounds"][layout_index]
    except:
        return []


tab = browser.new_tab()
tab.start()
tab.call_method("DOM.enable")
tab.call_method("DOMSnapshot.enable")
fix_window_size(tab)
print("Loading web page")
tab.Page.navigate(url="https://www.bbc.com", _timeout=5)
tab.wait(5)

dom_snapshot = tab.call_method("DOMSnapshot.captureSnapshot", computedStyles=[], includePaintOrder=True,
                               includeDOMRects=True)
dom_tree = tab.call_method("DOM.getDocument", depth=-1)
page_view = tab.call_method("Page.captureScreenshot", format='png')
write_image(page_view['data'], 'page.png')
write_json(dom_snapshot, 'domsnapsnot.json')
write_json(dom_tree, 'domtree.json')

print("Loading rtree")
for document in dom_snapshot["documents"]:
    for layout_index in range(len(document["layout"]["bounds"])):
        node_index = document["layout"]["nodeIndex"][layout_index]
        backend_id = document["nodes"]["backendNodeId"][node_index]

        rect = document["layout"]["bounds"][layout_index]
        if len(rect) > 0 and (rect[-1] > 0 and rect[-2] > 0):
            rtree.insert(backend_id, _conv_for_rtree(*rect))

print("Done loading rtree")

backendIds = list(rtree.intersection((51.5, 110.5, 667.5, 457)))
ans = find_nodes(dom_tree['root'], backendIds)
write_json(ans, "res.json")

clickable_backend_id = list(map(lambda x: dom_snapshot['documents'][0]['nodes']['backendNodeId'][x],
                                dom_snapshot['documents'][0]['nodes']['isClickable']['index']))

for backend_id in clickable_backend_id:
    node = find_node(dom_tree['root'], backend_id)
    if node["nodeName"] != "A":
        continue

    node_attr = dict_from_array(node.get("attributes"))
    if "href" not in node_attr:
        continue

    bounds = find_node_bounds(backend_id, dom_snapshot)
    if len(bounds) == 0:
        continue

    intersect_backend_ids = rtree.intersection(_conv_for_rtree(*bounds))
    intersect_backend_ids = fix_order(intersect_backend_ids, dom_snapshot)
    intersect_backend_ids = intersect_backend_ids[:intersect_backend_ids.index(backend_id) + 1]
    intersect_nodes = find_nodes(dom_tree['root'], intersect_backend_ids)
    if len(intersect_nodes) == 0:
        continue

    print("_"*100)
    for node in intersect_nodes:
        if node["nodeName"] not in ["IMG", "#text"]:
            continue

        node_attr = dict_from_array(node.get("attributes"))
        print(node["nodeName"] + ":" + ":".join(node.get("attributes", [])) + " >  " + node["nodeValue"].strip() + "  |||---  " + node_attr.get("href" , ""))



# code.interact(local=dict(globals(), **locals()))

tab.stop()
browser.close_tab(tab)
