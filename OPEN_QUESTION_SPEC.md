# GRIP Open-Loop Question Specification

One open-ended reasoning question per image, for all 34 domains. Each domain uses a
single template, parameterised per image. This file gives the **exact wording** for
every domain.

Do not modify any image, renderer, or closed L1–L5 question or answer.

---

## The approved structure

Every question follows this shape, taken from the route template:

> Trace the coloured lines that touch the label A at the top of the frame and follow
> each one through its bends to wherever it terminates: decide whether A is connected
> to every other labelled side of the frame or whether some remain unreached from
> it, and name the label at the far end of each line that begins at A. State your
> conclusion, justify it by describing the paths you followed and how you
> distinguished each line by colour where they overlap, and end with a confidence
> score from 0 to 1 for your conclusion.

Anatomy, which every question below follows:

1. Imperative opening naming a **visible** starting point
2. Colon, then the reasoning task as one connected sequence
3. Explicit request to state the conclusion
4. Explicit request to justify by describing what was traced or examined
5. Closing request for a confidence score from 0 to 1

**One flowing instruction. Not clipped. Not a numbered list. Never "explain briefly
what you used in the image."**

## Rules

- Answers derive from stored metadata the closed questions already use. Do not reach
  into fields no closed question touches.
- No coordinates, axes, or index schemes absent from the render.
- Every numeric answer has a tolerance stated in the question text and stored in the
  answer key. No zero-tolerance counts over many overlapping elements.
- Enumerate any fixed vocabulary the responder must use.
- `{...}` marks a per-image parameter.

---

## Two defects to fix first

**`fold_punch` L4 and L5 are identical** — same text, same answer (`exactly half`).
Report whether this affects all 3,000 items. Fix L5 to a distinct counterfactual
before generating the open question.

**`overlap_circles` L3 ground truth is `target_density`** — a metadata field name has
leaked into the answer slot. The question expects `clustered` or `spread`. Report how
many items are affected and correct them.

---

## angle_estimation

Comparison scenes:

> Look at each marked angle in turn, judging the opening between its rays rather than
> how long the rays are drawn: decide which of the two angles is larger, and estimate
> how many degrees larger it is, to the nearest 10 degrees. State your conclusion,
> justify it by describing the direction the rays point at each vertex, and end with a
> confidence score from 0 to 1.

Targets: `larger_angle`, difference from `angle_1_degrees` / `angle_2_degrees`.
Tolerance: ±10°.

Single-angle scenes:

> Look at the marked angle, judging the opening between its rays rather than how long
> the rays are drawn: estimate its size to the nearest 10 degrees, and say whether it
> is acute, right, obtuse or reflex. State your conclusion, justify it by describing
> the direction each ray points from the vertex, and end with a confidence score from
> 0 to 1.

Targets: the nearest-10-degree estimate from `angle_degrees`, and the angle class.
Tolerance: ±10°.

Triangle scenes:

> Look at the triangle's three interior angles, judging each opening rather than the
> lengths of the sides: estimate the size of the largest interior angle to the nearest
> 10 degrees. State your conclusion, justify it by comparing
> the three openings, and end with a confidence score from 0 to 1.

Target: the largest value from `interior_angles_degrees`, rounded to the nearest
10 degrees. Tolerance: ±10°. The vertex label is deliberately not scored because
the source generator assigns labels in a geometry-correlated order.

## clock_reading

> Trace both hands from the centre of the dial out towards the printed numerals: work
> out which is the hour hand and which is the minute hand, and read the time they show.
> State your conclusion, justify it by describing where each hand tip falls among the
> numerals, and end with a confidence score from 0 to 1.

Target: exact time. The smaller-angle sub-fact was removed because it is exactly
derivable from the reported time.

## combination

> Compare each separated piece of every candidate with the target shape: decide which
> single candidate could be slid and turned, without being flipped over, to reproduce
> the target exactly, and say what disqualifies one of the candidates you rejected.
> State your conclusion, justify it by describing how you tried to fit the pieces
> together, and end with a confidence score from 0 to 1.

Targets: `correct_answer_choice`, one rejected candidate's failure reason.

## combination3d

> Compare each separated group of cubes in every candidate with the target structure:
> decide which single candidate could be moved and turned about the upright axis to
> reproduce the target exactly, and say what disqualifies one of the candidates you
> rejected. State your conclusion, justify it by describing how you tried to fit the
> groups together and how you accounted for cubes hidden behind others, and end with a
> confidence score from 0 to 1.

Targets: `correct_answer_choice`, one rejected candidate's failure reason.

## compass_bearing

> Read the compass rose in the corner, then compare the straight-line displacement
> between every pair of landmarks: name the two landmarks that lie closest together,
> and give the bearing in degrees from the alphabetically earlier of them to the other,
> measuring clockwise from north and answering to the nearest 10 degrees. State your
> conclusion, justify it by describing the displacements you compared and how you read
> the direction against the rose, and end with a confidence score from 0 to 1.

Targets: closest pair from `all_pairwise_distances`, bearing from
`all_pairwise_bearings`. Bearing tolerance: ±10°. **Reject items where the second
smallest pairwise distance is less than 5% larger than the smallest**, because the
closest pair is not visually separable there.

Those items use this fallback when the largest pairwise distance is at least 5%
larger than the second largest:

> Read the compass rose in the corner, then take the two landmarks that lie farthest
> apart and give the bearing in degrees from the alphabetically earlier of them to
> the other, measuring clockwise from north and answering to the nearest 10 degrees.
> State your conclusion, justify it by describing the displacement you measured and
> how you read the direction against the rose, and end with a confidence score from 0
> to 1.

Fallback targets: farthest pair from `all_pairwise_distances`, bearing from
`all_pairwise_bearings`. Bearing tolerance: +/-10 degrees. **Reject the item if the
largest pairwise distance is less than 5% larger than the second largest.**

## coordinate_geometry

> Read the position of each labelled point against the printed grid: name the pair of
> points that lie farthest apart, give that distance to the nearest whole unit, and say
> whether it is greater or less than 12 units. State your conclusion, justify it by
> describing the horizontal and vertical grid separations you used, and end with a
> confidence score from 0 to 1.

Targets: farthest pair and distance from `all_pairwise_distances`. Tolerance: ±1 unit.
The farthest-pair variant requires the two largest exact pairwise distances to differ
by at least 1 grid unit. Items below that visual-separation guard use this fallback
instead, so coverage is preserved:

> Read every labelled point against the printed coordinate grid: report the
> coordinates of all points in alphabetical order. State your conclusion, justify it
> by describing how you projected each point to the horizontal and vertical axes, and
> end with a confidence score from 0 to 1.

Fallback target: the complete `points` mapping.

## cube_net

> Look at the labelled squares and the edges they share while the net lies flat: name
> the faces that touch face {TARGET} along a fold edge, then fold the net in your mind
> and name the face that ends up directly opposite {TARGET} on the finished cube. State
> your conclusion, justify it by describing the fold you followed and why a square
> touching only at a corner does not count, and end with a confidence score from 0 to 1.

Targets: `net_edge_neighbors[TARGET]`, `opposite_pairs`. **The two frames are separate
fields — flat neighbours from `net_edge_neighbors`, opposite from `opposite_pairs`.**

## cube_structure

> Scan the structure cube by cube, taking as vertical the direction the drawing
> renders as up: count exactly how many cubes have a visible top face, then work out
> exactly how many cubes are completely hidden from this viewpoint (tolerance 0 for both
> counts). State your conclusion, justify it by describing how you separated visible top
> faces from side faces and how the visible stacks imply any concealed cubes, and end
> with a confidence score from 0 to 1.

Targets: visible top-face count, `hidden_cube_count`. **Exclude items with
`has_ambiguous_visual_floater` true.**

## depth_height

> Compare the objects in the scene using the cues that indicate distance from the
> camera: rank every object from closest to farthest by colour, and name which one lies
> nearest. State your conclusion, justify it by describing the cues you used to order
> them, and end with a confidence score from 0 to 1.

Targets: `depth_ordering`, `closest_object_color`. **Only for items with
`scene_type = depth_ordering`; the stack-height items carry no depth cues.**

For `scene_type = stack_height`:

> Compare the coloured stacks by counting the visible blocks from the common baseline
> upward: rank every stack from shortest to tallest by colour, and name which one is
> tallest. State your conclusion, justify it by describing how you counted the blocks
> in each stack, and end with a confidence score from 0 to 1.

Targets: `height_ordering` reversed into the prompt's shortest-to-tallest order, and
`tallest_stack_color`.

## embedded_figures

> Study the complex figure and each of the candidate shapes beneath it: decide which
> candidate is hidden inside the figure, and say how many sides that shape has. State
> your conclusion, justify it by describing where in the figure you located the shape
> and which lines belong to it rather than to the surrounding clutter, and end with a
> confidence score from 0 to 1.

Targets: `correct_answer_choice`, `target_shape_type` side count.

## fbd

> Examine only the force arrows as they are drawn in this diagram, setting aside what
> the scenario physically requires: count the arrows, name which one represents the
> weight of the body, and rank their drawn magnitudes from largest to smallest,
> grouping any that appear equal. State your conclusion, justify it by describing the
> length and direction of each arrow as drawn, and end with a confidence score from 0
> to 1.

Targets: `shown_forces` count, weight arrow label, drawn magnitude ranking.
**Entirely in the rendered frame. Do not mix in the physical frame — that mixing was
the defect already fixed in L3.**

## fold_punch

> Follow the fold sequence from the first panel through to the punch: work out how many
> holes will appear once the paper is fully unfolded, and decide which of the unfolded
> patterns below shows them in the right places. State your conclusion, justify it by
> describing how each fold doubles the holes and where the mirror lines fall, and end
> with a confidence score from 0 to 1.

Targets: `num_holes`, `correct_answer_choice`.

## gauge_reading

> Read the needle against the printed scale: give the value it points to, rounded to
> the nearest tick mark, and say whether that value lies in the lower or upper half of
> the gauge's range. State your conclusion, justify it by describing which numbered
> marks the needle falls between, and end with a confidence score from 0 to 1.

Targets: `rounded_tick_value`, lower/upper half. **Report how often `needle_value`
sits exactly on a tick; if most items do, this tests landmark reading rather than
interpolation.**

## gear_train

> Follow the mesh from the driver gear through every gear it turns: name the gear that
> rotates fastest, and say whether gear {TARGET} turns in the same
> direction as the driver or the opposite. State your conclusion, justify it by
> describing the tooth counts you compared and how direction alternates along the
> chain, and end with a confidence score from 0 to 1.

Targets: fastest gear from `gears`, and the direction of `{TARGET}` from
`computed_rotation`. `{TARGET}` is chosen deterministically so same/opposite relations
are balanced without changing any image.

## hex_pathfinding

> Look closely at the green HOME hex and everything that immediately surrounds it:
> state whether it sits on the outer boundary of the hexagonal field or fully inside
> it, count how many hexes lie directly against it, and say how many of those are grey
> holes and how many are walkable. Name the position of any hole touching it using
> these six direction names only: upper-left, upper-right, left, right, lower-left,
> lower-right. State your conclusion, justify it by describing exactly what you see
> around HOME, and end with a confidence score from 0 to 1.

Targets: boundary status, neighbour count, hole count, hole directions, all from
`all_tiles` and `home_coordinate`.

## impossible_object

> Trace each beam through the structure and look closely at the points where one beam
> passes in front of another: count those crossings, then decide whether the depth
> relationships they imply could all hold at once in a real three-dimensional object.
> State your conclusion, justify it by describing which beam passes in front at the
> crossings that decide the matter, and end with a confidence score from 0 to 1.

Targets: `num_crossings`, `mode` (constructible or not). Tolerance on crossing
count: ±1.

## laser_mirror

> Follow the laser from where it enters the grid, turning it at each mirror it meets:
> count how many times it reflects, and name the edge and position where it leaves the
> grid. State your conclusion, justify it by describing the path you traced and which
> mirrors it struck, and end with a confidence score from 0 to 1.

Targets: `num_reflections`, `exit_edge`, `exit_position`. **Exclude items where
`num_reflections` is 0 from this variant.** Zero-reflection items use the following
straight-path variant instead:

> Follow the laser from where it enters the grid and trace its straight path across:
> name the edge and position where it leaves, and say how many mirrors it passes
> without striking. State your conclusion, justify it by describing the path you
> traced and where the nearest mirrors sit relative to it, and end with a confidence
> score from 0 to 1.

Targets: `exit_edge`, `exit_position`, and the count of mirror cells sharing an edge
with a traversed `path_cells` cell without lying on the path. Tolerance: 0.

## line_intersection

> Follow both polylines across the image from left edge to right: count how many times
> they cross one another, and say which colour is higher at the left edge. State your
> conclusion, justify it by describing where along the width of the image the crossings
> fall and how you compared the two starting heights, and end with a confidence score
> from 0 to 1.

Targets: `total_intersections` and the colour identified by
`red_above_blue_at_start`. The former endpoint-order target was removed because it was
determined exactly by crossing-count parity in every source item.

## nested_hexagons / nested_squares / nested_triangles

> Work outward from the innermost shape to the outermost: count how many shapes are
> nested inside one another, decide whether each step shrinks by roughly the same
> factor or by a changing one, and estimate through how many degrees the innermost
> shape has been turned relative to the outermost, giving a value from 0 to
> {MODULUS} degrees to the nearest 10. State your conclusion, justify it by describing
> how you matched corresponding corners between the innermost and outermost shapes, and
> end with a confidence score from 0 to 1.

`{MODULUS}` is 120 for triangles, 90 for squares, 60 for hexagons — the same value the
closed L4 uses. Targets: shape count, `factor_progression_direction`,
`cumulative_rotation_degrees`. Tolerance: ±10°.

## occluded_pattern

> Look at the objects visible around the occluder and the arrangement they suggest:
> name the kind of pattern they form, then work out how many objects the occluder is
> hiding from view. State your conclusion, justify it by describing how the visible
> objects let you infer where the pattern continues, and end with a confidence score
> from 0 to 1.

Targets: `pattern_type`, `occluded_object_count`.

## optical_illusion

> Measure the two marked elements against one another, disregarding the lines and
> shapes surrounding them: decide whether they are truly equal in size or whether one
> is genuinely larger, and separately say which one a typical human viewer would
> perceive as larger. State your conclusion, justify it by describing what you measured
> and what the surrounding context does to the impression, and end with a confidence
> score from 0 to 1.

Targets: `are_actually_equal`, `illusion_appears_larger_element`. **The two clauses
are in different frames and the wording must keep them apart — a model reporting true
equality is perceiving correctly and must not be marked wrong.**

## orthographic

> Compare the three orthographic views against one another: work out the smallest
> number of cubes a gravity-supported structure could have while still producing all
> three, and decide whether those views pin down a single arrangement or whether some
> different arrangement could produce the same three silhouettes. State your
> conclusion, justify it by describing which view constrains which direction, and end
> with a confidence score from 0 to 1.

Targets: `minimum_possible_cube_count`, `is_uniquely_determined`.

## overlap_circles

> Examine every circle and the way they lie across one another: count how many circles
> there are, and give how many
> are larger than the average size. State your conclusion, justify it by describing how
> you traced individual outlines where several circles overlap, and end with a
> confidence score from 0 to 1.

Targets: `total_circle_count`, `above_average_radius_count`. The isolated-circle
sub-fact is omitted because its source distribution has a fixable 72.0% majority.
**Exclude items with `max_stack_depth` above 4 — outlines become untraceable.**

## physical_stability

> Work up the stack from the ground, tracking where the combined weight of everything
> above each joint falls relative to the block beneath it: decide whether the stack
> stands or tips, and if it tips, name the lowest joint at which it first fails. State
> your conclusion, justify it by describing how each block sits relative to the one it
> rests on, and end with a confidence score from 0 to 1.

Targets: `is_stable`, `tipping_joint`.

## polyhedron

> Examine the solid's visible faces and the edges bounding them: say what shapes its
> faces are, and decide whether the solid is convex or whether some part of it folds
> inward. State your conclusion, justify it by describing the faces you could identify
> and how you judged convexity, and end with a confidence score from 0 to 1.

Targets: `face_shape_types`, `is_convex`. **Draw only boundary edges — face diagonals
are not edges and made a convex dodecahedron read as non-convex in an earlier build.**

## projectile_motion

> Read the launch values printed beside the trajectory and follow the arc from launch
> to landing: give the horizontal distance at which the projectile reaches its highest
> point, to the nearest metre, and say whether that peak rises above 13 metres. State
> your conclusion, justify it by describing which printed values you used and how they
> determine the shape of the arc, and end with a confidence score from 0 to 1.

Targets: `horizontal_position_at_peak_m`, `max_height_m` against 13 m. Tolerance:
±2 m. **Note this domain's answers are computable from the printed labels alone, which
makes it the natural text-only control.**

## rotation_matching

> Compare each candidate figure with the reference above them: decide which candidate
> is the reference turned rather than flipped over, and identify the one candidate that
> is a mirror image rather than a rotation. State your conclusion, justify it by
> describing which corners you matched between the reference and each candidate, and
> end with a confidence score from 0 to 1.

Targets: `correct_answer_choice`, `reflection_answer_choice`.

## route

> Trace the coloured lines that touch the label {TARGET} {POSITION} of the frame and
> follow each one through its bends to wherever it terminates: decide whether {TARGET}
> is connected to every other labelled side of the frame or whether some remain
> unreached from it, and name the label at the far end of each line that begins at
> {TARGET}. State your conclusion, justify it by describing the paths you followed and
> how you distinguished each line by colour where they overlap, and end with a
> confidence score from 0 to 1 for your conclusion.

`{TARGET}` chosen deterministically, preferring degree 2 or 3. `{POSITION}` is its
printed location. Targets: far-end labels and unreached labels from `routes`.

## rpm

> Read across the rows and down the columns of the matrix to work out what changes from
> one panel to the next: decide which of the numbered choices completes the pattern,
> and say which attributes had to change together for that choice to be the right one.
> State your conclusion, justify it by describing the progression you found along the
> rows and down the columns, and end with a confidence score from 0 to 1.

Targets: `correct_answer_index`, `active_rules`. **Exclude items where any two rows are
identical — the missing panel is then copyable rather than inferable.**

## shadow_inference

> Compare each object with the shadow it casts on the ground: say from which general
> direction the light is coming, and whether it sits high in the sky or low near the
> horizon. State your conclusion, justify it by describing the direction the shadows
> fall and how their length compares with the height of the objects casting them, and
> end with a confidence score from 0 to 1.

Targets: light direction bucket, high/low from `light_elevation_degrees`. **Keep the
existing azimuth exclusion — near 0° or 180° the shadows foreshorten to nothing.**

## surface_topology

> Examine the surface and trace how it closes back on itself: count how many holes or
> handles it has and decide whether it is orientable. State your conclusion, justify it
> by describing the feature that fixes the genus and whether the surface has a
> consistent inside and outside, and end with a confidence score from 0 to 1.

Targets: `genus`, `is_orientable`. Euler characteristic was removed because it is
determined by genus and orientability for these closed surfaces.

## symmetry_pattern

> Examine every shape and where it sits relative to the centre of the arrangement: work
> out which shapes pair with which, decide whether the pattern is fully symmetric or
> whether one element has been displaced from where its partner requires it to be, and
> say what kind of symmetry the arrangement is built on. State your conclusion, justify
> it by describing which shapes you paired and how you judged their positions, and end
> with a confidence score from 0 to 1.

Targets: `is_broken`, `symmetry_type`. **Verify `symmetry_pattern_0143`, which stores
4-fold rotation with six visible shapes — six elements cannot form a 4-fold orbit.
Assert `num_shapes` is a multiple of the symmetry order for every intact pattern.**

---

## Files

Inside each existing dataset folder, unchanged from the current layout:

```
open_questions.csv       # public: question_id, image, prompt
open_answer_key.csv      # private: question_id, image, one column per sub-fact,
                         #   acceptance_set, tolerances, targets
open_annotations.jsonl   # private: the above plus derivation
```

## Validation

- Re-derive every ground truth independently; report mismatches.
- Assert `open_questions.csv` has exactly three columns and no prompt leaks its answer.
- Assert no prompt contains coordinates or vocabulary absent from the render.
- Assert every numeric sub-fact has a tolerance in both the prompt and the key.
- Assert no sub-fact is derivable from another in the same question.
- Report answer distributions and constant-answer baselines per sub-fact; flag above 60%.
- Report exclusion counts for every rule marked in bold above.

## Release

Bump `dataset_version` on each modified domain, update `build_manifest.json` and
READMEs, rebuild the combined open-question files, push to GitHub and Hugging Face.
