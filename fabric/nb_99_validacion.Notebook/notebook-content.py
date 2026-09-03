# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "synapse_pyspark"
# META   },
# META   "dependencies": {}
# META }

# MARKDOWN ********************

# # nb_99_validacion · Chequeo previo a la ontología
# Ejecuta este notebook **antes** de generar la ontología. Verifica las condiciones que,
# cuando fallan, producen una ontología que se crea sin errores y no devuelve datos.
# Ese es el modo de falla más caro de Fabric IQ en preview: **no hay mensaje de error**.
# Las entidades aparecen, el grafo se dibuja, y las consultas vuelven vacías o con nulos.
# Cinco minutos aquí ahorran media hora de diagnóstico a ciegas.
# Al final exporta el vocabulario de `nb_05` en el formato que pide la interfaz de la
# ontología, para no volver a escribirlo a mano.

# CELL ********************

# semantic-link-labs no viene preinstalado en el runtime de Fabric.
# Va PRIMERO, antes del %run: %pip reinicia el interprete de Python y se
# llevaria por delante las variables y funciones que define nb_00_setup.
%pip install semantic-link-labs --quiet

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

%run nb_00_setup

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

from pyspark.sql import types as T
import sempy_labs
from sempy_labs.tom import connect_semantic_model

TABLAS_CLAVE = {
    "dim_tienda": "id_tienda",
    "dim_producto": "id_producto",
    "dim_cliente": "id_cliente",
    "ft_venta": "id_venta",
    "dim_ruta": "id_ruta",
    "dim_vehiculo": "id_vehiculo",
    "ft_despacho": "id_despacho",
    "dim_equipo": "id_equipo",
    "ft_lectura_sensor": "id_lectura",
}

MODELOS = ["sm_polar_ventas", "sm_polar_operaciones", "sm_polar_activos"]

fallas = []


def chequear(condicion: bool, descripcion: str, detalle: str = ""):
    if condicion:
        print(f"  OK    · {descripcion}")
    else:
        print(f"  FALLA · {descripcion}" + (f" — {detalle}" if detalle else ""))
        fallas.append(descripcion)

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## 1 · Las tablas Silver existen y tienen datos

# CELL ********************

print("Tablas de lh_silver_polar\n")
conteos = {}
for tabla in TABLAS_CLAVE:
    try:
        n = leer(LH_SILVER, tabla).count()
        conteos[tabla] = n
        chequear(n > 0, f"{tabla} tiene datos", f"{n} filas")
    except Exception as e:
        conteos[tabla] = 0
        chequear(False, f"{tabla} existe", str(e)[:120])

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## 2 · Sin column mapping
# Si Delta activó *column mapping* en una tabla, el grafo de la ontología no la puede
# leer. Se activa sola cuando un nombre de columna trae espacio, `,`, `;`, `{}`, `()`,
# `=`, tab o salto de línea.

# CELL ********************

print("Column mapping en tablas Silver\n")
for tabla in conteos:
    if conteos[tabla] == 0:
        continue
    detalle = spark.sql(f"DESCRIBE DETAIL delta.`{ruta(LH_SILVER, tabla)}`").collect()[0]
    props = detalle["properties"] or {}
    modo = props.get("delta.columnMapping.mode", "none")
    chequear(modo in ("none", None), f"{tabla} sin column mapping", f"modo = {modo}")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## 3 · Tipos compatibles con Fabric Graph
# `decimal` no está soportado: una columna decimal devuelve `null` en toda consulta de
# la ontología, sin avisar.

# CELL ********************

print("Tipos de dato\n")
for tabla in conteos:
    if conteos[tabla] == 0:
        continue
    decimales = [c.name for c in leer(LH_SILVER, tabla).schema.fields
                 if isinstance(c.dataType, T.DecimalType)]
    chequear(not decimales, f"{tabla} sin columnas decimal", ", ".join(decimales))

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## 4 · Claves únicas y de tipo válido
# La *entity type key* debe ser `string` o `integer`, y única. En el taller son todas
# `string` a propósito: en la ontología, una propiedad con el mismo nombre debe tener
# el mismo tipo en **todas** las entidades donde aparece, y mezclar `id` string con
# `id` entero rompe la generación.

# CELL ********************

print("Claves\n")
for tabla, clave in TABLAS_CLAVE.items():
    if conteos.get(tabla, 0) == 0:
        continue
    df = leer(LH_SILVER, tabla)
    tipo = dict((f.name, f.dataType) for f in df.schema.fields).get(clave)
    chequear(isinstance(tipo, (T.StringType, T.IntegerType, T.LongType)),
             f"{tabla}.{clave} es de tipo valido",
             tipo.simpleString() if tipo else "no existe")
    n, d = df.count(), df.select(clave).distinct().count()
    chequear(n == d, f"{tabla}.{clave} es unica", f"{n} filas, {d} distintos")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## 5 · Los modelos semánticos están listos

# CELL ********************

print("Modelos semanticos\n")
for modelo in MODELOS:
    try:
        with connect_semantic_model(dataset=modelo, workspace=WORKSPACE_ID, readonly=True) as tom:
            tablas = list(tom.model.Tables)
            relaciones = list(tom.model.Relationships)
            sin_clave = [t.Name for t in tablas if not any(c.IsKey for c in t.Columns)]
            modos = {p.Mode.ToString() for t in tablas for p in t.Partitions}
            ocultas = [t.Name for t in tablas if t.IsHidden]

            print(f"\n{modelo}")
            chequear(len(tablas) > 0, "tiene tablas", f"{len(tablas)}")
            chequear(len(relaciones) > 0, "tiene relaciones", f"{len(relaciones)}")
            chequear(not sin_clave, "todas las tablas tienen clave", ", ".join(sin_clave))
            chequear("DirectLake" in " ".join(modos), "esta en Direct Lake", f"modos = {modos}")
            chequear(not ocultas, "ninguna tabla oculta", ", ".join(ocultas))
    except Exception as e:
        print(f"\n{modelo}")
        chequear(False, "el modelo existe y es accesible", str(e)[:150])

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## 6 · Veredicto

# CELL ********************

print("=" * 68)
if fallas:
    print(f"{len(fallas)} chequeo(s) fallaron. NO generes la ontologia todavia.\n")
    for f in fallas:
        print(f"  - {f}")
    print("\nRevisa docs/99-troubleshooting.md para cada caso.")
else:
    print("Todo en orden. Puedes generar la ontologia.")
    print("\nRecuerda ademas, fuera de este notebook:")
    print("  - Ontology item (preview) habilitado en la configuracion del tenant")
    print("  - Workspace con acceso publico de entrada habilitado")
    print("    (sin eso la ontologia se crea SIN bindings a datos)")
    print("  - El workspace NO puede ser 'Mi area de trabajo'")
print("=" * 68)

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## 7 · Vocabulario para la ontología
# Los sinónimos de `nb_05` viven en el modelo semántico y **no** se heredan a la
# ontología: la ontología tiene su propio campo de sinónimos, que se carga en su
# interfaz. Aquí lo exportamos ya agrupado por entidad, listo para copiar y pegar.
# En la ontología, **solo los entity types aceptan sinónimos**; propiedades y
# relaciones aceptan descripción y metadata clave-valor, pero no sinónimos.

# CELL ********************

import pandas as pd

df_syn = pd.concat(
    [sempy_labs.list_synonyms(dataset=m, workspace=WORKSPACE_ID) for m in MODELOS],
    ignore_index=True,
)

# Solo el nivel tabla: es lo unico que la ontologia acepta como sinonimo.
entidades = df_syn[df_syn["Object Type"] == "Table"]

print("Sinonimos por entity type — copiar al campo Synonyms de la ontologia\n")
for entidad, grupo in entidades.groupby("Object Name"):
    terminos = sorted(set(grupo["Synonym"]))
    print(f"{entidad}")
    print(f"  {', '.join(terminos)}\n")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# Metadata clave-valor por propiedad, en el formato de "Additional metadata"
# de la ontologia.
print("Additional metadata por propiedad\n")

# Tienda aparece en los tres modelos, asi que deduplicamos por (entidad, propiedad).
vistas = {}
for modelo in MODELOS:
    with connect_semantic_model(dataset=modelo, workspace=WORKSPACE_ID, readonly=True) as tom:
        for t in tom.model.Tables:
            for c in t.Columns:
                anotaciones = [(a.Name, a.Value) for a in c.Annotations]
                if anotaciones:
                    vistas[(t.Name, c.Name)] = anotaciones

for (tabla, columna), anotaciones in sorted(vistas.items()):
    pares = "  ·  ".join(f"{k}: {v}" for k, v in anotaciones)
    print(f"{tabla}.{columna}")
    print(f"  {pares}")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }
