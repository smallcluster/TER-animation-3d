bl_info = {
    "name": "SimpleRetargeting",
    "description": "Simple retargeting method which auto apply rotations constraints from one rig to an other",
    "author": "Pierre Jaffuer",
    "version": (0, 0, 1),
    "blender": (2, 90, 3),
    "category": "Animation"
}

import bpy

# Show a small popup window under the mouse
def show_massage_box(message="", title="Message Box", icon="INFO"):
    def draw(self, context):
        self.layout.label(text=message)
    bpy.context.window_manager.popup_menu(draw, title=title, icon=icon)


def match_bones(self, context):
    sr_settings = context.scene.sr_settings
    for pair in sr_settings.bones_retarget_collection:
        # try to find the corresponding bone from source armature
        for bs in sr_settings.source_armature.pose.bones:
            # exact match have full priority
            if pair.name == bs.name:
                pair.value = bs.name
                break

        
def updateBonesCollection(self, context):

    sr_settings = context.scene.sr_settings

    # Clear list of bones
    sr_settings.bones_retarget_collection.clear()

    # Check if selected objects are armatures
    if sr_settings.source_armature != None and sr_settings.source_armature.type != "ARMATURE":
        sr_settings.source_armature = None
        show_massage_box("Source must be an Armature object !", "Not an armature", "ERROR")
        return
    
    if sr_settings.target_armature != None and sr_settings.target_armature.type != "ARMATURE":
        sr_settings.target_armature = None
        show_massage_box("Target must be an Armature object !", "Not an armature", "ERROR")
        return

    # Do nothing if source or target isn't set
    if sr_settings.source_armature == None or sr_settings.target_armature == None:
        return

    # Check that source and target objects are defferents
    if sr_settings.source_armature.name == sr_settings.target_armature.name:
        sr_settings.source_armature = None
        sr_settings.target_armature = None
        show_massage_box("Use different armatures for source and target !", "Bad selecetion", "ERROR")
        return

    # Create bone setup list
    for bt in sr_settings.target_armature.pose.bones:
        c = sr_settings.bones_retarget_collection.add()
        c.name = bt.name
    
    # Update bone setup list
    match_bones(self, context)
    
    return None

# ---------------------------------------------------------------------------------------------------------------------
# Property groups
# ---------------------------------------------------------------------------------------------------------------------

class BoneNamePair(bpy.types.PropertyGroup):
    name : bpy.props.StringProperty(name="Bone pair")
    value : bpy.props.StringProperty(name="Bone pair", default="")

    invert_x : bpy.props.BoolProperty(default=False)
    invert_y : bpy.props.BoolProperty(default=False)
    invert_z : bpy.props.BoolProperty(default=False)

class SRSettings(bpy.types.PropertyGroup):
    source_armature : bpy.props.PointerProperty(type=bpy.types.Object, update=updateBonesCollection)
    target_armature : bpy.props.PointerProperty(type=bpy.types.Object, update=updateBonesCollection)

    bones_retarget_collection : bpy.props.CollectionProperty(type=BoneNamePair)

    search_name : bpy.props.StringProperty()

    search_filter : bpy.props.EnumProperty(
        items=[
            ("ALL", "all", ""), 
            ("EMPTY", "empty", ""), 
            ("FILLED", "filled", "")
            ],
        name="Search filter",
        description="Filter displayed bones",
        default="ALL"
    )


# ---------------------------------------------------------------------------------------------------------------------
# Operators
# ---------------------------------------------------------------------------------------------------------------------

# Convention for blender operator:
# CLASS_OT_your_name
# bl_idname = "class.your_name"
class SR_OT_retarget(bpy.types.Operator):
    bl_idname = "sr.retarget"
    bl_label = "Retarget"
    bl_description = "Apply rotations constraints on specified bones"

    def execute(self, context):
        sr_settings = context.scene.sr_settings

        for pair in sr_settings.bones_retarget_collection:

            constraints = sr_settings.target_armature.pose.bones[pair.name].constraints
            c_rot_name = "SR_copy_rot"

            # remove constraints if previously set
            if pair.value == "":
                if c_rot_name in constraints:
                    constraints.remove(constraints[c_rot_name])
            # Add or update constraints
            else:
                if c_rot_name not in constraints: # add
                    c = constraints.new("COPY_ROTATION")
                    c.name = c_rot_name
                else: # update
                    c = constraints[c_rot_name]
                c.target = sr_settings.source_armature
                c.subtarget = pair.value
                c.invert_x = pair.invert_x
                c.invert_y = pair.invert_y
                c.invert_z = pair.invert_z
                c.target_space = "LOCAL"
                c.owner_space = "LOCAL"
                c.mix_mode = "ADD"
        
        return {"FINISHED"}

class SR_OT_match_bones(bpy.types.Operator):
    bl_idname = "sr.match_bones"
    bl_label = "Auto match bones"
    bl_description = "Try to match source and target bones"

    def execute(self, context):
        sr_settings = context.scene.sr_settings
        match_bones(self, context)
        return {"FINISHED"}

class SR_OT_match_selected_bones(bpy.types.Operator):
    bl_idname = "sr.match_selected_bones"
    bl_label = "Match selected bones"
    bl_description = "Match selected source bone to active target bone"

    def execute(self, context):
        sr_settings = context.scene.sr_settings

        # select 2 bones
        if len(bpy.context.selected_pose_bones) != 2:
            show_massage_box("Please select exactly 2 bones !", "Can't match bones", "ERROR")
            return {"CANCELLED"}

        selected_bone = bpy.context.selected_pose_bones[1]
        active_bone = bpy.context.object.data.bones.active

        selected_object = selected_bone.id_data
        active_object = active_bone.id_data

        # Object can't be the same
        if selected_object.name == active_object.name:
            show_massage_box("Selected bones can't be from the same armature !", "Can't match bones", "ERROR")
            return {"CANCELLED"}

        #--- check if one is from the target armature and the other from the source armature ---

        # selected object is target object
        if selected_object.name == sr_settings.target_armature.name:
            target_bone_name = selected_bone.name

            if active_object.name == sr_settings.source_armature.name:
                source_bone_name = active_bone.name
            else:
                show_massage_box("Active bone isn't from source armature !", "Can't match bones", "ERROR")
                return {"CANCELLED"}

        # active object is target object
        elif active_object.name == sr_settings.target_armature.name:
            target_bone_name = active_bone.name

            if selected_object.name == sr_settings.source_armature.name:
                source_bone_name = selected_bone.name
            else:
                show_massage_box("First selected bone isn't from source armature !", "Can't match bones", "ERROR")
                return {"CANCELLED"}

        # None of selected bones are from the target armature
        else:
            show_massage_box("No selected bones are from target armature !", "Can't match bones", "ERROR") 
            return {"CANCELLED"}

        # we have a source and a target bone
        sr_settings.bones_retarget_collection.get(target_bone_name).value = source_bone_name
        sr_settings.search_name = target_bone_name
        
        return {"FINISHED"}

class SR_OT_clear_bones(bpy.types.Operator):
    bl_idname = "sr.clear_bones"
    bl_label = "Clear all"
    bl_description = "Clear all matched bones"

    def execute(self, context):
        sr_settings = context.scene.sr_settings
        for pair in sr_settings.bones_retarget_collection:
            pair.value = ""
        return {"FINISHED"}

# ---------------------------------------------------------------------------------------------------------------------
# Panels
# ---------------------------------------------------------------------------------------------------------------------

class SR_PT_armature_setup_panel(bpy.types.Panel):
    bl_idname = "SR_PT_armature_setup_panel" # should match the class name
    bl_label = "Armatures setup"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "SimpleRetargeting"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        sr_settings = scene.sr_settings

        col = layout.column()
        col.prop_search(scene.sr_settings, "source_armature", bpy.data, "objects", text="Source")
        col.prop_search(scene.sr_settings, "target_armature", bpy.data, "objects", text="Target")
        col.separator()

        if not sr_settings.source_armature or not sr_settings.target_armature:
            return

        col.operator("sr.retarget")


class SR_PT_bones_setup_panel(bpy.types.Panel):
    bl_idname = "SR_PT_bones_setup_panel" # should match the class name
    bl_label = "Bones setup"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "SimpleRetargeting"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        sr_settings = scene.sr_settings

        if not sr_settings.source_armature or not sr_settings.target_armature:
            return

        col = layout.column()
        col.operator("sr.match_bones")
        row = layout.row()
        row.operator("sr.match_selected_bones")
        row.operator("sr.clear_bones")

        col = layout.column()
        col.separator()
        col.prop(sr_settings, "search_name", text="Search")
        col.prop(sr_settings, "search_filter")
        filter = sr_settings.search_filter
        col.separator()

        # display parm list for the search result, "" means show all
        search_name = sr_settings.search_name.upper()
        for pair in sr_settings.bones_retarget_collection:

            # apply search filter first
            if pair.value == "" and filter == "FILLED":
                continue
            elif pair.value != "" and filter == "EMPTY":
                continue
        
            # do not display if the search string isn't empty and there is no match 
            if search_name != "" and pair.name.upper().find(search_name) == -1:
                continue
            else: # Show all or search found
                layout.column()
                row = layout.row()
                row.prop_search(pair, "value", sr_settings.source_armature.pose, "bones", text=pair.name)
                row = layout.row()
                row = row.row()
                row.label(text="Invert")
                row.prop(pair, "invert_x", text="X", toggle=True)
                row.prop(pair, "invert_y", text="Y", toggle=True)
                row.prop(pair, "invert_z", text="Z", toggle=True)


# ---------------------------------------------------------------------------------------------------------------------
# Class registering/unregistering
# ---------------------------------------------------------------------------------------------------------------------

classes = (
    BoneNamePair,
    SRSettings,
    SR_OT_retarget,
    SR_OT_match_bones,
    SR_OT_match_selected_bones,
    SR_OT_clear_bones,
    SR_PT_armature_setup_panel,
    SR_PT_bones_setup_panel
)

def register():
    for cl in classes:
        bpy.utils.register_class(cl)

    # Init shared props, ie link the python interface to the C type
    bpy.types.Scene.sr_settings = bpy.props.PointerProperty(type=SRSettings)

    
def unregister():
    for cl in classes:
        bpy.utils.unregister_class(cl)

    # Free memory used by shared props
    del bpy.types.Scene.init_settings

if __name__ == "__main__":
    register()

