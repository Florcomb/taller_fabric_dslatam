# 4 · Agregados Gold

⏱️ 10 minutos · Artefacto: `nb_03_gold_agrega`

---

Este es el bloque que se recorta si el tiempo aprieta: se ejecuta el notebook sin comentarlo y se sigue. Pero la última tabla que produce **es el argumento central del taller**, así que si hay que recortar, recorta las tres primeras y muestra la cuarta.

## Las cuatro tablas

| Tabla | Grano | Para qué |
|---|---|---|
| `agg_venta_dia_tienda` | día × tienda × categoría | Informe comercial |
| `agg_despacho_dia_ruta` | día × ruta | Informe de operaciones |
| `agg_frio_dia_equipo` | día × equipo | Informe de mantenimiento |
| `agg_riesgo_cadena_frio` | día × tienda | **La pregunta cruzada** |

---

## La decisión que genera discusión

> Los tres modelos semánticos del taller se construyen sobre **Silver**, no sobre Gold.

Va contra lo que casi todo el mundo enseña. La razón:

**La ontología necesita entidades a grano atómico.** Una fila = una venta, un despacho, una lectura. Un agregado diario no es una entidad de negocio: es un resumen. No tiene identidad propia, no participa en relaciones, y no se puede navegar. `agg_venta_dia_tienda` no responde "¿qué le pasó a *esta* venta?" porque esa venta ya no existe como fila.

Entonces Gold sigue existiendo y sigue siendo la capa correcta para BI. Simplemente **BI y ontología quieren cosas distintas**:

| | Power BI quiere | La ontología quiere |
|---|---|---|
| Grano | El más grueso que sirva | El más fino posible |
| Columnas | Las del informe | Todas las que describan la entidad |
| Estructura | Estrella, desnormalizada | Entidades con identidad y relaciones |
| Cambios | Una tabla nueva por pregunta nueva | Ninguna: se navega el grafo |

Ese contraste es uno de los aprendizajes del taller. No es que Gold esté mal: es que Gold optimiza para una pregunta conocida, y la ontología existe para las preguntas que todavía no se hicieron.

---

## `agg_riesgo_cadena_frio`, o por qué existe Fabric IQ

La pregunta:

> *¿Cuánta venta de producto congelado ocurrió en tiendas que ese mismo día tuvieron un freezer en excursión térmica y recibieron un despacho atrasado?*

Ninguno de los tres modelos semánticos puede responderla. La venta está en uno, el despacho en otro, la temperatura en el tercero.

Para contestarla en Gold hay que escribir esto:

```python
riesgo_frio      = ft_lectura  ▷ dim_equipo  ▷ group by (fecha, tienda)  ▷ filter
riesgo_despacho  = ft_despacho ▷ filter atrasado ▷ group by (fecha, tienda)
venta_congelado  = ft_venta    ▷ dim_producto (requiere_frio) ▷ group by (fecha, tienda)

agg_riesgo_cadena_frio = venta_congelado ▷ riesgo_frio ▷ riesgo_despacho ▷ dim_tienda
```

Tres agregaciones intermedias, cuatro joins, una tabla materializada. Unas 50 líneas.

Y ahora la parte incómoda: **esa tabla sirve para esa pregunta y para ninguna otra.**

- ¿Y si preguntan por *marca* en vez de categoría? Tabla nueva.
- ¿Y si preguntan por *vehículo sin refrigeración* en vez de despacho atrasado? Tabla nueva.
- ¿Y si preguntan por el *cliente* que compró el producto afectado? Tabla nueva.

Cada pregunta cruzada cuesta una tabla, un desarrollo y un despliegue. Eso es lo que la ontología viene a reemplazar: en el bloque 8 hacemos esta misma pregunta —y las tres variantes— en lenguaje natural, sin escribir un solo join.

Guarda el número que imprime la última celda:

```
Venta de congelado expuesta a riesgo de cadena de frio: $XX,XXX,XXX CLP
Dias-tienda afectados: XXX
```

Lo vamos a comparar contra lo que responda el agente.

---

## Configuración de Spark para Gold

Tres líneas al inicio del notebook, antes de cualquier escritura:

```python
spark.conf.set("spark.sql.parquet.vorder.default", "true")
spark.conf.set("spark.databricks.delta.optimizeWrite.enabled", "true")
spark.conf.set("spark.databricks.delta.optimizeWrite.binSize", "1g")
```

| Ajuste | Qué hace |
|---|---|
| **V-Order** | Ordenamiento columnar propio de Fabric. Mejora mucho la lectura desde Direct Lake y desde el SQL endpoint |
| **Optimize Write** | Fusiona particiones chicas en archivos de ~1 GB. Menos archivos, menos overhead de escaneo |

Es el perfil de lectura intensiva: Gold se escribe una vez al día y se lee cientos de veces. En Bronze convendría lo contrario.

---

## Ejecución

Crea `nb_03_gold_agrega` con el contenido de [`fabric/nb_03_gold_agrega.Notebook/notebook-content.py`](../fabric/nb_03_gold_agrega.Notebook/notebook-content.py) y ejecútalo. ~2 minutos.

## Opcional · un informe rápido

Si sobra tiempo: sobre `lh_gold_polar`, **Nuevo informe** desde el modelo semántico por defecto del lakehouse, con `agg_riesgo_cadena_frio` en una tabla ordenada por `venta_congelado`. Es la versión "clásica" del resultado, y sirve de contraste visual con lo que hace el agente en el bloque 8.

---

**Siguiente:** [05 · Tres modelos semánticos](05-modelos-semanticos.md)
