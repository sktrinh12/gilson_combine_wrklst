# Gilson Worklist Combiner 

Automatically generates a `.tsl` worklist file to import into Trilution software to run multiple samples on the GX-180 liquid handler. Contains test code an raw data. The result is a `.py` file, called `combine_gilson_worklist_v2.py`

## Usage

From commman line, type:
```
python combine_gilson_worklist_v2.py ${1} ${2}

```
The two arguments `${1}` and `${2}` would be the two separate worklists generate by the Tecan liquid handler that solubilized samples prior to. 
