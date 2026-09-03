# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "synapse_pyspark"
# META   },
# META   "dependencies": {}
# META }

# MARKDOWN ********************

# # nb_04_modelos_semanticos · Tres modelos Direct Lake sobre Silver
# Creamos tres modelos semánticos, uno por dominio, todos en **Direct Lake** sobre las
# tablas de `lh_silver_polar`:
# | Modelo | Dominio | Tablas |
# |---|---|---|
# | `sm_polar_ventas` | Comercial | Tienda, Producto, Cliente, Venta |
# | `sm_polar_operaciones` | Logística | Tienda, Ruta, Vehiculo, Despacho |
# | `sm_polar_activos` | Cadena de frío | Tienda, Equipo, LecturaSensor |
# `Tienda` aparece en los tres. Ese solapamiento **es el diseño**: es el punto donde la
# ontología va a coser los tres dominios.
# ### Por qué Direct Lake y no Import
# No es una preferencia de rendimiento. Es un requisito duro de Fabric IQ:
# | Modo | Genera entidades y relaciones | Genera **bindings a datos** |
# |---|---|---|
# | Import | Sí | **No** |
# | **Direct Lake** | Sí | **Sí** |
# | DirectQuery | Sí | **No** |
# Un modelo Import produce una ontología con la estructura correcta y **sin datos
# detrás**. Las consultas no devuelven nada y el error no dice por qué.
# ⏱️ ~20 minutos · Salida: 3 modelos semánticos en el workspace


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
from sempy_labs.directlake import generate_direct_lake_semantic_model
from sempy_labs.tom import connect_semantic_model

print(f"semantic-link-labs {sempy_labs.__version__}")

# Los nombres de las tablas del modelo semantico se convierten en los nombres de las
# entidades de la ontologia. Por eso los ponemos en singular y en lenguaje de negocio,
# no con el prefijo tecnico dim_/ft_.
#
# Nota: en GQL, el lenguaje de consulta del grafo de Fabric, PRODUCT es palabra
# reservada. Nombrar en espanol evita esa colision de entrada.

MODELOS = {
    "sm_polar_ventas": {
        "Tienda": "dbo.dim_tienda",
        "Producto": "dbo.dim_producto",
        "Cliente": "dbo.dim_cliente",
        "Venta": "dbo.ft_venta",
    },
    "sm_polar_operaciones": {
        "Tienda": "dbo.dim_tienda",
        "Ruta": "dbo.dim_ruta",
        "Vehiculo": "dbo.dim_vehiculo",
        "Despacho": "dbo.ft_despacho",
    },
    "sm_polar_activos": {
        "Tienda": "dbo.dim_tienda",
        "Equipo": "dbo.dim_equipo",
        "LecturaSensor": "dbo.ft_lectura_sensor",
    },
}

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## Creación de los modelos
# `inherit_descriptions=True` es la clave del encadenamiento: toma los comentarios que
# `nb_02` dejó en las columnas Delta y los convierte en descripciones del modelo
# semántico. De ahí bajan a la ontología. Un comentario escrito una vez en Silver
# termina siendo el contexto que lee un agente.

# CELL ********************

for nombre, tablas in MODELOS.items():
    print(f"\n=== {nombre} ===")
    generate_direct_lake_semantic_model(
        dataset=nombre,
        tables=tablas,
        source=LH_SILVER,
        source_type="Lakehouse",
        workspace=WORKSPACE_ID,
        refresh=True,
        inherit_descriptions=True,   # comentarios Delta -> descripciones del modelo
        overwrite=True,              # el notebook es re-ejecutable
    )

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## Relaciones
# La ontología deriva sus **relationship types** de las relaciones del modelo semántico.
# Sin relaciones aquí, la ontología sale con entidades sueltas y sin grafo.
# `rely_on_referential_integrity=True` es correcto porque en `nb_02` ya descartamos
# las filas huérfanas: la integridad está garantizada aguas arriba.

# CELL ********************

RELACIONES = {
    "sm_polar_ventas": [
        ("Venta", "id_tienda", "Tienda", "id_tienda"),
        ("Venta", "id_producto", "Producto", "id_producto"),
        ("Venta", "id_cliente", "Cliente", "id_cliente"),
    ],
    "sm_polar_operaciones": [
        ("Despacho", "id_tienda", "Tienda", "id_tienda"),
        ("Despacho", "id_ruta", "Ruta", "id_ruta"),
        ("Despacho", "id_vehiculo", "Vehiculo", "id_vehiculo"),
    ],
    "sm_polar_activos": [
        ("Equipo", "id_tienda", "Tienda", "id_tienda"),
        ("LecturaSensor", "id_equipo", "Equipo", "id_equipo"),
    ],
}

for nombre, relaciones in RELACIONES.items():
    print(f"\n=== {nombre} ===")
    with connect_semantic_model(dataset=nombre, workspace=WORKSPACE_ID, readonly=False) as tom:
        existentes = {
            (r.FromTable.Name, r.FromColumn.Name, r.ToTable.Name, r.ToColumn.Name)
            for r in tom.model.Relationships
        }
        for desde_t, desde_c, hacia_t, hacia_c in relaciones:
            if (desde_t, desde_c, hacia_t, hacia_c) in existentes:
                print(f"  ya existe · {desde_t}[{desde_c}] -> {hacia_t}[{hacia_c}]")
                continue
            tom.add_relationship(
                from_table=desde_t, from_column=desde_c,
                to_table=hacia_t, to_column=hacia_c,
                from_cardinality="Many", to_cardinality="One",
                cross_filtering_behavior="OneDirection",
                rely_on_referential_integrity=True,
            )
            print(f"  creada    · {desde_t}[{desde_c}] -> {hacia_t}[{hacia_c}]")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## Claves primarias
# Este paso se salta muy fácil y cuesta caro después.
# La ontología usa la **clave primaria declarada en el modelo** como *entity type key*.
# Si una tabla no la tiene, Fabric IQ genera la entidad pero **no puede enlazar sus
# relaciones a datos**, y hay que definirlas a mano una por una en la interfaz.
# Marcamos también las claves de los hechos (`id_venta`, `id_despacho`, `id_lectura`).
# En un modelo de BI puro no harían falta; para la ontología son imprescindibles,
# porque un evento sin identidad no puede ser una entidad.

# CELL ********************

CLAVES = {
    "sm_polar_ventas": {
        "Tienda": "id_tienda", "Producto": "id_producto",
        "Cliente": "id_cliente", "Venta": "id_venta",
    },
    "sm_polar_operaciones": {
        "Tienda": "id_tienda", "Ruta": "id_ruta",
        "Vehiculo": "id_vehiculo", "Despacho": "id_despacho",
    },
    "sm_polar_activos": {
        "Tienda": "id_tienda", "Equipo": "id_equipo",
        "LecturaSensor": "id_lectura",
    },
}

for nombre, claves in CLAVES.items():
    print(f"\n=== {nombre} ===")
    with connect_semantic_model(dataset=nombre, workspace=WORKSPACE_ID, readonly=False) as tom:
        for tabla, columna in claves.items():
            col = tom.model.Tables[tabla].Columns[columna]
            col.IsKey = True
            # Un ID no se suma. Sin esto Power BI lo trata como medida numerica
            # cuando es entero, y ademas ensucia la lectura del modelo.
            tom.set_summarize_by(table_name=tabla, column_name=columna, value="None")
            print(f"  clave · {tabla}[{columna}]")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## Medidas
# Las medidas viven en el modelo semántico y **no** viajan a la ontología: Fabric IQ
# no consulta medidas ni columnas calculadas. Las agregamos igual porque el modelo
# también tiene que servir para Power BI, y porque el contraste es parte del taller:
# lo que sirve a un informe y lo que sirve a un agente no es lo mismo.

# CELL ********************

MEDIDAS = {
    "sm_polar_ventas": [
        ("Venta", "Venta total", "SUM('Venta'[monto_total])", '"$"#,0',
         "Monto facturado con IVA, en pesos chilenos."),
        ("Venta", "Venta neta", "SUM('Venta'[monto_neto])", '"$"#,0',
         "Monto facturado sin IVA, en pesos chilenos."),
        ("Venta", "Unidades vendidas", "SUM('Venta'[unidades])", "#,0",
         "Unidades fisicas vendidas."),
        ("Venta", "Ticket promedio",
         "DIVIDE([Venta total], DISTINCTCOUNT('Venta'[id_venta]))", '"$"#,0',
         "Venta total dividida por el numero de transacciones."),
        ("Venta", "Clientes activos", "DISTINCTCOUNT('Venta'[id_cliente])", "#,0",
         "Clientes distintos con al menos una compra en el periodo."),
    ],
    "sm_polar_operaciones": [
        ("Despacho", "Despachos", "COUNTROWS('Despacho')", "#,0",
         "Cantidad de despachos ejecutados."),
        ("Despacho", "Despachos atrasados",
         "CALCULATE(COUNTROWS('Despacho'), 'Despacho'[llego_atrasado] = TRUE())", "#,0",
         "Despachos que llegaron fuera de la ventana comprometida."),
        ("Despacho", "Tasa de atraso",
         "DIVIDE([Despachos atrasados], [Despachos])", "0.0%",
         "Proporcion de despachos con atraso sobre el total."),
        ("Despacho", "Atraso promedio min", "AVERAGE('Despacho'[minutos_atraso])", "#,0.0",
         "Minutos de atraso promedio, contando los despachos a tiempo como cero."),
    ],
    "sm_polar_activos": [
        ("LecturaSensor", "Lecturas", "COUNTROWS('LecturaSensor')", "#,0",
         "Cantidad de lecturas de sensor registradas."),
        ("LecturaSensor", "Temperatura promedio",
         "AVERAGE('LecturaSensor'[temperatura_c])", "#,0.0",
         "Temperatura media en grados Celsius."),
        ("LecturaSensor", "Lecturas en excursion",
         "CALCULATE(COUNTROWS('LecturaSensor'), 'LecturaSensor'[excursion_termica] = TRUE())", "#,0",
         "Lecturas por sobre -15 grados Celsius, umbral de quiebre de cadena de frio."),
        ("LecturaSensor", "Tasa de excursion",
         "DIVIDE([Lecturas en excursion], [Lecturas])", "0.0%",
         "Proporcion del tiempo en que la cadena de frio estuvo comprometida."),
        ("LecturaSensor", "Equipos afectados",
         "CALCULATE(DISTINCTCOUNT('LecturaSensor'[id_equipo]), 'LecturaSensor'[excursion_termica] = TRUE())", "#,0",
         "Equipos distintos que registraron al menos una excursion termica."),
    ],
}

for nombre, medidas in MEDIDAS.items():
    print(f"\n=== {nombre} ===")
    with connect_semantic_model(dataset=nombre, workspace=WORKSPACE_ID, readonly=False) as tom:
        existentes = {m.Name for t in tom.model.Tables for m in t.Measures}
        for tabla, medida, dax, formato, descripcion in medidas:
            if medida in existentes:
                print(f"  ya existe · {medida}")
                continue
            tom.add_measure(
                table_name=tabla, measure_name=medida, expression=dax,
                format_string=formato, description=descripcion,
                display_folder="Indicadores",
            )
            print(f"  creada    · {medida}")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## Verificación

# CELL ********************

for nombre in MODELOS:
    with connect_semantic_model(dataset=nombre, workspace=WORKSPACE_ID, readonly=True) as tom:
        tablas = list(tom.model.Tables)
        n_medidas = sum(len(list(t.Measures)) for t in tablas)
        n_desc = sum(1 for t in tablas for c in t.Columns
                     if c.Description and not c.Name.startswith("RowNumber"))
        claves = [f"{t.Name}[{c.Name}]" for t in tablas for c in t.Columns if c.IsKey]
        print(f"\n{nombre}")
        print(f"  tablas       {len(tablas)}  ({', '.join(t.Name for t in tablas)})")
        print(f"  relaciones   {len(list(tom.model.Relationships))}")
        print(f"  medidas      {n_medidas}")
        print(f"  columnas con descripcion heredada  {n_desc}")
        print(f"  claves       {', '.join(claves)}")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ### Antes de seguir
# Comprueba en la salida de arriba que los tres modelos tienen:
# - las tablas esperadas (4, 4 y 3),
# - relaciones > 0,
# - **una clave por tabla**, incluidas las de hechos,
# - columnas con descripción heredada > 0.
# Si las descripciones vienen en 0, los comentarios de `nb_02` no se persistieron:
# vuelve a ejecutar `nb_02` y luego este notebook con `overwrite=True`.
# Siguiente paso: `nb_05_enriquecer_sempy`.
