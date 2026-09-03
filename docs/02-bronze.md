# 2 · Ingesta Bronze

⏱️ 15 minutos · Artefacto: `nb_01_bronze_ingesta`

---

## Sin dataflows, a propósito

Este taller ingesta **solo con notebooks**. No es dogma: es que en un taller de ontología los notebooks tienen tres ventajas que importan.

- **Se versionan de verdad.** Un notebook es un `.py` que se lee y se revisa en GitHub. Un dataflow es un `mashup.pq` que nadie diffea.
- **Son deterministas.** El mismo código produce el mismo dato en cualquier tenant, sin conexiones ni gateways que configurar.
- **Dejan ver el tipo.** El paso crítico de este taller es el control de tipos y nombres de columna. En un dataflow ese control queda escondido en la interfaz; en PySpark está en la línea que estás leyendo.

Para cargas recurrentes desde sistemas reales, un pipeline con actividad Copy sigue siendo la herramienta correcta. Aquí no aplica: los datos se generan.

> **Importante para cuando lleves esto a un caso real:** Fabric Spark **no puede leer URLs HTTP arbitrarias**. Un `spark.read.csv("https://...")` falla. El dato hay que aterrizarlo primero en `Files/` del lakehouse — con un pipeline Copy, con la API de OneLake, o con un shortcut — y recién ahí leerlo.

---

## Qué hace el notebook

Genera nueve tablas en `lh_bronze_polar.dbo`:

| Dominio | Tablas |
|---|---|
| Comercial | `br_tiendas`, `br_productos`, `br_clientes`, `br_ventas` |
| Logística | `br_rutas`, `br_vehiculos`, `br_despachos` |
| Cadena de frío | `br_equipos`, `br_lecturas_sensor` |

Y a cada una le agrega las tres columnas que definen la capa:

```python
ts_ingesta      # cuándo entró
archivo_origen  # de dónde salió
id_lote         # con qué carga
```

Esas tres columnas son lo único que Bronze aporta al dato. **No se limpia nada más.** Bronze es el registro de auditoría: si mañana se descubre que la regla de limpieza estaba mal, se reprocesa desde aquí sin volver a pedirle nada al sistema de origen.

---

## Generación determinista

El notebook **no usa `rand()`**. En Spark, `rand()` depende del particionado, así que dos participantes con distinta configuración de cluster obtendrían datos distintos y ningún número del taller coincidiría.

En su lugar todo se deriva de `hash(columna, semilla)`:

```python
def azar(*cols, sal=0):
    return F.pmod(F.hash(*cols, F.lit(SEMILLA + sal)), F.lit(1_000_000)) / 1_000_000.0
```

Mismo input, mismo output, en cualquier cluster. Es un detalle chico con una consecuencia grande: el facilitador puede decir "te tiene que dar 19.412 filas" y que sea cierto para todos.

---

## Los defectos plantados

Cada uno existe para justificar una línea concreta de `nb_02`. Merece la pena mirarlos antes de correr el notebook siguiente.

| Defecto | Dónde | Por qué es realista |
|---|---|---|
| IDs con espacios y mayúsculas | `br_tiendas.ID_TIENDA` = `"  T-001"` | Exportaciones de ERP con campos de ancho fijo |
| Decimales con coma | `latitud`, `precio_lista`, `temperatura`, `distancia_km` | Configuración regional española/chilena en el origen |
| Fechas `dd-MM-yyyy` como texto | `br_ventas.fecha`, `br_clientes.fecha_alta` | CSV sin esquema declarado |
| Categorías con mayúsculas mixtas | `br_productos.categoria` = `HELADOS` / `Helados` | Carga manual sin validación |
| Booleanos como `SI`/`Si`/`si`/`NO` | `requiere_frio`, `refrigerado` | Campos de texto libre en el maestro |
| Clientes duplicados (5%) | `br_clientes` | Doble carga del CRM |
| Montos nulos (2%) | `br_ventas` | Incidencias del punto de venta |
| Unidades negativas (1%) | `br_ventas` | Devoluciones codificadas como venta |
| **Nombre de columna con espacio** | `br_ventas."Monto Total"` | El clásico: alguien nombró la columna en Excel |

### El último es el importante

`"Monto Total"` con espacio no es un defecto cosmético. Cuando Delta escribe una tabla con un espacio en el nombre de una columna, **activa *column mapping* automáticamente**. Y el grafo de la ontología **no soporta tablas con column mapping**.

Si esa columna llegara así hasta Silver, la cadena sería:

1. La tabla Silver se escribe sin problema.
2. El modelo semántico Direct Lake se crea sin problema.
3. La ontología se genera sin problema, con su entidad `Venta` y sus propiedades.
4. Y toda consulta sobre `Venta` devuelve vacío. **Sin ningún mensaje de error.**

Los caracteres que disparan column mapping son: espacio, `,`, `;`, `{`, `}`, `(`, `)`, `=`, tabulación y salto de línea.

La última celda del notebook lo deja a la vista:

```
Columnas de br_ventas:
  id_venta
  ...
  Monto Total  <-- con espacio
```

En `nb_02` esa columna se renombra en la **primera** operación de la transformación, antes de cualquier otra cosa.

---

## Ejecución

1. Crea el notebook `nb_01_bronze_ingesta` y pega el contenido de [`fabric/nb_01_bronze_ingesta.Notebook/notebook-content.py`](../fabric/nb_01_bronze_ingesta.Notebook/notebook-content.py) — o importa [`notebooks/nb_01_bronze_ingesta.ipynb`](../notebooks/nb_01_bronze_ingesta.ipynb)
2. Ejecuta todo. Toma 2–4 minutos, la mayoría en el arranque de la sesión de Spark.

Salida esperada:

```
Bronze · lote lote_taller_001

  br_tiendas                   12 filas
  br_productos                 40 filas
  br_clientes                 315 filas
  br_ventas                20,000 filas
  br_rutas                      8 filas
  br_vehiculos                 10 filas
  br_despachos              1,500 filas
  br_equipos                   36 filas
  br_lecturas_sensor       50,000 filas
```

`br_clientes` trae 315 y no 300: son los ~15 duplicados plantados.

---

## Para conversar mientras corre

Buena pregunta para el grupo: **¿por qué no limpiamos aquí mismo y nos ahorramos una capa?**

La respuesta corta es que el dato crudo es la única versión que no se puede reconstruir. Las reglas de negocio cambian —hoy una devolución se descarta, mañana se quiere analizar— y sin Bronze cada cambio de criterio obliga a volver a pedirle datos históricos al sistema de origen, que muchas veces ya no los tiene.

---

**Siguiente:** [03 · Transformación Silver](03-silver.md)
