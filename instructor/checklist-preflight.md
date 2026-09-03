# Checklist previo · facilitador

Todo lo que hay que verificar **antes** de la sesión. Si algo de la sección A falla, el taller no se puede dar como está diseñado: hay que decidir el plan B con anticipación, no en vivo.

---

## A · Bloqueantes · verificar con 48 h de anticipación

Requieren rol de administrador de Fabric. Si el tenant no los tiene, nadie lo resuelve el mismo día.

- [ ] **Capacidad Fabric** disponible para todos los participantes (F2 o superior, o trial vigente)
- [ ] **Ontology item (preview)** habilitado en el tenant
      *Portal de administración → Configuración del tenant → buscar "Ontology"*
- [ ] **Data agent** habilitado en el tenant
- [ ] Los participantes pueden **crear workspaces**, o ya tienen uno asignado con rol de Colaborador
- [ ] **Acceso público de entrada** habilitable en los workspaces
      *Sin esto la ontología se genera sin bindings y el bloque 8 no funciona*

> **Si Ontology no está habilitado:** el taller llega hasta el bloque 6. Es un taller válido de 90 minutos sobre medallón + Direct Lake + sempy, pero hay que decirlo al abrir, no al minuto 100.

---

## B · Ensayo completo · una semana antes

**Correr el taller entero, de punta a punta, en un workspace limpio.** No hay sustituto para esto: Fabric IQ está en preview y la interfaz cambia entre revisiones.

- [ ] Los tres lakehouses se crean
- [ ] `nb_01` corre y da los conteos esperados (12 / 40 / 315 / 20.000 / 8 / 10 / 1.500 / 36 / 50.000)
- [ ] `nb_02` corre; `validar_para_ontologia` pasa en las nueve tablas
- [ ] `nb_03` corre; **anotar el monto de riesgo de cadena de frío** para compararlo en vivo
- [ ] `nb_04` corre; los tres modelos con 4/4/3 tablas, relaciones > 0, claves en todas
- [ ] `nb_05` corre; `list_synonyms` devuelve ~100 filas
- [ ] `nb_99` termina con "Todo en orden"
- [ ] **Generate Ontology** aparece en la cinta de `sm_polar_ventas`
- [ ] La ontología se genera con las cuatro entidades y sus bindings
- [ ] **Instances** muestra datos reales, no vacío
- [ ] Las tres entidades manuales se crean y enlazan sin problema
- [ ] Las relaciones cruzadas se configuran y el grafo conecta
- [ ] El data agent responde la pregunta de nivel 3

Anota en cada bloque **cuánto tardó de verdad**. Los tiempos de la agenda son estimados; los de tu tenant son datos.

---

## C · El día anterior

- [ ] **Workspace de respaldo listo y completo** hasta el bloque 6, para proyectar si alguien se cae
- [ ] Fork del repositorio hecho y probado con la vía B, en un workspace distinto
- [ ] Los conteos y el monto de `nb_03` anotados y a mano
- [ ] Enlace al repositorio enviado a los participantes
- [ ] Requisitos previos enviados, con la instrucción de **crear su workspace antes de llegar**

---

## D · 30 minutos antes

- [ ] **Ejecutar una celda trivial en cada notebook del workspace de respaldo** para dejar el starter pool caliente. El primer arranque de Spark del día tarda 2–4 minutos y en vivo se siente eterno
- [ ] Verificar que la ontología del respaldo sigue respondiendo (el grafo puede necesitar refresco)
- [ ] Abrir las pestañas: workspace propio, repositorio, `ontologia/preguntas-demo.md`, `docs/99-troubleshooting.md`
- [ ] Confirmar que el data agent del respaldo responde: a veces necesita minutos para inicializar

---

## E · Al abrir la sesión

- [ ] Confirmar en sala quién tiene workspace con capacidad. Los que no, van directo a vía B en el workspace de un compañero o miran en pantalla compartida
- [ ] Decir de entrada que **Fabric IQ está en preview** y que la interfaz puede diferir del material
- [ ] Repartir a los rezagados el enlace de la vía B: [docs/09-via-rapida-git.md](../docs/09-via-rapida-git.md)

---

## Umbrales de decisión durante el taller

Cuándo cortar por lo sano. Definirlos antes evita decidir con la sala mirando.

| Situación | Umbral | Acción |
|---|---|---|
| La sesión de Spark no arranca | 5 min | Seguir en el workspace de respaldo, proyectado |
| Más de un tercio de la sala atrasada al minuto 60 | — | Todos a vía B, y avanzar |
| `nb_04` falla en varios participantes | 10 min | Proyectar el respaldo y continuar con la teoría del bloque 5 |
| La ontología se genera sin bindings | 5 min | Revisar acceso público de entrada. Si no se resuelve, usar el respaldo |
| El data agent no responde | 5 min | Usar la vista de grafo (**Overview → Expand → Query builder**). Se pierde el lenguaje natural, se conserva el argumento |

---

## Lo mínimo indispensable

Si todo sale mal y quedan 30 minutos, esto es lo que **no** se puede dejar de mostrar, proyectado desde el respaldo:

1. La tabla `agg_riesgo_cadena_frio` de `nb_03` y el join que costó escribirla.
2. La ontología con el grafo de las tres relaciones cruzadas.
3. La misma pregunta hecha al agente en lenguaje natural.

Eso son tres minutos y es el taller completo en miniatura.
