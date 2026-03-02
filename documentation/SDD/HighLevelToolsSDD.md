FEATURE IMPLEMENTATION — SDD MASTER SPEC (ALTO NIVEL)
1. Instrucción Principal

Actúa como un Arquitecto de Software Senior. Tu objetivo es transformar el sistema de "Prototipo de Simulación" a un "Sistema de Turismo Real" mediante la implementación de capacidades auténticas en la capa de herramientas (Tools).
2. Contexto de la Feature: "Real-World Tourism Capabilities"

El sistema actual es una cáscara funcional. Esta feature consiste en dotar al TourismMultiAgent de ojos y oídos reales en el mundo exterior.

Objetivos Estratégicos:

    Eliminación de Stubs: Sustituir la lógica hardcoded de Madrid por proveedores de datos dinámicos.

    Decisión Profile-Driven: El perfil de accesibilidad del usuario debe ser el filtro mandatorio para cualquier dato que devuelva una tool.

    Expansión de Casos de Uso: Permitir consultas sobre cualquier ciudad/punto de interés, no solo los 10 museos actuales de Madrid.

3. Contrato de Capacidades (Single Source of Truth)

Cualquier implementación técnica futura deberá cumplir con estos 3 pilares de datos:

    Inyección Universal de Perfil: Toda tool debe recibir el objeto Profile como contexto primario de filtrado.

    Interfaz de Proveedor (Integration Layer): Las herramientas no deben conocer la API final (Google, Yelp, etc.). Deben consumir una interfaz abstracta que normalice los datos de turismo.

    Contrato de Salida Normalizado: Independientemente de la fuente, el resultado debe incluir siempre metadatos de accesibilidad comparados contra el perfil del usuario.

4. Definición de Nuevos Casos de Uso Reales

Para que el sistema sea "Real", las nuevas implementaciones deben resolver:

    Caso A (Rutas Dinámicas): "Soy usuario en silla de ruedas, dime cómo llegar de mi ubicación actual a la Plaza Mayor evitando estaciones de metro sin ascensor".

    Caso B (Validación de Aforos/Horarios): "Busca museos de arte contemporáneo abiertos ahora que tengan entrada gratuita para personas con discapacidad".

    Caso C (Descubrimiento Universal): "¿Qué opciones de turismo accesible hay en Barcelona para una persona con discapacidad visual?".

5. Metodología de Implementación (Flujo de Decisión)

El SDD establece que en la siguiente fase se deberá decidir:

    Selección de Data Sources: Identificar qué APIs ofrecen el mejor ratio de datos de accesibilidad (ej. Google Places API vs OpenStreetMap).

    Estrategia de Orquestación: Decidir si el agente llama a las tools por separado o si se crea una "Mega-Tool" de búsqueda que combine Info + Accesibilidad + Ubicación.

    Mecanismo de Re-ranking: Cómo el sistema prioriza un resultado sobre otro basándose en el "Score de Match" con el perfil del usuario.

6. Checklist: Definition of Done (DoD) de Alto Nivel

    [ ] El sistema responde con datos que NO están en los archivos .json locales del proyecto.

    [ ] El perfil de usuario influye directamente en el orden y la inclusión de los resultados de las herramientas.

    [ ] Existe una capa de "Integración" que permite cambiar de proveedor de datos sin tocar la lógica del Agente.

    [ ] El sistema maneja fallos de conexión externa devolviendo una respuesta informativa de seguridad (Fallback).