import json
import os
import textwrap
import streamlit as st


def _safe_format(template: str, values: dict) -> str:
    if not template:
        return ""

    try:
        return template.format_map(values)
    except Exception:
        return template


@st.cache_data(show_spinner=False)
def load_site_content() -> dict:
    project_root = os.path.dirname(os.path.dirname(__file__))
    content_path = os.path.join(project_root, "assets", "site_content.json")

    try:
        with open(content_path, "r", encoding="utf-8") as file:
            return json.load(file)
    except Exception:
        return {}


def _build_bottom_nav_html(content: dict, app_values: dict) -> str:
    hero = content.get("hero", {})
    company = content.get("company", {})

    badge = _safe_format(hero.get("badge", ""), app_values)
    title = _safe_format(hero.get("title", "") or hero.get("title_template", ""), app_values)
    subtitle = _safe_format(hero.get("subtitle", "") or hero.get("subtitle_template", ""), app_values)

    features = [item for item in hero.get("features", []) if item]
    features_html = "".join(f"<li>{item}</li>" for item in features)

    hero_html = ""
    if badge or title or subtitle or features_html:
        hero_html = textwrap.dedent(f"""
            <div class="bottom-nav-hero">
                {f'<div class="bottom-nav-badge">{badge}</div>' if badge else ''}
                {f'<div class="bottom-nav-title">{title}</div>' if title else ''}
                {f'<div class="bottom-nav-subtitle">{subtitle}</div>' if subtitle else ''}
                {f'<ul class="bottom-nav-list">{features_html}</ul>' if features_html else ''}
            </div>
        """).strip()

    company_title = company.get("title", "")
    fields_html = ""
    for field in company.get("fields", []):
        label = field.get("label", "")
        value = field.get("value", "")
        if label or value:
            fields_html += (
                "<div class='bottom-nav-item'>"
                f"<span class='bottom-nav-label'>{label}</span>"
                f"<span class='bottom-nav-value'>{value}</span>"
                "</div>"
            )

    company_html = ""
    if company_title or fields_html:
        company_html = textwrap.dedent(f"""
            <div class="bottom-nav-company">
                {f'<div class="bottom-nav-company-title">{company_title}</div>' if company_title else ''}
                {fields_html}
            </div>
        """).strip()

    if not hero_html and not company_html:
        return ""

    return textwrap.dedent(f"""
        <div class="bottom-nav">
            <div class="bottom-nav-inner">
                {hero_html}
                {company_html}
            </div>
        </div>
        <div class="bottom-nav-spacer"></div>
    """).strip()


def _build_footer_html(content: dict) -> str:
    """Construit le HTML du footer (informations entreprise uniquement) pour affichage sur toutes les pages."""
    company = content.get("company", {})
    company_title = company.get("title", "")
    fields_html = ""
    for field in company.get("fields", []):
        label = field.get("label", "")
        value = field.get("value", "")
        if label or value:
            fields_html += (
                "<div class='app-footer-item'>"
                f"<span class='app-footer-label'>{label}</span>"
                f"<span class='app-footer-value'>{value}</span>"
                "</div>"
            )
    if not company_title and not fields_html:
        return ""
    return textwrap.dedent(f"""
        <footer class="app-footer">
            <div class="app-footer-inner">
                {f'<div class="app-footer-title">{company_title}</div>' if company_title else ''}
                {fields_html}
            </div>
        </footer>
    """).strip()


def render_app_footer() -> None:
    """
    Affiche le footer avec les informations de l'entreprise (nom, adresse, contact).
    À appeler sur toutes les pages, y compris la page de connexion.
    """
    content = load_site_content()
    footer_html = _build_footer_html(content)
    if not footer_html:
        return
    st.markdown("""
        <style>
        .app-footer {
            margin-top: 2.5rem;
            padding: 1rem 0;
            background: linear-gradient(135deg, #F3F0FB 0%, #E9FBF9 100%);
            border-top: 2px solid rgba(177, 156, 217, 0.4);
        }
        .app-footer-inner {
            max-width: 1200px;
            margin: 0 auto;
            padding: 0 1.5rem;
            display: flex;
            flex-wrap: wrap;
            align-items: flex-start;
            gap: 0.75rem 1.5rem;
        }
        .app-footer-title {
            font-weight: 700;
            color: #2C2C2C;
            font-size: 1rem;
            width: 100%;
            margin-bottom: 0.25rem;
        }
        .app-footer-item {
            display: inline-flex;
            gap: 0.4rem;
            font-size: 0.9rem;
            color: rgba(44, 44, 44, 0.86);
        }
        .app-footer-label { font-weight: 600; color: #2C2C2C; }
        .app-footer-value { color: rgba(44, 44, 44, 0.8); }
        </style>
    """, unsafe_allow_html=True)
    st.markdown(footer_html, unsafe_allow_html=True)


def render_bottom_nav(app_values: dict) -> None:
    content = load_site_content()
    bottom_nav_html = _build_bottom_nav_html(content, app_values)
    if not bottom_nav_html:
        return
    st.markdown("""
        <style>
        .bottom-nav {
            margin-top: 2.5rem;
            background: linear-gradient(135deg, #F3F0FB 0%, #E9FBF9 100%);
            border-top: 2px solid #B19CD9;
            padding: 1.1rem 0;
        }

        .bottom-nav-inner {
            max-width: 1200px;
            margin: 0 auto;
            display: grid;
            grid-template-columns: 1.3fr 1fr;
            gap: 1.8rem;
            align-items: flex-start;
            background: #FFFFFF;
            border-radius: 18px;
            padding: 1.1rem 1.4rem;
            border: 1px solid rgba(177, 156, 217, 0.25);
            box-shadow: 0 10px 24px rgba(0, 0, 0, 0.08);
        }

        .bottom-nav-hero {
            min-width: 260px;
        }

        .bottom-nav-badge {
            display: inline-block;
            padding: 0.32rem 0.85rem;
            border-radius: 999px;
            background: linear-gradient(135deg, #B19CD9 0%, #40E0D0 100%);
            color: #FFFFFF;
            font-weight: 700;
            font-size: 0.86rem;
            margin-bottom: 0.6rem;
            letter-spacing: 0.2px;
        }

        .bottom-nav-title {
            font-size: 1.2rem;
            font-weight: 700;
            color: #2C2C2C;
            margin-bottom: 0.35rem;
        }

        .bottom-nav-subtitle {
            color: rgba(44, 44, 44, 0.8);
            font-size: 0.98rem;
            margin-bottom: 0.65rem;
        }

        .bottom-nav-list {
            margin: 0;
            padding-left: 1.1rem;
            color: rgba(44, 44, 44, 0.85);
            font-size: 0.95rem;
            line-height: 1.45;
        }

        .bottom-nav-company {
            min-width: 240px;
            display: flex;
            flex-direction: column;
            gap: 0.45rem;
            background: #F8FAFF;
            border-radius: 14px;
            padding: 1rem 1.1rem;
            border: 1px solid rgba(177, 156, 217, 0.35);
            box-shadow: 0 8px 18px rgba(0, 0, 0, 0.08);
        }

        .bottom-nav-company-title {
            font-weight: 700;
            color: #2C2C2C;
            margin-bottom: 0.3rem;
        }

        .bottom-nav-item {
            display: grid;
            grid-template-columns: auto 1fr;
            gap: 0.5rem;
            font-size: 0.92rem;
            color: rgba(44, 44, 44, 0.86);
        }

        .bottom-nav-label {
            font-weight: 600;
            color: #2C2C2C;
        }

        .bottom-nav-value {
            color: rgba(44, 44, 44, 0.8);
        }

        @media (max-width: 900px) {
            .bottom-nav-inner {
                grid-template-columns: 1fr;
            }
        }
        </style>
    """, unsafe_allow_html=True)

    st.markdown(bottom_nav_html, unsafe_allow_html=True)
