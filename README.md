# Taller Fabric IQ · de lakehouse a ontología en 2 horas y media

De datos crudos a una ontología que responde preguntas que ningún modelo semántico contesta solo.
Microsoft Fabric · Data Science LATAM

> **Aviso.** Los datos de este taller son **sintéticos y de uso exclusivamente formativo**. *Polar Sur* es una cadena ficticia. Ninguna cifra, tienda ni cliente corresponde a una empresa real. El notebook `nb_01` genera todo el dataset: no hay que descargar nada ni conectarse a ninguna fuente externa.

---

## Qué se construye

Al terminar el taller cada participante tiene, en su propio workspace de Fabric:

- **3 lakehouses** en arquitectura medallón — Bronze, Silver, Gold
- **6 notebooks** de ingesta y transformación en PySpark, sin un solo dataflow
- **3 modelos semánticos** Direct Lake sobre Silver, uno por dominio de negocio
- **1 vocabulario** de ~90 sinónimos y metadata de negocio aplicado con `sempy`
- **1 ontología** de Fabric IQ que une los tres dominios
- **1 agente** que responde en lenguaje natural cruzando los tres

## La pregunta que ordena todo el taller

> *¿Cuánta venta de producto congelado ocurrió en tiendas que ese mismo día tuvieron un freezer fuera de rango y recibieron un despacho atrasado?*

La venta está en un modelo. El despacho, en otro. La temperatura, en un tercero. **Ninguno de los tres puede responderla.** En `nb_03` la respondemos a la fuerza: tres agregaciones y cuatro joins escritos a mano, materializados en una tabla que solo sirve para esa pregunta. Cada pregunta nueva, una tabla nueva.

Eso es exactamente lo que la ontología viene a reemplazar. El taller completo es la demostración de esa diferencia.

---

## El caso · Polar Sur

Cadena chilena ficticia de heladerías, con tres dominios que en la vida real pertenecen a tres gerencias distintas, con tres sistemas distintos y tres equipos de datos distintos:

| Dominio | Sistema de origen | Pregunta típica | Modelo semántico |
|---|---|---|---|
| **Comercial** | POS + CRM + PIM | ¿Cuánto vendimos y a quién? | `sm_polar_ventas` |
| **Logística** | TMS | ¿Llegaron a tiempo los despachos? | `sm_polar_operaciones` |
| **Cadena de frío** | Sensores IoT + CMMS | ¿Se mantuvo la temperatura? | `sm_polar_activos` |

La **tienda** aparece en los tres. Ese solapamiento es el diseño: es el punto donde la ontología cose los dominios.

---

## Dos formas de hacer el taller

### Vía A · Paso a paso *(la del taller en vivo)*

Se construye todo a mano siguiendo `docs/`. Es la que enseña, porque los errores aparecen y se explican en el momento.

### Vía B · Vía rápida por git

Se hace *fork* de este repositorio, se conecta el workspace de Fabric a ese fork y **los items se crean solos**: los tres lakehouses y los seis notebooks llegan al workspace sin crear nada a mano. Sirve para quien llega tarde, para quien se quedó atrás en un paso, o para repetir el taller después.

→ **[docs/09-via-rapida-git.md](docs/09-via-rapida-git.md)**

Las dos vías convergen en el paso 6. Desde el modelo semántico en adelante el camino es el mismo, porque la ontología se construye en la interfaz de Fabric.

---

## Agenda · 150 minutos

| # | Bloque | Min | Guía | Artefacto |
|---|---|---|---|---|
| 0 | Contexto y preparación | 10 | [00-preparacion.md](docs/00-preparacion.md) | Workspace + tenant settings |
| 1 | Tres lakehouses B/S/G | 15 | [01-lakehouses.md](docs/01-lakehouses.md) | `nb_00_setup` |
| 2 | Ingesta Bronze | 15 | [02-bronze.md](docs/02-bronze.md) | `nb_01_bronze_ingesta` |
| 3 | Transformación Silver | 20 | [03-silver.md](docs/03-silver.md) | `nb_02_silver_transforma` |
| 4 | Agregados Gold | 10 | [04-gold.md](docs/04-gold.md) | `nb_03_gold_agrega` |
| 5 | Tres modelos semánticos | 20 | [05-modelos-semanticos.md](docs/05-modelos-semanticos.md) | `nb_04_modelos_semanticos` |
| 6 | Enriquecimiento con sempy | 20 | [06-enriquecimiento-sempy.md](docs/06-enriquecimiento-sempy.md) | `nb_05_enriquecer_sempy` |
| 7 | **Ontología** | 25 | [07-ontologia.md](docs/07-ontologia.md) | Ontology item |
| 8 | Fabric IQ en acción | 15 | [08-fabric-iq.md](docs/08-fabric-iq.md) | Data agent |

Si el tiempo aprieta, el bloque 4 (Gold) es el que se recorta: se ejecuta el notebook sin comentarlo. Lo que **no** se recorta es el bloque 7.

---

## Contenido del repositorio

| Ruta | Qué es | ¿Quién lo usa? |
|---|---|---|
| `docs/` | Los nueve pasos del taller, uno por archivo | Participantes |
| `fabric/` | Items listos para git sync: 3 lakehouses + 7 notebooks | Participantes (vía B) |
| `notebooks/` | Los mismos 7 notebooks en `.ipynb`, para importar a mano | Participantes (vía A) |
| `ontologia/` | Mapa de entidades y relaciones, y el set de preguntas de demo | Participantes |
| `instructor/` | Guía de facilitación, tiempos, plan B y checklist previo | **Solo facilitadores** |
| `tools/` | Conversor que genera los `.ipynb` desde los `.py` | Mantención del repo |

### Los notebooks vienen en dos formatos

Con el mismo contenido, para dos formas distintas de trabajar:

| | `fabric/<nombre>.Notebook/notebook-content.py` | `notebooks/<nombre>.ipynb` |
|---|---|---|
| Formato | Integración con git de Fabric | Jupyter estándar |
| Llega al workspace | Solo con conectar git | **Importar → Notebook → desde este equipo** |
| Se sincroniza | **Sí** | No — vive fuera de `/fabric` |
| Se lee en GitHub | Sí, como Python | Regular: es JSON |
| Se abre en VS Code | No como notebook | **Sí** |

El `.py` es la **fuente de verdad**: es lo que Fabric sincroniza, y lo que llega de vuelta cuando alguien confirma un cambio desde el workspace. Los `.ipynb` se generan con `python tools/py_a_ipynb.py`. Detalle en [notebooks/README.md](notebooks/README.md).

---

## Requisitos previos

Sin esto el taller no corre. Verificarlo **antes** de la sesión, no durante.

| Requisito | Cómo verificarlo |
|---|---|
| Capacidad Fabric (F2 o superior, o trial) asignada al workspace | Configuración del workspace → Licencia |
| Workspace propio, **no** "Mi área de trabajo" | La ontología no se puede generar desde Mi área de trabajo |
| **Ontology item (preview)** habilitado en el tenant | Portal de administración → Configuración del tenant |
| **Acceso público de entrada** habilitado en el workspace | Sin esto la ontología se crea **sin bindings a datos** |
| Permiso para crear items y ejecutar notebooks | Rol de Colaborador o superior |
| Cuenta de GitHub *(solo vía B)* | Para el fork y la conexión de git |

> Fabric IQ y el item de ontología están en **preview**. Es una tecnología en movimiento: partes de la interfaz pueden haber cambiado desde la última revisión de este material. Cada paso indica el comportamiento verificado y qué hacer si no coincide.

`docs/00-preparacion.md` tiene el detalle de cada punto con las rutas exactas de configuración.

---

## Orden de ejecución de los notebooks

```
nb_00_setup              ← no se ejecuta solo; los demás lo invocan con %run
  ├─ nb_01_bronze_ingesta
  ├─ nb_02_silver_transforma
  ├─ nb_03_gold_agrega
  ├─ nb_04_modelos_semanticos      (instala semantic-link-labs)
  ├─ nb_05_enriquecer_sempy
  └─ nb_99_validacion              ← correr ANTES de generar la ontología
```

`nb_99_validacion` no es opcional. Verifica las condiciones que, cuando fallan, producen una ontología que **se crea sin errores y no devuelve datos** — el modo de falla más caro de Fabric IQ en preview, porque no hay mensaje que lo explique.

---

## Las cuatro reglas que hacen que la ontología funcione

Están repartidas por los notebooks, pero conviene tenerlas juntas desde el principio. Las cuatro se descubren de la peor manera: la ontología se crea bien y devuelve vacío.

1. **Direct Lake, no Import.** Un modelo Import genera entidades y relaciones, pero **no bindings a datos**. La estructura sale perfecta y detrás no hay nada.
2. **Nada de `decimal`.** Fabric Graph no soporta ese tipo. Una columna decimal se devuelve como `null` en toda consulta. Los montos van en `double`.
3. **Nombres sin espacios ni caracteres especiales.** Con espacio, `,`, `;`, `{}`, `()`, `=`, tab o salto de línea, Delta activa *column mapping* y el grafo deja de leer la tabla.
4. **Toda tabla con clave única declarada.** Incluidos los hechos. La ontología usa la clave primaria del modelo como *entity type key*; sin ella no puede enlazar relaciones a datos.

`nb_00_setup` incluye la función `validar_para_ontologia()`, que verifica las reglas 2, 3 y 4 antes de cada escritura en Silver. Fallar en el notebook es mucho mejor que descubrirlo en la ontología.

---

## Licencia y uso

Material desarrollado para talleres de ingeniería de datos en Microsoft Fabric. Uso libre para fines formativos citando la fuente. Los datos son sintéticos y no representan a ninguna organización real.
