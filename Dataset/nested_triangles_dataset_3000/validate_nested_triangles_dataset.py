import math,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]));import nested_polygon_common as common
from nested_polygon_validator_common import validate_dataset
def vertices(center,side,angle):
 cx,cy=center;radius=side/math.sqrt(3);start=math.radians(angle-90);return [(cx+radius*math.cos(start+2*math.pi*i/3),cy+radius*math.sin(start+2*math.pi*i/3)) for i in range(3)]
if __name__=="__main__":raise SystemExit(1 if validate_dataset(Path(__file__).resolve().parent,common.SPECS["triangle"],"triangles",vertices) else 0)
