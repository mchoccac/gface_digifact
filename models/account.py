# -*- encoding: utf-8 -*-

from openerp import models, fields, api, _
from openerp.exceptions import UserError, ValidationError

from datetime import datetime
from lxml import etree
from StringIO import StringIO
import base64
import cgi
import zeep

import logging

import sys
reload(sys)
sys.setdefaultencoding('utf8')

class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    firma_gface = fields.Char('Firma GFACE', copy=False)
    pdf_gface = fields.Binary('PDF GFACE', copy=False)

    def invoice_validate(self):
        detalles = []
        subtotal = 0
        for factura in self:
            if factura.journal_id.requestor_gface and not factura.firma_gface:

                FactDocGT = etree.Element("FactDocGT", xmlns="http://www.fact.com.mx/schema/gt")
                Version = etree.SubElement(FactDocGT, "Version")
                Version.text = "3"

                AsignacionSolicitada = etree.SubElement(FactDocGT, "AsignacionSolicitada")
                Serie = etree.SubElement(AsignacionSolicitada, "Serie")
                Serie.text = factura.journal_id.serie_gface
                NumeroDocumento = etree.SubElement(AsignacionSolicitada, "NumeroDocumento")
                NumeroDocumento.text = factura.number
                FechaEmision = etree.SubElement(AsignacionSolicitada, "FechaEmision")
                FechaEmision.text = fields.Date.context_today(self)+'T00:00:00'
                NumeroAutorizacion = etree.SubElement(AsignacionSolicitada, "NumeroAutorizacion")
                NumeroAutorizacion.text = factura.journal_id.numero_autorizacion_gface
                FechaResolucion = etree.SubElement(AsignacionSolicitada, "FechaResolucion")
                FechaResolucion.text = factura.journal_id.fecha_resolucion_gface
                RangoInicialAutorizado = etree.SubElement(AsignacionSolicitada, "RangoInicialAutorizado")
                RangoInicialAutorizado.text = str(factura.journal_id.rango_inicial_gface)
                RangoFinalAutorizado = etree.SubElement(AsignacionSolicitada, "RangoFinalAutorizado")
                RangoFinalAutorizado.text = str(factura.journal_id.rango_final_gface)

                Encabezado = etree.SubElement(FactDocGT, "Encabezado")
                TipoActivo = etree.SubElement(Encabezado, "TipoActivo")
                TipoActivo.text = factura.journal_id.tipo_documento_gface
                CodigoDeMoneda = etree.SubElement(Encabezado, "CodigoDeMoneda")
                CodigoDeMoneda.text = "GTQ"
                TipoDeCambio = etree.SubElement(Encabezado, "TipoDeCambio")
                TipoDeCambio.text = "1"
                InformacionDeRegimenIsr = etree.SubElement(Encabezado, "InformacionDeRegimenIsr")
                InformacionDeRegimenIsr.text = "PAGO_CAJAS"

                Vendedor = etree.SubElement(FactDocGT, "Vendedor")
                NitV = etree.SubElement(Vendedor, "Nit")
                NitV.text = factura.journal_id.nit_gface
                IdiomaV = etree.SubElement(Vendedor, "Idioma")
                IdiomaV.text = "es"
                CodigoDeEstablecimiento = etree.SubElement(Vendedor, "CodigoDeEstablecimiento")
                CodigoDeEstablecimiento.text = factura.journal_id.numero_establecimiento_gface
                DispositivoElectronico = etree.SubElement(Vendedor, "DispositivoElectronico")
                DispositivoElectronico.text = factura.journal_id.dispositivo_gface

                Comprador = etree.SubElement(FactDocGT, "Comprador")
                NitC = etree.SubElement(Comprador, "Nit")
                NitC.text = factura.partner_id.vat.replace('-','')
                if factura.partner_id.vat == 'CF':
                    NombreComercial = etree.SubElement(Comprador, "NombreComercial")
                    NombreComercial.text = factura.partner_id.vat.replace('-','')

                    DireccionComercial = etree.SubElement(Comprador, "DireccionComercial")
                    Direccion1 = etree.SubElement(DireccionComercial, "Direccion1")
                    Direccion1.text = "Ciudad"
                    Direccion2 = etree.SubElement(DireccionComercial, "Direccion2")
                    Direccion2.text = "Ciudad"
                    Municipio = etree.SubElement(DireccionComercial, "Municipio")
                    Municipio.text = "Guatemala"
                    Departamento = etree.SubElement(DireccionComercial, "Departamento")
                    Departamento.text = "Guatemala"
                    CodigoDePais = etree.SubElement(DireccionComercial, "CodigoDePais")
                    CodigoDePais.text = "GT"

                IdiomaC = etree.SubElement(Comprador, "Idioma")
                IdiomaC.text = "es"

                subtotal = 0
                total = 0
                Detalles = etree.SubElement(FactDocGT, "Detalles")
                for linea in factura.invoice_line_ids:
                    precio_total = linea.price_unit * (100-linea.discount) / 100

                    Detalle = etree.SubElement(Detalles, "Detalle")
                    Descripcion = etree.SubElement(Detalle, "Descripcion")
                    Descripcion.text = cgi.escape(linea.product_id.name)
                    CodigoEAN = etree.SubElement(Detalle, "CodigoEAN")
                    CodigoEAN.text = "00000000000000"
                    UnidadDeMedida = etree.SubElement(Detalle, "UnidadDeMedida")
                    UnidadDeMedida.text = "Uni"
                    Cantidad = etree.SubElement(Detalle, "Cantidad")
                    Cantidad.text = str(linea.quantity)

                    ValorSinDR = etree.SubElement(Detalle, "ValorSinDR")
                    PrecioSin = etree.SubElement(ValorSinDR, "Precio")
                    PrecioSin.text = str(linea.price_subtotal/linea.quantity)
                    MontoSin = etree.SubElement(ValorSinDR, "Monto")
                    MontoSin.text = str(linea.price_subtotal)

                    ValorConDR = etree.SubElement(Detalle, "ValorConDR")
                    PrecioCon = etree.SubElement(ValorConDR, "Precio")
                    PrecioCon.text = str(linea.price_subtotal/linea.quantity)
                    MontoCon = etree.SubElement(ValorConDR, "Monto")
                    MontoCon.text = str(linea.price_subtotal)

                    ImpuestosDetalle = etree.SubElement(Detalle, "Impuestos")
                    TotalDeImpuestosDetalle = etree.SubElement(ImpuestosDetalle, "TotalDeImpuestos")
                    TotalDeImpuestosDetalle.text = str(((linea.price_unit * linea.quantity * (100-linea.discount) / 100) - linea.price_subtotal ) * linea.quantity)
                    IngresosNetosGravadosDetalle = etree.SubElement(ImpuestosDetalle, "IngresosNetosGravados")
                    IngresosNetosGravadosDetalle.text = str(linea.price_subtotal)
                    TotalDeIVADetalle = etree.SubElement(ImpuestosDetalle, "TotalDeIVA")
                    TotalDeIVADetalle.text = str(((linea.price_unit * linea.quantity * (100-linea.discount) / 100) - linea.price_subtotal ) * linea.quantity)

                    ImpuestoDetalle = etree.SubElement(ImpuestosDetalle, "Impuesto")
                    TipoDetalle = etree.SubElement(ImpuestoDetalle, "Tipo")
                    TipoDetalle.text = "IVA"
                    BaseDetalle = etree.SubElement(ImpuestoDetalle, "Base")
                    BaseDetalle.text = str(precio_total)
                    TasaDetalle = etree.SubElement(ImpuestoDetalle, "Tasa")
                    TasaDetalle.text = "12"
                    MontoDetalle = etree.SubElement(ImpuestoDetalle, "Monto")
                    MontoDetalle.text = str(((linea.price_unit * linea.quantity * (100-linea.discount) / 100) - linea.price_subtotal ) * linea.quantity)

                    Categoria = etree.SubElement(Detalle, "Categoria")
                    if linea.product_id.type == 'product':
                        Categoria.text = "BIEN"
                    else:
                        Categoria.text = "SERVICIO"

                    subtotal += linea.price_subtotal
                    total += linea.price_unit * linea.quantity * (100-linea.discount) / 100

                Totales = etree.SubElement(FactDocGT, "Totales")
                SubTotalSinDR = etree.SubElement(Totales, "SubTotalSinDR")
                SubTotalSinDR.text = str(subtotal)
                SubTotalConDR = etree.SubElement(Totales, "SubTotalConDR")
                SubTotalConDR.text = str(subtotal)

                Impuestos = etree.SubElement(Totales, "Impuestos")
                TotalDeImpuestos = etree.SubElement(Impuestos, "TotalDeImpuestos")
                TotalDeImpuestos.text = str(total - subtotal)
                IngresosNetosGravados = etree.SubElement(Impuestos, "IngresosNetosGravados")
                IngresosNetosGravados.text = str(subtotal)
                TotalDeIVA = etree.SubElement(Impuestos, "TotalDeIVA")
                TotalDeIVA.text = str(total - subtotal)

                Impuesto = etree.SubElement(Impuestos, "Impuesto")
                Tipo = etree.SubElement(Impuesto, "Tipo")
                Tipo.text = "IVA"
                Base = etree.SubElement(Impuesto, "Base")
                Base.text = str(subtotal)
                Tasa = etree.SubElement(Impuesto, "Tasa")
                Tasa.text = "12"
                Monto = etree.SubElement(Impuesto, "Monto")
                Monto.text = str(total - subtotal)

                Total = etree.SubElement(Totales, "Total")
                Total.text = str(total)
                TotalLetras = etree.SubElement(Totales, "TotalLetras")
                TotalLetras.text = str(total)

                if factura.comment:
                    TextosDePie = etree.SubElement(FactDocGT, "TextosDePie")
                    Texto = etree.SubElement(Totales, "Texto")
                    Texto.text = factura.comment

                xmls = etree.tostring(FactDocGT, xml_declaration=True, encoding="UTF-8", pretty_print=True)
                logging.warn(xmls.encode('utf8'))

                wsdl = 'https://www.digifact.com.gt/mx.com.fact.wsfront/FactWSFront.asmx?wsdl'
                client = zeep.Client(wsdl=wsdl)

                resultado = client.service.RequestTransaction(factura.journal_id.requestor_gface, "CONVERT_NATIVE_XML", "GT", factura.journal_id.nit_gface, factura.journal_id.requestor_gface, "GT."+factura.journal_id.nit_gface+"."+factura.journal_id.usuario_gface, "<![CDATA["+xmls+"]]>", "XML,PDF", "")
                logging.warn(resultado)

                if resultado['Response']['Result']:
                    dte = etree.parse(StringIO(base64.b64decode(resultado['ResponseData']['ResponseData1'])))

                    pdf = resultado['ResponseData']['ResponseData3']
                    firma = dte.xpath("//*[local-name()='SignatureValue']")[0].text
                    numero = dte.xpath("//uniqueCreatorIdentification")[0].text
                    factura.pdf_gface = pdf
                    factura.firma_gface = firma
                    factura.name = numero
                else:
                    raise UserError(resultado['Response']['Description'])

        return super(AccountInvoice,self).invoice_validate()

class AccountJournal(models.Model):
    _inherit = "account.journal"

    requestor_gface = fields.Char('Requestor GFACE', copy=False)
    usuario_gface = fields.Char('Usuario GFACE', copy=False)
    nit_gface = fields.Char('NIT GFACE', copy=False)
    serie_gface = fields.Char('Serie GFACE', copy=False)
    numero_autorizacion_gface = fields.Char('Numero Autorización GFACE', copy=False)
    fecha_resolucion_gface = fields.Char('Fecha Resolución GFACE', copy=False)
    rango_inicial_gface = fields.Integer('Rango Inicial GFACE', copy=False)
    rango_final_gface = fields.Integer('Rango Final GFACE', copy=False)
    numero_establecimiento_gface = fields.Char('Numero Establecimiento GFACE', copy=False)
    dispositivo_gface = fields.Char('Dispositivo GFACE', copy=False)
    tipo_documento_gface = fields.Selection([('FACE63', 'FACE63')], 'Tipo de Documento GFACE', copy=False)


# http://soporte.solucionesprisma.com:5010/web/content/pos.order/6/pdf_gface
