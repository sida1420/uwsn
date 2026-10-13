"""Small launcher recovery checks; no simulation is launched."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from optimizer import PACKAGE
from optimizer.controller import initialize
from optimizer.storage import atomic, lock, read
from optimizer.windows.recover import recover


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=PACKAGE / '.test-output')
        self.study = Path(self.temp.name) / 'study'
        initialize(PACKAGE / 'config.example.yaml', self.study)

    def tearDown(self):
        self.temp.cleanup()

    def test_repair_preserves_checkpoint_and_budget(self):
        state = read(self.study / 'state.json')
        state.update(spent_wall=123., jobs={'0': dict(status='running'), '1': dict(status='complete')})
        atomic(self.study / 'state.json', state)
        checkpoint = self.study / 'saved-checkpoint.bin'
        checkpoint.write_bytes(b'unchanged checkpoint')
        recover(self.study)
        repaired = read(self.study / 'state.json')
        self.assertEqual(repaired['jobs']['0']['status'], 'paused')
        self.assertEqual(repaired['jobs']['1']['status'], 'complete')
        self.assertEqual(repaired['spent_wall'], 123.)
        self.assertEqual(checkpoint.read_bytes(), b'unchanged checkpoint')

    def test_live_controller_is_not_modified(self):
        before = (self.study / 'state.json').read_bytes()
        with lock(self.study / 'controller.lock'):
            result = subprocess.run([sys.executable, '-B', str(PACKAGE / 'windows/recover.py'),
                                     '--study', str(self.study)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 10, result.stderr)
        self.assertEqual((self.study / 'state.json').read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
