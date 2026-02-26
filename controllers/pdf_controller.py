"""
Contrôleur de génération de PDF (Controller dans MVC)
Génère un PDF complet avec QR code et logo de l'entreprise
"""

import os
import io
import json
import re
import tempfile
from datetime import datetime
from typing import Dict, Optional

# Imports ReportLab
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.utils import ImageReader

# Imports pour images et QR code
from PIL import Image as PILImage
import qrcode

# Configuration du chemin de stockage - Utiliser celui de config.py
try:
    from config import PDF_STORAGE_PATH
except ImportError:
    # Fallback si config.py n'est pas disponible
    PDF_STORAGE_PATH = os.path.join(os.path.dirname(__file__), 'pdfs')
    os.makedirs(PDF_STORAGE_PATH, exist_ok=True)


class PDFController:
    """Gère la génération de PDF pour les commandes (multi-tenant)"""

    def __init__(self, db_connection=None):
        """
        Initialise le contrôleur PDF
        
        Args:
            db_connection: Connexion à la base de données (optionnel, pour récupérer le logo)
        """
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

    def _build_footer_lines(self, salon_id: Optional[str]) -> Optional[list]:
        """
        Construit les lignes de pied de page pour un salon donné.
        Les informations proviennent exclusivement de la table salons.
        """
        if not (self.db_connection and salon_id):
            return None
        try:
            from models.salon_model import SalonModel
            salon_model = SalonModel(self.db_connection)
            salon = salon_model.obtenir_salon_by_id(str(salon_id))
            if not salon:
                return None

            nom = salon.get('nom_salon') or salon_id
            quartier = salon.get('quartier') or ''
            responsable = salon.get('responsable') or ''
            telephone = salon.get('telephone') or ''
            email = salon.get('email') or ''

            line1 = f"{nom} ({salon_id})"

            parts = []
            if quartier:
                parts.append(quartier)
            if responsable:
                parts.append(f"Resp.: {responsable}")
            if telephone:
                parts.append(f"Tél: {telephone}")
            if email:
                parts.append(f"Email: {email}")

            line2 = " | ".join(parts) if parts else ""

            lines = [line1]
            if line2:
                lines.append(line2)
            return lines
        except Exception as e:
            print(f"Erreur construction pied de page PDF pour salon {salon_id}: {e}")
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
            
            # Préparer le pied de page (informations du salon)
            footer_lines = self._build_footer_lines(salon_id)

            def dessiner_filigrane(canvas_obj, doc_obj):
                logo_img = None
                
                # Utiliser le logo depuis la BDD si disponible
                if logo_filigrane_data:
                    try:
                        logo_img = PILImage.open(io.BytesIO(logo_filigrane_data))
                        print("✅ Filigrane: Logo chargé depuis la BDD")
                    except Exception as e:
                        print(f"Erreur chargement logo filigrane depuis BDD: {e}")
                
                if not logo_img:
                    return
                
                try:
                    canvas_obj.saveState()
                    if hasattr(canvas_obj, "setFillAlpha"):
                        canvas_obj.setFillAlpha(0.12)

                    logo_img.thumbnail((300, 300), PILImage.Resampling.LANCZOS)

                    img_width = logo_img.width * 0.75
                    img_height = logo_img.height * 0.75
                    x = (A4[0] - img_width) / 2
                    y = (A4[1] - img_height) / 2

                    canvas_obj.drawImage(
                        ImageReader(logo_img),
                        x, y,
                        width=img_width,
                        height=img_height,
                        preserveAspectRatio=True
                    )
                    canvas_obj.restoreState()
                except Exception as e:
                    print(f"Erreur dessin filigrane: {e}")

            def dessiner_footer(canvas_obj, doc_obj):
                if not footer_lines:
                    return
                try:
                    canvas_obj.saveState()
                    page_width, _ = doc_obj.pagesize
                    footer_height = 2 * cm
                    # Bande de fond sur toute la largeur en bas de page
                    canvas_obj.setFillColor(colors.HexColor('#1F4ED8'))
                    canvas_obj.rect(0, 0, page_width, footer_height, fill=1, stroke=0)

                    # Texte du salon par-dessus la bande
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
                    print(f"Erreur dessin pied de page PDF commande: {e}")

            # ---------------------------
            # Création document
            # ---------------------------
            doc = SimpleDocTemplate(
                filepath,
                pagesize=A4,
                rightMargin=2*cm,
                leftMargin=2*cm
            )
            elements = []
            styles = getSampleStyleSheet()

            # Styles
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=22,
                textColor=colors.HexColor('#2C3E50'),
                alignment=1,
                spaceAfter=25
            )

            heading_style = ParagraphStyle(
                'CustomHeading',
                parent=styles['Heading2'],
                fontSize=14,
                textColor=colors.HexColor('#34495E'),
                spaceAfter=10
            )

            # ---------------------------
            # LOGO PDF - Récupéré depuis la BDD (multi-tenant) - PRIORITÉ ABSOLUE
            # ---------------------------
            logo_image = None
            
            # Utiliser le salon_id déjà récupéré (pas besoin de le récupérer à nouveau)
            # Essayer de récupérer le logo depuis la BDD en PRIORITÉ
            if self.db_connection and salon_id:
                try:
                    from models.database import AppLogoModel
                    logo_model = AppLogoModel(self.db_connection)
                    logo_data = logo_model.recuperer_logo(salon_id)
                    
                    if logo_data and logo_data.get('logo_data'):
                        # Créer une image depuis les bytes
                        logo_bytes = logo_data['logo_data']
                        # Créer un ImageReader puis une Image ReportLab
                        logo_reader = ImageReader(io.BytesIO(logo_bytes))
                        logo_image = Image(logo_reader, width=4*cm, height=4*cm)
                        print(f"✅ Logo PDF chargé depuis la base de données (Salon ID: {salon_id}): {logo_data.get('logo_name', 'logo')}")
                except Exception as e:
                    print(f"❌ Erreur récupération logo depuis BDD: {e}")
                    import traceback
                    traceback.print_exc()
            
            if logo_image:
                try:
                    # Créer une table pour centrer le logo
                    logo_table_data = [[logo_image]]
                    logo_table = Table(logo_table_data, colWidths=[15*cm])
                    logo_table.setStyle(TableStyle([
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ]))
                    elements.append(logo_table)
                except Exception as e:
                    print(f"Erreur ajout logo PDF: {e}")
                    import traceback
                    traceback.print_exc()
            else:
                print("⚠️ Logo PDF non trouvé (ni en BDD ni dans les fichiers)")
            elements.append(Spacer(1, 0.5*cm))

            elements.append(Paragraph("FICHE DE COMMANDE", title_style))

            # ---------------------------
            # Infos commande
            # ---------------------------
            elements.append(Paragraph("Informations de la commande", heading_style))

            # Formatage sécurisé de la date - Utiliser les données de la BDD
            def formater_date(date_obj, avec_heure=False):
                """Formate une date depuis différents formats possibles"""
                if not date_obj:
                    return 'Non définie'
                
                if isinstance(date_obj, datetime):
                    if avec_heure:
                        return date_obj.strftime('%d/%m/%Y à %H:%M')
                    return date_obj.strftime('%d/%m/%Y')
                
                if isinstance(date_obj, str):
                    # Essayer plusieurs formats de date courants
                    formats = [
                        '%Y-%m-%d %H:%M:%S',
                        '%Y-%m-%d %H:%M',
                        '%Y-%m-%d',
                        '%d/%m/%Y %H:%M:%S',
                        '%d/%m/%Y %H:%M',
                        '%d/%m/%Y'
                    ]
                    for fmt in formats:
                        try:
                            parsed = datetime.strptime(date_obj, fmt)
                            if avec_heure:
                                return parsed.strftime('%d/%m/%Y à %H:%M')
                            return parsed.strftime('%d/%m/%Y')
                        except:
                            continue
                    # Si aucun format ne fonctionne, retourner la string telle quelle
                    return date_obj
                
                return str(date_obj)

            date_creation_str = formater_date(commande_data.get('date_creation'), avec_heure=True)
            date_livraison_str = formater_date(commande_data.get('date_livraison'), avec_heure=False)

            info_data = [
                ['N° Commande:', str(commande_data.get('id', 'N/A'))],
                ['Date:', date_creation_str],
                ['Statut:', str(commande_data.get('statut', 'Non défini'))],
                ['Date de livraison:', date_livraison_str]
            ]

            info_table = Table(info_data, colWidths=[5*cm, 10*cm])
            info_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#ECF0F1')),
                ('GRID', (0, 0), (-1, -1), 0.4, colors.grey),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ]))
            elements.append(info_table)
            elements.append(Spacer(1, 0.4*cm))

            # ---------------------------
            # Infos client
            # ---------------------------
            elements.append(Paragraph("Informations du client", heading_style))

            client_data = [
                ['Nom:', f"{commande_data.get('client_nom', '')} {commande_data.get('client_prenom', '')}".strip()],
                ['Téléphone:', str(commande_data.get('client_telephone', 'Non renseigné'))],
                ['Email:', str(commande_data.get('client_email', 'Non renseigné'))]
            ]

            client_table = Table(client_data, colWidths=[5*cm, 10*cm])
            client_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#ECF0F1')),
                ('GRID', (0, 0), (-1, -1), 0.4, colors.grey),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ]))
            elements.append(client_table)
            elements.append(Spacer(1, 0.4*cm))

            # ---------------------------
            # Détails vêtement
            # ---------------------------
            elements.append(Paragraph("Détails du vêtement", heading_style))

            vetement_data = [
                ['Catégorie:', str(commande_data.get('categorie', 'Non définie')).capitalize()],
                ['Sexe:', str(commande_data.get('sexe', 'Non défini')).capitalize()],
                ['Modèle:', str(commande_data.get('modele', 'Non défini'))],
            ]

            vetement_table = Table(vetement_data, colWidths=[5*cm, 10*cm])
            vetement_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#ECF0F1')),
                ('GRID', (0, 0), (-1, -1), 0.4, colors.grey),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ]))
            elements.append(vetement_table)
            elements.append(Spacer(1, 0.4*cm))
            
            # ---------------------------
            # Images du tissu et du modèle
            # ---------------------------
            elements.append(Paragraph("Images de référence", heading_style))
            
            # Créer une table pour afficher les deux images côte à côte
            images_row = []
            
            # Image du tissu du client (fallback bytes BDD si le fichier n'existe plus)
            fabric_img = self._build_reportlab_image(
                image_path=commande_data.get('fabric_image_path'),
                image_bytes=commande_data.get('fabric_image'),
                width_cm=7.0,
                height_cm=7.0,
            )
            if fabric_img:
                images_row.append(fabric_img)
            else:
                images_row.append(Paragraph("Image du tissu\nnon disponible", styles['Normal']))
            
            # Image du modèle (fallback bytes BDD si le fichier n'existe plus)
            model_img = self._build_reportlab_image(
                image_path=commande_data.get('model_image_path'),
                image_bytes=commande_data.get('model_image'),
                width_cm=7.0,
                height_cm=7.0,
            )
            if model_img:
                images_row.append(model_img)
            else:
                images_row.append(Paragraph("Image du modèle\nnon disponible", styles['Normal']))
            
            # Table avec les deux images
            images_table = Table([images_row], colWidths=[7.5*cm, 7.5*cm])
            images_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('GRID', (0, 0), (-1, -1), 0.4, colors.grey),
            ]))
            elements.append(images_table)
            
            # Légendes sous les images
            legends_row = [
                Paragraph("<b>Tissu du client</b>", styles['Normal']),
                Paragraph("<b>Modèle souhaité</b>", styles['Normal'])
            ]
            legends_table = Table([legends_row], colWidths=[7.5*cm, 7.5*cm])
            legends_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            elements.append(legends_table)
            elements.append(Spacer(1, 0.4*cm))

            # ---------------------------
            # Mesures
            # ---------------------------
            elements.append(Paragraph("Mesures (en cm)", heading_style))

            mesures_data = [['Mesure', 'Valeur']]
            mesures = commande_data.get('mesures', {})
            if mesures and isinstance(mesures, dict):
                for mesure, valeur in mesures.items():
                    mesures_data.append([str(mesure), f"{valeur} cm"])
            else:
                mesures_data.append(['Aucune mesure', 'N/A'])

            mesures_table = Table(mesures_data, colWidths=[10*cm, 5*cm])
            mesures_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498DB')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('GRID', (0, 0), (-1, -1), 0.4, colors.grey)
            ]))
            elements.append(mesures_table)
            elements.append(Spacer(1, 0.4*cm))

            # ---------------------------
            # Finances
            # ---------------------------
            elements.append(Paragraph("Informations financières", heading_style))

            prix_total = float(commande_data.get('prix_total', 0))
            avance = float(commande_data.get('avance', 0))
            reste = float(commande_data.get('reste', 0))

            finance_data = [
                ['Prix total:', f"{prix_total:.2f} FCFA"],
                ['Avance versée:', f"{avance:.2f} FCFA"],
                ['Reste à payer:', f"{reste:.2f} FCFA"],
            ]

            finance_table = Table(finance_data, colWidths=[5*cm, 10*cm])
            finance_table.setStyle(TableStyle([
                ('GRID', (0, 0), (-1, -1), 0.4, colors.grey),
                ('BACKGROUND', (0, 2), (-1, 2), colors.HexColor('#E74C3C')),
                ('TEXTCOLOR', (0, 2), (-1, 2), colors.white),
                ('FONTNAME', (0, 2), (-1, 2), 'Helvetica-Bold'),
            ]))
            elements.append(finance_table)
            elements.append(Spacer(1, 0.4*cm))

            # ---------------------------
            # QR CODE - Toutes les informations de la BDD
            # ---------------------------
            elements.append(Paragraph("Code QR - Informations complètes", heading_style))

            # Préparer toutes les données pour le QR code depuis la BDD
            client_nom_complet = f"{commande_data.get('client_nom', '')} {commande_data.get('client_prenom', '')}".strip()
            couturier_nom_complet = f"{commande_data.get('couturier_prenom', '')} {commande_data.get('couturier_nom', '')}".strip()
            
            # Formatage des dates pour le QR code
            qr_date_creation = date_creation_str
            qr_date_livraison = date_livraison_str
            
            # Préparer les mesures pour le QR code
            mesures_qr = commande_data.get('mesures', {})
            if isinstance(mesures_qr, str):
                try:
                    mesures_qr = json.loads(mesures_qr)
                except:
                    mesures_qr = {}

            qr_data = {
                'commande_id': commande_data.get('id', 'N/A'),
                'statut': commande_data.get('statut', 'Non défini'),
                'date_creation': qr_date_creation,
                'date_livraison': qr_date_livraison,
                'client': {
                    'nom': commande_data.get('client_nom', ''),
                    'prenom': commande_data.get('client_prenom', ''),
                    'nom_complet': client_nom_complet,
                    'telephone': commande_data.get('client_telephone', ''),
                    'email': commande_data.get('client_email', '')
                },
                'vetement': {
                    'categorie': commande_data.get('categorie', ''),
                    'sexe': commande_data.get('sexe', ''),
                    'modele': commande_data.get('modele', ''),
                    'mesures': mesures_qr
                },
                'financier': {
                    'prix_total': prix_total,
                    'avance': avance,
                    'reste': reste
                },
                'couturier': {
                    'nom': commande_data.get('couturier_nom', ''),
                    'prenom': commande_data.get('couturier_prenom', ''),
                    'nom_complet': couturier_nom_complet,
                    'code': commande_data.get('couturier_code', '')
                }
            }

            # Générer le QR code avec toutes les informations
            qr_json = json.dumps(qr_data, ensure_ascii=False, indent=2)
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(qr_json)
            qr.make(fit=True)
            
            # Créer l'image du QR code
            qr_img = qr.make_image(fill_color="black", back_color="white")
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_qr:
                qr_path = tmp_qr.name
            qr_img.save(qr_path)

            # Centrer le QR code dans une table
            qr_table_data = [[Image(qr_path, width=5*cm, height=5*cm)]]
            qr_table = Table(qr_table_data, colWidths=[15*cm])
            qr_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            elements.append(qr_table)
            elements.append(Spacer(1, 0.3*cm))
            
            # Ajouter une description du QR code
            qr_desc_style = ParagraphStyle(
                'QRDesc',
                parent=styles['Normal'],
                fontSize=9,
                textColor=colors.HexColor('#7F8C8D'),
                alignment=1,
                fontName='Helvetica-Oblique'
            )
            elements.append(Paragraph(
                "Scannez ce code QR pour vérifier l'authenticité de ce document",
                qr_desc_style
            ))
            elements.append(Spacer(1, 0.4*cm))

            # ---------------------------
            # Avertissement
            # ---------------------------
            warning_style = ParagraphStyle(
                'Warning',
                parent=styles['Normal'],
                fontSize=12,
                textColor=colors.HexColor('#E74C3C'),
                alignment=1,
                fontName='Helvetica-Bold'
            )

            elements.append(Paragraph(
                "⚠️ Aucun vêtement ne sera retiré sans la présentation de ce document ⚠️",
                warning_style
            ))
            elements.append(Spacer(1, 0.4*cm))

            # ---------------------------
            # Couturier
            # ---------------------------
            elements.append(Paragraph("Informations du couturier", heading_style))

            couturier_data = [
                ['Nom:', f"{commande_data.get('couturier_prenom', '')} {commande_data.get('couturier_nom', '')}".strip()],
                ['Code couturier:', str(commande_data.get('couturier_code', '---'))]
            ]

            couturier_table = Table(couturier_data, colWidths=[5*cm, 10*cm])
            couturier_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#3498DB')),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                ('GRID', (0, 0), (-1, -1), 0.4, colors.grey),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ]))
            elements.append(couturier_table)
            elements.append(Spacer(1, 0.4*cm))

            # ---------------------------
            # BUILD PDF avec filigrane + pied de page
            # ---------------------------
            def _on_page(canvas_obj, doc_obj):
                dessiner_filigrane(canvas_obj, doc_obj)
                dessiner_footer(canvas_obj, doc_obj)

            doc.build(
                elements,
                onFirstPage=_on_page,
                onLaterPages=_on_page
            )

            # Nettoyage du QR code temporaire
            try:
                if os.path.exists(qr_path):
                    os.remove(qr_path)
            except Exception as e:
                print(f"Erreur suppression QR temporaire: {e}")

            print(f"✅ PDF généré avec succès: {filepath}")
            return filepath

        except Exception as e:
            error_msg = f"❌ Erreur génération PDF: {e}"
            print(error_msg)
            import traceback
            error_details = traceback.format_exc()
            print(error_details)
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

            # Préparer le pied de page (informations du salon)
            footer_lines = self._build_footer_lines(salon_id)

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
                    footer_height = 2 * cm
                    # Bande de fond sur toute la largeur en bas de page
                    canvas_obj.setFillColor(colors.HexColor('#17BEBB'))
                    canvas_obj.rect(0, 0, page_width, footer_height, fill=1, stroke=0)

                    # Texte du salon par-dessus la bande
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
                    print(f"Erreur dessin pied de page PDF livraison: {e}")

            # Création document
            doc = SimpleDocTemplate(
                filepath,
                pagesize=A4,
                rightMargin=2*cm,
                leftMargin=2*cm
            )
            elements = []
            styles = getSampleStyleSheet()

            # Styles
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=22,
                textColor=colors.HexColor('#27AE60'),
                alignment=1,
                spaceAfter=25
            )

            heading_style = ParagraphStyle(
                'CustomHeading',
                parent=styles['Heading2'],
                fontSize=14,
                textColor=colors.HexColor('#34495E'),
                spaceAfter=10
            )

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
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#27AE60')),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                ('GRID', (0, 0), (-1, -1), 0.4, colors.grey),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ]))
            elements.append(client_table)
            elements.append(Spacer(1, 0.4*cm))

            # Détails commande
            elements.append(Paragraph("Détails de la commande", heading_style))
            commande_info = [
                ['N° Commande:', str(commande_data.get('id', '---'))],
                ['Modèle:', str(commande_data.get('modele', '---'))],
                ['Date de livraison:', datetime.now().strftime('%d/%m/%Y')],
                ['Prix total:', f"{commande_data.get('prix_total', 0):,.0f} FCFA"]
            ]
            commande_table = Table(commande_info, colWidths=[5*cm, 10*cm])
            commande_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#3498DB')),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                ('GRID', (0, 0), (-1, -1), 0.4, colors.grey),
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