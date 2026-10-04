from ui.components.brick_filter.filters.base_filter import FilterMode, FilterResult, BaseFilter
from ui.components.brick_filter.filters.color_filter import ColorFilter
from ui.components.brick_filter.filters.force_all_filter import ForceAllFilter
from ui.components.brick_filter.filters.group_filter import EditorGroupFilter, WeldGroupFilter
from ui.components.brick_filter.filters.property_filter import HasPropertyFilter
from ui.components.brick_filter.filters.property_value_filter import PropertyValueFilter, PropertyComparison
from ui.components.brick_filter.filters.brick_type_filter import BrickTypeFilter
from ui.components.brick_filter.filters.group_membership_filter import GroupMembershipFilter
from ui.components.brick_filter.filters.expression_filter import ExpressionFilter
from ui.components.brick_filter.filters.duplicate_filter import DuplicateFilter, DuplicateMatch
from ui.components.brick_filter.filters.mirror_filter import MirrorFilter, MirrorStatus

filter_classes: list[BaseFilter] = [
    ColorFilter,
    BrickTypeFilter,
    EditorGroupFilter,
    WeldGroupFilter,
    GroupMembershipFilter,
    HasPropertyFilter,
    PropertyValueFilter,
    ExpressionFilter,
    DuplicateFilter,
    MirrorFilter,
    ForceAllFilter
]

# Filters which can be saved (rule presets)
filters_by_config_type: dict[str, type[BaseFilter]] = {
    cls.CONFIG_TYPE: cls for cls in filter_classes if cls.CONFIG_TYPE is not None
}
