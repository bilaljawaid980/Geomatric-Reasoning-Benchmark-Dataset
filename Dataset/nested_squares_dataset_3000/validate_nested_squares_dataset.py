import math,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]));import nested_polygon_common as common
from nested_polygon_validator_common import validate_dataset
def vertices(center,side,angle):
 cx,cy=center;a=math.radians(angle);c=math.cos(a);s=math.sin(a);h=side/2;return [(cx+c*x-s*y,cy+s*x+c*y) for x,y in ((-h,-h),(h,-h),(h,h),(-h,h))]
if __name__=="__main__":raise SystemExit(1 if validate_dataset(Path(__file__).resolve().parent,common.SPECS["square"],"squares",vertices) else 0)
