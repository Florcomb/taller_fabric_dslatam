# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "synapse_pyspark"
# META   },
# META   "dependencies": {}
# META }

# MARKDOWN ********************

# # nb_00_setup · Configuración y utilidades del taller
#
# Este notebook **no escribe datos**. Define la configuración y las funciones auxiliares
# que usan todos los demás notebooks del taller.
#
# Se invoca desde los otros notebooks con `%run nb_00_setup`.
#
# **Por qué existe:** ninguno de los notebooks del taller tiene un lakehouse "pegado"
# en su metadata. Los IDs de lakehouse cambian en cada workspace, así que si los
# dejáramos escritos a mano el repositorio no sería reutilizable por otra persona.
# En vez de eso resolvemos los IDs **en tiempo de ejecución, por nombre**, y escribimos
# con rutas `abfss://` explícitas.

# CELL ********************

# Nombres de los tres lakehouses de la arquitectura medallón.
# Si cambias el prefijo, cámbialo también en la documentación del taller.
LH_BRONZE = "lh_bronze_polar"
LH_SILVER = "lh_silver_polar"
LH_GOLD   = "lh_gold_polar"

# Esquema por defecto de los lakehouses (schema-enabled lakehouse).
ESQUEMA = "dbo"

# Semilla para la generación de datos sintéticos. Fijarla hace el taller reproducible:
# todos los participantes obtienen exactamente los mismos números.
SEMILLA = 20260903

# Volumen de datos. Pensado para correr en pocos minutos en una capacidad F2/F4.
# Si tienes más capacidad y quieres un dataset más realista, sube N_VENTAS y N_LECTURAS.
N_TIENDAS   = 12
N_PRODUCTOS = 40
N_CLIENTES  = 300
N_VENTAS    = 20000
N_DESPACHOS = 1500
N_EQUIPOS   = 36
N_LECTURAS  = 50000

# Ventana temporal de los datos generados.
FECHA_INICIO = "2026-01-01"
DIAS         = 240

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## Resolución del workspace y de los lakehouses
#
# `notebookutils.runtime.context` expone el contexto de ejecución del notebook.
# De ahí sacamos el ID del workspace actual, sin escribirlo a mano.

# CELL ********************

import notebookutils

WORKSPACE_ID = notebookutils.runtime.context["currentWorkspaceId"]
print(f"Workspace ID: {WORKSPACE_ID}")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

def crear_lakehouse_si_falta(nombre: str) -> str:
    """Devuelve el ID del lakehouse `nombre`. Lo crea si todavía no existe.

    Hace el notebook idempotente: se puede correr las veces que haga falta.
    También permite que quien NO usó la vía rápida de git tenga los tres
    lakehouses creados con un solo Run.
    """
    try:
        lh = notebookutils.lakehouse.get(nombre, WORKSPACE_ID)
        print(f"  ya existe  · {nombre} · {lh['id']}")
        return lh["id"]
    except Exception:
        lh = notebookutils.lakehouse.create(
            name=nombre,
            description=f"Taller Fabric IQ · capa {nombre.split('_')[1]}",
            workspaceId=WORKSPACE_ID,
        )
        print(f"  CREADO     · {nombre} · {lh['id']}")
        return lh["id"]


LAKEHOUSES = {}
for _nombre in (LH_BRONZE, LH_SILVER, LH_GOLD):
    LAKEHOUSES[_nombre] = crear_lakehouse_si_falta(_nombre)

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## Helpers de lectura y escritura
#
# Escribimos con rutas `abfss://` apuntando a la carpeta `Tables/` **del propio
# lakehouse**. Eso deja las tablas como **managed tables**, que es un requisito
# de la ontología de Fabric IQ: las tablas externas (las que viven fuera del
# directorio OneLake del lakehouse) **no** se pueden enlazar a una entidad.

# CELL ********************

def ruta(lakehouse: str, tabla: str, esquema: str = ESQUEMA) -> str:
    """Ruta abfss de una tabla managed dentro de un lakehouse del workspace actual."""
    lh_id = LAKEHOUSES[lakehouse]
    return (
        f"abfss://{WORKSPACE_ID}@onelake.dfs.fabric.microsoft.com/"
        f"{lh_id}/Tables/{esquema}/{tabla}"
    )


def escribir(df, lakehouse: str, tabla: str, modo: str = "overwrite"):
    """Escribe un DataFrame como tabla Delta managed y reporta el conteo."""
    (
        df.write.format("delta")
        .mode(modo)
        .option("overwriteSchema", "true")
        .save(ruta(lakehouse, tabla))
    )
    n = df.count()
    print(f"  escrito · {lakehouse}.{ESQUEMA}.{tabla} · {n:,} filas")
    return n


def leer(lakehouse: str, tabla: str):
    """Lee una tabla Delta de cualquiera de los lakehouses del taller."""
    return spark.read.format("delta").load(ruta(lakehouse, tabla))

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## Reglas de modelado que impone Fabric IQ
#
# Esta función no es decorativa: valida las tres restricciones que más rompen
# ontologías en producción. Los notebooks Silver y Gold la llaman antes de escribir.
#
# | Restricción | Por qué |
# |---|---|
# | Sin `decimal` | Fabric Graph no soporta el tipo `Decimal`. Una columna decimal se lee como `null` en **todas** las consultas de la ontología. Los montos van como `double`. |
# | Nombres sin espacios ni caracteres especiales | Delta activa *column mapping* automáticamente cuando hay `espacio`, `,`, `;`, `{}`, `()`, `=`, tab o salto de línea en un nombre de columna. El grafo de la ontología **no soporta** tablas con column mapping. |
# | Claves `string` o `integer` | Solo esos dos tipos sirven como *entity type key*. Y el nombre de una propiedad debe tener el mismo tipo en todas las entidades donde aparece. En el taller **todos los IDs son `string`**, justamente para no caer en esa trampa. |

# CELL ********************

import re
from pyspark.sql import types as T

CARACTERES_PROHIBIDOS = re.compile(r"[ ,;{}()=\n\t]")


def validar_para_ontologia(df, nombre_tabla: str, clave: str | None = None):
    """Verifica que un DataFrame cumpla las restricciones de binding de la ontología.

    Lanza ValueError con el detalle si algo no calza. Es preferible fallar aquí,
    en el notebook, que descubrirlo cuando la ontología devuelve nulls sin explicar.
    """
    problemas = []

    for campo in df.schema.fields:
        if CARACTERES_PROHIBIDOS.search(campo.name):
            problemas.append(
                f"columna '{campo.name}': carácter prohibido "
                f"(activaría column mapping en Delta)"
            )
        if isinstance(campo.dataType, T.DecimalType):
            problemas.append(
                f"columna '{campo.name}': tipo decimal no soportado por Fabric Graph "
                f"— castear a double"
            )

    if clave is not None:
        campos = {f.name: f.dataType for f in df.schema.fields}
        if clave not in campos:
            problemas.append(f"la clave '{clave}' no existe en la tabla")
        elif not isinstance(campos[clave], (T.StringType, T.IntegerType, T.LongType)):
            problemas.append(
                f"la clave '{clave}' es {campos[clave].simpleString()}; "
                f"una entity type key debe ser string o integer"
            )
        else:
            total = df.count()
            distintos = df.select(clave).distinct().count()
            if total != distintos:
                problemas.append(
                    f"la clave '{clave}' no es única: {total:,} filas, "
                    f"{distintos:,} valores distintos"
                )

    if problemas:
        detalle = "\n    - ".join(problemas)
        raise ValueError(f"[{nombre_tabla}] no apta para ontología:\n    - {detalle}")

    print(f"  válida  · {nombre_tabla}" + (f" · clave '{clave}' única" if clave else ""))

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

print("\nnb_00_setup listo.")
print(f"  Bronze : {LH_BRONZE}")
print(f"  Silver : {LH_SILVER}")
print(f"  Gold   : {LH_GOLD}")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }
