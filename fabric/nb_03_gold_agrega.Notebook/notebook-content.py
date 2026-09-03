# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "synapse_pyspark"
# META   },
# META   "dependencies": {}
# META }

# MARKDOWN ********************

# # nb_03_gold_agrega · Silver → Gold
# # Gold es la capa de **respuestas pre-calculadas**: agregados por día que un informe de
# Power BI puede leer sin recorrer millones de filas.
# # Ojo con una decisión de diseño del taller, que suele generar discusión:
# # > Los tres modelos semánticos del taller se construyen sobre **Silver**, no sobre Gold.
# # No es un descuido. La ontología necesita **entidades a grano atómico**: una fila = una
# venta, un despacho, una lectura. Un agregado diario no es una entidad de negocio, es un
# resumen; no tiene identidad propia ni participa en relaciones. Gold sigue existiendo y
# sigue siendo la capa correcta para BI — pero BI y ontología quieren cosas distintas, y
# ese es justamente uno de los aprendizajes del taller.
# # La última tabla de este notebook es el argumento completo: para responder una sola
# pregunta que cruza los tres dominios hay que escribir a mano un join de cinco tablas
# y materializarlo. Cada pregunta nueva, una tabla nueva. La ontología evita exactamente eso.
# # ⏱️ ~10 minutos · Salida: 4 tablas en `lh_gold_polar.dbo`

# CELL ********************

%run nb_00_setup

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

from pyspark.sql import functions as F

# Perfil de lectura intensiva: es lo que consume Power BI.
spark.conf.set("spark.sql.parquet.vorder.default", "true")
spark.conf.set("spark.databricks.delta.optimizeWrite.enabled", "true")
spark.conf.set("spark.databricks.delta.optimizeWrite.binSize", "1g")

dim_tienda = leer(LH_SILVER, "dim_tienda")
dim_producto = leer(LH_SILVER, "dim_producto")
dim_equipo = leer(LH_SILVER, "dim_equipo")
ft_venta = leer(LH_SILVER, "ft_venta")
ft_despacho = leer(LH_SILVER, "ft_despacho")
ft_lectura = leer(LH_SILVER, "ft_lectura_sensor")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## Agregados por dominio

# CELL ********************

agg_venta_dia_tienda = (
    ft_venta
    .join(dim_tienda.select("id_tienda", "nombre_tienda", "region", "comuna"), "id_tienda")
    .join(dim_producto.select("id_producto", "categoria"), "id_producto")
    .groupBy("fecha_venta", "id_tienda", "nombre_tienda", "region", "comuna", "categoria")
    .agg(
        F.countDistinct("id_venta").alias("transacciones"),
        F.sum("unidades").alias("unidades_vendidas"),
        F.round(F.sum("monto_total"), 0).alias("venta_total"),
        F.round(F.sum("monto_neto"), 0).alias("venta_neta"),
        F.countDistinct("id_cliente").alias("clientes_distintos"),
    )
)
escribir(agg_venta_dia_tienda, LH_GOLD, "agg_venta_dia_tienda")


agg_despacho_dia_ruta = (
    ft_despacho
    .groupBy("fecha_despacho", "id_ruta")
    .agg(
        F.count("id_despacho").alias("despachos"),
        F.sum(F.col("llego_atrasado").cast("int")).alias("despachos_atrasados"),
        F.round(F.avg("minutos_atraso"), 1).alias("atraso_promedio_min"),
        F.round(F.avg("minutos_viaje"), 1).alias("viaje_promedio_min"),
        F.sum("unidades_despachadas").alias("unidades_despachadas"),
    )
    .withColumn("tasa_atraso",
                F.round(F.col("despachos_atrasados") / F.col("despachos"), 3))
)
escribir(agg_despacho_dia_ruta, LH_GOLD, "agg_despacho_dia_ruta")


agg_frio_dia_equipo = (
    ft_lectura
    .groupBy("fecha_lectura", "id_equipo")
    .agg(
        F.count("id_lectura").alias("lecturas"),
        F.round(F.avg("temperatura_c"), 2).alias("temperatura_promedio_c"),
        F.round(F.max("temperatura_c"), 2).alias("temperatura_maxima_c"),
        F.sum(F.col("excursion_termica").cast("int")).alias("lecturas_en_excursion"),
        F.sum(F.col("alarma").cast("int")).alias("lecturas_con_alarma"),
    )
    .withColumn("horas_en_excursion",
                F.round(F.col("lecturas_en_excursion") * 0.5, 1))
)
escribir(agg_frio_dia_equipo, LH_GOLD, "agg_frio_dia_equipo")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## La tabla que justifica la ontología
# # Pregunta de negocio:
# # > *¿Cuánta venta de producto congelado ocurrió en tiendas que ese mismo día tuvieron
# > un freezer en excursión térmica y recibieron un despacho atrasado?*
# # Ningún modelo semántico del taller puede responderla: la venta está en uno, el
# despacho en otro y la temperatura en un tercero. Para contestarla en Gold hay que
# escribir **este** join a mano y materializarlo.
# # Cuenta las líneas. Después, en el paso de la ontología, la misma pregunta se hace
# en lenguaje natural sin escribir ningún join.

# CELL ********************

# Día-tienda con al menos un equipo en excursión térmica.
riesgo_frio = (
    ft_lectura
    .join(dim_equipo.select("id_equipo", "id_tienda"), "id_equipo")
    .groupBy("fecha_lectura", "id_tienda")
    .agg(
        F.sum(F.col("excursion_termica").cast("int")).alias("lecturas_en_excursion"),
        F.round(F.max("temperatura_c"), 2).alias("temperatura_maxima_c"),
        F.countDistinct(F.when(F.col("excursion_termica"), F.col("id_equipo"))).alias("equipos_afectados"),
    )
    .filter(F.col("lecturas_en_excursion") > 0)
    .withColumnRenamed("fecha_lectura", "fecha")
)

# Día-tienda con al menos un despacho atrasado.
riesgo_despacho = (
    ft_despacho
    .filter(F.col("llego_atrasado"))
    .groupBy("fecha_despacho", "id_tienda")
    .agg(
        F.count("id_despacho").alias("despachos_atrasados"),
        F.max("minutos_atraso").alias("atraso_maximo_min"),
    )
    .withColumnRenamed("fecha_despacho", "fecha")
)

# Venta de producto que exige cadena de frío.
venta_congelado = (
    ft_venta
    .join(dim_producto.filter("requiere_frio").select("id_producto", "categoria"), "id_producto")
    .groupBy(F.col("fecha_venta").alias("fecha"), "id_tienda")
    .agg(
        F.round(F.sum("monto_total"), 0).alias("venta_congelado"),
        F.sum("unidades").alias("unidades_congelado"),
    )
)

agg_riesgo_cadena_frio = (
    venta_congelado
    .join(riesgo_frio, ["fecha", "id_tienda"])
    .join(riesgo_despacho, ["fecha", "id_tienda"])
    .join(dim_tienda.select("id_tienda", "nombre_tienda", "region"), "id_tienda")
    .select(
        "fecha", "id_tienda", "nombre_tienda", "region",
        "venta_congelado", "unidades_congelado",
        "equipos_afectados", "lecturas_en_excursion", "temperatura_maxima_c",
        "despachos_atrasados", "atraso_maximo_min",
    )
)
escribir(agg_riesgo_cadena_frio, LH_GOLD, "agg_riesgo_cadena_frio")

print("\nTop 10 dias-tienda con venta de congelado en riesgo:")
display(agg_riesgo_cadena_frio.orderBy(F.desc("venta_congelado")).limit(10))

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

total_riesgo = agg_riesgo_cadena_frio.agg(F.sum("venta_congelado")).collect()[0][0] or 0
print(f"Venta de congelado expuesta a riesgo de cadena de frio: ${total_riesgo:,.0f} CLP")
print(f"Dias-tienda afectados: {agg_riesgo_cadena_frio.count():,}")
print()
print("Para llegar a este numero escribimos 3 agregaciones y 4 joins, a mano,")
print("y materializamos una tabla que solo sirve para esta pregunta.")
print("Con la ontologia, la siguiente pregunta cruzada no cuesta una tabla nueva.")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }
