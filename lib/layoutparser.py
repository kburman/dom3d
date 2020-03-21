import code
import io

import IPython
import rtree
from sympy import *
from sympy.geometry import *
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from PIL import Image
import numpy as np
import base64
import random


def write_image(base64_enc, file_name):
    with open(file_name, 'wb') as f:
        f.write(base64.b64decode(base64_enc))


class LayoutParser:
    def __init__(self, snapshot, tree, screenshot):
        self._screenshot = None
        self.dom_index = {}
        self.snapshot = snapshot
        self.tree = tree
        self.screenshot = screenshot
        self.idx = None

    def build_rtree_index(self):
        self.idx = rtree.index.Rtree('bulk', self.__rtree_data_gen())

    def build_dom_index(self):
        for doc in self.snapshot["documents"]:
            nodes = doc["nodes"]
            node_count = len(nodes["backendNodeId"])
            layout_count = len(doc["layout"]["nodeIndex"])

            for node_index in range(node_count):
                backend_id = nodes["backendNodeId"][node_index]
                node_data = {
                    "node_name": self.__resolve_string(nodes["nodeName"][node_index]),
                    "node_type": nodes["nodeType"][node_index],
                    "node_value": self.__resolve_string(nodes["nodeValue"][node_index]),
                    "frame_id": doc["frameId"],
                }

                node_attributes = list(
                    map(lambda str_indx: self.__resolve_string(str_indx), nodes["attributes"][node_index])
                )
                if len(node_attributes) > 0:
                    attributes = {}
                    for attr_index in range(0, len(node_attributes), 2):
                        attributes[node_attributes[attr_index]] = node_attributes[attr_index + 1]
                    node_data["attributes"] = attributes

                if backend_id in self.dom_index:
                    self.dom_index[backend_id].update(node_data)
                else:
                    self.dom_index[backend_id] = node_data

            layout = doc["layout"]
            for layout_index in range(layout_count):
                node_index = layout["nodeIndex"][layout_index]
                node_backend_id = nodes["backendNodeId"][node_index]
                self.dom_index[node_backend_id].update({
                    "bounds": layout["bounds"][layout_index],
                    "clientRects": layout["clientRects"][layout_index],
                    "offsetRects": layout["offsetRects"][layout_index],
                    "paintOrders": layout["paintOrders"][layout_index],
                    "scrollRects": layout["scrollRects"][layout_index],
                    "layout_text": self.__resolve_string(layout["text"][layout_index]),
                })

            cdi = nodes["contentDocumentIndex"]
            for cdi_index in range(len(cdi["index"])):
                cdi_node_index = cdi["index"][cdi_index]
                cdi_node_value = cdi["value"][cdi_index]
                cdi_backend_id = nodes["backendNodeId"][cdi_node_index]
                self.dom_index[cdi_backend_id]["contentDocumentIndex"] = self.__resolve_string(cdi_node_value)

            text_val = nodes["textValue"]
            for text_val_index in range(len(text_val["index"])):
                text_val_node_index = text_val["index"][text_val_index]
                text_val_node_value = text_val["value"][text_val_index]
                text_val_backend_id = nodes["backendNodeId"][text_val_node_index]
                self.dom_index[text_val_backend_id]["textValue"] = self.__resolve_string(text_val_node_value)

            origin_url = nodes["originURL"]
            for origin_index in range(len(origin_url["index"])):
                origin_node_index = origin_url["index"][origin_index]
                origin_node_value = origin_url["value"][origin_index]
                origin_node_backend_id = nodes["backendNodeId"][origin_node_index]
                self.dom_index[origin_node_backend_id]["originUrl"] = self.__resolve_string(origin_node_value)

            for node_index in nodes["isClickable"]["index"]:
                is_click_backend_id = nodes["backendNodeId"][node_index]
                self.dom_index[is_click_backend_id]["isClickable"] = True

            for node_index in layout["stackingContexts"]["index"]:
                is_stacking_cntx_backend_id = nodes["backendNodeId"][node_index]
                self.dom_index[is_stacking_cntx_backend_id]["isStackingContext"] = True

    def create_report1(self):
        response = []
        for backend_id, node in self.dom_index.items():
            if len(node.get("bounds", [])) == 0:
                continue

            if node["node_name"] != "A":
                continue

            if "href" not in node["attributes"]:
                continue

            if node["attributes"]["href"] is None or node["attributes"]["href"][0] == "#":
                continue

            x, y, w, h = node["bounds"]
            if w == 0 or h == 0:
                continue

            ply = Polygon((x, y), (x + w, y), (x + w, y + h), (x, y + h))
            rel_backend_ids = self.idx.intersection((x, y, x + w, y + h), objects=False)
            rel_backend_ids = map(lambda bid: self.dom_index[bid]["node_value"], rel_backend_ids)
            rel_backend_ids = [x.strip() for x in rel_backend_ids if x is not None]
            rel_backend_ids = [x.strip() for x in rel_backend_ids if len(x) > 1]

            if len(rel_backend_ids) == 0:
                continue
            response.append({
                "backend_id": backend_id,
                "node": node.copy(),
                "related": rel_backend_ids,
                "area": ply.area,
                "x": x,
            })
        response = sorted(response, key=lambda elem: [elem["x"], elem["area"]], reverse=True)
        return response

    def create_report(self):
        write_image(self.screenshot["data"], "page.png")
        # colors = ['red', 'green', 'yellow', 'blue', 'white', 'black', 'brown', 'gray']

        response = {}
        self._screenshot = Image.open('page.png').convert('RGB')
        # img = np.array(self._screenshot, dtype=np.uint8)
        # fig, ax = plt.subplots(1)
        # ax.imshow(img)
        for backend_id, node in self.dom_index.items():

            # if ("bounds" not in node) or (len(node["bounds"]) == 0) or (node["node_name"] not in ["DIV", "IMG", "A", "SPAN"]):
            #     continue
            if ("bounds" not in node) or (len(node["bounds"]) == 0):
                continue
            x, y, w, h = node["bounds"]
            response[backend_id] = node.copy()
            response[backend_id]["image"] = self._get_b64_screenshot(x, y, w, h)
            response[backend_id]["intersection"] = list(self.idx.intersection((x, y, x + w, y + h), objects=False))

            # rect = patches.Rectangle((x, y), w, h, linewidth=1, edgecolor=random.choice(colors), facecolor=random.choice(colors))
            # ax.add_patch(rect)
        # plt.show()
        return response

    def __resolve_string(self, string_table_index):
        if string_table_index == -1:
            return None
        else:
            return self.snapshot["strings"][string_table_index]

    def _get_b64_screenshot(self, x, y, w, h):
        try:
            img = self._screenshot.crop((x, y, x + w, y + h))
            with io.BytesIO() as output:
                img.save(output, format="jpeg")
                contents = output.getvalue()
                return base64.b64encode(contents).decode("utf-8")
        except:
            return None

    def __rtree_data_gen(self):
        """
        Returns generator which produces data in following format
        (i, (minx, miny, maxx, maxy), None)
        """
        for doc in self.snapshot["documents"]:
            layout_count = len(doc["layout"]["nodeIndex"])
            for layout_index in range(layout_count):
                node_index = doc["layout"]["nodeIndex"][layout_index]
                backend_id = doc["nodes"]["backendNodeId"][node_index]
                if len(doc["layout"]["bounds"][layout_index]) == 0:
                    continue

                x, y, w, h = doc["layout"]["bounds"][layout_index]
                yield backend_id, (x, y, x + w, y + h), None
