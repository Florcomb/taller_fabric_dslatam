# Mapa de la ontología `onto_polar_sur`

Hoja de referencia para construir la ontología en la interfaz de Fabric. Todo lo que hay que teclear está aquí.

---

## Entity types

| Entity type | Origen | Entity type key | Display name | Viene de |
|---|---|---|---|---|
| `Tienda` | `lh_silver_polar.dbo.dim_tienda` | `id_tienda` | `nombre_tienda` | Generada desde `sm_polar_ventas` |
| `Producto` | `lh_silver_polar.dbo.dim_producto` | `id_producto` | `nombre_producto` | Generada desde `sm_polar_ventas` |
| `Cliente` | `lh_silver_polar.dbo.dim_cliente` | `id_cliente` | `nombre_cliente` | Generada desde `sm_polar_ventas` |
| `Venta` | `lh_silver_polar.dbo.ft_venta` | `id_venta` | — | Generada desde `sm_polar_ventas` |
| `Despacho` | `lh_silver_polar.dbo.ft_despacho` | `id_despacho` | — | **Manual** · dominio logística |
| `Equipo` | `lh_silver_polar.dbo.dim_equipo` | `id_equipo` | `modelo` | **Manual** · dominio frío |
| `LecturaSensor` | `lh_silver_polar.dbo.ft_lectura_sensor` | `id_lectura` | — | **Manual** · dominio frío |
| `Ruta` *(opcional)* | `lh_silver_polar.dbo.dim_ruta` | `id_ruta` | `nombre_ruta` | **Manual** |
| `Vehiculo` *(opcional)* | `lh_silver_polar.dbo.dim_vehiculo` | `id_vehiculo` | `patente` | **Manual** |

> Nombres de entity type: 1–26 caracteres, alfanuméricos, guiones y guiones bajos, empezando y terminando en alfanumérico.

---

## Relationship types

| Nombre | Origen | Destino | Mapping table | Matched origen | Matched destino |
|---|---|---|---|---|---|
| `ocurre_en` | `Venta` | `Tienda` | `ft_venta` | `id_venta` | `id_tienda` |
| `contiene` | `Venta` | `Producto` | `ft_venta` | `id_venta` | `id_producto` |
| `comprada_por` | `Venta` | `Cliente` | `ft_venta` | `id_venta` | `id_cliente` |
| `entrega_en` | `Despacho` | `Tienda` | `ft_despacho` | `id_despacho` | `id_tienda` |
| `instalado_en` | `Equipo` | `Tienda` | `dim_equipo` | `id_equipo` | `id_tienda` |
| `mide` | `LecturaSensor` | `Equipo` | `ft_lectura_sensor` | `id_lectura` | `id_equipo` |
| `recorre` *(opc.)* | `Despacho` | `Ruta` | `ft_despacho` | `id_despacho` | `id_ruta` |
| `transportado_por` *(opc.)* | `Despacho` | `Vehiculo` | `ft_despacho` | `id_despacho` | `id_vehiculo` |

Las tres primeras las genera Fabric desde el modelo semántico, **definidas pero sin binding**: hay que completar mapping table y columnas *Matched* a mano. Las demás se crean completas.

### La mapping table, en una frase

Es la tabla que contiene, **en la misma fila**, las claves de las dos entidades. Es el mismo concepto que un join, con la diferencia de que se declara una vez y queda disponible para cualquier consulta futura.

---

## El grafo resultante

```
              comprada_por            contiene
   Cliente <───────────── Venta ─────────────> Producto
                            │
                        ocurre_en
                            ▼
   Despacho ──entrega_en──> Tienda <──instalado_en── Equipo
      │                                                ▲
   recorre                                           mide
      ▼                                                │
    Ruta                                        LecturaSensor
```

Desde una `LecturaSensor` se llega a un `Cliente` en cuatro saltos, cruzando tres dominios y tres modelos semánticos. Ese camino no existe en ningún modelo por separado.

---

## Propiedades por entidad

Se generan solas al enlazar la tabla. Esta lista sirve para verificar que no falte ninguna.

### Tienda
`id_tienda` · `nombre_tienda` · `comuna` · `region` · `latitud` · `longitud` · `formato_tienda` · `superficie_m2`

### Producto
`id_producto` · `nombre_producto` · `categoria` · `subcategoria` · `marca` · `precio_lista` · `requiere_frio`

### Cliente
`id_cliente` · `nombre_cliente` · `segmento` · `comuna_cliente` · `region_cliente` · `fecha_alta`

### Venta
`id_venta` · `id_tienda` · `id_producto` · `id_cliente` · `fecha_venta` · `canal` · `unidades` · `monto_total` · `monto_neto`

### Despacho
`id_despacho` · `id_ruta` · `id_vehiculo` · `id_tienda` · `fecha_despacho` · `hora_salida` · `hora_llegada` · `minutos_atraso` · `minutos_viaje` · `unidades_despachadas` · `estado_despacho` · `llego_atrasado`

### Equipo
`id_equipo` · `id_tienda` · `tipo_equipo` · `marca_equipo` · `modelo` · `temperatura_objetivo_c` · `fecha_instalacion`

### LecturaSensor
`id_lectura` · `id_equipo` · `ts_lectura` · `fecha_lectura` · `temperatura_c` · `humedad_pct` · `puerta_abierta` · `alarma` · `excursion_termica`

> **Regla de nombres.** Una propiedad con el mismo nombre debe tener el **mismo tipo** en todas las entidades donde aparezca. Por eso todos los IDs son `string`, y por eso `comuna` (Tienda) y `comuna_cliente` (Cliente) se llaman distinto: son conceptos distintos y mezclarlos habría sido peor que repetir el nombre.

---

## Enriquecimiento semántico

### Sinónimos · solo entity types

| Entity type | Sinónimos |
|---|---|
| `Tienda` | local, sucursal, punto de venta, pdv, heladeria, tiendas |
| `Producto` | articulo, sku, item, helado, surtido, productos |
| `Cliente` | comprador, cuenta, clientes |
| `Venta` | transaccion, boleta, factura, ticket, ventas |
| `Despacho` | entrega, reparto, envio, despachos |
| `Equipo` | freezer, congelador, camara de frio, equipos, activo |
| `LecturaSensor` | medicion, telemetria, lecturas, sensor |
| `Ruta` | recorrido, trayecto, rutas de reparto |
| `Vehiculo` | camion, movil, unidad de flota, flota |

**Propiedades y relaciones no aceptan sinónimos.** Solo descripción y metadata clave-valor. Si un término del negocio apunta a una propiedad —"quiebre de cadena de frío" → `excursion_termica`—, ese término entra por la **descripción**.

### Additional metadata · propiedades clave

| Propiedad | Pares clave-valor |
|---|---|
| `Venta.monto_total` | `unidad: CLP` · `incluye_iva: true` · `dueno_dato: Gerencia Comercial` |
| `Venta.monto_neto` | `unidad: CLP` · `incluye_iva: false` |
| `Venta.unidades` | `unidad: unidades` |
| `Cliente.nombre_cliente` | `sensibilidad: Confidencial` · `contiene_pii: true` |
| `Producto.precio_lista` | `unidad: CLP` |
| `Producto.requiere_frio` | `criticidad: alta` |
| `Despacho.minutos_atraso` | `unidad: minutos` · `umbral_critico: 30` |
| `Equipo.temperatura_objetivo_c` | `unidad: grados Celsius` · `estandar_cadena: -18` |
| `LecturaSensor.temperatura_c` | `unidad: grados Celsius` · `umbral_excursion: -15` · `frecuencia_muestreo: 30 minutos` |
| `LecturaSensor.excursion_termica` | `criticidad: alta` |

> Las claves deben ser **únicas dentro de cada objeto**. No se puede repetir `unidad` dos veces en la misma propiedad.

### Descripciones de relación

| Relación | Descripción |
|---|---|
| `ocurre_en` | La venta se registro en esta tienda. |
| `contiene` | La linea de venta corresponde a este producto. |
| `comprada_por` | La venta fue facturada a este cliente. |
| `entrega_en` | El despacho entrega mercaderia en la tienda de destino. |
| `instalado_en` | El equipo de frio esta fisicamente instalado en la tienda. |
| `mide` | La lectura de sensor corresponde a la medicion de un equipo de frio. |

---

## Restricciones de Fabric IQ, en una tabla

Las que condicionaron el diseño de todo el taller.

| Restricción | Consecuencia si se incumple | Cómo la cumplimos |
|---|---|---|
| Modelo en **Direct Lake** | Se generan entidades sin bindings a datos | `generate_direct_lake_semantic_model` |
| Workspace con **acceso público de entrada** | Se generan entidades sin bindings a datos | Requisito previo del taller |
| Solo tablas **managed** | La tabla no se puede enlazar | Escritura `abfss://` al directorio propio del lakehouse |
| Sin **column mapping** | La tabla devuelve vacío en el grafo | `snake_case`, sin espacios ni caracteres especiales |
| Sin lakehouse con **OneLake security** | El lakehouse no sirve como fuente | No se habilita |
| Sin tipo **`decimal`** | La propiedad devuelve `null` siempre | Montos en `double` |
| Clave `string` o `integer`, única | La entidad no tiene identidad; las relaciones no se enlazan | Todos los IDs `string`, validados en `nb_02` |
| Misma propiedad = mismo tipo en todas las entidades | La generación falla | Todos los IDs `string`; nombres diferenciados |
| **Un solo binding estático** por entidad | No se pueden combinar dos tablas en una entidad | Una entidad = una tabla Silver |
| No se puede generar desde **Mi área de trabajo** | No aparece la opción | Workspace propio |
| El grafo **no** detecta datos nuevos solo | Datos obsoletos | Refresco manual del modelo de grafo |
