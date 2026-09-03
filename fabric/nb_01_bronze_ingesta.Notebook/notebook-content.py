# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "synapse_pyspark"
# META   },
# META   "dependencies": {}
# META }

# MARKDOWN ********************

# # nb_01_bronze_ingesta · Aterrizaje en Bronze
# # Genera los datos crudos de **Polar Sur** (cadena ficticia de heladerías) y los deja
# en `lh_bronze_polar` tal como "llegarían" de los sistemas de origen: con tipos
# equivocados, duplicados, nulos y nombres inconsistentes.
# # **Regla de Bronze: no se limpia nada.** Bronze es el registro de auditoría. Lo único
# que agregamos son tres columnas de trazabilidad (`ts_ingesta`, `archivo_origen`,
# `id_lote`) que responden "¿de dónde salió esta fila y cuándo entró?".
# # La suciedad no es decorativa: cada defecto que ves aquí se corrige en `nb_02` y
# existe para justificar por qué la capa Silver no es opcional.
# # ⏱️ ~15 minutos · Salida: 9 tablas en `lh_bronze_polar.dbo`

# CELL ********************

%run nb_00_setup

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## Generación determinista
# # No usamos `rand()`. `rand()` en Spark depende del particionado, así que dos
# participantes con distinta configuración de cluster obtendrían datos distintos y
# los números del taller dejarían de coincidir.
# # En su lugar derivamos todo de `hash(columna, semilla)`: mismo input, mismo output,
# en cualquier cluster.

# CELL ********************

import uuid
from pyspark.sql import functions as F
from pyspark.sql import types as T

ID_LOTE = "lote_taller_001"


def azar(*cols, sal: int = 0):
    """Pseudo-aleatorio determinista en [0, 1) a partir de columnas + una sal."""
    return F.pmod(F.hash(*cols, F.lit(SEMILLA + sal)), F.lit(1_000_000)) / 1_000_000.0


def elegir(opciones, *cols, sal: int = 0):
    """Elige un elemento de `opciones` de forma determinista."""
    arr = F.array(*[F.lit(o) for o in opciones])
    idx = F.pmod(F.hash(*cols, F.lit(SEMILLA + sal)), F.lit(len(opciones))) + 1
    return F.element_at(arr, idx)


def sellar(df, archivo_origen: str):
    """Agrega las columnas de trazabilidad que definen la capa Bronze."""
    return (
        df.withColumn("ts_ingesta", F.current_timestamp())
        .withColumn("archivo_origen", F.lit(archivo_origen))
        .withColumn("id_lote", F.lit(ID_LOTE))
    )

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## Dominio comercial · tiendas, productos, clientes, ventas

# CELL ********************

COMUNAS = [
    ("Providencia", "Metropolitana"), ("Las Condes", "Metropolitana"),
    ("Maipu", "Metropolitana"), ("Nunoa", "Metropolitana"),
    ("Vina del Mar", "Valparaiso"), ("Valparaiso", "Valparaiso"),
    ("Concepcion", "Biobio"), ("Talcahuano", "Biobio"),
    ("La Serena", "Coquimbo"), ("Antofagasta", "Antofagasta"),
    ("Temuco", "Araucania"), ("Puerto Montt", "Los Lagos"),
]

# Las comunas se asignan por indice, no por hash: asi las 12 tiendas quedan en 12
# comunas distintas. Con hash habria colisiones y dos tiendas compartirian nombre,
# lo que despues confunde en la demo del agente ("la sucursal de Providencia").
_comunas = F.array(*[F.lit(c) for c, _ in COMUNAS])
_regiones = F.array(*[F.lit(r) for _, r in COMUNAS])

br_tiendas = (
    spark.range(N_TIENDAS)
    .withColumn("id", F.col("id").cast("int"))
    # ID con espacios y mayúsculas inconsistentes: así vienen de muchos ERP.
    .withColumn("ID_TIENDA", F.concat(F.lit("  T-"), F.lpad((F.col("id") + 1).cast("string"), 3, "0")))
    .withColumn("_i", F.pmod(F.col("id"), F.lit(len(COMUNAS))) + 1)
    .withColumn("comuna", F.element_at(_comunas, F.col("_i")))
    .withColumn("region", F.element_at(_regiones, F.col("_i")))
    .withColumn("nombre", F.concat(F.lit("Polar Sur "), F.col("comuna")))
    # Coordenadas como texto con coma decimal: clásico de exportaciones desde Excel.
    .withColumn("latitud", F.regexp_replace((F.lit(-33.45) - azar(F.col("id"), sal=2) * 8).cast("string"), r"\.", ","))
    .withColumn("longitud", F.regexp_replace((F.lit(-70.65) - azar(F.col("id"), sal=3) * 2).cast("string"), r"\.", ","))
    .withColumn("formato", elegir(["Mall", "Calle", "Strip Center"], F.col("id"), sal=4))
    .withColumn("superficie", (F.lit(60) + azar(F.col("id"), sal=5) * 140).cast("int").cast("string"))
    .drop("id", "_i")
)
escribir(sellar(br_tiendas, "erp_tiendas.csv"), LH_BRONZE, "br_tiendas")
display(br_tiendas.limit(5))

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

CATEGORIAS = ["Helados", "Postres congelados", "Bebidas", "Snacks"]
SUBCATEGORIAS = ["Individual", "Familiar", "Litro", "Pack", "Premium"]
MARCAS = ["Polar", "Antartica", "Glaciar", "Nevado"]

br_productos = (
    spark.range(N_PRODUCTOS)
    .withColumn("id", F.col("id").cast("int"))
    .withColumn("id_producto", F.concat(F.lit("P-"), F.lpad((F.col("id") + 1).cast("string"), 4, "0")))
    .withColumn("descripcion", F.concat(
        elegir(MARCAS, F.col("id"), sal=10), F.lit(" "),
        elegir(SUBCATEGORIAS, F.col("id"), sal=11), F.lit(" "),
        (F.col("id") + 1).cast("string")))
    # Categoría con mayúsculas inconsistentes: obliga a normalizar en Silver.
    .withColumn("categoria", F.when(F.col("id") % 3 == 0, F.upper(elegir(CATEGORIAS, F.col("id"), sal=12)))
                              .otherwise(elegir(CATEGORIAS, F.col("id"), sal=12)))
    .withColumn("subcategoria", elegir(SUBCATEGORIAS, F.col("id"), sal=11))
    .withColumn("marca", elegir(MARCAS, F.col("id"), sal=10))
    # Precio como texto con coma decimal y separador de miles.
    .withColumn("precio_lista", F.concat(
        (F.lit(1200) + azar(F.col("id"), sal=13) * 8800).cast("int").cast("string"),
        F.lit(",0")))
    .withColumn("requiere_frio", elegir(["SI", "Si", "si", "NO"], F.col("id"), sal=14))
    .drop("id")
)
escribir(sellar(br_productos, "pim_productos.csv"), LH_BRONZE, "br_productos")
display(br_productos.limit(5))

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

SEGMENTOS = ["Retail", "Mayorista", "Institucional", "Horeca"]

br_clientes_base = (
    spark.range(N_CLIENTES)
    .withColumn("id", F.col("id").cast("int"))
    .withColumn("id_cliente", F.concat(F.lit("C-"), F.lpad((F.col("id") + 1).cast("string"), 5, "0")))
    .withColumn("razon_social", F.concat(F.lit("Cliente "), F.lpad((F.col("id") + 1).cast("string"), 5, "0")))
    .withColumn("segmento", elegir(SEGMENTOS, F.col("id"), sal=20))
    .withColumn("comuna", elegir([c for c, _ in COMUNAS], F.col("id"), sal=21))
    .withColumn("region", elegir([r for _, r in COMUNAS], F.col("id"), sal=21))
    .withColumn("fecha_alta", F.date_format(
        F.date_add(F.to_date(F.lit("2023-01-01")), (azar(F.col("id"), sal=22) * 900).cast("int")),
        "dd-MM-yyyy"))
    .drop("id")
)

# Duplicados exactos en el 5% de los clientes: el sistema de origen los cargó dos veces.
br_clientes = br_clientes_base.unionByName(
    br_clientes_base.filter(F.pmod(F.hash(F.col("id_cliente"), F.lit(SEMILLA)), F.lit(20)) == 0)
)
escribir(sellar(br_clientes, "crm_clientes.csv"), LH_BRONZE, "br_clientes")
print(f"  incluye {br_clientes.count() - N_CLIENTES} filas duplicadas a propósito")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

CANALES = ["Tienda", "Delivery", "Retiro", "App"]

br_ventas = (
    spark.range(N_VENTAS)
    .withColumn("id", F.col("id").cast("int"))
    .withColumn("id_venta", F.concat(F.lit("V-"), F.lpad((F.col("id") + 1).cast("string"), 8, "0")))
    .withColumn("id_tienda", F.concat(F.lit("T-"), F.lpad(
        (F.pmod(F.hash(F.col("id"), F.lit(SEMILLA + 30)), F.lit(N_TIENDAS)) + 1).cast("string"), 3, "0")))
    .withColumn("id_producto", F.concat(F.lit("P-"), F.lpad(
        (F.pmod(F.hash(F.col("id"), F.lit(SEMILLA + 31)), F.lit(N_PRODUCTOS)) + 1).cast("string"), 4, "0")))
    .withColumn("id_cliente", F.concat(F.lit("C-"), F.lpad(
        (F.pmod(F.hash(F.col("id"), F.lit(SEMILLA + 32)), F.lit(N_CLIENTES)) + 1).cast("string"), 5, "0")))
    # Fecha en formato chileno como texto.
    .withColumn("fecha", F.date_format(
        F.date_add(F.to_date(F.lit(FECHA_INICIO)), (azar(F.col("id"), sal=33) * DIAS).cast("int")),
        "dd-MM-yyyy"))
    .withColumn("canal", elegir(CANALES, F.col("id"), sal=34))
    .withColumn("unidades", (F.lit(1) + azar(F.col("id"), sal=35) * 11).cast("int"))
    .withColumn("_precio", (F.lit(1200) + azar(F.col("id"), sal=36) * 8800).cast("int"))
)

br_ventas = (
    br_ventas
    # Nombre de columna CON ESPACIO: fuerza a Delta a activar column mapping.
    # Es exactamente lo que rompe una ontología si llega así hasta Silver.
    .withColumn("Monto Total", F.concat(
        (F.col("unidades") * F.col("_precio")).cast("string"), F.lit(",0")))
    # 2% de montos nulos: incidencias del punto de venta.
    .withColumn("Monto Total", F.when(
        F.pmod(F.hash(F.col("id"), F.lit(SEMILLA + 37)), F.lit(50)) == 0, F.lit(None))
        .otherwise(F.col("Monto Total")))
    # 1% de unidades negativas: devoluciones mal codificadas como ventas.
    .withColumn("unidades", F.when(
        F.pmod(F.hash(F.col("id"), F.lit(SEMILLA + 38)), F.lit(100)) == 0, -F.col("unidades"))
        .otherwise(F.col("unidades")))
    .drop("id", "_precio")
)
escribir(sellar(br_ventas, "pos_ventas.csv"), LH_BRONZE, "br_ventas")
display(br_ventas.limit(5))

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## Dominio operaciones · rutas, vehículos, despachos

# CELL ********************

ZONAS = ["Norte", "Centro", "Sur", "Costa"]
N_RUTAS = 8
N_VEHICULOS = 10

br_rutas = (
    spark.range(N_RUTAS)
    .withColumn("id", F.col("id").cast("int"))
    .withColumn("id_ruta", F.concat(F.lit("R-"), F.lpad((F.col("id") + 1).cast("string"), 3, "0")))
    .withColumn("nombre_ruta", F.concat(F.lit("Ruta "), elegir(ZONAS, F.col("id"), sal=40), F.lit(" "), (F.col("id") + 1).cast("string")))
    .withColumn("zona", elegir(ZONAS, F.col("id"), sal=40))
    .withColumn("distancia_km", F.concat((F.lit(15) + azar(F.col("id"), sal=41) * 200).cast("int").cast("string"), F.lit(",5")))
    .drop("id")
)
escribir(sellar(br_rutas, "tms_rutas.csv"), LH_BRONZE, "br_rutas")

br_vehiculos = (
    spark.range(N_VEHICULOS)
    .withColumn("id", F.col("id").cast("int"))
    .withColumn("id_vehiculo", F.concat(F.lit("VH-"), F.lpad((F.col("id") + 1).cast("string"), 3, "0")))
    .withColumn("patente", F.concat(F.lit("PSUR"), F.lpad((F.col("id") + 1).cast("string"), 2, "0")))
    .withColumn("tipo", elegir(["Camion 3/4", "Furgon", "Camion refrigerado"], F.col("id"), sal=42))
    .withColumn("capacidad_pallets", (F.lit(2) + azar(F.col("id"), sal=43) * 10).cast("int").cast("string"))
    .withColumn("refrigerado", elegir(["SI", "NO", "Si"], F.col("id"), sal=44))
    .drop("id")
)
escribir(sellar(br_vehiculos, "tms_vehiculos.csv"), LH_BRONZE, "br_vehiculos")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

br_despachos = (
    spark.range(N_DESPACHOS)
    .withColumn("id", F.col("id").cast("int"))
    .withColumn("id_despacho", F.concat(F.lit("D-"), F.lpad((F.col("id") + 1).cast("string"), 7, "0")))
    .withColumn("id_ruta", F.concat(F.lit("R-"), F.lpad(
        (F.pmod(F.hash(F.col("id"), F.lit(SEMILLA + 50)), F.lit(N_RUTAS)) + 1).cast("string"), 3, "0")))
    .withColumn("id_vehiculo", F.concat(F.lit("VH-"), F.lpad(
        (F.pmod(F.hash(F.col("id"), F.lit(SEMILLA + 51)), F.lit(N_VEHICULOS)) + 1).cast("string"), 3, "0")))
    .withColumn("id_tienda", F.concat(F.lit("T-"), F.lpad(
        (F.pmod(F.hash(F.col("id"), F.lit(SEMILLA + 52)), F.lit(N_TIENDAS)) + 1).cast("string"), 3, "0")))
    .withColumn("_fecha", F.date_add(F.to_date(F.lit(FECHA_INICIO)), (azar(F.col("id"), sal=53) * DIAS).cast("int")))
    .withColumn("fecha", F.date_format(F.col("_fecha"), "dd-MM-yyyy"))
    .withColumn("_salida_min", (F.lit(300) + azar(F.col("id"), sal=54) * 240).cast("int"))
    # El 18% de los despachos llega tarde. Ese sesgo es el que la ontología va a cruzar
    # después con la temperatura de los freezers.
    .withColumn("_atraso", F.when(
        F.pmod(F.hash(F.col("id"), F.lit(SEMILLA + 55)), F.lit(100)) < 18,
        (F.lit(20) + azar(F.col("id"), sal=56) * 160).cast("int")).otherwise(F.lit(0)))
    .withColumn("_viaje", (F.lit(45) + azar(F.col("id"), sal=57) * 120).cast("int"))
    .withColumn("hora_salida", F.date_format(
        (F.col("_fecha").cast("timestamp").cast("long") + F.col("_salida_min") * 60).cast("timestamp"),
        "yyyy-MM-dd HH:mm:ss"))
    .withColumn("hora_llegada", F.date_format(
        (F.col("_fecha").cast("timestamp").cast("long")
         + (F.col("_salida_min") + F.col("_viaje") + F.col("_atraso")) * 60).cast("timestamp"),
        "yyyy-MM-dd HH:mm:ss"))
    .withColumn("minutos_atraso", F.col("_atraso").cast("string"))
    .withColumn("unidades_despachadas", (F.lit(50) + azar(F.col("id"), sal=58) * 900).cast("int"))
    .withColumn("estado", F.when(F.col("_atraso") > 0, F.lit("Con atraso")).otherwise(F.lit("A tiempo")))
    .drop("id", "_fecha", "_salida_min", "_atraso", "_viaje")
)
escribir(sellar(br_despachos, "tms_despachos.csv"), LH_BRONZE, "br_despachos")
display(br_despachos.limit(5))

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## Dominio activos · equipos de frío y lecturas de sensor
# # Esta es la parte que ningún modelo semántico de ventas puede responder por sí solo,
# y por eso es la que justifica la ontología.

# CELL ********************

br_equipos = (
    spark.range(N_EQUIPOS)
    .withColumn("id", F.col("id").cast("int"))
    .withColumn("id_equipo", F.concat(F.lit("EQ-"), F.lpad((F.col("id") + 1).cast("string"), 4, "0")))
    .withColumn("id_tienda", F.concat(F.lit("T-"), F.lpad(
        (F.pmod(F.hash(F.col("id"), F.lit(SEMILLA + 60)), F.lit(N_TIENDAS)) + 1).cast("string"), 3, "0")))
    .withColumn("tipo", elegir(["Freezer vertical", "Freezer horizontal", "Camara de frio"], F.col("id"), sal=61))
    .withColumn("marca_equipo", elegir(["Frigus", "ColdTech", "Polarix"], F.col("id"), sal=62))
    .withColumn("modelo", F.concat(F.lit("MOD-"), (F.lit(100) + azar(F.col("id"), sal=63) * 900).cast("int").cast("string")))
    .withColumn("temperatura_objetivo", F.lit("-18,0"))
    .withColumn("fecha_instalacion", F.date_format(
        F.date_add(F.to_date(F.lit("2021-06-01")), (azar(F.col("id"), sal=64) * 1400).cast("int")), "dd-MM-yyyy"))
    .drop("id")
)
escribir(sellar(br_equipos, "cmms_equipos.csv"), LH_BRONZE, "br_equipos")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# Lecturas cada 30 minutos por equipo. La temperatura oscila en torno a -18 °C,
# pero un 6% de los equipos entra en excursión térmica (sobre -15 °C).
br_lecturas = (
    spark.range(N_LECTURAS)
    .withColumn("id", F.col("id").cast("int"))
    .withColumn("id_lectura", F.concat(F.lit("L-"), F.lpad((F.col("id") + 1).cast("string"), 9, "0")))
    .withColumn("id_equipo", F.concat(F.lit("EQ-"), F.lpad(
        (F.pmod(F.hash(F.col("id"), F.lit(SEMILLA + 70)), F.lit(N_EQUIPOS)) + 1).cast("string"), 4, "0")))
    .withColumn("_ts", (F.to_timestamp(F.lit(FECHA_INICIO)).cast("long")
                        + (azar(F.col("id"), sal=71) * DIAS * 86400).cast("long")).cast("timestamp"))
    .withColumn("timestamp_lectura", F.date_format(F.col("_ts"), "yyyy-MM-dd HH:mm:ss"))
    .withColumn("_excursion", F.pmod(F.hash(F.col("id"), F.lit(SEMILLA + 72)), F.lit(100)) < 6)
    .withColumn("temperatura", F.when(
        F.col("_excursion"), F.lit(-14.0) + azar(F.col("id"), sal=73) * 9)
        .otherwise(F.lit(-20.0) + azar(F.col("id"), sal=73) * 3.5))
    # Temperatura como texto con coma decimal.
    .withColumn("temperatura", F.regexp_replace(
        F.round(F.col("temperatura"), 2).cast("string"), r"\.", ","))
    .withColumn("humedad", F.round(F.lit(35) + azar(F.col("id"), sal=74) * 40, 1).cast("string"))
    .withColumn("puerta_abierta", elegir(["0", "1", "0", "0"], F.col("id"), sal=75))
    .withColumn("alarma", F.when(F.col("_excursion"), F.lit("1")).otherwise(F.lit("0")))
    .drop("id", "_ts", "_excursion")
)
escribir(sellar(br_lecturas, "iot_lecturas.csv"), LH_BRONZE, "br_lecturas_sensor")
display(br_lecturas.limit(5))

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## Resumen de la ingesta

# CELL ********************

TABLAS_BRONZE = [
    "br_tiendas", "br_productos", "br_clientes", "br_ventas",
    "br_rutas", "br_vehiculos", "br_despachos",
    "br_equipos", "br_lecturas_sensor",
]

print(f"Bronze · lote {ID_LOTE}\n")
for t in TABLAS_BRONZE:
    print(f"  {t:22s} {leer(LH_BRONZE, t).count():>8,} filas")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ### Qué llevamos a Silver
# # | Defecto plantado | Dónde | Se corrige en |
# |---|---|---|
# | IDs con espacios y mayúsculas | `br_tiendas.ID_TIENDA` | `nb_02` · `trim` + `upper` |
# | Decimales con coma | `latitud`, `precio_lista`, `temperatura`, `distancia_km` | `nb_02` · `regexp_replace` + cast a `double` |
# | Fechas `dd-MM-yyyy` como texto | `br_ventas.fecha`, `br_clientes.fecha_alta` | `nb_02` · `to_date` con formato explícito |
# | Nombre de columna con espacio | `br_ventas."Monto Total"` | `nb_02` · renombrar a `monto_total` |
# | Clientes duplicados | `br_clientes` | `nb_02` · `dropDuplicates` |
# | Montos nulos (2%) | `br_ventas` | `nb_02` · descarte con registro del conteo |
# | Unidades negativas (1%) | `br_ventas` | `nb_02` · descarte |
# | Booleanos como `SI`/`Si`/`si`/`NO` | `requiere_frio`, `refrigerado` | `nb_02` · normalización a `boolean` |
# # El de la columna con espacio es el más importante del taller: si esa columna llegara
# así a Silver, Delta activaría *column mapping* en la tabla y **la ontología no podría
# leerla**, sin ningún mensaje de error que lo explique.

# CELL ********************

# Comprobación de que el defecto está realmente ahí (lo vamos a arreglar en nb_02).
print("Columnas de br_ventas:")
for c in leer(LH_BRONZE, "br_ventas").columns:
    marca = "  <-- con espacio" if " " in c else ""
    print(f"  {c}{marca}")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }
