import argparse,math,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]));import nested_polygon_common as common
from nested_polygon_generator import generate_dataset,render_existing_dataset
SPEC=common.SPECS["hexagon"]
def vertices(center,side,angle):
 cx,cy=center;start=math.radians(angle-90);return [(cx+side*math.cos(start+math.pi*i/3),cy+side*math.sin(start+math.pi*i/3)) for i in range(6)]
def main():
 p=argparse.ArgumentParser();p.add_argument("--count",type=int,default=3000);p.add_argument("--start-index",type=int,default=1);p.add_argument("--output-dir",type=Path,default=Path(__file__).resolve().parent);p.add_argument("--metadata-only",action="store_true");p.add_argument("--render-existing",action="store_true");a=p.parse_args()
 if a.render_existing:render_existing_dataset(a.output_dir,"hexagons",vertices)
 else:generate_dataset(SPEC,"hexagons",vertices,Path(__file__),Path(__file__).with_name("validate_nested_hexagons_dataset.py"),a.count,a.output_dir,a.start_index,not a.metadata_only)
if __name__=="__main__":main()
