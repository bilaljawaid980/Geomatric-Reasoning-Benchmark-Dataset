# Polyhedron Classification Dataset

## 1. Dataset overview

This dataset is designed as a direct extension of the GIQ benchmark (Michalkiewicz et al., arXiv:2506.08194), which found that vision-language models including Claude, Gemini, and ChatGPT show remarkably low accuracy interpreting basic shape properties such as face geometry, convexity, and compound structures of complex polyhedra. This dataset replicates and extends that evaluation methodology at larger scale (3000 images vs GIQ's 224 unique polyhedra) with a structured five-level difficulty progression. See the [GIQ paper](https://arxiv.org/abs/2506.08194).

The current v4 collection contains 17 named solids, 3,000 unique dark-theme wireframe views, and exactly five questions per image (15,000 flattened rows).

### Version 4 geometry and edge correction

Version 4 removes face diagonals from every stored and rendered edge list. The 157 affected `great dodecahedron` records contained the regular dodecahedron geometry plus 60 pentagon diagonals; their PNGs were regenerated with the 30 true boundary edges. The two supposed stellated families were geometry-identical to regular solids and are now named and classified from their actual topology: 157 records became `icosahedron` and 157 became `dodecahedron`. Exhaustive independent checks now require boundary-edge equality, the appropriate Euler characteristic (including component-aware compound handling), hull/face-support convexity, topology-based identity, positive Euler Level-4 answers, and exact PNG edge-set recovery. All 3,000 PNGs pass.

Answer changes from v3 were: Level 1 = 157, Level 2 = 630, Level 3 = 58, Level 4 = 112, Level 5 = 0. The Level-2 count follows the requested literal point-hull definition: all 316 compound records also have every stored vertex on the hull boundary, although their interpenetrating face complexes are reported separately by the face-support diagnostic. Level 5 remains structurally constant (`no` for all 3,000 records) and is documented as such rather than treated as a measured distinction.

## 2. Full generation prompt

```text
Build a Python script that generates 3000 "polyhedron classification" images, testing 
whether models can identify structural properties of 3D solids — directly extending the 
GIQ benchmark's finding that VLMs fail at basic polyhedron face/shape reasoning.

=== VISUAL SPEC ===

Canvas: 450-500px, dark background (#1A1A1A), consistent with your dark-theme datasets.

- Render ONE polyhedron per image as a wireframe (thin light stroke, ~1px, no fill, 
  matching your other wireframe datasets) using isometric/orthographic projection at a 
  randomized viewing angle (rotate the solid randomly around Y-axis 0-360deg, tilt X-axis 
  15-45deg, so no two images show identical orientation).
- Solid types, hardcode exact vertex/edge/face data for each (do not approximate):
  PLATONIC (5): tetrahedron, cube, octahedron, dodecahedron, icosahedron
  ARCHIMEDEAN (subset of 6-8, pick well-known ones): truncated tetrahedron, cuboctahedron, 
  truncated cube, truncated octahedron, rhombicuboctahedron, icosidodecahedron
  CATALAN (subset of 4): triakis tetrahedron, rhombic dodecahedron, triakis octahedron, 
  rhombic triacontahedron
  COMPOUND (2-3): stella octangula (compound of two tetrahedra), compound of cube+octahedron
  NON-CONVEX (2-3): small stellated dodecahedron, great dodecahedron
  Total: aim for 18-22 distinct named solids, each appearing ~135-165 times across the 
  3000 images (varied only by viewing angle/scale/minor jitter).
- For each solid type, hardcode: exact face_count, edge_count, vertex_count, is_convex 
  (bool), face_shape_types (e.g. "triangles" | "squares" | "pentagons" | "mixed"), 
  solid_class ("Platonic"|"Archimedean"|"Catalan"|"Compound"|"NonConvex").
  Verify these numbers against Euler's formula (V - E + F = 2 for convex solids) as a 
  built-in sanity check during generation — reject any hardcoded solid where V-E+F != 2 
  for solids claimed convex.

=== GROUND TRUTH DATA PER IMAGE ===

- solid_name, solid_class, face_count, edge_count, vertex_count, is_convex, 
  face_shape_types, viewing_angle (rotation_y, tilt_x), visible_face_count (faces facing 
  the camera given the current rotation — compute via back-face culling / normal-vector 
  dot product with view direction)

=== 4 QUESTIONS PER IMAGE, ORDERED BY DIFFICULTY ===

LEVEL 1 - Simple Description (always include):
  "How many faces does this solid have in total (including hidden faces)?"
  ground_truth = face_count
  (Explicitly note in question text "including hidden faces" so the question tests 
  knowledge/inference of the full solid, not just visible-face counting)

LEVEL 2 - Basic Relational (always include):
  "Is this solid convex or non-convex? Answer 'convex' or 'non-convex'."
  ground_truth = "convex" if is_convex else "non-convex"

LEVEL 3 - Comparative/Structural (pick ONE at random per image from):
  a) "What shape are the faces of this solid — triangles, squares, pentagons, or a mix 
     of shapes? Answer with one of those options."
     ground_truth = face_shape_types
  b) "How many faces of this solid are visible from this viewing angle (not hidden behind 
     the solid)? Answer with a number."
     ground_truth = visible_face_count
  c) "How many vertices (corner points) does this solid have?"
     ground_truth = vertex_count

LEVEL 4 - Complex/Compound (pick ONE at random per image from):
  a) "Using Euler's formula (Vertices - Edges + Faces = 2 for convex solids), if this 
     solid has {vertex_count} vertices and {edge_count} edges, how many faces MUST it 
     have?" (only for is_convex=true images; fallback to (b) for non-convex)
     ground_truth = 2 - vertex_count + edge_count (must equal face_count; verify
     consistency)
  b) "Which family does this solid belong to: Platonic, Archimedean, Catalan, Compound, 
     or Non-convex? Base your answer on face uniformity — Platonic solids have all 
     identical regular faces, Archimedean have 2+ face types but identical vertices, 
     Catalan solids are duals of Archimedean (irregular faces, identical vertices-per-face 
     count is not guaranteed)."
     ground_truth = solid_class
  c) "This solid is composed of two overlapping shapes forming a compound structure. 
     Is that true for this specific solid? Answer yes or no." 
     ground_truth = "yes" if solid_class == "Compound" else "no"
     (only ask this on ~30% of images regardless of actual class, to keep it 
     discriminative rather than trivially guessable from context)

=== METADATA, OUTPUT, VALIDATION (same pipeline pattern) ===

1. annotations.jsonl, images/polyhedron_{index:04d}.png
2. flatten_annotations.py → dataset_final.csv (same task/image/prompt/groundtruth/metadata 
   schema and difficulty_level → task name mapping as your other 9 datasets)
3. validate_polyhedron_dataset.py: 
   - Re-verify Euler's formula holds for every convex solid (V-E+F=2)
   - Re-verify visible_face_count via independent back-face-culling recomputation from 
     stored vertex/face/normal data and viewing angle
   - Confirm even distribution across the ~18-22 solid types (roughly 135-165 each)
   - Re-derive every ground truth answer, confirm exact match
4. --sample flag, 5 images — manually cross-check face/edge/vertex counts against a 
   reliable geometry reference (Wikipedia polyhedron pages) for at least 3 solid types 
   before trusting the hardcoded data at scale. This is foundational reference data — 
   an error here silently corrupts every image of that solid type (~150 images each).

=== TECHNICAL NOTES ===

- Use a Python 3D geometry library (e.g. numpy for vertex transforms + manual perspective 
  projection, or trimesh/scipy if available) to store exact vertex coordinates for each 
  polyhedron and apply 3D rotation matrices for the randomized viewing angle, then project 
  to 2D for wireframe rendering.
- Source exact vertex/face data for each named solid from a verified reference (standard 
  polyhedron coordinate tables) — do not approximate or hand-eyeball vertex positions.
- Reuse random.seed(i) per image for reproducibility.

Output as: generate_polyhedron_dataset.py

=== README (same 7-section format, citing GIQ explicitly) ===

In section 1, explicitly state: "This dataset is designed as a direct extension of the 
GIQ benchmark (Michalkiewicz et al., arXiv:2506.08194), which found that vision-language 
models including Claude, Gemini, and ChatGPT show remarkably low accuracy interpreting 
basic shape properties such as face geometry, convexity, and compound structures of 
complex polyhedra. This dataset replicates and extends that evaluation methodology at 
larger scale (3000 images vs GIQ's 224 unique polyhedra) with a structured 4-level 
difficulty progression."

Known limitations: solid set limited to ~18-22 named types (not the full enumerable set 
of Archimedean/Catalan solids); wireframe-only rendering (GIQ uses photorealistic Mitsuba 
rendering, a meaningfully different visual difficulty); viewing angle randomized but not 
exhaustively sampled per solid.

Reasoning skills tested: polyhedron family classification, Euler's formula application, 
convexity judgment, face/edge/vertex counting including inference of hidden structure.
```

## 3. Question design rationale

Questions progress from total hidden-inclusive face count, through convexity, to face/visibility/vertex structure and Euler/family/compound reasoning. Actual template usage:

- Level 1: `face_count` 3000
- Level 2: `convexity` 3000
- Level 3: `face_shapes` 1019, `vertex_count` 999, `visible_face_count` 982
- Level 4: `euler_face_count` 1060, `is_compound` 1045, `solid_family` 895

Solid usage (157–158 each):

- `compound of cube and octahedron`: 158
- `cube`: 158
- `cuboctahedron`: 158
- `dodecahedron`: 158
- `great dodecahedron`: 157
- `icosahedron`: 158
- `icosidodecahedron`: 158
- `octahedron`: 158
- `rhombic dodecahedron`: 158
- `rhombic triacontahedron`: 158
- `rhombicuboctahedron`: 158
- `small stellated dodecahedron`: 157
- `stella octangula`: 158
- `tetrahedron`: 158
- `triakis octahedron`: 158
- `triakis tetrahedron`: 158
- `truncated cube`: 158
- `truncated octahedron`: 158
- `truncated tetrahedron`: 158

Class totals: Archimedean=948, Catalan=632, Compound=316, NonConvex=314, Platonic=790.

## 4. Ground truth generation and validation

Platonic coordinates use their standard exact coordinate families. Archimedean meshes are constructed by topology-preserving truncation or rectification, with the rhombicuboctahedron generated from signed permutations of `(1, 1, 1+√2)`. Catalan meshes are computed as convex duals. Compound meshes combine explicit component graphs. Each convex mesh is rejected unless `V−E+F=2`.

The independent validator checks a separate 19-solid reference topology table, Euler's formula for every convex record, file and canvas integrity, and independently rotates stored vertices and recomputes outward face normals/back-face visibility. Every question answer is then re-derived. Final result: **3,000/3,000 passed; 0 mismatches**.

### Version 3 Euler correction and constant Level 5

Version 3 corrects the Level 4 rearrangement of `V - E + F = 2` to `F = 2 - V + E`. All 1,060 Euler-template answers were wrong in v2: 984 were negative and 76 were zero. Version 3 changes exactly those 1,060 Level 4 answers and no answers at Levels 1, 2, 3, or 5. The validator permanently requires every Euler-template answer to equal the stored positive `face_count`, and separately verifies that the vertex and edge values printed in the prompt match the record. All 1,060 printed V/E pairs match, and all 999 Level 3 vertex-count answers match `vertex_count`. Images and all question wording are unchanged.

Level 5 is structurally constant by design: all 3,000 answers are `no`, because removing any face from a closed polyhedron creates a boundary, so the closed-surface Euler formula no longer applies directly. This 100% baseline is a property of the question form, not a measured distinction among solids; a future varying replacement would need to depend on the specific solid.

### Public evaluation files

`question_set.csv` is the only model-facing file. It contains exactly `question_id`, `task`, `image`, and `prompt`. `annotations.jsonl`, `answer_key.csv`, `dataset_final.csv`, and `dataset_final.jsonl` are private answer-key-side artifacts and contain ground truth or scene attributes that can reveal answers. **Do not expose `annotations.jsonl` to a tested model or evaluate a model as though it were a public input file.** The build-only `difficulty_score` field was removed from released annotations and is retained only in `validation_metrics.json` for audit history.

The earlier raw `canvas_size` association (about 0.77) was a sparse-table artifact: 1,801 distinct size pairs occur in only 3,000 records. Canvas width and height are sampled from each item seed independently of the cyclic solid selection. Bias-corrected Cramér's V is below 0.10 for every nonconstant level (0.000, 0.087, 0.088, and 0.000 for Levels 1–4), so images were not regenerated.

## 5. Known limitations

- The set is limited to 19 named types rather than the full Archimedean/Catalan/stellation catalogue.
- Rendering is thin wireframe rather than GIQ's photorealistic Mitsuba imagery, creating a meaningfully different visual task.
- Viewing angles are randomized but not exhaustively sampled for each solid.
- Wireframes show hidden edges, so visible-face questions use geometric face orientation rather than counting unobscured filled regions.
- Non-convex stellations use explicit star-edge diagrams and reference topology counts; their intersecting-face visibility is approximated by oriented face normals rather than ray-traced occlusion.

## 6. Reasoning skills tested

- Polyhedron family classification
- Euler's formula application
- Convexity and compound-structure judgment
- Face, edge, and vertex counting including hidden structure
- View-dependent face-orientation reasoning
- Generalization across randomized 3D rotations

## 7. File structure, schema, and worked example

```text
polyhedron_dataset_3000/
├── images/
├── annotations.jsonl
├── dataset_final.csv
├── dataset_final.jsonl
├── generate_polyhedron_dataset.py
├── validate_polyhedron_dataset.py
├── flatten_annotations.py
├── build_dataset_docs.py
├── validation_report.txt
├── contact_sheet.png
├── generation_prompt.txt
└── README.md
```

Raw annotations include topology counts, class, convexity, face-shape label, view angles, visible count, full vertices/faces/edges, seed, difficulty, and questions. Flattened metadata retains the compact identity and count fields but excludes full mesh arrays.

| task | image | prompt | groundtruth |
|---|---|---|---|
| Image Description | polyhedron_0001.png | How many faces does this solid have in total, including hidden faces? | 4 |
| Basic Relational Reasoning | polyhedron_0001.png | Is this solid convex or non-convex? Answer 'convex' or 'non-convex'. | convex |
| Comparative Reasoning | polyhedron_0001.png | How many faces of this solid face toward the camera from this viewing angle? | 3 |
| Compound Reasoning | polyhedron_0001.png | Which family does this solid belong to: Platonic, Archimedean, Catalan, Compound, or Non-convex? | Platonic |
