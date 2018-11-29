"""Module of commonly use python objects
"""
from docrep import DocstringProcessor

docstrings = DocstringProcessor()


def rgba2rgb(image, color=(255, 255, 255)):
    """Alpha composite an RGBA Image with a specified color.

    Source: http://stackoverflow.com/a/9459208/284318

    Parameters
    ----------
    image: PIL.Image
        The PIL RGBA Image object
    color: tuple
        The rgb color for the background

    Returns
    -------
    PIL.Image
        The rgb image
    """
    from PIL import Image
    image.load()  # needed for split()
    background = Image.new('RGB', image.size, color)
    background.paste(image, mask=image.split()[3])  # 3 is the alpha channel
    return background
