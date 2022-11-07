import json
import os
import pathlib

BASEDIR = os.path.join(pathlib.Path(__file__).parent.absolute(), "..")

data = {"default": []}

with open(f"{BASEDIR}/glossary/random_join.txt", "r+", encoding="utf-8") as f:
    for line in f:
        data["default"].append(line.strip())

with open(f"{BASEDIR}/glossary/random_join.json", "w+", encoding="utf-8") as f:
    json.dump(data, f, indent=4, ensure_ascii=False)
