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


def update_constraint(self, context):
    sr_settings = context.scene.sr_settings
    constraints = sr_settings.target_armature.pose.bones[self.name].constraints
    c_rot_name = "SR_copy_rot"

    # remove constraints if previously set
    if self.value == "":
        if c_rot_name in constraints:
            constraints.remove(constraints[c_rot_name])
    # Add or update constraints
    else:
        # add
        if c_rot_name not in constraints:
            c = constraints.new("COPY_ROTATION")
            c.name = c_rot_name
        # update
        else:
            c = constraints[c_rot_name]

        # settings
        c.target = sr_settings.source_armature
        c.subtarget = self.value
        c.invert_x = self.invert_x
        c.invert_y = self.invert_y
        c.invert_z = self.invert_z
        c.target_space = "LOCAL"
        c.owner_space = "LOCAL"
        c.mix_mode = "ADD"


def auto_match_bones(self, context):
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

        # Get previous bone match through constraint
        constraints = sr_settings.target_armature.pose.bones[bt.name].constraints
        c_rot_name = "SR_copy_rot"
        if c_rot_name in constraints:
            constraint = constraints[c_rot_name]
            c.value = constraint.subtarget
            c.invert_x = constraint.invert_x
            c.invert_y = constraint.invert_y
            c.invert_z = constraint.invert_z
    
    return None

# ---------------------------------------------------------------------------------------------------------------------
# Property groups
# ---------------------------------------------------------------------------------------------------------------------

class BoneNamePair(bpy.types.PropertyGroup):
    name : bpy.props.StringProperty(name="Bone pair")

    value : bpy.props.StringProperty(name="Bone pair", default="", update=update_constraint)
    invert_x : bpy.props.BoolProperty(default=False, update=update_constraint)
    invert_y : bpy.props.BoolProperty(default=False, update=update_constraint)
    invert_z : bpy.props.BoolProperty(default=False, update=update_constraint)

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
class SR_OT_auto_match_bones(bpy.types.Operator):
    bl_idname = "sr.auto_match_bones"
    bl_label = "Auto match bones"
    bl_description = "Try to match source and target bones"

    def execute(self, context):
        sr_settings = context.scene.sr_settings
        auto_match_bones(self, context)
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

        bone1 = bpy.context.selected_pose_bones[1]
        bone2 = bpy.context.selected_pose_bones[0]

        armature1 = bone1.id_data
        armature2 = bone2.id_data

        # Object can't be the same
        if armature1.name == armature2.name:
            show_massage_box("Selected bones can't be from the same armature !", "Can't match bones", "ERROR")
            return {"CANCELLED"}

        #--- check if one is from the target armature and the other from the source armature ---

        # armature 1 is target armature
        if armature1.name == sr_settings.target_armature.name:
            target_bone_name = bone1.name

            if armature2.name == sr_settings.source_armature.name:
                source_bone_name = bone2.name
            else:
                show_massage_box("Second bone isn't from source armature !", "Can't match bones", "ERROR")
                return {"CANCELLED"}

        # armature 2 is target armature
        elif armature2.name == sr_settings.target_armature.name:
            target_bone_name = bone2.name

            if armature1.name == sr_settings.source_armature.name:
                source_bone_name = bone1.name
            else:
                show_massage_box("First bone isn't from source armature !", "Can't match bones", "ERROR")
                return {"CANCELLED"}

        # None of selected bones are from the target armature
        else:
            show_massage_box("No selected bones are from target armature !", "Can't match bones", "ERROR") 
            return {"CANCELLED"}

        # we have a source and a target bone
        pair = sr_settings.bones_retarget_collection.get(target_bone_name)
        pair.value = source_bone_name
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
            pair.invert_x = False
            pair.invert_y = False
            pair.invert_z = False
        return {"FINISHED"}

class SR_OT_clear_selected(bpy.types.Operator):
    bl_idname = "sr.clear_selected"
    bl_label = "Clear selected"
    bl_description = "Clear constraint from selected bones"

    def execute(self, context):
        sr_settings = context.scene.sr_settings
        selected_bones = bpy.context.selected_pose_bones

        for bone in selected_bones:
            # bone is from the target armature
            print(bone.id_data.name)
            if bone.id_data.name == sr_settings.target_armature.name:
                pair = sr_settings.bones_retarget_collection.get(bone.name)
                print(pair.name)
                pair.value = ""
                pair.invert_x = False
                pair.invert_y = False
                pair.invert_z = False


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

        row = layout.row()
        row.operator("sr.auto_match_bones")
        row.operator("sr.match_selected_bones")
        row = layout.row()
        row.operator("sr.clear_bones")
        row.operator("sr.clear_selected")
        

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
    SR_OT_clear_selected,
    SR_OT_auto_match_bones,
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
