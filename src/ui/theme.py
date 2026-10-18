"""
LOG NEST - Dark Theme & Styles
Premium dark theme with glassmorphism-inspired design and accent colors.
"""

# ─── Color Palette ───────────────────────────────────────────────────────────
COLORS = {
    # Backgrounds
    "bg_darkest":     "#0A0E17",
    "bg_dark":        "#0F1923",
    "bg_medium":      "#162032",
    "bg_light":       "#1C2940",
    "bg_lighter":     "#243350",
    "bg_card":        "#141E2E",
    "bg_hover":       "#1E3050",

    # Accent colors
    "accent_primary":    "#6C63FF",  # Purple
    "accent_secondary":  "#00D4AA",  # Teal/Green
    "accent_tertiary":   "#FF6B8A",  # Pink
    "accent_blue":       "#4FC3F7",  # Light blue
    "accent_orange":     "#FFB74D",  # Orange

    # Text
    "text_primary":   "#E8EDF5",
    "text_secondary": "#8B9DC3",
    "text_muted":     "#5A6E8A",
    "text_accent":    "#6C63FF",

    # Severity
    "severity_info":     "#4FC3F7",
    "severity_warning":  "#FFB74D",
    "severity_error":    "#EF5350",
    "severity_critical": "#FF1744",

    # Category
    "cat_application": "#6C63FF",
    "cat_filesystem":  "#00D4AA",
    "cat_system":      "#4FC3F7",
    "cat_crash":       "#FF1744",

    # Borders
    "border":         "#1E3050",
    "border_light":   "#2A3F5F",

    # Scrollbar
    "scrollbar_bg":     "#0F1923",
    "scrollbar_handle": "#2A3F5F",
    "scrollbar_hover":  "#3A5070",
}


def get_main_stylesheet():
    """Return the main application stylesheet."""
    c = COLORS
    return f"""
    /* ─── Global ─────────────────────────────────────────────── */
    QWidget {{
        background-color: {c['bg_darkest']};
        color: {c['text_primary']};
        font-family: 'Segoe UI', 'Inter', 'Roboto', sans-serif;
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
        color: {c['accent_primary']};
        font-size: 20px;
        font-weight: bold;
        padding: 20px 16px 8px 16px;
    }}

    #sidebarSubtitle {{
        color: {c['text_muted']};
        font-size: 11px;
        padding: 0px 16px 20px 16px;
    }}

    QPushButton.nav-button {{
        background-color: transparent;
        color: {c['text_secondary']};
        border: none;
        border-radius: 8px;
        padding: 12px 16px;
        text-align: left;
        font-size: 14px;
        font-weight: 500;
        margin: 2px 8px;
    }}

    QPushButton.nav-button:hover {{
        background-color: {c['bg_hover']};
        color: {c['text_primary']};
    }}

    QPushButton.nav-button[active="true"] {{
        background-color: {c['accent_primary']};
        color: white;
    }}

    /* ─── Cards ──────────────────────────────────────────────── */
    QFrame.card {{
        background-color: {c['bg_card']};
        border: 1px solid {c['border']};
        border-radius: 12px;
        padding: 16px;
    }}

    QFrame.stat-card {{
        background-color: {c['bg_card']};
        border: 1px solid {c['border']};
        border-radius: 12px;
        padding: 20px;
        min-height: 100px;
    }}

    /* ─── Search Bar ─────────────────────────────────────────── */
    QLineEdit {{
        background-color: {c['bg_medium']};
        color: {c['text_primary']};
        border: 1px solid {c['border']};
        border-radius: 8px;
        padding: 10px 14px;
        font-size: 14px;
        selection-background-color: {c['accent_primary']};
    }}

    QLineEdit:focus {{
        border: 1px solid {c['accent_primary']};
    }}

    QLineEdit::placeholder {{
        color: {c['text_muted']};
    }}

    /* ─── Buttons ────────────────────────────────────────────── */
    QPushButton {{
        background-color: {c['bg_light']};
        color: {c['text_primary']};
        border: 1px solid {c['border']};
        border-radius: 8px;
        padding: 8px 16px;
        font-weight: 500;
        font-size: 13px;
    }}

    QPushButton:hover {{
        background-color: {c['bg_lighter']};
        border-color: {c['border_light']};
    }}

    QPushButton:pressed {{
        background-color: {c['bg_medium']};
    }}

    QPushButton.primary {{
        background-color: {c['accent_primary']};
        color: white;
        border: none;
    }}

    QPushButton.primary:hover {{
        background-color: #7B73FF;
    }}

    QPushButton.danger {{
        background-color: {c['severity_error']};
        color: white;
        border: none;
    }}

    /* ─── ComboBox ───────────────────────────────────────────── */
    QComboBox {{
        background-color: {c['bg_medium']};
        color: {c['text_primary']};
        border: 1px solid {c['border']};
        border-radius: 8px;
        padding: 8px 12px;
        min-width: 120px;
        font-size: 13px;
    }}

    QComboBox:hover {{
        border-color: {c['border_light']};
    }}

    QComboBox::drop-down {{
        border: none;
        width: 24px;
    }}

    QComboBox::down-arrow {{
        image: none;
        border: none;
    }}

    QComboBox QAbstractItemView {{
        background-color: {c['bg_medium']};
        color: {c['text_primary']};
        border: 1px solid {c['border']};
        border-radius: 4px;
        selection-background-color: {c['accent_primary']};
        selection-color: white;
        padding: 4px;
    }}

    /* ─── Scrollbars ─────────────────────────────────────────── */
    QScrollBar:vertical {{
        background-color: {c['scrollbar_bg']};
        width: 10px;
        border: none;
        border-radius: 5px;
        margin: 2px;
    }}

    QScrollBar::handle:vertical {{
        background-color: {c['scrollbar_handle']};
        border-radius: 5px;
        min-height: 30px;
    }}

    QScrollBar::handle:vertical:hover {{
        background-color: {c['scrollbar_hover']};
    }}

    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}

    QScrollBar:horizontal {{
        background-color: {c['scrollbar_bg']};
        height: 10px;
        border: none;
        border-radius: 5px;
        margin: 2px;
    }}

    QScrollBar::handle:horizontal {{
        background-color: {c['scrollbar_handle']};
        border-radius: 5px;
        min-width: 30px;
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
        font-size: 24px;
        font-weight: bold;
    }}

    QLabel.section-title {{
        color: {c['text_primary']};
        font-size: 16px;
        font-weight: 600;
    }}

    QLabel.stat-value {{
        color: {c['text_primary']};
        font-size: 32px;
        font-weight: bold;
    }}

    QLabel.stat-label {{
        color: {c['text_secondary']};
        font-size: 12px;
        font-weight: 500;
        text-transform: uppercase;
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
        padding: 10px 20px;
        font-size: 13px;
        font-weight: 500;
    }}

    QTabBar::tab:selected {{
        color: {c['accent_primary']};
        border-bottom: 2px solid {c['accent_primary']};
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
        width: 18px;
        height: 18px;
        border-radius: 4px;
        border: 2px solid {c['border_light']};
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
        border-radius: 8px;
        padding: 6px 10px;
    }}

    /* ─── DateEdit ───────────────────────────────────────────── */
    QDateEdit, QDateTimeEdit {{
        background-color: {c['bg_medium']};
        color: {c['text_primary']};
        border: 1px solid {c['border']};
        border-radius: 8px;
        padding: 8px 12px;
    }}

    QDateEdit:focus, QDateTimeEdit:focus {{
        border-color: {c['accent_primary']};
    }}

    QCalendarWidget {{
        background-color: {c['bg_dark']};
    }}

    /* ─── ToolTip ────────────────────────────────────────────── */
    QToolTip {{
        background-color: {c['bg_medium']};
        color: {c['text_primary']};
        border: 1px solid {c['border']};
        border-radius: 6px;
        padding: 6px 10px;
        font-size: 12px;
    }}

    /* ─── Splitter ───────────────────────────────────────────── */
    QSplitter::handle {{
        background-color: {c['border']};
    }}

    /* ─── Status Bar ─────────────────────────────────────────── */
    QStatusBar {{
        background-color: {c['bg_dark']};
        color: {c['text_muted']};
        border-top: 1px solid {c['border']};
        font-size: 11px;
        padding: 4px;
    }}

    /* ─── Group Box ──────────────────────────────────────────── */
    QGroupBox {{
        background-color: {c['bg_card']};
        border: 1px solid {c['border']};
        border-radius: 8px;
        margin-top: 16px;
        padding-top: 24px;
        font-weight: 600;
    }}

    QGroupBox::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding: 4px 12px;
        color: {c['text_primary']};
    }}

    /* ─── Progress Bar ───────────────────────────────────────── */
    QProgressBar {{
        background-color: {c['bg_medium']};
        border: none;
        border-radius: 4px;
        height: 6px;
        text-align: center;
    }}

    QProgressBar::chunk {{
        background-color: {c['accent_primary']};
        border-radius: 4px;
    }}

    /* ─── Menu ───────────────────────────────────────────────── */
    QMenu {{
        background-color: {c['bg_medium']};
        color: {c['text_primary']};
        border: 1px solid {c['border']};
        border-radius: 8px;
        padding: 4px;
    }}

    QMenu::item {{
        padding: 8px 20px;
        border-radius: 4px;
    }}

    QMenu::item:selected {{
        background-color: {c['accent_primary']};
        color: white;
    }}

    QMenu::separator {{
        height: 1px;
        background-color: {c['border']};
        margin: 4px 8px;
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
        f"background-color: {color}22; color: {color}; "
        f"border: 1px solid {color}44; border-radius: 4px; "
        f"padding: 2px 8px; font-size: 11px; font-weight: 600;"
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
