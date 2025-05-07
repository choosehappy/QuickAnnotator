from quickannotator.db.crud.annotation_class import search_annotation_class_by_project_id
import quickannotator.constants as constants

class ColorPalette():
    def __init__(self, project_id):
        color_palette_name = 'default'  # TODO: get this from project settings

        if color_palette_name not in constants.ANNOTATION_CLASS_COLOR_PALETTES:
            raise KeyError(f"Color palette '{color_palette_name}' does not exist in constants.COLOR_PALETTES.")
        
        self.color_list = constants.ANNOTATION_CLASS_COLOR_PALETTES[color_palette_name]
        self.project_id = project_id

    def get_unused_color(self):
        annotation_classes = search_annotation_class_by_project_id(self.project_id)
        used_colors = {str(ac.color) for ac in annotation_classes}
        unused_colors = list(set(self.color_list) - used_colors)
        if len(unused_colors) > 0:
            return unused_colors[0]
        
        raise ValueError("No unused colors available in the color palette.")