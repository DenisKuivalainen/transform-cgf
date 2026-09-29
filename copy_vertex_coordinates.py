bl_info = {
    "name": "Copy Vertex Coordinates",
    "author": "OpenAI",
    "version": (1, 0, 0),
    "blender": (4, 0, 0),
    "location": "Edit Mode > Vertex",
    "description": "Copy and paste vertex XYZ coordinates",
    "category": "Mesh",
}

import bpy
import bmesh
from mathutils import Vector

# Stores copied coordinates
COPIED_COORD = None


class MESH_OT_copy_vertex_coordinates(bpy.types.Operator):
    bl_idname = "mesh.copy_vertex_coordinates"
    bl_label = "Copy Vertex Coordinates"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return (
            context.object is not None
            and context.object.type == "MESH"
            and context.mode == "EDIT_MESH"
        )

    def execute(self, context):
        bm = bmesh.from_edit_mesh(context.object.data)

        active = bm.select_history.active
        if not isinstance(active, bmesh.types.BMVert):
            self.report({"ERROR"}, "Active element must be a vertex.")
            return {"CANCELLED"}

        co = active.co

        text = f"{co.x * 100}, {co.y * 100}, {co.z * 100}"

        context.window_manager.clipboard = text

        self.report({"INFO"}, f"Copied to clipboard: {text}")

        return {"FINISHED"}


class MESH_OT_paste_vertex_coordinates(bpy.types.Operator):
    bl_idname = "mesh.paste_vertex_coordinates"
    bl_label = "Paste Vertex Coordinates"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return (
            context.object is not None
            and context.object.type == "MESH"
            and context.mode == "EDIT_MESH"
        )

    def execute(self, context):
        def execute(self, context):
            context.window_manager.clipboard = "Hello from Blender!"
            self.report({"INFO"}, "Copied test text to clipboard.")
            return {"FINISHED"}

        bm = bmesh.from_edit_mesh(context.object.data)

        active = bm.select_history.active
        if not isinstance(active, bmesh.types.BMVert):
            self.report({"ERROR"}, "Active element must be a vertex.")
            return {"CANCELLED"}

        co = active.co

        text = f"{co.x:.6f}, {co.y:.6f}, {co.z:.6f}"

        context.window_manager.clipboard = text

        self.report({"INFO"}, f"Copied to clipboard: {text}")
        return {"FINISHED"}


def menu_func(self, context):
    self.layout.separator()
    self.layout.operator("mesh.copy_vertex_coordinates", icon="COPYDOWN")
    self.layout.operator("mesh.paste_vertex_coordinates", icon="PASTEDOWN")


classes = (
    MESH_OT_copy_vertex_coordinates,
    MESH_OT_paste_vertex_coordinates,
)

addon_keymaps = []


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.VIEW3D_MT_edit_mesh_vertices.append(menu_func)

    # Keyboard shortcuts
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon

    if kc:
        km = kc.keymaps.new(name="Mesh", space_type="EMPTY")

        # Ctrl+Shift+C = Copy
        kmi = km.keymap_items.new(
            "mesh.copy_vertex_coordinates",
            type="C",
            value="PRESS",
            ctrl=True,
            shift=True,
        )
        addon_keymaps.append((km, kmi))

        # Ctrl+Shift+V = Paste
        kmi = km.keymap_items.new(
            "mesh.paste_vertex_coordinates",
            type="V",
            value="PRESS",
            ctrl=True,
            shift=True,
        )
        addon_keymaps.append((km, kmi))


def unregister():

    # Remove shortcuts
    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()

    bpy.types.VIEW3D_MT_edit_mesh_vertices.remove(menu_func)

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
