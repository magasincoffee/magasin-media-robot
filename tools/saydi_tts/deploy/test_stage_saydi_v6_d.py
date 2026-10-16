"""Source-only negative tests; cannot qualify installation/field START on H4."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parent
SCRIPT = (ROOT / 'Stage-SaydiV6-D.ps1').read_text(encoding='utf-8')
WORKFLOW = (ROOT.parents[2] / '.github/workflows/saydi-v6-d-drive-stage.yml').read_text(encoding='utf-8')

class SourceStagingContract(unittest.TestCase):
    def test_h4_and_owner_repo_bound(self):
        for token in ('DESKTOP-H4A16IL', 'magasincoffee/magasin-media-robot',
                      'NOT_CANONICAL_MAIN', 'MAIN_SHA_MISMATCH', 'NOT_EXPLICIT_DISPATCH'):
            self.assertIn(token, SCRIPT)

    def test_d_only_isolated_stage(self):
        for token in ("'D:\\SAYDI_V6_STAGING'", 'STAGE_EXISTS_NO_OVERWRITE',
                      'STAGE_PARENT_MISSING_USE_APPROVED_D_ROOT', 'SOURCE_REPARSE_ENTRY_DENIED'):
            self.assertIn(token, SCRIPT)
        self.assertNotIn('Remove-Item', SCRIPT)
        self.assertNotIn('Start-Process', SCRIPT)

    def test_disk_guards(self):
        self.assertIn('$minCFreeGiB = 2.0', SCRIPT)
        self.assertIn('$minDFreeGiB = 10.0', SCRIPT)
        self.assertIn('STAGE_DENIED_RESOURCE', SCRIPT)
        self.assertIn('Get-PSDrive -Name C', SCRIPT)
        self.assertIn('Get-PSDrive -Name D', SCRIPT)

    def test_only_core_copied(self):
        self.assertIn("'02_SAYDI_CORE'", SCRIPT)
        self.assertIn('Copy-Item -LiteralPath $core', SCRIPT)
        self.assertNotIn('C:\\SAYDI\\output', SCRIPT)
        self.assertNotIn('C:\\SAYDI\\worker', SCRIPT)

    def test_no_worker_or_install(self):
        for signal in ("saydi_started = $false", "model_loaded = $false",
                       "production_modified = $false", 'SOURCE_STAGED_ONLY_NOT_INSTALLED'):
            self.assertIn(signal, SCRIPT)
        for forbidden in ('pip install', 'uv sync', 'winget install', 'Stop-Process', 'Start-Service'):
            self.assertNotIn(forbidden, SCRIPT)

    def test_manual_only(self):
        self.assertIn('workflow_dispatch:', WORKFLOW)
        for forbidden in ('  schedule:', '  issues:', '  pull_request:', '  push:'):
            self.assertNotIn(forbidden, WORKFLOW)
        self.assertIn('persist-credentials: false', WORKFLOW)
        self.assertIn('shell: cmd', WORKFLOW)
        self.assertIn('Inspect, Stage', WORKFLOW)

if __name__ == '__main__':
    unittest.main()