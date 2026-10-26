# MerweLab geometry tools v1
"""Blender Text Editor > Open > Run Script. Reads config/merwelab_coordinates.json."""
import json
from pathlib import Path
import bpy

PROJECT_ROOT = r""  # Normally automatic when this file is in scripts/wind/.
INCLUDE_REVIEW_GEOMETRY = True  # The partial 13-building source set is for review.

def project_root():
    if PROJECT_ROOT:return Path(PROJECT_ROOT).expanduser()
    candidates=[]
    if '__file__' in globals():candidates.append(Path(__file__).resolve())
    text=getattr(getattr(bpy.context,'space_data',None),'text',None)
    if text and text.filepath:candidates.append(Path(bpy.path.abspath(text.filepath)))
    for p in candidates:
        for parent in p.parents:
            if (parent/'config/merwelab_coordinates.json').is_file():return parent
    raise RuntimeError('Set PROJECT_ROOT at the top of this script to your MerweLab folder.')

def read_obj(path,origin):
    vertices=[];faces=[]
    for line in path.read_text().splitlines():
        p=line.split()
        if not p:continue
        if p[0]=='v':vertices.append(tuple(float(p[i+1])-origin[i] for i in range(3)))
        elif p[0]=='f':faces.append([int(x.split('/')[0])-1 if int(x.split('/')[0])>0 else len(vertices)+int(x.split('/')[0]) for x in p[1:]])
    return vertices,faces

def main():
    root=project_root();manifest=json.loads((root/'config/merwelab_coordinates.json').read_text());origin=manifest['RD_origin']
    groups=['shared','baseline','scenario_a','scenario_b']
    for name in ['MerweLab_BASELINE','MerweLab_V1','MerweLab_V2']:
        if bpy.data.scenes.get(name):raise RuntimeError('MerweLab scenes already exist. Open a new Blender file before importing; this script does not delete scenes.')
    assets=[a for a in manifest['items'] if INCLUDE_REVIEW_GEOMETRY or not a.get('review_only')]
    for a in assets:
        if not (root/a['path']).is_file():raise RuntimeError('Missing model: '+a['path'])
    collections={g:bpy.data.collections.new('MerweLab_'+g) for g in groups}
    for a in assets:
        vertices,faces=read_obj(root/a['path'],origin)
        mesh=bpy.data.meshes.new(Path(a['path']).stem+'_mesh');mesh.from_pydata(vertices,[],faces);mesh.update()
        obj=bpy.data.objects.new(Path(a['path']).stem,mesh);collections[a['group']].objects.link(obj)
        obj.location=(0,0,0);obj.rotation_euler=(0,0,0);obj.scale=(1,1,1)
        obj.lock_location=(True,True,True);obj.lock_rotation=(True,True,True);obj.lock_scale=(True,True,True)
        obj['model_key']=a['name'];obj['project_root']=str(root);obj['RD_origin_m']=origin;obj['source_status']=a['status'];obj['source_RD_file']=str(root/a['path'])
        color=tuple(int(a['color'][i:i+2],16)/255 for i in [1,3,5])+(1.,)
        mat=bpy.data.materials.new(Path(a['path']).stem+'_material');mat.diffuse_color=color;mat.use_nodes=True
        shader=mat.node_tree.nodes.get('Principled BSDF')
        if shader:shader.inputs['Base Color'].default_value=color;shader.inputs['Roughness'].default_value=.85
        mesh.materials.append(mat);obj.color=color
    scenes={}
    for group,label in [('baseline','BASELINE'),('scenario_a','V1'),('scenario_b','V2')]:
        scene=bpy.data.scenes.new('MerweLab_'+label);scenes[group]=scene
        scene.collection.children.link(collections['shared']);scene.collection.children.link(collections[group])
        scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1.;scene.unit_settings.length_unit='METERS'
        scene['RD_origin_m']=origin;scene['project_root']=str(root);scene['status']='Geometry review; incomplete building/source verification'
    if bpy.context.window:bpy.context.window.scene=scenes['scenario_b']
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type=='VIEW_3D':
                for space in area.spaces:
                    if space.type=='VIEW_3D':space.clip_start=.1;space.clip_end=20000;space.shading.color_type='MATERIAL'
    print('Loaded',len(assets),'named RD assets using the unchanged shared origin:',origin)
    print('Select MerweLab_BASELINE / MerweLab_V1 / MerweLab_V2. Press Home to frame all.')
    print('Partial additional buildings are review geometry, not approved final simulation inputs.')
if __name__=='__main__':main()
