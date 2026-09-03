# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "synapse_pyspark"
# META   },
# META   "dependencies": {}
# META }

# MARKDOWN ********************

# # nb_02_silver_transforma · Bronze → Silver
# # Silver es la capa donde el dato deja de ser "lo que llegó" y pasa a ser **lo que el
# negocio afirma**. Aquí se decide qué es una venta válida, qué es un cliente único y
# qué significa `-18,0`.
# # En este taller Silver tiene una exigencia extra: **es la capa sobre la que se van a
# construir los tres modelos semánticos y, a través de ellos, la ontología**. Eso impone
# tres reglas que en un proyecto normal serían opcionales y aquí no lo son:
# # 1. **Nada de `decimal`.** Fabric Graph no soporta ese tipo; una columna decimal se
#    devuelve como `null` en toda consulta de la ontología. Los montos van en `double`.
# 2. **Nombres `snake_case`, sin espacios ni caracteres especiales.** Si el nombre lleva
#    espacio, `,`, `;`, `{}`, `()`, `=`, tab o salto de línea, Delta activa *column
#    mapping* y el grafo de la ontología deja de poder leer la tabla.
# 3. **Toda tabla tiene una clave única `string`.** Es la futura *entity type key*. Los
#    hechos también: `ft_venta` necesita `id_venta` aunque el modelo de BI no lo use.
# # Además dejamos **comentarios en las columnas**. No es documentación decorativa: con
# `inherit_descriptions=True`, `sempy` los convierte en descripciones del modelo
# semántico, y de ahí bajan a la ontología como contexto para los agentes.
# # ⏱️ ~20 minutos · Salida: 9 tablas en `lh_silver_polar.dbo`

# CELL ********************

%run nb_00_setup

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

from pyspark.sql import functions as F

# Escritura optimizada para lectura: Direct Lake y el grafo de la ontología
# leen estas tablas muchas más veces de las que las escribimos.
spark.conf.set("spark.sql.parquet.vorder.default", "true")
spark.conf.set("spark.databricks.delta.optimizeWrite.enabled", "true")


def a_double(col):
    """Convierte texto con coma decimal y separadores de miles a double."""
    limpio = F.regexp_replace(F.trim(col.cast("string")), r"\.", "")
    limpio = F.regexp_replace(limpio, ",", ".")
    return limpio.cast("double")


def a_bool(col):
    """Normaliza SI/Si/si/1/true → true, el resto → false."""
    return F.upper(F.trim(col.cast("string"))).isin("SI", "S", "1", "TRUE", "VERDADERO")


def clave(col):
    """Normaliza una clave de negocio: sin espacios sobrantes, en mayúsculas."""
    return F.upper(F.trim(col))


def comentar(df, comentarios: dict):
    """Adjunta comentarios a las columnas. Delta los persiste en el esquema."""
    for col, texto in comentarios.items():
        df = df.withMetadata(col, {"comment": texto})
    return df


def comentar_tabla(lakehouse: str, tabla: str, texto: str):
    """Comentario a nivel de tabla."""
    spark.sql(
        f"ALTER TABLE delta.`{ruta(lakehouse, tabla)}` "
        f"SET TBLPROPERTIES ('comment' = '{texto}')"
    )


descartes = {}


def registrar_descarte(tabla: str, motivo: str, antes: int, despues: int):
    n = antes - despues
    descartes.setdefault(tabla, []).append((motivo, n))
    if n:
        print(f"  descarta {n:>6,} filas · {tabla} · {motivo}")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## dim_tienda
# # La tienda es la **entidad puente** del taller: aparece en los tres dominios
# (vende, recibe despachos, aloja equipos de frío). Es lo que hará que la ontología
# pueda cruzar información que ningún modelo semántico tiene por separado.

# CELL ********************

dim_tienda = (
    leer(LH_BRONZE, "br_tiendas")
    .select(
        clave(F.col("ID_TIENDA")).alias("id_tienda"),
        F.trim(F.col("nombre")).alias("nombre_tienda"),
        F.trim(F.col("comuna")).alias("comuna"),
        F.trim(F.col("region")).alias("region"),
        a_double(F.col("latitud")).alias("latitud"),
        a_double(F.col("longitud")).alias("longitud"),
        F.trim(F.col("formato")).alias("formato_tienda"),
        F.col("superficie").cast("int").alias("superficie_m2"),
    )
    .dropDuplicates(["id_tienda"])
)

dim_tienda = comentar(dim_tienda, {
    "id_tienda": "Codigo unico de la tienda en la red Polar Sur. Formato T-NNN.",
    "nombre_tienda": "Nombre comercial con el que la tienda aparece al publico.",
    "comuna": "Comuna donde esta emplazada la tienda.",
    "region": "Region administrativa de Chile a la que pertenece la tienda.",
    "latitud": "Latitud geografica en grados decimales (WGS84).",
    "longitud": "Longitud geografica en grados decimales (WGS84).",
    "formato_tienda": "Formato del local: Mall, Calle o Strip Center.",
    "superficie_m2": "Superficie de sala de venta en metros cuadrados.",
})

validar_para_ontologia(dim_tienda, "dim_tienda", clave="id_tienda")
escribir(dim_tienda, LH_SILVER, "dim_tienda")
comentar_tabla(LH_SILVER, "dim_tienda",
               "Locales de la cadena Polar Sur. Entidad puente entre venta, despacho y activos de frio.")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## dim_producto y dim_cliente

# CELL ********************

dim_producto = (
    leer(LH_BRONZE, "br_productos")
    .select(
        clave(F.col("id_producto")).alias("id_producto"),
        F.trim(F.col("descripcion")).alias("nombre_producto"),
        # initcap normaliza HELADOS / Helados / helados a una sola forma.
        F.initcap(F.trim(F.col("categoria"))).alias("categoria"),
        F.initcap(F.trim(F.col("subcategoria"))).alias("subcategoria"),
        F.trim(F.col("marca")).alias("marca"),
        a_double(F.col("precio_lista")).alias("precio_lista"),
        a_bool(F.col("requiere_frio")).alias("requiere_frio"),
    )
    .dropDuplicates(["id_producto"])
)

dim_producto = comentar(dim_producto, {
    "id_producto": "Codigo unico de producto (SKU). Formato P-NNNN.",
    "nombre_producto": "Descripcion comercial del producto.",
    "categoria": "Categoria mayor del surtido: Helados, Postres congelados, Bebidas o Snacks.",
    "subcategoria": "Subcategoria dentro de la categoria: Individual, Familiar, Litro, Pack o Premium.",
    "marca": "Marca propia bajo la que se comercializa el producto.",
    "precio_lista": "Precio de lista unitario en pesos chilenos, sin descuentos.",
    "requiere_frio": "Indica si el producto exige cadena de frio continua para su conservacion.",
})

validar_para_ontologia(dim_producto, "dim_producto", clave="id_producto")
escribir(dim_producto, LH_SILVER, "dim_producto")
comentar_tabla(LH_SILVER, "dim_producto", "Catalogo de productos de Polar Sur.")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

_clientes_bronze = leer(LH_BRONZE, "br_clientes")
_antes = _clientes_bronze.count()

dim_cliente = (
    _clientes_bronze
    .select(
        clave(F.col("id_cliente")).alias("id_cliente"),
        F.trim(F.col("razon_social")).alias("nombre_cliente"),
        F.trim(F.col("segmento")).alias("segmento"),
        F.trim(F.col("comuna")).alias("comuna_cliente"),
        F.trim(F.col("region")).alias("region_cliente"),
        F.to_date(F.col("fecha_alta"), "dd-MM-yyyy").alias("fecha_alta"),
    )
    .dropDuplicates(["id_cliente"])
)
registrar_descarte("dim_cliente", "duplicados exactos del CRM", _antes, dim_cliente.count())

dim_cliente = comentar(dim_cliente, {
    "id_cliente": "Codigo unico de cliente. Formato C-NNNNN.",
    "nombre_cliente": "Razon social o nombre del cliente.",
    "segmento": "Segmento comercial: Retail, Mayorista, Institucional u Horeca.",
    "comuna_cliente": "Comuna registrada del cliente.",
    "region_cliente": "Region registrada del cliente.",
    "fecha_alta": "Fecha en que el cliente fue dado de alta en el CRM.",
})

validar_para_ontologia(dim_cliente, "dim_cliente", clave="id_cliente")
escribir(dim_cliente, LH_SILVER, "dim_cliente")
comentar_tabla(LH_SILVER, "dim_cliente", "Maestro de clientes de Polar Sur, deduplicado.")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## ft_venta
# # Aquí se aplican las reglas de calidad que definen qué cuenta como venta.
# Nótese el `withColumnRenamed`: `Monto Total` → `monto_total`. Ese renombre es la
# diferencia entre una ontología que funciona y una que devuelve nulos en silencio.

# CELL ********************

_ventas_bronze = leer(LH_BRONZE, "br_ventas")
_n0 = _ventas_bronze.count()

_ventas = (
    _ventas_bronze
    # El renombre va primero: a partir de aquí ninguna columna tiene espacios.
    .withColumnRenamed("Monto Total", "monto_total_txt")
    .select(
        clave(F.col("id_venta")).alias("id_venta"),
        clave(F.col("id_tienda")).alias("id_tienda"),
        clave(F.col("id_producto")).alias("id_producto"),
        clave(F.col("id_cliente")).alias("id_cliente"),
        F.to_date(F.col("fecha"), "dd-MM-yyyy").alias("fecha_venta"),
        F.trim(F.col("canal")).alias("canal"),
        F.col("unidades").cast("int").alias("unidades"),
        a_double(F.col("monto_total_txt")).alias("monto_total"),
    )
)

# Regla 1 · una venta sin monto no es una venta, es una incidencia del punto de venta.
_n1 = _ventas.count()
_ventas = _ventas.filter(F.col("monto_total").isNotNull())
registrar_descarte("ft_venta", "monto nulo", _n1, _ventas.count())

# Regla 2 · unidades negativas son devoluciones mal codificadas. No van al hecho de venta.
_n2 = _ventas.count()
_ventas = _ventas.filter(F.col("unidades") > 0)
registrar_descarte("ft_venta", "unidades <= 0 (devoluciones mal codificadas)", _n2, _ventas.count())

# Regla 3 · integridad referencial. Una venta a una tienda que no existe no es utilizable
# en la ontologia: la relacion quedaria colgando.
_n3 = _ventas.count()
_ventas = (
    _ventas
    .join(dim_tienda.select("id_tienda"), "id_tienda", "left_semi")
    .join(dim_producto.select("id_producto"), "id_producto", "left_semi")
    .join(dim_cliente.select("id_cliente"), "id_cliente", "left_semi")
)
registrar_descarte("ft_venta", "sin match en dimensiones", _n3, _ventas.count())

ft_venta = (
    _ventas
    .withColumn("monto_neto", F.round(F.col("monto_total") / 1.19, 2))
    .dropDuplicates(["id_venta"])
)

ft_venta = comentar(ft_venta, {
    "id_venta": "Identificador unico de la linea de venta. Formato V-NNNNNNNN.",
    "id_tienda": "Tienda donde se registro la venta. Referencia a dim_tienda.",
    "id_producto": "Producto vendido. Referencia a dim_producto.",
    "id_cliente": "Cliente al que se le facturo. Referencia a dim_cliente.",
    "fecha_venta": "Fecha de la transaccion.",
    "canal": "Canal por el que se concreto la venta: Tienda, Delivery, Retiro o App.",
    "unidades": "Cantidad de unidades vendidas. Siempre mayor que cero.",
    "monto_total": "Monto facturado en pesos chilenos, IVA incluido.",
    "monto_neto": "Monto sin IVA en pesos chilenos, calculado como monto_total dividido por 1,19.",
})

validar_para_ontologia(ft_venta, "ft_venta", clave="id_venta")
escribir(ft_venta, LH_SILVER, "ft_venta")
comentar_tabla(LH_SILVER, "ft_venta",
               "Lineas de venta validadas. Grano: una fila por linea de boleta o factura.")
print(f"\n  ft_venta conserva {ft_venta.count():,} de {_n0:,} filas de Bronze")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## Dominio operaciones · dim_ruta, dim_vehiculo, ft_despacho

# CELL ********************

dim_ruta = (
    leer(LH_BRONZE, "br_rutas")
    .select(
        clave(F.col("id_ruta")).alias("id_ruta"),
        F.trim(F.col("nombre_ruta")).alias("nombre_ruta"),
        F.trim(F.col("zona")).alias("zona"),
        a_double(F.col("distancia_km")).alias("distancia_km"),
    )
    .dropDuplicates(["id_ruta"])
)
dim_ruta = comentar(dim_ruta, {
    "id_ruta": "Codigo unico de la ruta de distribucion. Formato R-NNN.",
    "nombre_ruta": "Nombre operativo de la ruta.",
    "zona": "Zona geografica que cubre la ruta: Norte, Centro, Sur o Costa.",
    "distancia_km": "Longitud total de la ruta en kilometros.",
})
validar_para_ontologia(dim_ruta, "dim_ruta", clave="id_ruta")
escribir(dim_ruta, LH_SILVER, "dim_ruta")
comentar_tabla(LH_SILVER, "dim_ruta", "Rutas de distribucion de la flota de Polar Sur.")


dim_vehiculo = (
    leer(LH_BRONZE, "br_vehiculos")
    .select(
        clave(F.col("id_vehiculo")).alias("id_vehiculo"),
        F.upper(F.trim(F.col("patente"))).alias("patente"),
        F.trim(F.col("tipo")).alias("tipo_vehiculo"),
        F.col("capacidad_pallets").cast("int").alias("capacidad_pallets"),
        a_bool(F.col("refrigerado")).alias("tiene_refrigeracion"),
    )
    .dropDuplicates(["id_vehiculo"])
)
dim_vehiculo = comentar(dim_vehiculo, {
    "id_vehiculo": "Codigo unico del vehiculo de la flota. Formato VH-NNN.",
    "patente": "Patente unica del vehiculo.",
    "tipo_vehiculo": "Tipo de vehiculo: Camion 3/4, Furgon o Camion refrigerado.",
    "capacidad_pallets": "Capacidad maxima de carga expresada en pallets.",
    "tiene_refrigeracion": "Indica si el vehiculo mantiene cadena de frio durante el traslado.",
})
validar_para_ontologia(dim_vehiculo, "dim_vehiculo", clave="id_vehiculo")
escribir(dim_vehiculo, LH_SILVER, "dim_vehiculo")
comentar_tabla(LH_SILVER, "dim_vehiculo", "Flota de distribucion de Polar Sur.")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

_despachos = (
    leer(LH_BRONZE, "br_despachos")
    .select(
        clave(F.col("id_despacho")).alias("id_despacho"),
        clave(F.col("id_ruta")).alias("id_ruta"),
        clave(F.col("id_vehiculo")).alias("id_vehiculo"),
        clave(F.col("id_tienda")).alias("id_tienda"),
        F.to_date(F.col("fecha"), "dd-MM-yyyy").alias("fecha_despacho"),
        F.to_timestamp(F.col("hora_salida"), "yyyy-MM-dd HH:mm:ss").alias("hora_salida"),
        F.to_timestamp(F.col("hora_llegada"), "yyyy-MM-dd HH:mm:ss").alias("hora_llegada"),
        F.col("minutos_atraso").cast("int").alias("minutos_atraso"),
        F.col("unidades_despachadas").cast("int").alias("unidades_despachadas"),
        F.trim(F.col("estado")).alias("estado_despacho"),
    )
)

_n = _despachos.count()
_despachos = _despachos.join(dim_tienda.select("id_tienda"), "id_tienda", "left_semi")
registrar_descarte("ft_despacho", "tienda inexistente", _n, _despachos.count())

ft_despacho = (
    _despachos
    .withColumn("minutos_viaje",
                ((F.col("hora_llegada").cast("long") - F.col("hora_salida").cast("long")) / 60).cast("int"))
    .withColumn("llego_atrasado", F.col("minutos_atraso") > 0)
    .dropDuplicates(["id_despacho"])
)

ft_despacho = comentar(ft_despacho, {
    "id_despacho": "Identificador unico del despacho. Formato D-NNNNNNN.",
    "id_ruta": "Ruta por la que se realizo el despacho. Referencia a dim_ruta.",
    "id_vehiculo": "Vehiculo que realizo el despacho. Referencia a dim_vehiculo.",
    "id_tienda": "Tienda de destino del despacho. Referencia a dim_tienda.",
    "fecha_despacho": "Fecha en que se ejecuto el despacho.",
    "hora_salida": "Marca de tiempo de salida del centro de distribucion.",
    "hora_llegada": "Marca de tiempo de llegada a la tienda de destino.",
    "minutos_atraso": "Minutos de atraso respecto de la ventana comprometida. Cero si llego a tiempo.",
    "minutos_viaje": "Duracion total del traslado en minutos.",
    "unidades_despachadas": "Unidades fisicas entregadas en el despacho.",
    "estado_despacho": "Estado final del despacho: A tiempo o Con atraso.",
    "llego_atrasado": "Verdadero cuando el despacho registro atraso. Riesgo de quiebre de cadena de frio.",
})

validar_para_ontologia(ft_despacho, "ft_despacho", clave="id_despacho")
escribir(ft_despacho, LH_SILVER, "ft_despacho")
comentar_tabla(LH_SILVER, "ft_despacho",
               "Despachos ejecutados a tiendas. Grano: una fila por despacho.")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## Dominio activos · dim_equipo, ft_lectura_sensor

# CELL ********************

dim_equipo = (
    leer(LH_BRONZE, "br_equipos")
    .select(
        clave(F.col("id_equipo")).alias("id_equipo"),
        clave(F.col("id_tienda")).alias("id_tienda"),
        F.trim(F.col("tipo")).alias("tipo_equipo"),
        F.trim(F.col("marca_equipo")).alias("marca_equipo"),
        F.trim(F.col("modelo")).alias("modelo"),
        a_double(F.col("temperatura_objetivo")).alias("temperatura_objetivo_c"),
        F.to_date(F.col("fecha_instalacion"), "dd-MM-yyyy").alias("fecha_instalacion"),
    )
    .dropDuplicates(["id_equipo"])
)
dim_equipo = comentar(dim_equipo, {
    "id_equipo": "Codigo unico del equipo de frio. Formato EQ-NNNN.",
    "id_tienda": "Tienda donde esta instalado el equipo. Referencia a dim_tienda.",
    "tipo_equipo": "Tipo de equipo: Freezer vertical, Freezer horizontal o Camara de frio.",
    "marca_equipo": "Fabricante del equipo de frio.",
    "modelo": "Modelo del equipo segun el fabricante.",
    "temperatura_objetivo_c": "Temperatura de consigna en grados Celsius. El estandar de la cadena es -18.",
    "fecha_instalacion": "Fecha de puesta en servicio del equipo en la tienda.",
})
validar_para_ontologia(dim_equipo, "dim_equipo", clave="id_equipo")
escribir(dim_equipo, LH_SILVER, "dim_equipo")
comentar_tabla(LH_SILVER, "dim_equipo",
               "Equipos de frio instalados en tiendas. Sostienen la cadena de frio del surtido congelado.")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# Umbral de negocio: sobre -15 grados se considera excursion termica y el producto
# congelado queda en riesgo. Es una definicion del negocio, y por eso vive en Silver
# y no en cada informe.
UMBRAL_EXCURSION_C = -15.0

ft_lectura_sensor = (
    leer(LH_BRONZE, "br_lecturas_sensor")
    .select(
        clave(F.col("id_lectura")).alias("id_lectura"),
        clave(F.col("id_equipo")).alias("id_equipo"),
        F.to_timestamp(F.col("timestamp_lectura"), "yyyy-MM-dd HH:mm:ss").alias("ts_lectura"),
        a_double(F.col("temperatura")).alias("temperatura_c"),
        F.col("humedad").cast("double").alias("humedad_pct"),
        (F.col("puerta_abierta") == "1").alias("puerta_abierta"),
        (F.col("alarma") == "1").alias("alarma"),
    )
    .filter(F.col("temperatura_c").isNotNull())
    .withColumn("fecha_lectura", F.to_date(F.col("ts_lectura")))
    .withColumn("excursion_termica", F.col("temperatura_c") > F.lit(UMBRAL_EXCURSION_C))
    .dropDuplicates(["id_lectura"])
)

ft_lectura_sensor = comentar(ft_lectura_sensor, {
    "id_lectura": "Identificador unico de la lectura de sensor. Formato L-NNNNNNNNN.",
    "id_equipo": "Equipo de frio que genero la lectura. Referencia a dim_equipo.",
    "ts_lectura": "Marca de tiempo exacta de la lectura del sensor.",
    "fecha_lectura": "Fecha de la lectura, derivada de ts_lectura para agregaciones diarias.",
    "temperatura_c": "Temperatura medida en grados Celsius dentro del equipo.",
    "humedad_pct": "Humedad relativa medida en porcentaje.",
    "puerta_abierta": "Verdadero si la puerta del equipo estaba abierta al momento de la lectura.",
    "alarma": "Verdadero si el equipo emitio alarma en esa lectura.",
    "excursion_termica": (
        "Verdadero cuando la temperatura supera los -15 grados Celsius. "
        "Es el umbral bajo el cual la cadena de frio se considera rota y el producto "
        "congelado queda en riesgo."
    ),
})

validar_para_ontologia(ft_lectura_sensor, "ft_lectura_sensor", clave="id_lectura")
escribir(ft_lectura_sensor, LH_SILVER, "ft_lectura_sensor")
comentar_tabla(LH_SILVER, "ft_lectura_sensor",
               "Serie de tiempo de temperatura y humedad de los equipos de frio.")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## Resumen de calidad

# CELL ********************

TABLAS_SILVER = [
    "dim_tienda", "dim_producto", "dim_cliente", "ft_venta",
    "dim_ruta", "dim_vehiculo", "ft_despacho",
    "dim_equipo", "ft_lectura_sensor",
]

print("Silver\n")
for t in TABLAS_SILVER:
    print(f"  {t:22s} {leer(LH_SILVER, t).count():>8,} filas")

print("\nDescartes aplicados\n")
for tabla, motivos in descartes.items():
    for motivo, n in motivos:
        print(f"  {tabla:16s} {n:>6,}  {motivo}")

pct = 100 * leer(LH_SILVER, "ft_lectura_sensor").filter("excursion_termica").count() / N_LECTURAS
print(f"\n  {pct:.1f}% de las lecturas estan en excursion termica (sobre {UMBRAL_EXCURSION_C} C)")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }
