import importlib.util
from pathlib import Path
import sys
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / "backend"
SCRIPT = BACKEND_ROOT / "scripts" / "diagnose_note_links_foreign_keys.py"
RELEASE = BACKEND_ROOT / "scripts" / "apply_cloud_domain_parity_release.py"


def _load(path: Path, name: str):
    if str(BACKEND_ROOT) not in sys.path:
        sys.path.insert(0, str(BACKEND_ROOT))
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _replace(contract, index, value):
    parts = list(contract)
    parts[index] = value
    return tuple(parts)


class NoteLinksForeignKeyDiagnosisTests(unittest.TestCase):
    def test_exact_contract_is_noop(self):
        diagnosis = _load(SCRIPT, "note_links_fk_diagnosis_exact")
        self.assertIsNone(
            diagnosis.diagnose_note_links_foreign_keys(
                set(diagnosis.EXPECTED_NOTE_LINKS_FKS)
            )
        )

    def test_missing_reasons_are_stable(self):
        diagnosis = _load(SCRIPT, "note_links_fk_diagnosis_missing")
        expected_by_reference = {
            (contract[0], contract[1], contract[2]): contract
            for contract in diagnosis.EXPECTED_NOTE_LINKS_FKS
        }
        source = expected_by_reference[diagnosis.SOURCE_REFERENCE]
        target = expected_by_reference[diagnosis.TARGET_REFERENCE]

        self.assertEqual(
            "both_missing",
            diagnosis.diagnose_note_links_foreign_keys(set()),
        )
        self.assertEqual(
            "source_missing",
            diagnosis.diagnose_note_links_foreign_keys({target}),
        )
        self.assertEqual(
            "target_missing",
            diagnosis.diagnose_note_links_foreign_keys({source}),
        )

    def test_driver_byte_string_action_representation_is_distinct(self):
        diagnosis = _load(SCRIPT, "note_links_fk_diagnosis_driver")
        actual = {
            _replace(_replace(contract, 3, "b'a'"), 4, "b'a'")
            for contract in diagnosis.EXPECTED_NOTE_LINKS_FKS
        }
        self.assertEqual(
            "driver_action_representation",
            diagnosis.diagnose_note_links_foreign_keys(actual),
        )

    def test_single_semantic_field_and_scope_are_identified(self):
        diagnosis = _load(SCRIPT, "note_links_fk_diagnosis_fields")
        expected_by_reference = {
            (contract[0], contract[1], contract[2]): contract
            for contract in diagnosis.EXPECTED_NOTE_LINKS_FKS
        }
        source = expected_by_reference[diagnosis.SOURCE_REFERENCE]
        target = expected_by_reference[diagnosis.TARGET_REFERENCE]

        cases = (
            (3, "r", "source_update_action", {source}),
            (4, "c", "target_delete_action", {target}),
            (5, True, "both_deferrable", {source, target}),
            (6, True, "source_initially_deferred", {source}),
            (7, False, "both_validation", {source, target}),
        )
        for index, value, expected_reason, changed in cases:
            with self.subTest(reason=expected_reason):
                actual = set(diagnosis.EXPECTED_NOTE_LINKS_FKS)
                for contract in changed:
                    actual.remove(contract)
                    actual.add(_replace(contract, index, value))
                self.assertEqual(
                    expected_reason,
                    diagnosis.diagnose_note_links_foreign_keys(actual),
                )

    def test_multiple_semantic_fields_fall_back_to_complex(self):
        diagnosis = _load(SCRIPT, "note_links_fk_diagnosis_complex")
        expected_by_reference = {
            (contract[0], contract[1], contract[2]): contract
            for contract in diagnosis.EXPECTED_NOTE_LINKS_FKS
        }
        source = expected_by_reference[diagnosis.SOURCE_REFERENCE]
        target = expected_by_reference[diagnosis.TARGET_REFERENCE]
        actual = set(diagnosis.EXPECTED_NOTE_LINKS_FKS)
        actual.remove(source)
        actual.add(_replace(source, 4, "c"))
        actual.remove(target)
        actual.add(_replace(target, 7, False))
        self.assertEqual(
            "semantics_complex",
            diagnosis.diagnose_note_links_foreign_keys(actual),
        )

    def test_release_maps_detailed_diagnosis_to_free_low_exit_codes(self):
        release = _load(RELEASE, "note_links_fk_diagnosis_release")
        expected = {
            "both_missing": 1,
            "source_missing": 2,
            "target_missing": 3,
            "driver_action_representation": 4,
            "source_update_action": 5,
            "target_update_action": 6,
            "both_update_action": 7,
            "source_delete_action": 8,
            "target_delete_action": 9,
            "both_delete_action": 10,
            "source_deferrable": 11,
            "target_deferrable": 12,
            "both_deferrable": 13,
            "source_initially_deferred": 14,
            "target_initially_deferred": 15,
            "both_initially_deferred": 16,
            "source_validation": 17,
            "target_validation": 18,
            "both_validation": 19,
        }
        self.assertEqual(expected, release.NOTE_LINKS_FK_DIAGNOSTIC_EXIT_CODES)
        self.assertEqual(set(range(1, 20)), set(expected.values()))
        for reason, code in expected.items():
            with self.subTest(reason=reason):
                error = release.note_links_fk_diagnosis.NoteLinksForeignKeyDiagnosisError(
                    reason
                )
                self.assertEqual(code, release.classify_failure(error))

        complex_error = release.note_links_fk_diagnosis.NoteLinksForeignKeyDiagnosisError(
            "semantics_complex"
        )
        self.assertEqual(252, release.classify_failure(complex_error))


if __name__ == "__main__":
    unittest.main()
