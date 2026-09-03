# Troubleshooting

Los casos están ordenados por frecuencia real en taller, no por gravedad.

---

## El síntoma que hay que aprender a reconocer

> **La ontología se creó bien y las consultas devuelven vacío o nulos.**

Fabric IQ en preview casi nunca falla con un error. Falla en silencio. Si ves entidades bien formadas, relaciones dibujadas y ningún dato, la causa está en esta lista y no en la ontología.

`nb_99_validacion` existe para detectar cinco de estas seis causas antes de llegar acá.

---

## La ontología se creó sin bindings

**Síntoma.** Las entidades y propiedades existen, pero no muestran fuente de datos. **Instances** viene vacío.

**Causas, en orden de probabilidad:**

1. **El workspace no tiene acceso público de entrada habilitado.** Con Direct Lake, la generación produce bindings **solo** si el workspace del lakehouse lo tiene habilitado.
   → Configuración del workspace → Red → **Acceso público de entrada: habilitado**. Regenera la ontología.

2. **El modelo semántico está en modo Import.** Import genera entidades y relaciones pero **nunca** bindings.
   → `nb_99` lo verifica. Recrea el modelo con `nb_04` (`overwrite=True`).

3. **La tabla no es managed.** La ontología solo enlaza tablas que viven en el directorio OneLake de su propio lakehouse. Shortcuts y tablas externas no sirven.
   → Los notebooks del taller escriben siempre en el directorio propio; si adaptaste el código, revisa la ruta.

4. **El lakehouse tiene OneLake security habilitada.** Un lakehouse con OneLake security no se puede usar como fuente de bindings.

---

## Todas las consultas devuelven `null` en una propiedad

**Causa.** La columna es de tipo `decimal`. Fabric Graph no lo soporta.

**Solución.** Castear a `double` en Silver y regenerar. El taller ya lo hace con `a_double()`; si agregaste columnas propias, pásalas por ahí.

> `Double` (coma flotante) sí está soportado. `Decimal` (precisión fija) no. Es contraintuitivo justamente para montos, que es donde más se usa `decimal`.

---

## Una tabla completa no devuelve datos

**Causa.** Delta activó *column mapping* en esa tabla. El grafo de la ontología no soporta tablas con column mapping.

Se activa **sola** cuando un nombre de columna contiene espacio, `,`, `;`, `{`, `}`, `(`, `)`, `=`, tabulación o salto de línea. También se activa sola en las tablas Delta que respaldan modelos semánticos en modo Import.

**Diagnóstico:**

```python
detalle = spark.sql(f"DESCRIBE DETAIL delta.`{ruta(LH_SILVER, 'ft_venta')}`").collect()[0]
print(detalle["properties"].get("delta.columnMapping.mode", "none"))
```

Debe decir `none`.

**Solución.** Renombrar la columna en Silver y **reescribir la tabla desde cero** (`overwrite`). Desactivar column mapping en una tabla existente no es trivial: es más rápido reescribirla.

---

## `set_synonym` lanza `ValueError`

```
The 'es-ES' culture does not exist within the semantic model.
Add a new culture using the add_translation function.
```

**Causa.** El esquema lingüístico vive por cultura, y la cultura no existe todavía en el modelo.

**Solución.** `tom.add_translation(language="es-ES")` **antes** del primer `set_synonym`, dentro del mismo `with`. `nb_05` ya lo hace; si escribiste tu propia celda, es esto.

---

## `list_synonyms` devuelve vacío después de correr `nb_05`

**Causa.** Alguna conexión quedó con `readonly=True` (el valor por defecto) y no hizo commit al salir del `with`.

**Solución.** Verifica que **todas** las conexiones que escriben tengan `readonly=False`:

```python
with connect_semantic_model(dataset=modelo, workspace=WORKSPACE_ID, readonly=False) as tom:
```

---

## Las columnas del modelo semántico no tienen descripción

**Causa.** Los comentarios de `nb_02` no se persistieron, o `nb_04` corrió antes que `nb_02`.

**Solución.**

1. Vuelve a ejecutar `nb_02` completo.
2. Vuelve a ejecutar `nb_04` (tiene `overwrite=True`, no hay que borrar los modelos).
3. Verifica en la última celda de `nb_04` que `columnas con descripcion heredada` sea > 0.

---

## Las relaciones de la ontología no tienen datos

**Síntoma.** Los relationship types aparecen, pero no hay instancias de relación y el grafo no conecta nada.

**Causa 1.** La relación quedó definida pero **sin binding**. La generación desde un modelo semántico deja las relaciones definidas y sin enlazar: hay que configurar **mapping table** y las dos columnas **Matched** a mano.

**Causa 2.** Faltó la clave primaria en el modelo. Los bindings de relación solo se generan cuando la clave primaria está identificada.
→ `nb_04`, bloque de claves: `col.IsKey = True`.

---

## El agente responde que no encuentra datos

En orden:

1. **Espera dos minutos.** El agente tarda en inicializarse tras agregar la fuente. Vuelve a preguntar.
2. **Falta la instrucción de agregación.** Agrega `Support group by in GQL` en **Agent instructions**. Sin eso, casi toda pregunta que agrupe falla.
3. **Faltan sinónimos.** Si preguntas por "sucursales" y la entidad es `Tienda` sin sinónimos, el agente no la encuentra. → [08-fabric-iq.md](08-fabric-iq.md#81--enriquecer-la-ontología).
4. **El grafo está desactualizado.** Refréscalo a mano.

---

## El grafo muestra datos viejos

**Causa.** Es el comportamiento esperado. El grafo se refresca solo cuando cambia el **esquema** de la ontología, no cuando cambian los **datos** de origen.

**Solución.** En el workspace, ubica el modelo de grafo asociado a la ontología → **... → Schedule** → dispara una actualización.

> El refresco es **completo** cada vez y tiene costo de capacidad. Agrupa los cambios antes de refrescar.

---

## No aparece "Generate Ontology" en el modelo semántico

1. **Ontology item (preview)** no está habilitado en el tenant → Portal de administración → Configuración del tenant.
2. El modelo está en **Mi área de trabajo**. No se puede generar una ontología desde ahí. Muévelo a un workspace propio.
3. El workspace no tiene capacidad Fabric asignada.

---

## No aparece el tipo de item "Data agent"

No está habilitado en el tenant. Requiere administrador de Fabric.

Alternativa sin agente: usa la vista de grafo de la ontología (**Overview → Expand → Query builder**) para mostrar las consultas cruzadas. Se pierde el lenguaje natural, se conserva el argumento.

---

## `notebookutils.lakehouse.create` falla con "already exists"

**Causa.** El lakehouse existe pero `get` falló, normalmente por una condición de carrera al ejecutar dos notebooks a la vez.

**Solución.** Vuelve a ejecutar la celda. `nb_00_setup` es idempotente.

---

## La sesión de Spark tarda muchísimo en arrancar

Normal en la primera ejecución del día: 2–4 minutos. Se puede reducir con un *starter pool* activo.

En un taller en vivo conviene que el facilitador ejecute una celda trivial en cada notebook **antes** de la sesión para dejar los pools calientes.

---

## `%pip install semantic-link-labs` reinicia el kernel

Es el comportamiento normal. Reinicia el intérprete de Python, **no** la sesión de Spark. Todo lo que había en memoria se pierde, incluidas las funciones y variables que define `%run nb_00_setup`.

Por eso en `nb_04`, `nb_05` y `nb_99` el `%pip` es la **primera** celda, antes del `%run`. Si ejecutas las celdas fuera de ese orden, o instalas algo a mitad del notebook, vuelve a correr el `%run nb_00_setup` antes de seguir.

Síntoma típico de haber invertido el orden:

```
NameError: name 'leer' is not defined
NameError: name 'LH_SILVER' is not defined
```

---

## No encuentro el error acá

Referencias oficiales:

- [Troubleshoot ontology (preview)](https://learn.microsoft.com/fabric/iq/ontology/resources-troubleshooting)
- [Generating an ontology from a semantic model — limitaciones](https://learn.microsoft.com/fabric/iq/ontology/concepts-generate)
- [Data binding — limitaciones](https://learn.microsoft.com/fabric/iq/ontology/how-to-bind-data)
- [semantic-link-labs](https://semantic-link-labs.readthedocs.io/)

Fabric IQ está en preview: partes de la interfaz cambian entre revisiones de este material. Si un paso no coincide con lo que ves, la documentación oficial manda.
