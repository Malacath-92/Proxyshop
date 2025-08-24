"""
* Helpers: Adjustment Layers
"""
# Standard Library
from typing import NotRequired, TypedDict, Unpack

# Third Party
from photoshop.api import BlendMode, DialogModes, ActionList, ActionDescriptor, ActionReference
from photoshop.api._artlayer import ArtLayer
from photoshop.api._document import Document
from photoshop.api._layerSet import LayerSet

# Local Imports
from src import APP
from src.helpers.colors import get_color, apply_color, add_color_to_gradient, rgb_black
from src.schema.colors import ColorObject, GradientConfig

# QOL Definitions
sID, cID = APP.stringIDToTypeID, APP.charIDToTypeID
NO_DIALOG = DialogModes.DisplayNoDialogs

"""
* Creating Adjustment Layers
"""


def create_vibrant_saturation(vibrancy: int, saturation: int) -> None:
    """Experimental scoot action to add vibrancy and saturation.

    Args:
        vibrancy: Vibrancy level integer
        saturation: Saturation level integer
    """
    # dialogMode (Have dialog popup?)
    desc232 = ActionDescriptor()
    desc232.putInteger(sID("vibrance"), vibrancy)
    desc232.putInteger(sID("saturation"), saturation)
    APP.executeAction(sID("vibrance"), desc232, NO_DIALOG)


class CreateColorLayerKwargs(TypedDict):
    clipped: NotRequired[bool]
    blend_mode: NotRequired[BlendMode]


def create_color_layer(
    color: ColorObject,
    layer: ArtLayer | LayerSet | None,
    docref: Document | None = None,
    **kwargs: Unpack[CreateColorLayerKwargs]
) -> ArtLayer:
    """Create a solid color adjustment layer.

    Args:
        color: Color to use for the layer.
        layer: ArtLayer or LayerSet to make active, if provided.
        docref: Reference Document, use active if not provided.

    Keyword Args:
        clipped (bool): Whether to apply as a clipping mask to the nearest layer, defaults to True.
        blend_mode (BlendMode): Optional blend mode to apply to the new layer.

    Returns:
        The new solid color adjustment layer.
    """
    docref = docref or APP.activeDocument
    if layer:
        docref.activeLayer = layer
    desc1 = ActionDescriptor()
    ref1 = ActionReference()
    desc2 = ActionDescriptor()
    desc3 = ActionDescriptor()
    ref1.putClass(sID("contentLayer"))
    desc1.putReference(sID("target"), ref1)
    desc2.putBoolean(sID("group"), kwargs.get('clipped', True))
    desc2.putEnumerated(sID("color"), sID("color"), sID("blue"))
    apply_color(desc3, color)
    desc2.putObject(sID("type"), sID("solidColorLayer"), desc3)
    desc1.putObject(sID("using"), sID("contentLayer"), desc2)
    APP.executeAction(sID("make"), desc1, NO_DIALOG)
    layer = docref.activeLayer
    if not isinstance(layer, ArtLayer):
        raise ValueError(
            "Failed to create a color layer. Active layer is unexpectedly not an ArtLayer."
        )
    if 'blend_mode' in kwargs:
        layer.blendMode = kwargs['blend_mode']
    return layer

class CreateGradientLayerKwargs(TypedDict):
    blend_mode: NotRequired[BlendMode]
    clipped: NotRequired[bool]
    dither: NotRequired[bool]
    rotation: NotRequired[float]
    scale: NotRequired[float]


def create_gradient_layer(
    colors: list[GradientConfig],
    layer: ArtLayer | LayerSet | None,
    docref: Document | None = None,
    **kwargs: Unpack[CreateGradientLayerKwargs]
) -> ArtLayer:
    """Create a gradient adjustment layer.

    Args:
        colors: List of gradient color dicts.
        layer: ArtLayer or LayerSet to make active, if provided.
        docref: Reference Document, use active if not provided.

    Keyword Args:
        blend_mode (BlendMode): Optional blend mode to apply to the new layer.
        clipped (bool): Whether to apply as a clipping mask to the nearest layer, defaults to True.
        dither (bool): Whether to enable dithering for the gradient.
        rotation (Union[int, float]): Rotation to apply to the gradient, defaults to 90.
        scale (Union[int, float]): Scale to apply to the gradient, defaults to 100.

    Returns:
        The new gradient adjustment layer.
    """
    docref = docref or APP.activeDocument
    if layer:
        docref.activeLayer = layer
    desc1 = ActionDescriptor()
    ref1 = ActionReference()
    desc2 = ActionDescriptor()
    desc3 = ActionDescriptor()
    desc4 = ActionDescriptor()
    color_list = ActionList()
    list2 = ActionList()
    desc9 = ActionDescriptor()
    desc10 = ActionDescriptor()
    ref1.putClass(sID("contentLayer"))
    desc1.putReference(sID("target"),  ref1)
    desc2.putBoolean(sID("group"), kwargs.get('clipped', True))
    desc3.putEnumerated(
        sID("gradientsInterpolationMethod"),
        sID("gradientInterpolationMethodType"),
        sID("perceptual")
    )
    desc3.putBoolean(sID("dither"), kwargs.get("dither", True))
    desc3.putUnitDouble(sID("angle"), sID("angleUnit"), kwargs.get('rotation', 0))
    desc3.putEnumerated(sID("type"), sID("gradientType"), sID("linear"))
    desc3.putUnitDouble(sID("scale"), sID("percentUnit"), kwargs.get('scale', 100))
    desc4.putEnumerated(sID("gradientForm"), sID("gradientForm"), sID("customStops"))
    desc4.putDouble(sID("interfaceIconFrameDimmed"),  4096)
    for c in colors:
        add_color_to_gradient(
            color_list,
            get_color(c.get('color', rgb_black())),
            int(c.get('location', 0)),
            int(c.get('midpoint', 50))
        )
    desc4.putList(sID("colors"),  color_list)
    desc9.putUnitDouble(sID("opacity"), sID("percentUnit"),  100)
    desc9.putInteger(sID("location"),  0)
    desc9.putInteger(sID("midpoint"),  50)
    list2.putObject(sID("transferSpec"),  desc9)
    desc10.putUnitDouble(sID("opacity"), sID("percentUnit"),  100)
    desc10.putInteger(sID("location"),  4096)
    desc10.putInteger(sID("midpoint"),  50)
    list2.putObject(sID("transferSpec"),  desc10)
    desc4.putList(sID("transparency"),  list2)
    desc3.putObject(sID("gradient"), sID("gradientClassEvent"),  desc4)
    desc2.putObject(sID("type"), sID("gradientLayer"),  desc3)
    desc1.putObject(sID("using"), sID("contentLayer"),  desc2)
    APP.executeAction(sID("make"), desc1,  NO_DIALOG)
    layer = docref.activeLayer
    if not isinstance(layer, ArtLayer):
        raise ValueError("Failed to create a gradient color layer")
    if 'blend_mode' in kwargs:
        layer.blendMode = kwargs['blend_mode']
    return layer
