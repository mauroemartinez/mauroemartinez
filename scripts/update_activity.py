"""Refresh the public GitHub card with readable spacing and 50-unit Y ticks."""

import math
from pathlib import Path
import re
import sys
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

SOURCE = (
    "https://github-profile-summary-cards.vercel.app/api/cards/profile-details"
    "?username=mauroemartinez&theme=github_dark&name=Mauro%20Martinez"
    "&title_color=58a6ff&text_color=c9d1d9&chart_color=59d6ef"
)
NS = {"s": "http://www.w3.org/2000/svg"}
ET.register_namespace("", NS["s"])


def format_card(source):
    root = ET.fromstring(source)
    # shortcut: depends on the upstream SVG structure; fail without overwriting if it changes.
    chart = next(g for g in root.iter(f"{{{NS['s']}}}g") if g.find("s:g[@class='gpsc-chart']", NS) is not None)
    axis = chart.find("s:g[@text-anchor='start']", NS)
    if axis is None:
        raise ValueError("Upstream chart has no Y axis")
    ticks = axis.findall("s:g[@class='tick']", NS)
    points = [
        (float(tick.find("s:text", NS).text), float(re.fullmatch(r"translate\(0,([\d.eE+-]+)\)", tick.get("transform")).group(1)))
        for tick in ticks
    ]
    maximum, top = max(points)
    minimum, bottom = min(points)
    if minimum != 0 or maximum <= 0 or not all(math.isfinite(v) for point in points for v in point):
        raise ValueError("Unexpected upstream Y scale")
    for tick in ticks:
        axis.remove(tick)
    for value in range(0, math.floor(maximum / 50) * 50 + 1, 50):
        position = bottom + (top - bottom) * value / maximum
        tick = ET.SubElement(axis, f"{{{NS['s']}}}g", {"class": "tick", "transform": f"translate(0,{position:g})"})
        ET.SubElement(tick, f"{{{NS['s']}}}line", {"stroke": "currentColor", "x2": "6"})
        ET.SubElement(tick, f"{{{NS['s']}}}text", {"fill": "currentColor", "x": "9", "dy": "0.32em"}).text = str(value)
    root.set("width", "900")
    root.set("height", "260")
    root.set("viewBox", "0 0 900 260")
    chart.set("transform", "translate(460,30) scale(1,1.25)")
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def self_test():
    sample = '''<svg xmlns="http://www.w3.org/2000/svg"><g><g class="gpsc-chart"><path d="M0,110L350,0"/></g><g text-anchor="start"><g class="tick" transform="translate(0,110.5)"><text>0</text></g><g class="tick" transform="translate(0,0.5)"><text>200</text></g></g></g></svg>'''
    result = ET.fromstring(format_card(sample))
    labels = result.findall(".//s:g[@class='tick']/s:text", NS)
    assert [label.text for label in labels] == ["0", "50", "100", "150", "200"]
    assert result.find(".//s:path", NS).get("d") == "M0,110L350,0"
    assert result.get("viewBox") == "0 0 900 260"


if __name__ == "__main__":
    self_test()
    if "--check" not in sys.argv:
        request = Request(SOURCE, headers={"User-Agent": "mauroemartinez-readme"})
        with urlopen(request, timeout=30) as response:
            card = format_card(response.read())
        destination = Path(__file__).resolve().parents[1] / "assets/github-activity.svg"
        pending = destination.with_suffix(".tmp")
        pending.write_bytes(card)
        pending.replace(destination)
