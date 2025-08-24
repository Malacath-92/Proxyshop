"""
* Helpers: Documents
"""
# Standard Library Imports
from pathlib import Path
from typing import Any
from collections.abc import Callable

# Third Party Imports
from photoshop.api import (
    DialogModes,
    ActionDescriptor,
    ActionReference,
    SaveOptions,
    PurgeTarget,
    PNGSaveOptions,
    JPEGSaveOptions,
    PhotoshopSaveOptions,
    ElementPlacement,
    FormatOptionsType
)
from photoshop.api._artlayer import ArtLayer
from photoshop.api._layerSet import LayerSet
from photoshop.api._document import Document

# Local Imports
from src import APP
from src.helpers.layers import create_new_layer
from src.utils.adobe import PS_EXCEPTIONS

# QOL Definitions
sID, cID = APP.stringIDToTypeID, APP.charIDToTypeID
NO_DIALOG = DialogModes.DisplayNoDialogs

"""
* Document Hierarchy
"""


def get_leaf_layers(group: Document | LayerSet | None = None) -> list[ArtLayer]:
    """Utility function to generate a list of leaf layers in a LayerSet or document.

    Args:
        group: Group to grab leaf layers from.

    Returns:
        A list of leaf layers in a LayerSet or document.
    """
    if not group:
        group = APP.activeDocument
    layers = [node for node in group.artLayers]
    for g in group.layerSets:
        layers.extend(get_leaf_layers(g))
    return layers

ArtLayerTree = dict[str, "ArtLayer | ArtLayerTree"]

def get_layer_tree(group: Document | LayerSet | None = None) -> ArtLayerTree:
    """Composes a dictionary tree of layers in the active document or a specific LayerSet.

    Args:
        group: A specific group to create a dictionary tree for.

    Returns:
        A dictionary tree comprised of all the layers in a document or group.
    """
    if not group:
        group = APP.activeDocument
    layers: ArtLayerTree = {layer.name: layer for layer in group.artLayers}
    for g in group.layerSets:
        layers[g.name] = get_layer_tree(g)
    return layers


"""
* Importing Files
"""


def import_art(
    layer: ArtLayer,
    path: str | Path,
    name: str = 'Layer 1',
    docref: Document | None = None
) -> ArtLayer:
    """Imports an art file into the active layer.

    Args:
        layer: Layer to make active and receive image.
        path: Image file to import.
        name: Name of the new layer.
        docref: Reference document if provided, otherwise use active.

    Returns:
        Imported art layer.
    """
    desc = ActionDescriptor()
    docref = docref or APP.activeDocument
    docref.activeLayer = layer
    desc.putPath(sID('target'), str(path))
    APP.executeAction(sID('placeEvent'), desc)

    active_layer = docref.activeLayer
    if not isinstance(active_layer, ArtLayer):
        raise ValueError("Failed to import art. Active layer is unexpectedly not an ArtLayer.")
    active_layer.name = name

    return active_layer


def import_svg(
    path: str | Path,
    ref: ArtLayer | LayerSet | None = None,
    placement: ElementPlacement | None = None,
    docref: Document | None = None
) -> ArtLayer:
    """Imports an SVG image, then moves it if needed.

    Args:
        path: SVG file to import.
        ref: Reference used to move layer.
        placement: Placement based on the reference.
        docref: Reference document if provided, otherwise use active.

    Returns:
        Imported SVG layer.
    """
    # Import the art
    desc = ActionDescriptor()
    docref = docref or APP.activeDocument
    desc.putPath(sID('target'), str(path))
    APP.executeAction(sID('placeEvent'), desc)

    active_layer = docref.activeLayer
    if not isinstance(active_layer, ArtLayer):
        raise ValueError("Failed to import SVG. Active layer is unexpectedly a LayerSet.")

    # Position the layer if needed
    if ref and placement:
        active_layer.move(ref, placement)
    return active_layer


def paste_file(
    layer: ArtLayer,
    path: str | Path,
    action: Callable[[], Any] | None = None,
    docref: Document | None = None
) -> ArtLayer:
    """Pastes the given file into the specified layer.

    Args:
        layer: Layer object to paste the image into.
        path: Filepath of the image to open.
        action: Optional action function to call on the image before importing it.
        action_args: Optional arguments to pass to the action function.
        docref: Reference document if provided, otherwise use active.

    Returns:
        Active layer where art was pasted.
    """
    # Select the correct layer, then load the file
    docref = docref or APP.activeDocument
    docref.activeLayer = layer
    APP.load(str(path))

    # Optionally run action on art before importing it
    if action:
        action()

    # Select the entire image, copy it, and close the file
    newdoc = APP.activeDocument
    docsel = newdoc.selection
    docsel.selectAll()
    docsel.copy()
    newdoc.close(
        SaveOptions.DoNotSaveChanges)

    # Paste the image into the specific layer
    docref.paste()

    active_layer = docref.activeLayer
    if not isinstance(active_layer, ArtLayer):
        raise ValueError("Failed to paste file. Active layer is unexpectedly not an ArtLayer.")

    return active_layer


def import_art_into_new_layer(
    path: str | Path,
    name: str = "New Layer",
    docref: Document | None = None
) -> ArtLayer:
    """Creates a new layer and imports a given art into that layer.

    Args:
        path: Image file to import, must have a valid image extension.
        name: Chosen name of the new layer.
        docref: Reference document if provided, otherwise use active.

    Returns:
        New ArtLayer with imported art.
    """
    return import_art(
        layer=create_new_layer(name),
        path=path,
        name=name,
        docref=docref)


"""
* Document History State
"""


def jump_to_history_state(position: int):
    """Jump to a position in the history state relative to its current position.
        2 moves forward two, -2 moves backwards two.

    Args:
        position: Integer value determining how far ahead or behind in the state to move.
    """
    desc1 = ActionDescriptor()
    ref1 = ActionReference()
    ref1.putOffset(sID('historyState'),  position)
    desc1.putReference(sID('target'),  ref1)
    APP.executeAction(sID('select'), desc1,  NO_DIALOG)


def toggle_history_state(direction: str = 'previous') -> None:
    """Alter the history state.

    Args:
        direction: Direction to move the history state ("previous" or "next").
    """
    desc1 = ActionDescriptor()
    ref1 = ActionReference()
    ref1.putEnumerated(sID('historyState'), sID('ordinal'), sID(direction))
    desc1.putReference(sID('target'), ref1)
    APP.executeAction(sID('select'), desc1, NO_DIALOG)


def undo_action() -> None:
    """Undo the last action in the history state."""
    toggle_history_state('previous')


def redo_action() -> None:
    """Redo the last action undone in the history state."""
    toggle_history_state('next')


def reset_document(docref: Document | None = None) -> None:
    """Reset to the history state to when document was first opened.

    Args:
        docref: Reference document to reset state in, use active if not provided.
    """
    docref = docref or APP.activeDocument
    d1, r1 = ActionDescriptor(), ActionReference()
    r1.putName(sID('snapshotClass'), docref.name)
    d1.putReference(sID('target'), r1)
    APP.executeAction(sID('select'), d1, NO_DIALOG)


"""
* Conversion Utilities
"""


def points_to_pixels(number: int | float, docref: Document | None = None) -> float:
    """Converts a given number in point units to pixel units.

    Args:
        number: Number represented in point units.
        docref: Document to reference, use active if not provided.

    Returns:
        Float representing the given value in pixel units.
    """
    docref = docref or APP.activeDocument
    return (docref.resolution / 72) * number


def pixels_to_points(number: int | float, docref: Document | None = None) -> float:
    """Converts a given number in pixel units to point units.

    Args:
        number: Number represented in pixel units.
        docref: Document to reference, use active if not provided.

    Returns:
        Float representing the given value in point units.
    """
    docref = docref or APP.activeDocument
    return number / (docref.resolution / 72)


"""
* Active Document Utils
"""


def check_active_document() -> bool:
    """Checks if there are any active documents loaded in Photoshop.

    Returns:
        True if exists, otherwise False.
    """
    try:
        if APP.documents.length > 0:
            return True
    except PS_EXCEPTIONS:
        pass
    return False


def get_document(name: str) -> Document | None:
    """Check if a Photoshop Document has been loaded.

    Args:
        name: Filename of the document.

    Returns:
        The Document if located, None if missing.
    """
    try:
        doc = APP.documents[name]
        APP.activeDocument = doc
        return doc
    except PS_EXCEPTIONS:
        return


"""
* Resize Document
"""


def trim_transparent_pixels() -> None:
    """Trim transparent pixels from Photoshop document."""
    desc258 = ActionDescriptor()
    desc258.putEnumerated(sID('trimBasedOn'), sID('trimBasedOn'), sID('transparency'))
    desc258.putBoolean(sID('top'), True)
    desc258.putBoolean(sID('bottom'), True)
    desc258.putBoolean(sID('left'), True)
    desc258.putBoolean(sID('right'), True)
    APP.executeAction(sID('trim'), desc258, NO_DIALOG)


"""
* Saving
"""


def save_document_png(path: Path, docref: Document | None = None) -> None:
    """Save the current document as a PNG.

    Args:
        path: Path to save the PNG file.
        docref: Current active document. Use active if not provided.
    """
    docref = docref or APP.activeDocument
    png_options = PNGSaveOptions()
    png_options.compression = 3
    png_options.interlaced = False
    docref.saveAs(
        file_path=str(path.with_suffix('.png')),
        options=png_options,
        asCopy=True)


def save_document_jpeg(path: Path, docref: Document | None = None, optimize: bool = True) -> None:
    """Save the current document as a JPEG.

    Args:
        path: Path to save the JPEG file.
        optimize: Whether to save with "Optimize Baseline". Reduces file size, but
            may cause an error on older versions of Photoshop.
        docref: Current active document. Use active if not provided.
    """

    # Set up the save options
    docref = docref or APP.activeDocument
    options = JPEGSaveOptions(quality=12)
    try:

        # Reduces filesize, unsupported by older Photoshop versions
        if optimize:
            options.formatOptions = FormatOptionsType.OptimizedBaseline

        # Save the document
        docref.saveAs(
            file_path=str(path.with_suffix('.jpg')),
            options=options,
            asCopy=True)

    # Retry without Optimize Baseline
    except PS_EXCEPTIONS as e:
        if optimize:
            return save_document_jpeg(
                path=path,
                optimize=False,
                docref=docref)
        raise OSError from e


def save_document_psd(path: Path, docref: Document | None = None) -> None:
    """Save the current document as a PSD.

    Args:
        path: Path to save the PSD file.
        docref: Open Photoshop document. Use active if not provided.
    """
    docref = docref or APP.activeDocument
    docref.saveAs(
        file_path=str(path.with_suffix('.psd')),
        options=PhotoshopSaveOptions(),
        asCopy=True)


def save_document_psb(path: Path) -> None:
    """Save the current document as a PSB.

    Args:
        path: Path to save the PSB file.
        _args: Ignored args used by similar methods but not here.
        _kwargs: Ignored kwargs used by similar methods but not here.
    """
    d1 = ActionDescriptor()
    d2 = ActionDescriptor()
    d2.putBoolean(sID('maximizeCompatibility'), True)
    d1.putObject(sID('as'), sID('largeDocumentFormat'), d2)
    d1.putPath(sID('in'), str(path.with_suffix('.psb')))
    d1.putBoolean(sID('lowerCase'), True)
    APP.executeAction(sID('save'), d1, NO_DIALOG)


def close_document(save: bool = False, docref: Document | None = None, purge: bool = True) -> None:
    """Close the active document.

    Args:
        save: Whether to save changes to the document before closing.
        docref: Open Photoshop document. Use active if not provided.
        purge: Whether to purge all caches.
    """
    docref = docref or APP.activeDocument
    save_options = SaveOptions.SaveChanges if save else SaveOptions.DoNotSaveChanges
    docref.close(saving=save_options)
    if purge:
        APP.purge(PurgeTarget.AllCaches)


"""
* Rotation
"""


def rotate_document(angle: int) -> None:
    """Rotate the document.

    Returns:
        angle: Angle to rotate the document.
    """
    desc1 = ActionDescriptor()
    ref1 = ActionReference()
    ref1.putEnumerated(sID('document'), sID('ordinal'), sID('first'))
    desc1.putReference(sID('target'), ref1)
    desc1.putUnitDouble(sID('angle'), sID('angleUnit'), angle)
    APP.executeAction(sID('rotateEventEnum'), desc1, NO_DIALOG)


def rotate_counter_clockwise() -> None:
    """Utility definition for rotating 90 degrees counter-clockwise."""
    rotate_document(-90)


def rotate_clockwise() -> None:
    """Utility definition for rotating 90 degrees clockwise."""
    rotate_document(90)


def rotate_full() -> None:
    """Utility definition for rotating a full 180 degrees."""
    rotate_document(180)


"""
* Copy / Paste
"""


def paste_to_document(layer: ArtLayer | LayerSet | None = None):
    """Paste current clipboard to the current layer.

    Args:
        layer: Layer to make active, if provided.
    """
    if layer:
        APP.activeDocument.activeLayer = layer
    desc1 = ActionDescriptor()
    desc1.putEnumerated(sID("antiAlias"), sID("antiAliasType"), sID("antiAliasNone"))
    desc1.putClass(sID("as"), sID("pixel"))
    APP.executeAction(sID("paste"), desc1, NO_DIALOG)
