import quickannotator.db as qadb
from quickannotator.db.models import Image


def get_image_by_id(image_id: int) -> Image:
    return qadb.db.session.query(Image).get(image_id)
    

# The following code is not in use - instead large_image is used for tile serving.
'''
def getTile(x, y, z, slide: ops.OpenSlide, tileWidth, tileHeight):
    # When we read a region from the SVS, we have to ask for it in the
    # SVS level 0 coordinate system.  Our x and y is in tile space at the
    # specified z level, so the offset in SVS level 0 coordinates has to be
    # scaled by the tile size and by the z level.
    scale = 2 ** (slide.level_count - 1 - z)

    offsetx = x * tileWidth * scale
    offsety = y * tileHeight * scale

    retries = 3
    while retries > 0:
        try:
            tile = slide.read_region(
                (offsetx, offsety), z,
                (tileWidth * scale,
                 tileHeight * scale))
            break
        except ops.lowlevel.OpenSlideError as exc:
            raise exc
    # Always scale to the svs level 0 tile size.
    if scale != 1:
        tile = tile.resize((tileWidth, tileHeight), getattr(PIL.Image, 'Resampling', PIL.Image).LANCZOS)
    return tile

def getTile(x, y, z, slide: ops.OpenSlide, tileWidth, tileHeight):
    svslevel = slide.level_downsamples[z]
    # When we read a region from the SVS, we have to ask for it in the
    # SVS level 0 coordinate system.  Our x and y is in tile space at the
    # specified z level, so the offset in SVS level 0 coordinates has to be
    # scaled by the tile size and by the z level.
    scale = 2 ** (slide.level_count - 1 - z)
    offsetx = x * tileWidth * scale
    offsety = y * tileHeight * scale

    # We ask to read an area that will cover the tile at the z level.  The
    # scale we computed in the __init__ process for this svs level tells
    # how much larger a region we need to read.


    retries = 3
    while retries > 0:
        try:
            tile = slide.read_region(
                (offsetx, offsety), svslevel['svslevel'],
                (tileWidth * svslevel['scale'],
                 tileHeight * svslevel['scale']))
            break
        except openslide.lowlevel.OpenSlideError as exc:
            self._largeImagePath = str(self._getLargeImagePath())
            msg = (
                'Failed to get OpenSlide region '
                f'({exc} on {self._largeImagePath}: {self}).')
            self.logger.info(msg)
            # Reopen handle after a lowlevel error
            try:
                self._openslide = openslide.OpenSlide(self._largeImagePath)
            except Exception:
                raise TileSourceError(msg)
            retries -= 1
            if retries <= 0:
                raise TileSourceError(msg)
        # Always scale to the svs level 0 tile size.
        if svslevel['scale'] != 1:
            tile = tile.resize((self.tileWidth, self.tileHeight),
                               getattr(PIL.Image, 'Resampling', PIL.Image).LANCZOS)
    return self._outputTile(tile, format, x, y, z, pilImageAllowed,
                            numpyAllowed, **kwargs)
    return tile
    
'''