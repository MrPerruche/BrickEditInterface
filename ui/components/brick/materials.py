import brickedit


MATERIALS = [  # list[tuple[name, display_name, is_transparent]]
    (brickedit.p.BrickMaterial.ALUMINIUM, "Aluminium", False),
    (brickedit.p.BrickMaterial.BRUSHED_ALUMINIUM, "Brushed Aluminium", False),
    (brickedit.p.BrickMaterial.CARBON, "Carbon", False),
    (brickedit.p.BrickMaterial.RIBBED_ALUMINIUM, "Channelled Aluminium", False),
    (brickedit.p.BrickMaterial.CHROME, "Chrome", False),
    (brickedit.p.BrickMaterial.FROSTED_GLASS, "Frosted Glass", True),
    (brickedit.p.BrickMaterial.CONCRETE, "Concrete", False),
    (brickedit.p.BrickMaterial.COPPER, "Copper", False),
    (brickedit.p.BrickMaterial.FOAM, "Foam", False),
    (brickedit.p.BrickMaterial.GLASS, "Glass", False),
    (brickedit.p.BrickMaterial.GLOW, "Glow", False),
    (brickedit.p.BrickMaterial.GOLD, "Gold", False),
    (brickedit.p.BrickMaterial.LED_MATRIX, "LED Matrix", False),
    (brickedit.p.BrickMaterial.OAK, "Oak", False),
    (brickedit.p.BrickMaterial.PINE, "Pine", False),
    (brickedit.p.BrickMaterial.PLASTIC, "Plastic", False),
    (brickedit.p.BrickMaterial.WEATHERED_WOOD, "Rough Wood", False),
    (brickedit.p.BrickMaterial.RUBBER, "Rubber", False),
    (brickedit.p.BrickMaterial.RUSTED_STEEL, "Rusted Steel", False),
    (brickedit.p.BrickMaterial.STEEL, "Steel", False),
    (brickedit.p.BrickMaterial.TUNGSTEN, "Tungsten", False),
]
OPAQUE_MATERIALS_LIST = [material for material in MATERIALS if not material[2]]
MATERIAL_DISPLAY_NAMES = {name: display_name for name, display_name, _ in MATERIALS}
