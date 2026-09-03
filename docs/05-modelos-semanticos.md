# 5 · Tres modelos semánticos Direct Lake

⏱️ 20 minutos · Artefacto: `nb_04_modelos_semanticos`

---

## Por qué tres y no uno

Podríamos hacer un modelo con las nueve tablas. No lo hacemos, por dos razones.

**La primera es realista.** En cualquier empresa de verdad, estos tres dominios pertenecen a tres gerencias distintas, con tres equipos y tres ciclos de vida. Nadie tiene un modelo semántico único que abarque comercial, logística y mantenimiento. Un taller que empiece asumiendo que sí existe está resolviendo un problema que nadie tiene.

**La segunda es pedagógica.** Si hubiera un solo modelo, la ontología no tendría nada que aportar: el modelo ya cruzaría todo. El valor de Fabric IQ aparece justamente cuando el conocimiento está repartido.

| Modelo | Dominio | Tablas |
|---|---|---|
| `sm_polar_ventas` | Comercial | Tienda, Producto, Cliente, Venta |
| `sm_polar_operaciones` | Logística | Tienda, Ruta, Vehiculo, Despacho |
| `sm_polar_activos` | Cadena de frío | Tienda, Equipo, LecturaSensor |

`Tienda` está en los tres. Ese solapamiento **es el diseño**.

---

## Direct Lake no es opcional

Es un requisito duro de Fabric IQ, no una preferencia de rendimiento:

| Modo del modelo | Genera entidades | Genera relaciones | Genera **bindings a datos** |
|---|---|---|---|
| Import | Sí | Sí | **No** |
| **Direct Lake** | Sí | Sí | **Sí** |
| DirectQuery | Sí | Sí | **No** |

Un modelo Import produce una ontología con la estructura perfecta y **sin nada detrás**. Las entidades aparecen, el grafo se dibuja, y las consultas vuelven vacías. No hay mensaje de error.

Y hay una condición adicional que se olvida siempre: con Direct Lake, los bindings se generan **solo si el workspace del lakehouse tiene acceso público de entrada habilitado**. Si está deshabilitado, la ontología se crea con sus entidades y sin bindings. Verifícalo antes ([00-preparacion.md](00-preparacion.md#3--acceso-público-de-entrada-en-el-workspace)).

---

## Nombres de tabla en lenguaje de negocio

En el notebook, las tablas del modelo no se llaman `dim_tienda` ni `ft_venta`:

```python
"sm_polar_ventas": {
    "Tienda": "dbo.dim_tienda",
    "Producto": "dbo.dim_producto",
    "Cliente": "dbo.dim_cliente",
    "Venta": "dbo.ft_venta",
}
```

**El nombre de la tabla del modelo semántico se convierte en el nombre del entity type de la ontología.** Un entity type llamado `ft_venta` es un entity type que un agente va a interpretar peor, y que un usuario de negocio no va a reconocer. El prefijo `dim_`/`ft_` es vocabulario de ingeniería y se queda en Silver.

> **Nota sobre palabras reservadas.** En GQL, el lenguaje de consulta del grafo de Fabric, `PRODUCT` es palabra reservada: una entidad llamada `Product` da problemas. Nombrar en español evita esa colisión de entrada. Si nombras en inglés, revisa la lista de términos reservados de GQL antes.

---

## Los cuatro pasos del notebook

### 1 · Crear los modelos

```python
generate_direct_lake_semantic_model(
    dataset=nombre,
    tables=tablas,
    source=LH_SILVER,
    source_type="Lakehouse",
    workspace=WORKSPACE_ID,
    refresh=True,
    inherit_descriptions=True,   # ← el eslabón
    overwrite=True,
)
```

`inherit_descriptions=True` es lo que engancha con `nb_02`: toma los comentarios que dejamos en las columnas Delta y los convierte en descripciones del modelo semántico. De ahí bajarán a la ontología.

`overwrite=True` hace el notebook re-ejecutable, que en un taller en vivo vale oro.

### 2 · Relaciones

`generate_direct_lake_semantic_model` crea las tablas pero **no las relaciones**. Hay que agregarlas, y no es un detalle estético: **la ontología deriva sus relationship types de las relaciones del modelo semántico**. Sin relaciones aquí, la ontología sale con entidades sueltas y sin grafo.

```python
tom.add_relationship(
    from_table="Venta", from_column="id_tienda",
    to_table="Tienda", to_column="id_tienda",
    from_cardinality="Many", to_cardinality="One",
    cross_filtering_behavior="OneDirection",
    rely_on_referential_integrity=True,
)
```

`rely_on_referential_integrity=True` es correcto aquí porque en `nb_02` ya descartamos las filas huérfanas. La integridad está garantizada aguas arriba, así que le podemos decir al motor que confíe.

### 3 · Claves primarias — el paso que se salta

```python
col = tom.model.Tables["Venta"].Columns["id_venta"]
col.IsKey = True
tom.set_summarize_by(table_name="Venta", column_name="id_venta", value="None")
```

La ontología usa **la clave primaria declarada en el modelo** como *entity type key*. Si una tabla no la tiene:

- la entidad se genera igual,
- pero sus **relaciones no se pueden enlazar a datos**,
- y hay que definir cada una a mano en la interfaz de la ontología, una por una.

En un modelo de BI puro, marcar `id_venta` como clave sería innecesario. Para la ontología es imprescindible: **un evento sin identidad no puede ser una entidad.**

El `set_summarize_by(..., "None")` es higiene: evita que Power BI trate un ID como una medida sumable.

### 4 · Medidas

Se agregan cinco por modelo (`Venta total`, `Tasa de atraso`, `Tasa de excursion`...). Con una advertencia explícita:

> **Las medidas no viajan a la ontología.** Fabric IQ no consulta medidas ni columnas calculadas.

Se agregan igual, porque el modelo también tiene que servir para Power BI. Pero el contraste es parte del taller: **lo que sirve a un informe y lo que sirve a un agente no es lo mismo**. Una medida es lógica de cálculo; una entidad es lógica de significado. La ontología quiere lo segundo.

---

## Ejecución

1. Crea `nb_04_modelos_semanticos` con el contenido de [`fabric/nb_04_modelos_semanticos.Notebook/notebook-content.py`](../fabric/nb_04_modelos_semanticos.Notebook/notebook-content.py) — o importa [`notebooks/nb_04_modelos_semanticos.ipynb`](../notebooks/nb_04_modelos_semanticos.ipynb)
2. Ejecuta. La primera celda instala `semantic-link-labs` (~1 minuto) y **reinicia el kernel de Python** — es normal, la sesión de Spark sigue viva.
3. Total: 5–8 minutos, la mayoría en los tres refrescos.

Salida esperada:

```
sm_polar_ventas
  tablas       4  (Tienda, Producto, Cliente, Venta)
  relaciones   3
  medidas      5
  columnas con descripcion heredada  25
  claves       Tienda[id_tienda], Producto[id_producto], Cliente[id_cliente], Venta[id_venta]
```

### Antes de seguir, verifica

- [ ] Los tres modelos tienen 4, 4 y 3 tablas
- [ ] Relaciones > 0 en los tres
- [ ] **Una clave por tabla**, incluidas las de hechos
- [ ] Columnas con descripción heredada > 0

Si las descripciones vienen en 0, los comentarios de `nb_02` no se persistieron. Vuelve a ejecutar `nb_02` y luego este notebook (tiene `overwrite=True`, no hay que borrar nada).

---

**Siguiente:** [06 · Enriquecimiento con sempy](06-enriquecimiento-sempy.md)
