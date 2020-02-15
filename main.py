import pychrome
from rtree import index
import base64
import json
import code

rtree = index.Index()
browser = pychrome.Browser(url="http://127.0.0.1:9222")


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
    # return : (left, bottom, right, top)
    # return [x, y + h, x + w, y]
    return [x, y, x + w, y + h]


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
        if len(rect) > 0:
            print(rect)
            rtree.insert(backend_id, _conv_for_rtree(*rect))

print("Done loading rtree")

backendIds = list(rtree.intersection((51.5, 110.5, 667.5, 457)))

node_queue = [dom_tree['root']]
ans = []
while len(node_queue) > 0:
    curr_node = node_queue.pop(0)
    if curr_node["backendNodeId"] in backendIds:
        ans.append(curr_node)

    if 'children' in curr_node:
        node_queue.extend(curr_node['children'])

write_json(ans, "res.json")

# code.interact(local=dict(globals(), **locals()))

tab.stop()
browser.close_tab(tab)
