from quickannotator.db.crud.annotation_class import get_all_annotation_classes_for_project, get_annotation_class_by_id
import quickannotator.constants as constants

class ColorPalette():
    def __init__(self, project_id):
        color_palette_name = 'default'  # TODO: get this from project settings

        if color_palette_name not in constants.ANNOTATION_CLASS_COLOR_PALETTES:
            raise KeyError(f"Color palette '{color_palette_name}' does not exist in constants.COLOR_PALETTES.")
        
        self.color_list = constants.ANNOTATION_CLASS_COLOR_PALETTES[color_palette_name]
        self.project_id = project_id

    def get_unused_color(self):
        result = [get_annotation_class_by_id(constants.MASK_CLASS_ID)]  # Always include the mask class
        result.extend(get_all_annotation_classes_for_project(self.project_id))
        used_colors = {ac.color for ac in result}
        for color in self.color_list:
            if color not in used_colors:
                return color
        
        raise ValueError("No unused colors available in the color palette.")