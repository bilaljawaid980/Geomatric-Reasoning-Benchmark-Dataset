import math,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]));import nested_polygon_common as common
from nested_polygon_validator_common import validate_dataset
def vertices(center,side,angle):
 cx,cy=center;return [(cx+side*math.cos(math.radians(angle-90+60*i)),cy+side*math.sin(math.radians(angle-90+60*i))) for i in range(6)]
if __name__=="__main__":raise SystemExit(1 if validate_dataset(Path(__file__).resolve().parent,common.SPECS["hexagon"],"hexagons",vertices) else 0)
