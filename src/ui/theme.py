"""
LOG NEST - Professional Windows Desktop Theme & Styles
Dark graphite and charcoal aesthetic with muted blue accents,
clean Segoe UI typography, and subtle borders.
"""

# ─── Color Palette (Dark Graphite & Charcoal) ───────────────────────────────
COLORS = {
    # Backgrounds - Dark Graphite & Charcoal (Windows Modern Dark)
    "bg_darkest":     "#18181B",  # Main canvas background
    "bg_dark":        "#1F1F23",  # Sidebar, dialogs, headers
    "bg_medium":      "#27272A",  # Inputs, controls, panels
    "bg_light":       "#303036",  # Elevated interactive surfaces
    "bg_lighter":     "#3B3B42",  # Active chips, subtle hover
    "bg_card":        "#222226",  # Cards (flat, clean, solid)
    "bg_hover":       "#2B2B30",  # Hover

    # Accent colors - Muted Windows Blue (No excessive purple or neon)
    "accent_primary":    "#2563EB",  # Professional Desktop Blue
    "accent_secondary":  "#38BDF8",  # Muted Sky Blue
    "accent_tertiary":   "#94A3B8",  # Slate
    "accent_blue":       "#60A5FA",  # Soft Blue
    "accent_orange":     "#F59E0B",  # Muted Amber

    # Text - Clean Neutral Slate
    "text_primary":   "#F8FAFC",  # Off-white primary text
    "text_secondary": "#94A3B8",  # Slate gray secondary text
    "text_muted":     "#64748B",  # Muted metadata
    "text_accent":    "#60A5FA",  # Accent label

    # Severity - Refined Status Colors
    "severity_info":     "#38BDF8",
    "severity_warning":  "#F59E0B",
    "severity_error":    "#EF4444",
    "severity_critical": "#DC2626",

    # Category - Clean Muted Identity
    "cat_application": "#3B82F6",  # Blue
    "cat_filesystem":  "#10B981",  # Emerald
    "cat_system":      "#64748B",  # Slate
    "cat_crash":       "#EF4444",  # Red

    # Borders - Subtle, 1px Windows Flat Lines
    "border":         "#2E2E35",
    "border_light":   "#3F3F46",

    # Scrollbar
    "scrollbar_bg":     "#18181B",
    "scrollbar_handle": "#3F3F46",
    "scrollbar_hover":  "#52525B",
}


def get_main_stylesheet():
    """Return the main application stylesheet."""
    c = COLORS
    return f"""
    /* ─── Global ─────────────────────────────────────────────── */
    QWidget {{
        background-color: {c['bg_darkest']};
        color: {c['text_primary']};
        font-family: 'Segoe UI Variable Text', 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif;
        font-size: 13px;
    }}

    /* ─── Main Window ────────────────────────────────────────── */
    QMainWindow {{
        background-color: {c['bg_darkest']};
    }}

    /* ─── Sidebar ────────────────────────────────────────────── */
    #sidebar {{
        background-color: {c['bg_dark']};
        border-right: 1px solid {c['border']};
        min-width: 220px;
        max-width: 220px;
    }}

    #sidebarTitle {{
        color: {c['text_primary']};
        font-size: 15px;
        font-weight: 700;
        letter-spacing: 0.5px;
        padding: 0px;
    }}

    #sidebarSubtitle {{
        color: {c['text_muted']};
        font-size: 11px;
        font-weight: 500;
        padding: 0px;
    }}

    QPushButton.nav-button {{
        background-color: transparent;
        color: {c['text_secondary']};
        border: none;
        border-radius: 6px;
        padding: 9px 14px;
        text-align: left;
        font-size: 13px;
        font-weight: 500;
        margin: 1px 8px;
    }}

    QPushButton.nav-button:hover {{
        background-color: {c['bg_medium']};
        color: {c['text_primary']};
    }}

    QPushButton.nav-button[active="true"] {{
        background-color: {c['bg_medium']};
        color: {c['text_primary']};
        border-left: 3px solid {c['accent_primary']};
        border-radius: 4px;
        font-weight: 600;
    }}

    /* ─── Cards ──────────────────────────────────────────────── */
    QFrame.card {{
        background-color: {c['bg_card']};
        border: 1px solid {c['border']};
        border-radius: 8px;
        padding: 14px;
    }}

    QFrame.stat-card {{
        background-color: {c['bg_card']};
        border: 1px solid {c['border']};
        border-radius: 8px;
        padding: 12px 14px;
    }}

    /* ─── Search Bar & Inputs ────────────────────────────────── */
    QLineEdit {{
        background-color: {c['bg_medium']};
        color: {c['text_primary']};
        border: 1px solid {c['border']};
        border-radius: 6px;
        padding: 8px 12px;
        font-size: 13px;
        selection-background-color: {c['accent_primary']};
    }}

    QLineEdit:focus {{
        border: 1px solid {c['accent_primary']};
        background-color: {c['bg_card']};
    }}

    QLineEdit::placeholder {{
        color: {c['text_muted']};
    }}

    /* ─── Buttons ────────────────────────────────────────────── */
    QPushButton {{
        background-color: {c['bg_medium']};
        color: {c['text_primary']};
        border: 1px solid {c['border']};
        border-radius: 6px;
        padding: 6px 14px;
        font-weight: 500;
        font-size: 13px;
    }}

    QPushButton:hover {{
        background-color: {c['bg_light']};
        border-color: {c['border_light']};
    }}

    QPushButton:pressed {{
        background-color: {c['bg_medium']};
    }}

    QPushButton.primary {{
        background-color: {c['accent_primary']};
        color: white;
        border: 1px solid {c['accent_primary']};
        font-weight: 600;
    }}

    QPushButton.primary:hover {{
        background-color: #1D4ED8;
        border-color: #1D4ED8;
    }}

    QPushButton.danger {{
        background-color: {c['severity_error']};
        color: white;
        border: none;
        font-weight: 600;
    }}

    QPushButton.danger:hover {{
        background-color: #DC2626;
    }}

    /* ─── ComboBox ───────────────────────────────────────────── */
    QComboBox {{
        background-color: {c['bg_medium']};
        color: {c['text_primary']};
        border: 1px solid {c['border']};
        border-radius: 6px;
        padding: 6px 10px;
        min-width: 110px;
        font-size: 13px;
    }}

    QComboBox:hover {{
        border-color: {c['border_light']};
    }}

    QComboBox::drop-down {{
        border: none;
        width: 20px;
    }}

    QComboBox::down-arrow {{
        image: none;
        border: none;
    }}

    QComboBox QAbstractItemView {{
        background-color: {c['bg_dark']};
        color: {c['text_primary']};
        border: 1px solid {c['border']};
        border-radius: 6px;
        selection-background-color: {c['accent_primary']};
        selection-color: white;
        padding: 4px;
    }}

    /* ─── Scrollbars ─────────────────────────────────────────── */
    QScrollBar:vertical {{
        background-color: transparent;
        width: 8px;
        border: none;
        margin: 2px;
    }}

    QScrollBar::handle:vertical {{
        background-color: {c['scrollbar_handle']};
        border-radius: 4px;
        min-height: 24px;
    }}

    QScrollBar::handle:vertical:hover {{
        background-color: {c['scrollbar_hover']};
    }}

    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}

    QScrollBar:horizontal {{
        background-color: transparent;
        height: 8px;
        border: none;
        margin: 2px;
    }}

    QScrollBar::handle:horizontal {{
        background-color: {c['scrollbar_handle']};
        border-radius: 4px;
        min-width: 24px;
    }}

    QScrollBar::handle:horizontal:hover {{
        background-color: {c['scrollbar_hover']};
    }}

    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
        width: 0px;
    }}

    /* ─── Labels ─────────────────────────────────────────────── */
    QLabel.page-title {{
        color: {c['text_primary']};
        font-size: 20px;
        font-weight: 700;
    }}

    QLabel.section-title {{
        color: {c['text_primary']};
        font-size: 15px;
        font-weight: 600;
    }}

    QLabel.stat-value {{
        color: {c['text_primary']};
        font-size: 24px;
        font-weight: 700;
    }}

    QLabel.stat-label {{
        color: {c['text_secondary']};
        font-size: 11px;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }}

    QLabel.text-muted {{
        color: {c['text_muted']};
    }}

    QLabel.text-secondary {{
        color: {c['text_secondary']};
    }}

    /* ─── Tab Widget ─────────────────────────────────────────── */
    QTabWidget::pane {{
        border: none;
        background-color: transparent;
    }}

    QTabBar::tab {{
        background-color: transparent;
        color: {c['text_muted']};
        border: none;
        border-bottom: 2px solid transparent;
        padding: 8px 16px;
        font-size: 13px;
        font-weight: 500;
    }}

    QTabBar::tab:selected {{
        color: {c['accent_primary']};
        border-bottom: 2px solid {c['accent_primary']};
        font-weight: 600;
    }}

    QTabBar::tab:hover {{
        color: {c['text_primary']};
    }}

    /* ─── CheckBox ───────────────────────────────────────────── */
    QCheckBox {{
        color: {c['text_primary']};
        spacing: 8px;
        font-size: 13px;
    }}

    QCheckBox::indicator {{
        width: 16px;
        height: 16px;
        border-radius: 4px;
        border: 1px solid {c['border_light']};
        background-color: {c['bg_medium']};
    }}

    QCheckBox::indicator:checked {{
        background-color: {c['accent_primary']};
        border-color: {c['accent_primary']};
    }}

    /* ─── SpinBox ────────────────────────────────────────────── */
    QSpinBox {{
        background-color: {c['bg_medium']};
        color: {c['text_primary']};
        border: 1px solid {c['border']};
        border-radius: 6px;
        padding: 6px 8px;
    }}

    /* ─── DateEdit ───────────────────────────────────────────── */
    QDateEdit, QDateTimeEdit {{
        background-color: {c['bg_medium']};
        color: {c['text_primary']};
        border: 1px solid {c['border']};
        border-radius: 6px;
        padding: 6px 10px;
    }}

    QDateEdit:focus, QDateTimeEdit:focus {{
        border-color: {c['accent_primary']};
    }}

    QCalendarWidget {{
        background-color: {c['bg_dark']};
    }}

    /* ─── ToolTip ────────────────────────────────────────────── */
    QToolTip {{
        background-color: {c['bg_dark']};
        color: {c['text_primary']};
        border: 1px solid {c['border_light']};
        border-radius: 4px;
        padding: 4px 8px;
        font-size: 12px;
    }}

    /* ─── Status Bar ─────────────────────────────────────────── */
    QStatusBar {{
        background-color: {c['bg_dark']};
        color: {c['text_muted']};
        border-top: 1px solid {c['border']};
        font-size: 11px;
        padding: 3px 6px;
    }}

    /* ─── Group Box ──────────────────────────────────────────── */
    QGroupBox {{
        background-color: {c['bg_card']};
        border: 1px solid {c['border']};
        border-radius: 8px;
        margin-top: 14px;
        padding-top: 20px;
        font-weight: 600;
    }}

    QGroupBox::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding: 2px 10px;
        color: {c['text_primary']};
        font-size: 13px;
    }}

    /* ─── Progress Bar ───────────────────────────────────────── */
    QProgressBar {{
        background-color: {c['bg_medium']};
        border: none;
        border-radius: 3px;
        height: 6px;
        text-align: center;
    }}

    QProgressBar::chunk {{
        background-color: {c['accent_primary']};
        border-radius: 3px;
    }}

    /* ─── Menu ───────────────────────────────────────────────── */
    QMenu {{
        background-color: {c['bg_dark']};
        color: {c['text_primary']};
        border: 1px solid {c['border_light']};
        border-radius: 6px;
        padding: 4px;
    }}

    QMenu::item {{
        padding: 6px 18px;
        border-radius: 4px;
    }}

    QMenu::item:selected {{
        background-color: {c['bg_medium']};
        color: {c['text_primary']};
    }}

    QMenu::separator {{
        height: 1px;
        background-color: {c['border']};
        margin: 4px 6px;
    }}
    """


def severity_badge_style(severity):
    """Get inline style for a severity badge."""
    c = COLORS
    color_map = {
        "info": c["severity_info"],
        "warning": c["severity_warning"],
        "error": c["severity_error"],
        "critical": c["severity_critical"],
    }
    color = color_map.get(severity, c["severity_info"])
    return (
        f"background-color: {color}18; color: {color}; "
        f"border: 1px solid {color}33; border-radius: 4px; "
        f"padding: 2px 6px; font-size: 11px; font-weight: 600;"
    )


def category_color(category):
    """Get the color for a category."""
    c = COLORS
    return {
        "Application": c["cat_application"],
        "FileSystem": c["cat_filesystem"],
        "System": c["cat_system"],
        "Crash": c["cat_crash"],
    }.get(category, c["text_muted"])
