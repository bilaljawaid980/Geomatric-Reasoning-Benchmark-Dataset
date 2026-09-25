## angle_estimation_dataset_3000

**Item:** angle_estimation_0952.png

| Level | Type | Question | Ground truth |
|---|---|---|---|
| L1 | shown_angle_count | How many separate angles are shown in this image? | 2 |
| L2 | larger_angle | Which angle is larger, Angle 1 or Angle 2? Answer with the label. | Angle 2 |
| L3 | angle_difference_nearest_10 | Approximately how many degrees larger is the bigger angle compared to the smaller one, rounded to the nearest 10 degrees? | 20 |
| L4 | angle_sum_bucket | If Angle 1 and Angle 2 were added together, answer 'right angle' if the sum is within 15 degrees of 90°, 'straight angle' if it is within 15 degrees of 180°, otherwise answer 'neither'. | neither |
| L5 | double_smaller_angle_compare | If the smaller shown angle were doubled, would it be larger than, equal to, or smaller than the other angle? | smaller |

**Metadata fields available:** angle_1_degrees, angle_2_degrees, angle_degrees, angles, arc_sweep_degrees, canvas_size, dataset_version, difficulty_score, id, image_path, interior_angles_degrees, larger_angle, largest_angle_vertex, marked_sweep, ray_endpoints, scene_type, seed, smallest_angle_vertex, triangle_class, triangle_vertices, vertex

---

## clock_reading_dataset_3000

**Item:** clock_reading_1122.png

| Level | Type | Question | Ground truth |
|---|---|---|---|
| L1 | hour_recently_passed | Which hour has the short hand most recently passed? Answer with a number from 1 to 12. | 8 |
| L2 | minute_before_after_six | Is the minute hand pointing before or after the 6 (half past)? Answer 'before' or 'after'. | before |
| L3 | exact_clock_time | What is the exact time shown? Answer in HH:MM format. | 08:27 |
| L4 | smaller_hand_angle | What is the smaller angle between the hour and minute hands, rounded to the nearest degree? | 92 |
| L5 | angle_after_twenty_minutes | If 20 minutes were added to the current time, what would the new smaller angle between the hands be, rounded to the nearest degree? | 19 |

**Metadata fields available:** after_twenty_minutes, angle_between_hands, angle_between_hands_fraction, canvas_size, dataset_version, difficulty_score, hour, hour_angle, hour_angle_fraction, id, image_path, minute, minute_angle, minute_angle_fraction, minute_relation_to_six, seed, time

---

## combination3d_dataset_3000

**Item:** combination3d_1531.png

| Level | Type | Question | Ground truth |
|---|---|---|---|
| L1 | target_cube_count | How many individual cubes make up the target structure? | 11 |
| L2 | assembly3d_choice | Which set of pieces (A, B, C, or D) can be assembled using only translation and rotation around the vertical axis to exactly form the target structure? Answer with the letter. | C |
| L3 | candidate_same_count | Does candidate A have the same total number of cubes as the target? Answer yes or no. | yes |
| L4 | target_count_and_height | Give the target's total cube count and maximum height along the vertical z-axis in layers as count,height. | 11,2 |
| L5 | whole_group_rotation | If the correctly assembled structure were rotated 90 degrees around the vertical z-axis as a whole, would it be the 'same shape, different angle' or a 'different structure'? | same shape, different angle |

**Metadata fields available:** candidates, canvas_size, coordinate_frame, correct_answer_choice, dataset_version, difficulty_score, gravity_supported, id, image_path, permitted_piece_rotation_axes, renderer_projection, seed, target_cube_count, target_cubes, vertical_axis

---

## combination_dataset_3000

**Item:** combination_1467.png

| Level | Type | Question | Ground truth |
|---|---|---|---|
| L1 | target_cell_count | How many unit cells make up the target shape? | 8 |
| L2 | assembly_choice | Which set of pieces (A, B, C, or D) can be assembled using only translation and rotation, with no mirroring, to exactly form the target? | C |
| L3 | candidate_piece_count | How many separate pieces are shown in candidate B? | 2 |
| L4 | wrong_area_choice | Which candidate has the wrong total number of unit cells compared with the target? | B |
| L5 | remove_top_left_cell_connectivity | If the topmost, then leftmost, target cell were removed, would the remaining target be connected or disconnected? | connected |

**Metadata fields available:** candidates, canvas_size, correct_answer_choice, dataset_version, difficulty_score, id, image_path, seed, target_cell_count, target_cells

---

## compass_bearing_dataset_3000

**Item:** compass_bearing_1343.png

| Level | Type | Question | Ground truth |
|---|---|---|---|
| L1 | landmark_count | How many landmarks are shown on this map? | 4 |
| L2 | north_south_relation | Is landmark D located north or south of landmark B? Answer 'north', 'south', or 'same latitude'. | south |
| L3 | rounded_compass_bearing | What is the compass bearing from landmark B to landmark C, rounded to the nearest 10 degrees? Answer with a three-digit number in curly brackets, e.g. {045}. | 090 |
| L4 | turn_angle_direction | If you are standing at landmark C facing landmark A, and then turn to face landmark B instead, how many degrees would you need to turn, and in which direction? Round the angle to the nearest degree and answer with the amount plus 'clockwise' or 'counterclockwise'. | 16 degrees counterclockwise |
| L5 | counterfactual_bearing_projection | If you traveled from landmark A along a bearing of 200 degrees for the same distance as A-to-C, which of these landmarks would the projected endpoint be closest to: B, C, D? Give the letter and briefly justify using endpoint distance and bearing difference. | D; projected endpoint is closest to D (37.7 map units away; bearing difference 10.7 degrees) |

**Metadata fields available:** all_pairwise_bearings, all_pairwise_distances, canvas_size, dataset_version, difficulty_score, distance_unit, frame_conventions, generation_attempt, has_path, id, image_path, landmarks, level2_pair, level3_pair, level4_triple, level5_projection, num_landmarks, path_bearing, path_end, path_start, seed

---

## coordinate_geometry_dataset_3000

**Item:** coordinate_geometry_2624.png

| Level | Type | Question | Ground truth |
|---|---|---|---|
| L1 | point_coordinates | What are the coordinates of point A? | (-6, 4) |
| L2 | pair_distance | What is the distance between point A and point C, rounded to 2 decimal places? | 2.24 |
| L3 | pair_midpoint | What are the coordinates of the midpoint between point B and point C? | (-6, 0.5) |
| L4 | distance_vs_10 | The distance from point A to point B is 9.06 units. Is this greater than, less than, or equal to 10 units? | less than |
| L5 | move_point_new_distance | If point A moved 2 units right and 1 unit down, what would its new distance from point B be, rounded to two decimals? | 8.06 |

**Metadata fields available:** all_pairwise_distances, all_pairwise_midpoints, canvas_size, collinear_labels, dataset_version, difficulty_score, frame_conventions, grid_range, id, image_path, is_collinear_triple, num_points, points, seed

---

## cube_net_dataset_3000

**Item:** cube_net_1746.png

| Level | Type | Question | Ground truth |
|---|---|---|---|
| L1 | face_count | How many squares (faces) make up this cube net? | 6 |
| L2 | net_edge_neighbor | Name one face that shares a fold edge with face B. | D |
| L3 | net_edge_degree | How many faces share a fold edge with face F? | 1 |
| L4 | folded_pair_relationship | If this net is folded into a cube, are face D and face E adjacent or opposite? Answer 'adjacent' or 'opposite'. | opposite |
| L5 | swap_preserves_opposite | If the positions of faces F and E were swapped in this net, would face F still end up opposite the same face it currently is opposite to? Answer yes or no. | no |

**Metadata fields available:** canvas_size, cube_adjacent_faces, cube_adjacent_pairs, dataset_version, difficulty_score, frame_conventions, id, image_path, letter_positions, net_edge_neighbors, net_edge_pairs, net_layout_type, opposite_pairs, seed, square_size_px, stroke_width_px

---

## cube_structure_dataset_3000

**Item:** cube_structure_2141.png

| Level | Type | Question | Ground truth |
|---|---|---|---|
| L1 | total_cube_count | How many cubes make up this structure in total? Answer with a number in curly brackets, e.g. {12}. | 11 |
| L2 | base_layer_count | How many cubes are touching the ground (bottom layer)? Answer with a number in curly brackets, e.g. {5}. | 8 |
| L3 | largest_layer | Which layer (counting from the ground as layer 1) has the most cubes? Answer with a number in curly brackets, e.g. {2}. | 1 |
| L4 | hidden_cube_count | How many cubes are completely hidden from the current view? Answer with a number. | 1 |
| L5 | hidden_to_visible_180 | If this structure were rotated 180 degrees around the vertical axis, how many currently-hidden cubes would become visible? Answer with a number in curly brackets, e.g. {3}. | 1 |

**Metadata fields available:** base_layer_count, canvas_size, cluster_counts, color_cluster_count, coordinate_frame, cubes, cubes_per_layer, dataset_version, difficulty_score, generation_attempt, has_ambiguous_visual_floater, hidden_cube_count, hidden_members_per_cluster, hidden_to_visible_180, id, image_path, line_width_px, max_height, render_frame, rotation_axis_level5, seed, total_cube_count, vertical_axis, visible_cube_count

---

## depth_height_dataset_3000

**Item:** depth_height_2725.png

| Level | Type | Question | Ground truth |
|---|---|---|---|
| L1 | object_count | How many objects are shown in this scene? | 4 |
| L2 | pair_closer | Which object is closer to the camera: the purple circle or the orange triangle? | orange |
| L3 | depth_ordering | Rank all objects in this scene from closest to farthest, by color. | ['magenta', 'orange', 'purple', 'teal'] |
| L4 | depth_span | What is the difference between the farthest and closest stored depth values, rounded to two decimals? | 0.65 |
| L5 | counterfactual_size | If the teal object moved twice as far from the camera as its current distance, would it appear larger, smaller, or about the same size as the orange object? | smaller |

**Metadata fields available:** base_size_px, block_height_px, block_pitch_px, block_width_px, canvas_size, closest_object_color, dataset_version, depth_ordering, difficulty_score, farthest_object_color, frame_conventions, height_ordering, id, image_path, objects, scene_type, seed, shortest_stack_color, stacks, tallest_stack_color

---

## embedded_figures_dataset_3000

**Item:** embedded_figure_1550.png

| Level | Type | Question | Ground truth |
|---|---|---|---|
| L1 | total_segments | How many straight line segments make up this complex figure in total? | 12 |
| L2 | target_side_count | How many sides does the hidden target shape have (visible in the answer choices below)? | 4 |
| L3 | embedded_choice | Which of the four candidate shapes (A, B, C, D) is actually hidden within the complex figure above? Answer with the letter. | B |
| L4 | distractor_segment_count | How many of the total line segments in the complex figure are NOT part of the hidden target shape (i.e. are distractor lines)? | 8 |
| L5 | remove_target_edge_closure | If exactly one edge of the embedded target polygon were removed while all other target edges stayed, would the target be closed or open? | open |

**Metadata fields available:** candidate_choices, canvas_size, correct_answer_choice, dataset_version, difficulty_score, distractor_choices_info, id, image_path, num_distractor_segments, num_total_segments, same_side_foil_exists, seed, segments, target_edges, target_shape_type, target_vertices

---

## fbd_dataset_3000

**Item:** fbd_0644.png

| Level | Type | Question | Ground truth |
|---|---|---|---|
| L1 | shown_force_count | How many force arrows are shown in this diagram? | 2 |
| L2 | identify_force | Which labeled arrow represents the weight force on the analyzed body? Answer with the arrow label. | W |
| L3 | rank_balance_equilibrium | Using only the arrows as drawn in this diagram, rank their shown magnitudes from largest to smallest, grouping ties, and state whether their shown vertical components are balanced. Then, as a separate judgment using the physically correct version of the scenario, state whether the body is in equilibrium overall. Give all three answers and keep the drawn-diagram and physically-correct frames separate. | {'magnitude_ranking': [['T'], ['W']], 'physical_equilibrium': 'yes', 'shown_vertical_forces_balanced': 'no'} |
| L4 | compound_force_and_error_detection | Using the physically correct force model (not any intentionally incorrect arrow as drawn), what is the physical net force magnitude in newtons, and what is the tension magnitude for this scenario? Give both values. Separately, inspect the rendered diagram: one drawn force is incorrect; identify that drawn arrow and explain its error relative to the physically correct model. | {'net_force_N': 0.0, 'tension_magnitude': 135.08, 'wrong_force_details': {'arrow_label': 'T', 'correct_value': {'direction_degrees': 90.0, 'magnitude': 135.0837}, 'error_kind': 'magnitude', 'shown_value': {'direction_degrees': 90.0, 'magnitude': 189.11718}, 'whats_wrong': 'magnitude is 40% larger than the physically required value', 'which_force': 'tension'}} |
| L5 | force_removed_direction | If force T were removed while all other physical forces stayed unchanged, what direction would the resulting acceleration point? Use 0 degrees for right and 90 degrees for up. | downward (270 degrees; 0=right, 90=up) |

**Metadata fields available:** analysis_mass_kg, analysis_target, dataset_version, derived_quantities, difficulty_score, forces, id, image_path, is_equilibrium, missing_force_id, missing_force_type, net_force_direction_degrees, net_force_magnitude, physical_frame, physics_parameters, preset, question_frame_policy, rendered_frame, resulting_acceleration_m_s2, scenario_type, seed, shown_forces, shown_net_force_direction_degrees, shown_net_force_magnitude, wrong_force_details

---

## fold_punch_dataset_3000

**Item:** fold_punch_1503.png

| Level | Type | Question | Ground truth |
|---|---|---|---|
| L1 | fold_count | How many fold steps are shown before the paper is punched? | 2 |
| L2 | unfolded_hole_count | How many holes will appear when the paper is fully unfolded? | 4 |
| L3 | correct_pattern_choice | Which of the four unfolded patterns (A, B, C, D) correctly shows where the holes will appear? Answer with the letter. | C |
| L4 | remove_last_fold | If the last fold were removed, would the unfolded hole count be 'exactly half' or have a 'different relationship'? | exactly half |
| L5 | remove_last_fold | If the last fold were removed, would the unfolded hole count be 'exactly half' or have a 'different relationship'? | exactly half |

**Metadata fields available:** candidates, canvas_size, coordinate_frame, correct_answer_choice, dataset_version, difficulty_score, final_folded_bounds, fold_sequence, id, image_path, minimum_distractor_displacement, num_folds, num_holes, punch_position, seed, unfolded_hole_positions

---

## gauge_reading_dataset_3000

**Item:** gauge_reading_1512.png

| Level | Type | Question | Ground truth |
|---|---|---|---|
| L1 | minimum_scale_value | What is the minimum value shown on this gauge's scale? | 0 |
| L2 | lower_or_upper_half | Is the needle pointing to a value in the lower half or upper half of the gauge's range? Answer 'lower half' or 'upper half'. | lower half |
| L3 | needle_value_nearest_tick | What value is the needle pointing to, rounded to the nearest tick mark interval? | 40 |
| L4 | danger_zone_status | Is the needle currently in the danger zone, if one is marked? If so, by how much does it exceed the threshold? | no danger zone marked |
| L5 | quarter_range_increase | If the needle value increased by 25% of the gauge's full range, would it exceed the maximum value on the scale? Answer yes or no, and give the new value. | no; new value 65 |

**Metadata fields available:** canvas_size, danger_zone_threshold, danger_zone_threshold_fraction, dataset_version, dial_start_angle, dial_sweep_degrees, difficulty_score, id, image_path, instrument_type, max_value, min_value, needle_angle, needle_angle_fraction, needle_value, needle_value_fraction, projected_exceeds_maximum, projected_value_after_quarter_range, projected_value_fraction, rounded_tick_value, rounded_tick_value_fraction, seed, tick_interval, unit

---

## gear_train_dataset_3000

**Item:** gear_train_1314.png

| Level | Type | Question | Ground truth |
|---|---|---|---|
| L1 | gear_count | How many gears are shown in this gear train? | 4 |
| L2 | direct_mesh_direction | Gear B directly meshes with gear A (the driver). Does gear B rotate in the same direction as the driver, or the opposite direction? | opposite |
| L3 | fastest_gear | Which gear rotates the fastest (has the highest RPM)? Answer with the letter. | A |
| L4 | multi_mesh_target_rpm | Gear A (the driver) rotates at 50 RPM. What is the RPM of gear D, which is 3 meshes from the driver? Answer with a number rounded to 1 decimal place. | 42.3 |
| L5 | double_teeth_counterfactual | If gear A's tooth count were doubled while the driver's RPM and direction stayed fixed, would gear D's rotation speed increase, decrease, or stay the same? Also state whether its rotation direction would change. | increase; direction unchanged |

**Metadata fields available:** arrangement_type, canvas_size, computed_rotation, dataset_version, difficulty_score, driver_direction, driver_label, driver_rpm, gears, id, image_path, level2_neighbor, level4_mesh_distance, level4_target, level5_scenario, mesh_edges, num_gears, seed

---

## hex_pathfinding_dataset_3000

**Item:** hex_pathfinding_2114.png

| Level | Type | Question | Ground truth |
|---|---|---|---|
| L1 | hole_tile_count | How many grey (hole) tiles are shown in this grid? | 11 |
| L2 | adjacent_neighbor_status | Is the tile outlined in blue with a '?', immediately adjacent to START, a grey hole or walkable? Answer 'hole' or 'walkable'. | hole |
| L3 | shortest_path_length | What is the minimum number of moves needed to travel from START to HOME while avoiding all grey holes? Answer with a number in curly brackets. | 6 |
| L4 | shortest_path_uniqueness | Is the shortest path from START to HOME unique, or are there multiple different shortest paths of the same length? If multiple, how many? | multiple (3) |
| L5 | blocked_tile_replanning | If the walkable tile marked with a purple X at axial position (2,1) were turned into a hole, would the shortest path length increase, stay the same, or would there be no valid path? If it increases, state the new shortest length. | increase to 7 moves |

**Metadata fields available:** all_tiles, canvas_size, coordinate_frame, dataset_version, difficulty_score, generation_attempt, grid_radius, hole_density, home_coordinate, id, image_path, level2_neighbor_coordinate, level2_neighbor_direction_is_toward_home, level5_blocked_coordinate, level5_new_shortest_path_length, level5_outcome, num_alternate_shortest_paths, num_hole_tiles, seed, shortest_path_length, shortest_path_sequence, start_coordinate

---

## impossible_object_dataset_3000

**Item:** impossible_object_1429.png

| Level | Type | Question | Ground truth |
|---|---|---|---|
| L1 | beam_count | How many distinct beams or segments make up this structure? | 5 |
| L2 | constructible | Is this 3D structure physically constructible in real space? Answer yes or no. | yes |
| L3 | nearest_center_front_beam | At the crossing closest to the image centre, which beam passes in front? Answer with the beam label. | B |
| L4 | crossing_count | How many crossing points are visible where one beam passes over another? Answer with a number. | 8 |
| L5 | single_beam_constructibility_repair | Which single beam, if removed, would make this structure physically constructible? Answer with the beam label, or 'already constructible' if the structure requires no change. | already constructible |

**Metadata fields available:** beams, canvas_size, color, crossings, dataset_version, depth_constraint_representation, depth_constraints, difficulty_score, id, image_path, mode, num_beams, num_crossings, reference_crossing_id, reference_crossing_point, reference_front_beam, reference_rule, removable_beam_label, scene_params, seed

---

## laser_mirror_dataset_3000

**Item:** laser_mirror_1299.png

| Level | Type | Question | Ground truth |
|---|---|---|---|
| L1 | mirror_count | How many mirrors are placed in this grid? | 2 |
| L2 | hits_any_mirror | Does the laser hit at least one mirror before exiting the grid? Answer yes or no. | yes |
| L3 | reflection_count | How many times does the laser reflect off a mirror before exiting the grid? | 1 |
| L4 | exit_edge_position | From which edge and position does the laser exit the grid? Answer with the edge (top/bottom/left/right) and cell position. | right, position 4 |
| L5 | flipped_mirror_exit | If the mirror at cell R4C3 were rotated 90 degrees (changed from '/' to '\\' or vice versa), would the laser's exit point change? If so, where would it now exit? | yes; exits at left, position 4 |

**Metadata fields available:** canvas_size, dataset_version, difficulty_score, entry_cell, entry_direction, entry_edge, entry_position, exit_cell, exit_direction, exit_edge, exit_position, generation_attempt, grid_size, id, image_path, level5_exit_cell, level5_exit_changed, level5_exit_direction, level5_exit_edge, level5_exit_position, level5_flipped_orientation, level5_mirror_cell, level5_num_reflections, level5_original_orientation, level5_path_cells, mirrors, num_reflections, path_cells, path_length, reflection_points, seed

---

## line_intersection_dataset_3000

**Item:** line_intersect_0918.png

| Level | Type | Question | Ground truth |
|---|---|---|---|
| L1 | blue_segment_count | How many line segments make up the blue line? | 3 |
| L2 | intersection_count | How many times do the blue and red lines touch each other? Answer with a number in curly brackets, e.g. {5}. | 1 |
| L3 | leftmost_intersection_side | Is the leftmost intersection point closer to the left edge or the right edge of the image? Answer 'left' or 'right'. | left |
| L4 | intersection_parity | If the two lines intersect an odd number of times, the line that starts higher must end lower (and vice versa). Based on this rule, do these two lines intersect an odd or even number of times? Answer 'odd' or 'even'. | odd |
| L5 | translate_red_intersections | If the entire red polyline were translated exactly 60 pixels downward without changing its shape, how many red-blue intersections would remain? | 0 |

**Metadata fields available:** blue_points, blue_self_intersecting, canvas_size, crossed_from_above_to_below, dataset_version, difficulty_score, frame_conventions, id, image_path, intersections, leftmost_intersection_x, num_blue_segments, num_red_segments, red_above_blue_at_end, red_above_blue_at_start, red_points, red_self_intersecting, rightmost_intersection_x, seed, total_intersections, wording_variant

---

## nested_hexagons_dataset_3000

**Item:** nested_hexagons_1589.png

| Level | Type | Question | Ground truth |
|---|---|---|---|
| L1 | count_hexagons | How many hexagons are in this image? Please answer with a number in curly brackets, e.g. {10}. | 7 |
| L2 | size_progression_direction | Do the shapes shrink by roughly the same factor at each step, or does the amount of shrinking change as you move inward? Answer 'constant' or 'changing'. | constant |
| L3 | outer_inner_side_ratio | What is the approximate ratio of the outermost hexagon's side length to the innermost hexagon's side length? Answer as a number rounded to 1 decimal in curly brackets, e.g. {3.2}. | 4.8 |
| L4 | cumulative_rotation | Through approximately how many degrees has the innermost hexagon been rotated relative to the outermost hexagon? Because regular hexagons have 6-fold symmetry, answer with a value from 0 to 60 in curly brackets, e.g. {20}. | 31 |
| L5 | next_hexagon_visually_distinguishable | If one more hexagon were added inside the innermost one following the same size-reduction pattern, would its side length still be long enough to be visually distinguishable at this image resolution (i.e. greater than roughly 12% of the outermost hexagon's side length)? Answer yes or no. | yes |

**Metadata fields available:** canvas_size, center_drift, color_alternation, cumulative_rotation_degrees, cumulative_rotation_fraction, dataset_version, difficulty_score, drift_floor_applied_as_rejection, extrapolation_reduction_factor, factor_progression_direction, generation_attempt, generation_rejections, hexagons, id, image_path, line_width_px, matched_clearance_target_px, minimum_adjacent_clear_background_px, num_hexagons, offset_requested_pre_containment, paired_nuisance_rank, parameter_seed, reduction_factor_span, reduction_mode, rejected_candidates, rotation_mode, sampled_total_inner_fraction, sampled_total_reduction_root, seed, size_axis_band, size_axis_pair_rank, size_reduction_factor, source_index, step_reduction_factors, stroke_colors_used, symmetry_modulus_degrees, target_cumulative_rotation_degrees

---

## nested_squares_dataset_3000

**Item:** nested_squares_1493.png

| Level | Type | Question | Ground truth |
|---|---|---|---|
| L1 | count_squares | How many squares are in this image? Please answer with a number in curly brackets, e.g. {10}. | 7 |
| L2 | size_progression_direction | Do the shapes shrink by roughly the same factor at each step, or does the amount of shrinking change as you move inward? Answer 'constant' or 'changing'. | constant |
| L3 | outer_inner_side_ratio | What is the approximate ratio of the outermost square's side length to the innermost square's side length? Answer as a number rounded to 1 decimal in curly brackets, e.g. {3.2}. | 5.0 |
| L4 | cumulative_rotation | Through approximately how many degrees has the innermost square been rotated relative to the outermost square? Because regular squares have 4-fold symmetry, answer with a value from 0 to 90 in curly brackets, e.g. {25}. | 36 |
| L5 | next_square_visually_distinguishable | If one more square were added inside the innermost one following the same size-reduction pattern, would its side length still be long enough to be visually distinguishable at this image resolution (i.e. greater than roughly 12% of the outermost square's side length)? Answer yes or no. | yes |

**Metadata fields available:** canvas_size, center_drift, color_alternation, cumulative_rotation_degrees, cumulative_rotation_fraction, dataset_version, difficulty_score, drift_floor_applied_as_rejection, extrapolation_reduction_factor, factor_progression_direction, generation_attempt, generation_rejections, id, image_path, line_width_px, matched_clearance_target_px, minimum_adjacent_clear_background_px, num_squares, offset_requested_pre_containment, paired_nuisance_rank, parameter_seed, reduction_factor_span, reduction_mode, rejected_candidates, rotation_mode, sampled_total_inner_fraction, sampled_total_reduction_root, seed, size_axis_band, size_axis_pair_rank, size_reduction_factor, source_index, squares, step_reduction_factors, stroke_colors_used, symmetry_modulus_degrees, target_cumulative_rotation_degrees

---

## nested_triangles_dataset_3000

**Item:** nested_triangles_1485.png

| Level | Type | Question | Ground truth |
|---|---|---|---|
| L1 | count_triangles | How many triangles are in this image? Please answer with a number in curly brackets, e.g. {10}. | 9 |
| L2 | size_progression_direction | Do the shapes shrink by roughly the same factor at each step, or does the amount of shrinking change as you move inward? Answer 'constant' or 'changing'. | constant |
| L3 | outer_inner_side_ratio | What is the approximate ratio of the outermost triangle's side length to the innermost triangle's side length? Answer as a number rounded to 1 decimal in curly brackets, e.g. {3.2}. | 8.2 |
| L4 | cumulative_rotation | Through approximately how many degrees has the innermost triangle been rotated relative to the outermost triangle? Because regular triangles have 3-fold symmetry, answer with a value from 0 to 120 in curly brackets, e.g. {25}. | 42 |
| L5 | next_triangle_visually_distinguishable | If one more triangle were added inside the innermost one following the same size-reduction pattern, would its side length still be long enough to be visually distinguishable at this image resolution (i.e. greater than roughly 12% of the outermost triangle's side length)? Answer yes or no. | no |

**Metadata fields available:** canvas_size, center_drift, color_alternation, cumulative_rotation_degrees, cumulative_rotation_fraction, dataset_version, difficulty_score, drift_floor_applied_as_rejection, extrapolation_reduction_factor, factor_progression_direction, generation_attempt, generation_rejections, id, image_path, line_width_px, matched_clearance_target_px, minimum_adjacent_clear_background_px, num_triangles, offset_requested_pre_containment, paired_nuisance_rank, parameter_seed, reduction_factor_span, reduction_mode, rejected_candidates, rotation_mode, sampled_total_inner_fraction, sampled_total_reduction_root, seed, size_axis_band, size_axis_pair_rank, size_reduction_factor, source_index, step_reduction_factors, stroke_colors_used, symmetry_modulus_degrees, target_cumulative_rotation_degrees, triangles

---

## occluded_pattern_dataset_3000

**Item:** occluded_pattern_1541.png

| Level | Type | Question | Ground truth |
|---|---|---|---|
| L1 | visible_object_count | How many objects are clearly visible (not hidden behind the occluder) in this image? | 8 |
| L2 | total_object_count | Assuming the pattern continues behind the occluded region, how many objects are there in total? Answer with a number in curly brackets, e.g. {12}. | 10 |
| L3 | pattern_type | What type of pattern do the objects form - a grid, a circle, or a triangular arrangement? Answer with one word. | circle |
| L4 | occluded_object_count | How many objects are hidden behind the occluded region specifically (not counting the visible ones)? Answer with a number in curly brackets. | 2 |
| L5 | remove_occluder_extend_pattern | If the occluder were removed and the pattern extended by one additional object outside the former occluded region, how many objects would be visible in total? | 11 |

**Metadata fields available:** canvas_size, dataset_version, difficulty_score, frame_conventions, id, image_path, object_color, object_positions, object_radius_px, occluded_object_count, occluder_bounds, occluder_style, pattern_params, pattern_type, seed, shape_type, total_object_count, visible_object_count

---

## optical_illusion_dataset_3000

**Item:** optical_illusion_1940.png

| Level | Type | Question | Ground truth |
|---|---|---|---|
| L1 | comparison_element_count | How many target line segments are being compared in this image? | 2 |
| L2 | contextual_apparent_size | Because of the converging lines, which element would a typical human viewer perceive as longer—element A or element B? Answer with the letter. | B |
| L3 | actual_size_comparison | Ignoring the surrounding context, measure the actual length of element A and element B. Are they equal, or is one actually longer? Answer 'equal', 'A', or 'B'. | equal |
| L4 | true_size_percent_difference | By approximately what percentage do the two elements' TRUE sizes differ (0% if equal)? Answer with a number in curly brackets, e.g. {12}. | 0 |
| L5 | remove_illusion_context | If the visual context (converging lines) were removed entirely and only the two bare elements remained, would your answer to 'which one is bigger' change from what the illusion suggests? Answer yes or no, and state which is actually bigger without the context. | yes; actually equal |

**Metadata fields available:** are_actually_equal, canvas_size, construction, dataset_version, difficulty_score, element_a_true_value, element_b_true_value, frame_conventions, id, illusion_appears_larger_element, illusion_direction, illusion_type, image_path, matches_illusion_direction, percent_difference, percent_difference_definition, percent_difference_fraction, seed

---

## orthographic_dataset_3000

**Item:** orthographic_1483.png

| Level | Type | Question | Ground truth |
|---|---|---|---|
| L1 | top_view_filled_count | How many unit cells are filled in the top view? | 7 |
| L2 | minimum_possible_cube_count | Based on the three views shown, what is the minimum possible number of cubes in a gravity-supported 3D structure? Answer with a number in curly brackets. | 9 |
| L3 | largest_filled_view | Which view (top, front, or side) shows the largest filled area (most filled cells)? | top |
| L4 | unique_determination | Do these three views uniquely determine the gravity-supported 3D structure, or could a different arrangement of cubes produce the exact same three views? Answer 'unique' or 'not unique'. | not unique |
| L5 | add_above_tallest_changed_views | If one cube were added directly on top of a tallest column, which orthographic view or views would change? | front and side |

**Metadata fields available:** add_cube_changed_views, candidates, canvas_size, correct_answer_choice, dataset_version, difficulty_score, front_view_cells, has_candidate_panel, id, image_path, is_uniquely_determined, is_uniquely_determined_same_count, minimum_possible_cube_count, seed, side_view_cells, tallest_column_xy, target_cubes, top_view_cells, total_cube_count, uniqueness_scope, view_filled_counts

---

## overlap_circles_dataset_3000

**Item:** overlap_circles_0283.png

| Level | Type | Question | Ground truth |
|---|---|---|---|
| L1 | total_circle_count | How many distinct circles are in this image? Answer with a number in curly brackets, e.g. {8}. | 9 |
| L2 | has_non_overlapping_circle | Is there any circle that does not overlap with any other circle? Answer yes or no. | yes |
| L3 | cluster_distribution | Are the circles clustered tightly in one area, or spread evenly across the whole image? Answer 'clustered' or 'spread'. | target_density |
| L4 | above_average_radius_count | How many circles have a radius larger than the average radius of all circles in this image? Answer with a number in curly brackets. | 4 |
| L5 | remove_largest_overlap_pairs | If the largest circle were removed, how many overlapping circle-pairs would remain? | 8 |

**Metadata fields available:** above_average_radius_count, canvas_size, circles, dataset_version, difficulty_score, generation_attempt, generation_mode, geometry_frame, id, image_path, isolated_after_largest_removal, largest_circle_index, largest_radius, line_width_px, max_stack_depth, max_stack_location, non_overlapping_circles, non_overlapping_count, overlap_density, overlapping_pairs_after_largest_removal, pairwise_overlaps, rejections_max_stack_depth, seed, smallest_circle_index, smallest_radius, target_overlap_density, three_plus_overlap_percent, total_circle_count, total_overlapping_pairs

---

## physical_stability_dataset_3000

**Item:** physical_stability_1508.png

| Level | Type | Question | Ground truth |
|---|---|---|---|
| L1 | block_count | How many blocks are in this stack? | 4 |
| L2 | relative_center_of_mass | Is block C's center of mass positioned to the left, right, or directly above the center of block B, which it rests on? | right |
| L3 | largest_support_offset | Which block has the largest absolute horizontal center offset from the block directly beneath it? Answer with the letter. | D |
| L4 | whole_stack_stability | Is this entire stack stable, or will it tip over? If it tips, state the lowest joint at which it first becomes unstable. | stable |
| L5 | remove_top_recheck_stability | If topmost block D were removed, would the remaining stack be stable or unstable? Answer accordingly and briefly state the center-of-mass reason. | stable; after removing block D, every cumulative center of mass remains within its supporting base |

**Metadata fields available:** after_top_removal, blocks, canvas_size, counterfactual_scenario, dataset_version, difficulty_score, id, image_path, is_stable, largest_offset_block, level2_upper_block, num_blocks, per_joint_stability, seed, tipping_joint

---

## polyhedron_dataset_3000

**Item:** polyhedron_1736.png

| Level | Type | Question | Ground truth |
|---|---|---|---|
| L1 | face_count | How many faces does this solid have in total, including hidden faces? | 14 |
| L2 | convexity | Is this solid convex or non-convex? Answer 'convex' or 'non-convex'. | convex |
| L3 | face_shapes | What shape are the faces of this solid — triangles, squares, pentagons, or a mix of shapes? | mixed |
| L4 | is_compound | Is this solid composed of overlapping shapes forming a compound structure? Answer yes or no. | no |
| L5 | remove_face_closed_surface | If one face were removed from this solid while all remaining faces stayed fixed, would the result still be a closed surface to which the closed-surface Euler formula directly applies? Answer yes or no. | no |

**Metadata fields available:** canvas_size, dataset_version, edge_count, edges, face_count, face_shape_types, faces, frame_conventions, id, image_path, is_convex, seed, solid_class, solid_name, vertex_count, vertices, viewing_angle, visible_face_count

---

## projectile_motion_dataset_1000

**Item:** projectile_motion_0987.png

| Level | Type | Question | Ground truth |
|---|---|---|---|
| L1 | read_launch_angle | What is the initial launch angle shown, in degrees? | 43 |
| L2 | height_above_20m | Will the projectile reach a higher maximum height than 20 meters? Answer yes or no. | no |
| L3 | horizontal_position_at_peak | At what horizontal distance from launch does the projectile reach its maximum height? Answer in meters, rounded to 1 decimal. | 26.9 |
| L4 | flight_time_and_range | What are the total time of flight in seconds and total horizontal range in meters? Round both to 1 decimal. | {'time_of_flight_s': 3.2, 'range_m': 53.8} |
| L5 | range_at_45_degrees | If the launch angle were changed to 45 degrees while keeping the same initial speed, would the horizontal range increase, decrease, or stay the same? | increase |

**Metadata fields available:** canvas_height, canvas_width, dataset_version, difficulty_score, gravity_m_s2, has_obstacle, horizontal_position_at_peak_m, id, image_path, initial_speed_m_s, initial_velocity_x_m_s, initial_velocity_y_m_s, launch_angle_degrees, max_height_m, obstacle, range_at_45_degrees_m, range_change_at_45_degrees, range_m, seed, time_of_flight_s

---

## rotation_matching_dataset_3000

**Item:** rotation_match_1649.png

| Level | Type | Question | Ground truth |
|---|---|---|---|
| L1 | reference_vertex_count | How many vertices (corners) does the reference figure have? | 7 |
| L2 | target_angle_rotation_choice | Which candidate shows the reference figure rigidly rotated 180 degrees clockwise? Answer with the letter. | A |
| L3 | candidate_rotation_angle | By how many degrees clockwise is candidate D rotated relative to the reference? Choose 45, 90, 135, 180, 225, 270, or 315 degrees. | 90 |
| L4 | reflection_choice | Exactly one candidate is a reflection (mirror image) rather than a rotation. Which one? Answer with the letter. | C |
| L5 | additional_rotation_angle | If the reference were first rotated by the target angle of 180 degrees clockwise and then rotated an additional 90 degrees clockwise, what would the total normalized rotation be? Answer from 45, 90, 135, 180, 225, 270, 315, or 360 degrees. | 270 |

**Metadata fields available:** candidates, canvas_size, coordinate_frame, correct_answer_choice, correct_rotation_angle, dataset_version, difficulty_score, id, image_path, minimum_turn_guard_degrees, minimum_turning_angle_degrees, num_reference_vertices, reference_generation_rejections, reference_vertices, reflection_answer_choice, seed

---

## route_dataset_3000

**Item:** route_puzzle_2676.png

| Level | Type | Question | Ground truth |
|---|---|---|---|
| L1 | num_labeled_endpoints | How many labeled endpoints (letters) are shown in this image? | 5 |
| L2 | count_routes_between_pair | Count the one-colored routes that go from B to D. Answer with a number in curly brackets e.g. {1} | 1 |
| L3 | letter_degree | How many routes does letter B have in total (i.e. touching B)? | 4 |
| L4 | single_route_pairs | List all letter-pairs that have exactly one connecting route between them. | ['AC', 'AE', 'BC', 'BD', 'CD'] |
| L5 | add_route_new_max_degree | If one new route were added directly between C and E, what would the maximum endpoint degree become? | 4 |

**Metadata fields available:** canvas_size, colors_used, crossing_count, dataset_version, difficulty_score, endpoint_letters, frame_conventions, id, image_path, line_width_px, num_endpoints, num_routes, routes, seed

---

## rpm_dataset_3000

**Item:** rpm_2816.png

| Level | Type | Question | Ground truth |
|---|---|---|---|
| L1 | top_left_shape_count | How many shapes appear in the panel at row 1, column 1 (top-left)? | 3 |
| L2 | correct_choice | Which of the 8 numbered choices correctly completes the pattern in the missing panel? Answer with the number. | 5 |
| L3 | distractor_classification | Choice 6 is wrong. Does it have the correct shape but wrong color, the correct color but wrong shape, or is it wrong in some other way? | wrong in some other way |
| L4 | choices_matching_correct_shape | How many of the 8 answer choices share the same shape type as the correct answer, even though most of them are wrong for other reasons? Answer with a number. | 6 |
| L5 | add_same_shape_distractor | If a ninth, incorrect choice with the same shape type as the correct answer but a wrong color were added, how many choices would then share the correct shape type? | 7 |

**Metadata fields available:** active_rules, answer_choices, background_constants, canvas_size, correct_answer_index, dataset_version, difficulty_score, difficulty_tier, distractor_violations, frame_conventions, grid_panels, id, image_path, num_active_rules, orientation, seed

---

## shadow_inference_dataset_3000

**Item:** shadow_inference_0577.png

| Level | Type | Question | Ground truth |
|---|---|---|---|
| L1 | object_count | How many objects are casting a shadow in this image? | 2 |
| L2 | light_direction_bucket | From which general direction is the light coming — left, right, front, or back? Answer with one word. | right |
| L3 | light_height_class | Is the light source high in the sky (steep angle) or low near the horizon (shallow angle)? Answer 'high' or 'low'. | high |
| L4 | opposite_azimuth_length_change | If the light source moved to the exact opposite direction (180 degrees azimuth rotation), would the shadows lengthen, shorten, or stay the same length? | same |
| L5 | raise_light_elevation | If the light elevation increased by 20 degrees while remaining below 90 degrees and all object geometry stayed fixed, would each shadow become longer, shorter, or unchanged? | shorter |

**Metadata fields available:** azimuth_convention, azimuth_exclusion_degrees, canvas_size, coordinate_frame, dataset_version, difficulty_score, ground_y, has_inconsistent_shadow, id, image_path, inconsistent_object_index, light_azimuth_degrees, light_elevation_degrees, num_objects, objects, seed

---

## surface_topology_dataset_3000

**Item:** surface_topology_1500.png

| Level | Type | Question | Ground truth |
|---|---|---|---|
| L1 | genus_count | How many holes or handles does this surface have? Answer with a number in curly brackets, e.g. {1}. | 1 |
| L2 | orientability | Is this surface orientable (has a consistent 'inside' and 'outside') or non-orientable (a single-sided surface, like a Möbius strip)? Answer 'orientable' or 'non-orientable'. | orientable |
| L3 | euler_characteristic | What is the Euler characteristic of this surface? Answer with a number in curly brackets (can be negative), e.g. {-2}. | 0 |
| L4 | combined_euler_orientability | Combine the depicted surface's genus/handle structure and orientability: report its Euler characteristic, followed by whether it is orientable or non-orientable. Answer as 'Euler characteristic; orientability'. | 0; orientable |
| L5 | remove_disk_euler_characteristic | If a small open disk were removed from this surface, creating exactly one additional boundary component without changing its genus or orientability, what would its new Euler characteristic be? Answer with a number in curly brackets, e.g. {-1}. | -1 |

**Metadata fields available:** boundary_count, canvas_size, dataset_version, difficulty_score, edge_count, euler_characteristic, face_count, frame_conventions, genus, genus_kind, id, image_path, is_orientable, mesh_edges, mesh_faces, mesh_vertices, render_color, seed, surface_type, surface_variant, vertex_count, viewing_angle

---

## symmetry_pattern_dataset_3000

**Item:** symmetry_pattern_1494.png

| Level | Type | Question | Ground truth |
|---|---|---|---|
| L1 | shape_count | How many shapes are in this pattern? | 8 |
| L2 | symmetry_status | Is this pattern symmetric, or is there an element that breaks the symmetry? Answer 'symmetric' or 'broken'. | symmetric |
| L3 | symmetry_family | What type of symmetry does this pattern have — rotational or mirror/reflective? Answer 'rotational' or 'mirror'. | rotational |
| L4 | symmetric_partner_count | How many shapes are positioned at the exact symmetric location of another shape? Answer with a number. | 8 |
| L5 | counterfactual_symmetry_repair_break | If exactly one shape shifted while its symmetric partner stayed fixed, would the global symmetry become broken? | yes |

**Metadata fields available:** break_type, broken_location, broken_shape_index, broken_shape_position, canvas_size, dataset_version, difficulty_score, frame_conventions, id, image_path, is_broken, num_shapes, seed, shapes, symmetric_partner_count, symmetry_type

---
