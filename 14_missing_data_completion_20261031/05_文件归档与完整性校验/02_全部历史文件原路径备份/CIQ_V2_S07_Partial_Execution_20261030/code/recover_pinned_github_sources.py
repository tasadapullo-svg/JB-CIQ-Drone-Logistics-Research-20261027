#!/usr/bin/env python3
"""Optional USER-SIDE download/verify source binary files at immutable GitHub commit.
Run only in a network-enabled local environment. No downloads or silent substitutions by default.
The two historic road graphs are legacy A/B scope and MUST NOT be merged into new ABC routing without new road topology QA.
"""
import argparse,hashlib,json,pathlib,urllib.parse,urllib.request,zipfile,csv,time
COMMIT='4569817b8145efe2ae06f4b21addc1986f971c12'
REPO='tasadapullo-svg/JB-CIQ-Drone-Logistics-Research-20261027'
PREFIX='03_gis_and_road_network/road_network_project/JB_CIQ_E02_roadnet_V4_6/outputs/'
W='data/weather_2026/processed/'
E=[
 ('JB_SG_Weather_2026_05.xlsx',W+'JB_SG_Weather_2026_05.xlsx',13001616,'4ae1a0f8f9462a66fda3f2cd24965604d1afb081'),
 ('JB_SG_Weather_2026_06.xlsx',W+'JB_SG_Weather_2026_06.xlsx',13001925,'b773932d1249c32a6788149bc6f8f8c7f08fb847'),
 ('JB_SG_Weather_2026_07.xlsx',W+'JB_SG_Weather_2026_07.xlsx',13752431,'a554f49d64500bd1d9df4b23b40a1da174f4eca0'),
 ('JB_SG_Weather_2026_08.xlsx',W+'JB_SG_Weather_2026_08.xlsx',14124507,'a1ad400f2e0897dce3e775a63e8f20a64bc2d86f'),
 ('JB_SG_Weather_2026_09.xlsx',W+'JB_SG_Weather_2026_09.xlsx',14148344,'ba4fbefe437989ae7103b4895fcaf06b32c92b9e'),
 ('E02_A_directed_edges_OSM.csv',PREFIX+'E02_A_directed_edges_OSM.csv',14959641,'96245d509e964d509e36bb0fde50015113cf91a0'),
 ('E02_B_directed_edges_OSM.csv',PREFIX+'E02_B_directed_edges_OSM.csv',8652178,'da71c01fdbea6da04eb63d80584219a081312d41'),
 ('E02_A_road_graph_nodes.csv',PREFIX+'E02_A_road_graph_nodes.csv',3230183,'afc8bb3150af914c397bdf59777997c07384cb03'),
 ('E02_B_road_graph_nodes.csv',PREFIX+'E02_B_road_graph_nodes.csv',1942569,'e48dd04e4147b09cdeda8585698ee131d8eb74c7'),
 ('19_site_reference_anchors_NOT_LAUNCH_PADS.csv','03_gis_and_road_network/road_network_project/JB_CIQ_E02_roadnet_V4_6/inputs/19_site_reference_anchors_NOT_LAUNCH_PADS.csv',5442,'4c76d71d50cd48ba4a01ed902bd9e253fdef49cf'),
 ('stage6_order_level.csv.gz','10_experiment_results/stage6_dual_region_multilevel_feeder/stage6_order_level.csv.gz',1542821,'5e68fb71c0b0737ed1846f680c85f82a4d04ce06'),
]
def git_blob(b):return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
def run(output:pathlib.Path,fetch:bool):
    output.mkdir(parents=True,exist_ok=True);rows=[]
    for name,p,size,h in E:
        target=output/name;url=f'https://raw.githubusercontent.com/{REPO}/{COMMIT}/'+urllib.parse.quote(p,safe='/')
        if fetch and not target.is_file():
            try:
                with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'S07-research-source-verifier'}),timeout=90) as fh, target.open('wb') as f:
                    import shutil;shutil.copyfileobj(fh,f)
            except Exception as exc:
                if target.exists():target.unlink()
                rows.append({'file':name,'status':'DOWNLOAD_FAILED','reason':str(exc),'source_url':url});continue
        if not target.is_file():
            rows.append({'file':name,'status':'NOT_PRESENT','reason':'Run --download in network-enabled environment or supply matching local file','source_url':url});continue
        data=target.read_bytes()
        verified=len(data)==size and git_blob(data)==h
        bad_zip=''
        if verified and name.endswith('.xlsx'):
            try:
                with zipfile.ZipFile(target) as z:bad_zip=z.testzip() or ''
            except Exception as e:bad_zip=str(e)
        rows.append({'file':name,'status':'PASS_GITHUB_BLOB_IDENTITY' if verified and not bad_zip else 'FAIL_HASH_SIZE_OR_ARCHIVE',
        'actual_size':len(data),'expected_size':size,'git_blob_sha1_actual':git_blob(data),'git_blob_sha1_expected':h,
        'sha256_actual':hashlib.sha256(data).hexdigest(),'zip_test_error':bad_zip,'source_url':url})
    with (output/'github_source_validation.json').open('w',encoding='utf-8') as f:json.dump(rows,f,ensure_ascii=False,indent=2)
    print(json.dumps({'pass':sum(r['status']=='PASS_GITHUB_BLOB_IDENTITY' for r in rows),'total':len(E),'download_attempted':fetch},ensure_ascii=False))
    # Important: file identity does not prove the original summary's historical SHA256, road coverage, flight approval, or science validity.
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=pathlib.Path,default=pathlib.Path('external_sources'));ap.add_argument('--download',action='store_true');a=ap.parse_args();run(a.out,a.download)
