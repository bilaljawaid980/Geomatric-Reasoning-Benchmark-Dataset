"""Regression tests for Test 4 answer equivalence."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

if str(Path(__file__).parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent))

from crossexam_common import answer_is_accepted


def accepted(answer: str, *candidates: str) -> bool:
    return answer_is_accepted(answer, json.dumps(list(candidates)))


class AnswerEquivalenceTests(unittest.TestCase):
    def test_exact_multifield_answer(self) -> None:
        self.assertTrue(accepted(
            "candidate=B; rejection_reason=gap or overlap",
            "candidate=B; rejection_reason=gap or overlap",
        ))

    def test_time_leading_zero_is_formatting(self) -> None:
        self.assertTrue(accepted("time=7:18", "time=07:18"))

    def test_different_minute_is_wrong(self) -> None:
        self.assertFalse(accepted("time=07:19", "time=07:18"))

    def test_landmark_pair_separators_are_equivalent(self) -> None:
        self.assertTrue(accepted(
            "closest_pair=A, C; bearing_degrees_nearest_10=180",
            "closest_pair=A-C; bearing_degrees_nearest_10=180",
        ))

    def test_wrong_landmark_pair_is_wrong(self) -> None:
        self.assertFalse(accepted("closest_pair=A-B", "closest_pair=A-C"))

    def test_ordered_list_plain_text_matches_json(self) -> None:
        self.assertTrue(accepted(
            "depth_ordering=orange, purple, blue",
            'depth_ordering=["orange","purple","blue"]',
        ))

    def test_ordered_list_wrong_order_is_wrong(self) -> None:
        self.assertFalse(accepted(
            "depth_ordering=purple, orange, blue",
            'depth_ordering=["orange","purple","blue"]',
        ))

    def test_set_like_list_may_be_reordered(self) -> None:
        self.assertTrue(accepted(
            "attributes_changed_together=count, shape",
            'attributes_changed_together=["shape","count"]',
        ))

    def test_coordinates_accept_equivalent_notation(self) -> None:
        self.assertTrue(accepted(
            "point_coordinates=A(-2,3), B(-5,-1), C(8,-7)",
            'point_coordinates={"A":[-2,3],"B":[-5,-1],"C":[8,-7]}',
        ))

    def test_coordinate_error_is_wrong(self) -> None:
        self.assertFalse(accepted(
            "point_coordinates=A(-2,3), B(-5,-1), C(7,-7)",
            'point_coordinates={"A":[-2,3],"B":[-5,-1],"C":[8,-7]}',
        ))

    def test_singular_face_name_is_equivalent(self) -> None:
        self.assertTrue(accepted("face_shapes=pentagon", "face_shapes=pentagons"))

    def test_numeric_values_remain_exact(self) -> None:
        self.assertTrue(accepted("angle_degrees_nearest_10=210 degrees", "angle_degrees_nearest_10=210"))
        self.assertFalse(accepted("angle_degrees_nearest_10=220", "angle_degrees_nearest_10=210"))

    def test_opposites_remain_distinct(self) -> None:
        self.assertFalse(accepted("orientability=orientable", "orientability=non-orientable"))
        self.assertFalse(accepted("uniqueness=unique", "uniqueness=not unique"))

    def test_established_wording_variants(self) -> None:
        self.assertTrue(accepted("uniqueness=non-unique", "uniqueness=not unique"))
        self.assertTrue(accepted("pattern_status=symmetric", "pattern_status=fully symmetric"))
        self.assertTrue(accepted("pattern_status=asymmetric", "pattern_status=broken"))
        self.assertTrue(accepted("pattern_type=circular", "pattern_type=circle"))
        self.assertTrue(accepted("convexity=concave", "convexity=non-convex"))
        self.assertTrue(accepted("relation_to_12=greater than", "relation_to_12=greater"))

    def test_attribute_name_variants(self) -> None:
        self.assertTrue(accepted(
            "attributes_changed_together=color, orientation",
            'attributes_changed_together=["color","rotation"]',
        ))

    def test_claim_field_order_does_not_matter(self) -> None:
        self.assertTrue(accepted(
            "bearing_degrees_nearest_10=180; closest_pair=A-C",
            "closest_pair=A-C; bearing_degrees_nearest_10=180",
        ))

    def test_connectivity_label_lists_are_unordered_multisets(self) -> None:
        self.assertTrue(accepted(
            'connectivity={"unreached_labels":["D","C"],"far_end_labels":["B","A","A"],"connected_to_all_other_labels":"no"}',
            'connectivity={"connected_to_all_other_labels":"no","far_end_labels":["A","A","B"],"unreached_labels":["C","D"]}',
        ))

    def test_ties_inside_magnitude_ranking_are_unordered(self) -> None:
        self.assertTrue(accepted(
            'drawn_magnitude_ranking=[["N","A"],["W","F"]]',
            'drawn_magnitude_ranking=[["A","N"],["F","W"]]',
        ))
        self.assertFalse(accepted(
            'drawn_magnitude_ranking=[["F","W"],["A","N"]]',
            'drawn_magnitude_ranking=[["A","N"],["F","W"]]',
        ))

    def test_natural_magnitude_ranking_notation(self) -> None:
        self.assertTrue(accepted(
            "drawn_magnitude_ranking=W2 > T1 = T2 > W1",
            'drawn_magnitude_ranking=[["W2"],["T1","T2"],["W1"]]',
        ))

    def test_plus_and_arrow_list_notation(self) -> None:
        self.assertTrue(accepted(
            "attributes_changed_together=count+orientation",
            'attributes_changed_together=["rotation","count"]',
        ))
        self.assertTrue(accepted(
            "depth_ordering=orange > blue > teal",
            'depth_ordering=["orange","blue","teal"]',
        ))

    def test_grid_dimension_prefix_is_descriptive(self) -> None:
        self.assertTrue(accepted("pattern_type=3x3 grid", "pattern_type=grid"))

    def test_elaborated_rejection_reason(self) -> None:
        self.assertTrue(accepted(
            "rejection_reason=wrong cube count (11 vs 8)",
            "rejection_reason=wrong cube count",
        ))

    def test_fold_order_wording(self) -> None:
        self.assertTrue(accepted("symmetry_type=6-fold rotational", "symmetry_type=rotational_6"))

    def test_boolean_wording_is_semantically_equal(self) -> None:
        self.assertTrue(accepted("constructible=false", "constructible=no"))
        self.assertTrue(accepted("peak_above_13_m=true", "peak_above_13_m=yes"))

    def test_spatial_direction_wording(self) -> None:
        self.assertTrue(accepted("light_direction=left", "light_direction=west"))
        self.assertTrue(accepted("light_direction=right", "light_direction=east"))
        self.assertTrue(accepted("light_direction=from the upper right", "light_direction=east"))
        self.assertTrue(accepted("light_height=low near the horizon", "light_height=low"))

    def test_descriptive_scalar_aliases(self) -> None:
        self.assertTrue(accepted("larger_angle=2", "larger_angle=Angle 2"))
        self.assertTrue(accepted("shrink_pattern=same", "shrink_pattern=constant"))
        self.assertTrue(accepted("uniqueness=false", "uniqueness=not unique"))
        self.assertTrue(accepted("pattern_status=one_displaced", "pattern_status=broken"))

    def test_pair_with_conjunction(self) -> None:
        self.assertTrue(accepted("farthest_pair=A and B", "farthest_pair=A-B"))

    def test_semicolon_separated_coordinates(self) -> None:
        self.assertTrue(accepted(
            "point_coordinates=A(-2,3); B(-5,-1); C(8,-7)",
            'point_coordinates={"A":[-2,3],"B":[-5,-1],"C":[8,-7]}',
        ))

    def test_attribute_annotations(self) -> None:
        self.assertTrue(accepted(
            "attributes_changed_together=count (rows), color (columns)",
            'attributes_changed_together=["color","count"]',
        ))

    def test_empty_direction_list_wording(self) -> None:
        self.assertTrue(accepted("hole_directions=none", "hole_directions=[]"))

    def test_stability_natural_wording(self) -> None:
        self.assertTrue(accepted(
            "stability_conclusion=stands",
            'stability_conclusion={"lowest_failing_joint":"none","status":"stable"}',
        ))
        self.assertTrue(accepted(
            "stability_conclusion=tips at C-D",
            'stability_conclusion={"lowest_failing_joint":"D","status":"tips"}',
        ))
        self.assertTrue(accepted(
            "stability_conclusion=tips at C-on-B",
            'stability_conclusion={"lowest_failing_joint":"C","status":"tips"}',
        ))

    def test_additional_shape_and_symmetry_wording(self) -> None:
        self.assertTrue(accepted("pattern_type=rectangular grid", "pattern_type=grid"))
        self.assertTrue(accepted("pattern_type=triangular grid", "pattern_type=triangle"))
        self.assertTrue(accepted("symmetry_type=180_rotational", "symmetry_type=rotational_2"))
        self.assertTrue(accepted(
            "symmetry_type=reflectional symmetry about the vertical axis",
            "symmetry_type=mirror_vertical",
        ))
        self.assertTrue(accepted(
            "symmetry_type=rotational symmetry of order 4",
            "symmetry_type=rotational_4",
        ))
        self.assertTrue(accepted(
            "symmetry_type=180-degree rotational symmetry",
            "symmetry_type=rotational_2",
        ))
        self.assertTrue(accepted("face_shapes=triangles and squares", "face_shapes=mixed"))

    def test_additional_descriptive_variants(self) -> None:
        self.assertTrue(accepted("pattern_status=one element displaced", "pattern_status=broken"))
        self.assertTrue(accepted("shrink_pattern=roughly_same_factor", "shrink_pattern=constant"))
        self.assertTrue(accepted("true_size_relation=B larger", "true_size_relation=B"))
        self.assertTrue(accepted("true_size_relation=A_equals_B", "true_size_relation=equal"))
        self.assertTrue(accepted("fastest_gear=Gear D", "fastest_gear=D"))
        self.assertTrue(accepted("relation_to_12=less than 12", "relation_to_12=less"))
        self.assertTrue(accepted("pattern_type=circular pattern", "pattern_type=circle"))

    def test_colour_and_attribute_wording_variants(self) -> None:
        self.assertTrue(accepted(
            "depth_ordering=pink, teal, blue",
            'depth_ordering=["magenta","teal","blue"]',
        ))
        self.assertTrue(accepted(
            "attributes_changed_together=color and star orientation",
            'attributes_changed_together=["color","rotation"]',
        ))
        self.assertTrue(accepted(
            "attributes_changed_together=number and size of triangles",
            'attributes_changed_together=["size","count"]',
        ))

    def test_phase1_audit_wording_variants(self) -> None:
        self.assertTrue(accepted("range_half=upper half", "range_half=upper"))
        self.assertTrue(accepted("relation_to_12=less than 12 units", "relation_to_12=less"))
        self.assertTrue(accepted("direction_target=Gear B", "direction_target=B"))
        self.assertTrue(accepted(
            "target_direction_relation=same as driver",
            "target_direction_relation=same",
        ))
        self.assertTrue(accepted(
            "shrink_pattern=roughly the same factor",
            "shrink_pattern=constant",
        ))
        self.assertTrue(accepted("pattern_status=perfectly symmetric", "pattern_status=fully symmetric"))
        self.assertTrue(accepted("orientability=nonorientable", "orientability=non-orientable"))
        self.assertTrue(accepted("light_direction=from left", "light_direction=west"))


if __name__ == "__main__":
    unittest.main()
