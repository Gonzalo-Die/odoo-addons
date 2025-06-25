# -*- coding: utf-8 -*-
import logging
from odoo import api, models
from woocommerce import API

_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def action_force_update_stock_woo(self):
        """
        Método que fuerza la actualización del stock en WooCommerce
        para este template (suma stock de sus variantes).
        """
        for template in self:
            # 1) Comprobar que el template esté marcado para Woo
            if not template.is_exported:
                _logger.warning("Omitido: template %s no marcado como 'Synced In WooCommerce'.",
                                template.id)
                continue

            # 2) Comprobar que tenga instancia configurada
            instance = template.woocomm_instance_id
            if not instance:
                _logger.warning("Omitido: template %s no tiene 'WooCommerce Instance'.", template.id)
                continue

            # 3) Crear cliente WooCommerce
            url_base = instance.shop_url.strip('/')
            try:
                woo_api = API(
                    url=url_base,
                    consumer_key=instance.wooc_consumer_key,
                    consumer_secret=instance.wooc_consumer_secret,
                    version=instance.wooc_api_version
                )
            except Exception as e:
                _logger.error("Error al crear cliente Woo: %s", e)
                continue

            # 4) Calcular stock total: sumamos qty_available de cada variante ya sincronizada
            total_qty = 0
            for variant in template.product_variant_ids:
                if variant.woocomm_variant_id:
                    total_qty += variant.qty_available

            # 5) Preparar el JSON payload con la cantidad total
            payload = {'stock_quantity': total_qty}

            # 6) Obtener el ID de Woo para el template
            tmpl_id = template.wooc_id
            if not tmpl_id:
                _logger.warning("Omitido: template %s sin 'WooCommerce ID'.", template.id)
                continue

            endpoint = f"products/{tmpl_id}"
            ref_id = f"{tmpl_id}"

            # 7) Hacer la llamada PUT a WooCommerce
            try:
                respuesta = woo_api.put(endpoint, payload)
            except Exception as ex_http:
                _logger.error("Error HTTP al actualizar stock (tmpl %s) en Woo: %s",
                              template.id, ex_http)
                continue

            # 8) Verificar el código HTTP
            status = respuesta.status_code
            if status in (200, 201):
                _logger.info("Éxito: stock en Woo actualizado (Woo ID=%s) → qty=%s",
                             ref_id, total_qty)
            else:
                _logger.error("Fallo actualización stock en Woo (Woo ID=%s). Código: %s, Mensaje: %s",
                              ref_id, status, respuesta.text)
