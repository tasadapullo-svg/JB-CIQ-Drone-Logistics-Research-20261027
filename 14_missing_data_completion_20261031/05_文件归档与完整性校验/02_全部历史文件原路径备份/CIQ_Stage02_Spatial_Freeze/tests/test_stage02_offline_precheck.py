"""Synthetic tests only. No real CIQ project used."""
import importlib.util, json, tempfile, zipfile
from pathlib import Path
S=Path(__file__).parents[1]/'scripts'/'stage02_offline_precheck.py'
spec=importlib.util.spec_from_file_location('stage02_offline_precheck',S)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

def makeqgs(source):
    return ('<qgis><projectCrs><spatialrefsys><authid>EPSG:4326</authid>'
     '</spatialrefsys></projectCrs><projectlayers><maplayer type="vector">'
     '<id>x</id><layername>TEST_ONLY_NODES</layername><provider>ogr</provider>'
     '<datasource>'+source+'</datasource></maplayer></projectlayers></qgis>').encode()

def test():
    with tempfile.TemporaryDirectory() as root:
        d=Path(root);work=d/'src';work.mkdir();out=d/'audit'
        (work/'nodes.geojson').write_text('{"type":"FeatureCollection","features":[]}',encoding='utf-8')
        qgs=work/'case.qgs';qgs.write_bytes(makeqgs('./nodes.geojson'))
        qa=m.run(qgs,work,out)
        assert qa['result']=='HOLD'
        assert qa['declared_layer_count']==1
        assert qa['local_sources_missing']==0
        assert qa['qgis_project_candidate_count']==1
        z=work/'case.qgz'
        with zipfile.ZipFile(z,'w') as dst:dst.writestr('case.qgs',qgs.read_bytes())
        qb=m.run(z,work,out)
        assert qb['project_crs']=='EPSG:4326'
        assert qb['qgis_project_candidate_count']==2
        qgs.write_bytes(makeqgs('./gone.gpkg'))
        qc=m.run(qgs,work,out)
        assert 'MISSING_LOCAL_LAYER_SOURCES' in qc['blockers']
        qgs.unlink();z.unlink()
        qd=m.run(None,work,out)
        assert 'PROJECT_NOT_EXPLICITLY_SELECTED' in qd['blockers']
    print('4 synthetic checks passed; no scientific PASS issued')
if __name__=='__main__':test()
