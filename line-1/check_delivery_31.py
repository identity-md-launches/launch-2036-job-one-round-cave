"""Read-only preflight for round 31; reports only task-local deliverable facts."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import zlib


def png(path):
    raw = path.read_bytes()
    assert raw[:8] == b'\x89PNG\r\n\x1a\n'
    offset, chunks = 8, []
    while offset < len(raw):
        size = struct.unpack_from('>I', raw, offset)[0]
        kind = raw[offset+4:offset+8]
        data = raw[offset+8:offset+8+size]
        crc = struct.unpack_from('>I', raw, offset+8+size)[0]
        assert zlib.crc32(kind+data) == crc
        if kind == b'IHDR':
            width, height, depth, color, compression, filtering, interlace = struct.unpack('>IIBBBBB', data)
            assert (width, height, depth, color, compression, filtering, interlace) == (1254,1254,8,2,0,0,0)
        if kind == b'IDAT':
            chunks.append(data)
        offset += size+12
        if kind == b'IEND':
            break
    assert offset == len(raw)
    assert len(zlib.decompress(b''.join(chunks))) == (1254*3+1)*1254
    return {'format': 'PNG', 'dimensions': [width,height], 'bytes': len(raw),
            'sha256': hashlib.sha256(raw).hexdigest()}


def jpeg(path):
    raw = path.read_bytes()
    assert raw[:2] == b'\xff\xd8' and raw[-2:] == b'\xff\xd9'
    offset = 2
    while offset < len(raw):
        assert raw[offset] == 255
        marker = raw[offset+1]
        size = int.from_bytes(raw[offset+2:offset+4], 'big')
        assert size >= 2
        if marker == 0xc0:
            height = int.from_bytes(raw[offset+5:offset+7], 'big')
            width = int.from_bytes(raw[offset+7:offset+9], 'big')
            assert (width, height) == (512,512)
            assert len(raw) <= 100000
            return {'format':'JPEG', 'dimensions':[width,height], 'bytes':len(raw)}
        offset += size+2
    raise AssertionError('JPEG frame absent')


def main():
    record_path = Path('dist/line-1/31.json')
    record = json.loads(record_path.read_text())
    assert set(record) == {'name','image','attributes'}
    attrs = record['attributes']
    assert len(attrs) == 6 and all(set(a) == {'trait_type','value'} for a in attrs)
    values = {a['trait_type']:a['value'] for a in attrs}
    assert set(values) == {'Cave','Wall','Number','Left behind','Meaning','One thing'}
    assert values['Number'] == 31 and type(values['Number']) is int
    assert values['Wall'] == 'Line 1' and values['Cave'] == 'Lava'
    assert values['Left behind'] == 'Goalslice'
    assert len(list(Path('dist/line-1').glob('*.json'))) == 31
    wall_path = Path('artifacts/line-1/wall-v12.png')
    wall = png(wall_path)
    assert Path('artifacts/line-1/wall.png').read_bytes() == wall_path.read_bytes()
    assert record['image'] == 'https://api.imd.fun/artifacts/'+wall['sha256']
    preview = jpeg(Path('dist/line-1/31.jpg'))
    media = json.loads(Path('line-1/media-check-31.json').read_text())
    assert media['sha256'] == wall['sha256']
    review = json.loads(Path('line-1/review-31.json').read_text())
    assert review['visual_review']['unmet_visual_requirements'] == []
    # Read every newly delivered source/report file, and enforce its byte bound.
    files = list(Path('line-1/tools/goalslice').glob('*')) + [
        Path('line-1/check_delivery_31.py'), Path('line-1/check-results-31.json'),
        Path('line-1/media-check-31.json'), Path('line-1/review-31.json'),
        Path('line-1/media/finish-wall-31.cjs'), record_path,
        Path('line-1/README.md'), Path('line-1/USED.md')]
    for path in files:
        assert path.is_file() and len(path.read_bytes()) <= 100000, str(path)
        if path.suffix == '.json':
            json.loads(path.read_text())
    assert 'python3 -B line-1/tools/goalslice/goalslice.py --demo --explain' in Path('line-1/tools/goalslice/README.md').read_text()
    # Original goal and every previous numbered record must match Git exactly.
    originals = ['line-1/GOAL.md'] + [f'dist/line-1/{n:02}.json' for n in range(1,31)]
    for name in originals:
        original = subprocess.run(['git','show','HEAD:'+name],capture_output=True,check=True).stdout
        assert Path(name).read_bytes() == original, name
    assert not subprocess.run(['git','ls-files',str(wall_path)],capture_output=True,check=True).stdout
    changes = subprocess.run(['git','diff','--name-only','HEAD'],capture_output=True,text=True,check=True).stdout.splitlines()
    assert all(n.startswith(('line-1/','dist/line-1/','artifacts/line-1/')) for n in changes)
    result = {'wall':wall,'continuing_wall_identical':True,'preview':preview,
              'record':str(record_path),'goal_and_30_older_records_unchanged':True,
              'named_wall_untracked':True,'new_source_and_report_files_under_100KB':True,
              'unmet_visual_requirements':[],
              'image_location_conflict':'Explicit record-adjacent JPEG requirement followed; see review-31.json.',
              'pixel_preservation':'Independently compare with node snippet in check-results-31.json; media-check-31.json records assembly.'}
    print(json.dumps(result,indent=2))


if __name__ == '__main__':
    main()
