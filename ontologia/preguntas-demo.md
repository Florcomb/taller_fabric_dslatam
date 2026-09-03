# Preguntas de demo

Para el agente `agente_polar_sur` sobre la ontología `onto_polar_sur`.

Ordenadas por número de dominios que cruzan. Las de nivel 1 y 2 calientan el motor; la de nivel 3 es la del taller.

> Antes de empezar: en **Agent instructions** debe estar `Support group by in GQL`. Sin eso, casi toda pregunta que agrupe falla o responde parcialmente. Ver [08-fabric-iq.md](../docs/08-fabric-iq.md#82--crear-el-data-agent).

---

## Nivel 1 · Un dominio

Confirman que los bindings funcionan y que el vocabulario está cargado.

| Pregunta | Prueba |
|---|---|
| *¿Cuántas tiendas tiene Polar Sur y en qué regiones?* | Bindings de `Tienda` |
| *¿Qué productos son congelados?* | Propiedad booleana + sinónimo "congelado" |
| *Muéstrame los equipos instalados en la sucursal de Providencia.* | Sinónimo "sucursal" → `Tienda` + relación `instalado_en` |
| *¿Cuál fue la venta total del mes pasado?* | Agregación simple (requiere la instrucción de GQL) |
| *¿Cuántos despachos llegaron atrasados?* | Propiedad `llego_atrasado` |

**Qué mirar:** preguntamos por "sucursal" y la entidad se llama `Tienda`. Eso lo resolvió el sinónimo del bloque 8.1. Sin él, el agente no encuentra nada.

---

## Nivel 2 · Dos dominios

Aquí ya ningún modelo semántico del taller alcanza. La venta está en uno, la temperatura en otro.

| Pregunta | Cruza |
|---|---|
| *¿Qué tiendas tuvieron equipos con quiebre de cadena de frío?* | Frío ↔ Tienda |
| *¿En qué locales hubo despachos atrasados de más de una hora?* | Logística ↔ Tienda |
| *¿Cuál fue la temperatura máxima registrada por tienda?* | Frío ↔ Tienda, con agregación |
| *¿Qué tiendas vendieron más congelados?* | Comercial ↔ Producto |
| *¿Qué rutas concentran los despachos atrasados?* | Logística interna |

**Qué mirar:** la respuesta referencia **entidades y relaciones**, no tablas. El agente no dice "hice un join entre `dim_equipo` y `dim_tienda`": dice que ciertos equipos están instalados en ciertas tiendas.

---

## Nivel 3 · Tres dominios · la pregunta del taller

> *¿Cuánta venta de producto congelado hubo en tiendas que ese mismo día tuvieron un freezer en excursión térmica y recibieron un despacho atrasado?*

**Compara el resultado con el número que imprimió `nb_03_gold_agrega`:**

```
Venta de congelado expuesta a riesgo de cadena de frio: $XX,XXX,XXX CLP
Dias-tienda afectados: XXX
```

En Gold esa respuesta costó tres agregaciones, cuatro joins, ~50 líneas de PySpark y una tabla materializada. Aquí costó una frase.

### Las variantes

Y ahora lo que de verdad importa: cada una de estas, en el mundo de Gold, habría sido **una tabla nueva, un desarrollo y un despliegue**. Aquí no cuestan nada.

- *¿Qué marcas se vieron más afectadas por quiebres de cadena de frío?*
- *¿Qué clientes compraron productos congelados en tiendas con problemas de temperatura?*
- *¿Hay relación entre despachos atrasados y excursiones térmicas en la misma tienda?*
- *¿Qué tiendas tienen a la vez los peores tiempos de entrega y las peores temperaturas?*
- *¿Los equipos de qué marca registran más excursiones térmicas?*
- *¿Qué región concentra el mayor riesgo de cadena de frío?*

---

## El contraste que vale la clase

Si queda tiempo, esta secuencia enseña más que cualquier lámina.

**Antes de cargar los sinónimos del bloque 8.1**, pregunta:

> *¿Qué sucursales tuvieron quiebre de cadena de frío?*

El agente probablemente no encuentre nada: no existe ninguna entidad llamada "sucursal" ni ninguna propiedad llamada "quiebre de cadena de frío".

**Carga los sinónimos y las descripciones. Pregunta lo mismo.**

Mismos datos, mismo modelo, misma pregunta. Lo único que cambió es el vocabulario. Es el argumento completo a favor de invertir en metadata, hecho en dos minutos.

---

## Preguntas para forzar los límites

Si el grupo va rápido, vale la pena mostrar también dónde **no** llega hoy la herramienta. Es más honesto y genera mejor conversación que quedarse solo en lo que funciona.

| Pregunta | Qué esperar |
|---|---|
| *¿Cuál es el ticket promedio?* | `Ticket promedio` es una **medida DAX**. La ontología no consulta medidas: el agente tendrá que calcularlo desde las propiedades, o no responderá |
| *¿Cuánto vendimos ayer?* | El dataset va de enero a agosto de 2026. Buen momento para hablar de datos sintéticos y de cómo un agente maneja preguntas sin respuesta |
| *¿Qué debería hacer para reducir los quiebres de frío?* | Sale del alcance de una consulta de datos. Sirve para separar **agente de datos** de **agente de decisión** |
| *Muéstrame la evolución de la temperatura del equipo EQ-0007* | Serie de tiempo. En el taller `ft_lectura_sensor` está enlazada como dato **estático**; para que funcione como serie hay que agregar un *time series binding* |

Esa última tiene una lección de diseño detrás: la ontología distingue **bindings estáticos** (uno por entidad, definen las instancias) de **bindings de serie de tiempo** (varios por entidad, agregan observaciones con marca temporal). Enlazar `LecturaSensor` como entidad estática, con `id_lectura` como clave, es la vía rápida y funciona; modelarla como serie de tiempo sobre `Equipo` sería lo correcto para un caso de IoT real.

---

## Guion sugerido para la demo · 6 minutos

| Min | Qué |
|---|---|
| 0–1 | Dos preguntas de nivel 1. Mostrar que responde y que usa sinónimos |
| 1–3 | Dos de nivel 2. Señalar que ningún modelo semántico podría |
| 3–5 | **La pregunta del taller.** Comparar contra el número de `nb_03` |
| 5–6 | Dos variantes seguidas, sin pausa. El punto es la velocidad: **cero desarrollo entre una y otra** |

Y la frase de cierre: **la ontología no reemplaza a Gold; reemplaza a la siguiente tabla de Gold que ibas a escribir.**
