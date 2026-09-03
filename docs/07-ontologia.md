# 7 · La ontología

⏱️ 25 minutos · Artefacto: item `onto_polar_sur` (preview)

---

## Antes de empezar: corre `nb_99_validacion`

No es opcional y no es burocracia. Verifica las condiciones que, cuando fallan, producen una ontología que **se crea sin errores y no devuelve datos**.

Ese es el modo de falla característico de Fabric IQ en preview: las entidades aparecen, el grafo se dibuja, y las consultas vuelven vacías. No hay mensaje que lo explique. Cinco minutos aquí ahorran media hora de diagnóstico a ciegas.

Crea `nb_99_validacion` con el contenido de [`fabric/nb_99_validacion.Notebook/notebook-content.py`](../fabric/nb_99_validacion.Notebook/notebook-content.py) y ejecútalo. Debe terminar con:

```
====================================================================
Todo en orden. Puedes generar la ontologia.
====================================================================
```

Si algo falla, [99-troubleshooting.md](99-troubleshooting.md) tiene el caso.

---

## El plan del bloque

Vamos a construir **una** ontología que abarque los tres dominios. El camino:

| Paso | Qué | Min |
|---|---|---|
| 7.1 | Generar la ontología desde `sm_polar_ventas` | 4 |
| 7.2 | Verificar entidades, propiedades y claves | 4 |
| 7.3 | Configurar las relaciones generadas | 5 |
| 7.4 | Agregar las entidades de los otros dos dominios | 7 |
| 7.5 | Crear las relaciones cruzadas | 3 |
| 7.6 | Refrescar el grafo y ver instancias | 2 |

> **Por qué no se generan tres ontologías.** Generar una ontología desde un modelo semántico crea **un item nuevo** cada vez; no fusiona con uno existente. Tres generaciones darían tres ontologías aisladas, que es exactamente el problema que veníamos a resolver. Así que generamos una desde el modelo más rico y la extendemos con las entidades de los otros dos dominios.

---

## 7.1 · Generar la ontología

1. Abre `sm_polar_ventas` en el workspace.
2. En la cinta superior: **Generate Ontology**.
   *(También está disponible desde la página de detalle del modelo, sin abrirlo.)*
3. **Workspace**: el tuyo. **Name**: `onto_polar_sur`.
4. **Create**.

> Los nombres de ontología aceptan letras, números y guion bajo. **Ni espacios ni guiones medios.**

La generación crea automáticamente:

- un **item de ontología** en el workspace,
- un **entity type por cada tabla** del modelo,
- las **propiedades estáticas** desde las columnas, con sus **data bindings**,
- los **relationship types** derivados de las relaciones del modelo.

Y crea además, como item hijo, un **modelo de grafo** (Graph in Microsoft Fabric). Ese es el motor que va a resolver las consultas.

### El detalle que se paga aquí

Las entidades se llaman **igual que las tablas del modelo semántico**. Como en `nb_04` las nombramos `Tienda`, `Producto`, `Cliente` y `Venta` en vez de `dim_tienda` y `ft_venta`, **no hay que renombrar nada**.

Si hubiéramos dejado los nombres técnicos, este sería el momento de renombrar cuatro entidades una por una, con `View Entity Type details → ... → Rename`. Es la clase de trabajo manual que se evita decidiendo bien 40 minutos antes.

---

## 7.2 · Verificar entidades, propiedades y claves

En el **Explorer** del canvas de configuración deben aparecer cuatro entidades: `Tienda`, `Producto`, `Cliente`, `Venta`.

Para cada una: selecciónala y usa **View Entity Type details** en la cinta. Se abre la página **Configure**.

| Entity type | Entity type key | Propiedades esperadas |
|---|---|---|
| `Tienda` | `id_tienda` | id_tienda, nombre_tienda, comuna, region, latitud, longitud, formato_tienda, superficie_m2 |
| `Producto` | `id_producto` | id_producto, nombre_producto, categoria, subcategoria, marca, precio_lista, requiere_frio |
| `Cliente` | `id_cliente` | id_cliente, nombre_cliente, segmento, comuna_cliente, region_cliente, fecha_alta |
| `Venta` | `id_venta` | id_venta, id_tienda, id_producto, id_cliente, fecha_venta, canal, unidades, monto_total, monto_neto |

**Comprueba tres cosas:**

1. **Cada entidad tiene su entity type key.** Debería venir de las claves que marcamos con `IsKey = True` en `nb_04`. Si alguna falta: **Define entity type key** → elige la columna → **Save**.
2. **Las propiedades tienen descripción.** Ahí está el comentario que escribiste en `nb_02`, tres capas más abajo. Vale la pena detenerse a mostrarlo: es la cadena completa `comentario Delta → modelo semántico → ontología`.
3. **Las propiedades están bound** a `lh_silver_polar`. Si el panel de propiedades muestra la fuente de datos, los bindings se generaron. Si aparecen sin binding, casi siempre es el acceso público de entrada del workspace → [99-troubleshooting.md](99-troubleshooting.md#la-ontología-se-creó-sin-bindings).

---

## 7.3 · Configurar las relaciones generadas

Los relationship types llegan **definidos pero no enlazados a datos**. Hay que completarlos uno por uno.

Selecciona `Venta` en el canvas: aparecen sus tres relaciones. Haz clic en cada una para abrir su configuración, que tiene tres paneles: **Origin entity type**, **Relationship type**, **Target entity type**.

En el panel central, completa:

| Relación generada | Renómbrala | Mapping table | Matched Venta | Matched (destino) |
|---|---|---|---|---|
| `Venta_has_Tienda` | `ocurre_en` | `ft_venta` | `id_venta` | `id_tienda` |
| `Venta_has_Producto` | `contiene` | `ft_venta` | `id_venta` | `id_producto` |
| `Venta_has_Cliente` | `comprada_por` | `ft_venta` | `id_venta` | `id_cliente` |

**Save** en cada una, confirma el mensaje de éxito, y **Cancel** para cerrar.

### Qué es la "mapping table"

Es la tabla del origen que contiene, **en la misma fila**, las claves de las dos entidades. Para `Venta → Tienda` es `ft_venta`, porque cada línea de venta trae su `id_venta` y su `id_tienda`.

Es exactamente el mismo concepto que un join, con una diferencia importante: se declara **una vez** y queda disponible para cualquier consulta futura, en vez de reescribirse en cada informe.

### Sobre los nombres

El nombre generado es `Origen_has_Destino`. Renombrarlos a verbos —`ocurre_en`, `contiene`, `comprada_por`— no es cosmético. La ontología es un vocabulario, y un agente lee esos nombres para entender el negocio. `Venta ocurre_en Tienda` es una frase; `Venta_has_Tienda` no dice nada.

---

## 7.4 · Agregar los otros dos dominios

Aquí es donde la ontología deja de ser un modelo semántico con otro nombre.

Vamos a agregar tres entidades más, que vienen de los dominios de **logística** y **cadena de frío**:

| Entity type | Fuente | Entity type key |
|---|---|---|
| `Despacho` | `lh_silver_polar.dbo.ft_despacho` | `id_despacho` |
| `Equipo` | `lh_silver_polar.dbo.dim_equipo` | `id_equipo` |
| `LecturaSensor` | `lh_silver_polar.dbo.ft_lectura_sensor` | `id_lectura` |

> Si además tienes tiempo, `Ruta` (`dim_ruta`) y `Vehiculo` (`dim_vehiculo`) siguen exactamente el mismo procedimiento. No son necesarias para las preguntas del bloque 8.

### Procedimiento, por cada entidad

1. En el canvas de configuración: **Add entity type** en la cinta superior.
2. Nombre: `Despacho`. **Add Entity Type**.
   > Los nombres deben tener 1–26 caracteres alfanuméricos, guiones o guiones bajos, y empezar y terminar en alfanumérico.
3. Selecciónala → **View Entity Type details** → página **Configure**.
4. **Add properties from data** (o **Manage property bindings → Add binding and properties**).
5. **Add data binding** → elige el tipo de fuente OneLake → busca `lh_silver_polar` en el catálogo → tabla `ft_despacho` → **Add**.
6. Las columnas de la tabla llenan solas la sección **Properties**. Revísalas: puedes renombrar, quitar o agregar.
7. **Define entity type key** → `id_despacho` → **Save**.
8. **Save** el binding. Confirma el mensaje, **Cancel** para cerrar.
9. Opcional pero recomendado: elige una **display name property** (`nombre_tienda` para Tienda, `nombre_producto` para Producto). Es el nombre amigable con el que las instancias aparecen aguas abajo.

Repite para `Equipo` y `LecturaSensor`.

### Las restricciones que ya resolvimos en Silver

Este paso funciona a la primera **porque `nb_02` preparó el terreno**. Vale la pena nombrarlo mientras se hace, porque es donde la mayoría de los proyectos se cae:

| Restricción de la ontología | Cómo la cumplimos |
|---|---|
| Solo tablas **managed** | Escribimos con `abfss://` al directorio propio del lakehouse |
| Sin **column mapping** | Renombramos `"Monto Total"` → `monto_total` en la primera línea |
| Sin lakehouse con **OneLake security** habilitada | No la activamos |
| Sin `decimal` | Todos los montos en `double` |
| Clave `string` o `integer`, única | Todos los IDs `string`, validados por `validar_para_ontologia()` |
| Una propiedad con el mismo nombre = el mismo tipo en todas las entidades | Todos los IDs `string`; nombres diferenciados (`comuna` vs `comuna_cliente`) |
| **Un solo binding estático** por entidad | Una entidad = una tabla Silver |

Esa última tiene una consecuencia de diseño que conviene decir en voz alta: **no se puede combinar datos estáticos de varias fuentes en una misma entidad.** Si necesitas una entidad que junte dos tablas, el join se hace en Silver, no en la ontología. Series de tiempo sí admiten múltiples fuentes; datos estáticos no.

---

## 7.5 · Las relaciones cruzadas

Este es el momento del taller. Aquí es donde tres dominios que en la empresa real no se hablan quedan conectados.

**Add relationship** en la cinta (o **... → Add relationship** junto a una entidad en el Explorer). Se abre **Add new relationship**: nombre, entidad origen, entidad destino → **Create**. Después se selecciona en el canvas para configurar el binding.

| Nombre | Origen | Destino | Mapping table | Matched origen | Matched destino |
|---|---|---|---|---|---|
| `entrega_en` | `Despacho` | `Tienda` | `ft_despacho` | `id_despacho` | `id_tienda` |
| `instalado_en` | `Equipo` | `Tienda` | `dim_equipo` | `id_equipo` | `id_tienda` |
| `mide` | `LecturaSensor` | `Equipo` | `ft_lectura_sensor` | `id_lectura` | `id_equipo` |

Con esas tres, el grafo queda cerrado:

```
Cliente ──comprada_por── Venta ──contiene── Producto
                           │
                        ocurre_en
                           ▼
   Despacho ──entrega_en──> Tienda <──instalado_en── Equipo
                                                       ▲
                                                     mide
                                                       │
                                                LecturaSensor
```

Desde una `LecturaSensor` se puede llegar a un `Cliente` en cuatro saltos, atravesando tres dominios y tres modelos semánticos. **Ese camino no existe en ningún modelo semántico del taller.** Es lo que compramos con este bloque.

---

## 7.6 · Refrescar el grafo y ver instancias

El grafo se refresca solo cuando cambias el **esquema** de la ontología. Pero **no** se entera de los cambios en los datos de origen: si `nb_01` agregara filas nuevas, el grafo seguiría mostrando las viejas hasta que se refresque a mano.

Como acabamos de cambiar el esquema varias veces, debería estar al día. Para forzarlo:

1. En el workspace, ubica el **modelo de grafo** asociado a la ontología (item hijo, mismo nombre base).
2. **... → Schedule** y dispara una actualización.

> El refresco es **completo** cada vez y tiene costo de capacidad. En producción conviene agrupar cambios y refrescar una vez, no después de cada edición.

### Comprobar que hay datos

En **View Entity Type details** hay tres pestañas: **Configure**, **Instances** y **Overview**.

- **Instances** — la tabla de instancias con sus valores. Si `Tienda` muestra 12 filas con nombres, los bindings funcionan.
- **Overview** — tiles con gráficos y el grafo de relaciones. **Expand** en un tile de grafo abre la vista completa.

En la vista de grafo, el **Query builder** permite consultar. La consulta por defecto muestra las entidades y todo lo que está a un salto. **Run query** y explora.

> **Si Instances viene vacío o con nulos**, no sigas al bloque 8. Ese es el síntoma del que hablábamos: ve a [99-troubleshooting.md](99-troubleshooting.md).

---

## Lo que acabamos de construir

Compara con `nb_03`:

| | Gold (`agg_riesgo_cadena_frio`) | Ontología |
|---|---|---|
| Para responder la pregunta | 3 agregaciones + 4 joins, ~50 líneas | 3 relationship types declarados una vez |
| Para la pregunta siguiente | Otra tabla, otro desarrollo, otro despliegue | Nada: se navega el grafo |
| Quién la puede hacer | Alguien que sepa PySpark | Cualquiera, en lenguaje natural |
| Vocabulario | El de las columnas | El del negocio |

La ontología no reemplaza a Gold. Reemplaza a **la siguiente tabla de Gold que ibas a escribir**.

---

**Siguiente:** [08 · Fabric IQ en acción](08-fabric-iq.md)
