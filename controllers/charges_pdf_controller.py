"""
Contrôleur PDF pour les charges : génération de PDF sans dépendance Streamlit.
Les fonctions reçoivent toutes les données nécessaires en paramètres.
"""

from __future__ import annotations

import io
import os
import re
import tempfile
from typing import Optional, Dict

import pandas as pd

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.utils import ImageReader
from PIL import Image as PILImage

from models.database import DatabaseConnection, AppLogoModel
from models.salon_model import SalonModel


def _get_logo_bytes(salon_id: Optional[str], db_connection: Optional[DatabaseConnection]) -> Optional[bytes]:
    """Récupère les octets du logo depuis la BDD, sans accès à st.session_state."""
    try:
        if salon_id and db_connection:
            logo_model = AppLogoModel(db_connection)
            logo_data = logo_model.recuperer_logo(salon_id)
            if logo_data and logo_data.get('logo_data'):
                return logo_data['logo_data']
    except Exception as e:
        print(f"Erreur récupération logo PDF: {e}")
    return None


def _get_footer_lines(salon_id: Optional[str], db_connection: Optional[DatabaseConnection]):
    """Construit les lignes de pied de page depuis la BDD, sans accès à st.session_state."""
    try:
        if salon_id and db_connection:
            salon_model = SalonModel(db_connection)
            salon = salon_model.obtenir_salon_by_id(salon_id)
            if salon:
                nom = salon.get('nom_salon') or salon_id
                quartier = salon.get('quartier') or ''
                responsable = salon.get('responsable') or ''
                telephone = salon.get('telephone') or ''
                email = salon.get('email') or ''
                slogan = salon.get('pdf_slogan') or "L'Elegance Sur Mesure"

                line1 = f"{nom} - {slogan}"
                parts = []
                if quartier:
                    parts.append(quartier)
                if responsable:
                    parts.append(f"Resp.: {responsable}")
                if telephone:
                    parts.append(f"Tel: {telephone}")
                if email:
                    parts.append(f"Email: {email}")
                line2 = " | ".join(parts) if parts else ""
                lines = [line1]
                if line2:
                    lines.append(line2)
                return lines
    except Exception as e:
        print(f"Erreur construction pied de page PDF: {e}")
    return None


def _get_pdf_branding(salon_id: Optional[str], db_connection: Optional[DatabaseConnection]) -> Dict[str, str]:
    """Récupère le slogan et la couleur PDF par salon avec fallback sûr."""
    branding = {"pdf_slogan": "L'Elegance Sur Mesure", "pdf_theme_color": "#9B8AB5"}
    try:
        if salon_id and db_connection:
            cfg = SalonModel(db_connection).obtenir_config_salon(salon_id)
            slogan = str(cfg.get("pdf_slogan") or "").strip()
            color = str(cfg.get("pdf_theme_color") or "").strip()
            if slogan:
                branding["pdf_slogan"] = slogan
            if re.match(r"^#[0-9A-Fa-f]{6}$", color):
                branding["pdf_theme_color"] = color
    except Exception as e:
        print(f"Erreur branding PDF salon: {e}")
    return branding


def generer_pdf_impots(
    date_debut,
    date_fin,
    ca: float,
    total_charges: float,
    impot: float,
    benefice: float,
    df_charges: pd.DataFrame,
    salon_id: Optional[str] = None,
    db_connection: Optional[DatabaseConnection] = None,
) -> Optional[Dict[str, bytes]]:
    """
    Génère un PDF récapitulatif des impôts pour une période donnée.
    Aucune dépendance à streamlit - toutes les données sont passées en paramètres.

    Returns:
        dict avec keys: 'filename', 'content' (bytes) ou None en cas d'erreur
    """
    try:
        date_debut_str = date_debut.strftime('%d-%m-%Y')
        date_fin_str = date_fin.strftime('%d-%m-%Y')
        filename = f"Releve_Impots_{date_debut_str}_au_{date_fin_str}.pdf"
        temp_dir = tempfile.gettempdir()
        filepath = os.path.join(temp_dir, filename)

        logo_filigrane_data = _get_logo_bytes(salon_id, db_connection)
        footer_lines = _get_footer_lines(salon_id, db_connection)
        branding = _get_pdf_branding(salon_id, db_connection)

        def dessiner_filigrane(canvas_obj, doc_obj):
            if not logo_filigrane_data:
                return
            try:
                logo_img = PILImage.open(io.BytesIO(logo_filigrane_data))
                canvas_obj.saveState()
                if hasattr(canvas_obj, "setFillAlpha"):
                    canvas_obj.setFillAlpha(0.08)
                logo_img.thumbnail((300, 300), PILImage.Resampling.LANCZOS)
                img_width = logo_img.width * 0.75
                img_height = logo_img.height * 0.75
                page_width, page_height = doc_obj.pagesize
                x = (page_width - img_width) / 2
                y = (page_height - img_height) / 2
                canvas_obj.drawImage(
                    ImageReader(logo_img), x, y,
                    width=img_width, height=img_height, preserveAspectRatio=True
                )
                canvas_obj.restoreState()
            except Exception as e:
                print(f"Erreur filigrane impots: {e}")

        def dessiner_footer(canvas_obj, doc_obj):
            if not footer_lines:
                return
            try:
                canvas_obj.saveState()
                page_width, _ = doc_obj.pagesize
                footer_height = 2 * cm
                canvas_obj.setFillColor(colors.HexColor(branding["pdf_theme_color"]))
                canvas_obj.rect(0, 0, page_width, footer_height, fill=1, stroke=0)
                font_name = "Helvetica"
                font_size = 8
                canvas_obj.setFont(font_name, font_size)
                canvas_obj.setFillColor(colors.white)
                base_y = 0.6 * cm
                for idx, line in enumerate(footer_lines):
                    text = str(line)
                    text_width = canvas_obj.stringWidth(text, font_name, font_size)
                    x = (page_width - text_width) / 2
                    y = base_y + idx * 0.35 * cm
                    if y < footer_height - 0.2 * cm:
                        canvas_obj.drawString(x, y, text)
                canvas_obj.restoreState()
            except Exception as e:
                print(f"Erreur pied de page impots: {e}")

        doc = SimpleDocTemplate(
            filepath,
            pagesize=landscape(A4),
            rightMargin=2 * cm,
            leftMargin=2 * cm,
            topMargin=2 * cm,
            bottomMargin=2 * cm,
        )

        elements = []
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            'TitreImpot',
            parent=styles['Heading1'],
            fontSize=20,
            textColor=colors.HexColor('#2C3E50'),
            alignment=1,
            spaceAfter=20
        )
        heading_style = ParagraphStyle(
            'SectionHeading',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#34495E'),
            spaceAfter=10
        )
        desc_style = ParagraphStyle(
            'DescCharge',
            parent=styles['Normal'],
            fontSize=8,
            leading=9,
            spaceAfter=0,
            spaceBefore=0
        )

        if logo_filigrane_data:
            try:
                logo_img = PILImage.open(io.BytesIO(logo_filigrane_data))
                logo_img.thumbnail((200, 200), PILImage.Resampling.LANCZOS)
                logo_table_data = [[Image(ImageReader(logo_img), width=3.5 * cm, height=3.5 * cm)]]
                logo_table = Table(logo_table_data, colWidths=[15 * cm])
                logo_table.setStyle(TableStyle([
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ]))
                elements.append(logo_table)
            except Exception as e:
                print(f"Erreur logo impots (BDD): {e}")

        elements.append(Spacer(1, 0.4 * cm))
        titre = (
            f"RELEVE D'IMPOTS<br/>"
            f"{date_debut.strftime('%d/%m/%Y')} - {date_fin.strftime('%d/%m/%Y')}"
        )
        elements.append(Paragraph(titre, title_style))
        elements.append(Spacer(1, 0.3 * cm))

        elements.append(Paragraph("Recapitulatif financier", heading_style))
        recap_data = [
            ["Chiffre d'affaires", f"{ca:,.0f} FCFA"],
            ["Total des charges", f"{total_charges:,.0f} FCFA"],
            ["Impot a payer", f"{impot:,.0f} FCFA"],
            ["Benefice net", f"{benefice:,.0f} FCFA"],
        ]
        recap_table = Table(recap_data, colWidths=[7 * cm, 8 * cm])
        recap_table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.4, colors.grey),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#ECF0F1')),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BACKGROUND', (0, 2), (-1, 2), colors.HexColor('#FFF4E6')),
            ('TEXTCOLOR', (0, 2), (-1, 2), colors.HexColor('#F39C12')),
            ('FONTNAME', (0, 2), (-1, 2), 'Helvetica-Bold'),
        ]))
        elements.append(recap_table)
        elements.append(Spacer(1, 0.5 * cm))

        elements.append(Paragraph("Detail des charges sur la periode", heading_style))
        charges_data = [["Date", "Type", "Categorie", "Description", "Montant (FCFA)"]]
        if not df_charges.empty:
            df_tmp = df_charges.copy()
            df_tmp['date_charge'] = pd.to_datetime(df_tmp['date_charge'])
            df_tmp = df_tmp.sort_values('date_charge')
            for _, row in df_tmp.iterrows():
                date_str = row['date_charge'].strftime('%d/%m/%Y')
                type_str = str(row.get('type', ''))
                cat_str = str(row.get('categorie', ''))
                raw_desc = str(row.get('description', '') or f"Charge {cat_str}")
                para_desc = Paragraph(raw_desc.replace('\n', '<br/>'), desc_style)
                montant = f"{float(row.get('montant', 0)):,.0f}"
                charges_data.append([date_str, type_str, cat_str, para_desc, montant])
        else:
            charges_data.append(["Aucune charge", "", "", "", ""])

        charges_table = Table(
            charges_data,
            colWidths=[2.3 * cm, 2.3 * cm, 2.7 * cm, 7.0 * cm, 2.4 * cm]
        )
        charges_table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.3, colors.grey),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498DB')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
        ]))
        elements.append(charges_table)

        def _on_page(canvas_obj, doc_obj):
            dessiner_filigrane(canvas_obj, doc_obj)
            dessiner_footer(canvas_obj, doc_obj)

        doc.build(elements, onFirstPage=_on_page, onLaterPages=_on_page)

        with open(filepath, "rb") as f:
            content = f.read()
        try:
            os.remove(filepath)
        except Exception:
            pass

        return {"filename": filename, "content": content}
    except Exception as e:
        print(f"Erreur generation PDF impots: {e}")
        return None


def generer_pdf_analyse_charges(
    date_debut,
    date_fin,
    df_details: pd.DataFrame,
    df_recap: pd.DataFrame,
    salon_id: Optional[str] = None,
    db_connection: Optional[DatabaseConnection] = None,
) -> Optional[Dict[str, bytes]]:
    """
    Génère un PDF d'analyse des charges (détails + récap mensuel + évolution graphique).
    Aucune dépendance à streamlit - toutes les données sont passées en paramètres.

    Returns:
        dict avec keys: 'filename', 'content' (bytes) ou None en cas d'erreur
    """
    try:
        dd_str = date_debut.strftime('%d-%m-%Y')
        df_str = date_fin.strftime('%d-%m-%Y')
        filename = f"AnalyseDesCharges_Du_{dd_str}_Et_{df_str}.pdf"
        temp_dir = tempfile.gettempdir()
        filepath = os.path.join(temp_dir, filename)

        logo_filigrane_data = _get_logo_bytes(salon_id, db_connection)
        footer_lines = _get_footer_lines(salon_id, db_connection)
        branding = _get_pdf_branding(salon_id, db_connection)

        def dessiner_filigrane(canvas_obj, doc_obj):
            if not logo_filigrane_data:
                return
            try:
                logo_img = PILImage.open(io.BytesIO(logo_filigrane_data))
                canvas_obj.saveState()
                if hasattr(canvas_obj, "setFillAlpha"):
                    canvas_obj.setFillAlpha(0.08)
                logo_img.thumbnail((400, 400), PILImage.Resampling.LANCZOS)
                img_width = logo_img.width * 0.75
                img_height = logo_img.height * 0.75
                page_width, page_height = doc_obj.pagesize
                x = (page_width - img_width) / 2
                y = (page_height - img_height) / 2
                canvas_obj.drawImage(
                    ImageReader(logo_img), x, y,
                    width=img_width, height=img_height, preserveAspectRatio=True
                )
                canvas_obj.restoreState()
            except Exception as e:
                print(f"Erreur filigrane analyse charges: {e}")

        def dessiner_footer(canvas_obj, doc_obj):
            if not footer_lines:
                return
            try:
                canvas_obj.saveState()
                page_width, _ = doc_obj.pagesize
                footer_height = 2 * cm
                canvas_obj.setFillColor(colors.HexColor(branding["pdf_theme_color"]))
                canvas_obj.rect(0, 0, page_width, footer_height, fill=1, stroke=0)
                font_name = "Helvetica"
                font_size = 8
                canvas_obj.setFont(font_name, font_size)
                canvas_obj.setFillColor(colors.white)
                base_y = 0.6 * cm
                for idx, line in enumerate(footer_lines):
                    text = str(line)
                    text_width = canvas_obj.stringWidth(text, font_name, font_size)
                    x = (page_width - text_width) / 2
                    y = base_y + idx * 0.35 * cm
                    if y < footer_height - 0.2 * cm:
                        canvas_obj.drawString(x, y, text)
                canvas_obj.restoreState()
            except Exception as e:
                print(f"Erreur pied de page analyse charges: {e}")

        doc = SimpleDocTemplate(
            filepath,
            pagesize=landscape(A4),
            rightMargin=2 * cm,
            leftMargin=2 * cm,
            topMargin=2 * cm,
            bottomMargin=2 * cm,
        )

        elements = []
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            'TitreAnalyse',
            parent=styles['Heading1'],
            fontSize=20,
            textColor=colors.HexColor('#2C3E50'),
            alignment=1,
            spaceAfter=18
        )
        heading_style = ParagraphStyle(
            'HeadingSection',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#34495E'),
            spaceAfter=10
        )
        cell_style = ParagraphStyle(
            'Cellule',
            parent=styles['Normal'],
            fontSize=8,
            leading=9,
            spaceAfter=0,
            spaceBefore=0
        )

        if logo_filigrane_data:
            try:
                logo_img = PILImage.open(io.BytesIO(logo_filigrane_data))
                logo_img.thumbnail((220, 220), PILImage.Resampling.LANCZOS)
                logo_table_data = [[Image(ImageReader(logo_img), width=3.5 * cm, height=3.5 * cm)]]
                logo_table = Table(logo_table_data, colWidths=[25 * cm])
                logo_table.setStyle(TableStyle([
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ]))
                elements.append(logo_table)
            except Exception as e:
                print(f"Erreur logo analyse charges (BDD): {e}")

        elements.append(Spacer(1, 0.4 * cm))
        titre = (
            f"ANALYSE DES CHARGES<br/>"
            f"Periode du {date_debut.strftime('%d/%m/%Y')} au {date_fin.strftime('%d/%m/%Y')}"
        )
        elements.append(Paragraph(titre, title_style))
        elements.append(Spacer(1, 0.3 * cm))

        # Tableau DETAILS DES CHARGES
        elements.append(Paragraph("Detail des charges", heading_style))
        details = df_details.copy()
        if not details.empty:
            details = details.sort_values('date_charge')
            details['date_charge'] = pd.to_datetime(details['date_charge']).dt.strftime('%d/%m/%Y')
            table_data = [["Date", "Type", "Categorie", "Description", "Montant (FCFA)"]]
            for _, row in details.iterrows():
                date_str = str(row.get('date_charge', ''))
                type_str = str(row.get('type', ''))
                cat_str = str(row.get('categorie', ''))
                desc_raw = str(row.get('description', '') or '')
                desc_para = Paragraph(desc_raw.replace('\n', '<br/>'), cell_style)
                montant = f"{float(row.get('montant', 0.0)):,.0f}"
                table_data.append([date_str, type_str, cat_str, desc_para, montant])
        else:
            table_data = [
                ["Date", "Type", "Categorie", "Description", "Montant (FCFA)"],
                ["Aucune charge", "", "", "", ""]
            ]
        details_table = Table(
            table_data,
            colWidths=[2.2 * cm, 2.4 * cm, 2.8 * cm, 11.0 * cm, 3.0 * cm]
        )
        details_table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.35, colors.grey),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498DB')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(details_table)
        elements.append(Spacer(1, 0.5 * cm))

        # Tableau RECAPITULATIF MENSUEL
        elements.append(Paragraph("Recapitulatif mensuel", heading_style))
        recap = df_recap.copy()
        recap_table_data = [["Mois"] + list(recap.columns)]
        for mois_label, row in recap.iterrows():
            ligne = [str(mois_label)]
            for col in recap.columns:
                val = float(row[col]) if pd.notnull(row[col]) else 0.0
                ligne.append(f"{val:,.0f}")
            recap_table_data.append(ligne)
        recap_table = Table(
            recap_table_data,
            colWidths=[4.0 * cm] + [
                ((24 * cm) - 4.0 * cm) / max(1, len(recap.columns))
            ] * len(recap.columns)
        )
        recap_table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.35, colors.grey),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2ECC71')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(recap_table)
        elements.append(Spacer(1, 0.5 * cm))

        # Graphique d'evolution mensuelle
        try:
            import matplotlib.pyplot as plt

            def _nettoyer_label(label):
                if not label:
                    return "Type"
                label_str = str(label)
                mapping = {
                    "Charges Ponctuelles (reparations...)": "Charges Ponctuelles",
                    "Charges Ponctuelles": "Charges Ponctuelles",
                    "Ponctuelles": "Ponctuelles",
                    "Charges liees a une commande": "Charges liees a une commande",
                    "Salaires": "Salaires",
                    "Charges Fixes (loyer, salaires...)": "Charges Fixes",
                    "Charges Fixes": "Charges Fixes",
                }
                if label_str in mapping:
                    return mapping[label_str]
                label_clean = re.sub(
                    r'[\U0001F300-\U0001F9FF\U00002600-\U000026FF\U00002700-\U000027BF]',
                    '', label_str
                )
                return label_clean.strip()

            fig, ax = plt.subplots(figsize=(8, 3))
            mois_labels = list(recap.index)
            x = range(len(mois_labels))
            type_cols = [c for c in recap.columns if c != 'Total']
            for col in type_cols:
                y = [float(v) for v in recap[col].values]
                label_clean = _nettoyer_label(col)
                ax.plot(x, y, marker='o', label=label_clean)
            ax.set_xticks(x)
            ax.set_xticklabels(mois_labels, rotation=45, ha='right')
            ax.set_ylabel("Montant (FCFA)")
            ax.set_title("Evolution mensuelle des charges par type")
            ax.grid(True, axis='y', linestyle='--', alpha=0.4)
            ax.legend(fontsize=7)
            fig.tight_layout()

            img_buffer = io.BytesIO()
            fig.savefig(img_buffer, format='png', dpi=120)
            plt.close(fig)
            img_buffer.seek(0)

            evolution_img = Image(img_buffer, width=24 * cm, height=7 * cm)
            elements.append(Paragraph("Evolution graphique", heading_style))
            elements.append(evolution_img)
        except Exception as e:
            print(f"Erreur generation graphique analyse charges: {e}")

        def _on_page(canvas_obj, doc_obj):
            dessiner_filigrane(canvas_obj, doc_obj)
            dessiner_footer(canvas_obj, doc_obj)

        doc.build(elements, onFirstPage=_on_page, onLaterPages=_on_page)

        with open(filepath, "rb") as f:
            content = f.read()
        try:
            os.remove(filepath)
        except Exception:
            pass

        return {"filename": filename, "content": content}
    except Exception as e:
        print(f"Erreur generation PDF analyse charges: {e}")
        return None
