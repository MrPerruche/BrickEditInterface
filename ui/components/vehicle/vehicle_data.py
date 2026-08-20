import brickedit


BEI_GROUP_ID_PREFIX = 'bei#'
GROUP_ID_LEN_LIMIT = 100
FORBIDDEN_PREFIX = "*"  # Symbol for non user defined groups. User defined groups cannot start with this letter
assert GROUP_ID_LEN_LIMIT >= 13


def get_group_id(raw_str: str) -> str | None:
    """Turns a raw input into the group id OR None if there is no bei group id """
    raw_str = raw_str.strip().rstrip('')
    if not raw_str.startswith(BEI_GROUP_ID_PREFIX):
        return None

    normalized = raw_str[len(BEI_GROUP_ID_PREFIX):].replace('\n', '').replace('\r', '').strip()
    if not normalized:
        return None

    if len(normalized) > GROUP_ID_LEN_LIMIT:
        return normalized[ :GROUP_ID_LEN_LIMIT - 8] + '...' + normalized[-5: ]

    return normalized


def merge_group_id(gid1: str, gid2: str) -> str | None:
    """Merge two group ids and ensure they are under the limit."""
    gid12 = gid1 + ' ' + gid2
    if len(gid12) > GROUP_ID_LEN_LIMIT:
        return gid12[ :GROUP_ID_LEN_LIMIT - 8] + '...' + gid12[-5: ]
    return gid12


class VehicleData:

    def __init__(self, brvfile: brickedit.BRVFile):
        self.brvfile = brvfile

        self.editor_groups: dict[str, list[brickedit.Brick]] = {}
        self.weld_groups: dict[str, list[brickedit.Brick]] = {}
        self.unnamed_editor_groups: list[list[brickedit.Brick]] = []
        self.unnamed_weld_groups: list[list[brickedit.Brick]] = []
        self.not_in_editor_group: list[brickedit.Brick] = []
        self.not_in_weld_group: list[brickedit.Brick] = []
        self.editor_be_to_bei: dict[str, str] = {}
        self.weld_be_to_bei: dict[str, str] = {}

        self.unique_properties: set[str] = set()

        self.load_brvfile(brvfile)


    def load_brvfile(self, brvfile: brickedit.BRVFile):

        editor_grp_to_bricks: dict[str, list[brickedit.Brick]] = {}
        editor_be_to_bei: dict[str, str] = {}
        weld_grp_to_bricks: dict[str, list[brickedit.Brick]] = {}
        weld_be_to_bei: dict[str, str] = {}

        properties = set()

        for brick in brvfile.bricks:

            # GROUPS
            editor, weld = brick.ref.editor, brick.ref.weld

            # Editor
            if editor is not None:
                editor_grp_to_bricks.setdefault(editor, []).append(brick)
                try:
                    text = brick.get_property(brickedit.p.TEXT)
                    gid = get_group_id(text)
                    if gid is not None:
                        if editor in editor_be_to_bei:
                            editor_be_to_bei[editor] = merge_group_id(editor_be_to_bei[editor], gid)
                        else:
                            editor_be_to_bei[editor] = gid
                except brickedit.BrickError:
                    pass

            # Weld
            if weld is not None:
                weld_grp_to_bricks.setdefault(weld, []).append(brick)
                try:
                    text = brick.get_property(brickedit.p.TEXT)
                    gid = get_group_id(text)
                    if gid is not None:
                        if weld in weld_be_to_bei:
                            weld_be_to_bei[weld] = merge_group_id(weld_be_to_bei[weld], gid)
                        else:
                            weld_be_to_bei[weld] = gid
                except brickedit.BrickError:
                    pass

            # PROPERTIES
            # Unknown metas' default properties are blank so we must look at non-default properties (slower)
            if isinstance(brick.meta(), brickedit.p.UnknownPropertyMeta):
                properties.update(brick.get_all_properties().keys())
            else:
                properties.update(brick.meta().p.keys())

        # Merge changes
        self.unique_properties = properties

        self.editor_groups = {editor_be_to_bei[be_group]: bricklist for be_group, bricklist in editor_grp_to_bricks.items() if be_group in editor_be_to_bei}
        self.weld_groups = {weld_be_to_bei[be_group]: bricklist for be_group, bricklist in weld_grp_to_bricks.items() if be_group in weld_be_to_bei}

        self.unnamed_editor_groups = [bricklist for be_group, bricklist in editor_grp_to_bricks.items() if be_group not in editor_be_to_bei]
        self.unnamed_weld_groups = [bricklist for be_group, bricklist in weld_grp_to_bricks.items() if be_group not in weld_be_to_bei]

        self.not_in_editor_group = [brick for brick in brvfile.bricks if brick.ref.editor is None]
        self.not_in_weld_group = [brick for brick in brvfile.bricks if brick.ref.weld is None]

        self.editor_be_to_bei = editor_be_to_bei
        self.weld_be_to_bei = weld_be_to_bei
