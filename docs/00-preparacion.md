# 0 · Contexto y preparación

⏱️ 10 minutos

---

## Qué es Fabric IQ, en una frase

Fabric IQ es la capa donde el negocio define **qué son las cosas** —una tienda, un despacho, un equipo de frío— y las conecta a los datos que ya viven en OneLake, para que personas y agentes razonen sobre conceptos en vez de sobre tablas.

El item que materializa eso se llama **ontología** *(preview)*, y tiene cuatro piezas:

| Pieza | Qué es | Ejemplo en el taller |
|---|---|---|
| **Entity type** | El concepto reutilizable | `Tienda`, `Despacho`, `Equipo` |
| **Property** | Un hecho sobre el concepto, con tipo declarado | `Tienda.comuna`, `LecturaSensor.temperatura_c` |
| **Relationship** | Un vínculo dirigido y tipado entre conceptos | `Despacho llega_a Tienda` |
| **Data binding** | La conexión de la definición a datos reales de OneLake | `Tienda` → `lh_silver_polar.dbo.dim_tienda` |

## Ontología y modelo semántico no son lo mismo

Es la confusión más común, y vale la pena zanjarla antes de empezar:

| | Modelo semántico | Ontología |
|---|---|---|
| Parte de | Un caso de análisis | Un concepto de negocio |
| Optimizado para | Calcular y explorar métricas | Razonar y navegar relaciones |
| Alcance natural | Un dominio | Varios dominios a la vez |
| Grano | El que convenga al informe | Atómico: una fila = una cosa |
| Consumidor típico | Un informe, una persona | Un agente, un proceso |
| Medidas DAX | Su razón de ser | **No las usa** |

No compiten. En este taller la ontología se construye **encima** de los modelos semánticos: los tres son su punto de entrada.

---

## Verificación previa

Estos cinco puntos hay que confirmarlos **antes** de la sesión. Los tres primeros no se pueden arreglar en el momento si el tenant no los tiene habilitados.

### 1 · Capacidad Fabric

El workspace necesita capacidad Fabric asignada: F2 o superior, o una trial vigente.

**Configuración del workspace → Licencia → Tipo de licencia**

Una capacidad de Power BI Pro **no sirve**: no habilita lakehouses, notebooks Spark ni Fabric IQ.

### 2 · Ontology item (preview) habilitado en el tenant

**Portal de administración → Configuración del tenant → buscar "Ontology"**

Requiere rol de administrador de Fabric. Si está deshabilitado, el taller se puede hacer hasta el bloque 6 (modelos semánticos y `sempy`) pero no el 7 ni el 8.

### 3 · Acceso público de entrada en el workspace

**Configuración del workspace → Red → Acceso público de entrada: habilitado**

Este es el que más silenciosamente arruina el taller. Con un modelo Direct Lake, la generación de la ontología produce bindings a datos **solo si el workspace del lakehouse tiene acceso público de entrada habilitado**. Si está deshabilitado, la ontología se crea igual, con sus entidades y relaciones, y **sin datos detrás**. No hay mensaje de error.

### 4 · Un workspace propio, no "Mi área de trabajo"

No se puede generar una ontología desde un modelo semántico que vive en Mi área de trabajo. Cada participante crea su workspace:

```
taller-fabriciq-<nombre>
```

### 5 · Rol de Colaborador o superior

Para crear items, ejecutar notebooks y conectar git.

---

## Elegir la vía

| | Vía A · paso a paso | Vía B · git sync |
|---|---|---|
| Los items se crean | A mano, uno por uno | Solos, al sincronizar |
| Tiempo hasta el bloque 5 | ~60 min | ~15 min |
| Qué se aprende | Todo el detalle | El resultado, y CI/CD de Fabric |
| Para quién | El taller en vivo | Quien llega tarde o repite |

Las dos convergen en el bloque 6. Se puede empezar por A y saltar a B si el tiempo se va.

→ Vía B: **[09-via-rapida-git.md](09-via-rapida-git.md)**

---

## Convenciones de nombres

Consistentes en todo el taller. Si cambias una, cámbiala también en `nb_00_setup`.

| Item | Nombre |
|---|---|
| Lakehouse Bronze | `lh_bronze_polar` |
| Lakehouse Silver | `lh_silver_polar` |
| Lakehouse Gold | `lh_gold_polar` |
| Modelos semánticos | `sm_polar_ventas`, `sm_polar_operaciones`, `sm_polar_activos` |
| Ontología | `onto_polar_sur` |

> Los nombres de ontología aceptan letras, números y guion bajo. **Ni espacios ni guiones medios.**

---

**Siguiente:** [01 · Tres lakehouses](01-lakehouses.md)
