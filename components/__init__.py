"""
Modular Streamlit UI components for Agentic Data Analyst.
"""

from components.dataset_summary import (
    extract_summary_metrics,
    render_dataset_summary,
)
from components.data_preview import (
    filter_preview_data,
    paginate_data,
    render_data_preview,
)
from components.column_selector import (
    classify_columns,
    filter_columns_by_type,
    render_column_select,
    render_column_multiselect,
    render_type_aware_selector,
)
from components.analysis_result import (
    get_health_grade_color,
    get_distribution_badge_info,
    get_correlation_badge_info,
    render_health_grade_badge,
    render_health_score_card,
    render_actionable_warnings,
    render_distribution_badge,
    render_correlation_badge,
)
from components.sidebar import (
    get_supported_file_extensions,
    get_dataset_metadata,
    format_sidebar_badge_html,
    load_dataset_file,
    render_active_dataset_card,
    render_data_source_picker,
    render_sidebar,
)
from components.chart_selector import (
    get_available_chart_types,
    validate_chart_config,
    render_chart_selector,
)
from components.chat_interface import (
    create_chat_message,
    validate_chat_message,
    render_single_message,
    render_chat_history,
    render_chat_empty_state,
    render_chat_interface,
)
from components.auth_ui import (
    render_auth_gate,
    render_user_profile_badge,
)

__all__ = [
    "extract_summary_metrics",
    "render_dataset_summary",
    "filter_preview_data",
    "paginate_data",
    "render_data_preview",
    "classify_columns",
    "filter_columns_by_type",
    "render_column_select",
    "render_column_multiselect",
    "render_type_aware_selector",
    "get_health_grade_color",
    "get_distribution_badge_info",
    "get_correlation_badge_info",
    "render_health_grade_badge",
    "render_health_score_card",
    "render_actionable_warnings",
    "render_distribution_badge",
    "render_correlation_badge",
    "get_supported_file_extensions",
    "get_dataset_metadata",
    "format_sidebar_badge_html",
    "load_dataset_file",
    "render_active_dataset_card",
    "render_data_source_picker",
    "render_sidebar",
    "get_available_chart_types",
    "validate_chart_config",
    "render_chart_selector",
    "create_chat_message",
    "validate_chat_message",
    "render_single_message",
    "render_chat_history",
    "render_chat_empty_state",
    "render_chat_interface",
    "render_auth_gate",
    "render_user_profile_badge",
]



