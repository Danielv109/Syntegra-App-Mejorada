from datetime import datetime
from pathlib import Path
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT

from app.workers.celery_app import celery_app
from app.database import SessionLocal
from app.models.report import ReportHistory
from app.models.analytics import AnalyticsSummary, Trend
from app.models.client import Client
from app.logger import get_logger

logger = get_logger()


@celery_app.task(name="reports.generate_client_report")
def generate_client_report_task(client_id: int, user_id: int, report_config: dict):
    """
    Generar reporte PDF para un cliente
    """
    db = SessionLocal()
    logger.info(f"Generando reporte para cliente {client_id}")
    
    try:
        client = db.query(Client).filter(Client.id == client_id).first()
        if not client:
            raise ValueError(f"Cliente {client_id} no encontrado")
        
        # Obtener datos para el reporte
        metrics = db.query(AnalyticsSummary).filter(
            AnalyticsSummary.client_id == client_id
        ).order_by(AnalyticsSummary.date.desc()).limit(100).all()
        
        trends = db.query(Trend).filter(
            Trend.client_id == client_id
        ).order_by(Trend.growth_rate.desc()).limit(10).all()
        
        # Crear directorio de reportes
        reports_dir = Path("reports")
        reports_dir.mkdir(parents=True, exist_ok=True)
        
        # Nombre del archivo
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"reporte_cliente_{client_id}_{timestamp}.pdf"
        filepath = reports_dir / filename
        
        # Generar PDF
        doc = SimpleDocTemplate(str(filepath), pagesize=A4)
        story = []
        styles = getSampleStyleSheet()
        
        # Estilos personalizados
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1a1a1a'),
            spaceAfter=30,
            alignment=TA_CENTER,
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#333333'),
            spaceAfter=12,
        )
        
        # Título
        story.append(Paragraph(f"Reporte de Análisis - {client.name}", title_style))
        story.append(Spacer(1, 0.2*inch))
        
        # Fecha
        story.append(Paragraph(
            f"Generado el: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
            styles['Normal']
        ))
        story.append(Spacer(1, 0.5*inch))
        
        # Resumen ejecutivo
        story.append(Paragraph("Resumen Ejecutivo", heading_style))
        
        executive_summary = report_config.get('executive_summary', 
            f"Este reporte contiene el análisis de datos de {client.name}. "
            f"Se han analizado {len(metrics)} métricas y detectado {len(trends)} tendencias principales."
        )
        
        story.append(Paragraph(executive_summary, styles['Normal']))
        story.append(Spacer(1, 0.3*inch))
        
        # Métricas principales
        story.append(Paragraph("Métricas Principales", heading_style))
        
        if metrics:
            # Calcular scores ponderados
            weights = report_config.get('weights', {})
            scores = {}
            
            for metric in metrics[:10]:  # Top 10 métricas
                metric_type = metric.metric_name.split('_')[0]
                weight = weights.get(metric_type, 1.0)
                score = metric.metric_value * weight
                scores[metric.metric_name] = score
            
            # Tabla de métricas
            metrics_data = [['Métrica', 'Valor', 'Score Ponderado']]
            for metric in metrics[:10]:
                score = scores.get(metric.metric_name, metric.metric_value)
                metrics_data.append([
                    metric.metric_name,
                    f"{metric.metric_value:.2f}",
                    f"{score:.2f}"
                ])
            
            metrics_table = Table(metrics_data, colWidths=[3*inch, 1.5*inch, 1.5*inch])
            metrics_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            story.append(metrics_table)
            story.append(Spacer(1, 0.3*inch))
            
            # Score final
            final_score = sum(scores.values()) / len(scores) if scores else 0
            story.append(Paragraph(
                f"<b>Score Final: {final_score:.2f}/10</b>",
                styles['Normal']
            ))
        
        story.append(Spacer(1, 0.5*inch))
        
        # Tendencias
        story.append(Paragraph("Tendencias Detectadas", heading_style))
        
        if trends:
            trends_data = [['Keyword', 'Frecuencia', 'Crecimiento (%)', 'Estado']]
            for trend in trends:
                trends_data.append([
                    trend.keyword,
                    str(trend.frequency),
                    f"{trend.growth_rate:.2f}%",
                    trend.trend_status
                ])
            
            trends_table = Table(trends_data, colWidths=[2*inch, 1.5*inch, 1.5*inch, 1.5*inch])
            trends_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            story.append(trends_table)
        else:
            story.append(Paragraph("No se detectaron tendencias en el período analizado.", styles['Normal']))
        
        # Construir PDF
        doc.build(story)
        
        # Guardar registro en base de datos
        report = ReportHistory(
            client_id=client_id,
            report_type="client_analysis",
            report_name=f"Análisis {client.name}",
            file_path=str(filepath),
            parameters=report_config,
            scores=scores,
            final_score=final_score if metrics else None,
            executive_summary=executive_summary,
            generated_by=user_id,
        )
        
        db.add(report)
        db.commit()
        db.refresh(report)
        
        logger.info(f"Reporte generado exitosamente: {filepath}")
        
        return {
            "status": "success",
            "report_id": report.id,
            "filepath": str(filepath),
            "final_score": final_score if metrics else None,
        }
        
    except Exception as e:
        logger.error(f"Error generando reporte: {e}")
        db.rollback()
        raise
    finally:
        db.close()
