# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "synapse_pyspark"
# META   },
# META   "dependencies": {}
# META }

# MARKDOWN ********************

# # nb_05_enriquecer_sempy · Sinónimos y metadata de negocio
#
# Un modelo semántico correcto no basta para que un agente responda bien. El agente
# falla porque el usuario **no usa las palabras del modelo**: pregunta por "locales",
# el modelo tiene `Tienda`; pregunta por "SKU", el modelo tiene `Producto`; pregunta
# por "quiebre de frío", el modelo tiene `excursion_termica`.
#
# Eso es lo que resolvemos aquí, con `sempy` y el TOM, sobre los tres modelos a la vez.
#
# ### Las tres capas que agregamos
#
# | Capa | Método | Para qué sirve |
# |---|---|---|
# | **Descripciones** | `Description` en TOM | Qué significa el objeto. Es lo que lee el agente cuando explora el esquema. |
# | **Sinónimos** | `set_synonym` | Cómo lo llama la gente. Vive en el *esquema lingüístico* del modelo, por cultura. |
# | **Metadata de negocio** | `set_annotation` / `set_extended_property` | Unidad, dueño, sensibilidad, umbral. Contexto que no cabe en una descripción. |
#
# ### Qué viaja a la ontología y qué no
#
# Conviene decirlo antes de que alguien lo pregunte a mitad del taller:
#
# - Las **descripciones** son el puente real: vienen del comentario Delta de `nb_02`,
#   pasan por el modelo semántico y llegan a la ontología.
# - Los **sinónimos** que ponemos aquí son del modelo semántico (Copilot y Q&A de
#   Power BI). La ontología tiene **su propio campo de sinónimos**, que se carga en
#   su interfaz. No se heredan automáticamente. Por eso en `nb_99` exportamos este
#   vocabulario a una tabla: para copiarlo a la ontología sin volver a inventarlo.
#
# ⏱️ ~20 minutos

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

import sempy_labs
from sempy_labs.tom import connect_semantic_model

MODELOS = ["sm_polar_ventas", "sm_polar_operaciones", "sm_polar_activos"]

# El esquema linguistico vive por cultura. set_synonym FALLA si la cultura no existe
# todavia en el modelo, asi que la creamos primero con add_translation.
CULTURA = "es-ES"

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## 1 · Descripciones de tabla
#
# Las columnas ya heredaron sus descripciones desde los comentarios Delta de `nb_02`.
# Falta el nivel de tabla, que es el que más pesa cuando un agente decide **qué entidad
# mirar** para responder una pregunta.

# CELL ********************

DESCRIPCIONES_TABLA = {
    "Tienda": (
        "Local de venta de la cadena Polar Sur. Es la entidad que conecta los tres "
        "dominios del negocio: en una tienda se vende, se recibe despacho y se opera "
        "equipamiento de frio."
    ),
    "Producto": (
        "Articulo del surtido de Polar Sur. Los productos marcados con requiere_frio "
        "dependen de que la cadena de frio no se interrumpa en ningun punto."
    ),
    "Cliente": (
        "Persona o empresa que compra en Polar Sur, segmentada en Retail, Mayorista, "
        "Institucional y Horeca."
    ),
    "Venta": (
        "Linea de venta individual. Grano: una fila por producto vendido en una "
        "transaccion. Es el hecho central del dominio comercial."
    ),
    "Ruta": "Trayecto de distribucion que agrupa las tiendas atendidas por un mismo recorrido.",
    "Vehiculo": (
        "Unidad de la flota de distribucion. Los vehiculos sin refrigeracion no pueden "
        "trasladar producto congelado sin riesgo."
    ),
    "Despacho": (
        "Entrega ejecutada desde el centro de distribucion a una tienda. Grano: una "
        "fila por despacho. Un despacho atrasado es el primer indicador de riesgo de "
        "cadena de frio."
    ),
    "Equipo": (
        "Equipo de frio instalado en una tienda: freezer o camara. Mantener la "
        "temperatura de consigna de -18 grados Celsius es su funcion critica."
    ),
    "LecturaSensor": (
        "Medicion de temperatura y humedad de un equipo de frio en un instante. "
        "Grano: una fila por lectura. Es la evidencia de si la cadena de frio se sostuvo."
    ),
}

for modelo in MODELOS:
    with connect_semantic_model(dataset=modelo, workspace=WORKSPACE_ID, readonly=False) as tom:
        for tabla in tom.model.Tables:
            if tabla.Name in DESCRIPCIONES_TABLA:
                tabla.Description = DESCRIPCIONES_TABLA[tabla.Name]
    print(f"  descripciones de tabla · {modelo}")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## 2 · Sinónimos
#
# El vocabulario está definido **una sola vez**, abajo, y se aplica a los tres modelos.
# Que `Tienda` tenga los mismos sinónimos en los tres es exactamente el punto: un
# vocabulario común es lo que después permite que la ontología los trate como la
# misma cosa.
#
# El `peso` (0 a 1) desempata cuando dos objetos comparten un término.

# CELL ********************

# (tabla, columna | None, [sinonimos], peso)
# columna = None significa que el sinonimo aplica a la tabla completa.
VOCABULARIO = [
    ("Tienda", None, ["local", "sucursal", "punto de venta", "pdv", "heladeria", "tiendas"], 0.9),
    ("Tienda", "nombre_tienda", ["nombre del local", "sucursal"], None),
    ("Tienda", "comuna", ["municipio", "distrito"], None),
    ("Tienda", "region", ["zona geografica", "region administrativa"], None),
    ("Tienda", "formato_tienda", ["tipo de local", "formato comercial"], None),

    ("Producto", None, ["articulo", "sku", "item", "helado", "productos", "surtido"], 0.9),
    ("Producto", "nombre_producto", ["descripcion del producto", "nombre del articulo"], None),
    ("Producto", "categoria", ["familia", "linea de producto", "rubro"], None),
    ("Producto", "precio_lista", ["precio", "precio unitario", "valor de lista"], None),
    ("Producto", "requiere_frio", ["congelado", "necesita frio", "cadena de frio"], 0.8),

    ("Cliente", None, ["comprador", "cuenta", "clientes"], 0.9),
    ("Cliente", "segmento", ["tipo de cliente", "segmentacion comercial"], None),

    ("Venta", None, ["transaccion", "boleta", "factura", "ticket", "ventas"], 0.9),
    ("Venta", "monto_total", ["facturacion", "ingreso", "venta con iva", "monto bruto"], None),
    ("Venta", "monto_neto", ["venta sin iva", "ingreso neto"], None),
    ("Venta", "unidades", ["cantidad", "volumen vendido", "piezas"], None),
    ("Venta", "canal", ["via de venta", "medio de compra"], None),

    ("Ruta", None, ["recorrido", "trayecto", "rutas de reparto"], 0.9),
    ("Ruta", "zona", ["area de cobertura", "sector"], None),

    ("Vehiculo", None, ["camion", "movil", "unidad de flota", "vehiculos", "flota"], 0.9),
    ("Vehiculo", "tiene_refrigeracion", ["refrigerado", "con frio", "termico"], None),

    ("Despacho", None, ["entrega", "reparto", "envio", "despachos"], 0.9),
    ("Despacho", "minutos_atraso", ["demora", "retraso", "atraso"], None),
    ("Despacho", "llego_atrasado", ["entrega tardia", "fuera de ventana", "atrasado"], 0.8),
    ("Despacho", "estado_despacho", ["cumplimiento de entrega", "estado de la entrega"], None),

    ("Equipo", None, ["freezer", "congelador", "camara de frio", "equipos", "activo"], 0.9),
    ("Equipo", "temperatura_objetivo_c", ["consigna", "setpoint", "temperatura objetivo"], None),

    ("LecturaSensor", None, ["medicion", "telemetria", "lecturas", "sensor"], 0.9),
    ("LecturaSensor", "temperatura_c", ["temperatura", "grados", "temperatura medida"], None),
    ("LecturaSensor", "excursion_termica", [
        "quiebre de cadena de frio", "excursion", "sobre temperatura",
        "fuera de rango", "riesgo de frio",
    ], 1.0),
    ("LecturaSensor", "alarma", ["alerta", "aviso del equipo"], None),
]

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

from decimal import Decimal

total = 0
for modelo in MODELOS:
    aplicados = 0
    with connect_semantic_model(dataset=modelo, workspace=WORKSPACE_ID, readonly=False) as tom:
        # Sin esto set_synonym lanza ValueError: la cultura no existe en el modelo.
        tom.add_translation(language=CULTURA)

        nombres_tabla = {t.Name for t in tom.model.Tables}
        for tabla, columna, sinonimos, peso in VOCABULARIO:
            if tabla not in nombres_tabla:
                continue  # esta tabla no pertenece a este modelo
            objeto = (tom.model.Tables[tabla] if columna is None
                      else tom.model.Tables[tabla].Columns[columna])
            for s in sinonimos:
                tom.set_synonym(
                    culture=CULTURA,
                    object=objeto,
                    synonym_name=s,
                    weight=Decimal(str(peso)) if peso is not None else None,
                )
                aplicados += 1
    total += aplicados
    print(f"  {modelo}: {aplicados} sinonimos")

print(f"\nTotal: {total} sinonimos en {len(MODELOS)} modelos")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## 3 · Metadata de negocio
#
# Lo que una descripción no alcanza a decir: en qué unidad está el número, quién es
# el dueño del dato, cuál es el umbral que lo vuelve un problema, si es sensible.
#
# Usamos las dos vías que ofrece el TOM, porque no son lo mismo:
#
# - **`set_annotation`** — clave/valor libre. Es el mecanismo estándar para metadata
#   propia y sobrevive a los despliegues.
# - **`set_extended_property`** — clave/valor tipado (`String` o `Json`), pensado para
#   que lo consuman herramientas externas.
#
# Estos pares clave-valor son además el borrador de la **additional metadata** que
# cargaremos en la ontología: la estructura es idéntica.

# CELL ********************

# (tabla, columna, {clave: valor})
METADATA = [
    ("Venta", "monto_total", {
        "unidad": "CLP", "incluye_iva": "true", "dueno_dato": "Gerencia Comercial",
    }),
    ("Venta", "monto_neto", {
        "unidad": "CLP", "incluye_iva": "false", "dueno_dato": "Gerencia Comercial",
    }),
    ("Venta", "unidades", {"unidad": "unidades", "dueno_dato": "Gerencia Comercial"}),
    ("Cliente", "nombre_cliente", {
        "sensibilidad": "Confidencial", "contiene_pii": "true",
        "dueno_dato": "Gerencia Comercial",
    }),
    ("Producto", "precio_lista", {"unidad": "CLP", "dueno_dato": "Categoria"}),
    ("Despacho", "minutos_atraso", {
        "unidad": "minutos", "umbral_critico": "30",
        "dueno_dato": "Gerencia de Operaciones",
    }),
    ("Despacho", "minutos_viaje", {"unidad": "minutos", "dueno_dato": "Gerencia de Operaciones"}),
    ("Ruta", "distancia_km", {"unidad": "kilometros", "dueno_dato": "Gerencia de Operaciones"}),
    ("Equipo", "temperatura_objetivo_c", {
        "unidad": "grados Celsius", "estandar_cadena": "-18",
        "dueno_dato": "Gerencia de Operaciones",
    }),
    ("LecturaSensor", "temperatura_c", {
        "unidad": "grados Celsius", "umbral_excursion": "-15",
        "frecuencia_muestreo": "30 minutos",
        "dueno_dato": "Mantenimiento",
    }),
    ("LecturaSensor", "humedad_pct", {"unidad": "porcentaje", "dueno_dato": "Mantenimiento"}),
    ("Tienda", "superficie_m2", {"unidad": "metros cuadrados", "dueno_dato": "Inmobiliaria"}),
]

for modelo in MODELOS:
    aplicados = 0
    with connect_semantic_model(dataset=modelo, workspace=WORKSPACE_ID, readonly=False) as tom:
        nombres_tabla = {t.Name for t in tom.model.Tables}
        for tabla, columna, pares in METADATA:
            if tabla not in nombres_tabla:
                continue
            col = tom.model.Tables[tabla].Columns[columna]
            for k, v in pares.items():
                tom.set_annotation(object=col, name=k, value=v)
                tom.set_extended_property(
                    object=col, extended_property_type="String", name=k, value=v
                )
                aplicados += 1
    print(f"  {modelo}: {aplicados} pares clave-valor")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# Metadata a nivel de modelo: quien es el dueno del dominio y para que sirve.
DOMINIOS = {
    "sm_polar_ventas": ("Comercial", "Gerencia Comercial"),
    "sm_polar_operaciones": ("Logistica y distribucion", "Gerencia de Operaciones"),
    "sm_polar_activos": ("Cadena de frio y activos", "Mantenimiento"),
}

for modelo, (dominio, dueno) in DOMINIOS.items():
    with connect_semantic_model(dataset=modelo, workspace=WORKSPACE_ID, readonly=False) as tom:
        tom.set_annotation(object=tom.model, name="dominio_negocio", value=dominio)
        tom.set_annotation(object=tom.model, name="dueno_dominio", value=dueno)
        tom.set_annotation(object=tom.model, name="taller", value="Fabric IQ · Polar Sur")
    print(f"  {modelo} · dominio '{dominio}' · dueno '{dueno}'")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## 4 · Verificación
#
# `list_synonyms` lee el esquema lingüístico y devuelve lo que quedó realmente guardado.
# Si aquí no aparece nada, el `with` no llegó a hacer commit: revisa que
# `readonly=False` esté puesto en todas las conexiones de arriba.

# CELL ********************

df_sinonimos = sempy_labs.list_synonyms(dataset="sm_polar_ventas", workspace=WORKSPACE_ID)
print(f"sm_polar_ventas · {len(df_sinonimos)} sinonimos registrados\n")
display(df_sinonimos)

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

for modelo in MODELOS:
    with connect_semantic_model(dataset=modelo, workspace=WORKSPACE_ID, readonly=True) as tom:
        tablas = list(tom.model.Tables)
        con_desc_tabla = sum(1 for t in tablas if t.Description)
        con_desc_col = sum(1 for t in tablas for c in t.Columns if c.Description)
        con_anot = sum(1 for t in tablas for c in t.Columns if len(list(c.Annotations)) > 0)
        culturas = [c.Name for c in tom.model.Cultures]
        print(f"\n{modelo}")
        print(f"  tablas con descripcion    {con_desc_tabla}/{len(tablas)}")
        print(f"  columnas con descripcion  {con_desc_col}")
        print(f"  columnas con metadata     {con_anot}")
        print(f"  culturas                  {culturas}")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ### Pruébalo antes de seguir
#
# Abre `sm_polar_ventas` en el workspace y usa Copilot o una visualización de P&R.
# Pregunta con las palabras del negocio, no con las del modelo:
#
# - *¿cuál es la facturación por sucursal?* — "facturación" y "sucursal" no son nombres
#   de ninguna columna; ahora el modelo igual entiende.
# - *¿qué locales vendieron más congelados?*
#
# Ese salto es lo que acabamos de comprar con 30 líneas de `sempy`. Es también el
# argumento para el paso siguiente: si un vocabulario mejora tanto **un** modelo,
# la ontología es lo que permite tener **un solo vocabulario para los tres**.
#
# Siguiente paso: `docs/07-ontologia.md`.
