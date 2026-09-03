# 6 · Enriquecimiento semántico con sempy

⏱️ 20 minutos · Artefacto: `nb_05_enriquecer_sempy`

---

## El problema que resuelve

Los tres modelos están correctos. Tienen las tablas bien, las relaciones bien, las medidas bien. Y aun así un agente va a fallar, por una razón que no tiene nada que ver con el modelado:

**el usuario no usa las palabras del modelo.**

| Pregunta la gente | El modelo tiene |
|---|---|
| "los locales" / "las sucursales" | `Tienda` |
| "el SKU" / "el artículo" | `Producto` |
| "la facturación" | `monto_total` |
| "quiebre de cadena de frío" | `excursion_termica` |
| "entregas tardías" | `llego_atrasado` |

Ninguna de esas palabras aparece en el modelo. Un agente que no las conoce responde *"no encuentro esa información"* sobre datos que tiene delante.

Eso se arregla con vocabulario, y el vocabulario se aplica con código.

---

## Las tres capas que agrega el notebook

| Capa | Método TOM | Qué aporta |
|---|---|---|
| **Descripciones** | `Description` | Qué significa el objeto. Es lo que lee un agente al explorar el esquema |
| **Sinónimos** | `set_synonym` | Cómo lo llama la gente. Vive en el *esquema lingüístico*, por cultura |
| **Metadata de negocio** | `set_annotation` / `set_extended_property` | Unidad, dueño, umbral, sensibilidad |

### Descripciones de tabla

Las columnas ya heredaron su descripción de los comentarios Delta de `nb_02`. Falta el nivel de tabla, que es el que más pesa cuando un agente decide **qué entidad mirar**:

```python
"Despacho": (
    "Entrega ejecutada desde el centro de distribucion a una tienda. Grano: una "
    "fila por despacho. Un despacho atrasado es el primer indicador de riesgo de "
    "cadena de frio."
)
```

Fíjate en la última frase. No describe la tabla: describe **para qué sirve en el negocio**. Es lo que le permite a un agente conectar "riesgo de frío" con la entidad correcta.

### Sinónimos

```python
tom.add_translation(language="es-ES")   # ← obligatorio, y se olvida siempre
tom.set_synonym(
    culture="es-ES",
    object=tom.model.Tables["Tienda"],
    synonym_name="sucursal",
    weight=Decimal("0.9"),
)
```

> **`add_translation` primero.** El esquema lingüístico vive por cultura, y `set_synonym` **lanza un error** si la cultura no existe todavía en el modelo. Es el fallo más común de este bloque.

El `weight` (0 a 1) desempata cuando dos objetos comparten un término. `excursion_termica` lleva peso 1.0 para "quiebre de cadena de frío": queremos que gane siempre.

El vocabulario está definido **una sola vez** en el notebook y se aplica a los tres modelos. Que `Tienda` tenga los mismos sinónimos en los tres es el punto: un vocabulario común es lo que después permite que la ontología trate las tres tiendas como la misma cosa.

### Metadata de negocio

Lo que una descripción no alcanza a decir:

```python
("LecturaSensor", "temperatura_c", {
    "unidad": "grados Celsius",
    "umbral_excursion": "-15",
    "frecuencia_muestreo": "30 minutos",
    "dueno_dato": "Mantenimiento",
}),
```

Se aplica por las dos vías del TOM, porque no son lo mismo:

- **`set_annotation`** — clave/valor libre. Es el mecanismo estándar para metadata propia y sobrevive a los despliegues.
- **`set_extended_property`** — clave/valor tipado (`String` o `Json`), pensado para que lo consuman herramientas externas.

Estos pares son además el borrador de la **additional metadata** de la ontología: la estructura es idéntica, y en `nb_99` los exportamos ya con ese formato.

---

## Qué viaja a la ontología y qué no

Conviene decirlo antes de que alguien lo pregunte a mitad del bloque:

| | ¿Llega a la ontología? |
|---|---|
| Descripciones de columna (desde el comentario Delta) | **Sí** — es el puente real |
| Descripciones de tabla | **Sí** |
| Sinónimos del modelo semántico | **No** automáticamente |
| Anotaciones y extended properties | **No** automáticamente |
| Medidas DAX | **No**, y no las usa |

Los sinónimos que ponemos aquí sirven a Copilot y a P&R de Power BI. La ontología tiene **su propio campo de sinónimos**, que se carga en su interfaz.

No es trabajo perdido, por dos motivos: el modelo semántico también se consume solo, y `nb_99_validacion` exporta este vocabulario ya agrupado por entidad, listo para pegar en la ontología sin volver a inventarlo.

---

## Ejecución

Crea `nb_05_enriquecer_sempy` con el contenido de [`fabric/nb_05_enriquecer_sempy.Notebook/notebook-content.py`](../fabric/nb_05_enriquecer_sempy.Notebook/notebook-content.py) y ejecuta. ~3 minutos.

Salida esperada:

```
  sm_polar_ventas: 38 sinonimos
  sm_polar_operaciones: 32 sinonimos
  sm_polar_activos: 30 sinonimos

Total: 100 sinonimos en 3 modelos
```

Y la verificación final por modelo:

```
sm_polar_ventas
  tablas con descripcion    4/4
  columnas con descripcion  25
  columnas con metadata     8
  culturas                  ['en-US', 'es-ES']
```

Si `list_synonyms` devuelve vacío, el `with` no llegó a hacer commit: revisa que todas las conexiones tengan `readonly=False`.

---

## Pruébalo · el momento del taller

Antes de pasar a la ontología, vale la pena ver el efecto. Abre `sm_polar_ventas` en el workspace y usa Copilot o una visualización de preguntas y respuestas. Pregunta con las palabras del negocio, no con las del modelo:

- *¿cuál es la facturación por sucursal?*
- *¿qué locales vendieron más congelados?*
- *muéstrame el ticket promedio por tipo de cliente*

Ninguna de esas palabras es un nombre de tabla ni de columna. Antes de este notebook, el modelo no las entendía.

Y ahí está el argumento para el bloque siguiente: **si un vocabulario mejora tanto un modelo, la ontología es lo que permite tener un solo vocabulario para los tres.**

---

**Siguiente:** [07 · La ontología](07-ontologia.md)
