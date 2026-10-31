from zipfile import ZipFile
from hashlib import sha256
from csv import DictReader
import io,sys
z=ZipFile(sys.argv[1])
rows=list(DictReader(io.StringIO(z.read('00_总目录与SHA256校验/ALL_FILES_SHA256.csv').decode('utf-8-sig'))))
for i,r in enumerate(rows,1):
    data=z.read('01_全部历史文件原路径/'+r['relative_path'])
    assert len(data)==int(r['bytes']),(i,r['relative_path'],'size')
    assert sha256(data).hexdigest()==r['sha256'],(i,r['relative_path'],'SHA256')
print(f'PASS: {len(rows)} files verified, all SHA256 matched')
