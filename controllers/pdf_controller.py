"""
Contrôleur de génération de PDF (Controller dans MVC)
Génère un PDF complet avec QR code et logo de l'entreprise
"""

import os
import io
import json
import logging
import re
import tempfile
import unicodedata
from datetime import datetime
from typing import Dict, Optional

from PIL import Image as PILImage
import qrcode

# Imports ReportLab
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    Image,
    KeepTogether,
    PageTemplate,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.lib.utils import ImageReader

try:
    from pypdf import PdfReader as _PdfReader
except ImportError:
    _PdfReader = None

try:
    from config import PDF_STORAGE_PATH
except ImportError:
    PDF_STORAGE_PATH = os.path.join(os.path.dirname(__file__), "pdfs")

_logger = logging.getLogger("pdf_controller")
if not _logger.handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("[pdf] %(levelname)s %(message)s"))
    _logger.addHandler(_h)
    _logger.setLevel(logging.INFO)


def _pdf_ensure_storage_path() -> str:
    """Garantit que le dossier de sortie PDF existe avant chaque génération.

    Lève une exception explicite si impossible (permission, disque plein...).
    """
    try:
        os.makedirs(PDF_STORAGE_PATH, exist_ok=True)
    except OSError as exc:
        _logger.error(
            "Impossible de créer le dossier PDF %s : %s", PDF_STORAGE_PATH, exc
        )
        raise
    return PDF_STORAGE_PATH


# ---------------------------------------------------------------------------
# Gestion des polices Unicode (accents / emojis)
# ---------------------------------------------------------------------------
_PDF_UNICODE_FONT: Optional[str] = None
_PDF_UNICODE_FONT_BOLD: Optional[str] = None


def _try_register_unicode_font() -> None:
    """Enregistre une police TTF Unicode si on en trouve une sur le système.

    Essaye DejaVu Sans (Linux/Mac/Windows) puis Arial comme repli.
    Laisse le contrôleur retomber sur Helvetica si rien n'est trouvé.
    """
    global _PDF_UNICODE_FONT, _PDF_UNICODE_FONT_BOLD

    if _PDF_UNICODE_FONT is not None:
        return

    candidates = [
        # (nom logique, chemin regular, chemin bold)
        (
            "DejaVuSans",
            ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
             "/Library/Fonts/DejaVuSans.ttf",
             "C:/Windows/Fonts/DejaVuSans.ttf"],
            ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
             "/Library/Fonts/DejaVuSans-Bold.ttf",
             "C:/Windows/Fonts/DejaVuSans-Bold.ttf"],
        ),
        (
            "Arial",
            ["C:/Windows/Fonts/arial.ttf",
             "/Library/Fonts/Arial.ttf"],
            ["C:/Windows/Fonts/arialbd.ttf",
             "/Library/Fonts/Arial Bold.ttf"],
        ),
    ]

    for nom, regs, bolds in candidates:
        reg = next((p for p in regs if os.path.exists(p)), None)
        if not reg:
            continue
        try:
            pdfmetrics.registerFont(TTFont(nom, reg))
            _PDF_UNICODE_FONT = nom
            bold = next((p for p in bolds if os.path.exists(p)), None)
            if bold:
                try:
                    pdfmetrics.registerFont(TTFont(f"{nom}-Bold", bold))
                    _PDF_UNICODE_FONT_BOLD = f"{nom}-Bold"
                except Exception as exc:  # pragma: no cover
                    _logger.warning("Echec enregistrement %s-Bold : %s", nom, exc)
            _logger.info("Police Unicode PDF: %s", nom)
            return
        except Exception as exc:  # pragma: no cover
            _logger.warning("Echec enregistrement police %s : %s", nom, exc)

    _logger.info("Aucune police Unicode trouvée, repli sur Helvetica (accents OK, pas d'emoji)")


# Tente l'enregistrement une fois au chargement du module
_try_register_unicode_font()


# Regex pour détecter les emojis / symboles non latin-1
_EMOJI_RE = re.compile(
    "["
    "\U0001F300-\U0001F6FF"   # emoticônes, transports, symboles
    "\U0001F700-\U0001F77F"
    "\U0001F780-\U0001F7FF"
    "\U0001F800-\U0001F8FF"
    "\U0001F900-\U0001F9FF"
    "\U0001FA00-\U0001FA6F"
    "\U0001FA70-\U0001FAFF"
    "\U00002600-\U000026FF"   # ☀️ ☁️ ⚠️ ...
    "\U00002700-\U000027BF"   # ✅ ❌ ...
    "]",
    flags=re.UNICODE,
)


def _pdf_safe_text(texte: Optional[str]) -> str:
    """Nettoie un texte pour l'affichage PDF.

    - Si une police Unicode est chargée : renvoie le texte tel quel.
    - Sinon (Helvetica / latin-1) : retire les emojis, normalise les accents.
    """
    if texte is None:
        return ""
    s = str(texte)
    if _PDF_UNICODE_FONT:
        return s
    # Repli Helvetica : on strip les emojis, on garde les accents latin-1
    s = _EMOJI_RE.sub("", s)
    # Remplace quelques symboles problématiques par leur équivalent ASCII
    remplacements = {
        "\u2192": "->",
        "\u2190": "<-",
        "\u2013": "-",
        "\u2014": "-",
        "\u2026": "...",
        "\xa0": " ",
    }
    for k, v in remplacements.items():
        s = s.replace(k, v)
    # Normalise (décompose puis recompose) pour maximiser la compatibilité latin-1
    s = unicodedata.normalize("NFC", s)
    return s.strip()


def _pdf_font(bold: bool = False) -> str:
    """Renvoie la police à utiliser (Unicode si disponible, sinon Helvetica)."""
    if bold:
        return _PDF_UNICODE_FONT_BOLD or "Helvetica-Bold"
    return _PDF_UNICODE_FONT or "Helvetica"

# Palette PDF commande — mauve doux & or champagne (tons clairs, non bordeaux)
_P_MAUVE = colors.HexColor("#9B8AB5")
_P_MAUVE_FONCE = colors.HexColor("#6E5D80")
_P_MAUVE_CLAIR = colors.HexColor("#B8A9C9")
_P_MAUVE_TRES_CLAIR = colors.HexColor("#E8E0F0")
_P_OR_CHAMPAGNE = colors.HexColor("#E8DCC4")
_P_OR_DOUX = colors.HexColor("#C9B896")
_P_OR_PALE = colors.HexColor("#F3EBDD")
_P_CREME = colors.HexColor("#FBF9F6")
_P_IVOIRE = colors.HexColor("#F3EFF7")
_P_NOIR_DOUX = colors.HexColor("#3A3640")
_P_GRIS = colors.HexColor("#6B6570")
_P_GRIS_CLAIR = colors.HexColor("#D9D4E0")
_P_ROUGE_ALERTE = colors.HexColor("#C45C5C")
_P_VERT_VALIDE = colors.HexColor("#5A9B6E")
_P_ALERTE_BG = colors.HexColor("#F5D5D5")


def _pdf_fmt_fcfa(montant: float) -> str:
    return f"{int(round(montant)):,} FCFA".replace(",", " ")


def _pdf_styles_commande():
    s = {}
    s["document_titre"] = ParagraphStyle(
        "CmdDocTitre",
        fontName="Helvetica-Bold",
        fontSize=22,
        textColor=_P_MAUVE_FONCE,
        alignment=TA_CENTER,
        leading=26,
        spaceBefore=6,
        spaceAfter=2,
    )
    s["document_sous_titre"] = ParagraphStyle(
        "CmdDocSous",
        fontName="Helvetica-Oblique",
        fontSize=10,
        textColor=_P_OR_DOUX,
        alignment=TA_CENTER,
        spaceAfter=16,
    )
    s["section"] = ParagraphStyle(
        "CmdSection",
        fontName="Helvetica-Bold",
        fontSize=13,
        textColor=colors.white,
        alignment=TA_LEFT,
        leading=18,
        leftIndent=8,
        spaceAfter=0,
    )
    s["legende"] = ParagraphStyle(
        "CmdLegende",
        fontName="Helvetica-Bold",
        fontSize=9,
        textColor=_P_MAUVE_FONCE,
        alignment=TA_CENTER,
        spaceAfter=2,
    )
    s["signature"] = ParagraphStyle(
        "CmdSig",
        fontName="Helvetica-Oblique",
        fontSize=9,
        textColor=_P_GRIS,
        alignment=TA_CENTER,
    )
    s["qr_note"] = ParagraphStyle(
        "CmdQrNote",
        fontName="Helvetica-Oblique",
        fontSize=8.5,
        textColor=_P_GRIS,
        alignment=TA_CENTER,
    )
    return s


def _pdf_table_infos_commande(lignes: list, largeur_label_cm: float = 4.5):
    data = [
        [
            Paragraph(
                f"<b>{l}</b>",
                ParagraphStyle(
                    "k",
                    fontName="Helvetica-Bold",
                    fontSize=10,
                    textColor=_P_MAUVE_FONCE,
                ),
            ),
            Paragraph(
                v,
                ParagraphStyle(
                    "v",
                    fontName="Helvetica",
                    fontSize=10,
                    textColor=_P_NOIR_DOUX,
                ),
            ),
        ]
        for l, v in lignes
    ]
    t = Table(
        data,
        colWidths=[largeur_label_cm * cm, (17.5 - largeur_label_cm) * cm],
    )
    style = [
        ("BACKGROUND", (0, 0), (0, -1), _P_IVOIRE),
        ("LINEBELOW", (0, 0), (-1, -2), 0.4, _P_GRIS_CLAIR),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("BOX", (0, 0), (-1, -1), 0.6, _P_MAUVE),
        ("LINEAFTER", (0, 0), (0, -1), 0.4, _P_OR_DOUX),
    ]
    for i in range(len(data)):
        if i % 2 == 1:
            style.append(("BACKGROUND", (1, i), (1, i), _P_CREME))
    t.setStyle(TableStyle(style))
    return t


def _pdf_table_mesures_commande(mesures: dict):
    entete = [
        Paragraph(
            "<b>MESURE</b>",
            ParagraphStyle(
                "h",
                fontName="Helvetica-Bold",
                fontSize=10,
                textColor=colors.white,
            ),
        ),
        Paragraph(
            "<b>VALEUR</b>",
            ParagraphStyle(
                "h2",
                fontName="Helvetica-Bold",
                fontSize=10,
                textColor=colors.white,
                alignment=TA_CENTER,
            ),
        ),
    ]
    lignes = [entete]
    for nom, val in mesures.items():
        try:
            val_txt = f"<b>{float(val):.1f} cm</b>"
        except (TypeError, ValueError):
            val_txt = f"<b>{val} cm</b>"
        lignes.append(
            [
                Paragraph(
                    str(nom),
                    ParagraphStyle(
                        "x",
                        fontName="Helvetica",
                        fontSize=10,
                        textColor=_P_NOIR_DOUX,
                    ),
                ),
                Paragraph(
                    val_txt,
                    ParagraphStyle(
                        "y",
                        fontName="Helvetica",
                        fontSize=10,
                        textColor=_P_MAUVE_FONCE,
                        alignment=TA_CENTER,
                    ),
                ),
            ]
        )
    t = Table(lignes, colWidths=[12 * cm, 5.5 * cm])
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), _P_MAUVE),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("BOX", (0, 0), (-1, -1), 0.6, _P_MAUVE),
        ("LINEBELOW", (0, 0), (-1, -1), 0.3, _P_GRIS_CLAIR),
        ("LINEAFTER", (0, 0), (0, -1), 0.4, _P_OR_DOUX),
    ]
    for i in range(1, len(lignes)):
        if i % 2 == 0:
            style.append(("BACKGROUND", (0, i), (-1, i), _P_CREME))
        else:
            style.append(("BACKGROUND", (0, i), (-1, i), _P_IVOIRE))
    t.setStyle(TableStyle(style))
    return t


def _pdf_table_finances_commande(prix: float, avance: float, reste: float):
    data = [
        [
            Paragraph(
                "<b>Prix total</b>",
                ParagraphStyle(
                    "a",
                    fontName="Helvetica-Bold",
                    fontSize=11,
                    textColor=_P_MAUVE_FONCE,
                ),
            ),
            Paragraph(
                _pdf_fmt_fcfa(prix),
                ParagraphStyle(
                    "b",
                    fontName="Helvetica",
                    fontSize=11,
                    textColor=_P_NOIR_DOUX,
                    alignment=TA_RIGHT,
                ),
            ),
        ],
        [
            Paragraph(
                "<b>Avance versée</b>",
                ParagraphStyle(
                    "c",
                    fontName="Helvetica-Bold",
                    fontSize=11,
                    textColor=_P_MAUVE_FONCE,
                ),
            ),
            Paragraph(
                _pdf_fmt_fcfa(avance),
                ParagraphStyle(
                    "d",
                    fontName="Helvetica",
                    fontSize=11,
                    textColor=_P_VERT_VALIDE,
                    alignment=TA_RIGHT,
                ),
            ),
        ],
        [
            Paragraph(
                "<b>Reste à payer</b>",
                ParagraphStyle(
                    "e",
                    fontName="Helvetica-Bold",
                    fontSize=12,
                    textColor=_P_MAUVE_FONCE,
                ),
            ),
            Paragraph(
                f"<b>{_pdf_fmt_fcfa(reste)}</b>",
                ParagraphStyle(
                    "f",
                    fontName="Helvetica-Bold",
                    fontSize=14,
                    textColor=_P_MAUVE_FONCE,
                    alignment=TA_RIGHT,
                ),
            ),
        ],
    ]
    t = Table(data, colWidths=[10 * cm, 7.5 * cm])
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), _P_IVOIRE),
                ("BACKGROUND", (0, 1), (-1, 1), _P_CREME),
                ("BACKGROUND", (0, 2), (-1, 2), _P_ALERTE_BG),
                ("TEXTCOLOR", (0, 2), (-1, 2), _P_ROUGE_ALERTE),
                ("LEFTPADDING", (0, 0), (-1, -1), 14),
                ("RIGHTPADDING", (0, 0), (-1, -1), 14),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ("BOX", (0, 0), (-1, -1), 0.6, _P_MAUVE),
                ("LINEBELOW", (0, 0), (-1, 1), 0.4, _P_GRIS_CLAIR),
            ]
        )
    )
    return t


def _pdf_bandeau_section_commande(titre: str):
    t = Table(
        [
            [
                Paragraph(
                    f"<b>{titre.upper()}</b>",
                    ParagraphStyle(
                        "s",
                        fontName="Helvetica-Bold",
                        fontSize=12,
                        textColor=colors.white,
                        leading=16,
                    ),
                )
            ]
        ],
        colWidths=[17.5 * cm],
    )
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), _P_MAUVE),
                ("LEFTPADDING", (0, 0), (-1, -1), 14),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ("LINEBEFORE", (0, 0), (0, -1), 4, _P_OR_CHAMPAGNE),
            ]
        )
    )
    return t


def _pdf_dessiner_decor_commande(
    canvas_obj,
    salon_row: Optional[Dict],
    numero_commande: str,
    logo_bytes: Optional[bytes],
    total_pages: Optional[int],
    watermark_logo_bytes: Optional[bytes],
):
    W, H = A4
    nom = (
        (salon_row or {}).get("nom_salon") or "Salon de couture"
    ).strip()
    slogan = "L'Élégance Sur Mesure"
    adresse = ((salon_row or {}).get("quartier") or "—") or "—"
    if isinstance(adresse, str):
        adresse = adresse.strip() or "—"
    responsable = ((salon_row or {}).get("responsable") or "").strip()
    telephone = ((salon_row or {}).get("telephone") or "").strip()
    email = ((salon_row or {}).get("email") or "").strip()

    # Filigrane texte très pâle
    canvas_obj.saveState()
    canvas_obj.setFillColor(_P_MAUVE_TRES_CLAIR)
    canvas_obj.setFont("Helvetica-Bold", 56)
    canvas_obj.translate(W / 2, H / 2)
    canvas_obj.rotate(28)
    canvas_obj.drawCentredString(0, 0, nom[:18] if len(nom) > 18 else nom)
    canvas_obj.restoreState()

    # Filigrane logo (optionnel), plus léger que l’ancien rendu
    if watermark_logo_bytes:
        try:
            logo_img = PILImage.open(io.BytesIO(watermark_logo_bytes))
            logo_img.thumbnail((280, 280), PILImage.Resampling.LANCZOS)
            canvas_obj.saveState()
            if hasattr(canvas_obj, "setFillAlpha"):
                canvas_obj.setFillAlpha(0.08)
            iw, ih = logo_img.size
            img_width = iw * 0.9
            img_height = ih * 0.9
            x = (W - img_width) / 2
            y = (H - img_height) / 2
            canvas_obj.drawImage(
                ImageReader(logo_img),
                x,
                y,
                width=img_width,
                height=img_height,
                preserveAspectRatio=True,
            )
            canvas_obj.restoreState()
        except Exception as e:
            print(f"Filigrane logo PDF commande: {e}")

    # Bandeau en-tête (mauve clair)
    canvas_obj.setFillColor(_P_MAUVE)
    canvas_obj.rect(0, H - 3.2 * cm, W, 3.2 * cm, stroke=0, fill=1)
    canvas_obj.setFillColor(_P_OR_CHAMPAGNE)
    canvas_obj.rect(0, H - 3.35 * cm, W, 0.15 * cm, stroke=0, fill=1)

    cx, cy, r = 2.2 * cm, H - 1.6 * cm, 0.85 * cm
    drawn_logo = False
    if logo_bytes:
        try:
            pil = PILImage.open(io.BytesIO(logo_bytes))
            pil.thumbnail((170, 170), PILImage.Resampling.LANCZOS)
            canvas_obj.saveState()
            canvas_obj.drawImage(
                ImageReader(pil),
                cx - r,
                cy - r,
                width=2 * r,
                height=2 * r,
                preserveAspectRatio=True,
                mask="auto",
            )
            canvas_obj.restoreState()
            drawn_logo = True
        except Exception as exc:
            _logger.warning(
                "Logo salon illisible (%s octets) : %s — repli monogramme",
                len(logo_bytes) if logo_bytes else 0,
                exc,
            )
            drawn_logo = False
    else:
        _logger.debug("Pas de logo_bytes : monogramme utilisé")
    if not drawn_logo:
        canvas_obj.setFillColor(_P_OR_CHAMPAGNE)
        canvas_obj.circle(cx, cy, r, stroke=0, fill=1)
        canvas_obj.setFillColor(_P_MAUVE_FONCE)
        canvas_obj.setFont("Helvetica-Bold", 20)
        initiale = (nom[:2] or "SA").upper()
        canvas_obj.drawCentredString(cx, cy - 7, initiale)

    canvas_obj.setFillColor(colors.white)
    canvas_obj.setFont("Helvetica-Bold", 20)
    canvas_obj.drawString(3.6 * cm, H - 1.32 * cm, nom[:42])
    canvas_obj.setFillColor(_P_OR_PALE)
    canvas_obj.setFont("Helvetica-Oblique", 10)
    canvas_obj.drawString(3.6 * cm, H - 1.82 * cm, slogan)
    canvas_obj.setFillColor(colors.white)
    canvas_obj.setFont("Helvetica", 8.5)
    canvas_obj.drawString(3.6 * cm, H - 2.32 * cm, "Document de livraison officiel")

    canvas_obj.setFillColor(colors.white)
    canvas_obj.setFont("Helvetica-Bold", 9)
    canvas_obj.drawRightString(W - 1.2 * cm, H - 1.08 * cm, adresse[:55])
    canvas_obj.setFont("Helvetica", 8.5)
    if responsable:
        canvas_obj.drawRightString(
            W - 1.2 * cm, H - 1.52 * cm, f"Resp. : {responsable[:40]}"
        )
    if telephone:
        canvas_obj.drawRightString(
            W - 1.2 * cm, H - 1.92 * cm, f"Tél. : {telephone[:32]}"
        )
    if email:
        canvas_obj.drawRightString(
            W - 1.2 * cm, H - 2.32 * cm, f"Email : {email[:40]}"
        )

    # Pied de page
    canvas_obj.setFillColor(_P_OR_CHAMPAGNE)
    canvas_obj.rect(0, 0, W, 0.15 * cm, stroke=0, fill=1)
    canvas_obj.setFillColor(_P_MAUVE)
    canvas_obj.rect(0, 0.15 * cm, W, 1.5 * cm, stroke=0, fill=1)
    canvas_obj.setFillColor(colors.white)
    canvas_obj.setFont("Helvetica-Bold", 9)
    canvas_obj.drawCentredString(W / 2, 1.15 * cm, f"{nom} — {slogan}")
    canvas_obj.setFont("Helvetica", 8)
    coord = " | ".join(
        p
        for p in [adresse, f"Tél. : {telephone}" if telephone else "", f"Email : {email}" if email else ""]
        if p
    )
    canvas_obj.drawCentredString(W / 2, 0.75 * cm, coord[:120])
    canvas_obj.setFont("Helvetica-Oblique", 7.5)
    page_txt = (
        f"— Page {canvas_obj.getPageNumber()} / {total_pages} —"
        if total_pages
        else f"— Page {canvas_obj.getPageNumber()} —"
    )
    canvas_obj.drawCentredString(
        W / 2,
        0.4 * cm,
        f"Document officiel {page_txt}",
    )


class PDFController:
    """Gère la génération de PDF pour les commandes (multi-tenant)"""

    def __init__(self, db_connection=None):
        """
        Initialise le contrôleur PDF

        Args:
            db_connection: Connexion à la base de données (optionnel, pour récupérer le logo)
        """
        # Assure la présence du dossier de sortie, sinon log l'erreur (non fatal à l'init,
        # mais la génération qui suit remontera l'exception proprement).
        try:
            self.storage_path = _pdf_ensure_storage_path()
        except Exception:
            self.storage_path = PDF_STORAGE_PATH
        self.db_connection = db_connection
        self.last_error = None
        self.last_error_details = None

    def _build_reportlab_image(
        self,
        image_path: Optional[str],
        image_bytes: Optional[bytes],
        width_cm: float = 7.0,
        height_cm: float = 7.0,
    ):
        """
        Construit une image ReportLab depuis le fichier, puis fallback bytes BDD.
        """
        if image_path:
            normalized = os.path.normpath(str(image_path))
            if normalized.startswith("./") or normalized.startswith(".\\"):
                base_dir = os.path.dirname(os.path.dirname(__file__))
                normalized = os.path.join(base_dir, normalized.lstrip("./\\"))
            if os.path.exists(normalized):
                return Image(normalized, width=width_cm * cm, height=height_cm * cm)

        if image_bytes:
            try:
                return Image(ImageReader(io.BytesIO(image_bytes)), width=width_cm * cm, height=height_cm * cm)
            except Exception:
                return None
        return None

    def _charger_salon(self, salon_id: Optional[str]) -> Optional[Dict]:
        """Charge la fiche salon (une seule requête pour en-tête + pied de page)."""
        if not (self.db_connection and salon_id):
            return None
        try:
            from models.salon_model import SalonModel
            return SalonModel(self.db_connection).obtenir_salon_by_id(str(salon_id))
        except Exception as e:
            print(f"Erreur chargement salon PDF {salon_id}: {e}")
            return None

    def _build_footer_lines(self, salon: Optional[Dict]) -> Optional[list]:
        """
        Pied de page professionnel : nom du salon + coordonnées, sans code technique (salon_id).
        """
        if not salon:
            return None
        try:
            nom = (salon.get('nom_salon') or '').strip() or 'Salon de couture'
            responsable = (salon.get('responsable') or '').strip()
            telephone = (salon.get('telephone') or '').strip()
            email = (salon.get('email') or '').strip()

            segments = [nom]
            if responsable:
                segments.append(f"Resp.: {responsable}")
            if telephone:
                segments.append(f"Tél: {telephone}")
            if email:
                segments.append(f"Email: {email}")

            line = " | ".join(segments)
            # Ligne unique ou couper si trop longue pour le canvas
            if len(line) <= 118:
                return [line]
            row2_parts = []
            if responsable:
                row2_parts.append(f"Resp.: {responsable}")
            if telephone:
                row2_parts.append(f"Tél: {telephone}")
            if email:
                row2_parts.append(f"Email: {email}")
            return [nom, " | ".join(row2_parts)] if row2_parts else [nom]
        except Exception as e:
            print(f"Erreur construction pied de page PDF: {e}")
            return None

    def generer_pdf_commande(self, commande_data: Dict) -> Optional[str]:
        """
        Génère un PDF pour une commande

        Args:
            commande_data: Données de la commande

        Returns:
            Chemin PDF généré ou None
        """

        try:
            # Vérifier que les données essentielles sont présentes
            champs_requis = ['id', 'client_nom', 'client_prenom', 'modele']
            champs_manquants = [champ for champ in champs_requis if champ not in commande_data or commande_data[champ] is None]
            if champs_manquants:
                raise ValueError(f"Champs manquants dans commande_data: {', '.join(champs_manquants)}")
            
            # ---------------------------
            # Nettoyage nom du fichier
            # ---------------------------
            def _sanitize_filename(value: str) -> str:
                if not value:
                    return 'unknown'
                value = str(value).strip().replace(' ', '_')
                return re.sub(r"[^A-Za-z0-9_\-]", "", value)

            client_nom = _sanitize_filename(str(commande_data.get('client_nom', 'client')))
            client_prenom = _sanitize_filename(str(commande_data.get('client_prenom', '')))
            modele = _sanitize_filename(str(commande_data.get('modele', 'modele')))

            date_creation = commande_data.get('date_creation', datetime.now())
            if isinstance(date_creation, datetime):
                date_str = date_creation.strftime('%Y%m%d')
            else:
                date_str = datetime.now().strftime('%Y%m%d')

            commande_id = commande_data.get('id', 'N/A')
            nom_complet = f"{client_prenom}_{client_nom}" if client_prenom else client_nom

            filename = f"{nom_complet}_{commande_id}_{date_str}.pdf"
            filepath = os.path.join(self.storage_path, filename)

            # ---------------------------
            # Filigrane (logo PDF en arrière-plan) - Récupéré depuis la BDD
            # ---------------------------
            logo_filigrane_data = None
            
            # Récupérer salon_id depuis les données de la commande (multi-tenant)
            salon_id = None
            
            # 1. Vérifier si salon_id est directement dans commande_data
            if commande_data.get('salon_id'):
                salon_id = commande_data['salon_id']
                print(f"✅ Salon ID récupéré depuis commande_data: {salon_id}")
            
            # 2. Sinon, récupérer salon_id depuis couturier_id
            if not salon_id and self.db_connection and commande_data.get('couturier_id'):
                try:
                    cursor = self.db_connection.get_connection().cursor()
                    cursor.execute("SELECT salon_id FROM couturiers WHERE id = %s", (commande_data['couturier_id'],))
                    result = cursor.fetchone()
                    cursor.close()
                    if result and result[0]:
                        salon_id = result[0]
                        print(f"✅ Salon ID récupéré depuis couturier_id: {salon_id}")
                except Exception as e:
                    print(f"⚠️ Erreur récupération salon_id depuis couturier_id: {e}")
            
            if self.db_connection and salon_id:
                try:
                    from models.database import AppLogoModel
                    logo_model = AppLogoModel(self.db_connection)
                    logo_data = logo_model.recuperer_logo(salon_id)
                    
                    if logo_data and logo_data.get('logo_data'):
                        logo_filigrane_data = logo_data['logo_data']
                        print(f"✅ Logo filigrane chargé depuis la base de données (Salon ID: {salon_id})")
                except Exception as e:
                    print(f"Erreur récupération logo filigrane depuis BDD: {e}")
            
            salon_row = self._charger_salon(salon_id)
            logo_header_bytes = logo_filigrane_data

            def formater_date(date_obj, avec_heure=False):
                """Formate une date depuis différents formats possibles."""
                if not date_obj:
                    return "Non définie"
                if isinstance(date_obj, datetime):
                    if avec_heure:
                        return date_obj.strftime("%d/%m/%Y à %H:%M")
                    return date_obj.strftime("%d/%m/%Y")
                if isinstance(date_obj, str):
                    formats = [
                        "%Y-%m-%d %H:%M:%S",
                        "%Y-%m-%d %H:%M",
                        "%Y-%m-%d",
                        "%d/%m/%Y %H:%M:%S",
                        "%d/%m/%Y %H:%M",
                        "%d/%m/%Y",
                    ]
                    for fmt in formats:
                        try:
                            parsed = datetime.strptime(date_obj, fmt)
                            if avec_heure:
                                return parsed.strftime("%d/%m/%Y à %H:%M")
                            return parsed.strftime("%d/%m/%Y")
                        except Exception:
                            continue
                    return date_obj
                return str(date_obj)

            date_creation_str = formater_date(
                commande_data.get("date_creation"), avec_heure=True
            )
            date_livraison_str = formater_date(
                commande_data.get("date_livraison"), avec_heure=False
            )

            mesures = commande_data.get("mesures", {})
            if isinstance(mesures, str):
                try:
                    mesures = json.loads(mesures)
                except Exception:
                    mesures = {}
            if not isinstance(mesures, dict):
                mesures = {}

            prix_total = float(commande_data.get("prix_total", 0) or 0)
            avance = float(commande_data.get("avance", 0) or 0)
            reste_raw = commande_data.get("reste", None)
            if reste_raw is not None:
                reste = float(reste_raw)
            else:
                reste = max(0.0, prix_total - avance)

            client_nom_complet = (
                f"{commande_data.get('client_nom', '')} "
                f"{commande_data.get('client_prenom', '')}"
            ).strip()
            couturier_nom_complet = (
                f"{commande_data.get('couturier_prenom', '')} "
                f"{commande_data.get('couturier_nom', '')}"
            ).strip()

            # QR : texte compact (lisible par tout téléphone) + résumé JSON sans mesures
            # (les mesures gonflaient le payload et rendaient le QR illisible ou vide à la lecture).
            tel_qr = str(commande_data.get("client_telephone", "") or "").replace("|", " ").strip()
            ligne_compacte = (
                "ANSCOUT|"
                f"id={commande_data.get('id', '')}|"
                f"client={client_nom_complet.replace('|', ' ')}|"
                f"tel={tel_qr}|"
                f"total={prix_total:.0f}|avance={avance:.0f}|reste={reste:.0f}|"
                f"statut={commande_data.get('statut', '')}|"
                f"livraison={date_livraison_str}"
            )
            qr_data = {
                "commande_id": commande_data.get("id", "N/A"),
                "statut": commande_data.get("statut", "Non défini"),
                "date_creation": date_creation_str,
                "date_livraison": date_livraison_str,
                "client": {
                    "nom": commande_data.get("client_nom", ""),
                    "prenom": commande_data.get("client_prenom", ""),
                    "nom_complet": client_nom_complet,
                    "telephone": commande_data.get("client_telephone", ""),
                    "email": commande_data.get("client_email", ""),
                },
                "vetement": {
                    "categorie": commande_data.get("categorie", ""),
                    "sexe": commande_data.get("sexe", ""),
                    "modele": commande_data.get("modele", ""),
                },
                "financier": {
                    "prix_total": prix_total,
                    "avance": avance,
                    "reste": reste,
                },
                "couturier": {
                    "nom": commande_data.get("couturier_nom", ""),
                    "prenom": commande_data.get("couturier_prenom", ""),
                    "nom_complet": couturier_nom_complet,
                    "code": commande_data.get("couturier_code", ""),
                },
            }

            qr_json = json.dumps(qr_data, ensure_ascii=False, separators=(",", ":"))
            qr_payload = ligne_compacte + "\n" + qr_json
            qr = qrcode.QRCode(
                version=None,
                error_correction=qrcode.constants.ERROR_CORRECT_H,
                box_size=10,
                border=2,
            )
            qr.add_data(qr_payload)
            qr.make(fit=True)
            qr_img = qr.make_image(fill_color="#6E5D80", back_color="#FBF9F6")
            tmp_qr = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
            qr_path = tmp_qr.name
            tmp_qr.close()
            qr_img.save(qr_path)

            styles_pdf = _pdf_styles_commande()
            nom_salon_affiche = (
                (salon_row.get("nom_salon") if salon_row else "") or "Salon de couture"
            ).strip()
            numero_cmd = str(commande_data.get("id", "N/A"))

            story = []
            story.append(Paragraph(_pdf_safe_text("FICHE DE COMMANDE"), styles_pdf["document_titre"]))
            story.append(
                Paragraph(
                    _pdf_safe_text("— Confirmation officielle de réception —"),
                    styles_pdf["document_sous_titre"],
                )
            )

            statut_lc = str(commande_data.get("statut", "")).lower()
            if "livr" in statut_lc:
                statut_couleur = _P_VERT_VALIDE
            elif "cours" in statut_lc:
                statut_couleur = _P_OR_DOUX
            else:
                statut_couleur = _P_MAUVE_CLAIR

            ruban = Table(
                [
                    [
                        Paragraph(
                            f"<b>Statut : {commande_data.get('statut', 'Non défini')}</b>",
                            ParagraphStyle(
                                "RubanS",
                                fontName="Helvetica-Bold",
                                fontSize=11,
                                textColor=colors.white,
                                alignment=TA_CENTER,
                            ),
                        ),
                        Paragraph(
                            f"<b>Livraison : {date_livraison_str}</b>",
                            ParagraphStyle(
                                "RubanL",
                                fontName="Helvetica-Bold",
                                fontSize=11,
                                textColor=colors.white,
                                alignment=TA_CENTER,
                            ),
                        ),
                    ]
                ],
                colWidths=[8.75 * cm, 8.75 * cm],
            )
            ruban.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (0, 0), statut_couleur),
                        ("BACKGROUND", (1, 0), (1, 0), _P_MAUVE),
                        ("TOPPADDING", (0, 0), (-1, -1), 8),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                        ("LINEBEFORE", (1, 0), (1, 0), 2, colors.white),
                    ]
                )
            )
            story.append(ruban)
            story.append(Spacer(1, 14))

            story.append(_pdf_bandeau_section_commande("Informations de la commande"))
            story.append(Spacer(1, 4))
            story.append(
                _pdf_table_infos_commande(
                    [
                        ("Date :", date_creation_str),
                        ("Statut :", str(commande_data.get("statut", "Non défini"))),
                        ("Date de livraison :", date_livraison_str),
                    ]
                )
            )
            story.append(Spacer(1, 14))

            story.append(_pdf_bandeau_section_commande("Informations du client"))
            story.append(Spacer(1, 4))
            story.append(
                _pdf_table_infos_commande(
                    [
                        ("Nom & Prénom :", client_nom_complet or "—"),
                        (
                            "Téléphone :",
                            str(commande_data.get("client_telephone", "Non renseigné")),
                        ),
                        (
                            "Email :",
                            str(commande_data.get("client_email", "Non renseigné")),
                        ),
                    ]
                )
            )
            story.append(Spacer(1, 14))

            story.append(_pdf_bandeau_section_commande("Détails du vêtement"))
            story.append(Spacer(1, 4))
            story.append(
                _pdf_table_infos_commande(
                    [
                        (
                            "Catégorie :",
                            str(commande_data.get("categorie", "Non définie")).capitalize(),
                        ),
                        (
                            "Sexe :",
                            str(commande_data.get("sexe", "Non défini")).capitalize(),
                        ),
                        ("Modèle :", str(commande_data.get("modele", "Non défini"))),
                    ]
                )
            )
            story.append(Spacer(1, 14))

            fabric_img = self._build_reportlab_image(
                image_path=commande_data.get("fabric_image_path"),
                image_bytes=commande_data.get("fabric_image"),
                width_cm=5.8,
                height_cm=5.8,
            )
            model_img = self._build_reportlab_image(
                image_path=commande_data.get("model_image_path"),
                image_bytes=commande_data.get("model_image"),
                width_cm=5.8,
                height_cm=5.8,
            )
            ph_style = ParagraphStyle(
                "ImgPh",
                fontName="Helvetica",
                fontSize=10,
                textColor=_P_GRIS,
                alignment=TA_CENTER,
            )
            cell_f = fabric_img or Paragraph(
                "Image du tissu<br/>non disponible", ph_style
            )
            cell_m = model_img or Paragraph(
                "Image du modèle<br/>non disponible", ph_style
            )
            ligne_img = [cell_f, cell_m]
            ligne_lab = [
                Paragraph("Tissu du client", styles_pdf["legende"]),
                Paragraph("Modèle souhaité", styles_pdf["legende"]),
            ]
            t_img = Table(
                [ligne_img, ligne_lab],
                colWidths=[8.75 * cm, 8.75 * cm],
            )
            t_img.setStyle(
                TableStyle(
                    [
                        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("BOX", (0, 0), (-1, 0), 1, _P_OR_CHAMPAGNE),
                        ("INNERGRID", (0, 0), (-1, 0), 0.5, _P_GRIS_CLAIR),
                        ("TOPPADDING", (0, 0), (-1, -1), 6),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ]
                )
            )
            story.append(
                KeepTogether(
                    [
                        _pdf_bandeau_section_commande("Images de référence"),
                        Spacer(1, 6),
                        t_img,
                    ]
                )
            )
            story.append(Spacer(1, 14))

            if mesures:
                story.append(
                    KeepTogether(
                        [
                            _pdf_bandeau_section_commande("Mesures du client (en cm)"),
                            Spacer(1, 4),
                            _pdf_table_mesures_commande(mesures),
                        ]
                    )
                )
                story.append(Spacer(1, 18))

            story.append(
                KeepTogether(
                    [
                        _pdf_bandeau_section_commande("Informations financières"),
                        Spacer(1, 4),
                        _pdf_table_finances_commande(prix_total, avance, reste),
                    ]
                )
            )
            story.append(Spacer(1, 18))

            qr_block = Table(
                [
                    [
                        Image(qr_path, width=4.2 * cm, height=4.2 * cm),
                        Paragraph(
                            "<b>Code QR de vérification</b><br/><br/>"
                            "La première ligne contient un résumé lisible (client, montants, dates). "
                            "La seconde est un résumé structuré (sans mesures détaillées, pour garder un QR fiable).<br/><br/>"
                            "<font color='#C45C5C'><b>Important :</b> aucun vêtement "
                            "ne sera remis sans la présentation de ce document.</font>",
                            ParagraphStyle(
                                "QrTxt",
                                fontName="Helvetica",
                                fontSize=10,
                                textColor=_P_NOIR_DOUX,
                                leading=14,
                                alignment=TA_LEFT,
                            ),
                        ),
                    ]
                ],
                colWidths=[5 * cm, 12.5 * cm],
            )
            qr_block.setStyle(
                TableStyle(
                    [
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("BOX", (0, 0), (-1, -1), 1, _P_OR_CHAMPAGNE),
                        ("BACKGROUND", (0, 0), (-1, -1), _P_CREME),
                        ("LEFTPADDING", (0, 0), (-1, -1), 12),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                        ("TOPPADDING", (0, 0), (-1, -1), 12),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
                        ("LINEBEFORE", (0, 0), (0, -1), 4, _P_MAUVE),
                    ]
                )
            )
            story.append(
                KeepTogether(
                    [
                        _pdf_bandeau_section_commande("Authentification du document"),
                        Spacer(1, 8),
                        qr_block,
                    ]
                )
            )
            story.append(Spacer(1, 18))

            story.append(
                KeepTogether(
                    [
                        _pdf_bandeau_section_commande("Couturier en charge"),
                        Spacer(1, 4),
                        _pdf_table_infos_commande(
                            [
                                (
                                    "Nom du couturier :",
                                    couturier_nom_complet or "—",
                                ),
                                (
                                    "Code couturier :",
                                    str(commande_data.get("couturier_code", "—")),
                                ),
                            ]
                        ),
                    ]
                )
            )
            story.append(Spacer(1, 24))

            sig = Table(
                [
                    [
                        Paragraph(
                            "Signature du client",
                            ParagraphStyle(
                                "SigC",
                                fontName="Helvetica-Bold",
                                fontSize=10,
                                textColor=_P_MAUVE_FONCE,
                                alignment=TA_CENTER,
                            ),
                        ),
                        "",
                        Paragraph(
                            "Signature & cachet du salon",
                            ParagraphStyle(
                                "SigS",
                                fontName="Helvetica-Bold",
                                fontSize=10,
                                textColor=_P_MAUVE_FONCE,
                                alignment=TA_CENTER,
                            ),
                        ),
                    ],
                    ["", "", ""],
                    [
                        Paragraph(
                            "_____________________",
                            ParagraphStyle(
                                "Lin1",
                                fontName="Helvetica",
                                fontSize=10,
                                textColor=_P_GRIS,
                                alignment=TA_CENTER,
                            ),
                        ),
                        "",
                        Paragraph(
                            "_____________________",
                            ParagraphStyle(
                                "Lin2",
                                fontName="Helvetica",
                                fontSize=10,
                                textColor=_P_GRIS,
                                alignment=TA_CENTER,
                            ),
                        ),
                    ],
                ],
                colWidths=[7 * cm, 3.5 * cm, 7 * cm],
                rowHeights=[0.8 * cm, 1.6 * cm, 0.6 * cm],
            )
            sig.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
            story.append(sig)
            story.append(Spacer(1, 10))
            story.append(
                Paragraph(
                    f"Document généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')} "
                    f"— {nom_salon_affiche} © tous droits réservés",
                    styles_pdf["signature"],
                )
            )

            total_pages_ref: list = []

            def _make_on_page():
                def _on_page(c, _doc):
                    tot = total_pages_ref[0] if total_pages_ref else None
                    _pdf_dessiner_decor_commande(
                        c,
                        salon_row,
                        numero_cmd,
                        logo_header_bytes,
                        tot,
                        logo_filigrane_data,
                    )

                return _on_page

            def _build_doc(path: str):
                doc = BaseDocTemplate(
                    path,
                    pagesize=A4,
                    leftMargin=1.6 * cm,
                    rightMargin=1.6 * cm,
                    topMargin=3.8 * cm,
                    bottomMargin=2.0 * cm,
                    title="Fiche de commande",
                    author=nom_salon_affiche,
                    subject="Confirmation de commande",
                )
                frame = Frame(
                    doc.leftMargin,
                    doc.bottomMargin,
                    doc.width,
                    doc.height,
                    id="main",
                )
                doc.addPageTemplates(
                    [
                        PageTemplate(
                            id="default",
                            frames=[frame],
                            onPage=_make_on_page(),
                        ),
                    ]
                )
                doc.build(list(story))
                return doc

            fd, tmp_path = tempfile.mkstemp(suffix=".pdf")
            os.close(fd)
            try:
                _build_doc(tmp_path)
                if _PdfReader:
                    try:
                        total_pages_ref.append(len(_PdfReader(tmp_path).pages))
                    except Exception as e:
                        print(f"PDF commande — lecture nombre de pages: {e}")
                _build_doc(filepath)
            finally:
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass

            try:
                if os.path.exists(qr_path):
                    os.remove(qr_path)
            except Exception as e:
                print(f"Erreur suppression QR temporaire: {e}")

            print(f"✅ PDF généré avec succès: {filepath}")
            return filepath

        except Exception as e:
            error_msg = f"Erreur génération PDF commande: {e}"
            import traceback
            error_details = traceback.format_exc()
            _logger.error(error_msg)
            _logger.debug(error_details)
            # Stocker l'erreur dans un attribut pour que la vue puisse y accéder
            self.last_error = error_msg
            self.last_error_details = error_details
            return None

    def generer_pdf_livraison(self, commande_data: Dict) -> Optional[str]:
        """
        Génère un PDF de livraison pour une commande

        Args:
            commande_data: Données de la commande

        Returns:
            Chemin PDF généré ou None
        """
        try:
            # Vérifier que les données essentielles sont présentes
            champs_requis = ['id', 'client_nom', 'client_prenom', 'modele']
            champs_manquants = [champ for champ in champs_requis if champ not in commande_data or commande_data[champ] is None]
            if champs_manquants:
                raise ValueError(f"Champs manquants dans commande_data: {', '.join(champs_manquants)}")
            
            # Nettoyage nom du fichier
            def _sanitize_filename(value: str) -> str:
                if not value:
                    return 'unknown'
                value = str(value).strip().replace(' ', '_')
                return re.sub(r"[^A-Za-z0-9_\-]", "", value)

            client_nom = _sanitize_filename(str(commande_data.get('client_nom', 'client')))
            client_prenom = _sanitize_filename(str(commande_data.get('client_prenom', '')))
            modele = _sanitize_filename(str(commande_data.get('modele', 'modele')))

            date_creation = commande_data.get('date_creation', datetime.now())
            if isinstance(date_creation, datetime):
                date_str = date_creation.strftime('%Y%m%d')
            else:
                date_str = datetime.now().strftime('%Y%m%d')

            commande_id = commande_data.get('id', 'N/A')
            nom_complet = f"{client_prenom}_{client_nom}" if client_prenom else client_nom

            filename = f"Livraison_{nom_complet}_{commande_id}_{date_str}.pdf"
            filepath = os.path.join(self.storage_path, filename)

            # -----------------------------------------------------------------
            # Récupérer le logo depuis la BDD (multi-tenant, via AppLogoModel)
            # PRIORITÉ : table app_logo (un logo par salon_id)
            # -----------------------------------------------------------------
            logo_filigrane_data = None
            salon_id = None

            # 1) Si salon_id est déjà présent dans les données de la commande
            if commande_data.get('salon_id'):
                salon_id = commande_data['salon_id']

            # 2) Sinon, le récupérer via le couturier_id (commande → couturier → salon_id)
            if not salon_id and self.db_connection and commande_data.get('couturier_id'):
                try:
                    cursor = self.db_connection.get_connection().cursor()
                    cursor.execute("SELECT salon_id FROM couturiers WHERE id = %s", (commande_data['couturier_id'],))
                    result = cursor.fetchone()
                    cursor.close()
                    if result and result[0]:
                        salon_id = result[0]
                        print(f"✅ Salon ID récupéré depuis couturier_id pour PDF livraison: {salon_id}")
                except Exception as e:
                    print(f"⚠️ Erreur récupération salon_id pour PDF livraison depuis couturier_id: {e}")

            # 3) Utiliser AppLogoModel en priorité si on a un salon_id
            if self.db_connection and salon_id:
                try:
                    from models.database import AppLogoModel
                    logo_model = AppLogoModel(self.db_connection)
                    logo_data = logo_model.recuperer_logo(salon_id)
                    if logo_data and logo_data.get('logo_data'):
                        logo_filigrane_data = logo_data['logo_data']
                        print(f"✅ Logo filigrane (livraison) chargé depuis app_logo (Salon ID: {salon_id})")
                except Exception as e:
                    print(f"❌ Erreur récupération logo livraison depuis app_logo: {e}")

            # 5) Fallback très secondaire : ancienne colonne salons.logo si encore présente
            if not logo_filigrane_data and salon_id and self.db_connection:
                try:
                    cursor = self.db_connection.get_connection().cursor()
                    cursor.execute("SELECT logo FROM salons WHERE salon_id = %s", (salon_id,))
                    result = cursor.fetchone()
                    cursor.close()
                    if result and result[0]:
                        logo_filigrane_data = result[0]
                        print(f"⚠️ Logo filigrane (livraison) chargé depuis salons.logo (fallback, Salon ID: {salon_id})")
                except Exception as e:
                    print(f"⚠️ Erreur récupération logo BDD (fallback salons.logo) pour PDF livraison: {e}")

            salon_row = self._charger_salon(salon_id)
            footer_lines = self._build_footer_lines(salon_row)

            # Filigrane
            def dessiner_filigrane(canvas_obj, doc_obj):
                if logo_filigrane_data:
                    try:
                        logo_img = ImageReader(io.BytesIO(logo_filigrane_data))
                        img_width, img_height = logo_img.getSize()
                        aspect = img_width / float(img_height)
                        display_height = 3 * cm
                        display_width = display_height * aspect
                        x = (A4[0] - display_width) / 2
                        y = (A4[1] - display_height) / 2
                        canvas_obj.saveState()
                        canvas_obj.setFillColor(colors.HexColor('#E8E8E8'), alpha=0.1)
                        canvas_obj.drawImage(logo_img, x, y, width=display_width, height=display_height, mask='auto')
                        canvas_obj.restoreState()
                    except Exception as e:
                        print(f"Erreur dessin filigrane: {e}")

            def dessiner_footer(canvas_obj, doc_obj):
                if not footer_lines:
                    return
                try:
                    canvas_obj.saveState()
                    page_width, _ = doc_obj.pagesize
                    footer_height = 2.2 * cm
                    canvas_obj.setFillColor(colors.HexColor('#EEF2F7'))
                    canvas_obj.rect(0, 0, page_width, footer_height, fill=1, stroke=0)
                    canvas_obj.setStrokeColor(colors.HexColor('#CBD5E1'))
                    canvas_obj.setLineWidth(0.8)
                    canvas_obj.line(0, footer_height, page_width, footer_height)

                    font_name = "Helvetica"
                    max_w = page_width - 1.2 * cm
                    for idx, line in enumerate(footer_lines):
                        text = str(line)
                        fs = 8
                        while text and canvas_obj.stringWidth(text, font_name, fs) > max_w and fs > 6:
                            fs -= 1
                        canvas_obj.setFont(font_name, fs)
                        canvas_obj.setFillColor(colors.HexColor('#334155'))
                        text_width = canvas_obj.stringWidth(text, font_name, fs)
                        x = max(0.6 * cm, (page_width - text_width) / 2)
                        base_y = 0.55 * cm
                        y = base_y + idx * 0.38 * cm
                        if y < footer_height - 0.15 * cm:
                            canvas_obj.drawString(x, y, text)
                    canvas_obj.restoreState()
                except Exception as e:
                    print(f"Erreur dessin pied de page PDF livraison: {e}")

            # Création document
            doc = SimpleDocTemplate(
                filepath,
                pagesize=A4,
                rightMargin=2 * cm,
                leftMargin=2 * cm,
                topMargin=1.4 * cm,
                bottomMargin=2.6 * cm,
            )
            elements = []
            styles = getSampleStyleSheet()

            # Styles
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=22,
                textColor=colors.HexColor('#0F766E'),
                alignment=1,
                spaceAfter=10
            )

            heading_style = ParagraphStyle(
                'CustomHeading',
                parent=styles['Heading2'],
                fontSize=13,
                textColor=colors.HexColor('#0D9488'),
                spaceAfter=10
            )

            salon_tagline_style = ParagraphStyle(
                'LivraisonTagline',
                parent=styles['Normal'],
                fontSize=10,
                textColor=colors.HexColor('#64748B'),
                alignment=1,
                spaceAfter=14,
                fontName='Helvetica-Oblique',
            )

            if salon_row and (salon_row.get('nom_salon') or '').strip():
                sn = ParagraphStyle(
                    'LivraisonSalon',
                    parent=styles['Normal'],
                    fontSize=14,
                    textColor=colors.HexColor('#115E59'),
                    alignment=1,
                    spaceAfter=4,
                    fontName='Helvetica-Bold',
                )
                elements.append(Paragraph((salon_row.get('nom_salon') or '').strip(), sn))
            elements.append(Paragraph(
                "Salon de couture · bon de livraison officiel",
                salon_tagline_style
            ))
            # Titre
            elements.append(Paragraph("🚚 BON DE LIVRAISON", title_style))
            elements.append(Spacer(1, 0.5*cm))

            # Informations client
            elements.append(Paragraph("Informations du client", heading_style))
            client_data = [
                ['Nom:', f"{commande_data.get('client_prenom', '')} {commande_data.get('client_nom', '')}".strip()],
                ['Téléphone:', str(commande_data.get('client_telephone', '---'))],
                ['Email:', str(commande_data.get('client_email', 'Non renseigné'))]
            ]
            client_table = Table(client_data, colWidths=[5*cm, 10*cm])
            client_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F1F5F9')),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#1E293B')),
                ('GRID', (0, 0), (-1, -1), 0.35, colors.HexColor('#E2E8F0')),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ]))
            elements.append(client_table)
            elements.append(Spacer(1, 0.4*cm))

            # Détails commande
            elements.append(Paragraph("Détails de la commande", heading_style))
            commande_info = [
                ['Modèle:', str(commande_data.get('modele', '---'))],
                ['Date de livraison:', datetime.now().strftime('%d/%m/%Y')],
                ['Prix total:', f"{commande_data.get('prix_total', 0):,.0f} FCFA"]
            ]
            commande_table = Table(commande_info, colWidths=[5*cm, 10*cm])
            commande_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F1F5F9')),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#1E293B')),
                ('GRID', (0, 0), (-1, -1), 0.35, colors.HexColor('#E2E8F0')),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ]))
            elements.append(commande_table)
            elements.append(Spacer(1, 0.4*cm))

            # Avertissement
            warning_style = ParagraphStyle(
                'Warning',
                parent=styles['Normal'],
                fontSize=12,
                textColor=colors.HexColor('#E74C3C'),
                alignment=1,
                spaceAfter=20,
                fontName='Helvetica-Bold'
            )
            elements.append(Paragraph(
                "⚠️ IMPORTANT: Ce document est requis pour récupérer votre vêtement",
                warning_style
            ))

            # Build PDF
            def _on_page(canvas_obj, doc_obj):
                dessiner_filigrane(canvas_obj, doc_obj)
                dessiner_footer(canvas_obj, doc_obj)

            doc.build(
                elements,
                onFirstPage=_on_page,
                onLaterPages=_on_page
            )

            print(f"✅ PDF de livraison généré avec succès: {filepath}")
            return filepath

        except Exception as e:
            error_msg = f"❌ Erreur génération PDF de livraison: {e}"
            print(error_msg)
            import traceback
            error_details = traceback.format_exc()
            print(error_details)
            self.last_error = error_msg
            self.last_error_details = error_details
            return None