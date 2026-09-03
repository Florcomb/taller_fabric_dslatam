# Vía rápida · crear todo desde GitHub

⏱️ 10–15 minutos hasta tener los 10 items creados

---

En vez de crear los tres lakehouses y los siete notebooks a mano, se conecta el workspace de Fabric a un fork de este repositorio y **Fabric los crea solos**.

Sirve para tres situaciones:

- Alguien llegó tarde o se quedó atrás y necesita alcanzar al grupo.
- El facilitador quiere tener el workspace de respaldo listo antes de la sesión.
- Alguien quiere repetir el taller después, sin volver a teclear nada.

> **Lo que esto no hace:** no trae datos. La integración con git sincroniza la **definición** de los items, no el contenido de las tablas. Los tres lakehouses llegan vacíos y hay que ejecutar `nb_01` igual. Es lo correcto: los datos de un lakehouse no son código.

---

## 1 · Fork del repositorio

En [github.com/wcalcagno/taller_fabric_dslatam](https://github.com/wcalcagno/taller_fabric_dslatam) → **Fork** → a tu cuenta personal.

Necesitas tu propio fork, no el original: Fabric va a querer escribir en el repositorio cuando hagas *commit* de lo que construyas.

---

## 2 · Token de acceso de GitHub

Fabric se autentica contra GitHub con un **Personal Access Token**.

**GitHub → Settings → Developer settings → Personal access tokens**

| Tipo de token | Permisos |
|---|---|
| Fine-grained *(recomendado)* | Solo el repositorio del fork · **Contents: Read and write** |
| Classic | Alcance `repo` |

Copia el token: GitHub lo muestra una sola vez.

---

## 3 · Conectar el workspace

En tu workspace de Fabric:

**Configuración del workspace → Integración con Git**

| Campo | Valor |
|---|---|
| Proveedor de Git | **GitHub** |
| URL del repositorio | `https://github.com/<tu-usuario>/taller_fabric_dslatam` |
| Token | El del paso 2 |
| Rama | `main` |
| Directorio | **`/fabric`** |

**Conectar y sincronizar**.

> **El directorio importa.** Si apuntas a la raíz, Fabric intenta interpretar `docs/`, `notebooks/`, `ontologia/` e `instructor/` como items y no encuentra nada válido. Apunta a `/fabric`, que es donde viven los items.

> **`notebooks/` no se sincroniza, y es a propósito.** Esa carpeta tiene los mismos siete notebooks en `.ipynb`, para quien los importa a mano o los abre en VS Code. Vive fuera de `/fabric` justamente para que Fabric no intente crear siete notebooks duplicados. Si usas la vía rápida, ignórala.

---

## 4 · Actualizar

El panel de **Control de código fuente** muestra 10 cambios entrantes. **Actualizar todo**.

Al terminar, en el workspace deben aparecer:

| Item | Tipo |
|---|---|
| `lh_bronze_polar` · `lh_silver_polar` · `lh_gold_polar` | Lakehouse |
| `nb_00_setup` | Notebook |
| `nb_01_bronze_ingesta` · `nb_02_silver_transforma` · `nb_03_gold_agrega` | Notebook |
| `nb_04_modelos_semanticos` · `nb_05_enriquecer_sempy` · `nb_99_validacion` | Notebook |

---

## 5 · Ejecutar

Los lakehouses están vacíos. En orden:

```
nb_01_bronze_ingesta      ~3 min
nb_02_silver_transforma   ~3 min
nb_03_gold_agrega         ~2 min
nb_04_modelos_semanticos  ~6 min   (instala semantic-link-labs)
nb_05_enriquecer_sempy    ~3 min
nb_99_validacion          ~2 min
```

`nb_00_setup` no se ejecuta solo: los demás lo invocan con `%run`.

Desde ahí, sigue en [07-ontologia.md](07-ontologia.md). La ontología se construye en la interfaz, igual para las dos vías.

---

## Por qué esto funciona en cualquier workspace

Un repositorio de Fabric normalmente **no** es portable, y vale la pena entender por qué este sí lo es. Es la parte de CI/CD que este bloque enseña de regalo.

### El problema

Un notebook de Fabric suele llevar su lakehouse anclado en la metadata, por GUID:

```json
"dependencies": {
  "lakehouse": {
    "default_lakehouse": "fef4e400-36b2-4048-95d2-c1eb2197b4c8",
    "default_lakehouse_workspace_id": "fb0905fd-76e1-4862-81bf-a8ad86ea00d6"
  }
}
```

Esos GUIDs son de **un** workspace. Al sincronizar el repositorio en otro, el notebook apunta a un lakehouse que ahí no existe. Falla en la primera celda que toque una tabla, con un error que no explica la causa.

### La solución del taller

Los notebooks de `fabric/` tienen `"dependencies": {}`. Ningún lakehouse anclado. En su lugar, `nb_00_setup`:

1. lee el workspace actual del contexto de ejecución,
2. resuelve los lakehouses **por nombre** y los crea si faltan,
3. lee y escribe con rutas `abfss://` construidas en tiempo de ejecución.

El mismo repositorio funciona en el workspace de cualquiera sin editar una línea.

### El `logicalId`

Cada item del repositorio tiene un `.platform` con un `logicalId`:

```json
{
  "metadata": { "type": "Notebook", "displayName": "nb_01_bronze_ingesta" },
  "config": { "version": "2.0", "logicalId": "0abc4b58-e764-4f01-a118-906b0e8ea6a1" }
}
```

Es el identificador que conecta un item del workspace con su representación en git. Sobrevive a renombres y a cambios de carpeta. Una misma rama puede sincronizarse en **varios workspaces** —todos los participantes a la vez— sin conflicto, porque cada workspace mantiene su propio mapeo entre `logicalId` e ID real.

Por eso, si duplicas una carpeta de item para crear uno nuevo, **hay que cambiar el `logicalId`**: dos items con el mismo `logicalId` en un mismo workspace es un estado inválido.

---

## Guardar tu trabajo de vuelta en git

Todo lo que construyas después —los modelos semánticos, la ontología— se puede comprometer al repositorio.

**Control de código fuente → Cambios sin confirmar → Confirmar**

Se sincronizan, entre otros:

- **Modelos semánticos** *(preview)* — como carpeta `definition/` con TMDL. Muy legible en un diff: se ve exactamente qué medida cambió.
- **Ontología** *(preview)* — con su estructura de `EntityTypes/` y `RelationshipTypes/`, cada uno con su `definition.json` y sus carpetas de bindings.

> **Advertencia honesta sobre la ontología en git.** El soporte es **preview** y los data bindings hacen referencia a lakehouses del workspace donde se creó la ontología. Restaurar la ontología en un workspace distinto probablemente exija revisar y rehacer los bindings. Como respaldo de la estructura funciona bien; como despliegue entre entornos, todavía no lo trates como resuelto.

Los tres lakehouses sincronizan su definición y sus shortcuts, **nunca sus datos**.

---

## Si algo sale mal

| Síntoma | Causa habitual |
|---|---|
| No aparece ningún cambio entrante | El **Directorio** no apunta a `/fabric` |
| Error de autenticación | Token vencido, o sin permiso **Contents: Read and write** |
| Los notebooks llegan pero fallan al ejecutar | Se ejecutó otro notebook antes que `nb_01`, o falta capacidad Fabric |
| "Item no soportado" en algún item | Tipo no soportado por git integration en tu tenant. El resto sincroniza igual |
| Un item aparece duplicado | Se copió una carpeta sin cambiar el `logicalId` |

---

**Volver a:** [README](../README.md) · **Seguir en:** [07 · La ontología](07-ontologia.md)
