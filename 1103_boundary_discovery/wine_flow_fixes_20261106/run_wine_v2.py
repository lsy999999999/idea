"""New wine runs with preserved disciplinary identities and a copied memory checkpoint."""
import argparse
from pathlib import Path
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent/'src'))
import learning_lab as lab
from learning_memory import Memory


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run-id', default='wine_inquiry_v2_001')
    parser.add_argument('--executor', choices=['cli', 'queue'], default='queue')
    args = parser.parse_args()
    if not args.run_id.replace('_', '').isalnum():
        parser.error('Use a safe new run ID')
    memory = ROOT/'researchers'
    if not (ROOT/'ORIGINAL_MEMORY_SNAPSHOT.json').is_file():
        raise ValueError('Verified original wine memory checkpoint is missing')
    settings = SimpleNamespace(model='gpt-6-luna', effort='low', timeout=300,
                               check_timeout=600, executor=args.executor)
    lab.run_case('wine', ROOT.parent/'runs'/args.run_id, settings, Memory(memory))


if __name__ == '__main__':
    main()
