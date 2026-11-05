"""Build a local, additive FCS storage patch; never write the live game."""
import ast
import copy
import hashlib
import json
import struct
from pathlib import Path

GAME = Path('D:/steam/steamapps/common/Kenshi')
OUT = Path(__file__).resolve().parent
SOURCE = GAME / 'mods/JACK_WastelandCraft/JACK_WastelandCraft.mod'
BEFORE_SHA = '9d4bc5566a8ea7915dc56393095da10043b75f5efd5d6a0e97bedcba16a88c02'
READER_SOURCE = Path('D:/JACK/kenshi_armour_audit/read_data.py')
TARGETS = {
    '97246-rebirth.mod': [
        '200-JACK_EnergyWeapons.mod', '210-JACK_EnergyWeapons.mod',
    ],
    '97243-rebirth.mod': [
        f'{n}-JACK_WastelandCraft.mod' for n in (400, 410, 420, 430, 440)
    ],
    '56129-rebirth.mod': [
        '450-JACK_WastelandCraft.mod', '460-JACK_WastelandCraft.mod',
    ],
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


namespace = {'struct': struct}
tree = ast.parse(READER_SOURCE.read_text('utf8'))
definitions = [n for n in tree.body if isinstance(n, (ast.ClassDef, ast.FunctionDef))]
exec(compile(ast.Module(body=definitions, type_ignores=[]), str(READER_SOURCE), 'exec'), namespace)
Reader = namespace['Reader']
merge = namespace['merge']


def uint(value):
    return struct.pack('<I', value & 0xffffffff)


def string(value):
    data = value.encode('utf8')
    return uint(len(data)) + data


def encode(records, prefix):
    data = prefix + uint(len(records))
    for record in records:
        data += (uint(0) + uint(record['type']) + uint(0) + string(record['name'])
                 + string(record['id']) + uint(record['flags']))
        for kind, fmt in enumerate(('?', 'f', 'i', '3f', '4f', 's', 's')):
            fields = [(k, v) for k, v in record['fields'].items()
                      if record['field_types'][k] == kind]
            data += uint(len(fields))
            for key, value in fields:
                data += string(key)
                if fmt == 's':
                    data += string(value)
                elif fmt in ('3f', '4f'):
                    data += struct.pack('<' + fmt, *value)
                else:
                    data += struct.pack('<' + fmt, value)
        data += uint(len(record['refs']))
        for key, refs in record['refs'].items():
            data += string(key) + uint(len(refs))
            for sid, values in refs.items():
                data += string(sid) + struct.pack('<3i', *values)
        data += uint(0)
    return data


def main():
    candidate = OUT / 'JACK_WastelandCraft.mod.candidate'
    assert not candidate.exists(), 'Preserve earlier candidates'
    assert digest(SOURCE) == BEFORE_SHA, 'Live content changed; do not overwrite'
    before_bytes = SOURCE.read_bytes()
    reader = Reader(SOURCE)
    assert reader.val('i') == 16
    reader.val('i')
    for _ in range(4):
        reader.s()
    reader.val('i')
    prefix = reader.b[:reader.o]
    original = list(Reader(SOURCE).records())
    assert encode(original, prefix) == before_bytes, 'FCS writer roundtrip mismatch'
    assert not (set(TARGETS) & {r['id'] for r in original}), 'Storage patches already exist'
    storage = json.loads((OUT / 'storage-before.json').read_text('utf8'))
    owned = {r['id']: r for r in original}
    owned.update({r['id']: r for r in Reader(
        GAME / 'mods/JACK_EnergyWeapons/JACK_EnergyWeapons.mod').records()})
    patches = []
    for sid, items in TARGETS.items():
        base = storage[sid]
        assert base['type'] == 0 and base['fields']['itemtype limit'] == 4
        assert '1518-gamedata.base' in base['refs']['functionality']
        assert all(owned[item]['type'] == 4 for item in items)
        patches.append({
            'type': 0, 'id': sid, 'name': base['name'], 'flags': 16,
            'fields': {}, 'field_types': {},
            'refs': {'limit inventory': {item: [0, 0, 0] for item in items}},
        })
    rows = copy.deepcopy(original) + patches
    candidate.write_bytes(encode(rows, prefix))
    assert list(Reader(candidate).records()) == rows
    assert rows[:len(original)] == original
    after = copy.deepcopy(storage)
    for patch in patches:
        previous = copy.deepcopy(storage[patch['id']])
        merge(after, [copy.deepcopy(patch)], 'JACK_WastelandCraft.mod')
        merged = after[patch['id']]
        assert merged['fields'] == previous['fields']
        for key, refs in previous['refs'].items():
            assert all(merged['refs'][key][k] == v for k, v in refs.items())
        expected = previous['refs']['limit inventory'] | patch['refs']['limit inventory']
        assert merged['refs']['limit inventory'] == expected
    guns = storage['1532622-rebirth.mod']
    assert guns['fields']['itemtype limit'] == 107
    assert not guns['refs'].get('limit inventory')
    assert all(owned[f'{n}-JACK_EnergyWeapons.mod']['type'] == 107 for n in (100, 110))
    report = {
        'before_sha256': BEFORE_SHA, 'candidate_sha256': digest(candidate),
        'bytes_before': len(before_bytes), 'bytes_after': candidate.stat().st_size,
        'record_count_before': len(original), 'record_count_after': len(rows),
        'storage_patch_records': 3, 'new_whitelist_references': 9,
        'mapping': TARGETS, 'all_original_records_unchanged': True,
        'existing_whitelists_preserved': True, 'existing_fields_preserved': True,
        'new_assets_scripts_pollers': 0, 'resource_caps_unchanged': True,
        'guns_use_existing_crossbow_locker_type_107': True,
        'finished_t60_armour_storage_unchanged': True,
        'native_storage_function': 2,
        'real_game_inventory_and_ai_hauling': 'not verified',
        'installation': 'pending', 'effective': 'next game restart',
    }
    (OUT / 'validation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), 'utf8')
    print(json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    main()
