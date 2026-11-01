import json
from pathlib import Path
import sys

import bpy


def main():
    tasks = json.loads(Path(sys.argv[sys.argv.index("--") + 1]).read_text())
    for task in tasks:
        for obj in list(bpy.data.objects):
            bpy.data.objects.remove(obj, do_unlink=True)
        for collection in (bpy.data.meshes, bpy.data.materials):
            for block in list(collection):
                collection.remove(block)
        bpy.ops.wm.obj_import(filepath=task["input"], forward_axis="Y", up_axis="Z")
        objects = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
        if not objects:
            raise ValueError(f"No geometry imported from {task['input']}")
        for obj in objects:
            modifier = obj.modifiers.new(name="Web triangulation", type="TRIANGULATE")
            modifier.quad_method = "BEAUTY"
            modifier.ngon_method = "BEAUTY"
        bpy.ops.export_scene.gltf(
            filepath=task["output"],
            export_format="GLB",
            export_yup=True,
            export_apply=True,
            export_extras=True,
            export_cameras=False,
            export_lights=False,
        )


if __name__ == "__main__":
    main()
