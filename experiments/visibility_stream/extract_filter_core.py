"""Extract unchanged filter code; output contains no game exports or hooks."""
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parent
source = root / 'baseline/t60_visibility_indexed.c'
manifest = json.loads((root / 'source-provenance.json').read_text('utf8'))
assert hashlib.sha256(source.read_bytes()).hexdigest() == manifest['source_sha256'][source.name]
text = source.read_text('utf8')
spans = [
    ('typedef void (*BoolSet)', 'typedef int (*InstallHook)'),
    ('typedef void (*QueueUpdate)', 'static void* implementation('),
    ('static void cache_filter(', 'static int setup('),
]
chunks = []
for start, end in spans:
    begin = text.index(start)
    finish = text.index(end, begin)
    chunks.append(text[begin:finish])
(root / 'baseline_filter_core.h').write_text(
    '/* Generated verbatim slices; no engine access, setup, collection or exports. */\n'
    + '#include <stdint.h>\n#include <string.h>\n' + '\n'.join(chunks), 'utf8')
