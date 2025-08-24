"""
* Helpers: PS Object Descriptors
"""
# Standard Library Imports

# Third Party Imports
from photoshop.api import ActionDescriptor, DialogModes, ActionReference
from photoshop.api._artlayer import ArtLayer
from photoshop.api._layerSet import LayerSet

# Local Imports
from src import APP

# QOL Definitions
sID, cID = APP.stringIDToTypeID, APP.charIDToTypeID
NO_DIALOG = DialogModes.DisplayNoDialogs

"""
* Layer Action Descriptors
"""


def get_layer_action_descriptor(layer: ArtLayer | LayerSet) -> ActionDescriptor:
    """Gets action descriptor info object using layer as a reference.

    Args:
        layer: Layer or layer group to get action descriptor info for.

    Returns:
        Action descriptor info object about the layer.
    """
    ref = ActionReference()
    ref.putIdentifier(sID('layer'), layer.id)
    return APP.executeActionGet(ref)
