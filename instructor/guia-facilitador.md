# Guía de facilitación

Taller Fabric IQ · 150 minutos

---

## La idea que hay que dejar instalada

Todo el taller sirve a una sola frase:

> **La ontología no reemplaza a Gold. Reemplaza a la siguiente tabla de Gold que ibas a escribir.**

Todo lo demás —medallón, Direct Lake, `sempy`, sinónimos— es el andamiaje que permite llegar a esa frase con evidencia en pantalla en vez de con una lámina.

El arco narrativo es una sola pregunta, planteada en el minuto 5 y respondida dos veces:

1. **Minuto 75, en `nb_03`:** a la fuerza. Tres agregaciones, cuatro joins, ~50 líneas, una tabla materializada que sirve para esa pregunta y ninguna otra.
2. **Minuto 145, con el agente:** en lenguaje natural, sin escribir un join, y con tres variantes seguidas que en Gold habrían sido tres tablas más.

Si el taller se cae en algún punto, **protege esos dos momentos**. Todo lo demás es negociable.

---

## Ritmo por bloque

| # | Bloque | Min | Acumulado | Modo |
|---|---|---|---|---|
| 0 | Contexto y preparación | 10 | 10 | Expositivo |
| 1 | Tres lakehouses | 15 | 25 | Manos a la obra |
| 2 | Bronze | 15 | 40 | Manos a la obra |
| 3 | Silver | 20 | 60 | Manos a la obra + discusión |
| 4 | Gold | 10 | 70 | **Momento 1** |
| 5 | Modelos semánticos | 20 | 90 | Manos a la obra |
| 6 | sempy | 20 | 110 | Manos a la obra + prueba |
| 7 | Ontología | 25 | 135 | Manos a la obra, guiado |
| 8 | Fabric IQ | 15 | 150 | **Momento 2** |

**Dónde recortar, en este orden:**

1. Bloque 4 → ejecutar `nb_03` sin comentar los agregados, pero **mostrar `agg_riesgo_cadena_frio`**. Ahorra 6 min.
2. Bloque 7 → saltar `Ruta` y `Vehiculo` (ya son opcionales). Si urge, saltar también `Despacho` y quedarse con `Equipo` + `LecturaSensor`: la pregunta del taller pierde una dimensión pero sigue cruzando dos dominios. Ahorra 8 min.
3. Bloque 8 → cargar sinónimos solo en `Tienda`, `Equipo` y `LecturaSensor`. Ahorra 4 min.

**Lo que no se recorta:** el bloque 3 (Silver). Es donde se plantan las cuatro reglas que hacen que la ontología funcione. Si se recorta ahí, el bloque 7 falla y no se entiende por qué.

---

## Bloque por bloque

### 0 · Contexto · 10 min

Abre con la pregunta, no con la arquitectura:

> *¿Cuánta venta de congelado hubo en tiendas que ese día tuvieron un freezer fuera de rango y un despacho atrasado?*

Y la observación que la sigue: en cualquier empresa real, esos tres datos pertenecen a tres gerencias distintas, con tres sistemas y tres equipos de datos. Nadie tiene un modelo único.

Deja la distinción **modelo semántico vs ontología** planteada y sin cerrar. Se cierra sola en el bloque 7.

Di de entrada que **Fabric IQ está en preview**. Baja la ansiedad cuando algo no coincida con el material.

### 1 · Lakehouses · 15 min

El contenido técnico es trivial; el valor está en `nb_00_setup`. Detente en el problema del lakehouse anclado por GUID y en por qué estos notebooks no lo tienen. Es la parte de CI/CD que la mayoría no ha visto.

Menciona `validar_para_ontologia()` sin explicarla todavía. Se explica en el bloque 3, cuando falle... o cuando pase.

**Trampa de tiempo:** el primer arranque de Spark. Si dejaste los pools calientes (checklist D), son 30 segundos; si no, 4 minutos de silencio.

### 2 · Bronze · 15 min

Mientras corre, recorre la tabla de defectos plantados. Detente en **`"Monto Total"` con espacio**: es el defecto más importante del taller y el que menos se ve venir.

**Pregunta para la sala:** *¿por qué no limpiamos aquí mismo y nos ahorramos una capa?* Deja que respondan antes de dar la razón (las reglas de negocio cambian; el dato crudo es la única versión que no se puede reconstruir).

### 3 · Silver · 20 min · el bloque denso

Aquí se juega el resto del taller. Tres cosas que no se pueden pasar rápido:

1. **Nada de `decimal`.** Es contraintuitivo —`decimal` es el tipo correcto para dinero— y por eso se olvida. Consecuencia: `null` en todas las consultas de la ontología, sin aviso.
2. **El renombre de `"Monto Total"` va en la primera línea.** Explica *column mapping* y por qué la falla es silenciosa.
3. **La cadena de los comentarios.** Comentario Delta → descripción del modelo → descripción de la entidad → contexto del agente. Es la inversión de documentación con mejor retorno del taller, y la que todo el mundo se salta.

**Discusión:** *¿por qué descartamos las devoluciones en vez de marcarlas?* No hay respuesta única. El punto es que una entidad debe significar **una** cosa: un `Venta` que a veces es una devolución es una entidad que un agente va a interpretar mal.

### 4 · Gold · 10 min · **momento 1**

Ejecuta rápido los tres agregados. Detente en `agg_riesgo_cadena_frio`.

Proyecta el código y **haz contar las líneas en voz alta**. Después:

> *¿Y si ahora preguntan por marca en vez de categoría?* — Tabla nueva.
> *¿Y si preguntan por el cliente?* — Tabla nueva.

**Anota el monto que imprime la última celda en un lugar visible.** Se compara en el minuto 145.

Y planta la decisión que va a generar discusión: **los modelos semánticos se construyen sobre Silver, no sobre Gold.** Deja que la objeción salga de la sala. La respuesta: la ontología necesita grano atómico; un agregado diario no es una entidad porque no tiene identidad.

### 5 · Modelos semánticos · 20 min

Tres puntos con consecuencia:

- **Direct Lake no es preferencia, es requisito.** Import genera entidades sin bindings.
- **Los nombres de tabla se convierten en nombres de entidad.** Por eso `Tienda` y no `dim_tienda`. Muestra que gracias a eso, en el bloque 7 no habrá que renombrar nada.
- **Las claves.** El paso que se salta y que después cuesta media hora de trabajo manual en la interfaz.

Menciona que **las medidas no viajan a la ontología**. Genera buena conversación: lo que sirve a un informe y lo que sirve a un agente no es lo mismo.

**Trampa de tiempo:** `%pip install semantic-link-labs` toma ~1 minuto y reinicia el intérprete de Python. Avísalo antes de que alguien crea que se rompió.

### 6 · sempy · 20 min

El bloque más satisfactorio, porque el efecto se ve al final.

`add_translation` **antes** de `set_synonym`: es el error más común y lanza un `ValueError` explícito.

**Reserva 5 minutos para la prueba.** Abrir `sm_polar_ventas` y preguntarle a Copilot *"¿cuál es la facturación por sucursal?"*. Ninguna de esas dos palabras existe en el modelo. Que lo vean funcionar es lo que justifica el bloque 7.

Sé explícito con lo que **no** se hereda: los sinónimos del modelo semántico no bajan a la ontología. No es trabajo perdido —el modelo también se consume solo, y `nb_99` exporta el vocabulario listo para pegar— pero decirlo evita una decepción a mitad del bloque 7.

### 7 · Ontología · 25 min · el bloque guiado

**Corre `nb_99_validacion` primero. Sin excepciones.** Es lo que evita diagnosticar a ciegas más adelante.

Ve despacio en la primera relación y rápido en las demás: el concepto de **mapping table** cuesta una vez y después es mecánico.

Cuando llegues a las relaciones cruzadas del paso 7.5, **para y nómbralo**. Es el momento en que tres dominios que en la empresa real no se hablan quedan conectados. Dibuja el grafo en la pizarra si hace falta.

Ten [`ontologia/mapa-entidades.md`](../ontologia/mapa-entidades.md) proyectado: tiene todo lo que hay que teclear.

**Si Instances viene vacío, no avances al bloque 8.** Cambia al workspace de respaldo. El bloque 8 sin datos no es demostrable.

### 8 · Fabric IQ · 15 min · **momento 2**

`Support group by in GQL` en las instrucciones del agente. Sin eso, casi nada agrega bien.

Sigue el guion de 6 minutos de [`ontologia/preguntas-demo.md`](../ontologia/preguntas-demo.md). La clave del cierre es **el ritmo**: tres variantes seguidas, sin pausa, para que se sienta que entre una pregunta y la siguiente no hubo desarrollo.

Cierra con las limitaciones reales. Un taller que promete magia deja gente frustrada el lunes; uno que dice dónde está el borde deja gente que confía en lo que le dijiste.

---

## Objeciones que van a aparecer

**"Esto es lo mismo que un modelo semántico bien hecho."**
No: un modelo semántico responde dentro de su dominio. La prueba está en la pregunta del taller, que ninguno de los tres modelos puede contestar. Y el argumento más fuerte es de gobierno, no técnico: en una empresa real esos tres modelos pertenecen a tres gerencias y nadie los va a fusionar.

**"¿Por qué no un solo modelo con las nueve tablas?"**
Porque nadie lo tiene. Y porque si lo tuvieras, la ontología no aportaría: su valor aparece cuando el conocimiento está repartido.

**"Esto es un data catalog con otro nombre."**
Un catálogo describe **dónde** está el dato. La ontología describe **qué significa** y **cómo se conecta**, y es consultable. Un catálogo no responde preguntas.

**"¿Y el rendimiento?"**
Es preview, y el grafo se refresca completo, con costo de capacidad. Hoy la ontología es una inversión en vocabulario gobernado, no un motor de consulta de alto volumen. Decirlo sube tu credibilidad, no la baja.

**"¿Reemplaza a Power BI?"**
No. Los informes siguen siendo la forma correcta de mirar métricas conocidas. La ontología es para las preguntas que todavía no se hicieron.

---

## Errores que vas a ver en sala

| Síntoma | Causa | Solución en vivo |
|---|---|---|
| `NameError: name 'leer' is not defined` | Ejecutaron `%pip` después del `%run` | Volver a correr la celda del `%run` |
| `set_synonym` lanza `ValueError` | Falta `add_translation` | Está en el notebook; ejecutaron celdas sueltas |
| Ontología sin bindings | Acceso público de entrada deshabilitado | Habilitarlo y regenerar. Si no se puede, respaldo |
| `Instances` vacío | Igual que arriba, o modelo en Import | `nb_99` lo detecta |
| Una propiedad siempre en `null` | Columna `decimal` | Silver, castear a `double` |
| El agente no encuentra nada | Falta `Support group by in GQL`, o faltan sinónimos | Ambas cosas se arreglan en un minuto |
| Todo lento | Starter pool frío | Paciencia; la próxima vez, checklist D |

Detalle completo en [`docs/99-troubleshooting.md`](../docs/99-troubleshooting.md).

---

## Si te sobran 15 minutos

- **`Ruta` y `Vehiculo`** en la ontología, y la pregunta *"¿los despachos en vehículos sin refrigeración generan más excursiones térmicas?"*
- **Fabric Graph directo**: abrir el grafo y escribir una consulta GQL a mano. Muestra que debajo del lenguaje natural hay un motor de grafo de verdad.
- **Commit a git** de la ontología, y ver su estructura de `EntityTypes/` y `RelationshipTypes/` en GitHub. Cierra el círculo con la vía B.
- **Time series binding** sobre `Equipo`: es el modelado correcto para IoT y muestra la diferencia entre binding estático y de serie de tiempo.

## Si te faltan 15 minutos

Salta a lo mínimo indispensable del [checklist](checklist-preflight.md#lo-mínimo-indispensable): la tabla de Gold, el grafo, la pregunta al agente. Tres minutos, y es el taller completo en miniatura.
