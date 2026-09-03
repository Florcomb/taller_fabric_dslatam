# 8 · Fabric IQ en acción

⏱️ 15 minutos · Artefacto: un data agent sobre `onto_polar_sur`

---

Este bloque cierra el arco: la pregunta que en `nb_03` costó 50 líneas de PySpark y una tabla materializada, ahora se hace hablando.

| Paso | Qué | Min |
|---|---|---|
| 8.1 | Enriquecer la ontología con sinónimos y metadata | 6 |
| 8.2 | Crear el data agent | 3 |
| 8.3 | Las preguntas | 6 |

---

## 8.1 · Enriquecer la ontología

Esto es lo que hace la diferencia entre un agente que responde y uno que dice *"no encuentro esa información"*.

En `nb_05` enriquecimos los **modelos semánticos**. La ontología tiene su propia capa de enriquecimiento, y **no se hereda**: hay que cargarla en su interfaz. La buena noticia es que `nb_99_validacion` ya exportó el vocabulario agrupado por entidad, listo para copiar.

### Qué acepta cada objeto

| Objeto | Descripción | Sinónimos | Metadata clave-valor |
|---|---|---|---|
| Entity type | Sí | **Sí** | Sí |
| Property | Sí | **No** | Sí |
| Relationship type | Sí | **No** | Sí |

**Solo los entity types aceptan sinónimos.** Es la limitación más relevante para el diseño: si un término del negocio se refiere a una propiedad —"quiebre de cadena de frío" apunta a `excursion_termica`—, ese término tiene que entrar por la **descripción** de la propiedad, no por un sinónimo.

### Sinónimos por entidad

**View Entity Type details** → sección **Metadata** → **Edit** → completa **Description** y **Synonyms** → **Update**.

| Entity type | Sinónimos |
|---|---|
| `Tienda` | local, sucursal, punto de venta, pdv, heladeria, tiendas |
| `Producto` | articulo, sku, item, helado, surtido, productos |
| `Cliente` | comprador, cuenta, clientes |
| `Venta` | transaccion, boleta, factura, ticket, ventas |
| `Despacho` | entrega, reparto, envio, despachos |
| `Equipo` | freezer, congelador, camara de frio, equipos, activo |
| `LecturaSensor` | medicion, telemetria, lecturas, sensor |

Si el tiempo aprieta, carga solo `Tienda`, `Equipo` y `LecturaSensor`: son las tres que aparecen en las preguntas de demo.

### Metadata en las propiedades que importan

**Configure** → abre la configuración de binding → sección **Properties** → icono de **etiqueta** junto a la propiedad → **Description** y **Additional metadata** → **Update**.

Las tres que más cambian el resultado:

| Propiedad | Descripción | Additional metadata |
|---|---|---|
| `LecturaSensor.temperatura_c` | Temperatura medida dentro del equipo de frio, en grados Celsius. Por sobre -15 la cadena de frio se considera rota. | `unidad: grados Celsius`, `umbral_excursion: -15` |
| `LecturaSensor.excursion_termica` | Verdadero cuando la temperatura supera los -15 grados Celsius. Es el quiebre de cadena de frio: el producto congelado queda en riesgo. | `criticidad: alta` |
| `Despacho.minutos_atraso` | Minutos de atraso respecto de la ventana comprometida. Cero si llego a tiempo. Sobre 30 minutos se considera critico. | `unidad: minutos`, `umbral_critico: 30` |
| `Venta.monto_total` | Monto facturado con IVA incluido, en pesos chilenos. | `unidad: CLP`, `incluye_iva: true` |
| `Producto.requiere_frio` | Verdadero si el producto exige cadena de frio continua. Identifica el surtido congelado. | `criticidad: alta` |

> **Las claves de metadata deben ser únicas dentro de cada objeto.** No puedes repetir `unidad` dos veces en la misma propiedad.

### Y también las relaciones

**Description** en cada relationship type. Corto y en lenguaje de negocio:

- `entrega_en` — *"El despacho entrega mercaderia en la tienda de destino."*
- `instalado_en` — *"El equipo de frio esta fisicamente instalado en la tienda."*
- `mide` — *"La lectura de sensor corresponde a la medicion de un equipo de frio."*

---

## 8.2 · Crear el data agent

1. En el workspace: **+ Nuevo item → Data agent**. Nómbralo `agente_polar_sur`.
   > Si no aparece el tipo de item, falta habilitarlo en la configuración del tenant.
2. **Add a data source** → busca `onto_polar_sur` → **Add**.
3. Cuando el agente esté listo, la ontología y sus entity types aparecen en el Explorer.

### La instrucción que hay que agregar sí o sí

**Agent instructions** en la cinta → al final del cuadro de texto, agrega:

```
Support group by in GQL
```

Es un *workaround* documentado por Microsoft para un problema conocido de agregación. Sin esa línea, las preguntas que agrupan —que son casi todas las interesantes— fallan o devuelven parcialidades. Se aplica sola.

Aprovecha de agregar también el contexto del negocio:

```
Support group by in GQL

Polar Sur es una cadena de heladerias. Una excursion termica ocurre cuando la
temperatura de un equipo supera los -15 grados Celsius: en ese momento la cadena
de frio se rompe y el producto congelado queda en riesgo. Los productos con
requiere_frio verdadero son los que dependen de la cadena de frio. Los montos
estan en pesos chilenos.
```

---

## 8.3 · Las preguntas

> Si las primeras consultas dicen que no hay datos, espera un par de minutos: el agente todavía se está inicializando. Vuelve a preguntar.

### Nivel 1 · Un solo dominio

Calientan el motor y confirman que los bindings funcionan.

- *¿Cuántas tiendas tiene Polar Sur y en qué regiones?*
- *¿Qué productos son congelados?*
- *Muéstrame los equipos instalados en la sucursal de Providencia.*

Fíjate en el vocabulario: preguntamos por **"sucursal"**, y la entidad se llama `Tienda`. Eso lo resolvió el sinónimo.

### Nivel 2 · Dos dominios

Aquí ya ningún modelo semántico del taller alcanza.

- *¿Qué tiendas tuvieron equipos con quiebre de cadena de frío?*
- *¿En qué locales hubo despachos atrasados de más de una hora?*
- *¿Cuál fue la temperatura máxima registrada por tienda?*

### Nivel 3 · La pregunta del taller

- *¿Cuánta venta de producto congelado hubo en tiendas que ese mismo día tuvieron un freezer en excursión térmica y recibieron un despacho atrasado?*

**Compara el resultado con el número que imprimió `nb_03`.** Ese es el momento: la misma respuesta, sin escribir un join.

Y ahora las variantes, que en Gold habrían costado una tabla nueva cada una:

- *¿Qué marcas se vieron más afectadas por quiebres de cadena de frío?*
- *¿Qué clientes compraron productos congelados en tiendas con problemas de temperatura?*
- *¿Hay relación entre despachos atrasados y excursiones térmicas en la misma tienda?*

Ninguna necesitó desarrollo. Ese es el argumento completo del taller.

### Prueba el contraste, si queda tiempo

Vale mucho más que una lámina: pregunta *"¿qué sucursales tuvieron quiebre de cadena de frío?"* **antes** de cargar los sinónimos de 8.1 y después. La misma pregunta, sobre los mismos datos, con y sin vocabulario.

---

## Qué esperar de verdad

Fabric IQ está en **preview**, y un taller que prometa magia deja gente frustrada el lunes. Lo que la documentación de Microsoft declara hoy:

- El enriquecimiento semántico ayuda al agente en la **exploración del esquema y el razonamiento**, pero **no interviene directamente en la generación de la consulta**. La mejora es real y es indirecta.
- El enriquecimiento **a nivel de relación** todavía no lo usan las experiencias de data agent públicas.
- La agregación necesita el workaround de `Support group by in GQL`.
- El grafo **no se entera** de datos nuevos en el origen: hay que refrescarlo a mano, y el refresco es completo y tiene costo de capacidad.

Nada de eso invalida el ejercicio. Sí conviene decirlo: la ontología es hoy una inversión en **vocabulario gobernado**, y su retorno crece a medida que las experiencias de agente maduran encima.

---

## Otras formas de consumir la ontología

El data agent es la más rápida de mostrar, no la única:

| Vía | Para qué |
|---|---|
| **Fabric data agent** | Preguntas de negocio dentro de Fabric. Es la del taller |
| **Foundry IQ** (Azure AI Foundry) | Agentes con herramientas propias e integración con sistemas empresariales |
| **Copilot Studio** | Agentes conversacionales de bajo código, publicables en Teams |
| **Operations agent** | Monitoreo continuo de la ontología contra objetivos de negocio, con recomendaciones |
| **Servidor MCP de ontología** | Exponer la ontología como herramienta a un asistente externo |
| **Fabric Graph / GQL** | Consultas de grafo directas, para casos de análisis de caminos y centralidad |

---

## Cierre

Lo que quedó construido, en orden:

```
dato crudo          nb_01   Bronze, con trazabilidad y sin limpiar
  ↓
dato afirmado       nb_02   Silver, con reglas de negocio y comentarios
  ↓
dato modelado       nb_04   3 modelos Direct Lake, uno por dominio
  ↓
dato hablado        nb_05   vocabulario: sinónimos y metadata
  ↓
dato con significado  ─     ontología: entidades y relaciones cruzadas
  ↓
dato accionable       ─     agente que responde en lenguaje natural
```

Y la frase para cerrar: **el modelo semántico le enseñó a la empresa a calcular; la ontología le enseña a significar.**

---

**Ver también:** [ontologia/preguntas-demo.md](../ontologia/preguntas-demo.md) · [99-troubleshooting.md](99-troubleshooting.md)
