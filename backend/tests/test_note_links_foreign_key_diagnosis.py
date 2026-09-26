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


class NoteLinksForeignKeyDiagnosisTests(unittest.TestCase):
    def test_exact_contract_is_noop(self):
        diagnosis = _load(SCRIPT, "note_links_fk_diagnosis_exact")
        self.assertIsNone(
            diagnosis.diagnose_note_links_foreign_keys(
                set(diagnosis.EXPECTED_NOTE_LINKS_FKS)
            )
        )

    def test_missing_and_semantics_reasons_are_stable(self):
        diagnosis = _load(SCRIPT, "note_links_fk_diagnosis_reasons")
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

        changed_semantics = set(diagnosis.EXPECTED_NOTE_LINKS_FKS)
        changed_semantics.remove(source)
        changed_semantics.add(
            (
                source[0],
                source[1],
                source[2],
                source[3],
                "c",
                source[5],
                source[6],
                source[7],
            )
        )
        self.assertEqual(
            "semantics_mismatch",
            diagnosis.diagnose_note_links_foreign_keys(changed_semantics),
        )

    def test_release_maps_diagnosis_to_free_exit_codes(self):
        diagnosis = _load(SCRIPT, "note_links_fk_diagnosis_exit_source")
        release = _load(RELEASE, "note_links_fk_diagnosis_release")
        self.assertEqual(
            {
                "both_missing": 1,
                "source_missing": 2,
                "target_missing": 3,
                "semantics_mismatch": 4,
                "other": 5,
            },
            release.NOTE_LINKS_FK_DIAGNOSTIC_EXIT_CODES,
        )
        for reason, code in release.NOTE_LINKS_FK_DIAGNOSTIC_EXIT_CODES.items():
            with self.subTest(reason=reason):
                error = diagnosis.NoteLinksForeignKeyDiagnosisError(reason)
                # Loader's class identities differ, so create through the release module.
                release_error = (
                    release.note_links_fk_diagnosis.NoteLinksForeignKeyDiagnosisError(
                        reason
                    )
                )
                self.assertEqual(code, release.classify_failure(release_error))
                self.assertTrue(1 <= code <= 5)


if __name__ == "__main__":
    unittest.main()
