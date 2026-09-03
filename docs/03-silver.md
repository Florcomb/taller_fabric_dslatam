# 3 · Transformación Silver

⏱️ 20 minutos · Artefacto: `nb_02_silver_transforma`

---

Este es el bloque más denso del taller y el que más determina si la ontología va a funcionar. Silver es donde el dato deja de ser *lo que llegó* y pasa a ser *lo que el negocio afirma*.

## Las nueve tablas

| Dominio | Tabla | Clave | Grano |
|---|---|---|---|
| Comercial | `dim_tienda` | `id_tienda` | Una tienda |
| Comercial | `dim_producto` | `id_producto` | Un SKU |
| Comercial | `dim_cliente` | `id_cliente` | Un cliente |
| Comercial | `ft_venta` | `id_venta` | Una línea de venta |
| Logística | `dim_ruta` | `id_ruta` | Una ruta |
| Logística | `dim_vehiculo` | `id_vehiculo` | Un vehículo |
| Logística | `ft_despacho` | `id_despacho` | Un despacho |
| Frío | `dim_equipo` | `id_equipo` | Un equipo de frío |
| Frío | `ft_lectura_sensor` | `id_lectura` | Una lectura de sensor |

`dim_tienda` es la **entidad puente**: la referencian `ft_venta`, `ft_despacho` y `dim_equipo`. Los tres dominios se tocan ahí y en ningún otro lado. Es lo que hará posible la ontología.

---

## Tres exigencias que no son negociables

En un proyecto normal estas serían buenas prácticas. Aquí son requisitos duros, porque Silver es la capa que va a alimentar la ontología.

### 1 · Ningún `decimal`

Fabric Graph no soporta el tipo `Decimal`. Si una columna de montos llega como `decimal(18,2)`, la ontología la devuelve como `null` en **todas** sus consultas, sin advertirlo.

Es contraintuitivo: `decimal` es precisamente el tipo correcto para dinero. Aquí no. Los montos van en `double`.

```python
def a_double(col):
    limpio = F.regexp_replace(F.trim(col.cast("string")), r"\.", "")   # separador de miles
    limpio = F.regexp_replace(limpio, ",", ".")                        # coma decimal
    return limpio.cast("double")
```

> `Double` (coma flotante) sí está soportado. `Decimal` (precisión fija) no. No es lo mismo, aunque en el día a día se traten como sinónimos.

### 2 · Nombres `snake_case`

El renombre de `"Monto Total"` a `monto_total` es la **primera** operación de la transformación de ventas:

```python
_ventas_bronze.withColumnRenamed("Monto Total", "monto_total_txt")
```

Va primero por una razón práctica: a partir de esa línea ninguna columna del pipeline tiene un carácter que dispare *column mapping*, y ya no hay que estar pendiente.

### 3 · Clave única en toda tabla, incluidos los hechos

`ft_venta` necesita `id_venta` aunque el modelo de BI nunca lo use. La ontología convierte cada tabla en un *entity type*, y un entity type **necesita identidad**: sin clave, la ontología genera la entidad pero no puede enlazar sus relaciones a datos, y hay que definirlas a mano una por una en la interfaz.

Además, todos los IDs del taller son `string`. Es deliberado: en la ontología, **una propiedad con el mismo nombre debe tener el mismo tipo en todas las entidades donde aparece**. Si `id` fuera texto en una entidad y entero en otra, la generación falla. Con todos los IDs en `string` el problema no existe.

---

## Las reglas de calidad, y quién las decide

Estas no son técnicas. Son decisiones de negocio, y por eso viven en Silver y no en cada informe:

| Regla | Decisión | Filas afectadas |
|---|---|---|
| Monto nulo → se descarta | Una venta sin monto es una incidencia del POS, no una venta | ~2% |
| Unidades ≤ 0 → se descarta | Una devolución mal codificada no es una venta | ~1% |
| Sin match en dimensiones → se descarta | Una venta a una tienda inexistente deja la relación colgando en la ontología | 0 en este dataset |
| Clientes duplicados → se deduplica | El CRM cargó dos veces | ~15 |
| `temperatura_c > -15` → `excursion_termica = true` | **Umbral del negocio** | ~6% de lecturas |

La última merece detenerse. `UMBRAL_EXCURSION_C = -15.0` es una definición de negocio: por sobre esa temperatura, el producto congelado queda en riesgo. Ponerla en Silver como una columna booleana significa que **existe una sola definición de "quiebre de cadena de frío"** en toda la organización. Si viviera en cada informe, habría tantas definiciones como analistas.

Esa columna `excursion_termica` es la que en el bloque 7 se convierte en la propiedad que un agente puede consultar en lenguaje natural.

Todos los descartes se registran y se imprimen al final. En un pipeline real irían a una tabla de auditoría; el principio es el mismo: **un descarte silencioso es un error, un descarte contado es una regla.**

---

## Los comentarios: el eslabón que casi nadie usa

Cada columna se escribe con un comentario:

```python
dim_tienda = comentar(dim_tienda, {
    "id_tienda": "Codigo unico de la tienda en la red Polar Sur. Formato T-NNN.",
    "latitud": "Latitud geografica en grados decimales (WGS84).",
    ...
})
```

No es documentación decorativa. Es el primer eslabón de una cadena que llega hasta el agente:

```
comentario Delta  (nb_02, aquí)
      ↓  generate_direct_lake_semantic_model(inherit_descriptions=True)
descripción del modelo semántico  (nb_04)
      ↓  generación de la ontología
descripción del entity type y de sus propiedades  (bloque 7)
      ↓
contexto que lee el agente al explorar el esquema  (bloque 8)
```

Un comentario escrito una vez, aquí, termina siendo lo que le permite a un agente entender qué significa `excursion_termica`. Es la inversión de documentación con mejor retorno de todo el taller — y la más fácil de saltarse.

Fíjate en el comentario de `excursion_termica`: no dice "indica si hubo excursión". Dice cuál es el umbral y qué implica. Eso es lo que un agente necesita para responder bien.

---

## Ejecución

1. Crea `nb_02_silver_transforma` con el contenido de [`fabric/nb_02_silver_transforma.Notebook/notebook-content.py`](../fabric/nb_02_silver_transforma.Notebook/notebook-content.py)
2. Ejecuta todo. ~3 minutos.

Salida esperada, en dos partes. Las validaciones:

```
  válida  · dim_tienda · clave 'id_tienda' única
  escrito · lh_silver_polar.dbo.dim_tienda · 12 filas
  ...
```

Y el resumen de calidad:

```
Descartes aplicados

  dim_cliente          15  duplicados exactos del CRM
  ft_venta            ~400  monto nulo
  ft_venta            ~196  unidades <= 0 (devoluciones mal codificadas)
  ft_venta               0  sin match en dimensiones

  6.0% de las lecturas estan en excursion termica (sobre -15.0 C)
```

Si `validar_para_ontologia` lanza un `ValueError`, **léelo**: dice exactamente qué columna y por qué. Ese error es el notebook haciendo su trabajo.

---

## Para conversar

**¿Por qué descartamos las devoluciones en vez de marcarlas?**

Es una decisión discutible y vale la pena discutirla. Descartarlas mantiene `ft_venta` con un solo significado —"esto se vendió"— a costa de perder información. Marcarlas con una columna `es_devolucion` conserva todo pero obliga a que cada consulta filtre. Para una ontología, la primera opción suele ser mejor: una entidad debe significar **una** cosa. Un `Venta` que a veces es una devolución es una entidad que un agente va a interpretar mal.

---

**Siguiente:** [04 · Agregados Gold](04-gold.md)
