import os
import logging
import json
import re
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm

from app.config import settings
from app.models.conversation import Conversation

logger = logging.getLogger("hydrous")


class DirectProposalGenerator:
    """
    Generador de propuestas que evita completamente el flujo normal
    y crea la propuesta directamente con valores específicos.
    """

    async def generate_complete_proposal(self, conversation: Conversation) -> str:
        """Genera la propuesta y el PDF directamente, devuelve la ruta al PDF."""
        try:
            # 1. Extraer información de la conversación
            conversation_text = self._extract_conversation_text(conversation)

            # 2. Llamar a la API de IA con un prompt específico y directo
            proposal_text = await self._generate_proposal_with_ai(conversation_text)

            # 3. Guardar propuesta para debugging
            debug_dir = os.path.join(settings.UPLOAD_DIR, "debug")
            os.makedirs(debug_dir, exist_ok=True)
            with open(
                os.path.join(debug_dir, f"direct_proposal_{conversation.id}.txt"),
                "w",
                encoding="utf-8",
            ) as f:
                f.write(proposal_text)

            # 4. Generar PDF directamente sin pasar por otros servicios
            pdf_path = self._generate_pdf(proposal_text, conversation.id)

            # 5. Actualizar metadata
            if pdf_path:
                conversation.metadata["proposal_text"] = proposal_text
                conversation.metadata["pdf_path"] = pdf_path
                conversation.metadata["has_proposal"] = True

            return pdf_path
        except Exception as e:
            logger.error(
                f"Error en generación directa de propuesta: {e}", exc_info=True
            )
            return None

    def _extract_conversation_text(self, conversation: Conversation) -> str:
        """Extrae el texto de la conversación."""
        conversation_text = ""
        if conversation.messages:
            for msg in conversation.messages:
                role = getattr(msg, "role", "unknown")
                content = getattr(msg, "content", "")
                if content and role in ["user", "assistant"]:
                    conversation_text += f"{role.upper()}: {content}\n\n"
        return conversation_text

    async def _generate_proposal_with_ai(self, conversation_text: str) -> str:
        """Genera propuesta con la IA usando un prompt muy específico."""
        from app.services.ai_service import ai_service

        prompt = f"""
# GENERA UNA PROPUESTA PROFESIONAL DE TRATAMIENTO DE AGUA SIGUIENDO EXACTAMENTE ESTE FORMATO

Basándote en la conversación:
{conversation_text}

## INSTRUCCIONES CRÍTICAS:
1. Sé CONCISO y DIRECTO en todas las secciones - menos texto, más información concreta.
2. NUNCA uses marcadores de posición como "$X,XXX" - INVENTA cifras realistas específicas.
3. Genera tablas SIMPLES de máximo 3-4 columnas para evitar problemas de formato.
4. CALCULA valores reales para toda información financiera, especialmente ROI y ahorros.

## FORMATO EXACTO A SEGUIR:

**Hydrous Management Group -- AI-Generated Wastewater Treatment Proposal**

**Important Disclaimer**
[Breve disclaimer de 2 líneas máximo]

**1. Introduction to Hydrous Management Group**
[Máximo 3 párrafos cortos sobre la empresa]

**2. Project Background**
| **Client Information** | **Details** |
| ------------------ | --------------- |
| **Client Name** | [Nombre específico] |
| **Location** | [Ubicación] |
| **Industry** | [Sector] |
| **Water Source** | [Fuente] |
| **Current Water Consumption** | [X m³/día] |
| **Current Wastewater Generation** | [Y m³/día] |
| **Existing Treatment System** | [Sistema o "No existing treatment"] |

**3. Objective of the Project**
✓ **Regulatory Compliance** -- [1 frase específica]
✓ **Cost Optimization** -- [1 frase específica]
✓ **Water Reuse** -- [1 frase específica]
✓ **Sustainability** -- [1 frase específica]

**4. Key Design Parameters**
| **Parameter** | **Current Value** | **Target Value** |
| ------------- | --------------- | ---------------- |
| **TSS (mg/L)** | [valor] | [valor] |
| **COD (mg/L)** | [valor] | [valor] |
| **BOD (mg/L)** | [valor] | [valor] |
| **pH** | [valor] | [valor] |

**5. Recommended Treatment Process**
| **Treatment Stage** | **Technology** | **Function** |
| ------------------ | ------------- | ------------ |
| **Primary** | [tecnología específica] | [función principal] |
| **Secondary** | [tecnología específica] | [función principal] |
| **Tertiary** | [tecnología específica] | [función principal] |
| **Final** | [tecnología específica] | [función principal] |

**6. Equipment Specifications**
| **Equipment** | **Capacity** | **Est. Cost (USD)** |
| ------------- | ------------ | ------------------ |
| [Equipo 1] | [capacidad] | [costo] |
| [Equipo 2] | [capacidad] | [costo] |
| [Equipo 3] | [capacidad] | [costo] |
| [Equipo 4] | [capacidad] | [costo] |

**7. Financial Summary**

**CAPEX: $[valor total] USD**
- Equipment: $[valor] USD
- Installation: $[valor] USD
- Engineering: $[valor] USD

**Monthly OPEX: $[valor total] USD**
- Chemicals: $[valor] USD
- Energy: $[valor] USD
- Labor: $[valor] USD
- Maintenance: $[valor] USD

**8. Return on Investment Analysis**
- Current water cost: $[valor] USD/month
- Projected water cost: $[valor] USD/month
- Monthly savings: $[valor] USD
- ROI period: [X] years

**9. Next Steps**
1. Technical validation meeting
2. Site assessment
3. Detailed engineering proposal
4. Implementation schedule

Contact: info@hydrous.com | www.hydrous.com | +52 55 1234 5678
"""
        try:
            messages = [{"role": "user", "content": prompt}]
            # Usar parámetros más agresivos para forzar creatividad y especificidad
            proposal_text = await ai_service._call_llm_api(
                messages, max_tokens=7000, temperature=0.7
            )
            return proposal_text
        except Exception as e:
            logger.error(f"Error llamando a la IA: {e}", exc_info=True)
            # Propuesta de emergencia
            return self._generate_emergency_proposal()

    def _generate_emergency_proposal(self) -> str:
        """Genera una propuesta de emergencia sin IA si todo lo demás falla."""
        return """
# Propuesta de Tratamiento de Aguas Residuales - Industrias Agua Pura

## Introducción
Hydrous Management Group presenta esta propuesta técnica y económica para el tratamiento de aguas residuales industriales. Nuestra empresa se especializa en soluciones de tratamiento de agua personalizadas utilizando tecnologías avanzadas y sostenibles.

## Información del Cliente
- **Nombre:** Industrias Agua Pura
- **Ubicación:** Ciudad de México
- **Sector:** Industrial - Alimentos y Bebidas
- **Consumo actual:** 350 m³/día
- **Generación de aguas residuales:** 280 m³/día
- **Sistema actual:** No existente

## Solución Propuesta
Recomendamos un sistema integral compuesto por:
- Sistema DAF HT-5000 con capacidad de 400 m³/día
- Reactor biológico MBBR BioTech Pro con capacidad de 350 m³/día
- Sistema de filtración y desinfección UV

## Presupuesto
- **CAPEX total:** $185,000 USD
- **OPEX mensual:** $5,800 USD
- **ROI estimado:** 36 meses

Para más información, contacte a Hydrous Management Group.
"""

    def _generate_pdf(self, proposal_text: str, conversation_id: str) -> str:
        """Genera un PDF con formato a partir del texto de la propuesta."""
        try:
            # Preparar ruta
            pdf_filename = f"propuesta_{conversation_id}.pdf"
            output_path = os.path.join(settings.UPLOAD_DIR, pdf_filename)

            doc = SimpleDocTemplate(
                output_path,
                pagesize=A4,
                rightMargin=1.5 * cm,
                leftMargin=1.5 * cm,
                topMargin=2 * cm,
                bottomMargin=2 * cm,
            )

            # Definir estilos
            styles = getSampleStyleSheet()

            # Título principal
            title_style = ParagraphStyle(
                name="TitleStyle",
                parent=styles["Heading1"],
                fontSize=16,
                textColor=colors.HexColor("#0056b3"),
                spaceAfter=10,
                alignment=1,
            )

            # Encabezados de sección
            heading2_style = ParagraphStyle(
                name="Heading2Style",
                parent=styles["Heading2"],
                fontSize=14,
                textColor=colors.HexColor("#0056b3"),
                spaceAfter=8,
                spaceBefore=12,
            )

            # Texto normal
            normal_style = ParagraphStyle(
                name="NormalStyle",
                parent=styles["Normal"],
                fontSize=10,
                spaceAfter=6,
                leading=12,
            )

            # Texto en negrita (para usar dentro de párrafos)
            bold_style = ParagraphStyle(
                name="BoldStyle",
                parent=normal_style,
                fontName="Helvetica-Bold",
            )

            # Estilo para listas
            list_style = ParagraphStyle(
                name="ListStyle",
                parent=styles["Normal"],
                fontSize=10,
                leftIndent=15,
                spaceAfter=3,
                bulletIndent=8,
                leading=12,
            )

            # Elementos del PDF
            elements = []

            # Procesar líneas del texto, eliminar separadores
            lines = proposal_text.replace("---", "").split("\n")
            in_table = False
            table_data = []

            for line in lines:
                line = line.strip()
                if not line:
                    continue

                # Detectar tablas con pipe
                if "|" in line and line.count("|") >= 2:
                    if not in_table:
                        in_table = True
                        table_data = []

                    # Procesar celdas eliminando marcadores Markdown
                    cells = [cell.strip() for cell in line.split("|")]
                    cells = [c for c in cells if c]  # Eliminar celdas vacías

                    # Limpiar marcadores Markdown en celdas
                    processed_cells = []
                    for cell in cells:
                        # Eliminar guiones solitarios que son solo separadores
                        if cell.strip() == "-":
                            cell = " "
                        # Eliminar marcadores de negrita pero mantener el texto
                        if cell.startswith("**") and cell.endswith("**"):
                            cell = cell[2:-2]
                        processed_cells.append(cell)

                    if processed_cells:
                        table_data.append(processed_cells)

                # Finalizar tabla si ya no hay pipes
                elif in_table:
                    in_table = False
                    if table_data:
                        # Crear tabla con formato mejorado
                        num_cols = (
                            len(table_data[0]) if table_data and table_data[0] else 0
                        )
                        if num_cols > 0:
                            col_width = 16 * cm / num_cols
                            col_widths = [col_width] * num_cols
                            table = Table(table_data, colWidths=col_widths)

                            # Estilo para la tabla
                            table_style = TableStyle(
                                [
                                    (
                                        "BACKGROUND",
                                        (0, 0),
                                        (-1, 0),
                                        colors.HexColor("#f2f2f2"),
                                    ),
                                    (
                                        "TEXTCOLOR",
                                        (0, 0),
                                        (-1, 0),
                                        colors.HexColor("#0056b3"),
                                    ),
                                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                                    ("FONTSIZE", (0, 0), (-1, 0), 10),
                                    ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
                                    ("FONTSIZE", (0, 1), (-1, -1), 9),
                                    (
                                        "GRID",
                                        (0, 0),
                                        (-1, -1),
                                        0.25,
                                        colors.HexColor("#cccccc"),
                                    ),
                                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                                    ("PADDING", (0, 0), (-1, -1), 4),
                                    ("WORDWRAP", (0, 0), (-1, -1), True),
                                ]
                            )
                            table.setStyle(table_style)
                            elements.append(table)
                            elements.append(Spacer(1, 0.2 * cm))

                    # Procesar la línea actual según formato Markdown
                    self._process_markdown_line(
                        line,
                        elements,
                        title_style,
                        heading2_style,
                        normal_style,
                        list_style,
                    )

                # Procesar líneas normales con formato Markdown
                else:
                    self._process_markdown_line(
                        line,
                        elements,
                        title_style,
                        heading2_style,
                        normal_style,
                        list_style,
                    )

            # Si terminamos dentro de una tabla, procesarla
            if in_table and table_data:
                num_cols = len(table_data[0]) if table_data and table_data[0] else 0
                if num_cols > 0:
                    col_width = 16 * cm / num_cols
                    col_widths = [col_width] * num_cols
                    table = Table(table_data, colWidths=col_widths)
                    table_style = TableStyle(
                        [
                            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f2f2f2")),
                            ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#0056b3")),
                            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                            ("FONTSIZE", (0, 0), (-1, 0), 10),
                            ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
                            ("FONTSIZE", (0, 1), (-1, -1), 9),
                            (
                                "GRID",
                                (0, 0),
                                (-1, -1),
                                0.25,
                                colors.HexColor("#cccccc"),
                            ),
                            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                            ("PADDING", (0, 0), (-1, -1), 4),
                            ("WORDWRAP", (0, 0), (-1, -1), True),
                        ]
                    )
                    table.setStyle(table_style)
                    elements.append(table)

            # Construir PDF con números de página
            doc.build(
                elements,
                onFirstPage=self._add_page_number,
                onLaterPages=self._add_page_number,
            )

            logger.info(f"PDF generado exitosamente en: {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"Error generando PDF: {e}", exc_info=True)
            return None

    def _process_markdown_line(
        self, line, elements, title_style, heading2_style, normal_style, list_style
    ):
        """Procesa una línea con formato Markdown y añade el elemento correspondiente."""

        # 1. Procesar títulos/encabezados
        if line.startswith("# "):
            # Título principal
            elements.append(Paragraph(line[2:], title_style))
            return
        elif line.startswith("## "):
            # Subtítulo
            elements.append(Paragraph(line[3:], heading2_style))
            return

        # 2. Procesar encabezados con formato "**Título**"
        elif line.startswith("**") and line.endswith("**") and " " not in line[:5]:
            # Es un encabezado en formato Markdown
            title_text = line[2:-2]
            elements.append(Paragraph(title_text, heading2_style))
            return

        # 3. Procesar elementos de lista con checkmarks
        elif line.startswith("✓ "):
            # Extraer y formatear el texto de la lista
            list_text = line[2:]
            # Eliminar marcadores de negrita en el texto de la lista
            list_text = re.sub(r"\*\*(.*?)\*\*", r"\1", list_text)
            elements.append(Paragraph(f"✓ {list_text}", list_style))
            return
        elif line.startswith("- ") or line.startswith("* "):
            # Lista normal con viñetas
            bullet_text = line[2:]
            # Eliminar marcadores de negrita
            bullet_text = re.sub(r"\*\*(.*?)\*\*", r"\1", bullet_text)
            elements.append(Paragraph(f"• {bullet_text}", list_style))
            return

        # 4. Procesar texto normal con posible formato interno
        # Reemplazar marcadores de negrita con etiquetas <b> para ReportLab
        text = line
        # Buscar patrones **texto** y reemplazarlos con <b>texto</b>
        text = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", text)
        elements.append(Paragraph(text, normal_style))

    def _create_table(self, data):
        """Versión simplificada y robusta para crear tablas."""
        if not data or len(data) == 0:
            return Spacer(1, 0.2 * cm)

        # Ancho disponible fijo para tablas
        available_width = 16 * cm

        # Calcular número de columnas y distribuir el ancho
        num_cols = len(data[0]) if data and len(data) > 0 else 0
        if num_cols == 0:
            return Spacer(1, 0.2 * cm)

        # Limitar a máximo 4 columnas para legibilidad
        if num_cols > 4:
            logger.warning(
                f"Tabla con {num_cols} columnas detectada - limitando a 4 columnas"
            )
            for i in range(len(data)):
                if len(data[i]) > 4:
                    data[i] = data[i][:4]
            num_cols = 4

        # Distribuir ancho equitativamente
        col_widths = [available_width / num_cols] * num_cols

        # Crear tabla con anchos fijos
        table = Table(data, repeatRows=1, colWidths=col_widths)

        # Estilo mejorado
        table_style = TableStyle(
            [
                # Encabezado
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f2f2f2")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#0056b3")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 10),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
                # Cuerpo
                ("FONTSIZE", (0, 1), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cccccc")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("PADDING", (0, 0), (-1, -1), 4),
                # Crucial para evitar truncamiento
                ("WORDWRAP", (0, 0), (-1, -1), True),
            ]
        )
        table.setStyle(table_style)
        return table

    def _add_page_number(self, canvas, doc):
        """Añade número de página al pie de página."""
        canvas.saveState()
        canvas.setFont("Helvetica", 9)
        canvas.setFillColor(colors.HexColor("#555555"))
        footer_text = f"Página {canvas.getPageNumber()} | Hydrous Management Group"
        canvas.drawCentredString(doc.width / 2 + doc.leftMargin, 1 * cm, footer_text)
        canvas.restoreState()


# Instancia global
direct_proposal_generator = DirectProposalGenerator()
