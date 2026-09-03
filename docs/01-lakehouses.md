# 1 · Tres lakehouses: Bronze, Silver, Gold

⏱️ 15 minutos · Artefacto: `nb_00_setup`

---

## Por qué tres y no uno

La arquitectura medallón separa el dato por **grado de confianza**, no por tema:

| Capa | Qué contiene | Regla | Quién manda |
|---|---|---|---|
| **Bronze** | El dato tal como llegó | No se limpia nada | Ingeniería |
| **Silver** | El dato que el negocio afirma | Se aplican reglas de calidad | Ingeniería + calidad de datos |
| **Gold** | Respuestas pre-calculadas | Solo datasets aprobados | Analítica |

Tres lakehouses separados, no tres carpetas en uno. Las razones prácticas:

- **Permisos distintos.** Bronze puede tener datos crudos con PII que nadie de negocio debería ver.
- **Optimización distinta.** Bronze se escribe mucho y se lee poco; Gold al revés. La configuración de Spark que conviene a uno perjudica al otro.
- **Ciclo de vida distinto.** Bronze se purga; Gold se conserva.
- **Linaje legible.** Cuando una cifra sale rara, se ve en qué capa se rompió.

Y una que aplica específicamente a este taller: **la ontología solo puede enlazar tablas managed**, es decir, tablas que viven físicamente dentro del directorio OneLake de su propio lakehouse. Los shortcuts encadenados entre capas no sirven. Cada capa se materializa de verdad.

---

## Crear los lakehouses

### Opción 1 · Con el notebook *(recomendada)*

`nb_00_setup` los crea si no existen. Es idempotente: se puede correr las veces que haga falta.

Hay dos formas de traer el notebook al workspace. Las dos dejan lo mismo:

**a) Importar el `.ipynb`** — más rápido, y es lo que conviene si vas justo de tiempo.

> **Importar → Notebook → Desde este equipo** → [`notebooks/nb_00_setup.ipynb`](../notebooks/nb_00_setup.ipynb)
>
> Puedes importar los siete de una vez y despreocuparte del resto del taller. **Conserva los nombres:** los demás notebooks invocan a `nb_00_setup` con `%run`, y esa llamada resuelve por nombre.

**b) Copiar celda por celda** desde [`fabric/nb_00_setup.Notebook/notebook-content.py`](../fabric/nb_00_setup.Notebook/notebook-content.py) — más lento, pero hace ver la estructura del notebook y de dónde sale cada cosa. Es la que suele usarse en el taller en vivo para este primer notebook, y la importación para los demás.

En cualquiera de los dos casos: **+ Nuevo item → Notebook**, nómbralo `nb_00_setup`, y ejecútalo completo.

En la salida deberías ver:

```
Workspace ID: 3f2a...
  CREADO     · lh_bronze_polar · 1a2b...
  CREADO     · lh_silver_polar · 3c4d...
  CREADO     · lh_gold_polar   · 5e6f...
```

En una segunda ejecución dirá `ya existe`. Eso está bien.

### Opción 2 · A mano

**+ Nuevo item → Lakehouse**, tres veces, con los nombres de la tabla de convenciones. Deja marcada la opción de **esquemas de lakehouse** (schema-enabled): el taller usa el esquema `dbo`.

### Opción 3 · Vía git

Ya están en el repositorio. → [09-via-rapida-git.md](09-via-rapida-git.md)

---

## Qué hace `nb_00_setup` y por qué importa

Este notebook no escribe datos. Define la configuración y los helpers que usan todos los demás. Vale la pena mirarlo, porque resuelve un problema real que aparece siempre que un repositorio de Fabric se comparte.

### El problema del lakehouse "pegado"

Un notebook de Fabric normalmente lleva un lakehouse por defecto anclado en su metadata, por GUID:

```json
"default_lakehouse": "fef4e400-36b2-4048-95d2-c1eb2197b4c8"
```

Ese GUID es **específico de un workspace**. Si el notebook viaja a otro workspace por git, el GUID apunta a un lakehouse que ahí no existe, y todo falla en la primera celda que toque una tabla.

### La solución del taller

Ninguno de estos notebooks tiene lakehouse anclado. En vez de eso:

1. Se lee el workspace actual del contexto de ejecución:
   ```python
   WORKSPACE_ID = notebookutils.runtime.context["currentWorkspaceId"]
   ```
2. Se resuelven los lakehouses **por nombre**, y se crean si faltan.
3. Se lee y escribe con rutas `abfss://` explícitas:
   ```python
   abfss://{workspace_id}@onelake.dfs.fabric.microsoft.com/{lakehouse_id}/Tables/dbo/{tabla}
   ```

El resultado es un repositorio que funciona en el workspace de cualquiera sin editar una línea. Es también, de paso, el patrón correcto para escribir entre lakehouses en producción.

> **Opcional, solo para comodidad visual:** puedes adjuntar `lh_silver_polar` como lakehouse por defecto en el explorador del notebook, para ver las tablas mientras trabajas. No cambia nada del código.

### La función que evita el problema más caro

`nb_00_setup` define `validar_para_ontologia(df, nombre, clave)`, que se llama antes de cada escritura en Silver y verifica tres cosas:

| Verifica | Por qué |
|---|---|
| Ninguna columna `decimal` | Fabric Graph no soporta ese tipo: devuelve `null` en toda consulta de la ontología |
| Ningún nombre con espacio, `,`, `;`, `{}`, `()`, `=`, tab o salto de línea | Delta activaría *column mapping* y el grafo dejaría de leer la tabla |
| La clave existe, es `string` o `integer`, y es única | Es la futura *entity type key* |

Ninguna de las tres da error en Fabric IQ cuando fallan. La ontología se crea, se ve bien, y devuelve vacío. Fallar aquí, con un `ValueError` explícito en el notebook, es mucho mejor negocio.

---

## Verificación

En el explorador del workspace deben aparecer los tres lakehouses, vacíos. Cada uno con su SQL analytics endpoint y su modelo semántico por defecto, que Fabric crea solo y que **no vamos a usar**: los modelos del taller se crean en el bloque 5.

---

**Siguiente:** [02 · Ingesta Bronze](02-bronze.md)
